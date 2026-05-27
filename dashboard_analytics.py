#!/usr/bin/env python3
"""Learning dashboard analytics for the merged STB crawler app.

This module reads the crawler's persistent artifacts and emits two views:
- executive: progress, confidence, risk, learning maturity
- engineering: state/action coverage, OCR/focus quality, timings, rewards, frontiers

It is intentionally Superset-friendly: every panel can be exported as JSON/CSV/SQL
without requiring Superset at runtime.
"""
from __future__ import annotations

import csv
import io
import json
import math
import re
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ISO_ZONES = ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z")
DEFAULT_ACTIONS = ["up", "down", "left", "right", "guide", "back", "home", "info", "select"]
IMPORTANT_WORDS = re.compile(r"\b(parental|lock|locked|settings|diagnostics|network|audio|caption|dvr|guide|apps|search|pin|password|control|receiver|signal|system)\b", re.I)
RISK_WORDS = re.compile(r"\b(pin|password|purchase|rent|adult|parental|delete|reset|factory|locked|unlock|payment|subscribe)\b", re.I)
OCR_SOUP = re.compile(r"\b([a-z]{1,2}|[a-z]*[0-9][a-z0-9]*|[bcdfghjklmnpqrstvwxyz]{4,})\b", re.I)

try:
    from channel_metadata import is_plausible_program_title, sanitize_program_title, is_plausible_channel_code
    from ppv_pricing import extract_purchase_pricing, format_limit
    from time_context import extract_display_clock
    from ondemand_flow_intelligence import normalize_title as normalize_od_title
except Exception:  # pragma: no cover - dashboard can still render legacy data
    def is_plausible_program_title(value: Any) -> bool:
        val = clean_text(value, 180) if 'clean_text' in globals() else str(value or '').strip()
        return bool(val and len(val) >= 3)
    def sanitize_program_title(value: Any) -> str:
        val = clean_text(value, 180) if 'clean_text' in globals() else str(value or '').strip()
        return val if is_plausible_program_title(val) else ''
    def is_plausible_channel_code(value: Any) -> bool:
        val = str(value or '').strip().upper()
        return bool(re.fullmatch(r'[A-Z0-9&+!-]{1,10}', val))
    def extract_purchase_pricing(*texts: Any) -> Dict[str, Any]:
        txt = ' '.join(str(t or '') for t in texts)
        m = re.search(r'\$\s*(\d+(?:\.\d{2})?)', txt)
        if m:
            return {'found': True, 'amount': float(m.group(1)), 'price_text': '$'+m.group(1), 'category': 'paid', 'confidence': 0.8, 'flags': []}
        if re.search(r'\bfree\b', txt, re.I):
            return {'found': True, 'amount': 0.0, 'price_text': '$0.00', 'category': 'free', 'confidence': 0.6, 'flags': []}
        return {'found': False, 'amount': None, 'price_text': '', 'category': 'unknown', 'confidence': 0.0, 'flags': []}
    def format_limit(value: Optional[float]) -> str:
        return 'unlimited' if value is None else f'${float(value):.2f}'
    def extract_display_clock(screen_text: str = '', focus: Optional[Dict[str, Any]] = None, observed_at: Any = None) -> Dict[str, Any]:
        return {'found': False, 'displayed': '', 'actual_iso': '', 'drift_minutes': None, 'confidence': 0, 'source': '', 'flags': []}
    def normalize_od_title(value: Any) -> str:
        return clean_text(value, 180) if 'clean_text' in globals() else str(value or '').strip()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path, default: Any) -> Any:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return default
    return default


def parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except Exception:
        pass
    # Some artifacts have compact timestamp fragments in screenshot file names.
    m = re.search(r"(20\d{6})[_-](\d{6})", s)
    if m:
        try:
            return datetime.strptime("".join(m.groups()), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def iso_bucket(value: Any, granularity: str = "hour") -> str:
    dt = parse_ts(value)
    if not dt:
        return "unknown"
    if granularity == "day":
        return dt.strftime("%Y-%m-%d")
    return dt.strftime("%Y-%m-%d %H:00")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except Exception:
        return default


def pct(part: float, total: float) -> float:
    return round((part / total * 100.0), 2) if total else 0.0


def clean_text(s: Any, max_len: int = 140) -> str:
    return " ".join(str(s or "").replace("\n", " ").split())[:max_len]




def normalize_channel_number(value: Any) -> str:
    s = clean_text(value, 40).replace("–", "-").strip()
    m = re.search(r"\b(\d{1,4}(?:-\d{1,3})?)\b", s)
    return m.group(1) if m else ""


def channel_sort_tuple(value: Any) -> Tuple[int, int, str]:
    s = normalize_channel_number(value)
    if not s:
        return (999999, 999999, str(value or ""))
    try:
        base = int(s.split("-", 1)[0])
    except Exception:
        base = 999999
    suffix = 0
    if "-" in s:
        try:
            suffix = int(s.split("-", 1)[1])
        except Exception:
            suffix = 999999
    return (base, suffix, s)

def get_focus(rep: Dict[str, Any]) -> Dict[str, Any]:
    focus = rep.get("focus") or {}
    return focus if isinstance(focus, dict) else {}


def ui_context(focus: Dict[str, Any]) -> Dict[str, Any]:
    ui = focus.get("ui_context") or {}
    return ui if isinstance(ui, dict) else {}


def focus_title(focus: Dict[str, Any]) -> str:
    ui = ui_context(focus)
    for key in ("page_name", "block_title", "screen_title", "menu_title", "active_tab", "human_label"):
        val = clean_text(focus.get(key) or ui.get(key), 100)
        if val:
            return val
    return ""


def focus_item(focus: Dict[str, Any]) -> str:
    ui = ui_context(focus)
    for key in ("focused_item", "label_text", "focus_text"):
        val = clean_text(focus.get(key) or ui.get(key), 100)
        if val:
            return val
    return ""


def node_label(node: Dict[str, Any]) -> str:
    rep = node.get("representative", {})
    focus = get_focus(rep)
    title = focus_title(focus)
    item = focus_item(focus)
    if title and item and item.lower() not in title.lower():
        return f"{title} → {item}"[:160]
    if title:
        return title[:160]
    return clean_text(node.get("label") or rep.get("ocr_text") or node.get("state_id"), 160)


def classify_quality(node: Dict[str, Any]) -> Tuple[str, List[str]]:
    rep = node.get("representative", {})
    focus = get_focus(rep)
    ocr_text = clean_text(rep.get("ocr_text"), 400)
    title = focus_title(focus)
    item = focus_item(focus)
    reasons: List[str] = []
    score = 100
    if not focus.get("found"):
        score -= 35
        reasons.append("no focus")
    if safe_float(focus.get("confidence"), 0) < 0.45 and focus.get("found"):
        score -= 25
        reasons.append("low focus confidence")
    if not title:
        score -= 20
        reasons.append("missing page/menu title")
    if not item:
        score -= 10
        reasons.append("weak focused item")
    if len(ocr_text) < 8:
        score -= 15
        reasons.append("little OCR text")
    soup_hits = len(OCR_SOUP.findall(ocr_text[:800]))
    if soup_hits > 18:
        score -= 10
        reasons.append("OCR noise")
    if score >= 75:
        return "good", reasons
    if score >= 45:
        return "questionable", reasons
    return "bad", reasons


@dataclass
class DashboardDataset:
    crawler_dir: Path
    graph: Dict[str, Any]
    brain: Dict[str, Any]
    sequences: Dict[str, Any]
    unreachable: Dict[str, Any]
    channel_surf: Dict[str, Any]
    sysdiag: List[Dict[str, Any]]
    ppv_log: Dict[str, Any]
    ppv_limits: Dict[str, Any]

    @classmethod
    def load(cls, crawler_dir: Path) -> "DashboardDataset":
        crawler_dir = Path(crawler_dir)
        return cls(
            crawler_dir=crawler_dir,
            graph=read_json(crawler_dir / "nav_graph.json", {}),
            brain=read_json(crawler_dir / "crawler_brain.json", {}),
            sequences=read_json(crawler_dir / "learned_sequences.json", {}),
            unreachable=read_json(crawler_dir / "unreachable_states.json", {}),
            channel_surf=read_json(crawler_dir / "channel_surf_log.json", {}),
            sysdiag=read_json(crawler_dir / "sysdiag_bootstrap_history.json", []),
            ppv_log=read_json(crawler_dir / "ppv_purchase_test_log.json", {}),
            ppv_limits=read_json(crawler_dir / "ppv_purchase_limits.json", {}),
        )

    @property
    def nodes(self) -> Dict[str, Dict[str, Any]]:
        return self.graph.get("nodes", {}) if isinstance(self.graph.get("nodes", {}), dict) else {}

    @property
    def edges(self) -> Dict[str, Dict[str, Any]]:
        return self.graph.get("edges", {}) if isinstance(self.graph.get("edges", {}), dict) else {}

    @property
    def action_rewards(self) -> Dict[str, Dict[str, Any]]:
        return self.brain.get("action_rewards", {}) if isinstance(self.brain.get("action_rewards", {}), dict) else {}

    @property
    def action_timing(self) -> Dict[str, Dict[str, Any]]:
        return self.brain.get("action_timing", {}) if isinstance(self.brain.get("action_timing", {}), dict) else {}

    @property
    def state_actions(self) -> Dict[str, Dict[str, Any]]:
        return self.brain.get("state_actions", {}) if isinstance(self.brain.get("state_actions", {}), dict) else {}

    @property
    def channel_observations(self) -> List[Dict[str, Any]]:
        if isinstance(self.channel_surf, dict):
            return list(self.channel_surf.get("observations") or [])
        if isinstance(self.channel_surf, list):
            return list(self.channel_surf)
        return []

    @property
    def sysdiag_rows(self) -> List[Dict[str, Any]]:
        return list(self.sysdiag) if isinstance(self.sysdiag, list) else []

    def node_rows(self) -> List[Dict[str, Any]]:
        rows = []
        for sid, node in self.nodes.items():
            rep = node.get("representative", {})
            focus = get_focus(rep)
            ui = ui_context(focus)
            human = focus.get("human_cues") if isinstance(focus.get("human_cues"), dict) else {}
            quality, reasons = classify_quality(node)
            text = clean_text(rep.get("ocr_text"), 500)
            risk = bool(RISK_WORDS.search(text) or RISK_WORDS.search(json.dumps(focus)[:1500]) or human.get("risk_flags"))
            rows.append({
                "state_id": sid,
                "label": node_label(node),
                "first_seen": node.get("first_seen") or rep.get("timestamp"),
                "last_seen": node.get("last_seen") or rep.get("timestamp"),
                "first_bucket": iso_bucket(node.get("first_seen") or rep.get("timestamp")),
                "observation_count": int(node.get("observation_count", 0) or 0),
                "page_name": clean_text(focus.get("page_name") or ui.get("page_name"), 100),
                "block_title": clean_text(focus.get("block_title") or ui.get("block_title"), 100),
                "screen_title": clean_text(focus.get("screen_title") or ui.get("screen_title"), 100),
                "focused_item": focus_item(focus),
                "focused_value": clean_text(focus.get("focused_value") or ui.get("focused_value"), 100),
                "focus_found": bool(focus.get("found")),
                "focus_confidence": round(safe_float(focus.get("confidence"), 0), 4),
                "context_confidence": round(safe_float(focus.get("context_confidence") or ui.get("context_confidence"), 0), 4),
                "quality": quality,
                "quality_reasons": ", ".join(reasons),
                "risk_flag": risk,
                "human_screen_kind": human.get("screen_kind") or "",
                "human_confidence": round(safe_float(human.get("confidence"), 0), 4) if human else 0.0,
                "human_feature_tags": ", ".join(human.get("feature_tags", [])[:12]) if human else "",
                "human_test_goals": ", ".join(g.get("goal", "") for g in human.get("test_goals", [])[:6]) if human else "",
                "human_annoyance_flags": ", ".join(human.get("annoyance_flags", [])[:12]) if human else "",
                "ui_pattern": rep.get("ui_pattern") or "unknown",
                "pattern_confidence": round(safe_float(rep.get("pattern_confidence"), 0), 4),
                "brightness": safe_float(rep.get("brightness"), 0),
                "variance": safe_float(rep.get("variance"), 0),
                "entropy": safe_float(rep.get("entropy"), 0),
                "edge_density": safe_float(rep.get("edge_density"), 0),
                "ocr_token_count": len(rep.get("ocr_tokens") or []),
                "screenshot": rep.get("screenshot") or "",
            })
        return rows

    def edge_rows(self) -> List[Dict[str, Any]]:
        labels = {sid: node_label(n) for sid, n in self.nodes.items()}
        rows = []
        for eid, edge in self.edges.items():
            attempts = int(edge.get("attempts", 0) or 0)
            successes = int(edge.get("successes", 0) or 0)
            rows.append({
                "edge_id": eid,
                "from_state": edge.get("from_state", ""),
                "from_label": labels.get(edge.get("from_state", ""), edge.get("from_state", "")),
                "action": edge.get("action", ""),
                "to_state": edge.get("to_state", ""),
                "to_label": labels.get(edge.get("to_state", ""), edge.get("to_state", "")),
                "attempts": attempts,
                "successes": successes,
                "failures": int(edge.get("failures", 0) or 0),
                "noops": int(edge.get("noops", 0) or 0),
                "success_rate": round(successes / attempts, 4) if attempts else 0,
                "confidence": round(safe_float(edge.get("confidence"), 0), 4),
                "last_seen": edge.get("last_seen", ""),
                "last_bucket": iso_bucket(edge.get("last_seen")),
                "sample_count": len(edge.get("samples") or []),
                "transition_type": "self_loop" if edge.get("from_state") == edge.get("to_state") else "transition",
            })
        return rows

    def action_rows(self) -> List[Dict[str, Any]]:
        actions = sorted(set(self.action_rewards.keys()) | set(self.action_timing.keys()))
        rows = []
        for action in actions:
            r = self.action_rewards.get(action, {})
            t = self.action_timing.get(action, {})
            rows.append({
                "action": action,
                "reward_attempts": int(r.get("attempts", 0) or 0),
                "total_reward": safe_float(r.get("total_reward"), 0),
                "avg_reward": round(safe_float(r.get("avg_reward"), 0), 4),
                "timing_attempts": int(t.get("attempts", 0) or 0),
                # Legacy response fields now represent first visible action start.
                "avg_response_s": round(safe_float(t.get("avg_response_s"), 0), 4),
                "last_response_s": round(safe_float(t.get("last_response_s"), 0), 4),
                "min_response_s": round(safe_float(t.get("min_response_s"), 0), 4),
                "max_response_s": round(safe_float(t.get("max_response_s"), 0), 4),
                "avg_start_s": round(safe_float(t.get("avg_start_s", t.get("avg_response_s")), 0), 4),
                "last_start_s": round(safe_float(t.get("last_start_s", t.get("last_response_s")), 0), 4),
                "avg_complete_s": round(safe_float(t.get("avg_complete_s"), 0), 4),
                "last_complete_s": round(safe_float(t.get("last_complete_s"), 0), 4),
                "max_complete_s": round(safe_float(t.get("max_complete_s"), 0), 4),
                "avg_stable_s": round(safe_float(t.get("avg_stable_s"), 0), 4),
                "remarkable_count": int(t.get("remarkable_count", 0) or 0),
                "last_flags": ",".join(t.get("last_flags", []) if isinstance(t.get("last_flags", []), list) else []),
            })
        return rows

    def coverage_rows(self, actions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        actions = actions or DEFAULT_ACTIONS
        rows = []
        for sid, node in self.nodes.items():
            label = node_label(node)
            for action in actions:
                stat = self.state_actions.get(f"{sid}|{action}", {})
                rows.append({
                    "state_id": sid,
                    "label": label,
                    "action": action,
                    "attempts": int(stat.get("attempts", 0) or 0),
                    "successes": int(stat.get("successes", 0) or 0),
                    "discoveries": int(stat.get("discoveries", 0) or 0),
                    "avg_reward": round(safe_float(stat.get("avg_reward"), 0), 4),
                    "last_to_state": stat.get("last_to_state", ""),
                    "last_seen": stat.get("last_seen", ""),
                    "coverage_state": "tried" if int(stat.get("attempts", 0) or 0) else "untested",
                })
        return rows

    def timeline_rows(self) -> List[Dict[str, Any]]:
        buckets: Dict[str, Dict[str, int]] = defaultdict(lambda: {"new_states": 0, "edge_seen": 0, "observations": 0})
        for row in self.node_rows():
            b = row["first_bucket"]
            buckets[b]["new_states"] += 1
            buckets[b]["observations"] += row["observation_count"]
        for row in self.edge_rows():
            b = row["last_bucket"]
            buckets[b]["edge_seen"] += 1
        out = []
        for b in sorted(buckets):
            if b == "unknown":
                continue
            item = {"bucket": b}
            item.update(buckets[b])
            out.append(item)
        return out

    def known_unknown_rows(self) -> List[Dict[str, Any]]:
        rows = []
        for r in self.coverage_rows():
            if r["coverage_state"] == "untested":
                rows.append({**r, "unknown_type": "untested_state_action", "priority": 0.4 + (0.2 if IMPORTANT_WORDS.search(r["label"]) else 0.0)})
        for row in self.node_rows():
            if row["quality"] != "good":
                rows.append({
                    "state_id": row["state_id"],
                    "label": row["label"],
                    "action": "reprocess_context",
                    "attempts": 0,
                    "successes": 0,
                    "discoveries": 0,
                    "avg_reward": 0,
                    "last_to_state": "",
                    "last_seen": row["last_seen"],
                    "coverage_state": row["quality"],
                    "unknown_type": "questionable_perception",
                    "priority": 0.85 if row["quality"] == "bad" else 0.65,
                })
        unreach = self.unreachable.get("unreachable_states", {}) if isinstance(self.unreachable.get("unreachable_states", {}), dict) else {}
        for sid, u in unreach.items():
            rows.append({
                "state_id": sid,
                "label": clean_text((u.get("context") or {}).get("label") or sid, 160),
                "action": "retry_route",
                "attempts": int(u.get("attempts", 0) or 0),
                "successes": 0,
                "discoveries": 0,
                "avg_reward": 0,
                "last_to_state": "",
                "last_seen": u.get("last_attempt", ""),
                "coverage_state": "unreachable",
                "unknown_type": "route_recovery",
                "priority": safe_float(u.get("priority"), 0.8),
            })
        rows.sort(key=lambda r: (safe_float(r.get("priority"), 0), r.get("unknown_type", "")), reverse=True)
        return rows[:5000]

    def channel_surf_rows(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for idx, obs in enumerate(self.channel_observations):
            live = obs.get("live_health") or {}
            info = obs.get("info_health") or {}
            guide = obs.get("guide_health") or {}
            tctxs = [obs.get("live_time_context") or {}, obs.get("info_time_context") or {}, obs.get("guide_time_context") or {}]
            best_time = next((t for t in tctxs if t.get("found")), {})
            drift_vals = [abs(safe_float(t.get("drift_minutes"), 0)) for t in tctxs if t.get("found") and t.get("drift_minutes") is not None]
            max_drift = max(drift_vals) if drift_vals else 0.0
            flags = list(obs.get("warning_flags") or [])
            best_meta = obs.get("best_metadata") or {}
            live_meta = obs.get("live_metadata") or {}
            info_meta = obs.get("info_metadata") or {}
            guide_meta = obs.get("guide_metadata") or {}
            raw_code = clean_text(obs.get("channel_code_guess") or best_meta.get("channel_code"), 80)
            trusted_code = raw_code if is_plausible_channel_code(raw_code) else ""
            raw_name = clean_text(obs.get("channel_name_guess"), 120)
            trusted_name = raw_name if is_plausible_channel_code(raw_name) else trusted_code
            raw_program_title = clean_text(obs.get("program_title_guess") or best_meta.get("program_title"), 180)
            trusted_program_title = sanitize_program_title(raw_program_title)
            raw_program_guess = clean_text(obs.get("program_guess"), 180)
            trusted_program_guess = ""  # v24: legacy blob-level program_guess is quarantined; trust region metadata only
            if raw_code and not trusted_code:
                flags.append("dashboard_rejected_noisy_channel_code")
            if raw_program_title and not trusted_program_title:
                flags.append("dashboard_rejected_noisy_program_title")
            if raw_program_guess and not trusted_program_guess:
                flags.append("dashboard_rejected_legacy_program_guess")
            if live_meta and not live_meta.get("banner_valid"):
                flags.append("dashboard_live_banner_validation_failed")
            rows.append({
                "idx": idx,
                "ts": obs.get("ts", ""),
                "bucket": iso_bucket(obs.get("ts")),
                "channel": obs.get("channel", ""),
                "requested_channel": obs.get("requested_channel", ""),
                "actual_channel_guess": obs.get("actual_channel_guess", ""),
                "actual_channel_source": obs.get("actual_channel_source", ""),
                "input_method": obs.get("input_method", "direct_digits"),
                "navigation_key": obs.get("navigation_key", ""),
                "previous_channel_guess": obs.get("previous_channel_guess", ""),
                "skipped_channel_detected": bool(obs.get("skipped_channel_detected")),
                "skipped_channel_note": clean_text(obs.get("skipped_channel_note"), 160),
                "ok": bool(obs.get("ok")),
                "tune_start_s": safe_float(obs.get("tune_start_s"), 0),
                "tune_complete_s": safe_float(obs.get("tune_complete_s"), 0),
                "live_signal_class": live.get("signal_class", ""),
                "live_active": bool(live.get("active")),
                "live_banner_valid": bool(live_meta.get("banner_valid")),
                "live_banner_validation_score": safe_float(live_meta.get("banner_validation_score"), 0),
                "live_banner_validation_flags": ",".join(map(str, live_meta.get("banner_validation_flags") or [])),
                "live_banner_program_title": sanitize_program_title(live_meta.get("program_title")),
                "live_banner_program_description": clean_text(live_meta.get("program_description") or live_meta.get("program_subtitle"), 260),
                "live_banner_program_time_range": clean_text(live_meta.get("program_time_range"), 80),
                "live_banner_channel_number": clean_text(live_meta.get("channel_number"), 40),
                "live_banner_channel_code": clean_text(live_meta.get("channel_code"), 80) if is_plausible_channel_code(live_meta.get("channel_code", "")) else "",
                "live_banner_displayed_time": clean_text(live_meta.get("displayed_datetime_text"), 80),
                "live_banner_logo_text": clean_text(live_meta.get("channel_logo_text"), 100),
                "info_signal_class": info.get("signal_class", ""),
                "guide_signal_class": guide.get("signal_class", ""),
                "channel_name_guess": trusted_name,
                "channel_code_guess": trusted_code,
                "program_guess": trusted_program_guess,
                "program_title_guess": trusted_program_title,
                "program_description_guess": clean_text(obs.get("program_description_guess") or best_meta.get("program_description"), 260) if trusted_program_title else "",
                "program_time_range": clean_text(best_meta.get("program_time_range"), 80),
                "best_program_time_range": clean_text(best_meta.get("program_time_range"), 80),
                "guide_channel_guess": obs.get("guide_channel_guess", ""),
                "metadata_screen_type": best_meta.get("screen_type", ""),
                "metadata_confidence": safe_float(best_meta.get("confidence"), 0),
                "metadata_source": best_meta.get("source", ""),
                "live_program_title": sanitize_program_title(live_meta.get("program_title")),
                "info_program_title": sanitize_program_title(info_meta.get("program_title")),
                "guide_program_title": sanitize_program_title(guide_meta.get("program_title")),
                "live_channel_number": live_meta.get("channel_number", ""),
                "info_channel_number": info_meta.get("channel_number", ""),
                "guide_channel_number": guide_meta.get("channel_number", ""),
                "live_channel_code": live_meta.get("channel_code", "") if is_plausible_channel_code(live_meta.get("channel_code", "")) else "",
                "info_channel_code": info_meta.get("channel_code", "") if is_plausible_channel_code(info_meta.get("channel_code", "")) else "",
                "guide_channel_code": guide_meta.get("channel_code", "") if is_plausible_channel_code(guide_meta.get("channel_code", "")) else "",
                "best_displayed_datetime": best_meta.get("displayed_datetime_text", ""),
                "live_displayed_datetime": live_meta.get("displayed_datetime_text", ""),
                "info_displayed_datetime": info_meta.get("displayed_datetime_text", ""),
                "guide_displayed_datetime": guide_meta.get("displayed_datetime_text", ""),
                "ppv_available": bool(obs.get("ppv_available")),
                "ppv_cues": ", ".join(map(str, obs.get("ppv_cues") or [])),
                "warning_flags": ",".join(map(str, flags)),
                "display_time_found": bool(best_time.get("found")),
                "display_time": best_time.get("displayed", ""),
                "display_time_source": best_time.get("source", ""),
                "display_time_drift_minutes": safe_float(best_time.get("drift_minutes"), 0),
                "max_abs_time_drift_minutes": round(max_drift, 3),
                "time_discrepancy_flags": ",".join(map(str, obs.get("time_discrepancy_flags") or [])),
            })
        return rows

    def learned_channel_map(self) -> Dict[str, Dict[str, Any]]:
        """Return learned channel memory keyed by channel number as a string."""
        channels = self.brain.get("channels", {}) if isinstance(self.brain.get("channels", {}), dict) else {}
        out: Dict[str, Dict[str, Any]] = {}
        for key, val in channels.items():
            if not isinstance(val, dict):
                continue
            num = clean_text(val.get("channel") or key, 40)
            if not num:
                continue
            out[str(num)] = val
        return out

    @staticmethod
    def _row_channel_number(row: Dict[str, Any]) -> str:
        for key in (
            "actual_channel_guess", "guide_channel_number", "info_channel_number", "live_channel_number",
            "requested_channel", "channel",
        ):
            val = clean_text(row.get(key), 40)
            if val:
                num = normalize_channel_number(val)
                if num:
                    return num
        return ""

    @staticmethod
    def _row_channel_code(row: Dict[str, Any]) -> str:
        def plausible(val: str) -> bool:
            return is_plausible_channel_code(val)
        for key in ("channel_code_guess", "guide_channel_code", "info_channel_code", "live_channel_code", "channel_name_guess"):
            val = clean_text(row.get(key), 80)
            if plausible(val):
                return val
        return ""

    @staticmethod
    def _row_program_title(row: Dict[str, Any]) -> str:
        for key in ("program_title_guess", "info_program_title", "live_program_title", "guide_program_title"):
            val = sanitize_program_title(row.get(key))
            if val:
                return val
        return ""

    def observed_stb_time_rows(self) -> List[Dict[str, Any]]:
        """All observed receiver-clock/displayed-time reads, not only discrepancies."""
        rows: List[Dict[str, Any]] = []
        for obs in self.channel_observations:
            base_channel = clean_text(obs.get("actual_channel_guess") or obs.get("channel") or obs.get("requested_channel"), 40)
            best_meta = obs.get("best_metadata") or {}
            for surface in ("live", "info", "guide"):
                ctx = obs.get(f"{surface}_time_context") or {}
                meta = obs.get(f"{surface}_metadata") or {}
                displayed = clean_text(ctx.get("displayed") or meta.get("displayed_datetime_text"), 80)
                if not displayed:
                    continue
                drift = ctx.get("drift_minutes")
                flags = list(ctx.get("flags") or [])
                rows.append({
                    "ts": obs.get("ts", ""),
                    "bucket": iso_bucket(obs.get("ts")),
                    "channel": base_channel,
                    "surface": surface,
                    "displayed_time": displayed,
                    "displayed_iso": ctx.get("displayed_iso", ""),
                    "actual_iso": ctx.get("actual_iso", ""),
                    "drift_minutes": safe_float(drift, 0) if drift is not None else "",
                    "severity": ctx.get("severity", ""),
                    "source": ctx.get("source") or meta.get("source") or best_meta.get("source", ""),
                    "confidence": safe_float(ctx.get("confidence"), safe_float(meta.get("confidence"), 0)),
                    "flags": ",".join(map(str, flags)),
                    "program_title": clean_text((meta.get("program_title") or best_meta.get("program_title")), 180),
                    "channel_number": clean_text((meta.get("channel_number") or best_meta.get("channel_number") or base_channel), 40),
                    "channel_code": clean_text((meta.get("channel_code") or best_meta.get("channel_code")), 80),
                })
        rows.sort(key=lambda r: r.get("ts", ""), reverse=True)
        return rows

    def channel_catalog_rows(self) -> List[Dict[str, Any]]:
        """Aggregate latest observed channel facts for Exec/Eng/Superset dashboards."""
        learned = self.learned_channel_map()
        by_channel: Dict[str, Dict[str, Any]] = {}
        name_counts: Dict[str, Counter] = defaultdict(Counter)
        program_counts: Dict[str, Counter] = defaultdict(Counter)
        for row in self.channel_surf_rows():
            ch = self._row_channel_number(row)
            if not ch:
                continue
            rec = by_channel.setdefault(ch, {
                "channel_number": ch,
                "observations": 0,
                "ok_observations": 0,
                "active_video_observations": 0,
                "first_seen": row.get("ts", ""),
                "last_seen": row.get("ts", ""),
                "observed_channel_code": "",
                "observed_channel_name": "",
                "observed_channel_label": ch,
                "learned_channel_name": "",
                "learned_channel_symbols": "",
                "learned_confidence": "",
                "latest_program_title": "",
                "latest_program_description": "",
                "latest_program_time_range": "",
                "latest_displayed_time": "",
                "latest_time_surface": "",
                "latest_time_drift_minutes": "",
                "latest_signal_class": "",
                "latest_input_method": "",
                "latest_tune_complete_s": "",
                "latest_metadata_confidence": "",
                "latest_metadata_source": "",
                "ppv_observations": 0,
                "skipped_channel_transitions": 0,
                "banner_valid_observations": 0,
                "latest_live_banner_valid": "",
                "latest_live_banner_score": "",
                "latest_live_banner_flags": "",
                "latest_live_banner_program_title": "",
                "latest_live_banner_program_description": "",
                "latest_live_banner_program_time_range": "",
                "latest_live_banner_channel_number": "",
                "latest_live_banner_channel_code": "",
                "latest_live_banner_displayed_time": "",
                "latest_live_banner_logo_text": "",
                "warning_flags": "",
                "names_seen": "",
                "programs_seen": "",
            })
            rec["observations"] += 1
            if row.get("ok"):
                rec["ok_observations"] += 1
            if row.get("live_active"):
                rec["active_video_observations"] += 1
            if row.get("ppv_available"):
                rec["ppv_observations"] += 1
            if row.get("skipped_channel_detected"):
                rec["skipped_channel_transitions"] += 1
            if row.get("live_banner_valid"):
                rec["banner_valid_observations"] += 1
            code = self._row_channel_code(row)
            if code:
                name_counts[ch][code] += 1
            title = self._row_program_title(row)
            if title:
                program_counts[ch][title] += 1
            # Use newest observation as the current/latest state.
            prev_dt = parse_ts(rec.get("last_seen"))
            cur_dt = parse_ts(row.get("ts"))
            if not prev_dt or (cur_dt and cur_dt >= prev_dt):
                rec["last_seen"] = row.get("ts", "")
                rec["observed_channel_code"] = code or rec.get("observed_channel_code", "")
                rec["observed_channel_name"] = clean_text(row.get("channel_name_guess") or code, 100)
                rec["latest_program_title"] = title
                rec["latest_program_description"] = clean_text(row.get("program_description_guess"), 260)
                # program_time_range currently comes from metadata but may not be flattened in old rows.
                rec["latest_program_time_range"] = clean_text(row.get("program_time_range") or row.get("best_program_time_range"), 80)
                rec["latest_displayed_time"] = clean_text(row.get("display_time") or row.get("best_displayed_datetime"), 80)
                rec["latest_time_surface"] = clean_text(row.get("display_time_source"), 80)
                rec["latest_time_drift_minutes"] = row.get("display_time_drift_minutes", "")
                rec["latest_signal_class"] = row.get("live_signal_class", "")
                rec["latest_input_method"] = row.get("input_method", "")
                rec["latest_tune_complete_s"] = row.get("tune_complete_s", "")
                rec["latest_metadata_confidence"] = row.get("metadata_confidence", "")
                rec["latest_metadata_source"] = row.get("metadata_source", "")
                rec["latest_live_banner_valid"] = row.get("live_banner_valid", "")
                rec["latest_live_banner_score"] = row.get("live_banner_validation_score", "")
                rec["latest_live_banner_flags"] = row.get("live_banner_validation_flags", "")
                rec["latest_live_banner_program_title"] = row.get("live_banner_program_title", "")
                rec["latest_live_banner_program_description"] = row.get("live_banner_program_description", "")
                rec["latest_live_banner_program_time_range"] = row.get("live_banner_program_time_range", "")
                rec["latest_live_banner_channel_number"] = row.get("live_banner_channel_number", "")
                rec["latest_live_banner_channel_code"] = row.get("live_banner_channel_code", "")
                rec["latest_live_banner_displayed_time"] = row.get("live_banner_displayed_time", "")
                rec["latest_live_banner_logo_text"] = row.get("live_banner_logo_text", "")
                rec["warning_flags"] = row.get("warning_flags", "")
            first_dt = parse_ts(rec.get("first_seen"))
            if (cur_dt and first_dt and cur_dt < first_dt) or (cur_dt and not first_dt):
                rec["first_seen"] = row.get("ts", "")
        for ch, rec in by_channel.items():
            lrn = learned.get(ch, {})
            top_name = name_counts[ch].most_common(1)[0][0] if name_counts[ch] else rec.get("observed_channel_code", "")
            rec["observed_channel_code"] = rec.get("observed_channel_code") or top_name
            rec["observed_channel_name"] = rec.get("observed_channel_name") or top_name
            rec["observed_channel_label"] = (f"{ch} {top_name}" if top_name else ch).strip()
            rec["learned_channel_name"] = clean_text(lrn.get("name_guess") or lrn.get("channel_name") or lrn.get("name"), 120)
            syms = lrn.get("symbols") or []
            rec["learned_channel_symbols"] = ",".join(map(str, syms)) if isinstance(syms, list) else clean_text(syms, 120)
            rec["learned_confidence"] = lrn.get("confidence", "")
            rec["names_seen"] = ", ".join(f"{name} ({cnt})" for name, cnt in name_counts[ch].most_common(5))
            rec["programs_seen"] = ", ".join(f"{name} ({cnt})" for name, cnt in program_counts[ch].most_common(6))
            rec["active_video_pct"] = pct(rec["active_video_observations"], rec["observations"])
            rec["ok_pct"] = pct(rec["ok_observations"], rec["observations"])
            rec["banner_valid_pct"] = pct(rec["banner_valid_observations"], rec["observations"])
        def _sort_key(r: Dict[str, Any]) -> Tuple[int, int, str]:
            return channel_sort_tuple(r.get("channel_number"))
        return sorted(by_channel.values(), key=_sort_key)

    def time_discrepancy_rows(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for obs in self.channel_observations:
            for surface in ("live", "info", "guide"):
                ctx = obs.get(f"{surface}_time_context") or {}
                if not ctx.get("found"):
                    continue
                flags = ctx.get("flags") or []
                if flags or abs(safe_float(ctx.get("drift_minutes"), 0)) > 3.0:
                    rows.append({
                        "ts": obs.get("ts", ""),
                        "bucket": iso_bucket(obs.get("ts")),
                        "channel": obs.get("actual_channel_guess") or obs.get("channel", ""),
                        "surface": surface,
                        "displayed": ctx.get("displayed", ""),
                        "displayed_iso": ctx.get("displayed_iso", ""),
                        "actual_iso": ctx.get("actual_iso", ""),
                        "drift_minutes": safe_float(ctx.get("drift_minutes"), 0),
                        "severity": ctx.get("severity", ""),
                        "source": ctx.get("source", ""),
                        "confidence": safe_float(ctx.get("confidence"), 0),
                        "flags": ",".join(map(str, flags)),
                    })
        rows.sort(key=lambda r: abs(safe_float(r.get("drift_minutes"), 0)), reverse=True)
        return rows

    def ppv_purchase_rows(self) -> List[Dict[str, Any]]:
        raw_events = self.ppv_log.get("events", []) if isinstance(self.ppv_log, dict) else []
        rows: List[Dict[str, Any]] = []
        for ev in raw_events:
            if not isinstance(ev, dict):
                continue
            etype = str(ev.get("type") or "")
            # Operator monitor learning writes before_purchase_flow/purchase_flow.
            # Prefer the post-button purchase_flow for what the viewer actually saw
            # after the command, while purchase_test_run still reports the pre-run
            # screen that authorized the action.
            result = ev.get("purchase_flow") or ev.get("result") or ev.get("analysis") or ev.get("before") or {}
            before_flow = ev.get("before_purchase_flow") or ev.get("before") or {}
            if etype == "purchase_test_run":
                result = ev.get("before") or result
            pricing = result.get("pricing") if isinstance(result, dict) else {}
            if not isinstance(pricing, dict) or pricing.get("amount") is None and not pricing.get("price_text"):
                pricing = extract_purchase_pricing(json.dumps(result, ensure_ascii=False), json.dumps(ev, ensure_ascii=False))
            limits = ev.get("limits") or (ev.get("authorization") or {}).get("limits") or self.ppv_limits or {}
            auth = ev.get("price_authorization") or ev.get("authorization") or {}
            amount = pricing.get("amount")
            if etype == "purchase_recorded" and ev.get("amount") is not None:
                amount = ev.get("amount")
            ctx = result.get("display_time_context") if isinstance(result, dict) and isinstance(result.get("display_time_context"), dict) else {}
            displayed_time = (result.get("displayed_time") if isinstance(result, dict) else "") or ctx.get("displayed", "")
            if displayed_time and not ctx.get("actual_iso"):
                try:
                    ctx = extract_display_clock(str(displayed_time), {}, observed_at=ev.get("ts"))
                except Exception:
                    ctx = ctx or {}
            raw_title = ev.get("title") or (result.get("asset_title") or result.get("title_guess") if isinstance(result, dict) else "")
            title = normalize_od_title(raw_title) or clean_text(raw_title, 180)
            rows.append({
                "ts": ev.get("ts", ""),
                "bucket": iso_bucket(ev.get("ts")),
                "event_type": etype,
                "operator_key": ev.get("key", ""),
                "screen_stage": clean_text(result.get("screen_stage"), 80) if isinstance(result, dict) else "",
                "before_screen_stage": clean_text(before_flow.get("screen_stage"), 80) if isinstance(before_flow, dict) else "",
                "asset_type": clean_text(result.get("asset_type"), 80) if isinstance(result, dict) else "",
                "title": title,
                "displayed_time": clean_text(displayed_time, 80),
                "displayed_iso": clean_text(ctx.get("displayed_iso", ""), 80),
                "actual_iso": clean_text(ctx.get("actual_iso", ""), 80),
                "display_time_drift_minutes": safe_float(ctx.get("drift_minutes"), 0) if ctx.get("drift_minutes") is not None else "",
                "display_time_source": clean_text(ctx.get("source", ""), 80),
                "display_time_confidence": safe_float(ctx.get("confidence"), 0),
                "display_time_flags": ",".join(map(str, ctx.get("flags") or [])),
                "price_amount": safe_float(amount, 0) if amount is not None else "",
                "price_text": clean_text(ev.get("price_text") or pricing.get("price_text"), 40),
                "cost_category": clean_text(pricing.get("category"), 40),
                "pricing_confidence": safe_float(pricing.get("confidence"), 0),
                "individual_limit": limits.get("individual_limit"),
                "individual_limit_label": limits.get("individual_limit_label") or format_limit(limits.get("individual_limit")),
                "session_limit": limits.get("session_limit"),
                "session_limit_label": limits.get("session_limit_label") or format_limit(limits.get("session_limit")),
                "session_spent": limits.get("session_spent", ev.get("session_spent_after", "")),
                "session_remaining": limits.get("session_remaining", ""),
                "allowed": auth.get("allowed", ""),
                "authorization_reason": auth.get("reason", ""),
                "confirm_purchase": ev.get("confirm_purchase", ""),
                "final_confirm": ev.get("final_confirm", ""),
                "armed": result.get("armed", "") if isinstance(result, dict) else "",
                "screenshot": result.get("screenshot", "") if isinstance(result, dict) else "",
                "pricing_flags": ",".join(map(str, pricing.get("flags") or [])) if isinstance(pricing, dict) else "",
            })
        rows.sort(key=lambda r: str(r.get("ts", "")), reverse=True)
        return rows

    def ppv_purchase_summary(self) -> Dict[str, Any]:
        rows = self.ppv_purchase_rows()
        purchased = [r for r in rows if r.get("event_type") == "purchase_recorded"]
        blocked = [r for r in rows if r.get("event_type") == "purchase_blocked_by_limit"]
        paid = [r for r in purchased if safe_float(r.get("price_amount"), 0) > 0]
        free = [r for r in purchased if r.get("price_amount") != "" and safe_float(r.get("price_amount"), 0) == 0]
        total = round(sum(safe_float(r.get("price_amount"), 0) for r in purchased), 2)
        return {
            "events": len(rows),
            "purchase_records": len(purchased),
            "paid_purchase_records": len(paid),
            "free_purchase_records": len(free),
            "blocked_by_limit": len(blocked),
            "session_spend_observed": total,
            "latest_limit_individual": (self.ppv_limits or {}).get("individual_limit"),
            "latest_limit_session": (self.ppv_limits or {}).get("session_limit"),
            "latest_session_spent": (self.ppv_limits or {}).get("session_spent", total),
        }

    def ppv_display_time_rows(self) -> List[Dict[str, Any]]:
        return [
            {
                "ts": r.get("ts", ""),
                "event_type": r.get("event_type", ""),
                "screen_stage": r.get("screen_stage", ""),
                "title": r.get("title", ""),
                "displayed_time": r.get("displayed_time", ""),
                "actual_iso": r.get("actual_iso", ""),
                "drift_minutes": r.get("display_time_drift_minutes", ""),
                "confidence": r.get("display_time_confidence", ""),
                "source": r.get("display_time_source", ""),
                "flags": r.get("display_time_flags", ""),
            }
            for r in self.ppv_purchase_rows()
            if r.get("displayed_time")
        ]

    def ppv_stage_summary(self) -> Dict[str, Any]:
        rows = self.ppv_purchase_rows()
        stages = Counter(clean_text(r.get("screen_stage"), 80) or "unknown" for r in rows)
        prices = Counter(clean_text(r.get("price_text"), 40) for r in rows if r.get("price_text"))
        return {
            "stages": dict(stages),
            "displayed_time_reads": len(self.ppv_display_time_rows()),
            "prices_seen": dict(prices),
        }

    def channel_surf_summary(self) -> Dict[str, Any]:
        rows = self.channel_surf_rows()
        if not rows:
            return {"observations": 0, "ok_pct": 0.0, "active_video_pct": 0.0, "banner_valid_pct": 0.0, "banner_invalid_observations": 0, "time_discrepancies": 0, "skipped_channel_steps": 0, "ppv_observations": 0, "black_screen_count": 0}
        catalog = self.channel_catalog_rows()
        return {
            "observations": len(rows),
            "observed_channels": len(catalog),
            "channels_with_latest_programming": sum(1 for r in catalog if r.get("latest_program_title")),
            "observed_stb_time_reads": len(self.observed_stb_time_rows()),
            "ok_pct": pct(sum(1 for r in rows if r["ok"]), len(rows)),
            "active_video_pct": pct(sum(1 for r in rows if r["live_active"]), len(rows)),
            "banner_valid_pct": pct(sum(1 for r in rows if r.get("live_banner_valid")), len(rows)),
            "banner_invalid_observations": sum(1 for r in rows if not r.get("live_banner_valid")),
            "time_discrepancies": len(self.time_discrepancy_rows()),
            "skipped_channel_steps": sum(1 for r in rows if r["skipped_channel_detected"]),
            "ppv_observations": sum(1 for r in rows if r["ppv_available"]),
            "black_screen_count": sum(1 for r in rows if r["live_signal_class"] == "black_screen"),
            "avg_tune_complete_s": round(sum(r["tune_complete_s"] for r in rows) / max(1, len(rows)), 3),
        }

    def executive(self) -> Dict[str, Any]:
        nodes = self.node_rows()
        edges = self.edge_rows()
        actions = self.action_rows()
        coverage = self.coverage_rows()
        ku = self.known_unknown_rows()
        state_count = len(nodes)
        edge_count = len(edges)
        tried = sum(1 for r in coverage if r["attempts"] > 0)
        total_state_actions = len(coverage)
        good = sum(1 for r in nodes if r["quality"] == "good")
        risky = sum(1 for r in nodes if r["risk_flag"])
        avg_edge_conf = round(sum(r["confidence"] for r in edges) / max(1, edge_count), 4)
        avg_focus_conf = round(sum(r["focus_confidence"] for r in nodes if r["focus_found"]) / max(1, sum(1 for r in nodes if r["focus_found"])), 4)
        channels = self.brain.get("channels", {}) if isinstance(self.brain.get("channels", {}), dict) else {}
        sequences = self.sequences.get("learned_sequences", {}) if isinstance(self.sequences.get("learned_sequences", {}), dict) else {}
        surf_summary = self.channel_surf_summary()
        ppv_summary = self.ppv_purchase_summary()
        ppv_stage_summary = self.ppv_stage_summary()
        maturity = round((0.30 * min(100, pct(tried, total_state_actions)) + 0.22 * pct(good, state_count) + 0.18 * min(100, edge_count / max(1, state_count) * 100) + 0.18 * min(100, len(channels) * 4) + 0.12 * min(100, surf_summary.get("active_video_pct", 0))), 2)
        return {
            "generated_at": now_iso(),
            "schema": "stb_learning_exec_v1",
            "headline": {
                "learning_maturity_pct": maturity,
                "states": state_count,
                "transitions": edge_count,
                "coverage_pct": pct(tried, total_state_actions),
                "perception_quality_pct": pct(good, state_count),
                "avg_transition_confidence": avg_edge_conf,
                "avg_focus_confidence": avg_focus_conf,
                "known_channels": len(channels),
                "known_menu_titles": len(self.brain.get("known_menu_titles", []) or []),
                "known_focus_items": len(self.brain.get("known_focus_items", []) or []),
                "known_unknowns": len(ku),
                "risk_flagged_states": risky,
                "learned_sequences": len(sequences),
                "channel_surf_observations": surf_summary.get("observations", 0),
                "observed_channels": surf_summary.get("observed_channels", 0),
                "channels_with_latest_programming": surf_summary.get("channels_with_latest_programming", 0),
                "observed_stb_time_reads": surf_summary.get("observed_stb_time_reads", 0),
                "channel_surf_ok_pct": surf_summary.get("ok_pct", 0),
                "active_video_pct": surf_summary.get("active_video_pct", 0),
                "live_banner_valid_pct": surf_summary.get("banner_valid_pct", 0),
                "live_banner_invalid_observations": surf_summary.get("banner_invalid_observations", 0),
                "time_discrepancies": surf_summary.get("time_discrepancies", 0),
                "skipped_channel_steps": surf_summary.get("skipped_channel_steps", 0),
                "ppv_observations": surf_summary.get("ppv_observations", 0),
                "black_screen_count": surf_summary.get("black_screen_count", 0),
                "ppv_purchase_events": ppv_summary.get("events", 0),
                "ppv_purchase_records": ppv_summary.get("purchase_records", 0),
                "ppv_paid_purchase_records": ppv_summary.get("paid_purchase_records", 0),
                "ppv_free_purchase_records": ppv_summary.get("free_purchase_records", 0),
                "ppv_blocked_by_limit": ppv_summary.get("blocked_by_limit", 0),
                "ppv_session_spend_observed": ppv_summary.get("session_spend_observed", 0),
                "ppv_display_time_reads": ppv_stage_summary.get("displayed_time_reads", 0),
            },
            "timeline": self.timeline_rows(),
            "top_actions": sorted(actions, key=lambda r: (r["avg_reward"], r["reward_attempts"]), reverse=True)[:12],
            "top_known_menus": Counter([r["page_name"] or r["screen_title"] or r["block_title"] for r in nodes if r["page_name"] or r["screen_title"] or r["block_title"]]).most_common(20),
            "known_unknowns": ku[:30],
            "channels": sorted(({"channel": k, **v} for k, v in channels.items()), key=lambda r: int(r.get("channel", 0)))[:100],
            "channel_catalog": self.channel_catalog_rows(),
            "channel_surf": self.channel_surf_rows()[-120:],
            "observed_stb_times": self.observed_stb_time_rows()[:200],
            "time_discrepancies": self.time_discrepancy_rows()[:80],
            "channel_surf_summary": surf_summary,
            "ppv_purchase_summary": ppv_summary,
            "ppv_stage_summary": ppv_stage_summary,
            "ppv_display_times": self.ppv_display_time_rows()[:200],
            "ppv_purchases": self.ppv_purchase_rows()[:200],
            "narrative": self.exec_narrative(maturity, state_count, edge_count, len(ku), risky) + self.channel_surf_narrative(surf_summary) + self.ppv_purchase_narrative(ppv_summary),
        }

    def exec_narrative(self, maturity: float, states: int, edges: int, unknowns: int, risks: int) -> List[str]:
        lines = []
        if states == 0:
            return ["No crawler learning data has been collected yet."]
        lines.append(f"The agent has mapped {states} distinct UI states and {edges} observed transitions.")
        if maturity >= 70:
            lines.append("Learning maturity is strong; the system is ready for targeted workflow validation and regression-style reruns.")
        elif maturity >= 35:
            lines.append("Learning maturity is improving; the next value is filling state/action gaps and stabilizing perception quality.")
        else:
            lines.append("Learning maturity is early; prioritize teacher-mode demonstrations and focused exploration around settings/guide/DVR flows.")
        if unknowns:
            lines.append(f"There are {unknowns} known-unknown items: untested actions, questionable OCR/focus captures, or retry-worthy routes.")
        if risks:
            lines.append(f"{risks} states are risk-flagged because they mention PIN, parental, purchase, reset, or similar guarded flows.")
        return lines

    def channel_surf_narrative(self, surf_summary: Dict[str, Any]) -> List[str]:
        if not surf_summary.get("observations"):
            return ["Channel Surf has not collected channel observations yet."]
        lines = [f"Channel Surf has collected {surf_summary.get('observations')} observations across {surf_summary.get('observed_channels', 0)} observed channel(s), with {surf_summary.get('active_video_pct')}% active-video confirmation and {surf_summary.get('banner_valid_pct', 0)}% valid live-banner reads."]
        if surf_summary.get("channels_with_latest_programming"):
            lines.append(f"Latest programming is now tracked for {surf_summary.get('channels_with_latest_programming')} observed channel(s), including channel number/code, displayed STB time, and latest program title when available.")
        if surf_summary.get("time_discrepancies"):
            lines.append(f"Displayed-clock checks found {surf_summary.get('time_discrepancies')} time discrepancy candidates for engineering review.")
        if surf_summary.get("skipped_channel_steps"):
            lines.append(f"Channel-up/down stepping discovered {surf_summary.get('skipped_channel_steps')} skipped or jumped channel transitions.")
        if surf_summary.get("ppv_observations"):
            lines.append(f"PPV/purchase cues were observed {surf_summary.get('ppv_observations')} time(s); flows remain observe-only unless supervised.")
        return lines

    def ppv_purchase_narrative(self, ppv_summary: Dict[str, Any]) -> List[str]:
        if not ppv_summary.get("events"):
            return ["PPV / On Demand purchase testing has no recorded events yet."]
        lines = [f"PPV / On Demand lab has {ppv_summary.get('events')} recorded event(s), {ppv_summary.get('purchase_records')} purchase record(s), and ${ppv_summary.get('session_spend_observed', 0):.2f} observed session spend."]
        if ppv_summary.get("blocked_by_limit"):
            lines.append(f"Purchase guardrails blocked {ppv_summary.get('blocked_by_limit')} attempted transaction(s) due to individual/session limits.")
        return lines

    def engineering(self) -> Dict[str, Any]:
        nodes = self.node_rows()
        edges = self.edge_rows()
        actions = self.action_rows()
        coverage = self.coverage_rows()
        qualities = Counter(r["quality"] for r in nodes)
        patterns = Counter(r["ui_pattern"] for r in nodes)
        human_kinds = Counter(r.get("human_screen_kind") or "unknown" for r in nodes)
        per_action_coverage = defaultdict(lambda: {"tried": 0, "total": 0})
        for r in coverage:
            per_action_coverage[r["action"]]["total"] += 1
            if r["attempts"]:
                per_action_coverage[r["action"]]["tried"] += 1
        return {
            "generated_at": now_iso(),
            "schema": "stb_learning_eng_v1",
            "headline": self.executive()["headline"],
            "quality_breakdown": [{"quality": k, "count": v} for k, v in qualities.items()],
            "pattern_breakdown": [{"pattern": k, "count": v} for k, v in patterns.items()],
            "per_action_coverage": [{"action": a, "tried": v["tried"], "total": v["total"], "coverage_pct": pct(v["tried"], v["total"])} for a, v in sorted(per_action_coverage.items())],
            "actions": actions,
            "slow_actions": sorted(actions, key=lambda r: r.get("avg_complete_s") or r.get("avg_response_s") or 0, reverse=True)[:20],
            "remarkable_timing_actions": [a for a in sorted(actions, key=lambda r: r.get("remarkable_count", 0), reverse=True) if a.get("remarkable_count", 0) > 0][:40],
            "edges_low_confidence": [e for e in sorted(edges, key=lambda r: r["confidence"]) if e["confidence"] < 0.45][:80],
            "state_quality": sorted(nodes, key=lambda r: ({"bad": 0, "questionable": 1, "good": 2}.get(r["quality"], 3), -r["observation_count"]))[:200],
            "known_unknowns": self.known_unknown_rows()[:200],
            "timeline": self.timeline_rows(),
            "top_edges": sorted(edges, key=lambda r: (r["successes"], r["confidence"]), reverse=True)[:100],
            "state_table": nodes[:1000],
            "channel_surf_summary": self.channel_surf_summary(),
            "channel_catalog": self.channel_catalog_rows(),
            "channel_surf": self.channel_surf_rows()[-500:],
            "observed_stb_times": self.observed_stb_time_rows()[:500],
            "time_discrepancies": self.time_discrepancy_rows()[:300],
            "sysdiag_bootstrap": self.sysdiag_rows[-100:] if isinstance(self.sysdiag_rows, list) else [],
            "ppv_purchase_summary": self.ppv_purchase_summary(),
            "ppv_stage_summary": self.ppv_stage_summary(),
            "ppv_display_times": self.ppv_display_time_rows()[:500],
            "ppv_purchases": self.ppv_purchase_rows()[:500],
        }

    def superset_tables(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "stb_learning_states": self.node_rows(),
            "stb_learning_edges": self.edge_rows(),
            "stb_learning_actions": self.action_rows(),
            "stb_learning_coverage": self.coverage_rows(),
            "stb_learning_known_unknowns": self.known_unknown_rows(),
            "stb_learning_timeline": self.timeline_rows(),
            "stb_channel_surf": self.channel_surf_rows(),
            "stb_observed_channel_catalog": self.channel_catalog_rows(),
            "stb_observed_stb_times": self.observed_stb_time_rows(),
            "stb_display_time_checks": self.time_discrepancy_rows(),
            "stb_sysdiag_bootstrap": self.sysdiag_rows,
            "stb_ppv_purchases": self.ppv_purchase_rows(),
            "stb_ppv_display_times": self.ppv_display_time_rows(),
        }

    def export_zip_bytes(self) -> bytes:
        tables = self.superset_tables()
        manifest = self.superset_manifest()
        sql = self.superset_sql()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("README_SUPERSET_DASHBOARDS.md", self.superset_readme())
            zf.writestr("superset_manifest.json", json.dumps(manifest, indent=2))
            zf.writestr("superset_sql_views.sql", sql)
            zf.writestr("exec_dashboard_payload.json", json.dumps(self.executive(), indent=2))
            zf.writestr("eng_dashboard_payload.json", json.dumps(self.engineering(), indent=2))
            for name, rows in tables.items():
                zf.writestr(f"datasets/{name}.csv", rows_to_csv(rows))
        return buf.getvalue()

    def superset_manifest(self) -> Dict[str, Any]:
        return {
            "generated_at": now_iso(),
            "dashboards": [
                {
                    "name": "STB Autonomous Learning - Executive",
                    "slug": "stb-autonomous-learning-exec",
                    "audience": "leadership",
                    "datasets": ["stb_learning_timeline", "stb_learning_states", "stb_learning_edges", "stb_learning_known_unknowns", "stb_channel_surf", "stb_observed_channel_catalog", "stb_observed_stb_times", "stb_display_time_checks", "stb_ppv_purchases", "stb_ppv_display_times"],
                    "recommended_charts": [
                        "Big Number: Learning Maturity %",
                        "Big Number: States / Transitions / Coverage",
                        "Line: new states over time",
                        "Bar: top learned menus",
                        "Table: highest-priority known unknowns",
                        "Table: observed channel catalog with latest programming",
                        "Table: observed STB displayed times",
                        "Big Number: Channel Surf observations / active-video %",
                        "Big Number: Live banner valid %",
                        "Table: displayed-clock discrepancies",
                    ],
                },
                {
                    "name": "STB Autonomous Learning - Engineering",
                    "slug": "stb-autonomous-learning-eng",
                    "audience": "engineering",
                    "datasets": list(self.superset_tables().keys()),
                    "recommended_charts": [
                        "Heatmap: state/action coverage",
                        "Table: low-confidence transitions",
                        "Bar: action start vs completion timing by action",
                        "Table: remarkable timing flags",
                        "Bar: reward by action",
                        "Table: questionable OCR/focus states",
                        "Line: exploration history",
                        "Table: channel surf observations",
                        "Table: observed channel catalog / latest programming",
                        "Table: observed STB displayed times by surface",
                        "Table: skipped channel-up/down transitions",
                        "Table: live banner validation failures",
                        "Table: displayed-clock drift by surface",
                    ],
                },
            ],
        }

    def superset_sql(self) -> str:
        return """-- STB Autonomous Learning Superset helper views\n-- Load the exported CSVs into tables named exactly as below, then create these views.\n\nCREATE OR REPLACE VIEW v_stb_exec_learning_summary AS\nSELECT\n  COUNT(*) AS states,\n  SUM(CASE WHEN quality = 'good' THEN 1 ELSE 0 END) AS good_states,\n  SUM(CASE WHEN risk_flag THEN 1 ELSE 0 END) AS risk_states,\n  AVG(focus_confidence) AS avg_focus_confidence,\n  AVG(context_confidence) AS avg_context_confidence\nFROM stb_learning_states;\n\nCREATE OR REPLACE VIEW v_stb_eng_transition_quality AS\nSELECT\n  action,\n  COUNT(*) AS transitions,\n  SUM(attempts) AS attempts,\n  SUM(successes) AS successes,\n  AVG(confidence) AS avg_confidence,\n  AVG(success_rate) AS avg_success_rate\nFROM stb_learning_edges\nGROUP BY action;\n\nCREATE OR REPLACE VIEW v_stb_known_unknown_priority AS\nSELECT *\nFROM stb_learning_known_unknowns\nORDER BY priority DESC, unknown_type;\n\nCREATE OR REPLACE VIEW v_stb_state_action_coverage AS\nSELECT\n  action,\n  COUNT(*) AS total_state_actions,\n  SUM(CASE WHEN attempts > 0 THEN 1 ELSE 0 END) AS tried_state_actions,\n  100.0 * SUM(CASE WHEN attempts > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) AS coverage_pct\nFROM stb_learning_coverage\nGROUP BY action;\n\nCREATE OR REPLACE VIEW v_stb_observed_channel_latest AS\nSELECT\n  channel_number,\n  observed_channel_label,\n  observed_channel_name,\n  learned_channel_name,\n  latest_program_title,\n  latest_program_description,\n  latest_displayed_time,\n  latest_time_drift_minutes,\n  latest_live_banner_valid,\n  latest_live_banner_score,\n  latest_live_banner_program_title,\n  latest_live_banner_channel_number,\n  latest_live_banner_channel_code,\n  latest_live_banner_displayed_time,\n  banner_valid_pct,\n  active_video_pct,\n  ok_pct,\n  observations,\n  last_seen\nFROM stb_observed_channel_catalog;\n\nCREATE OR REPLACE VIEW v_stb_observed_clock_by_surface AS\nSELECT\n  channel_number,\n  channel_code,\n  surface,\n  displayed_time,\n  actual_iso,\n  drift_minutes,\n  severity,\n  confidence,\n  ts\nFROM stb_observed_stb_times;\n"""

    def superset_readme(self) -> str:
        return """# STB Autonomous Learning Dashboards\n\nThis export contains two Superset-oriented dashboard packages:\n\n1. **STB Autonomous Learning - Executive**\n   Leadership-ready summary of progress, confidence, coverage, risk, known channels, and remaining known-unknowns.\n\n2. **STB Autonomous Learning - Engineering**\n   Debug-oriented dashboard for state/action coverage, OCR/focus quality, timing, rewards, low-confidence edges, unreachable routes, and training history.\n\n## Import pattern\n\nLoad each CSV in `datasets/` into Superset as a dataset/table with the same base name.\nThen run `superset_sql_views.sql` if you want convenience views for summary charts.\n\nThe live app also serves built-in dashboard pages:\n\n- `/dashboards`\n- `/dashboard/exec`\n- `/dashboard/eng`\n- `/api/dashboards/exec`\n- `/api/dashboards/eng`\n- `/api/dashboards/superset.zip`\n"""


def rows_to_csv(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return ""
    keys: List[str] = []
    for r in rows:
        for k in r.keys():
            if k not in keys:
                keys.append(k)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=keys, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        clean = {}
        for k in keys:
            v = row.get(k, "")
            if isinstance(v, (list, dict)):
                clean[k] = json.dumps(v, ensure_ascii=False)
            else:
                clean[k] = v
        writer.writerow(clean)
    return buf.getvalue()


def build_dashboard_payload(crawler_dir: Path) -> Dict[str, Any]:
    ds = DashboardDataset.load(crawler_dir)
    return {"generated_at": now_iso(), "exec": ds.executive(), "eng": ds.engineering()}
