"""UI pattern recognition and adaptive state matching helpers.

Merged from Jake's aBotTesty fork and hardened for the JAMboree active-video
crawler.  These helpers are optional intelligence: if they misclassify a screen,
they should influence ordering/thresholds, never crash the app.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import re


class UIPattern(Enum):
    GRID_MENU = "grid_menu"
    LINEAR_MENU = "linear_menu"
    FORM = "form"
    VIDEO_PLAYER = "video_player"
    INFO_CARD = "info_card"
    PIN_PROMPT = "pin_prompt"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        return self.value


@dataclass
class PatternConfidence:
    pattern: UIPattern
    confidence: float
    reasons: List[str] = field(default_factory=list)


class PatternRecognizer:
    GRID_KEYWORDS = re.compile(r"\b(guide|grid|channel|channels|apps|gallery|library|catalog|browse|tiles|trending)\b", re.I)
    LINEAR_MENU_KEYWORDS = re.compile(r"\b(settings|menu|options|preferences|setup|configure|diagnostics|parental|locks|locked|list)\b", re.I)
    FORM_KEYWORDS = re.compile(r"\b(search|enter|input|type|keyboard|find|query|clear|space|delete|abc|qwerty)\b", re.I)
    VIDEO_KEYWORDS = re.compile(r"\b(live|watching|playing|playback|pause|resume|recorded|dvr|rewind|skip|recall)\b", re.I)
    INFO_KEYWORDS = re.compile(r"\b(info|details|description|synopsis|about|diagnostic|status|receiver|network|system)\b", re.I)
    PIN_KEYWORDS = re.compile(r"\b(pin|passcode|password|enter code|unlock|locked|parental code|parental pin)\b", re.I)

    def __init__(self) -> None:
        self.learned_patterns: Dict[str, UIPattern] = {}
        self.pattern_history: List[Dict[str, Any]] = []

    def classify_screen(self, fp: Any, focus: Optional[Dict[str, Any]] = None) -> PatternConfidence:
        focus = focus if isinstance(focus, dict) else (getattr(fp, "focus", {}) or {})
        text = self._get_all_text(fp, focus)
        scores: Dict[UIPattern, float] = {p: 0.0 for p in [
            UIPattern.GRID_MENU, UIPattern.LINEAR_MENU, UIPattern.FORM,
            UIPattern.VIDEO_PLAYER, UIPattern.INFO_CARD, UIPattern.PIN_PROMPT,
        ]}
        reasons: Dict[UIPattern, List[str]] = {p: [] for p in scores}

        keyword_rules = [
            (UIPattern.GRID_MENU, self.GRID_KEYWORDS, 0.30, "grid/menu keywords"),
            (UIPattern.LINEAR_MENU, self.LINEAR_MENU_KEYWORDS, 0.32, "linear/settings keywords"),
            (UIPattern.FORM, self.FORM_KEYWORDS, 0.34, "form/search keywords"),
            (UIPattern.VIDEO_PLAYER, self.VIDEO_KEYWORDS, 0.24, "video/playback keywords"),
            (UIPattern.INFO_CARD, self.INFO_KEYWORDS, 0.26, "info/status keywords"),
            (UIPattern.PIN_PROMPT, self.PIN_KEYWORDS, 0.45, "PIN/lock keywords"),
        ]
        for pat, rx, weight, why in keyword_rules:
            if rx.search(text):
                scores[pat] += weight
                reasons[pat].append(why)

        self._score_visual_features(fp, scores, reasons)
        if isinstance(focus, dict) and focus.get("found"):
            self._score_focus_features(focus, scores, reasons)
        self._score_layout_hints(fp, scores, reasons)

        if max(scores.values()) < 0.22:
            return PatternConfidence(UIPattern.UNKNOWN, 0.0, ["insufficient evidence"])
        best, score = max(scores.items(), key=lambda item: item[1])
        conf = max(0.0, min(1.0, float(score)))
        state_id = getattr(fp, "state_id", "")
        if state_id:
            self.learned_patterns[state_id] = best
        self.pattern_history.append({"state_id": state_id, "pattern": best.value, "confidence": conf, "reasons": reasons[best][-5:]})
        self.pattern_history = self.pattern_history[-500:]
        return PatternConfidence(best, round(conf, 4), reasons[best])

    def _get_all_text(self, fp: Any, focus: Dict[str, Any]) -> str:
        parts: List[str] = []
        for val in [getattr(fp, "ocr_text", "")]:
            if val:
                parts.append(str(val))
        if isinstance(focus, dict):
            for key in [
                "page_name", "block_title", "screen_title", "menu_title", "human_label",
                "focused_item", "focused_value", "label_text", "focus_text", "context_text", "row_text",
            ]:
                val = focus.get(key)
                if isinstance(val, str) and val.strip():
                    parts.append(val)
            ui = focus.get("ui_context") or {}
            if isinstance(ui, dict):
                for key in ["context_summary", "screen_title", "focused_item", "focused_value", "row_text"]:
                    val = ui.get(key)
                    if isinstance(val, str) and val.strip():
                        parts.append(val)
        return " ".join(parts).lower()

    def _score_visual_features(self, fp: Any, scores: Dict[UIPattern, float], reasons: Dict[UIPattern, List[str]]) -> None:
        variance = float(getattr(fp, "variance", 0.0) or 0.0)
        edge_density = float(getattr(fp, "edge_density", 0.0) or 0.0)
        token_count = len(getattr(fp, "ocr_tokens", []) or [])
        if variance > 1400 and edge_density < 0.16:
            scores[UIPattern.VIDEO_PLAYER] += 0.20
            reasons[UIPattern.VIDEO_PLAYER].append("video-like motion/texture")
        if token_count > 35:
            scores[UIPattern.INFO_CARD] += 0.18
            reasons[UIPattern.INFO_CARD].append(f"text-dense screen ({token_count} tokens)")
        if 0.05 <= edge_density <= 0.22:
            scores[UIPattern.GRID_MENU] += 0.08
            scores[UIPattern.LINEAR_MENU] += 0.06
            reasons[UIPattern.GRID_MENU].append("structured UI edges")

    def _score_focus_features(self, focus: Dict[str, Any], scores: Dict[UIPattern, float], reasons: Dict[UIPattern, List[str]]) -> None:
        region = str(focus.get("region") or "").lower()
        role = str(focus.get("focus_role") or "").lower()
        row = focus.get("row_guess")
        col = focus.get("col_guess")
        if col is not None and row is not None:
            scores[UIPattern.GRID_MENU] += 0.18
            reasons[UIPattern.GRID_MENU].append("row/column focus geometry")
        if "setting" in role or "list" in role or region in {"left-pane", "right-pane"}:
            scores[UIPattern.LINEAR_MENU] += 0.18
            reasons[UIPattern.LINEAR_MENU].append("focus looks like settings/list item")
        if focus.get("focused_value"):
            scores[UIPattern.FORM] += 0.10
            scores[UIPattern.LINEAR_MENU] += 0.10
            reasons[UIPattern.LINEAR_MENU].append("focused setting/value pair")
        risk = focus.get("risk_flags") or []
        if any("pin" in str(x).lower() or "lock" in str(x).lower() for x in risk):
            scores[UIPattern.PIN_PROMPT] += 0.25
            reasons[UIPattern.PIN_PROMPT].append("PIN/lock risk flag")

    def _score_layout_hints(self, fp: Any, scores: Dict[UIPattern, float], reasons: Dict[UIPattern, List[str]]) -> None:
        sid = getattr(fp, "state_id", "")
        if sid in self.learned_patterns:
            pat = self.learned_patterns[sid]
            scores[pat] += 0.14
            reasons[pat].append(f"previously learned as {pat.value}")

    def get_pattern_stats(self) -> Dict[str, Any]:
        counts = Counter(p.value if isinstance(p, UIPattern) else str(p) for p in self.learned_patterns.values())
        return {"total_classified": len(self.learned_patterns), "by_pattern": dict(counts), "history_length": len(self.pattern_history)}


class AdaptiveThresholdModel:
    """Adaptive similarity thresholds by UI pattern plus state stability."""

    def __init__(self) -> None:
        self.thresholds: Dict[str, float] = {
            "grid_menu": 0.82,
            "linear_menu": 0.94,
            "form": 0.88,
            "video_player": 0.75,
            "info_card": 0.91,
            "pin_prompt": 0.92,
            "unknown": 0.86,
        }
        self.state_stability: Dict[str, float] = {}
        self.stats: Dict[str, Dict[str, int]] = {k: {"total": 0, "matches": 0} for k in self.thresholds}

    def get_threshold(self, pattern: str, state_id: Optional[str] = None, default: float = 0.86) -> float:
        key = str(pattern or "unknown")
        base = float(self.thresholds.get(key, default))
        if state_id and state_id in self.state_stability:
            base = min(0.98, base + self.state_stability[state_id] * 0.06)
        return max(0.70, min(0.98, base))

    def update_state_stability(self, state_id: str, observations: int, variance: float) -> None:
        obs = min(1.0, max(0.0, float(observations) / 20.0))
        var = max(0.0, 1.0 - (float(variance or 0.0) / 2400.0))
        self.state_stability[state_id] = round(obs * 0.62 + var * 0.38, 4)

    def record_match(self, pattern: str, matched: bool) -> None:
        key = str(pattern or "unknown") if str(pattern or "unknown") in self.stats else "unknown"
        self.stats[key]["total"] += 1
        if matched:
            self.stats[key]["matches"] += 1

    def get_stats(self) -> Dict[str, Any]:
        return {"thresholds": dict(self.thresholds), "state_stability_count": len(self.state_stability), "stats": self.stats}
