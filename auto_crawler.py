#!/usr/bin/env python3
"""Autonomous UI crawler for the merged active-video + JAMboree Lite app.

The crawler learns a set-top-box UI as a directed graph:
    screen state --remote key--> next screen state

It is intentionally dependency-light. The "ML" layer is a practical computer-vision
classifier built from perceptual hashes, color/edge features, entropy, optional OCR,
and adaptive nearest-neighbor matching. If pytesseract is installed and Tesseract is
on PATH, OCR automatically becomes part of the state fingerprint; otherwise the crawler
continues using visual features only.
"""
from __future__ import annotations

import json
import logging
import math
import random
import re
import threading
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional, Tuple

import cv2
import numpy as np

from focus_detector import detect_focus


# Phase A Enhancement: Pattern Recognition
from persistence_tracker import PersistenceTracker, UnreachableState
from sequence_learner import SequenceLearner, LearnedSequence
from pattern_recognition import UIPattern, PatternRecognizer, PatternConfidence

log = logging.getLogger("merged.crawler")

FrameCallback = Callable[[], Optional[np.ndarray]]
StatusCallback = Callable[[], Dict[str, Any]]
SendKeyCallback = Callable[[str], Dict[str, Any]]


DANGEROUS_TEXT = re.compile(
    r"\b(purchase|buy|rent|order|subscribe|unsubscribe|delete|erase|factory|reset|format|"
    r"payment|pin|password|adult|parental|cancel service|confirm purchase|record series)\b",
    re.IGNORECASE,
)


@dataclass
class CrawlerConfig:
    enabled_keys: List[str] = field(
        default_factory=lambda: ["up", "down", "left", "right", "guide", "back", "home", "info", "select"]
    )
    reset_key: str = "home"
    reverse_key: str = "back"
    start_sequence: List[str] = field(default_factory=list)
    settle_s: float = 1.15
    reset_settle_s: float = 1.8
    between_key_s: float = 0.35
    max_steps: int = 250
    max_states: int = 80
    max_depth: int = 7
    state_similarity_threshold: float = 0.86
    changed_similarity_threshold: float = 0.94
    min_active_required: bool = True
    allow_select_on_dangerous_text: bool = False
    save_screenshots: bool = True
    ocr_enabled: bool = True
    ocr_every_n_observations: int = 1
    home_first: bool = True
    replay_retries: int = 2

    # Rewarded exploration / learning controls
    self_explore_enabled: bool = True
    reward_new_state: float = 10.0
    reward_new_menu: float = 5.0
    reward_new_setting: float = 8.0
    reward_new_feature: float = 6.0
    reward_new_text_tokens: float = 0.25
    penalty_noop: float = -1.0
    penalty_inactive: float = -6.0
    penalty_blocked: float = -3.0

    # Adaptive timing controls
    adaptive_timing_enabled: bool = True
    min_settle_s: float = 0.35
    max_settle_s: float = 3.5
    timing_poll_s: float = 0.18
    stable_similarity_threshold: float = 0.985
    stable_observations_required: int = 2

    # Channel learning controls
    channel_learning_enabled: bool = False
    channel_scan_list: List[int] = field(default_factory=list)
    channel_digit_gap_s: float = 0.075
    channel_tune_settle_s: float = 2.2
    channel_suffix_key: str = "select"

    # Continuous deep-exploration controls. Set max_steps=0 to run until stopped.
    continuous_exploration_enabled: bool = False
    continuous_idle_s: float = 2.0
    max_cycles: int = 0  # 0 = unlimited cycles while continuous mode is enabled
    # If the local frontier dries up, keep probing from human-like anchor points
    # instead of letting the run naturally finish. This is the "watch TV like a
    # curious human" mode: go Home, Guide, Live, Back, etc. and re-seed the map.
    reseed_when_idle: bool = True
    idle_reseed_every_cycles: int = 1
    anchor_sequences: List[List[str]] = field(default_factory=lambda: [
        ["back"],
        ["home"],
        ["home", "guide"],
        ["live"],
        ["guide"],
        ["home", "dvr"],
        ["home", "settings"],
        ["info"],
        ["options"],
        ["input"],
    ])
    max_action_attempts_per_state: int = 2
    reward_new_edge: float = 3.0
    reward_leads_to_unexplored: float = 4.0
    penalty_repeat_transition: float = -1.25
    penalty_same_state_loop: float = -2.0
    repeat_reward_floor_for_retry: float = 3.0

    # Human-like exploration enhancements
    curiosity_randomness: float = 0.12
    transition_sample_limit: int = 30
    flow_lane_card_w: int = 280
    flow_lane_card_h: int = 190


@dataclass
class ActionTiming:
    action: str
    attempts: int = 0
    avg_response_s: float = 0.0
    last_response_s: float = 0.0
    min_response_s: float = 999.0
    max_response_s: float = 0.0

    def update(self, response_s: float) -> None:
        response_s = max(0.0, float(response_s))
        self.attempts += 1
        alpha = 0.30 if self.attempts <= 5 else 0.15
        if self.avg_response_s <= 0:
            self.avg_response_s = response_s
        else:
            self.avg_response_s = (1.0 - alpha) * self.avg_response_s + alpha * response_s
        self.last_response_s = response_s
        self.min_response_s = min(self.min_response_s, response_s)
        self.max_response_s = max(self.max_response_s, response_s)


@dataclass
class ActionRewardStats:
    action: str
    attempts: int = 0
    total_reward: float = 0.0
    avg_reward: float = 0.0

    def update(self, reward: float) -> None:
        self.attempts += 1
        self.total_reward += float(reward)
        self.avg_reward = self.total_reward / max(1, self.attempts)


@dataclass
class StateActionStats:
    state_id: str
    action: str
    attempts: int = 0
    successes: int = 0
    noops: int = 0
    failures: int = 0
    discoveries: int = 0
    total_reward: float = 0.0
    avg_reward: float = 0.0
    last_to_state: str = ""
    last_seen: str = ""

    def update(self, to_state: str, reward: float, success: bool, noop: bool, discovery: bool, when: str) -> None:
        self.attempts += 1
        if success:
            self.successes += 1
        else:
            self.failures += 1
        if noop:
            self.noops += 1
        if discovery:
            self.discoveries += 1
        self.total_reward += float(reward)
        self.avg_reward = self.total_reward / max(1, self.attempts)
        self.last_to_state = str(to_state or "")
        self.last_seen = when


@dataclass
class ChannelRecord:
    channel: int
    first_seen: str
    last_seen: str
    observations: int = 0
    state_id: str = ""
    name_guess: str = ""
    symbols: List[str] = field(default_factory=list)
    ocr_texts: List[str] = field(default_factory=list)
    screenshot: Optional[str] = None
    confidence: float = 0.0


@dataclass
class ScreenFingerprint:
    state_id: str
    timestamp: str
    screenshot: Optional[str]
    ahash: str
    dhash: str
    phash: str
    brightness: float
    variance: float
    entropy: float
    edge_density: float
    color_hist: List[float]
    ocr_text: str = ""
    ocr_tokens: List[str] = field(default_factory=list)
    focus: Dict[str, Any] = field(default_factory=dict)
    width: int = 0
    height: int = 0
    # Pattern recognition fields (Phase A Enhancement)
    ui_pattern: str = "unknown"
    pattern_confidence: float = 0.0
    pattern_reasons: List[str] = field(default_factory=list)


@dataclass
class StateNode:
    state_id: str
    first_seen: str
    last_seen: str
    observation_count: int
    representative: ScreenFingerprint
    label: str = ""
    aliases: List[str] = field(default_factory=list)


@dataclass
class TransitionEdge:
    from_state: str
    action: str
    to_state: str
    attempts: int = 0
    successes: int = 0
    noops: int = 0
    failures: int = 0
    confidence: float = 0.0
    reversible_with: Optional[str] = None
    last_seen: str = ""
    samples: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CrawlEvent:
    ts: str
    level: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)


class FeatureExtractor:
    """Visual + optional OCR feature extraction for STB screens."""

    def __init__(self, data_dir: Path, save_screenshots: bool = True, ocr_enabled: bool = True) -> None:
        self.data_dir = Path(data_dir)
        self.states_dir = self.data_dir / "states"
        self.states_dir.mkdir(parents=True, exist_ok=True)
        self.save_screenshots = save_screenshots
        self.ocr_enabled = ocr_enabled
        self._pytesseract = None
        if ocr_enabled:
            try:
                import pytesseract  # type: ignore

                self._pytesseract = pytesseract
            except Exception:
                self._pytesseract = None

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _bits_to_hex(bits: np.ndarray) -> str:
        bits = bits.astype(np.uint8).flatten()
        if bits.size % 4:
            bits = np.pad(bits, (0, 4 - bits.size % 4), constant_values=0)
        out = []
        for i in range(0, bits.size, 4):
            nibble = int(bits[i] << 3 | bits[i + 1] << 2 | bits[i + 2] << 1 | bits[i + 3])
            out.append(format(nibble, "x"))
        return "".join(out)

    @classmethod
    def average_hash(cls, gray: np.ndarray, size: int = 16) -> str:
        small = cv2.resize(gray, (size, size), interpolation=cv2.INTER_AREA)
        return cls._bits_to_hex(small >= float(np.mean(small)))

    @classmethod
    def difference_hash(cls, gray: np.ndarray, size: int = 16) -> str:
        small = cv2.resize(gray, (size + 1, size), interpolation=cv2.INTER_AREA)
        return cls._bits_to_hex(small[:, 1:] > small[:, :-1])

    @classmethod
    def perceptual_hash(cls, gray: np.ndarray, size: int = 32, keep: int = 8) -> str:
        small = cv2.resize(gray, (size, size), interpolation=cv2.INTER_AREA).astype(np.float32)
        dct = cv2.dct(small)
        low = dct[:keep, :keep]
        # Ignore the DC term when computing median so overall brightness does not dominate.
        med = float(np.median(low.flatten()[1:]))
        return cls._bits_to_hex(low >= med)

    @staticmethod
    def color_histogram(frame: np.ndarray) -> List[float]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 4, 4], [0, 180, 0, 256, 0, 256])
        hist = cv2.normalize(hist, hist).flatten().astype(float)
        return [round(float(v), 5) for v in hist.tolist()]

    @staticmethod
    def image_entropy(gray: np.ndarray) -> float:
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        prob = hist / max(1.0, float(hist.sum()))
        prob = prob[prob > 0]
        return float(-np.sum(prob * np.log2(prob)))

    @staticmethod
    def edge_density(gray: np.ndarray) -> float:
        small = cv2.resize(gray, (320, 180), interpolation=cv2.INTER_AREA)
        edges = cv2.Canny(small, 80, 160)
        return float(np.mean(edges > 0))

    @staticmethod
    def tokenize(text: str) -> List[str]:
        words = re.findall(r"[a-zA-Z0-9]{2,}", text.lower())
        stop = {"the", "and", "for", "you", "your", "are", "with", "this", "that"}
        return sorted(set(w for w in words if w not in stop))[:80]

    def ocr(self, frame: np.ndarray) -> str:
        if not self._pytesseract:
            return ""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Upscale and threshold for TV UI text.
            scaled = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
            scaled = cv2.bilateralFilter(scaled, 5, 35, 35)
            text = self._pytesseract.image_to_string(scaled, config="--psm 6")
            return " ".join(text.split())[:1000]
        except Exception as exc:
            log.debug("OCR unavailable/failed: %s", exc)
            return ""

    def extract(self, frame: np.ndarray, hint_id: Optional[str] = None) -> ScreenFingerprint:
        if frame is None or not frame.size:
            raise ValueError("cannot fingerprint empty frame")
        sid = hint_id or f"screen_{uuid.uuid4().hex[:10]}"
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        screenshot = None
        if self.save_screenshots:
            screenshot_path = self.states_dir / f"{sid}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
            cv2.imwrite(str(screenshot_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
            screenshot = str(screenshot_path.relative_to(self.data_dir))
        text = self.ocr(frame)
        focus = detect_focus(frame, self._pytesseract)
        # Merge focus-local OCR into the global OCR context. This makes labels and
        # state matching much clearer when the full screen OCR is noisy.
        focus_text_parts = []
        if isinstance(focus, dict):
            # v9: merge spatial/semantic context, not just the raw focused crop.
            for key in (
                "screen_title", "menu_title", "active_tab", "human_label",
                "focused_item", "focused_value", "label_text", "focus_text",
                "row_text", "context_text", "header_text", "action_bar_text",
            ):
                val = str(focus.get(key) or "").strip()
                if val and val not in focus_text_parts:
                    focus_text_parts.append(val)
            ui = focus.get("ui_context") or {}
            if isinstance(ui, dict):
                for key in ("context_summary", "screen_title", "focused_item", "focused_value", "row_text"):
                    val = str(ui.get(key) or "").strip()
                    if val and val not in focus_text_parts:
                        focus_text_parts.append(val)
                for pair in ui.get("setting_pairs") or []:
                    if isinstance(pair, dict):
                        val = f"{pair.get('label','')} {pair.get('value','')}".strip()
                        if val and val not in focus_text_parts:
                            focus_text_parts.append(val)
            for direction, val in (focus.get("neighbor_text") or {}).items() if isinstance(focus.get("neighbor_text"), dict) else []:
                val = str(val or "").strip()
                if val and val not in focus_text_parts:
                    focus_text_parts.append(val)
        merged_text = " ".join([text] + focus_text_parts).strip()[:2200]
        merged_tokens = sorted(set(self.tokenize(merged_text)) | set(focus.get("tokens", []) if isinstance(focus, dict) else []))[:180]
        return ScreenFingerprint(
            state_id=sid,
            timestamp=self._now(),
            screenshot=screenshot,
            ahash=self.average_hash(gray),
            dhash=self.difference_hash(gray),
            phash=self.perceptual_hash(gray),
            brightness=round(float(np.mean(gray)), 3),
            variance=round(float(np.var(gray)), 3),
            entropy=round(self.image_entropy(gray), 4),
            edge_density=round(self.edge_density(gray), 5),
            color_hist=self.color_histogram(frame),
            ocr_text=merged_text,
            ocr_tokens=merged_tokens,
            focus=focus if isinstance(focus, dict) else {},
            width=int(frame.shape[1]),
            height=int(frame.shape[0]),
        )


class SimilarityModel:
    @staticmethod
    def hamming_hex(a: str, b: str) -> float:
        if not a or not b:
            return 1.0
        n = min(len(a), len(b))
        ai = int(a[:n], 16)
        bi = int(b[:n], 16)
        dist = (ai ^ bi).bit_count()
        return dist / max(1, n * 4)

    @staticmethod
    def cosine(a: Iterable[float], b: Iterable[float]) -> float:
        va = np.array(list(a), dtype=np.float32)
        vb = np.array(list(b), dtype=np.float32)
        if va.size != vb.size or va.size == 0:
            return 0.0
        denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
        if denom <= 1e-9:
            return 0.0
        return max(0.0, min(1.0, float(np.dot(va, vb) / denom)))

    @staticmethod
    def jaccard(a: List[str], b: List[str]) -> float:
        sa, sb = set(a), set(b)
        if not sa and not sb:
            return 0.5
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / max(1, len(sa | sb))

    @classmethod
    def compare(cls, a: ScreenFingerprint, b: ScreenFingerprint) -> Dict[str, float]:
        phash_sim = 1.0 - cls.hamming_hex(a.phash, b.phash)
        dhash_sim = 1.0 - cls.hamming_hex(a.dhash, b.dhash)
        ahash_sim = 1.0 - cls.hamming_hex(a.ahash, b.ahash)
        hist_sim = cls.cosine(a.color_hist, b.color_hist)
        text_sim = cls.jaccard(a.ocr_tokens, b.ocr_tokens)
        fa = a.focus if isinstance(getattr(a, "focus", {}), dict) else {}
        fb = b.focus if isinstance(getattr(b, "focus", {}), dict) else {}
        focus_token_sim = cls.jaccard(list(fa.get("tokens") or []), list(fb.get("tokens") or []))
        if fa.get("found") and fb.get("found") and fa.get("center_norm") and fb.get("center_norm"):
            dax = abs(float(fa["center_norm"][0]) - float(fb["center_norm"][0]))
            day = abs(float(fa["center_norm"][1]) - float(fb["center_norm"][1]))
            focus_pos_sim = 1.0 - min(1.0, (dax + day) / 0.85)
        elif not fa.get("found") and not fb.get("found"):
            focus_pos_sim = 0.55
        else:
            focus_pos_sim = 0.20
        # Same whole-screen image but different focused row/tile is meaningful on STB UIs.
        # Give the focus semantics enough weight to split navigation states.
        focus_sim = 0.62 * focus_token_sim + 0.38 * focus_pos_sim
        bright_sim = 1.0 - min(1.0, abs(a.brightness - b.brightness) / 96.0)
        var_sim = 1.0 - min(1.0, abs(math.sqrt(max(a.variance, 0.0)) - math.sqrt(max(b.variance, 0.0))) / 80.0)
        edge_sim = 1.0 - min(1.0, abs(a.edge_density - b.edge_density) / 0.25)
        metric_sim = (bright_sim + var_sim + edge_sim) / 3.0
        # OCR is useful when available but should not punish the model when absent.
        text_weight = 0.16 if (a.ocr_tokens or b.ocr_tokens) else 0.03
        focus_weight = 0.20 if (fa.get("found") and fb.get("found")) else (0.10 if (fa.get("found") or fb.get("found")) else 0.02)
        visual_weight = max(0.0, 1.0 - text_weight - focus_weight)
        visual = 0.36 * phash_sim + 0.22 * dhash_sim + 0.10 * ahash_sim + 0.22 * hist_sim + 0.10 * metric_sim
        score = visual_weight * visual + text_weight * text_sim + focus_weight * focus_sim
        return {
            "score": round(max(0.0, min(1.0, score)), 5),
            "phash": round(phash_sim, 5),
            "dhash": round(dhash_sim, 5),
            "ahash": round(ahash_sim, 5),
            "hist": round(hist_sim, 5),
            "text": round(text_sim, 5),
            "focus": round(focus_sim, 5),
            "focus_tokens": round(focus_token_sim, 5),
            "focus_position": round(focus_pos_sim, 5),
            "metrics": round(metric_sim, 5),
        }


class NavigationGraph:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.graph_path = self.data_dir / "nav_graph.json"
        self.nodes: Dict[str, StateNode] = {}
        self.edges: Dict[str, TransitionEdge] = {}
        self.root_state: Optional[str] = None
        self.load()
        self.adaptive_thresholds = AdaptiveThresholdModel()  # Phase A Step A5

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def edge_key(from_state: str, action: str, to_state: str) -> str:
        return f"{from_state}|{action}|{to_state}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "jamboree_nav_graph_v2_focus",
            "updated_at": self._now(),
            "root_state": self.root_state,
            "nodes": {sid: asdict(node) for sid, node in self.nodes.items()},
            "edges": {eid: asdict(edge) for eid, edge in self.edges.items()},
        }

    def load(self) -> None:
        if not self.graph_path.is_file():
            return
        try:
            raw = json.loads(self.graph_path.read_text(encoding="utf-8"))
            self.root_state = raw.get("root_state")
            self.nodes = {
                sid: StateNode(
                    state_id=node["state_id"],
                    first_seen=node["first_seen"],
                    last_seen=node["last_seen"],
                    observation_count=int(node.get("observation_count", 1)),
                    representative=ScreenFingerprint(**{k: v for k, v in node["representative"].items() if k in ScreenFingerprint.__dataclass_fields__}),
                    label=node.get("label", ""),
                    aliases=node.get("aliases", []),
                )
                for sid, node in raw.get("nodes", {}).items()
            }
            self.edges = {
                eid: TransitionEdge(**edge) for eid, edge in raw.get("edges", {}).items()
            }
        except Exception:
            log.exception("Unable to load nav graph; starting fresh")
            self.nodes = {}
            self.edges = {}
            self.root_state = None

    def save(self) -> None:
        tmp = self.graph_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(self.graph_path)

    def reset(self) -> None:
        self.nodes = {}
        self.edges = {}
        self.root_state = None
        self.save()

    def find_best(self, fp: ScreenFingerprint) -> Tuple[Optional[str], Dict[str, float]]:
        best_id = None
        best_cmp = {"score": 0.0}
        for sid, node in self.nodes.items():
            cmp = SimilarityModel.compare(fp, node.representative)
            if cmp["score"] > best_cmp["score"]:
                best_id = sid
                best_cmp = cmp
        return best_id, best_cmp

    def upsert_state(self, fp: ScreenFingerprint, threshold: float) -> Tuple[str, bool, Dict[str, float]]:
        best_id, cmp = self.find_best(fp)
        now = self._now()
        if best_id and cmp["score"] >= threshold:
            node = self.nodes[best_id]
            node.last_seen = now
            node.observation_count += 1
            # Keep the original stable representative, but opportunistically enrich text.
            if fp.ocr_text and len(fp.ocr_text) > len(node.representative.ocr_text):
                node.representative.ocr_text = fp.ocr_text
                node.representative.ocr_tokens = fp.ocr_tokens
            if fp.focus and fp.focus.get("found"):
                old_conf = float((node.representative.focus or {}).get("confidence") or 0.0) if isinstance(node.representative.focus, dict) else 0.0
                new_conf = float(fp.focus.get("confidence") or 0.0)
                if new_conf >= old_conf:
                    node.representative.focus = fp.focus
                    focus_label = self.suggest_label(fp)
                    if focus_label and (not node.label or node.label.startswith("brightness=")):
                        node.label = focus_label
            return best_id, False, cmp

        sid = fp.state_id
        suffix = 1
        while sid in self.nodes:
            suffix += 1
            sid = f"{fp.state_id}_{suffix}"
        fp.state_id = sid
        label = self.suggest_label(fp)
        self.nodes[sid] = StateNode(
            state_id=sid,
            first_seen=now,
            last_seen=now,
            observation_count=1,
            representative=fp,
            label=label,
        )
        if self.root_state is None:
            self.root_state = sid
        return sid, True, cmp

    @staticmethod
    def suggest_label(fp: ScreenFingerprint) -> str:
        focus = fp.focus if isinstance(getattr(fp, "focus", {}), dict) else {}
        if focus:
            ui = focus.get("ui_context") or {}
            if isinstance(ui, dict):
                for key in ("human_label", "context_summary"):
                    label = " ".join(str(ui.get(key) or "").split())
                    if label:
                        return label[:110]
            for key in ("human_label", "screen_title", "menu_title"):
                label = " ".join(str(focus.get(key) or "").split())
                if label and key in ("screen_title", "menu_title"):
                    item = " ".join(str(focus.get("focused_item") or "").split())
                    value = " ".join(str(focus.get("focused_value") or "").split())
                    if item:
                        return f"{label} → {item}{(' = ' + value) if value else ''}"[:110]
                if label:
                    return label[:110]
        if focus.get("found"):
            label = " ".join(str(focus.get("label_text") or focus.get("focus_text") or "").split())
            context = " ".join(str(focus.get("context_text") or "").split()[:8])
            region = str(focus.get("region") or "focus")
            if label:
                return f"{region}: {label}"[:90]
            if context:
                return f"{region}: {context}"[:90]
            return f"focus {region} r{focus.get('row_guess')}c{focus.get('col_guess')}"
        text = fp.ocr_text.strip()
        if text:
            short = " ".join(text.split()[:8])
            return short[:100]
        return f"brightness={fp.brightness:.0f} entropy={fp.entropy:.1f}"

    def record_edge(
        self,
        from_state: str,
        action: str,
        to_state: str,
        changed: bool,
        success: bool,
        confidence: float,
        sample: Optional[Dict[str, Any]] = None,
        reversible_with: Optional[str] = None,
    ) -> TransitionEdge:
        eid = self.edge_key(from_state, action, to_state)
        edge = self.edges.get(eid)
        if edge is None:
            edge = TransitionEdge(from_state=from_state, action=action, to_state=to_state)
            self.edges[eid] = edge
        edge.attempts += 1
        if success:
            edge.successes += 1
        else:
            edge.failures += 1
        if not changed:
            edge.noops += 1
        edge.confidence = round((edge.successes + 0.5) / (edge.attempts + 1.0) * float(confidence), 5)
        edge.last_seen = self._now()
        if reversible_with:
            edge.reversible_with = reversible_with
        if sample:
            edge.samples.append(sample)
            edge.samples = edge.samples[-30:]
        return edge

    def shortest_path(self, start: str, target: str) -> Optional[List[str]]:
        if start == target:
            return []
        q: Deque[Tuple[str, List[str]]] = deque([(start, [])])
        seen = {start}
        while q:
            sid, path = q.popleft()
            for edge in self.edges.values():
                if edge.from_state != sid or edge.to_state in seen:
                    continue
                if edge.successes <= 0 or edge.confidence < 0.2:
                    continue
                new_path = path + [edge.action]
                if edge.to_state == target:
                    return new_path
                seen.add(edge.to_state)
                q.append((edge.to_state, new_path))
        return None


    def outgoing_edges(self, state_id: str, min_confidence: float = 0.15) -> List[TransitionEdge]:
        edges = [e for e in self.edges.values() if e.from_state == state_id and e.successes > 0 and e.confidence >= min_confidence]
        return sorted(edges, key=lambda e: (e.confidence, e.successes, -e.failures), reverse=True)

    def incoming_edges(self, state_id: str) -> List[TransitionEdge]:
        edges = [e for e in self.edges.values() if e.to_state == state_id]
        return sorted(edges, key=lambda e: (e.confidence, e.successes, -e.failures), reverse=True)

    def shortest_route(self, start: str, target: str, min_confidence: float = 0.15) -> Optional[List[TransitionEdge]]:
        """Return the best known action route as edge objects.

        This is BFS by hop count, but edges leaving each node are ordered by confidence
        so equal-length routes prefer more reliable paths.
        """
        if start == target:
            return []
        if start not in self.nodes or target not in self.nodes:
            return None
        q: Deque[Tuple[str, List[TransitionEdge]]] = deque([(start, [])])
        seen = {start}
        while q:
            sid, route = q.popleft()
            for edge in self.outgoing_edges(sid, min_confidence=min_confidence):
                if edge.to_state in seen:
                    continue
                new_route = route + [edge]
                if edge.to_state == target:
                    return new_route
                seen.add(edge.to_state)
                q.append((edge.to_state, new_route))
        return None

    @staticmethod
    def route_confidence(route: Optional[List[TransitionEdge]]) -> float:
        if route is None:
            return 0.0
        if not route:
            return 1.0
        conf = 1.0
        for edge in route:
            conf *= max(0.01, min(1.0, float(edge.confidence)))
        # Product punishes long routes heavily. Blend with minimum edge confidence so
        # operators see both accumulated and weakest-link confidence in one stable score.
        weakest = min(max(0.01, min(1.0, float(e.confidence))) for e in route)
        return round((0.65 * conf) + (0.35 * weakest), 5)

    def depths_from_root(self) -> Dict[str, int]:
        if not self.root_state or self.root_state not in self.nodes:
            return {}
        depths = {self.root_state: 0}
        q: Deque[str] = deque([self.root_state])
        while q:
            sid = q.popleft()
            for edge in self.outgoing_edges(sid, min_confidence=0.05):
                if edge.to_state not in depths:
                    depths[edge.to_state] = depths[sid] + 1
                    q.append(edge.to_state)
        return depths


class CrawlerBrain:
    """Small persistent learner for rewards, action timing, concepts, and channels."""

    MENU_TEXT = re.compile(r"\b(menu|guide|home|apps|dvr|search|on demand|library|browse|sports|movies)\b", re.I)
    SETTINGS_TEXT = re.compile(
        r"\b(settings|preferences|options|setup|system|diagnostics|network|display|audio|caption|"
        r"accessibility|remote|bluetooth|parental|favorites|language|device|about)\b",
        re.I,
    )
    FEATURE_TEXT = re.compile(
        r"\b(record|recording|series|restart|watch|resume|info|details|filter|sort|hd|4k|cc|sap|"
        r"favorite|lock|unlock|profile|apps|netflix|youtube|prime|hulu|max|disney)\b",
        re.I,
    )
    CALLSIGN_TEXT = re.compile(r"\b[A-Z]{2,8}(?:-[A-Z0-9]{1,4})?\b")

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / "crawler_brain.json"
        self.action_timing: Dict[str, ActionTiming] = {}
        self.action_rewards: Dict[str, ActionRewardStats] = {}
        self.state_actions: Dict[str, StateActionStats] = {}
        self.known_tokens: set[str] = set()
        self.known_concepts: set[str] = set()
        self.known_menu_titles: set[str] = set()
        self.known_focus_items: set[str] = set()
        self.known_setting_pairs: set[str] = set()
        self.channels: Dict[str, ChannelRecord] = {}
        self.load()

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def load(self) -> None:
        if not self.path.is_file():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.action_timing = {
                k: ActionTiming(**v) for k, v in raw.get("action_timing", {}).items()
            }
            self.action_rewards = {
                k: ActionRewardStats(**v) for k, v in raw.get("action_rewards", {}).items()
            }
            self.state_actions = {
                k: StateActionStats(**v) for k, v in raw.get("state_actions", {}).items()
            }
            self.known_tokens = set(raw.get("known_tokens", []))
            self.known_concepts = set(raw.get("known_concepts", []))
            self.known_menu_titles = set(raw.get("known_menu_titles", []))
            self.known_focus_items = set(raw.get("known_focus_items", []))
            self.known_setting_pairs = set(raw.get("known_setting_pairs", []))
            self.channels = {
                k: ChannelRecord(**v) for k, v in raw.get("channels", {}).items()
            }
        except Exception:
            log.exception("Unable to load crawler brain; starting fresh")
            self.action_timing = {}
            self.action_rewards = {}
            self.state_actions = {}
            self.known_tokens = set()
            self.known_concepts = set()
            self.known_menu_titles = set()
            self.known_focus_items = set()
            self.known_setting_pairs = set()
            self.channels = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "jamboree_crawler_brain_v6_semantic_context",
            "updated_at": self.now(),
            "action_timing": {k: asdict(v) for k, v in self.action_timing.items()},
            "action_rewards": {k: asdict(v) for k, v in self.action_rewards.items()},
            "state_actions": {k: asdict(v) for k, v in self.state_actions.items()},
            "known_tokens": sorted(self.known_tokens),
            "known_concepts": sorted(self.known_concepts),
            "known_menu_titles": sorted(self.known_menu_titles),
            "known_focus_items": sorted(self.known_focus_items),
            "known_setting_pairs": sorted(self.known_setting_pairs),
            "channels": {k: asdict(v) for k, v in sorted(self.channels.items(), key=lambda kv: int(kv[0]))},
        }

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def reset(self) -> None:
        self.action_timing.clear()
        self.action_rewards.clear()
        self.state_actions.clear()
        self.known_tokens.clear()
        self.known_concepts.clear()
        self.known_menu_titles.clear()
        self.known_focus_items.clear()
        self.known_setting_pairs.clear()
        self.channels.clear()
        self.save()

    def timing_for(self, action: str) -> ActionTiming:
        action = str(action)
        if action not in self.action_timing:
            self.action_timing[action] = ActionTiming(action=action)
        return self.action_timing[action]

    def update_timing(self, action: str, response_s: float) -> None:
        self.timing_for(action).update(response_s)

    def expected_settle_s(self, action: str, cfg: CrawlerConfig) -> float:
        timing = self.timing_for(action)
        if not cfg.adaptive_timing_enabled or timing.avg_response_s <= 0:
            return cfg.settle_s
        return max(cfg.min_settle_s, min(cfg.max_settle_s, timing.avg_response_s * 1.35 + 0.15))

    def reward_stats_for(self, action: str) -> ActionRewardStats:
        action = str(action)
        if action not in self.action_rewards:
            self.action_rewards[action] = ActionRewardStats(action=action)
        return self.action_rewards[action]

    def update_reward(self, action: str, reward: float) -> None:
        self.reward_stats_for(action).update(reward)

    def order_actions(self, actions: Iterable[str]) -> List[str]:
        """Exploit actions with good reward, but preserve some exploration for unknowns."""
        now_weighted = []
        for idx, action in enumerate(actions):
            stats = self.action_rewards.get(action)
            if stats is None or stats.attempts == 0:
                # New actions should be tried early, but maintain configured order.
                score = 3.0 - idx * 0.001
            else:
                exploration_bonus = 1.0 / math.sqrt(stats.attempts + 1.0)
                score = stats.avg_reward + exploration_bonus
            now_weighted.append((score, -idx, action))
        return [a for _, _, a in sorted(now_weighted, reverse=True)]

    @classmethod
    def concepts_from_text(cls, text: str) -> List[str]:
        concepts = []
        low = text.lower()
        for name, rx in [("menu", cls.MENU_TEXT), ("settings", cls.SETTINGS_TEXT), ("feature", cls.FEATURE_TEXT)]:
            if rx.search(low):
                concepts.append(name)
        return concepts

    def score_observation(
        self,
        cfg: CrawlerConfig,
        action: str,
        before_fp: Optional[ScreenFingerprint],
        after_fp: Optional[ScreenFingerprint],
        created: bool,
        changed: bool,
        inactive: bool = False,
        blocked: bool = False,
    ) -> Tuple[float, Dict[str, Any]]:
        if inactive:
            return cfg.penalty_inactive, {"inactive": True}
        if blocked:
            return cfg.penalty_blocked, {"blocked": True}
        reward = 0.0
        details: Dict[str, Any] = {}
        if not changed:
            reward += cfg.penalty_noop
            details["noop"] = cfg.penalty_noop
        if created:
            reward += cfg.reward_new_state
            details["new_state"] = cfg.reward_new_state
        if after_fp:
            text = after_fp.ocr_text or ""
            focus = after_fp.focus if isinstance(getattr(after_fp, "focus", {}), dict) else {}
            if focus.get("found"):
                ui = focus.get("ui_context") or {}
                if not isinstance(ui, dict):
                    ui = {}
                details["focus"] = {
                    "confidence": focus.get("confidence"),
                    "context_confidence": focus.get("context_confidence") or ui.get("context_confidence"),
                    "bbox": focus.get("bbox"),
                    "region": focus.get("region"),
                    "screen_title": focus.get("screen_title") or ui.get("screen_title"),
                    "focused_item": focus.get("focused_item") or ui.get("focused_item"),
                    "focused_value": focus.get("focused_value") or ui.get("focused_value"),
                    "human_label": focus.get("human_label") or ui.get("human_label"),
                    "focus_role": focus.get("focus_role") or ui.get("focus_role"),
                    "tokens": focus.get("tokens", [])[:28],
                }
                # v9 semantic rewards: the crawler is now rewarded for learning
                # screen titles, focused choices, and setting/value relationships,
                # not just generic OCR tokens.
                title = str(focus.get("screen_title") or ui.get("screen_title") or focus.get("menu_title") or "").strip()
                item = str(focus.get("focused_item") or ui.get("focused_item") or "").strip()
                value = str(focus.get("focused_value") or ui.get("focused_value") or "").strip()
                if title and title not in self.known_menu_titles:
                    reward += 4.0
                    details["new_screen_title"] = title
                    details["new_title_reward"] = 4.0
                    self.known_menu_titles.add(title)
                if item:
                    item_key = f"{title}::{item}" if title else item
                    if item_key not in self.known_focus_items:
                        reward += 2.5
                        details["new_focused_item"] = item_key[:160]
                        details["new_focus_item_reward"] = 2.5
                        self.known_focus_items.add(item_key)
                pairs = focus.get("setting_pairs") or ui.get("setting_pairs") or []
                learned_pairs = []
                if value and item:
                    pairs = list(pairs) + [{"label": item, "value": value, "source": "focused_item"}]
                for pair in pairs:
                    if not isinstance(pair, dict):
                        continue
                    label = str(pair.get("label") or "").strip()
                    val = str(pair.get("value") or "").strip()
                    if not label or not val:
                        continue
                    pair_key = f"{title}::{label}={val}"
                    if pair_key not in self.known_setting_pairs:
                        self.known_setting_pairs.add(pair_key)
                        learned_pairs.append(pair_key[:180])
                if learned_pairs:
                    pair_reward = min(6.0, 2.0 * len(learned_pairs))
                    reward += pair_reward
                    details["new_setting_pairs"] = learned_pairs[:6]
                    details["new_setting_pair_reward"] = pair_reward
                semantic_tags = focus.get("semantic_tags") or ui.get("semantic_tags") or []
                if semantic_tags:
                    details["semantic_tags"] = semantic_tags[:12]
                risk_flags = focus.get("risk_flags") or ui.get("risk_flags") or []
                if risk_flags:
                    details["risk_flags"] = risk_flags[:12]
            new_tokens = set(after_fp.ocr_tokens) - self.known_tokens
            if new_tokens:
                token_reward = min(5.0, len(new_tokens) * cfg.reward_new_text_tokens)
                reward += token_reward
                details["new_tokens"] = sorted(new_tokens)[:20]
                details["new_token_reward"] = token_reward
                self.known_tokens |= set(after_fp.ocr_tokens)
            concepts = self.concepts_from_text(text)
            for concept in concepts:
                if concept not in self.known_concepts:
                    if concept == "menu":
                        reward += cfg.reward_new_menu
                        details["new_menu_reward"] = cfg.reward_new_menu
                    elif concept == "settings":
                        reward += cfg.reward_new_setting
                        details["new_setting_reward"] = cfg.reward_new_setting
                    elif concept == "feature":
                        reward += cfg.reward_new_feature
                        details["new_feature_reward"] = cfg.reward_new_feature
                    self.known_concepts.add(concept)
            details["concepts"] = concepts
        self.update_reward(action, reward)
        return round(reward, 4), details

    @staticmethod
    def state_action_key(state_id: str, action: str) -> str:
        return f"{state_id}|{action}"

    def state_action_for(self, state_id: str, action: str) -> StateActionStats:
        key = self.state_action_key(state_id, action)
        if key not in self.state_actions:
            self.state_actions[key] = StateActionStats(state_id=state_id, action=str(action))
        return self.state_actions[key]

    def update_state_action(
        self,
        state_id: str,
        action: str,
        to_state: str,
        reward: float,
        success: bool,
        noop: bool,
        discovery: bool,
    ) -> StateActionStats:
        stat = self.state_action_for(state_id, action)
        stat.update(to_state=to_state, reward=reward, success=success, noop=noop, discovery=discovery, when=self.now())
        return stat

    def state_action_attempts(self, state_id: str, action: str) -> int:
        return self.state_actions.get(self.state_action_key(state_id, action), StateActionStats(state_id, str(action))).attempts

    def state_action_avg_reward(self, state_id: str, action: str) -> float:
        return self.state_actions.get(self.state_action_key(state_id, action), StateActionStats(state_id, str(action))).avg_reward

    def coverage_summary(self, state_ids: Iterable[str], actions: Iterable[str], max_attempts_per_state: int) -> Dict[str, Any]:
        states = list(state_ids)
        acts = list(actions)
        total = len(states) * len(acts)
        tried = 0
        saturated = 0
        discoveries = 0
        remaining_by_state: Dict[str, List[str]] = {}
        for sid in states:
            for action in acts:
                stat = self.state_actions.get(self.state_action_key(sid, action))
                attempts = stat.attempts if stat else 0
                if attempts > 0:
                    tried += 1
                if stat and stat.discoveries:
                    discoveries += stat.discoveries
                if attempts >= max(1, int(max_attempts_per_state)):
                    saturated += 1
                else:
                    remaining_by_state.setdefault(sid, []).append(action)
        return {
            "state_count": len(states),
            "action_count": len(acts),
            "total_state_actions": total,
            "tried_state_actions": tried,
            "saturated_state_actions": saturated,
            "remaining_state_actions": max(0, total - saturated),
            "completion_pct": round((saturated / total * 100.0), 2) if total else 100.0,
            "discoveries": discoveries,
            "remaining_by_state": remaining_by_state,
        }

    @staticmethod
    def parse_channel_action(action: str) -> Optional[int]:
        raw = str(action or "").strip().upper()
        for prefix in ("CH_", "CHANNEL:", "CHANNEL_", "CH:"):
            if raw.startswith(prefix) and raw[len(prefix):].isdigit():
                return int(raw[len(prefix):])
        if raw.isdigit() and 2 <= len(raw) <= 4:
            return int(raw)
        return None

    @staticmethod
    def name_guess_from_ocr(channel: int, text: str) -> str:
        clean = " ".join(str(text or "").split())
        if not clean:
            return ""
        # Prefer a short phrase around the channel number; otherwise take the first useful words.
        m = re.search(rf"\b{re.escape(str(channel))}\b(.{{0,80}})", clean)
        snippet = m.group(1).strip(" :-|•") if m else clean
        words = [w for w in re.findall(r"[A-Za-z0-9&+.-]{2,}", snippet) if not w.isdigit()]
        return " ".join(words[:8])[:80]

    @classmethod
    def symbols_from_ocr(cls, text: str) -> List[str]:
        symbols = []
        for sym in cls.CALLSIGN_TEXT.findall(text or ""):
            if sym not in {"HD", "TV", "CC", "SAP", "DVR", "INFO", "GUIDE", "HOME"} and not sym.isdigit():
                symbols.append(sym)
        # Deduplicate preserving order.
        out = []
        for s in symbols:
            if s not in out:
                out.append(s)
        return out[:12]

    def learn_channel(self, channel: int, state_id: str, fp: ScreenFingerprint, confidence: float) -> ChannelRecord:
        key = str(int(channel))
        now = self.now()
        rec = self.channels.get(key)
        if rec is None:
            rec = ChannelRecord(channel=int(channel), first_seen=now, last_seen=now)
            self.channels[key] = rec
        rec.last_seen = now
        rec.observations += 1
        rec.state_id = state_id
        rec.screenshot = fp.screenshot or rec.screenshot
        rec.confidence = max(rec.confidence, round(float(confidence), 4))
        guess = self.name_guess_from_ocr(channel, fp.ocr_text)
        if guess and (not rec.name_guess or len(guess) > len(rec.name_guess)):
            rec.name_guess = guess
        for sym in self.symbols_from_ocr(fp.ocr_text):
            if sym not in rec.symbols:
                rec.symbols.append(sym)
        if fp.ocr_text and fp.ocr_text not in rec.ocr_texts:
            rec.ocr_texts.append(fp.ocr_text[:1000])
            rec.ocr_texts = rec.ocr_texts[-5:]
        return rec

    def channel_summary(self) -> Dict[str, Any]:
        return {k: asdict(v) for k, v in sorted(self.channels.items(), key=lambda kv: int(kv[0]))}


class AutonomousCrawler:
    def __init__(
        self,
        data_dir: Path,
        capture_frame: FrameCallback,
        capture_status: StatusCallback,
        send_key: SendKeyCallback,
        config: Optional[CrawlerConfig] = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.capture_frame = capture_frame
        self.capture_status = capture_status
        self.send_key = send_key
        self.config = config or CrawlerConfig()
        self.extractor = FeatureExtractor(
            self.data_dir,
            save_screenshots=self.config.save_screenshots,
            ocr_enabled=self.config.ocr_enabled,
        )
        self.probe_extractor = FeatureExtractor(self.data_dir, save_screenshots=False, ocr_enabled=False)
        self.graph = NavigationGraph(self.data_dir)
        self.brain = CrawlerBrain(self.data_dir)
        self.pattern_recognizer = PatternRecognizer()  # Phase A
        self.sequence_learner = SequenceLearner(self.data_dir)  # Phase B
        self.persistence_tracker = PersistenceTracker(self.data_dir)  # Phase C
        self.recent_actions: Deque[str] = deque(maxlen=10)  # Phase B
        self.events: Deque[CrawlEvent] = deque(maxlen=300)
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._running = False
        self._run_id: Optional[str] = None
        self._steps = 0
        self._last_state: Optional[str] = None
        self._last_error = ""
        self._last_stop_reason = ""
        self._started_at: Optional[str] = None
        self._finished_at: Optional[str] = None

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def event(self, level: str, message: str, **data: Any) -> None:
        evt = CrawlEvent(ts=self._now(), level=level, message=message, data=data)
        with self._lock:
            self.events.append(evt)
        if level.lower() in {"error", "warning"}:
            log.warning("crawler: %s %s", message, data)
        else:
            log.info("crawler: %s %s", message, data)

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "ok": True,
                "running": self._running,
                "run_id": self._run_id,
                "started_at": self._started_at,
                "finished_at": self._finished_at,
                "steps": self._steps,
                "last_state": self._last_state,
                "last_error": self._last_error,
                "last_stop_reason": self._last_stop_reason,
                "node_count": len(self.graph.nodes),
                "edge_count": len(self.graph.edges),
                "root_state": self.graph.root_state,
                "config": asdict(self.config),
                "ocr_available": bool(self.extractor._pytesseract),
                "graph_file": str(self.graph.graph_path),
                "brain_file": str(self.brain.path),
                "learning": {
                    "known_token_count": len(self.brain.known_tokens),
                    "known_concepts": sorted(self.brain.known_concepts),
                    "known_menu_titles": sorted(getattr(self.brain, "known_menu_titles", set())),
                    "known_focus_items": sorted(getattr(self.brain, "known_focus_items", set())),
                    "known_setting_pairs": sorted(getattr(self.brain, "known_setting_pairs", set())),
                    "action_rewards": {k: asdict(v) for k, v in self.brain.action_rewards.items()},
                    "action_timing": {k: asdict(v) for k, v in self.brain.action_timing.items()},
                    "state_actions": {k: asdict(v) for k, v in self.brain.state_actions.items()},
                    "coverage": self.exploration_coverage(),
                    "channels": self.brain.channel_summary(),
                },
                "recent_events": [asdict(e) for e in list(self.events)[-40:]],
            }


    # ============================================================================
    # PHASE A STEP A4: Adaptive Action Selection
    # Pattern-specific action ordering for efficient exploration
    # ============================================================================
    
    def _prefer_directional(self, actions: List[str]) -> List[str]:
        """
        Prefer directional navigation for grid-based UIs.
        
        Args:
            actions: Available actions
            
        Returns:
            Reordered actions prioritizing directional buttons
        """
        directional = ['up', 'down', 'left', 'right']
        dir_actions = [a for a in actions if a in directional]
        other_actions = [a for a in actions if a not in directional]
        return dir_actions + other_actions
    
    def _prefer_select_and_back(self, actions: List[str]) -> List[str]:
        """
        Prefer select and back for form/menu UIs.
        
        Args:
            actions: Available actions
            
        Returns:
            Reordered actions prioritizing select/back/enter
        """
        priority = ['select', 'enter', 'ok', 'back']
        directional = ['up', 'down', 'left', 'right']
        
        priority_actions = [a for a in actions if a in priority]
        dir_actions = [a for a in actions if a in directional]
        other_actions = [a for a in actions if a not in priority and a not in directional]
        
        # For forms/menus: select/back first, then directional (to navigate), then others
        return priority_actions + dir_actions + other_actions
    
    def _prefer_meta_buttons(self, actions: List[str]) -> List[str]:
        """
        Prefer meta buttons (guide, info, menu) for video players.
        
        Args:
            actions: Available actions
            
        Returns:
            Reordered actions prioritizing overlay/meta buttons
        """
        meta = ['guide', 'info', 'menu', 'options', 'back', 'home']
        playback = ['play', 'pause', 'stop', 'rewind', 'forward']
        directional = ['up', 'down', 'left', 'right']
        
        meta_actions = [a for a in actions if a in meta]
        playback_actions = [a for a in actions if a in playback]
        dir_actions = [a for a in actions if a in directional]
        other_actions = [a for a in actions if a not in meta + playback + directional]
        
        # For video: meta buttons to access overlays, then playback, avoid directional spam
        return meta_actions + playback_actions + other_actions + dir_actions
    
    def _apply_pattern_preference(self, actions: List[str], pattern: str) -> List[str]:
        """
        Apply pattern-specific action ordering.
        
        Args:
            actions: Available actions
            pattern: Detected UI pattern (from UIPattern enum)
            
        Returns:
            Reordered actions based on pattern
        """
        if not actions:
            return actions
        
        if pattern == "grid_menu":
            return self._prefer_directional(actions)
        elif pattern in ["linear_menu", "form"]:
            return self._prefer_select_and_back(actions)
        elif pattern == "video_player":
            return self._prefer_meta_buttons(actions)
        elif pattern == "info_card":
            # Info cards: back to exit, avoid random navigation
            return self._prefer_select_and_back(actions)
        else:
            # Unknown pattern: use default ordering
            return actions



    def choose_action_with_sequences(self, state_id: str, available_actions: List[str]) -> str:
        """
        Choose next action considering learned sequences.
        Phase B enhancement.
        
        Args:
            state_id: Current state
            available_actions: Available actions
            
        Returns:
            Chosen action
        """
        # Phase B: Check for sequence completion opportunity
        if hasattr(self, 'sequence_learner') and hasattr(self, 'recent_actions'):
            suggestion = self.sequence_learner.suggest_next_action(list(self.recent_actions))
            
            if suggestion:
                suggested_action, confidence = suggestion
                
                # Use suggestion if action is available and confidence is high enough
                if suggested_action in available_actions and confidence > 0.25:
                    self.event("info", "Completing learned sequence", 
                              action=suggested_action, confidence=confidence,
                              recent=list(self.recent_actions)[-3:])
                    return suggested_action
        
        # Fall back to pattern-based selection
        if hasattr(self, 'pattern_recognizer') and state_id in self.graph.nodes:
            state_node = self.graph.nodes[state_id]
            state_fp = state_node.representative
            pattern = getattr(state_fp, 'ui_pattern', 'unknown')
            
            if pattern and pattern != 'unknown':
                return self._apply_pattern_preference(available_actions, pattern)[0] if available_actions else "back"
        
        # Random fallback
        return available_actions[0] if available_actions else "back"

    def start(self, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            if self._running:
                return self.status()
            if overrides:
                self.apply_overrides(overrides)
            self.extractor = FeatureExtractor(
                self.data_dir,
                save_screenshots=self.config.save_screenshots,
                ocr_enabled=self.config.ocr_enabled,
            )
            self.probe_extractor = FeatureExtractor(self.data_dir, save_screenshots=False, ocr_enabled=False)
            self._stop.clear()
            self._running = True
            self._run_id = f"crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self._started_at = self._now()
            self._finished_at = None
            self._last_error = ""
            self._last_stop_reason = ""
            self._steps = 0
            self._thread = threading.Thread(target=self._run_safe, name="AutonomousCrawler", daemon=True)
            self._thread.start()
            self.event("info", "crawl started", run_id=self._run_id)
            return self.status()

    def apply_overrides(self, overrides: Dict[str, Any]) -> None:
        allowed = set(CrawlerConfig.__dataclass_fields__.keys())
        list_fields = {"enabled_keys", "start_sequence"}
        int_list_fields = {"channel_scan_list"}
        bool_fields = {
            "allow_select_on_dangerous_text",
            "ocr_enabled",
            "home_first",
            "self_explore_enabled",
            "adaptive_timing_enabled",
            "channel_learning_enabled",
            "min_active_required",
            "continuous_exploration_enabled",
            "reseed_when_idle",
        }
        int_fields = {"max_steps", "max_states", "max_depth", "replay_retries", "stable_observations_required", "max_cycles", "max_action_attempts_per_state", "transition_sample_limit", "flow_lane_card_w", "flow_lane_card_h", "idle_reseed_every_cycles"}
        float_fields = {
            "settle_s", "reset_settle_s", "between_key_s", "state_similarity_threshold",
            "changed_similarity_threshold", "reward_new_state", "reward_new_menu", "reward_new_setting",
            "reward_new_feature", "reward_new_text_tokens", "penalty_noop", "penalty_inactive",
            "penalty_blocked", "min_settle_s", "max_settle_s", "timing_poll_s",
            "stable_similarity_threshold", "channel_digit_gap_s", "channel_tune_settle_s",
            "continuous_idle_s", "reward_new_edge", "reward_leads_to_unexplored",
            "penalty_repeat_transition", "penalty_same_state_loop", "repeat_reward_floor_for_retry",
            "curiosity_randomness",
        }
        for key, value in overrides.items():
            if key not in allowed:
                continue
            if key == "anchor_sequences":
                if isinstance(value, str):
                    groups = [g.strip() for g in re.split(r"[;\n]+", value) if g.strip()]
                    value = [[x.strip() for x in re.split(r"[,\s]+", g) if x.strip()] for g in groups]
                elif isinstance(value, list):
                    norm = []
                    for item in value:
                        if isinstance(item, str):
                            seq = [x.strip() for x in re.split(r"[,\s]+", item) if x.strip()]
                        elif isinstance(item, list):
                            seq = [str(x).strip() for x in item if str(x).strip()]
                        else:
                            seq = []
                        if seq:
                            norm.append(seq)
                    value = norm
            elif key in list_fields and isinstance(value, str):
                value = [x.strip() for x in re.split(r"[,\s]+", value) if x.strip()]
            elif key in int_list_fields and isinstance(value, str):
                value = [int(x) for x in re.findall(r"\d{2,4}", value)]
            elif key in int_list_fields and isinstance(value, list):
                value = [int(x) for x in value if str(x).strip().isdigit()]
            elif key in bool_fields:
                if isinstance(value, str):
                    value = value.strip().lower() in {"1", "true", "yes", "on"}
                else:
                    value = bool(value)
            elif key in int_fields:
                value = int(value)
            elif key in float_fields:
                value = float(value)
            setattr(self.config, key, value)

    def stop(self) -> Dict[str, Any]:
        self._stop.set()
        self.event("info", "stop requested")
        return self.status()

    def reset_graph(self) -> Dict[str, Any]:
        if self._running:
            raise RuntimeError("stop crawler before resetting graph")
        self.graph.reset()
        self.brain.reset()
        self.events.clear()
        self.event("info", "navigation graph and learning brain reset")
        return self.status()

    def classify_current(self) -> Dict[str, Any]:
        fp = self.capture_fingerprint(hint_prefix="probe")
        sid, created, cmp = self.graph.upsert_state(fp, self.config.state_similarity_threshold)
        self.graph.save()
        with self._lock:
            self._last_state = sid
        return {
            "ok": True,
            "state_id": sid,
            "created": created,
            "similarity": cmp,
            "state": asdict(self.graph.nodes[sid]),
        }

    def _run_safe(self) -> None:
        try:
            self.run()
        except Exception as exc:
            log.exception("autonomous crawler failed")
            with self._lock:
                self._last_error = str(exc)
            self.event("error", "crawler failed", error=str(exc))
        finally:
            with self._lock:
                if not self._last_stop_reason and self._stop.is_set():
                    self._last_stop_reason = "stop_requested"
                elif not self._last_stop_reason:
                    self._last_stop_reason = "worker_finished"
                self._running = False
                self._finished_at = self._now()
            self.graph.save()
            self.brain.save()
            self.event("info", "crawl finished", steps=self._steps, states=len(self.graph.nodes), edges=len(self.graph.edges))

    def restore_start_context(self) -> None:
        cfg = self.config
        if cfg.home_first:
            self.safe_send(cfg.reset_key)
            time.sleep(cfg.reset_settle_s)
        if cfg.start_sequence:
            self.event("info", "running configured start sequence", start_sequence=cfg.start_sequence)
            for key in cfg.start_sequence:
                if self._stop.is_set():
                    break
                self.safe_send(key)
                time.sleep(self.brain.expected_settle_s(key, cfg))

    def exploration_coverage(self) -> Dict[str, Any]:
        return self.brain.coverage_summary(
            state_ids=self.graph.nodes.keys(),
            actions=self.config.enabled_keys,
            max_attempts_per_state=self.config.max_action_attempts_per_state,
        )

    def remaining_actions_for_state(self, state_id: str) -> List[str]:
        cfg = self.config
        remaining: List[str] = []
        for action in cfg.enabled_keys:
            attempts = self.brain.state_action_attempts(state_id, action)
            avg_reward = self.brain.state_action_avg_reward(state_id, action)
            # New or under-sampled actions are preferred. A repeatedly useful action
            # may be retried even after saturation because it can be a hallway to new rooms.
            if attempts < max(1, cfg.max_action_attempts_per_state) or avg_reward >= cfg.repeat_reward_floor_for_retry:
                remaining.append(action)
        return remaining

    def build_frontier(self) -> Deque[Tuple[str, int, float]]:
        depths = self.graph.depths_from_root()
        if self.graph.root_state and self.graph.root_state not in depths:
            depths[self.graph.root_state] = 0
        candidates: List[Tuple[float, str, int]] = []
        for sid in self.graph.nodes:
            depth = depths.get(sid, 99)
            if depth > self.config.max_depth:
                continue
            remaining = self.remaining_actions_for_state(sid)
            if not remaining:
                continue
            # Higher score = more unexplored actions, higher state confidence, and
            # shallower reachability. This prevents it from camping in one hallway.
            avg_reward = 0.0
            rewards = [self.brain.state_action_avg_reward(sid, a) for a in remaining]
            if rewards:
                avg_reward = sum(rewards) / len(rewards)
            score = len(remaining) * 2.0 + self.state_confidence(sid) + max(-2.0, min(5.0, avg_reward)) - depth * 0.12
            candidates.append((score, sid, depth))
        candidates.sort(reverse=True)
        return deque((sid, depth, score) for score, sid, depth in candidates)

    def _set_stop_reason(self, reason: str, **data: Any) -> None:
        with self._lock:
            self._last_stop_reason = reason
        if reason:
            self.event("info", "stop reason set", reason=reason, **data)

    def reseed_exploration(self, cycle: int) -> Optional[str]:
        """Keep continuous exploration alive by moving to a fresh human-like anchor.

        A pure graph crawler can exhaust its local frontier or fail to replay into
        disconnected screens. A human would press Back/Home/Guide/Live and look
        around again. This method does exactly that and records the resulting
        screen as a new possible root/frontier seed.
        """
        cfg = self.config
        sequences = [seq for seq in (cfg.anchor_sequences or []) if seq]
        if not sequences:
            sequences = [[cfg.reverse_key], [cfg.reset_key], ["guide"], ["live"], ["info"]]
        seq = sequences[cycle % len(sequences)]
        self.event("info", "continuous reseed", cycle=cycle + 1, sequence=seq)
        for key in seq:
            if self._stop.is_set():
                return None
            self.safe_send(key)
            time.sleep(self.brain.expected_settle_s(key, cfg))
        try:
            sid, created, cmp = self.current_state_id()
            self.graph.root_state = self.graph.root_state or sid
            self.graph.save()
            self.event("info", "reseed classified screen", state=sid, created=created, similarity=cmp)
            return sid
        except Exception as exc:
            self.event("warning", "reseed classify failed", error=str(exc))
            return None

    def run(self) -> None:
        cfg = self.config
        self.restore_start_context()

        root_fp = self.capture_fingerprint(hint_prefix="root")
        root_id, root_created, _ = self.graph.upsert_state(root_fp, cfg.state_similarity_threshold)
        self.graph.root_state = root_id
        self.graph.save()
        self.event("info", "root state ready", state=root_id, created=root_created)

        if cfg.channel_learning_enabled and cfg.channel_scan_list:
            self.scan_channels(root_id)

        cycles = 0
        while not self._stop.is_set():
            if cfg.max_cycles and cycles >= cfg.max_cycles:
                self._set_stop_reason("max_cycles_reached", max_cycles=cfg.max_cycles)
                break
            if cfg.max_steps and self._steps >= cfg.max_steps:
                self._set_stop_reason("max_steps_reached", max_steps=cfg.max_steps)
                break
            if cfg.max_states and len(self.graph.nodes) >= cfg.max_states:
                self._set_stop_reason("max_states_reached", max_states=cfg.max_states)
                break

            frontier = self.build_frontier()
            if not frontier:
                coverage = self.exploration_coverage()
                self.event("info", "known map fully swept for current limits", coverage=coverage)
                if not cfg.continuous_exploration_enabled:
                    self._set_stop_reason("frontier_exhausted_for_current_limits", coverage=coverage)
                    break
                # In continuous mode, do not finish. Keep watching, then actively
                # reseed from human-like anchors so it can crawl out of small loops.
                time.sleep(max(0.25, cfg.continuous_idle_s))
                try:
                    sid, created, cmp = self.current_state_id()
                    if created:
                        self.event("info", "new passive state discovered while idling", state=sid, similarity=cmp)
                except Exception as exc:
                    self.event("warning", "idle passive classify failed", error=str(exc))
                if cfg.reseed_when_idle and (cycles % max(1, cfg.idle_reseed_every_cycles) == 0):
                    self.reseed_exploration(cycles)
                cycles += 1
                continue

            self.event("info", "exploration cycle started", cycle=cycles + 1, frontier=len(frontier), coverage=self.exploration_coverage())
            while frontier and not self._stop.is_set():
                if cfg.max_steps and self._steps >= cfg.max_steps:
                    break
                if cfg.max_states and len(self.graph.nodes) >= cfg.max_states:
                    break
                state_id, depth, _score = frontier.popleft()
                if depth > cfg.max_depth:
                    continue
                remaining_actions = self.remaining_actions_for_state(state_id)
                if not remaining_actions:
                    continue
                if not self.navigate_to_state(state_id):
                    self.event("warning", "unable to restore target state; skipping", state=state_id)
                    continue

                actions = self.brain.order_actions(remaining_actions) if cfg.self_explore_enabled else list(remaining_actions)
                # Human-like curiosity: mostly exploit learned high-reward paths, but occasionally
                # try a lower-ranked under-sampled action so it can escape local menu loops.
                if cfg.self_explore_enabled and len(actions) > 2 and random.random() < max(0.0, min(0.5, cfg.curiosity_randomness)):
                    head, tail = actions[:2], actions[2:]
                    random.shuffle(tail)
                    actions = head + tail
                for action in actions:
                    if self._stop.is_set() or (cfg.max_steps and self._steps >= cfg.max_steps):
                        break
                    # Re-check attempts after navigation; another path may have updated it.
                    attempts = self.brain.state_action_attempts(state_id, action)
                    avg_reward = self.brain.state_action_avg_reward(state_id, action)
                    if attempts >= max(1, cfg.max_action_attempts_per_state) and avg_reward < cfg.repeat_reward_floor_for_retry:
                        continue
                    result = self.try_action(state_id, action)
                    reward = float(result.get("reward", 0.0))
                    to_state = result.get("to_state")
                    # New states, or known states with fresh remaining actions, become next frontier.
                    if to_state and to_state in self.graph.nodes and to_state != state_id:
                        rem = self.remaining_actions_for_state(to_state)
                        if rem and depth + 1 <= cfg.max_depth:
                            frontier.append((to_state, depth + 1, reward))
                    self.graph.save()
                    self.brain.save()
            cycles += 1
            if not cfg.continuous_exploration_enabled:
                self._set_stop_reason("single_pass_complete")
                break
            # In continuous mode, re-seed after each pass. This prevents the
            # worker from looking idle just because the current root was swept.
            if cfg.reseed_when_idle:
                self.reseed_exploration(cycles)
    def scan_channels(self, root_id: str) -> None:
        cfg = self.config
        unique_channels = []
        for ch in cfg.channel_scan_list:
            try:
                ch_int = int(ch)
            except Exception:
                continue
            if ch_int not in unique_channels:
                unique_channels.append(ch_int)
        if not unique_channels:
            return
        self.event("info", "channel learning scan started", channels=unique_channels)
        for ch in unique_channels:
            if self._stop.is_set() or self._steps >= cfg.max_steps:
                break
            if not self.navigate_to_state(root_id):
                self.event("warning", "unable to restore root before channel scan", channel=ch)
            result = self.try_action(root_id, f"CH_{ch}", force_settle_s=cfg.channel_tune_settle_s)
            self.event("info", "channel scan result", channel=ch, result=result)
            # Return to the configured start/root context before the next channel.
            self.restore_start_context()

    def wait_for_good_frame(self, timeout_s: float = 8.0) -> Tuple[np.ndarray, Dict[str, Any]]:
        deadline = time.time() + timeout_s
        last_status: Dict[str, Any] = {}
        while time.time() < deadline:
            frame = self.capture_frame()
            status = self.capture_status()
            last_status = status
            if frame is not None and frame.size:
                if not self.config.min_active_required or status.get("active", False):
                    return frame, status
            time.sleep(0.15)
        raise RuntimeError(f"no active video frame available; last_status={last_status}")

    def capture_fingerprint(self, hint_prefix: str = "screen") -> ScreenFingerprint:
        frame, status = self.wait_for_good_frame()
        hint = f"{hint_prefix}_{uuid.uuid4().hex[:10]}"
        fp = self.extractor.extract(frame, hint_id=hint)
        
        # Phase A: Add pattern detection
        if hasattr(self, 'pattern_recognizer'):
            pattern_result = self.pattern_recognizer.classify_screen(fp, fp.focus)
            fp.ui_pattern = pattern_result.pattern.value
            fp.pattern_confidence = pattern_result.confidence
            fp.pattern_reasons = pattern_result.reasons
            
            # Learn this pattern for future reference
            self.pattern_recognizer.learn_pattern(fp.state_id, pattern_result.pattern)

        # Preserve capture status in the OCR text if there is no OCR, useful for labels/debugging.
        if not fp.ocr_text:
            fp.ocr_text = ""
        return fp

    def safe_send(self, key: str) -> Dict[str, Any]:
        key = str(key).strip()
        self.event("debug", "send key", key=key)
        result = self.send_key(key)
        time.sleep(self.config.between_key_s)

        # Phase B: Record action for sequence learning
        if hasattr(self, 'sequence_learner'):
            self.sequence_learner.record_action(
                from_state=state_id,
                action=action,
                to_state=result.get("to_state", state_id),
                reward=result.get("reward", 0.0),
                time_s=result.get("settle_time", 0.0)
            )
        
        # Phase B: Track recent actions
        if hasattr(self, 'recent_actions'):
            self.recent_actions.append(action)

        return result

    def quick_fingerprint(self, hint_prefix: str = "probe") -> ScreenFingerprint:
        frame, _ = self.wait_for_good_frame(timeout_s=max(1.0, self.config.timing_poll_s * 4))
        return self.probe_extractor.extract(frame, hint_id=f"{hint_prefix}_{uuid.uuid4().hex[:8]}")

    def wait_after_action(
        self,
        action: str,
        before_fp: ScreenFingerprint,
        force_settle_s: Optional[float] = None,
    ) -> Tuple[ScreenFingerprint, float, Dict[str, Any]]:
        cfg = self.config
        if force_settle_s is not None:
            time.sleep(max(cfg.min_settle_s, float(force_settle_s)))
            return self.capture_fingerprint(hint_prefix="after"), float(force_settle_s), {"mode": "forced"}
        if not cfg.adaptive_timing_enabled:
            time.sleep(cfg.settle_s)
            return self.capture_fingerprint(hint_prefix="after"), cfg.settle_s, {"mode": "fixed"}

        expected = self.brain.expected_settle_s(action, cfg)
        deadline = time.time() + max(cfg.max_settle_s, expected)
        earliest = time.time() + max(cfg.min_settle_s, min(expected, cfg.max_settle_s))
        start = time.time()
        first_change_s: Optional[float] = None
        stable_count = 0
        previous: Optional[ScreenFingerprint] = None
        last: Optional[ScreenFingerprint] = None
        debug: Dict[str, Any] = {"mode": "adaptive", "expected_s": round(expected, 3), "samples": []}

        while time.time() < deadline:
            time.sleep(max(0.05, cfg.timing_poll_s))
            try:
                current = self.quick_fingerprint("timing")
            except Exception:
                continue
            last = current
            before_cmp = SimilarityModel.compare(before_fp, current)
            prev_cmp = SimilarityModel.compare(previous, current) if previous else {"score": 0.0}
            debug["samples"].append({
                "t": round(time.time() - start, 3),
                "before": before_cmp["score"],
                "previous": prev_cmp["score"],
            })
            debug["samples"] = debug["samples"][-8:]
            if first_change_s is None and before_cmp["score"] < cfg.changed_similarity_threshold:
                first_change_s = time.time() - start
            if previous and prev_cmp["score"] >= cfg.stable_similarity_threshold:
                stable_count += 1
            else:
                stable_count = 0
            previous = current
            if time.time() >= earliest and stable_count >= cfg.stable_observations_required:
                break

        response_s = first_change_s if first_change_s is not None else max(expected, time.time() - start)
        self.brain.update_timing(action, response_s)
        # Capture a full, saved/OCR fingerprint once the screen is believed stable.
        after_fp = self.capture_fingerprint(hint_prefix="after") if last is not None else self.capture_fingerprint(hint_prefix="after")
        debug["response_s"] = round(response_s, 3)
        debug["stable_count"] = stable_count
        return after_fp, response_s, debug

    def current_state_id(self) -> Tuple[str, bool, Dict[str, float]]:
        fp = self.capture_fingerprint()
        sid, created, cmp = self.graph.upsert_state(fp, self.config.state_similarity_threshold)
        with self._lock:
            self._last_state = sid
        return sid, created, cmp

    def navigate_to_state(self, target_state: str) -> bool:
        cfg = self.config
        if self.graph.root_state is None:
            return False
        for attempt in range(max(1, cfg.replay_retries)):
            self.restore_start_context()
            sid, _, cmp = self.current_state_id()
            if target_state == sid:
                return True
            path = self.graph.shortest_path(sid, target_state) or self.graph.shortest_path(self.graph.root_state, target_state)
            if not path:
                return target_state == self.graph.root_state
            self.event("info", "replaying path", target=target_state, path=path, attempt=attempt + 1)
            for key in path:
                self.safe_send(key)
                time.sleep(self.brain.expected_settle_s(key, cfg))
            sid, _, cmp = self.current_state_id()
            if sid == target_state or cmp.get("score", 0.0) >= cfg.state_similarity_threshold:
                return True
        return False

    def try_action(self, from_state: str, action: str, force_settle_s: Optional[float] = None) -> Dict[str, Any]:
        cfg = self.config
        self._steps += 1

        action_norm = str(action).strip()
        action_lower = action_norm.lower()
        self.event("info", "try action", from_state=from_state, action=action_norm, step=self._steps)

        before_fp = self.capture_fingerprint(hint_prefix="before")
        before_id, _, _ = self.graph.upsert_state(before_fp, cfg.state_similarity_threshold)
        if before_id != from_state:
            # The live UI drifted. Learn from what we see rather than lying to the graph.
            self.event("warning", "state drift before action", expected=from_state, actual=before_id)
            from_state = before_id

        if action_lower == "select" and not cfg.allow_select_on_dangerous_text:
            node = self.graph.nodes.get(from_state)
            text = " ".join([before_fp.ocr_text, node.representative.ocr_text if node else ""])
            if DANGEROUS_TEXT.search(text):
                edge = self.graph.record_edge(from_state, action_norm, from_state, False, False, 0.0, {"blocked": "dangerous_text"})
                reward, reward_details = self.brain.score_observation(cfg, action_norm, before_fp, before_fp, False, False, blocked=True)
                self.brain.save()
                self.event("warning", "blocked select on risky screen", state=from_state, text=text[:160], reward=reward)
                return {
                    "ok": False,
                    "blocked": True,
                    "to_state": from_state,
                    "new_state": False,
                    "reward": reward,
                    "reward_details": reward_details,
                    "edge": asdict(edge),
                }

        send_started = time.time()
        send_result = self.safe_send(action_norm)

        status = self.capture_status()
        if cfg.min_active_required and not status.get("active", False):
            edge = self.graph.record_edge(
                from_state,
                action_norm,
                from_state,
                changed=False,
                success=False,
                confidence=0.0,
                sample={"status": status, "send": send_result},
            )
            reward, reward_details = self.brain.score_observation(
                cfg, action_norm, before_fp, before_fp, created=False, changed=False, inactive=True
            )
            self.event("warning", "action produced inactive video", from_state=from_state, action=action_norm, status=status, reward=reward)
            self.safe_send(cfg.reverse_key)
            self.brain.save()
            return {
                "ok": False,
                "to_state": from_state,
                "new_state": False,
                "reward": reward,
                "reward_details": reward_details,
                "edge": asdict(edge),
            }

        after_fp, response_s, timing_debug = self.wait_after_action(action_norm, before_fp, force_settle_s=force_settle_s)
        after_id, created, cmp_to_known = self.graph.upsert_state(after_fp, cfg.state_similarity_threshold)
        cmp_before_after = SimilarityModel.compare(before_fp, after_fp)
        changed = cmp_before_after["score"] < cfg.changed_similarity_threshold or after_id != from_state
        success = True
        confidence = 1.0 - cmp_before_after["score"] if changed else cmp_before_after["score"]
        if after_id != from_state:
            confidence = max(confidence, cmp_to_known.get("score", 0.5))
        confidence = max(0.05, min(1.0, confidence))

        edge_existed = self.graph.edge_key(from_state, action_norm, after_id) in self.graph.edges
        reward, reward_details = self.brain.score_observation(
            cfg, action_norm, before_fp, after_fp, created=created, changed=changed
        )
        if changed and not edge_existed:
            reward += cfg.reward_new_edge
            reward_details["new_edge_reward"] = cfg.reward_new_edge
        if after_id == from_state:
            reward += cfg.penalty_same_state_loop
            reward_details["same_state_loop_penalty"] = cfg.penalty_same_state_loop
        if changed and edge_existed and not created and not any(k.startswith("new_") for k in reward_details):
            reward += cfg.penalty_repeat_transition
            reward_details["repeat_transition_penalty"] = cfg.penalty_repeat_transition
        if after_id != from_state and self.remaining_actions_for_state(after_id):
            reward += cfg.reward_leads_to_unexplored
            reward_details["leads_to_unexplored_reward"] = cfg.reward_leads_to_unexplored
        channel = self.brain.parse_channel_action(action_norm)
        channel_record = None
        if channel is not None:
            channel_record = self.brain.learn_channel(channel, after_id, after_fp, confidence)
            reward += 2.0
            reward_details["channel_learning"] = {"channel": channel, "name_guess": channel_record.name_guess, "symbols": channel_record.symbols}
            self.brain.update_reward(action_norm, 2.0)

        edge = self.graph.record_edge(
            from_state,
            action_norm,
            after_id,
            changed=changed,
            success=success,
            confidence=confidence,
            reversible_with=cfg.reverse_key if changed else None,
            sample={
                "before_state": from_state,
                "after_state": after_id,
                "button": action_norm,
                "button_sequence": self._action_sequence_for_display(action_norm),
                "before": {
                    "state_id": from_state,
                    "label": self.graph.nodes.get(from_state).label if from_state in self.graph.nodes else from_state,
                    "screenshot": before_fp.screenshot,
                    "image_url": self._node_image_url(from_state),
                    "ocr_text": before_fp.ocr_text,
                    "ocr_tokens": before_fp.ocr_tokens,
                    "focus": before_fp.focus if isinstance(getattr(before_fp, "focus", {}), dict) else {},
                    "focus_label": self.focus_label(before_fp),
                    "phash": before_fp.phash,
                    "brightness": before_fp.brightness,
                    "entropy": before_fp.entropy,
                },
                "after": {
                    "state_id": after_id,
                    "label": self.graph.nodes.get(after_id).label if after_id in self.graph.nodes else after_id,
                    "screenshot": after_fp.screenshot,
                    "image_url": self._node_image_url(after_id),
                    "ocr_text": after_fp.ocr_text,
                    "ocr_tokens": after_fp.ocr_tokens,
                    "focus": after_fp.focus if isinstance(getattr(after_fp, "focus", {}), dict) else {},
                    "focus_label": self.focus_label(after_fp),
                    "phash": after_fp.phash,
                    "brightness": after_fp.brightness,
                    "entropy": after_fp.entropy,
                },
                "ocr_delta": {
                    "new_tokens": sorted(set(after_fp.ocr_tokens) - set(before_fp.ocr_tokens))[:50],
                    "lost_tokens": sorted(set(before_fp.ocr_tokens) - set(after_fp.ocr_tokens))[:50],
                    "before_focus": self.focus_label(before_fp),
                    "after_focus": self.focus_label(after_fp),
                    "focus_changed": self.focus_label(before_fp) != self.focus_label(after_fp),
                },
                "before_after_similarity": cmp_before_after,
                "known_similarity": cmp_to_known,
                "send": send_result,
                "created_state": created,
                "changed": changed,
                "reward": reward,
                "reward_details": reward_details,
                "timing": timing_debug,
                "elapsed_s": round(time.time() - send_started, 3),
                "channel": channel,
                "edge_existed": edge_existed,
            },
        )
        state_action_stat = self.brain.update_state_action(
            state_id=from_state,
            action=action_norm,
            to_state=after_id,
            reward=reward,
            success=success,
            noop=not changed,
            discovery=bool(created or not edge_existed or reward_details.get("new_tokens") or reward_details.get("new_menu_reward") or reward_details.get("new_setting_reward") or reward_details.get("new_feature_reward")),
        )

        self.event(
            "info",
            "edge learned",
            from_state=from_state,
            action=action_norm,
            to_state=after_id,
            changed=changed,
            new_state=created,
            score=cmp_before_after["score"],
            reward=reward,
            response_s=round(response_s, 3),
        )
        self.brain.save()

        # Try to unwind so the next action starts from the same source state. The outer loop
        # can still recover via HOME + replay even if BACK does not return cleanly. For direct
        # channel entry, HOME is usually safer than BACK because channel banners can be transient.
        if changed and action_lower not in {cfg.reverse_key.lower(), cfg.reset_key.lower()}:
            unwind_key = cfg.reset_key if channel is not None else cfg.reverse_key
            self.safe_send(unwind_key)
            time.sleep(self.brain.expected_settle_s(unwind_key, cfg))
            try:
                returned_id, _, _ = self.current_state_id()
                if returned_id == from_state:
                    edge.reversible_with = unwind_key
                else:
                    self.event("debug", "unwind landed elsewhere", expected=from_state, actual=returned_id, key=unwind_key)
            except Exception as exc:
                self.event("warning", "unwind verification failed", error=str(exc))

        return {
            "ok": True,
            "to_state": after_id,
            "new_state": created,
            "changed": changed,
            "reward": reward,
            "reward_details": reward_details,
            "response_s": response_s,
            "timing": timing_debug,
            "channel": asdict(channel_record) if channel_record else None,
            "state_action": asdict(state_action_stat),
            "edge": asdict(edge),
        }

    # ──────────────────────────────────────────────────────────────────────
    # Operator intelligence, confidence, routing, and goal-directed control
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _text_for_node(node: StateNode) -> str:
        fp = node.representative
        return " ".join([node.state_id, node.label or "", fp.ocr_text or "", " ".join(fp.ocr_tokens or [])]).strip()

    @staticmethod
    def _query_tokens(query: str) -> List[str]:
        return FeatureExtractor.tokenize(query or "")

    def state_kind(self, state_id: str) -> str:
        node = self.graph.nodes.get(state_id)
        if not node:
            return "unknown"
        for rec in self.brain.channels.values():
            if rec.state_id == state_id:
                return "channel"
        text = self._text_for_node(node).lower()
        if CrawlerBrain.SETTINGS_TEXT.search(text):
            return "settings"
        if CrawlerBrain.MENU_TEXT.search(text):
            return "menu"
        if CrawlerBrain.FEATURE_TEXT.search(text):
            return "feature"
        return "screen"

    def state_confidence(self, state_id: str) -> float:
        node = self.graph.nodes.get(state_id)
        if not node:
            return 0.0
        obs_conf = min(1.0, float(node.observation_count) / 4.0)
        incoming = self.graph.incoming_edges(state_id)
        edge_conf = max([e.confidence for e in incoming], default=(0.95 if state_id == self.graph.root_state else 0.35))
        text_bonus = 0.08 if node.representative.ocr_tokens else 0.0
        return round(max(0.0, min(1.0, 0.42 * obs_conf + 0.50 * edge_conf + text_bonus)), 4)

    def action_confidence_report(self) -> Dict[str, Any]:
        by_action: Dict[str, Dict[str, Any]] = {}
        for edge in self.graph.edges.values():
            a = edge.action
            row = by_action.setdefault(a, {
                "action": a, "attempts": 0, "successes": 0, "failures": 0, "noops": 0,
                "edge_count": 0, "weighted_confidence_sum": 0.0, "confidence": 0.0,
            })
            row["attempts"] += edge.attempts
            row["successes"] += edge.successes
            row["failures"] += edge.failures
            row["noops"] += edge.noops
            row["edge_count"] += 1
            row["weighted_confidence_sum"] += edge.confidence * max(1, edge.attempts)
        for action, row in by_action.items():
            attempts = max(1, int(row["attempts"]))
            row["confidence"] = round(float(row.pop("weighted_confidence_sum")) / attempts, 4)
            timing = self.brain.action_timing.get(action)
            reward = self.brain.action_rewards.get(action)
            row["avg_response_s"] = round(timing.avg_response_s, 3) if timing else None
            row["last_response_s"] = round(timing.last_response_s, 3) if timing else None
            row["avg_reward"] = round(reward.avg_reward, 3) if reward else None
        return dict(sorted(by_action.items(), key=lambda kv: kv[1].get("confidence", 0), reverse=True))

    def _node_image_url(self, state_id: str) -> Optional[str]:
        node = self.graph.nodes.get(state_id)
        if not node or not node.representative.screenshot:
            return None
        return f"/api/crawl/state/{state_id}/image"

    def _state_summary(self, state_id: str) -> Dict[str, Any]:
        node = self.graph.nodes.get(state_id)
        if not node:
            return {"state_id": state_id, "label": state_id, "missing": True}
        fp = node.representative
        focus = fp.focus if isinstance(getattr(fp, "focus", {}), dict) else {}
        ui = focus.get("ui_context") if isinstance(focus, dict) else {}
        if not isinstance(ui, dict):
            ui = {}
        return {
            "state_id": state_id,
            "label": node.label or state_id,
            "kind": self.state_kind(state_id),
            "confidence": self.state_confidence(state_id),
            "observations": node.observation_count,
            "image_url": self._node_image_url(state_id),
            "screenshot": fp.screenshot,
            "ocr_text": fp.ocr_text,
            "ocr_tokens": fp.ocr_tokens,
            "focus": focus,
            "focus_label": self.focus_label(fp),
            "screen_title": focus.get("screen_title") or ui.get("screen_title") or "",
            "focused_item": focus.get("focused_item") or ui.get("focused_item") or "",
            "focused_value": focus.get("focused_value") or ui.get("focused_value") or "",
            "human_label": focus.get("human_label") or ui.get("human_label") or self.focus_label(fp),
            "focus_role": focus.get("focus_role") or ui.get("focus_role") or "",
            "context_summary": ui.get("context_summary") or "",
            "setting_pairs": focus.get("setting_pairs") or ui.get("setting_pairs") or [],
            "semantic_tags": focus.get("semantic_tags") or ui.get("semantic_tags") or [],
            "risk_flags": focus.get("risk_flags") or ui.get("risk_flags") or [],
            "first_seen": node.first_seen,
            "last_seen": node.last_seen,
        }

    @staticmethod
    def focus_label(fp: ScreenFingerprint) -> str:
        focus = fp.focus if isinstance(getattr(fp, "focus", {}), dict) else {}
        if not focus:
            return ""
        ui = focus.get("ui_context") or {}
        if isinstance(ui, dict):
            for key in ("human_label", "context_summary", "focused_item"):
                label = str(ui.get(key) or "").strip()
                if label:
                    return label[:120]
        for key in ("human_label", "focused_item", "label_text", "focus_text", "screen_title"):
            label = str(focus.get(key) or "").strip()
            if label:
                return label[:120]
        toks = focus.get("tokens") or []
        if toks:
            return " ".join(toks[:10])[:120]
        return str(focus.get("region") or "focus")

    def analyze_focus_current(self) -> Dict[str, Any]:
        frame, status = self.wait_for_good_frame(timeout_s=4.0)
        fp = self.extractor.extract(frame, hint_id=f"focus_{uuid.uuid4().hex[:8]}")
        sid, created, cmp = self.graph.upsert_state(fp, self.config.state_similarity_threshold)
        self.graph.save()
        with self._lock:
            self._last_state = sid
        return {
            "ok": True,
            "state_id": sid,
            "created": created,
            "similarity": cmp,
            "focus": fp.focus,
            "focus_label": self.focus_label(fp),
            "state": self._state_summary(sid),
            "video": status,
        }

    def enrich_existing_context(self, max_nodes: int = 0) -> Dict[str, Any]:
        """Re-run v9 focus/title/context perception over saved screenshots.

        This lets an existing crawler_data directory become smarter without
        throwing away already learned states/edges. It updates representative
        focus context, state labels, and OCR tokens in place.
        """
        updated = 0
        attempted = 0
        missing = 0
        titles: Dict[str, int] = {}
        examples: List[Dict[str, Any]] = []
        limit = int(max_nodes or 0)
        for sid, node in list(self.graph.nodes.items()):
            if limit and attempted >= limit:
                break
            fp = node.representative
            if not fp.screenshot:
                missing += 1
                continue
            path = self.data_dir / str(fp.screenshot).replace("\\", "/")
            if not path.is_file():
                missing += 1
                continue
            attempted += 1
            frame = cv2.imread(str(path))
            if frame is None or not getattr(frame, "size", 0):
                missing += 1
                continue
            focus = detect_focus(frame, self.extractor._pytesseract)
            if not isinstance(focus, dict):
                continue
            old_label = node.label
            fp.focus = focus
            parts = [fp.ocr_text or ""]
            for key in ("screen_title", "human_label", "focused_item", "focused_value", "row_text", "context_text", "header_text", "action_bar_text"):
                val = str(focus.get(key) or "").strip()
                if val:
                    parts.append(val)
            ui = focus.get("ui_context") or {}
            if isinstance(ui, dict):
                for key in ("context_summary", "screen_title", "focused_item", "focused_value", "row_text"):
                    val = str(ui.get(key) or "").strip()
                    if val:
                        parts.append(val)
            merged = " ".join(parts).strip()[:2200]
            if merged:
                fp.ocr_text = merged
                fp.ocr_tokens = sorted(set(self.extractor.tokenize(merged)) | set(focus.get("tokens") or []))[:180]
            node.label = self.graph.suggest_label(fp)
            title = str(focus.get("screen_title") or (focus.get("ui_context") or {}).get("screen_title") or "").strip()
            if title:
                titles[title] = titles.get(title, 0) + 1
                self.brain.known_menu_titles.add(title)
            item = str(focus.get("focused_item") or (focus.get("ui_context") or {}).get("focused_item") or "").strip()
            if item:
                self.brain.known_focus_items.add(f"{title}::{item}" if title else item)
            for pair in focus.get("setting_pairs") or (focus.get("ui_context") or {}).get("setting_pairs") or []:
                if isinstance(pair, dict) and pair.get("label") and pair.get("value"):
                    self.brain.known_setting_pairs.add(f"{title}::{pair.get('label')}={pair.get('value')}")
            updated += 1
            if len(examples) < 12 and (node.label != old_label or title or item):
                examples.append({
                    "state_id": sid,
                    "old_label": old_label,
                    "new_label": node.label,
                    "screen_title": title,
                    "focused_item": item,
                    "focused_value": focus.get("focused_value") or "",
                    "role": focus.get("focus_role") or "",
                    "context_confidence": focus.get("context_confidence") or 0,
                })
        self.graph.save()
        self.brain.save()
        return {
            "ok": True,
            "attempted": attempted,
            "updated": updated,
            "missing": missing,
            "titles": dict(sorted(titles.items(), key=lambda kv: (-kv[1], kv[0]))),
            "examples": examples,
        }

    @staticmethod
    def _action_sequence_for_display(action: str) -> List[str]:
        channel = CrawlerBrain.parse_channel_action(action)
        if channel is not None:
            return list(str(channel)) + ["select"]
        if "," in str(action):
            return [p.strip() for p in str(action).split(",") if p.strip()]
        return [str(action)]

    def transition_cards(self, limit: int = 300) -> List[Dict[str, Any]]:
        """Return explicit before → button/sequence → after transition cards.

        This is deliberately redundant with edges because humans need to audit the causal chain:
        the screen it thought it was on, the exact remote input, and the screen it landed on.
        """
        cards: List[Dict[str, Any]] = []
        for eid, edge in self.graph.edges.items():
            stat = self.brain.state_actions.get(self.brain.state_action_key(edge.from_state, edge.action))
            last_sample = edge.samples[-1] if edge.samples else {}
            reward = last_sample.get("reward")
            timing = last_sample.get("timing") if isinstance(last_sample.get("timing"), dict) else {}
            before = last_sample.get("before") if isinstance(last_sample.get("before"), dict) else self._state_summary(edge.from_state)
            after = last_sample.get("after") if isinstance(last_sample.get("after"), dict) else self._state_summary(edge.to_state)
            before.setdefault("image_url", self._node_image_url(edge.from_state))
            after.setdefault("image_url", self._node_image_url(edge.to_state))
            before.setdefault("label", self.graph.nodes.get(edge.from_state).label if edge.from_state in self.graph.nodes else edge.from_state)
            after.setdefault("label", self.graph.nodes.get(edge.to_state).label if edge.to_state in self.graph.nodes else edge.to_state)
            cards.append({
                "id": eid,
                "before_state": edge.from_state,
                "button": edge.action,
                "button_sequence": self._action_sequence_for_display(edge.action),
                "after_state": edge.to_state,
                "before": before,
                "after": after,
                "confidence": edge.confidence,
                "attempts": edge.attempts,
                "successes": edge.successes,
                "failures": edge.failures,
                "noops": edge.noops,
                "reversible_with": edge.reversible_with,
                "last_seen": edge.last_seen,
                "reward": reward,
                "avg_state_action_reward": round(stat.avg_reward, 3) if stat else None,
                "state_action_attempts": stat.attempts if stat else edge.attempts,
                "discoveries": stat.discoveries if stat else 0,
                "response_s": timing.get("response_s"),
                "timing": timing,
                "created_state": last_sample.get("created_state"),
                "reward_details": last_sample.get("reward_details", {}),
                "similarity": last_sample.get("before_after_similarity", {}),
                "edge_existed": last_sample.get("edge_existed"),
                "ocr_delta": last_sample.get("ocr_delta", {}),
                "is_self_loop": edge.from_state == edge.to_state,
            })
        cards.sort(key=lambda c: (c.get("last_seen") or "", float(c.get("confidence") or 0), int(c.get("attempts") or 0)), reverse=True)
        return cards[: max(1, int(limit))]

    def visual_map(self) -> Dict[str, Any]:
        depths = self.graph.depths_from_root()
        for sid in self.graph.nodes:
            depths.setdefault(sid, 999)

        # Flowchart lanes are vertical columns by graph depth. Unreachable/passive discoveries
        # get their own wrapped columns instead of being crushed into one tiny bottom row.
        levels: Dict[int, List[str]] = {}
        for sid, depth in depths.items():
            levels.setdefault(depth, []).append(sid)
        for level_nodes in levels.values():
            level_nodes.sort(key=lambda sid: (-self.state_confidence(sid), self.state_kind(sid), self.graph.nodes[sid].label, sid))

        nodes: List[Dict[str, Any]] = []
        channels_by_state: Dict[str, List[Dict[str, Any]]] = {}
        for rec in self.brain.channels.values():
            channels_by_state.setdefault(rec.state_id, []).append(asdict(rec))

        card_w = int(getattr(self.config, "flow_lane_card_w", 280))
        card_h = int(getattr(self.config, "flow_lane_card_h", 190))
        x_gap = card_w + 90
        y_gap = card_h + 42
        normal_depths = [d for d in sorted(levels) if d != 999]
        if not normal_depths and levels:
            normal_depths = []
        depth_to_lane = {depth: idx for idx, depth in enumerate(normal_depths)}
        orphan_start_lane = len(depth_to_lane) + (1 if depth_to_lane else 0)

        for depth in sorted(levels):
            sids = levels[depth]
            if depth == 999:
                # Wrap orphan/passive nodes into several readable columns.
                per_col = 8
                base_lane = orphan_start_lane
                lane_label = "Unlinked/passive"
            else:
                per_col = max(1, len(sids) + 1)
                base_lane = depth_to_lane.get(depth, 0)
                lane_label = f"Depth {depth}"
            for idx, sid in enumerate(sids):
                col_offset = idx // per_col if depth == 999 else 0
                row = idx % per_col
                lane = base_lane + col_offset
                node = self.graph.nodes[sid]
                fp = node.representative
                remaining = self.remaining_actions_for_state(sid)
                outgoing = [asdict(e) for e in self.graph.outgoing_edges(sid, min_confidence=0.0)]
                incoming = [asdict(e) for e in self.graph.incoming_edges(sid)]
                frontier_score = len(remaining) * 2.0 + self.state_confidence(sid)
                nodes.append({
                    "id": sid,
                    "label": node.label or sid,
                    "kind": self.state_kind(sid),
                    "lane": lane,
                    "lane_label": lane_label,
                    "depth": depth if depth != 999 else None,
                    "x": int(80 + lane * x_gap),
                    "y": int(90 + row * y_gap),
                    "w": card_w,
                    "h": card_h,
                    "confidence": self.state_confidence(sid),
                    "frontier_score": round(frontier_score, 3),
                    "observations": node.observation_count,
                    "ocr_text": fp.ocr_text,
                    "ocr_tokens": fp.ocr_tokens,
                    "focus": fp.focus if isinstance(getattr(fp, "focus", {}), dict) else {},
                    "focus_label": self.focus_label(fp),
                    "screenshot": fp.screenshot,
                    "image_url": self._node_image_url(sid),
                    "channels": channels_by_state.get(sid, []),
                    "remaining_actions": remaining,
                    "remaining_count": len(remaining),
                    "outgoing": outgoing,
                    "incoming": incoming,
                    "first_seen": node.first_seen,
                    "last_seen": node.last_seen,
                })

        pair_counts: Dict[Tuple[str, str], int] = {}
        edges: List[Dict[str, Any]] = []
        for eid, edge in self.graph.edges.items():
            last_sample = edge.samples[-1] if edge.samples else {}
            pair = (edge.from_state, edge.to_state)
            curve_index = pair_counts.get(pair, 0)
            pair_counts[pair] = curve_index + 1
            stat = self.brain.state_actions.get(self.brain.state_action_key(edge.from_state, edge.action))
            before = self._state_summary(edge.from_state)
            after = self._state_summary(edge.to_state)
            edges.append({
                "id": eid,
                "from": edge.from_state,
                "to": edge.to_state,
                "action": edge.action,
                "button_sequence": self._action_sequence_for_display(edge.action),
                "before": before,
                "after": after,
                "attempts": edge.attempts,
                "successes": edge.successes,
                "failures": edge.failures,
                "noops": edge.noops,
                "confidence": edge.confidence,
                "reward": last_sample.get("reward"),
                "avg_state_action_reward": round(stat.avg_reward, 3) if stat else None,
                "state_action_attempts": stat.attempts if stat else edge.attempts,
                "discoveries": stat.discoveries if stat else 0,
                "response_s": (last_sample.get("timing") or {}).get("response_s") if isinstance(last_sample.get("timing"), dict) else None,
                "reversible_with": edge.reversible_with,
                "last_seen": edge.last_seen,
                "curve_index": curve_index,
                "is_self_loop": edge.from_state == edge.to_state,
                "ocr_delta": last_sample.get("ocr_delta", {}),
            })
        edges.sort(key=lambda e: (e["from"], e["action"], -float(e["confidence"])))

        action_conf = self.action_confidence_report()
        best_route_conf = 0.0
        reachable = 0
        if self.graph.root_state:
            for sid in self.graph.nodes:
                route = self.graph.shortest_route(self.graph.root_state, sid, min_confidence=0.05)
                if route is not None:
                    reachable += 1
                    best_route_conf = max(best_route_conf, self.graph.route_confidence(route))

        coverage = self.exploration_coverage()
        lane_count = max([n["lane"] for n in nodes], default=0) + 1
        row_count = max([int((n["y"] - 90) / y_gap) for n in nodes], default=0) + 1
        transitions = self.transition_cards(limit=300)
        return {
            "ok": True,
            "schema": "jamboree_visual_flow_map_v4_focus",
            "updated_at": self._now(),
            "root_state": self.graph.root_state,
            "current_state": self._last_state,
            "node_count": len(self.graph.nodes),
            "edge_count": len(self.graph.edges),
            "transition_count": len(transitions),
            "reachable_from_root": reachable,
            "highest_route_confidence": best_route_conf,
            "coverage": coverage,
            "layout": {
                "mode": "vertical_lanes",
                "card_w": card_w,
                "card_h": card_h,
                "x_gap": x_gap,
                "y_gap": y_gap,
                "lane_count": lane_count,
                "row_count": row_count,
            },
            "nodes": nodes,
            "edges": edges,
            "transitions": transitions,
            "action_confidence": action_conf,
            "timing": {k: asdict(v) for k, v in self.brain.action_timing.items()},
            "channels": self.brain.channel_summary(),
            "recent_events": [asdict(e) for e in list(self.events)[-30:]],
        }

    def find_state_candidates(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        q = str(query or "").strip()
        if not q:
            return []
        qlow = q.lower()
        qtokens = set(self._query_tokens(q))
        candidates = []
        for sid, node in self.graph.nodes.items():
            text = self._text_for_node(node)
            low = text.lower()
            ntokens = set(node.representative.ocr_tokens or []) | set(self._query_tokens(node.label or ""))
            token_score = (len(qtokens & ntokens) / max(1, len(qtokens))) if qtokens else 0.0
            substring_bonus = 0.35 if qlow in low else 0.0
            kind_bonus = 0.12 if self.state_kind(sid) in qlow else 0.0
            score = min(1.0, token_score * 0.62 + substring_bonus + kind_bonus + self.state_confidence(sid) * 0.18)
            if score > 0.08:
                candidates.append({
                    "state_id": sid,
                    "label": node.label,
                    "kind": self.state_kind(sid),
                    "score": round(score, 4),
                    "confidence": self.state_confidence(sid),
                    "ocr_text": node.representative.ocr_text,
                    "image_url": f"/api/crawl/state/{sid}/image" if node.representative.screenshot else None,
                })
        candidates.sort(key=lambda c: (c["score"], c["confidence"]), reverse=True)
        return candidates[:max(1, int(limit))]

    def _route_payload(self, start_state: str, target_state: str, route: Optional[List[TransitionEdge]]) -> Dict[str, Any]:
        actions = [e.action for e in route] if route is not None else None
        return {
            "start_state": start_state,
            "target_state": target_state,
            "path": actions,
            "steps": [asdict(e) for e in route] if route is not None else None,
            "length": len(route) if route is not None else None,
            "route_confidence": self.graph.route_confidence(route),
        }

    def plan_route(self, target_state: Optional[str] = None, query: Optional[str] = None, channel: Optional[int] = None) -> Dict[str, Any]:
        if channel is not None:
            rec = self.brain.channels.get(str(int(channel)))
            if rec and rec.state_id in self.graph.nodes:
                target_state = rec.state_id
            else:
                return {
                    "ok": True,
                    "mode": "direct_channel",
                    "channel": int(channel),
                    "known": False,
                    "path": [f"CH_{int(channel)}"],
                    "route_confidence": 0.78,
                    "note": "Channel is not in the learned map yet, but direct numeric tune can still be attempted.",
                }
        candidates: List[Dict[str, Any]] = []
        if not target_state and query:
            candidates = self.find_state_candidates(query, limit=8)
            if candidates:
                target_state = candidates[0]["state_id"]
        if not target_state or target_state not in self.graph.nodes:
            return {"ok": False, "error": "target_state_not_found", "query": query, "candidates": candidates}

        try:
            current_state, _, _ = self.current_state_id()
        except Exception:
            current_state = self.graph.root_state or target_state
        route = self.graph.shortest_route(current_state, target_state, min_confidence=0.10)
        start_state = current_state
        start_mode = "current"
        if route is None and self.graph.root_state:
            route = self.graph.shortest_route(self.graph.root_state, target_state, min_confidence=0.10)
            start_state = self.graph.root_state
            start_mode = "root"
        payload = self._route_payload(start_state, target_state, route)
        payload.update({
            "ok": route is not None,
            "mode": "known_state",
            "start_mode": start_mode,
            "query": query,
            "candidates": candidates,
            "target": asdict(self.graph.nodes[target_state]),
        })
        if route is None:
            payload["error"] = "no_learned_route"
        return payload

    def navigate_to_target(self, target_state: Optional[str] = None, query: Optional[str] = None, channel: Optional[int] = None, dry_run: bool = False) -> Dict[str, Any]:
        if channel is not None:
            action = f"CH_{int(channel)}"
            if dry_run:
                return {"ok": True, "dry_run": True, "mode": "direct_channel", "channel": int(channel), "path": [action]}
            self.event("info", "direct channel navigation requested", channel=int(channel))
            before_fp = self.capture_fingerprint(hint_prefix="before_channel_nav")
            self.safe_send(action)
            time.sleep(self.config.channel_tune_settle_s)
            after_fp = self.capture_fingerprint(hint_prefix="after_channel_nav")
            after_id, created, cmp = self.graph.upsert_state(after_fp, self.config.state_similarity_threshold)
            confidence = max(0.5, cmp.get("score", 0.5))
            rec = self.brain.learn_channel(int(channel), after_id, after_fp, confidence)
            self.graph.save(); self.brain.save()
            with self._lock:
                self._last_state = after_id
            return {"ok": True, "mode": "direct_channel", "channel": int(channel), "state_id": after_id, "created": created, "channel_record": asdict(rec)}

        plan = self.plan_route(target_state=target_state, query=query)
        if dry_run or not plan.get("ok"):
            plan["dry_run"] = dry_run
            return plan
        route_edges = [TransitionEdge(**e) for e in plan.get("steps") or []]
        if plan.get("start_mode") == "root":
            self.restore_start_context()
        execution = []
        for edge in route_edges:
            if self._stop.is_set():
                break
            action = edge.action
            self.event("info", "route step", action=action, expected_to=edge.to_state, target=plan.get("target_state"))
            self.safe_send(action)
            time.sleep(self.brain.expected_settle_s(action, self.config))
            actual_id, _, cmp = self.current_state_id()
            ok = actual_id == edge.to_state or cmp.get("score", 0.0) >= self.config.state_similarity_threshold
            execution.append({
                "action": action,
                "expected_state": edge.to_state,
                "actual_state": actual_id,
                "ok": ok,
                "similarity": cmp,
                "expected_confidence": edge.confidence,
            })
            if not ok:
                self.event("warning", "route verification failed", action=action, expected=edge.to_state, actual=actual_id)
                break
        final_state = execution[-1]["actual_state"] if execution else plan.get("start_state")
        return {
            "ok": bool(execution) and execution[-1].get("ok", False) if route_edges else True,
            "mode": "known_state",
            "target_state": plan.get("target_state"),
            "route_confidence": plan.get("route_confidence"),
            "path": plan.get("path"),
            "execution": execution,
            "final_state": final_state,
        }

    def run_goal(self, query: str, desired_value: str = "", final_sequence: Optional[List[str]] = None, dry_run: bool = True) -> Dict[str, Any]:
        final_sequence = final_sequence or []
        candidates = self.find_state_candidates(query, limit=8)
        if not candidates:
            return {"ok": False, "error": "no_matching_learned_screen", "query": query, "candidates": []}
        target_state = candidates[0]["state_id"]
        plan = self.plan_route(target_state=target_state, query=query)
        response: Dict[str, Any] = {
            "ok": bool(plan.get("ok")),
            "query": query,
            "desired_value": desired_value,
            "target_state": target_state,
            "candidates": candidates,
            "plan": plan,
            "dry_run": dry_run,
            "note": "Settings control is evidence-based: it navigates to the best known screen, then only applies the optional final sequence you provide.",
        }
        if dry_run or not plan.get("ok"):
            return response
        nav = self.navigate_to_target(target_state=target_state, dry_run=False)
        response["navigation"] = nav
        applied = []
        if nav.get("ok") and final_sequence:
            for key in final_sequence:
                key = str(key).strip()
                if not key:
                    continue
                if key.lower() == "select" and not self.config.allow_select_on_dangerous_text:
                    fp = self.capture_fingerprint(hint_prefix="goal_guard")
                    if DANGEROUS_TEXT.search(fp.ocr_text or ""):
                        applied.append({"key": key, "ok": False, "blocked": True, "reason": "dangerous_text", "text": fp.ocr_text[:200]})
                        break
                result = self.safe_send(key)
                time.sleep(self.brain.expected_settle_s(key, self.config))
                sid, _, cmp = self.current_state_id()
                applied.append({"key": key, "ok": True, "result": result, "state_id": sid, "similarity": cmp})
        response["applied_sequence"] = applied
        response["final_state"] = applied[-1]["state_id"] if applied else nav.get("final_state")
        return response

