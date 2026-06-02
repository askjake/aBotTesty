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
import os
import random
import re
import threading
import time
import uuid
try:
    import psutil as _psutil
except ImportError:  # pragma: no cover
    _psutil = None  # type: ignore
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional, Tuple

import cv2
import numpy as np

from focus_detector import detect_focus

# v34: guide-grid intelligence learns selectable program/channel rows. Optional
# so crawler still boots on machines without OCR/Tesseract.
try:
    from channel_metadata import extract_guide_grid
except Exception:  # pragma: no cover
    def extract_guide_grid(*a, **k): return {"detected": False, "quality_flags": ["guide_grid_unavailable"]}

# v23: region-first perception.  This lets the crawler look at known UI
# regions first, then broaden only when expectations fail.
try:
    from region_first_perception import RegionFirstPerceiver, pattern_from_region_family
except Exception:  # pragma: no cover
    class RegionFirstPerceiver:  # type: ignore
        def __init__(self, *a, **k): pass
        def perceive(self, *a, **k): return {}
    def pattern_from_region_family(family: str) -> str: return "unknown"

# v18: human-like observer layer; non-fatal so experimental bundles still boot.
try:
    from human_observer import observe_human_cues, screen_kind_from_focus, is_transient_focus
except Exception:  # pragma: no cover
    def observe_human_cues(frame, focus=None, ocr_text="", metrics=None):
        return {"screen_kind": "unknown", "is_transient": False, "is_actionable": True, "feature_tags": [], "risk_flags": []}
    def screen_kind_from_focus(focus):
        return "unknown"
    def is_transient_focus(focus):
        return False

# v15: fork intelligence modules from aBotTesty. These are intentionally
# non-critical; the crawler must still boot if one module is missing while
# someone is experimenting with the fork.
try:
    from pattern_recognition import UIPattern, PatternRecognizer, PatternConfidence, AdaptiveThresholdModel
except Exception:  # pragma: no cover - defensive fallback for partial forks
    UIPattern = None  # type: ignore
    PatternConfidence = None  # type: ignore
    class PatternRecognizer:  # type: ignore
        def classify_screen(self, fp, focus=None):
            class _P:
                pattern = type("_Enum", (), {"value": "unknown"})()
                confidence = 0.0
                reasons = ["pattern_recognition unavailable"]
            return _P()
        def get_pattern_stats(self):
            return {"unavailable": True}
    class AdaptiveThresholdModel:  # type: ignore
        def get_threshold(self, pattern, state_id=None, default=0.86): return default
        def update_state_stability(self, state_id, observations, variance): pass
        def record_match(self, pattern, matched): pass
        def get_stats(self): return {"unavailable": True}
try:
    from sequence_learner import SequenceLearner, LearnedSequence
except Exception:  # pragma: no cover
    LearnedSequence = None  # type: ignore
    class SequenceLearner:  # type: ignore
        def __init__(self, data_dir): pass
        def record_action(self, *a, **k): pass
        def mine_sequences(self, *a, **k): return []
        def suggest_next_action(self, *a, **k): return None
        def record_suggestion_outcome(self, *a, **k): pass
        def get_stats(self): return {"unavailable": True}
        def save(self): pass
        def reset(self): pass
try:
    from persistence_tracker import PersistenceTracker, UnreachableState
except Exception:  # pragma: no cover
    UnreachableState = None  # type: ignore
    class PersistenceTracker:  # type: ignore
        def __init__(self, data_dir): pass
        def mark_navigation_failed(self, *a, **k): pass
        def mark_navigation_succeeded(self, *a, **k): pass
        def record_retry_attempt(self, *a, **k): pass
        def get_retry_candidates(self, *a, **k): return []
        def get_stats(self): return {"unavailable": True}
        def save(self): pass
        def reset(self): pass

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
        default_factory=lambda: [
            "up", "down", "left", "right", "guide", "back", "home", "info", "select",
            "live", "recall", "input", "diamond", "ddiamond", "options", "dvr", "ch_up", "ch_down"
        ]
    )
    reset_key: str = "home"
    reverse_key: str = "back"
    start_sequence: List[str] = field(default_factory=list)
    settle_s: float = 1.15
    reset_settle_s: float = 1.8
    between_key_s: float = 0.08
    # Hard limits — 0 means unlimited. In continuous mode these are managed
    # automatically by the DynamicGovernor; do not set manually.
    max_steps: int = 0
    max_states: int = 0
    max_depth: int = 18
    # Dynamic governor
    governor_enabled: bool = True
    governor_mem_warn_pct: float = 72.0
    governor_mem_critical_pct: float = 88.0
    governor_step_target_s: float = 6.0
    governor_slow_step_s: float = 14.0
    governor_depth_floor: int = 8
    governor_depth_ceil: int = 24
    governor_match_floor: int = 60
    governor_match_ceil: int = 600
    governor_check_every_n_steps: int = 20
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

    # v14: separated execution speed from perception depth.
    # "deep" = full OCR after most actions; "balanced" = full OCR at checkpoints;
    # "tunnel" = fast visual verification for known paths, deep OCR only on surprises.
    execution_mode: str = "balanced"
    fast_known_path_enabled: bool = True
    fast_known_action_min_attempts: int = 2
    fast_known_action_min_reward: float = 4.0
    fast_known_action_success_ratio: float = 0.60
    deep_ocr_every_n_steps: int = 6
    deep_ocr_on_select: bool = True
    max_adaptive_observe_s: float = 1.8
    timing_outlier_clip_s: float = 4.0
    route_replay_gap_s: float = 0.075
    route_replay_checkpoint_s: float = 0.45

    # v17: phased timing.  The crawler now learns three separate events:
    # button press -> first visible reaction -> completed/stable screen.
    # This prevents it from treating the first flash of movement as the finished menu.
    max_completion_observe_s: float = 6.0
    completion_min_observe_s: float = 0.35
    completion_quiet_s: float = 0.45
    completion_stability_threshold: float = 0.992
    completion_stable_observations_required: int = 3
    completion_extra_wait_on_incomplete_s: float = 1.2
    completion_extra_attempts: int = 2
    remarkable_timing_multiplier: float = 2.75
    remarkable_timing_min_delta_s: float = 1.0

    # v18: human-observer controls.  These make the crawler act less like a
    # frame-differencer and more like a person watching TV: wait on loading
    # interstitials, collapse passive video frames, and bias actions toward the
    # affordances a human would notice.
    human_observer_enabled: bool = True
    human_skip_transient_frontier: bool = True
    human_collapse_passive_video: bool = True
    passive_video_similarity_score: float = 0.915
    loading_similarity_score: float = 0.965
    human_loading_extra_wait_s: float = 0.65
    human_loading_max_extra_attempts: int = 4

    # v23: region-first perception.  A human does not OCR the whole TV image
    # every time; they first look at known UI anchors like the top title, guide
    # row, info panel, focused row, right detail panel, and action bar.  If the
    # expected regions do not contain what they should, the crawler broadens
    # its view and records why.
    region_first_perception_enabled: bool = True
    region_first_min_confidence: float = 0.62
    region_first_full_ocr_threshold: float = 0.44
    region_first_action_bias_enabled: bool = True

    # v28: UI-friendly crawl mode.  The crawler had become smart but too
    # synchronous: full graph scans, pretty JSON saves, frequent sequence mining,
    # and deep OCR could make /monitor feel sticky while the crawl ran.  These
    # knobs batch disk writes, reduce hot-loop CPU, and keep deep analysis at
    # checkpoints instead of every tiny motion.
    ui_friendly_mode: bool = True
    compact_json_saves: bool = True
    hot_loop_save_every_n_actions: int = 6
    hot_loop_save_min_interval_s: float = 8.0
    sequence_mining_every_n_steps: int = 24
    graph_match_candidate_limit: int = 240

    penalty_transient_loading_state: float = -4.0
    penalty_passive_video_duplicate: float = -1.5
    reward_human_feature_goal: float = 4.0
    # v19: video-health and bootstrap controls.
    # Color bars count as active capture input. A true black screen is treated as
    # STB/video misbehavior and triggers channel recovery instead of silently
    # stopping the crawl.
    video_black_screen_recovery_enabled: bool = True
    video_black_screen_recovery_sequence: List[str] = field(default_factory=lambda: ["ch_up", "ch_down", "live"])
    video_black_screen_recovery_wait_s: float = 1.6
    video_black_screen_max_recoveries: int = 3

    # Every supervised test can start from a system-diagnostics capture, then
    # return to live TV. This provides receiver/software/baseline context before
    # the crawler begins changing state.
    sysdiag_bootstrap_enabled: bool = False
    sysdiag_bootstrap_key: str = "sys info"
    sysdiag_bootstrap_settle_s: float = 3.0
    sysdiag_bootstrap_live_key: str = "live"
    sysdiag_bootstrap_live_settle_s: float = 2.0


    # Channel learning controls
    channel_learning_enabled: bool = False
    channel_scan_list: List[int] = field(default_factory=list)
    channel_digit_gap_s: float = 0.075
    channel_tune_settle_s: float = 2.2
    channel_suffix_key: str = "select"
    guide_grid_learning_enabled: bool = True
    guide_grid_min_confidence: float = 0.35


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

    # v32: demonstration-driven exploration. Manual Teacher Mode and monitor
    # operator paths represent real customer/operator intent. The crawler should
    # rehearse those paths, trust them more than random probes, and branch out
    # from each demonstrated waypoint to discover adjacent features.
    demo_practice_enabled: bool = True
    demo_practice_sources: List[str] = field(default_factory=lambda: [
        "manual_teaching", "manual_teaching_fast", "operator_monitor_auto"
    ])
    demo_practice_frontier_bonus: float = 18.0
    demo_practice_action_bonus: float = 9.0
    demo_practice_action_budget_bonus: int = 3
    demo_practice_min_confidence: float = 0.15
    demo_practice_every_cycles: int = 1
    demo_practice_max_edges_per_cycle: int = 2
    demo_practice_neighbor_actions: int = 3

    # Human-like exploration enhancements
    curiosity_randomness: float = 0.12
    transition_sample_limit: int = 30
    flow_lane_card_w: int = 280
    flow_lane_card_h: int = 190


@dataclass
class ActionTiming:
    """Per-action timing model.

    v14/v16 only learned a single ``response`` value.  That was really the
    first visible change, so menus were often captured while still loading.
    v17 keeps backwards-compatible fields but adds phased timing:
      - start: first visible reaction after the key press
      - complete: screen appears stable/finished
      - stable: local visual stability window duration
    """
    action: str
    attempts: int = 0
    avg_response_s: float = 0.0  # backwards-compatible alias for avg_start_s
    last_response_s: float = 0.0
    min_response_s: float = 999.0
    max_response_s: float = 0.0

    avg_start_s: float = 0.0
    last_start_s: float = 0.0
    min_start_s: float = 999.0
    max_start_s: float = 0.0

    avg_complete_s: float = 0.0
    last_complete_s: float = 0.0
    min_complete_s: float = 999.0
    max_complete_s: float = 0.0

    avg_stable_s: float = 0.0
    last_stable_s: float = 0.0
    remarkable_count: int = 0
    last_remarkable: Optional[Dict[str, Any]] = None
    last_flags: List[str] = field(default_factory=list)

    @staticmethod
    def _ema(old: float, new: float, attempts: int) -> float:
        alpha = 0.30 if attempts <= 5 else 0.15
        return float(new) if old <= 0 else (1.0 - alpha) * float(old) + alpha * float(new)

    @staticmethod
    def _safe(v: Optional[float], default: float = 0.0) -> float:
        try:
            if v is None:
                return float(default)
            return max(0.0, float(v))
        except Exception:
            return float(default)

    def update(self, response_s: float) -> None:
        # Legacy path: treat response as start and complete when only one value exists.
        self.update_phase(start_s=response_s, complete_s=response_s, stable_s=0.0, flags=[])

    def update_phase(
        self,
        start_s: Optional[float],
        complete_s: Optional[float],
        stable_s: Optional[float] = 0.0,
        flags: Optional[List[str]] = None,
        remarkable: Optional[Dict[str, Any]] = None,
    ) -> None:
        start_s = self._safe(start_s, 0.0)
        complete_s = max(start_s, self._safe(complete_s, start_s))
        stable_s = self._safe(stable_s, 0.0)
        self.attempts += 1

        self.avg_start_s = self._ema(self.avg_start_s or self.avg_response_s, start_s, self.attempts)
        self.last_start_s = start_s
        self.min_start_s = min(self.min_start_s, start_s)
        self.max_start_s = max(self.max_start_s, start_s)

        self.avg_complete_s = self._ema(self.avg_complete_s, complete_s, self.attempts)
        self.last_complete_s = complete_s
        self.min_complete_s = min(self.min_complete_s, complete_s)
        self.max_complete_s = max(self.max_complete_s, complete_s)

        self.avg_stable_s = self._ema(self.avg_stable_s, stable_s, self.attempts)
        self.last_stable_s = stable_s

        # Preserve old field names for dashboards/tests/old saved JSON readers.
        self.avg_response_s = self.avg_start_s
        self.last_response_s = start_s
        self.min_response_s = min(self.min_response_s, start_s)
        self.max_response_s = max(self.max_response_s, start_s)

        self.last_flags = list(flags or [])[:12]
        if remarkable:
            self.remarkable_count += 1
            self.last_remarkable = dict(remarkable)


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
    # v34 guide-grid learning: keep channel identity and visible program options.
    channel_code: str = ""
    channel_name: str = ""
    channel_logo_texts: List[str] = field(default_factory=list)
    icon_signatures: List[str] = field(default_factory=list)
    programs: List[Dict[str, Any]] = field(default_factory=list)
    guide_observations: int = 0
    guide_rows_seen: int = 0


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
    # v15: adaptive UI pattern intelligence from aBotTesty fork.
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

    def __init__(
        self,
        data_dir: Path,
        save_screenshots: bool = True,
        ocr_enabled: bool = True,
        region_first_enabled: bool = True,
        region_first_min_confidence: float = 0.62,
        region_first_full_ocr_threshold: float = 0.44,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.states_dir = self.data_dir / "states"
        self.states_dir.mkdir(parents=True, exist_ok=True)
        self.save_screenshots = save_screenshots
        self.ocr_enabled = ocr_enabled
        self.region_first_enabled = bool(region_first_enabled)
        self.region_first_min_confidence = float(region_first_min_confidence)
        self.region_first_full_ocr_threshold = float(region_first_full_ocr_threshold)
        self._pytesseract = None
        if ocr_enabled:
            try:
                import pytesseract  # type: ignore

                self._pytesseract = pytesseract
            except Exception:
                self._pytesseract = None
        self.region_perceiver = RegionFirstPerceiver(self._pytesseract if self.ocr_enabled else False)

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
        # v23: region-first perception.  Read known anchors first; only fall
        # back to full-frame OCR when the targeted read cannot recognize the
        # surface.  This preserves learning quality while avoiding OCR soup.
        region_context: Dict[str, Any] = {}
        text = ""
        if self.region_first_enabled and self.ocr_enabled:
            try:
                region_context = self.region_perceiver.perceive(frame, min_confidence=self.region_first_min_confidence)
                text = str(region_context.get("text") or "").strip()
                if float(region_context.get("confidence") or 0.0) < self.region_first_full_ocr_threshold and self._pytesseract:
                    broad_text = self.ocr(frame)
                    if broad_text:
                        text = " ".join([text, broad_text]).strip()
                        region_context.setdefault("quality_flags", []).append("full_ocr_fallback_used")
            except Exception:
                log.debug("region-first perception failed; falling back to full OCR", exc_info=True)
                region_context = {}
                text = self.ocr(frame)
        else:
            text = self.ocr(frame)
        focus = detect_focus(frame, self._pytesseract if self.ocr_enabled else False)
        if isinstance(focus, dict) and region_context:
            focus["region_first"] = region_context
            # Let high-confidence targeted reads fill weak generic focus fields.
            if region_context.get("title") and (not focus.get("screen_title") or float(focus.get("context_confidence") or 0.0) < 0.55):
                focus["screen_title"] = region_context.get("title")
                focus["menu_title"] = focus.get("menu_title") or region_context.get("title")
                focus["title_source"] = focus.get("title_source") or "region_first"
            if region_context.get("focused_item_hint") and not focus.get("focused_item"):
                focus["focused_item"] = region_context.get("focused_item_hint")
                focus["human_label"] = focus.get("human_label") or region_context.get("focused_item_hint")
            if region_context.get("displayed_datetime_text"):
                focus["displayed_datetime_text"] = region_context.get("displayed_datetime_text")
            if region_context.get("channel_number") and not focus.get("channel_number"):
                focus["channel_number"] = region_context.get("channel_number")
            if region_context.get("channel_code") and not focus.get("channel_name"):
                focus["channel_name"] = region_context.get("channel_code")
            focus.setdefault("quality_flags", [])
            for flag in region_context.get("quality_flags") or []:
                if flag not in focus["quality_flags"]:
                    focus["quality_flags"].append(flag)
        # Merge focus-local OCR into the global OCR context. This makes labels and
        # state matching much clearer when the full screen OCR is noisy.
        focus_text_parts = []
        if isinstance(focus, dict):
            # v9: merge spatial/semantic context, not just the raw focused crop.
            for key in (
                "screen_title", "menu_title", "page_name", "block_title", "title_source", "active_tab", "human_label",
                "focused_item", "focused_value", "channel_number", "channel_name", "popup_type",
                "label_text", "focus_text", "row_text", "context_text", "header_text", "action_bar_text",
                "displayed_datetime_text",
            ):
                val = str(focus.get(key) or "").strip()
                if val and val not in focus_text_parts:
                    focus_text_parts.append(val)
            ui = focus.get("ui_context") or {}
            if isinstance(ui, dict):
                for key in ("context_summary", "screen_title", "page_name", "block_title", "focused_item", "focused_value", "row_text"):
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
            rc = focus.get("region_first") if isinstance(focus.get("region_first"), dict) else {}
            for key in ("screen_family", "title", "displayed_datetime_text", "channel_number", "channel_code", "focused_item_hint", "text"):
                val = str(rc.get(key) or "").strip()
                if val and val not in focus_text_parts:
                    focus_text_parts.append(val)
            for name, val in (rc.get("regions") or {}).items() if isinstance(rc.get("regions"), dict) else []:
                val = str(val or "").strip()
                if val and val not in focus_text_parts:
                    focus_text_parts.append(val)
        brightness = round(float(np.mean(gray)), 3)
        variance = round(float(np.var(gray)), 3)
        entropy = round(self.image_entropy(gray), 4)
        edge_density = round(self.edge_density(gray), 5)
        merged_text = " ".join([text] + focus_text_parts).strip()[:2200]

        # v18: add a human-like interpretation layer.  It recognizes loading
        # interstitials, passive video, PIN/rating/PPV/timer flows, and suggests
        # how a human operator would treat the screen.  This is stored inside the
        # focus dict so old graph readers remain compatible.
        if isinstance(focus, dict):
            try:
                human = observe_human_cues(
                    frame,
                    focus=focus,
                    ocr_text=merged_text,
                    metrics={"brightness": brightness, "variance": variance, "entropy": entropy, "edge_density": edge_density},
                )
                focus["human_cues"] = human
                fallback_focus = ((human.get("visible_affordances") or {}).get("fallback_focus") or {}) if isinstance(human, dict) else {}
                if fallback_focus.get("found") and not focus.get("found"):
                    focus.update({
                        "found": True,
                        "confidence": fallback_focus.get("confidence", 0.0),
                        "bbox": fallback_focus.get("bbox"),
                        "center_norm": fallback_focus.get("center_norm"),
                        "row_guess": fallback_focus.get("row_guess"),
                        "col_guess": fallback_focus.get("col_guess"),
                        "region": fallback_focus.get("region", "fallback_red_focus"),
                        "focus_role": "visual_focus_fallback",
                    })
                    focus.setdefault("tokens", [])
                    for tok in fallback_focus.get("tokens", []) or []:
                        if tok not in focus["tokens"]:
                            focus["tokens"].append(tok)
                    # Re-attach the richer focus state for graph consumers.
                    human["visible_affordances"]["focus_found"] = True
                    human["visible_affordances"]["focus_confidence"] = float(fallback_focus.get("confidence") or 0.0)
                if human.get("screen_kind") == "loading_interstitial":
                    focus["loading"] = True
                    focus["popup_type"] = focus.get("popup_type") or "loading"
                if human.get("screen_kind") == "passive_video" and not focus.get("screen_title"):
                    focus["screen_title"] = "Live TV"
                if human.get("channel_number") and not focus.get("channel_number"):
                    focus["channel_number"] = human.get("channel_number")
                if human.get("channel_name") and not focus.get("channel_name"):
                    focus["channel_name"] = human.get("channel_name")
                focus.setdefault("semantic_tags", [])
                for tag in human.get("feature_tags", []) or []:
                    if tag not in focus["semantic_tags"]:
                        focus["semantic_tags"].append(tag)
                focus.setdefault("risk_flags", [])
                for flag in human.get("risk_flags", []) or []:
                    if flag not in focus["risk_flags"]:
                        focus["risk_flags"].append(flag)
                focus.setdefault("quality_flags", [])
                for flag in human.get("annoyance_flags", []) or []:
                    if flag not in focus["quality_flags"]:
                        focus["quality_flags"].append(flag)
                # v23: region-first perception can recommend/avoid concrete
                # actions based on screen family. Merge those hints into the same
                # human_cues channel consumed by the action orderer.
                rc = focus.get("region_first") if isinstance(focus.get("region_first"), dict) else {}
                if rc:
                    human.setdefault("recommended_actions", [])
                    human.setdefault("avoid_actions", [])
                    for act in rc.get("suggested_actions") or []:
                        if act not in human["recommended_actions"]:
                            human["recommended_actions"].append(act)
                    for act in rc.get("avoid_actions") or []:
                        if act not in human["avoid_actions"]:
                            human["avoid_actions"].append(act)
                    if rc.get("screen_family") and rc.get("screen_family") != "unknown":
                        human.setdefault("feature_tags", [])
                        tag = f"screen_family:{rc.get('screen_family')}"
                        if tag not in human["feature_tags"]:
                            human["feature_tags"].append(tag)
                if human.get("summary") and human.get("screen_kind") in {"loading_interstitial", "passive_video", "pin_prompt", "purchase_or_ppv", "timer_or_recording_flow"}:
                    merged_text = " ".join([merged_text, human.get("summary", ""), " ".join(human.get("feature_tags", []) or [])]).strip()[:2600]
            except Exception:
                log.debug("human observer failed", exc_info=True)

        region_tokens = []
        if isinstance(focus, dict) and isinstance(focus.get("region_first"), dict):
            region_tokens = self.tokenize(" ".join([str(focus["region_first"].get("text") or ""), str(focus["region_first"].get("screen_family") or "")]))
        merged_tokens = sorted(set(self.tokenize(merged_text)) | set(region_tokens) | set(focus.get("tokens", []) if isinstance(focus, dict) else []) | set(((focus.get("human_cues") or {}).get("tokens") or []) if isinstance(focus, dict) else []))[:200]
        return ScreenFingerprint(
            state_id=sid,
            timestamp=self._now(),
            screenshot=screenshot,
            ahash=self.average_hash(gray),
            dhash=self.difference_hash(gray),
            phash=self.perceptual_hash(gray),
            brightness=brightness,
            variance=variance,
            entropy=entropy,
            edge_density=edge_density,
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

        # v18: collapse things a human would treat as one state.  Dynamic video
        # frames should not create thousands of states; loading interstitials are
        # transient and should match each other strongly if they slip into the graph.
        ha = fa.get("human_cues") if isinstance(fa.get("human_cues"), dict) else {}
        hb = fb.get("human_cues") if isinstance(fb.get("human_cues"), dict) else {}
        ka = str(ha.get("screen_kind") or "")
        kb = str(hb.get("screen_kind") or "")
        if ka == kb == "loading_interstitial":
            score = max(score, 0.965)
        elif ka == kb == "passive_video":
            cha = str(ha.get("channel_number") or fa.get("channel_number") or "")
            chb = str(hb.get("channel_number") or fb.get("channel_number") or "")
            if cha and chb and cha != chb:
                score = min(score, 0.72)
            elif cha and chb and cha == chb:
                score = max(score, 0.945)
            else:
                score = max(score, 0.915)

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
        self.adaptive_thresholds = AdaptiveThresholdModel()
        self.compact_save: bool = True
        self.match_candidate_limit: int = 240
        self.load()

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
        payload = self.to_dict()
        if self.compact_save:
            tmp.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        else:
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self.graph_path)

    def reset(self) -> None:
        self.nodes = {}
        self.edges = {}
        self.root_state = None
        self.save()

    @staticmethod
    def _quick_candidate_score(fp: ScreenFingerprint, node: StateNode) -> float:
        """Cheap prefilter for large graphs.

        Full SimilarityModel.compare is rich but expensive when there are thousands
        of nodes because it compares OCR/focus/color vectors for every state.  This
        prefilter uses small hashes and coarse metrics to choose likely candidates,
        then the full model is applied only to the shortlist.
        """
        rep = node.representative
        try:
            ph = 1.0 - SimilarityModel.hamming_hex(fp.phash, rep.phash)
            dh = 1.0 - SimilarityModel.hamming_hex(fp.dhash, rep.dhash)
            ah = 1.0 - SimilarityModel.hamming_hex(fp.ahash, rep.ahash)
            br = 1.0 - min(1.0, abs(float(fp.brightness) - float(rep.brightness)) / 96.0)
            ed = 1.0 - min(1.0, abs(float(fp.edge_density) - float(rep.edge_density)) / 0.25)
            pattern_bonus = 0.04 if (getattr(fp, "ui_pattern", "") and fp.ui_pattern == getattr(rep, "ui_pattern", "")) else 0.0
            return max(0.0, min(1.0, 0.45 * ph + 0.24 * dh + 0.12 * ah + 0.10 * br + 0.09 * ed + pattern_bonus))
        except Exception:
            return 0.0

    def find_best(self, fp: ScreenFingerprint) -> Tuple[Optional[str], Dict[str, float]]:
        best_id = None
        best_cmp = {"score": 0.0}
        items = list(self.nodes.items())
        limit = int(getattr(self, "match_candidate_limit", 240) or 0)
        if limit > 0 and len(items) > limit:
            scored = sorted(
                ((self._quick_candidate_score(fp, node), sid, node) for sid, node in items),
                key=lambda x: x[0],
                reverse=True,
            )[:limit]
            candidates = [(sid, node) for _score, sid, node in scored]
        else:
            candidates = items
        for sid, node in candidates:
            cmp = SimilarityModel.compare(fp, node.representative)
            if cmp["score"] > best_cmp["score"]:
                best_id = sid
                best_cmp = cmp
        if len(items) > len(candidates):
            best_cmp = dict(best_cmp)
            best_cmp["candidate_count"] = len(candidates)
            best_cmp["total_states"] = len(items)
            best_cmp["candidate_prefilter"] = 1.0
        return best_id, best_cmp

    def upsert_state(self, fp: ScreenFingerprint, threshold: float) -> Tuple[str, bool, Dict[str, float]]:
        pattern = str(getattr(fp, "ui_pattern", "unknown") or "unknown")
        threshold = float(self.adaptive_thresholds.get_threshold(pattern, default=threshold))
        best_id, cmp = self.find_best(fp)
        now = self._now()
        matched = bool(best_id and cmp["score"] >= threshold)
        self.adaptive_thresholds.record_match(pattern, matched)
        if best_id and cmp["score"] >= threshold:
            node = self.nodes[best_id]
            node.last_seen = now
            node.observation_count += 1
            self.adaptive_thresholds.update_state_stability(best_id, node.observation_count, node.representative.variance)
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
        self.adaptive_thresholds.update_state_stability(sid, 1, fp.variance)
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
        self.compact_save: bool = True
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
            allowed_channel_fields = set(ChannelRecord.__dataclass_fields__.keys())
            self.channels = {
                k: ChannelRecord(**{kk: vv for kk, vv in dict(v).items() if kk in allowed_channel_fields})
                for k, v in raw.get("channels", {}).items()
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
            "schema": "jamboree_crawler_brain_v7_phased_timing",
            "updated_at": self.now(),
            "action_timing": {k: asdict(v) for k, v in self.action_timing.items()},
            "action_rewards": {k: asdict(v) for k, v in self.action_rewards.items()},
            "state_actions": {k: asdict(v) for k, v in self.state_actions.items()},
            "known_tokens": sorted(self.known_tokens),
            "known_concepts": sorted(self.known_concepts),
            "known_menu_titles": sorted(self.known_menu_titles),
            "known_focus_items": sorted(self.known_focus_items),
            "known_setting_pairs": sorted(self.known_setting_pairs),
            "channels": {k: asdict(v) for k, v in sorted(self.channels.items(), key=lambda kv: int(str(kv[0]).split("-", 1)[0]) if str(kv[0]).split("-", 1)[0].isdigit() else 999999)},
        }

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        payload = self.to_dict()
        if self.compact_save:
            tmp.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        else:
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
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

    @staticmethod
    def default_start_expectation(action: str) -> float:
        a = str(action or "").lower()
        if a.isdigit():
            return 0.18
        if a in {"up", "down", "left", "right"}:
            return 0.24
        if a in {"back", "recall"}:
            return 0.35
        if a in {"guide", "home", "dvr", "apps", "settings", "options", "info", "input", "live"}:
            return 0.55
        if a == "select":
            return 0.45
        return 0.40

    @staticmethod
    def default_completion_expectation(action: str) -> float:
        a = str(action or "").lower()
        if a.isdigit():
            return 0.28
        if a in {"up", "down", "left", "right"}:
            return 0.65
        if a in {"back", "recall"}:
            return 1.10
        if a in {"options", "info", "input"}:
            return 1.35
        if a in {"guide", "home", "dvr", "apps", "settings", "live"}:
            return 2.20
        if a == "select":
            return 1.65
        return 1.20

    def update_timing(self, action: str, response_s: float, max_sample_s: Optional[float] = None) -> None:
        # Legacy compatibility: update both start and complete with the same value.
        try:
            response_s = float(response_s)
            if max_sample_s is not None and max_sample_s > 0:
                response_s = min(response_s, float(max_sample_s))
        except Exception:
            response_s = 0.0
        self.timing_for(action).update(response_s)

    def update_timing_phase(
        self,
        action: str,
        start_s: Optional[float],
        complete_s: Optional[float],
        stable_s: Optional[float] = 0.0,
        cfg: Optional[CrawlerConfig] = None,
        flags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        timing = self.timing_for(action)
        # Compare against the already-learned expectation before updating it.
        expected_start = timing.avg_start_s or timing.avg_response_s or self.default_start_expectation(action)
        expected_complete = timing.avg_complete_s or self.default_completion_expectation(action)
        start_val = 0.0 if start_s is None else max(0.0, float(start_s))
        complete_val = max(start_val, 0.0 if complete_s is None else float(complete_s))
        max_sample = float(getattr(cfg, "timing_outlier_clip_s", 4.0) or 4.0) if cfg else 4.0
        # Start timing is a remote reaction latency, so clip it aggressively.
        clipped_start = min(start_val, max_sample)
        # Completion can legitimately be longer for guide/home/menu loads.
        max_complete = max(max_sample, float(getattr(cfg, "max_completion_observe_s", max_sample) or max_sample)) if cfg else max_sample
        clipped_complete = min(complete_val, max_complete)
        remarkable: Dict[str, Any] = {}
        mult = float(getattr(cfg, "remarkable_timing_multiplier", 2.75) or 2.75) if cfg else 2.75
        min_delta = float(getattr(cfg, "remarkable_timing_min_delta_s", 1.0) or 1.0) if cfg else 1.0
        out_flags = list(flags or [])
        if expected_start > 0 and start_val > expected_start * mult and (start_val - expected_start) >= min_delta:
            out_flags.append("remarkable_slow_start")
            remarkable["slow_start"] = {"observed_s": round(start_val, 3), "expected_s": round(expected_start, 3)}
        if expected_complete > 0 and complete_val > expected_complete * mult and (complete_val - expected_complete) >= min_delta:
            out_flags.append("remarkable_slow_completion")
            remarkable["slow_completion"] = {"observed_s": round(complete_val, 3), "expected_s": round(expected_complete, 3)}
        timing.update_phase(
            start_s=clipped_start,
            complete_s=clipped_complete,
            stable_s=stable_s,
            flags=out_flags,
            remarkable=remarkable or None,
        )
        return {
            "expected_start_s": round(expected_start, 3),
            "expected_complete_s": round(expected_complete, 3),
            "clipped_start_s": round(clipped_start, 3),
            "clipped_complete_s": round(clipped_complete, 3),
            "flags": out_flags[:12],
            "remarkable": remarkable,
        }

    def sanitize_timing_outliers(self, max_avg_s: float = 4.0) -> int:
        fixed = 0
        for timing in self.action_timing.values():
            for attr in ("avg_response_s", "last_response_s", "avg_start_s", "last_start_s"):
                if getattr(timing, attr, 0.0) > max_avg_s:
                    setattr(timing, attr, max_avg_s)
                    fixed += 1
            for attr in ("min_response_s", "min_start_s"):
                if getattr(timing, attr, 999.0) > max_avg_s:
                    setattr(timing, attr, max_avg_s)
            for attr in ("max_response_s", "max_start_s"):
                if getattr(timing, attr, 0.0) > max_avg_s * 3:
                    setattr(timing, attr, max_avg_s * 3)
            # Completion is allowed to be longer, but still cannot grow unbounded.
            comp_cap = max(max_avg_s, 6.0)
            for attr in ("avg_complete_s", "last_complete_s"):
                if getattr(timing, attr, 0.0) > comp_cap:
                    setattr(timing, attr, comp_cap)
                    fixed += 1
            if getattr(timing, "max_complete_s", 0.0) > comp_cap * 2:
                timing.max_complete_s = comp_cap * 2
        if fixed:
            self.save()
        return fixed

    def expected_start_s(self, action: str, cfg: CrawlerConfig) -> float:
        timing = self.timing_for(action)
        if not cfg.adaptive_timing_enabled:
            return self.default_start_expectation(action)
        val = timing.avg_start_s or timing.avg_response_s or self.default_start_expectation(action)
        return max(0.05, min(float(cfg.max_adaptive_observe_s), float(val) * 1.25 + 0.05))

    def expected_settle_s(self, action: str, cfg: CrawlerConfig) -> float:
        timing = self.timing_for(action)
        if not cfg.adaptive_timing_enabled:
            return cfg.settle_s
        val = timing.avg_complete_s or self.default_completion_expectation(action)
        return max(cfg.min_settle_s, min(float(cfg.max_completion_observe_s), float(val) * 1.25 + 0.20))

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
                # v18 human-observer rewards/penalties: useful features matter,
                # but transient/loading frames and duplicate passive video should
                # not be celebrated as navigation discoveries.
                human = focus.get("human_cues") if isinstance(focus.get("human_cues"), dict) else {}
                if human:
                    details["human_cues"] = {
                        "screen_kind": human.get("screen_kind"),
                        "confidence": human.get("confidence"),
                        "feature_tags": human.get("feature_tags", [])[:12],
                        "test_goals": human.get("test_goals", [])[:6],
                        "risk_flags": human.get("risk_flags", [])[:12],
                        "annoyance_flags": human.get("annoyance_flags", [])[:12],
                    }
                    kind = str(human.get("screen_kind") or "")
                    if kind == "loading_interstitial":
                        reward += float(getattr(cfg, "penalty_transient_loading_state", -4.0))
                        details["transient_loading_penalty"] = float(getattr(cfg, "penalty_transient_loading_state", -4.0))
                    elif kind == "passive_video" and created:
                        reward += float(getattr(cfg, "penalty_passive_video_duplicate", -1.5))
                        details["passive_video_duplicate_penalty"] = float(getattr(cfg, "penalty_passive_video_duplicate", -1.5))
                    if human.get("test_goals"):
                        reward += float(getattr(cfg, "reward_human_feature_goal", 4.0))
                        details["human_feature_goal_reward"] = float(getattr(cfg, "reward_human_feature_goal", 4.0))
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

    def learn_guide_grid(
        self,
        guide: Dict[str, Any],
        state_id: str = "",
        screenshot: Optional[str] = None,
        max_programs_per_channel: int = 24,
    ) -> Dict[str, Any]:
        """Learn every visible channel row and program cell from a DISH guide grid.

        Older channel learning only remembered explicit CH_n tune attempts. v34
        teaches the crawler that the guide itself is structured data: visible
        logos/callsigns identify channel rows, and every cell is a selectable
        program option reachable by a relative button sequence.
        """
        rows = list((guide or {}).get("rows") or [])
        now = self.now()
        updated_channels = 0
        updated_programs = 0
        updated_icons = 0
        selected = (guide or {}).get("selected") or {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            ch = str(row.get("channel_number") or "").strip()
            if not ch:
                continue
            key = ch
            try:
                ch_int = int(ch.split("-", 1)[0])
            except Exception:
                ch_int = 0
            rec = self.channels.get(key)
            if rec is None:
                rec = ChannelRecord(channel=ch_int, first_seen=now, last_seen=now)
                self.channels[key] = rec
                updated_channels += 1
            rec.last_seen = now
            rec.observations += 1
            rec.guide_observations += 1
            rec.guide_rows_seen += 1
            if state_id:
                rec.state_id = state_id
            if screenshot:
                rec.screenshot = screenshot
            code = str(row.get("channel_code") or "").strip()
            if code:
                rec.channel_code = code
                rec.channel_name = rec.channel_name or code
                rec.name_guess = rec.name_guess or code
                if code not in rec.symbols:
                    rec.symbols.append(code)
            logo_text = " ".join(str(row.get("channel_logo_text") or "").split())
            if logo_text and logo_text not in rec.channel_logo_texts:
                rec.channel_logo_texts.append(logo_text[:180])
                rec.channel_logo_texts = rec.channel_logo_texts[-12:]
            icon_sig = str(row.get("icon_signature") or "").strip()
            if icon_sig and icon_sig not in rec.icon_signatures:
                rec.icon_signatures.append(icon_sig)
                rec.icon_signatures = rec.icon_signatures[-12:]
                updated_icons += 1
            if logo_text and logo_text not in rec.ocr_texts:
                rec.ocr_texts.append(logo_text[:220])
                rec.ocr_texts = rec.ocr_texts[-8:]
            rec.confidence = max(float(rec.confidence or 0.0), float((guide or {}).get("confidence") or 0.0))
            seen_keys = {
                (str(p.get("title") or "").strip().lower(), str(p.get("time_label") or ""), int(p.get("col_index") or 0))
                for p in rec.programs if isinstance(p, dict)
            }
            for prog in row.get("programs") or []:
                if not isinstance(prog, dict):
                    continue
                title = " ".join(str(prog.get("title") or prog.get("raw_text") or "").split())
                if not title:
                    continue
                pkey = (title.lower(), str(prog.get("time_label") or ""), int(prog.get("col_index") or 0))
                if pkey in seen_keys:
                    # Refresh selected flag / sequence on repeated observations.
                    for existing in rec.programs:
                        if not isinstance(existing, dict):
                            continue
                        ex_key = (str(existing.get("title") or "").strip().lower(), str(existing.get("time_label") or ""), int(existing.get("col_index") or 0))
                        if ex_key == pkey:
                            existing["last_seen"] = now
                            existing["observations"] = int(existing.get("observations") or 1) + 1
                            if prog.get("selected"):
                                existing["selected"] = True
                            if prog.get("button_sequence"):
                                existing["button_sequence"] = list(prog.get("button_sequence") or [])
                            break
                    continue
                seen_keys.add(pkey)
                rec.programs.append({
                    "title": title[:160],
                    "raw_text": str(prog.get("raw_text") or "")[:220],
                    "time_label": str(prog.get("time_label") or "")[:40],
                    "row_index": int(prog.get("row_index") or 0),
                    "col_index": int(prog.get("col_index") or 0),
                    "selected": bool(prog.get("selected")),
                    "button_sequence": list(prog.get("button_sequence") or []),
                    "first_seen": now,
                    "last_seen": now,
                    "observations": 1,
                    "source": "guide_grid_v34",
                })
                updated_programs += 1
            rec.programs = rec.programs[-max(1, int(max_programs_per_channel or 24)):]
        return {
            "updated_channels": updated_channels,
            "updated_programs": updated_programs,
            "updated_icons": updated_icons,
            "known_channels": len(self.channels),
            "selected": selected,
            "guide_counts": (guide or {}).get("counts") or {},
        }

    def find_program_candidates(self, query: str = "", channel: Optional[int] = None, limit: int = 20) -> List[Dict[str, Any]]:
        q = " ".join(str(query or "").lower().split())
        out: List[Tuple[float, Dict[str, Any]]] = []
        for ch_key, rec in self.channels.items():
            if channel is not None and str(ch_key).split("-", 1)[0] != str(int(channel)):
                continue
            for prog in rec.programs:
                if not isinstance(prog, dict):
                    continue
                title = str(prog.get("title") or "")
                hay = " ".join([title, rec.channel_code, rec.channel_name, str(ch_key)]).lower()
                score = 0.0
                if q:
                    if q in hay:
                        score += 3.0
                    qt = {x for x in q.split() if len(x) >= 2}
                    ht = set(hay.split())
                    if qt:
                        score += len(qt & ht) / len(qt)
                else:
                    score = 0.5
                if score <= 0:
                    continue
                item = dict(prog)
                item.update({
                    "channel_number": ch_key,
                    "channel_code": rec.channel_code,
                    "channel_name": rec.channel_name or rec.name_guess,
                    "icon_signatures": rec.icon_signatures[-3:],
                    "channel_logo_texts": rec.channel_logo_texts[-3:],
                    "score": round(score, 5),
                })
                out.append((score, item))
        out.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in out[:max(1, int(limit or 20))]]

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



class _DynamicGovernor:
    """v38: Self-tuning performance governor for continuous exploration.

    Watches step latency and system memory, then adjusts:
      - max_depth                    (how deep the frontier searches)
      - graph_match_candidate_limit  (state dedup comparison width)
      - between_key_s                (pacing when the system is slow)

    Hard limits (max_steps, max_states, max_cycles) are 0 (unlimited) in
    continuous mode so they never interrupt exploration. They are only
    non-zero for single-pass/testing scenarios.
    """

    def __init__(self, config: "CrawlerConfig", graph) -> None:
        self._cfg = config
        self._graph = graph
        self._step_times: list = []
        self._window = 10
        self._last_check_step: int = 0
        self._action_start: float = 0.0

    def action_start(self) -> None:
        self._action_start = time.time()

    def action_end(self) -> None:
        if self._action_start:
            self._step_times.append(time.time() - self._action_start)
            if len(self._step_times) > self._window * 3:
                self._step_times = self._step_times[-self._window:]
            self._action_start = 0.0

    def maybe_tune(self, step: int) -> dict:
        cfg = self._cfg
        if not getattr(cfg, "governor_enabled", True):
            return {}
        every = max(1, int(getattr(cfg, "governor_check_every_n_steps", 20) or 20))
        if step - self._last_check_step < every:
            return {}
        self._last_check_step = step
        return self._tune()

    @staticmethod
    def _mem_pct() -> float:
        if _psutil is None:
            return 0.0
        try:
            return float(_psutil.virtual_memory().percent)
        except Exception:
            return 0.0

    @staticmethod
    def _process_mem_mb() -> float:
        if _psutil is None:
            return 0.0
        try:
            return _psutil.Process(os.getpid()).memory_info().rss / 1_048_576
        except Exception:
            return 0.0

    def _avg_step_s(self) -> float:
        recent = self._step_times[-self._window:] if self._step_times else []
        return sum(recent) / len(recent) if recent else 0.0

    def _tune(self) -> dict:
        cfg = self._cfg
        changes: dict = {}
        mem_pct   = self._mem_pct()
        avg_step  = self._avg_step_s()
        node_count = len(self._graph.nodes)

        warn_pct   = float(getattr(cfg, "governor_mem_warn_pct",      72.0))
        crit_pct   = float(getattr(cfg, "governor_mem_critical_pct",  88.0))
        step_target= float(getattr(cfg, "governor_step_target_s",      6.0))
        slow_step  = float(getattr(cfg, "governor_slow_step_s",       14.0))
        d_floor    = int(getattr(cfg,   "governor_depth_floor",         8))
        d_ceil     = int(getattr(cfg,   "governor_depth_ceil",         24))
        m_floor    = int(getattr(cfg,   "governor_match_floor",        60))
        m_ceil     = int(getattr(cfg,   "governor_match_ceil",        600))

        # graph_match_candidate_limit: scale with node count, contract under pressure
        ideal_limit = max(m_floor, min(m_ceil, node_count * 2 + 80))
        if mem_pct > crit_pct:
            ideal_limit = max(m_floor, ideal_limit // 2)
        elif mem_pct > warn_pct:
            ideal_limit = max(m_floor, int(ideal_limit * 0.70))
        cur_limit = int(getattr(cfg, "graph_match_candidate_limit", 240) or 240)
        new_limit = int(cur_limit * 0.75 + ideal_limit * 0.25)
        if abs(new_limit - cur_limit) >= 5:
            cfg.graph_match_candidate_limit = new_limit
            self._graph.match_candidate_limit = new_limit
            changes["graph_match_candidate_limit"] = new_limit

        # max_depth: grow when healthy, shrink under load
        cur_depth = int(getattr(cfg, "max_depth", 18))
        if mem_pct > crit_pct or (avg_step > 0 and avg_step > slow_step):
            new_depth = max(d_floor, cur_depth - 1)
        elif mem_pct < warn_pct * 0.80 and (avg_step == 0 or avg_step < step_target):
            new_depth = min(d_ceil, cur_depth + 1)
        else:
            new_depth = cur_depth
        if new_depth != cur_depth:
            cfg.max_depth = new_depth
            changes["max_depth"] = new_depth

        # between_key_s: slow pacing when system is stressed
        cur_gap = float(getattr(cfg, "between_key_s", 0.0) or 0.0)
        if avg_step > slow_step and cur_gap < 0.5:
            new_gap = min(0.5, cur_gap + 0.05)
            cfg.between_key_s = new_gap
            changes["between_key_s"] = round(new_gap, 3)
        elif avg_step > 0 and avg_step < step_target and cur_gap > 0.0:
            new_gap = max(0.0, cur_gap - 0.02)
            cfg.between_key_s = new_gap
            changes["between_key_s"] = round(new_gap, 3)

        if changes:
            changes["_mem_pct"]   = round(mem_pct, 1)
            changes["_avg_step_s"]= round(avg_step, 2)
            changes["_nodes"]     = node_count
        return changes


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
            region_first_enabled=self.config.region_first_perception_enabled,
            region_first_min_confidence=self.config.region_first_min_confidence,
            region_first_full_ocr_threshold=self.config.region_first_full_ocr_threshold,
        )
        self.probe_extractor = FeatureExtractor(self.data_dir, save_screenshots=False, ocr_enabled=False, region_first_enabled=False)
        # v14 fast extractor saves a screenshot but skips OCR. It is used for
        # quick checkpoints so commands can stay fast while the crawler still
        # remembers visual transitions.
        self.fast_extractor = FeatureExtractor(self.data_dir, save_screenshots=True, ocr_enabled=False, region_first_enabled=False)
        self.graph = NavigationGraph(self.data_dir)
        self.graph.compact_save = bool(getattr(self.config, "compact_json_saves", True))
        self.graph.match_candidate_limit = int(getattr(self.config, "graph_match_candidate_limit", 240) or 0)
        self.brain = CrawlerBrain(self.data_dir)
        self.brain.compact_save = bool(getattr(self.config, "compact_json_saves", True))
        self._save_dirty = False
        self._last_hot_save = 0.0
        self.pattern_recognizer = PatternRecognizer()
        self.sequence_learner = SequenceLearner(self.data_dir)
        self.persistence_tracker = PersistenceTracker(self.data_dir)
        self.recent_actions: Deque[str] = deque(maxlen=12)
        self.events: Deque[CrawlEvent] = deque(maxlen=300)
        self._lock = threading.RLock()
        self._governor = _DynamicGovernor(self.config, self.graph)
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._running = False
        self._run_id: Optional[str] = None
        self._steps = 0
        self._last_state: Optional[str] = None
        self._last_error = ""
        self._last_stop_reason = ""
        self._black_screen_recoveries = 0
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
        elif level.lower() == "debug":
            log.debug("crawler: %s %s", message, data)
        else:
            log.info("crawler: %s %s", message, data)

    def mark_learning_dirty(self) -> None:
        self._save_dirty = True

    def maybe_save_hot_loop(self, force: bool = False) -> bool:
        """Batch expensive JSON writes while the crawler is active.

        Writing a large nav_graph/crawler_brain with pretty JSON after every
        action was one of the main causes of monitor lag.  This keeps data safe
        enough during a run, but defers most disk churn to checkpoints/final save.
        """
        if not self._save_dirty and not force:
            return False
        now = time.time()
        every = max(1, int(getattr(self.config, "hot_loop_save_every_n_actions", 6) or 6))
        interval = max(0.5, float(getattr(self.config, "hot_loop_save_min_interval_s", 8.0) or 8.0))
        due_by_step = self._steps > 0 and (self._steps % every == 0)
        due_by_time = (now - float(getattr(self, "_last_hot_save", 0.0) or 0.0)) >= interval
        if not (force or due_by_step or due_by_time):
            return False
        self.graph.save()
        self.brain.save()
        self._last_hot_save = now
        self._save_dirty = False
        return True

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
                "runtime_policy": self.execution_policy_summary(),
                "performance": {
                    "ui_friendly_mode": bool(getattr(self.config, "ui_friendly_mode", True)),
                    "compact_json_saves": bool(getattr(self.config, "compact_json_saves", True)),
                    "save_dirty": bool(getattr(self, "_save_dirty", False)),
                    "last_hot_save_age_s": round(time.time() - float(getattr(self, "_last_hot_save", 0.0) or time.time()), 3),
                    "hot_loop_save_every_n_actions": int(getattr(self.config, "hot_loop_save_every_n_actions", 6) or 6),
                    "hot_loop_save_min_interval_s": float(getattr(self.config, "hot_loop_save_min_interval_s", 8.0) or 8.0),
                    "graph_match_candidate_limit": int(getattr(self.config, "graph_match_candidate_limit", 240) or 0),
                    "sequence_mining_every_n_steps": int(getattr(self.config, "sequence_mining_every_n_steps", 24) or 24),
                    "governor": {
                        "enabled": bool(getattr(self.config, "governor_enabled", True)),
                        "avg_step_s": round(self._governor._avg_step_s(), 2),
                        "mem_pct": round(self._governor._mem_pct(), 1),
                        "process_mem_mb": round(self._governor._process_mem_mb(), 1),
                        "cur_depth": int(getattr(self.config, "max_depth", 18)),
                        "cur_match_limit": int(getattr(self.config, "graph_match_candidate_limit", 240) or 240),
                    },
                },
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
                    "patterns": self.pattern_recognizer.get_pattern_stats(),
                    "adaptive_thresholds": self.graph.adaptive_thresholds.get_stats(),
                    "sequences": self.sequence_learner.get_stats(),
                    "demonstrations": self.demonstration_stats(),
                    "persistence": self.persistence_tracker.get_stats(),
                },
                "recent_events": [asdict(e) for e in list(self.events)[-40:]],
            }

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
                region_first_enabled=self.config.region_first_perception_enabled,
                region_first_min_confidence=self.config.region_first_min_confidence,
                region_first_full_ocr_threshold=self.config.region_first_full_ocr_threshold,
            )
            self.probe_extractor = FeatureExtractor(self.data_dir, save_screenshots=False, ocr_enabled=False, region_first_enabled=False)
            self.fast_extractor = FeatureExtractor(self.data_dir, save_screenshots=True, ocr_enabled=False, region_first_enabled=False)
            self.graph.compact_save = bool(getattr(self.config, "compact_json_saves", True))
            self.graph.match_candidate_limit = int(getattr(self.config, "graph_match_candidate_limit", 240) or 0)
            self.brain.compact_save = bool(getattr(self.config, "compact_json_saves", True))
            self._save_dirty = False
            self._last_hot_save = time.time()
            fixed = self.brain.sanitize_timing_outliers(float(self.config.timing_outlier_clip_s))
            if fixed:
                log.info("crawler timing outliers clipped: %s", fixed)
            self._stop.clear()
            self._running = True
            self._run_id = f"crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self._started_at = self._now()
            self._finished_at = None
            self._last_error = ""
            self._last_stop_reason = ""
            self._steps = 0
            # v38-fix: Validate anchor sequences before launch to catch bad keys.
            self._validate_anchor_sequences()
            self._thread = threading.Thread(target=self._run_safe, name="AutonomousCrawler", daemon=True)
            self._thread.start()
            self.event("info", "crawl started", run_id=self._run_id)
            return self.status()

    def _validate_anchor_sequences(self) -> None:
        """v38-fix: Sanitise anchor_sequences before a crawl run starts.

        Removes keys that have no SGS mapping and splits accidentally-concatenated
        comma-separated strings into proper sub-lists so reseed_exploration()
        never triggers 'No SGS mapping for <compound_key>' ValueErrors.
        """
        cfg = self.config
        if not getattr(cfg, "anchor_sequences", None):
            return
        try:
            from jamboree.commands import button_id_to_number  # local import avoids circular dep
        except ImportError:
            return
        valid_keys: set = set(button_id_to_number.keys())
        cleaned = []
        for seq in cfg.anchor_sequences:
            clean_seq: list = []
            for key in seq:
                key_lower = str(key).lower().strip()
                # Split comma-separated compound keys stored as a single string.
                parts = [k.strip() for k in key_lower.split(",")] if "," in key_lower else [key_lower]
                for part in parts:
                    if part in valid_keys:
                        clean_seq.append(part)
                    else:
                        self.event("warning", "anchor sequence key removed (no SGS mapping)",
                                   key=part, original_sequence=seq)
            if clean_seq:
                cleaned.append(clean_seq)
        if cleaned != cfg.anchor_sequences:
            self.event("info", "anchor sequences sanitised",
                       before=len(cfg.anchor_sequences), after=len(cleaned))
            cfg.anchor_sequences = cleaned

    def apply_overrides(self, overrides: Dict[str, Any]) -> None:
        allowed = set(CrawlerConfig.__dataclass_fields__.keys())
        list_fields = {"enabled_keys", "start_sequence", "demo_practice_sources"}
        int_list_fields = {"channel_scan_list"}
        bool_fields = {
            "allow_select_on_dangerous_text",
            "ocr_enabled",
            "home_first",
            "governor_enabled",
            "self_explore_enabled",
            "adaptive_timing_enabled",
            "channel_learning_enabled",
            "guide_grid_learning_enabled",
            "min_active_required",
            "continuous_exploration_enabled",
            "reseed_when_idle",
            "fast_known_path_enabled",
            "deep_ocr_on_select",
            "human_observer_enabled",
            "demo_practice_enabled",
            "human_skip_transient_frontier",
            "human_collapse_passive_video",
            "region_first_perception_enabled",
            "region_first_action_bias_enabled",
            "ui_friendly_mode",
            "compact_json_saves",
            "video_black_screen_recovery_enabled",
            "sysdiag_bootstrap_enabled",
        }
        int_fields = {"max_steps", "max_states", "max_depth", "replay_retries", "stable_observations_required", "completion_stable_observations_required", "completion_extra_attempts", "human_loading_max_extra_attempts", "max_cycles", "max_action_attempts_per_state", "transition_sample_limit", "flow_lane_card_w", "flow_lane_card_h", "idle_reseed_every_cycles", "fast_known_action_min_attempts", "deep_ocr_every_n_steps", "video_black_screen_max_recoveries", "hot_loop_save_every_n_actions", "sequence_mining_every_n_steps", "graph_match_candidate_limit", "demo_practice_action_budget_bonus", "demo_practice_every_cycles", "demo_practice_max_edges_per_cycle", "demo_practice_neighbor_actions", "governor_check_every_n_steps", "governor_depth_floor", "governor_depth_ceil", "governor_match_floor", "governor_match_ceil"}
        float_fields = {
            "settle_s", "reset_settle_s", "between_key_s", "state_similarity_threshold",
            "changed_similarity_threshold", "reward_new_state", "reward_new_menu", "reward_new_setting",
            "reward_new_feature", "reward_new_text_tokens", "penalty_noop", "penalty_inactive",
            "penalty_blocked", "min_settle_s", "max_settle_s", "timing_poll_s",
            "stable_similarity_threshold", "channel_digit_gap_s", "channel_tune_settle_s", "guide_grid_min_confidence",
            "continuous_idle_s", "reward_new_edge", "reward_leads_to_unexplored",
            "penalty_repeat_transition", "penalty_same_state_loop", "repeat_reward_floor_for_retry",
            "curiosity_randomness", "fast_known_action_min_reward", "fast_known_action_success_ratio",
            "max_adaptive_observe_s", "timing_outlier_clip_s", "route_replay_gap_s", "route_replay_checkpoint_s", "max_completion_observe_s", "completion_min_observe_s", "completion_quiet_s", "completion_stability_threshold", "completion_extra_wait_on_incomplete_s", "remarkable_timing_multiplier", "remarkable_timing_min_delta_s", "passive_video_similarity_score", "loading_similarity_score", "human_loading_extra_wait_s", "penalty_transient_loading_state", "penalty_passive_video_duplicate", "reward_human_feature_goal", "video_black_screen_recovery_wait_s", "sysdiag_bootstrap_settle_s", "sysdiag_bootstrap_live_settle_s", "region_first_min_confidence", "region_first_full_ocr_threshold", "hot_loop_save_min_interval_s", "demo_practice_frontier_bonus", "demo_practice_action_bonus", "demo_practice_min_confidence",
        }
        for key, value in overrides.items():
            if key not in allowed:
                continue
            if key == "video_black_screen_recovery_sequence":
                if isinstance(value, str):
                    value = [x.strip() for x in re.split(r"[,\s]+", value) if x.strip()]
                elif isinstance(value, list):
                    value = [str(x).strip() for x in value if str(x).strip()]
            elif key == "anchor_sequences":
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
        self.sequence_learner.reset()
        self.persistence_tracker.reset()
        self.recent_actions.clear()
        self.events.clear()
        self.event("info", "navigation graph and learning brain reset")
        return self.status()

    def analyze_guide_current(self, learn: bool = True, max_rows: int = 8) -> Dict[str, Any]:
        frame = self.capture_frame()
        if frame is None or not getattr(frame, "size", 0):
            return {"ok": False, "error": "no frame available", "status": self.status()}
        guide = extract_guide_grid(frame, max_rows=max_rows)
        learned: Dict[str, Any] = {}
        if learn and bool(getattr(self.config, "guide_grid_learning_enabled", True)) and float(guide.get("confidence") or 0.0) >= float(getattr(self.config, "guide_grid_min_confidence", 0.35)):
            try:
                sid = ""
                fp = self.extractor.extract(frame, hint_id="guide_grid", ocr_deep=False)
                sid, _created, _cmp = self.graph.upsert_state(fp, self.config.state_similarity_threshold)
                learned = self.brain.learn_guide_grid(guide, state_id=sid, screenshot=fp.screenshot, max_programs_per_channel=32)
                self.brain.save()
            except Exception as exc:
                learned = {"error": str(exc)}
        return {"ok": True, "guide": guide, "learned": learned, "status": self.status()}

    def find_program_candidates(self, query: str = "", channel: Optional[int] = None, limit: int = 20) -> List[Dict[str, Any]]:
        return self.brain.find_program_candidates(query=query, channel=channel, limit=limit)

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
            self.maybe_save_hot_loop(force=True)
            try:
                self.sequence_learner.save()
                self.persistence_tracker.save()
            except Exception:
                log.debug("unable to save auxiliary learners", exc_info=True)
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


    def bootstrap_sysdiag_then_live(self) -> Dict[str, Any]:
        """Capture Sys Diags/System Info before a crawl/test, then return to Live TV.

        This creates a receiver baseline file in crawler_data so later failures can
        be correlated with model/software/receiver information.
        """
        cfg = self.config
        result: Dict[str, Any] = {
            "ok": False,
            "enabled": bool(getattr(cfg, "sysdiag_bootstrap_enabled", False)),
            "snapshots": [],
        }
        if not result["enabled"]:
            return result

        self.event("info", "sysdiag bootstrap starting", key=cfg.sysdiag_bootstrap_key)
        try:
            self.safe_send(str(cfg.sysdiag_bootstrap_key))
            time.sleep(max(0.5, float(cfg.sysdiag_bootstrap_settle_s)))
            fp = self.capture_fingerprint(hint_prefix="sysdiag", perception="full")
            sid, created, cmp = self.graph.upsert_state(fp, self.config.state_similarity_threshold)
            result.update(
                ok=True,
                state_id=sid,
                created=created,
                similarity=cmp,
                ocr_text=fp.ocr_text[:2000],
                screenshot=fp.screenshot,
                focus=fp.focus,
            )
            # Append persistent sysdiag history.
            path = self.data_dir / "sysdiag_bootstrap_history.json"
            history = []
            if path.exists():
                try:
                    history = json.loads(path.read_text(encoding="utf-8"))
                    if not isinstance(history, list):
                        history = []
                except Exception:
                    history = []
            history.append({
                "ts": self._now(),
                "state_id": sid,
                "screenshot": fp.screenshot,
                "ocr_text": fp.ocr_text[:2000],
                "focus": fp.focus,
            })
            path.write_text(json.dumps(history[-100:], indent=2), encoding="utf-8")
            self.event("info", "sysdiag bootstrap captured", state=sid, screenshot=fp.screenshot)
        except Exception as exc:
            result.update(ok=False, error=str(exc))
            self.event("warning", "sysdiag bootstrap failed", error=str(exc))
        finally:
            try:
                self.safe_send(str(cfg.sysdiag_bootstrap_live_key))
                time.sleep(max(0.5, float(cfg.sysdiag_bootstrap_live_settle_s)))
                result["returned_live"] = True
            except Exception as exc:
                result["returned_live"] = False
                result["live_error"] = str(exc)
        return result

    def exploration_coverage(self) -> Dict[str, Any]:
        return self.brain.coverage_summary(
            state_ids=self.graph.nodes.keys(),
            actions=self.config.enabled_keys,
            max_attempts_per_state=self.config.max_action_attempts_per_state,
        )

    def _human_cues_for_state(self, state_id: str) -> Dict[str, Any]:
        node = self.graph.nodes.get(state_id)
        if not node:
            return {}
        focus = node.representative.focus if isinstance(getattr(node.representative, "focus", {}), dict) else {}
        human = focus.get("human_cues") if isinstance(focus.get("human_cues"), dict) else {}
        return human

    def _human_screen_kind(self, state_id: str) -> str:
        return str(self._human_cues_for_state(state_id).get("screen_kind") or "unknown")

    def _state_is_transient(self, state_id: str) -> bool:
        human = self._human_cues_for_state(state_id)
        return bool(human.get("is_transient")) or self._human_screen_kind(state_id) == "loading_interstitial"

    def _sample_source(self, sample: Dict[str, Any]) -> str:
        if not isinstance(sample, dict):
            return ""
        src = str(sample.get("source") or "")
        if not src:
            timing = sample.get("timing") if isinstance(sample.get("timing"), dict) else {}
            src = str(timing.get("source") or "")
        return src

    def edge_is_demonstrated(self, edge: TransitionEdge) -> bool:
        """True when an edge came from Teacher Mode or monitor/operator learning."""
        sources = {str(x) for x in (getattr(self.config, "demo_practice_sources", []) or [])}
        for sample in list(getattr(edge, "samples", []) or []):
            if not isinstance(sample, dict):
                continue
            if bool(sample.get("operator_auto")):
                return True
            src = self._sample_source(sample)
            if src in sources or src.startswith("manual_") or "operator" in src:
                return True
            rd = sample.get("reward_details") if isinstance(sample.get("reward_details"), dict) else {}
            if rd.get("manual_demonstration_reward") or rd.get("operator_customer_path_weight"):
                return True
        return False

    def demonstration_outgoing_edges(self, state_id: str) -> List[TransitionEdge]:
        if not getattr(self.config, "demo_practice_enabled", True):
            return []
        min_conf = float(getattr(self.config, "demo_practice_min_confidence", 0.15) or 0.15)
        edges = [e for e in self.graph.outgoing_edges(state_id, min_confidence=min_conf) if self.edge_is_demonstrated(e)]
        return sorted(edges, key=lambda e: (e.confidence, e.successes, e.last_seen or ""), reverse=True)

    def demonstration_state_score(self, state_id: str) -> float:
        if not getattr(self.config, "demo_practice_enabled", True):
            return 0.0
        out_edges = self.demonstration_outgoing_edges(state_id)
        in_edges = [e for e in self.graph.incoming_edges(state_id) if self.edge_is_demonstrated(e)]
        if not out_edges and not in_edges:
            return 0.0
        remaining = self.remaining_actions_for_state(state_id) if state_id in self.graph.nodes else []
        bonus = float(getattr(self.config, "demo_practice_frontier_bonus", 18.0) or 18.0)
        score = bonus
        score += min(12.0, 2.0 * len(out_edges) + 1.0 * len(in_edges))
        score += min(8.0, 1.5 * len(remaining))
        # States reached by a human but not fully branched from are very valuable.
        if in_edges and remaining:
            score += bonus * 0.5
        return score

    def demonstration_stats(self) -> Dict[str, Any]:
        edges = [e for e in self.graph.edges.values() if self.edge_is_demonstrated(e)]
        states = set()
        actions: Dict[str, int] = {}
        for e in edges:
            states.add(e.from_state); states.add(e.to_state)
            actions[e.action] = actions.get(e.action, 0) + int(e.successes or 1)
        top_edges = sorted(edges, key=lambda e: (e.confidence, e.successes, e.last_seen or ""), reverse=True)[:12]
        return {
            "enabled": bool(getattr(self.config, "demo_practice_enabled", True)),
            "edge_count": len(edges),
            "state_count": len(states),
            "top_actions": sorted(actions.items(), key=lambda kv: kv[1], reverse=True)[:12],
            "top_edges": [
                {"from": e.from_state, "action": e.action, "to": e.to_state, "confidence": e.confidence, "successes": e.successes, "last_seen": e.last_seen}
                for e in top_edges
            ],
        }

    def demonstration_next_actions(self, state_id: str, actions: List[str]) -> List[str]:
        if not getattr(self.config, "demo_practice_enabled", True) or not actions:
            return actions
        demo_edges = self.demonstration_outgoing_edges(state_id)
        if not demo_edges:
            return actions
        demo_actions: List[str] = []
        for edge in demo_edges:
            expanded = self._action_sequence_for_display(edge.action)
            if edge.action in actions and edge.action not in demo_actions:
                demo_actions.append(edge.action)
            for key in expanded:
                if key in actions and key not in demo_actions:
                    demo_actions.append(key)
        if not demo_actions:
            return actions
        return demo_actions + [a for a in actions if a not in demo_actions]

    def practice_demonstration_paths(self, cycle: int) -> Dict[str, Any]:
        """Rehearse high-value human-demonstrated edges, then branch nearby.

        This is deliberately small per cycle: it proves the path still works and
        makes the destination attractive to the normal frontier, without turning
        the crawler into a brittle macro runner.
        """
        cfg = self.config
        if not getattr(cfg, "demo_practice_enabled", True):
            return {"ok": True, "enabled": False, "practiced": 0}
        every = max(1, int(getattr(cfg, "demo_practice_every_cycles", 1) or 1))
        if cycle % every != 0:
            return {"ok": True, "enabled": True, "skipped": "cycle_interval", "cycle": cycle}
        max_edges = max(0, int(getattr(cfg, "demo_practice_max_edges_per_cycle", 2) or 0))
        if max_edges <= 0:
            return {"ok": True, "enabled": True, "skipped": "max_edges_zero"}
        candidates = [e for e in self.graph.edges.values() if self.edge_is_demonstrated(e) and e.successes > 0 and e.confidence >= float(getattr(cfg, "demo_practice_min_confidence", 0.15) or 0.15)]
        if not candidates:
            return {"ok": True, "enabled": True, "practiced": 0, "reason": "no_demonstrated_edges"}
        def candidate_score(e: TransitionEdge) -> float:
            rem = len(self.remaining_actions_for_state(e.to_state)) if e.to_state in self.graph.nodes else 0
            from_attempts = self.brain.state_action_attempts(e.from_state, e.action)
            return float(e.confidence) * 8.0 + min(10.0, rem * 1.5) + max(0.0, 4.0 - min(4.0, from_attempts * 0.25))
        candidates.sort(key=candidate_score, reverse=True)
        practiced = []
        for edge in candidates[:max_edges]:
            if self._stop.is_set():
                break
            self.event("info", "practicing demonstrated path", from_state=edge.from_state, action=edge.action, expected_to=edge.to_state, confidence=edge.confidence)
            if not self.navigate_to_state(edge.from_state):
                practiced.append({"edge": self.graph.edge_key(edge.from_state, edge.action, edge.to_state), "ok": False, "reason": "navigate_to_from_failed"})
                continue
            result: Dict[str, Any] = {}
            current_from = edge.from_state
            sequence = self._action_sequence_for_display(edge.action) or [edge.action]
            for seq_key in sequence:
                result = self.try_action(current_from, seq_key)
                current_from = str(result.get("to_state") or current_from)
                if self._stop.is_set():
                    break
            actual = str(result.get("to_state") or current_from or "")
            ok = bool(actual)
            if actual == edge.to_state:
                self.sequence_learner.record_suggestion_outcome(True)
            branch_state = actual or edge.to_state
            branch_results = []
            neighbor_limit = max(0, int(getattr(cfg, "demo_practice_neighbor_actions", 3) or 0))
            if neighbor_limit and branch_state in self.graph.nodes:
                actions = self.remaining_actions_for_state(branch_state)
                actions = self.apply_pattern_action_order(branch_state, actions)
                demo_keys = set(self._action_sequence_for_display(edge.action) + [edge.action])
                actions = [a for a in actions if a not in demo_keys][:neighbor_limit]
                for a in actions:
                    if self._stop.is_set():
                        break
                    branch_results.append(self.try_action(branch_state, a))
                    self.mark_learning_dirty()
            practiced.append({"from": edge.from_state, "action": edge.action, "expected_to": edge.to_state, "actual_to": actual, "ok": ok, "branches": len(branch_results)})
            self.mark_learning_dirty()
            self.maybe_save_hot_loop()
        if practiced:
            self.event("info", "demonstration practice complete", practiced=practiced[:6])
        return {"ok": True, "enabled": True, "practiced": len(practiced), "items": practiced}

    def action_budget_for_state(self, state_id: str, action: str) -> int:
        """v19: give human-important surfaces more exploration budget.

        The old crawler could mark a Home tab, Guide grid, or tile carousel
        saturated after two tries. A person would keep moving horizontally/vertically
        through tabs/tiles/guide cells because that is where features live.
        """
        base = max(1, int(self.config.max_action_attempts_per_state))
        if getattr(self.config, "demo_practice_enabled", True):
            for edge in self.demonstration_outgoing_edges(state_id):
                if str(edge.action) == str(action) or str(action) in self._action_sequence_for_display(str(edge.action)):
                    base += max(0, int(getattr(self.config, "demo_practice_action_budget_bonus", 3) or 0))
                    break
        node = self.graph.nodes.get(state_id)
        if not node:
            return base
        focus = node.representative.focus if isinstance(getattr(node.representative, "focus", {}), dict) else {}
        text = " ".join([
            str(node.label or ""),
            str(node.representative.ocr_text or ""),
            str(focus.get("page_name") or ""),
            str(focus.get("block_title") or ""),
            str(focus.get("screen_title") or ""),
            str(focus.get("menu_title") or ""),
            str(focus.get("human_label") or ""),
        ]).lower()
        action_l = str(action).lower()
        if any(k in text for k in ["guide", "all channels", "schedule", "time", "channel"]):
            if action_l in {"up", "down", "left", "right", "info", "select", "ch_up", "ch_down"}:
                return max(base, 5)
        if any(k in text for k in ["home", "shows", "sports", "movies", "on demand", "search", "apps", "dvr"]):
            if action_l in {"left", "right", "up", "down", "select", "info", "options"}:
                return max(base, 4)
        if any(k in text for k in ["record", "recording", "timer", "reminder", "dvr"]):
            if action_l in {"select", "options", "info", "dvr", "play", "pauseplay", "back"}:
                return max(base, 4)
        if any(k in text for k in ["ppv", "pay per view", "rent", "order", "purchase"]):
            if action_l in {"info", "options", "back", "home"}:
                return max(base, 4)
        return base

    def remaining_actions_for_state(self, state_id: str) -> List[str]:
        cfg = self.config
        # v18: humans do not explore loading screens; they wait for them to finish.
        if getattr(cfg, "human_skip_transient_frontier", True) and self._state_is_transient(state_id):
            return []
        allowed_actions = list(cfg.enabled_keys)
        kind = self._human_screen_kind(state_id)
        if getattr(cfg, "human_observer_enabled", True):
            if kind == "passive_video":
                # Avoid learning thousands of arrow-key outcomes from changing video.
                preferred = {"guide", "info", "options", "recall", "home", "live", "input", "ch_up", "ch_down", "back"}
                filtered = [a for a in allowed_actions if str(a).lower() in preferred or str(a).isdigit()]
                if filtered:
                    allowed_actions = filtered
            elif kind == "purchase_or_ppv":
                # Read/escape only unless operator explicitly drives it in Teacher Mode.
                preferred = {"info", "back", "home", "options"}
                allowed_actions = [a for a in allowed_actions if str(a).lower() in preferred]
            elif kind == "pin_prompt":
                preferred = {"back", "home"}
                allowed_actions = [a for a in allowed_actions if str(a).lower() in preferred]
        remaining: List[str] = []
        for action in allowed_actions:
            attempts = self.brain.state_action_attempts(state_id, action)
            avg_reward = self.brain.state_action_avg_reward(state_id, action)
            # New or under-sampled actions are preferred. A repeatedly useful action
            # may be retried even after saturation because it can be a hallway to new rooms.
            budget = self.action_budget_for_state(state_id, action)
            if attempts < budget or avg_reward >= cfg.repeat_reward_floor_for_retry:
                remaining.append(action)
        return remaining

    def _pattern_for_state(self, state_id: str) -> str:
        node = self.graph.nodes.get(state_id)
        if not node:
            return "unknown"
        pattern = str(getattr(node.representative, "ui_pattern", "unknown") or "unknown")
        if pattern == "unknown":
            focus = node.representative.focus if isinstance(getattr(node.representative, "focus", {}), dict) else {}
            rc = focus.get("region_first") if isinstance(focus.get("region_first"), dict) else {}
            family = str(rc.get("screen_family") or "unknown")
            pattern = pattern_from_region_family(family)
        return pattern

    def apply_pattern_action_order(self, state_id: str, actions: List[str]) -> List[str]:
        """v15/v18: reorder actions according to UI pattern, sequence hints, and human-observer cues."""
        if not actions:
            return actions
        human = self._human_cues_for_state(state_id)
        if human and getattr(self.config, "human_observer_enabled", True):
            rec = [str(a).lower() for a in human.get("recommended_actions", []) or []]
            avoid = {str(a).lower() for a in human.get("avoid_actions", []) or []}
            # Map human-level recommendations to concrete remote keys.
            rec_map = {
                "wait": [],
                "read_focus": [],
                "read_title_price": ["info", "back"],
                "info": ["info"],
                "guide": ["guide"],
                "options": ["options"],
                "recall": ["recall"],
                "home": ["home"],
                "back": ["back"],
                "select": ["select"],
                "up": ["up"], "down": ["down"], "left": ["left"], "right": ["right"],
                "ch_up": ["ch_up"], "ch_down": ["ch_down"],
            }
            priority: List[str] = []
            for r in rec:
                priority.extend(rec_map.get(r, [r]))
            if priority:
                rank = {a: i for i, a in enumerate(priority)}
                actions = sorted(actions, key=lambda a: (rank.get(str(a).lower(), 99), actions.index(a)))
            if avoid:
                actions = [a for a in actions if str(a).lower() not in avoid]
                if not actions:
                    actions = [a for a in self.config.enabled_keys if str(a).lower() in {"back", "home", "info"}]
        if getattr(self.config, "region_first_action_bias_enabled", True):
            node = self.graph.nodes.get(state_id)
            focus = node.representative.focus if node and isinstance(getattr(node.representative, "focus", {}), dict) else {}
            rc = focus.get("region_first") if isinstance(focus.get("region_first"), dict) else {}
            suggested = [str(a).lower() for a in rc.get("suggested_actions", [])] if rc else []
            avoid2 = {str(a).lower() for a in rc.get("avoid_actions", [])} if rc else set()
            if suggested:
                rank2 = {a: i for i, a in enumerate(suggested)}
                actions = sorted(actions, key=lambda a: (rank2.get(str(a).lower(), 99), actions.index(a)))
            if avoid2:
                actions = [a for a in actions if str(a).lower() not in avoid2] or actions
        pattern = self._pattern_for_state(state_id)
        priority: List[str]
        if pattern == "grid_menu":
            # v19: grid surfaces include guide cells, Home top tabs, tile carousels,
            # OnDemand shelves, DVR rows, and channel lists. Explore both axes
            # before leaving; read info/options before risky select.
            priority = ["left", "right", "up", "down", "info", "options", "select", "ch_up", "ch_down", "guide", "dvr", "back", "home"]
        elif pattern in {"linear_menu", "form", "pin_prompt"}:
            priority = ["down", "up", "right", "left", "info", "options", "select", "back", "home"]
        elif pattern == "video_player":
            priority = ["guide", "info", "options", "back", "home", "live", "recall", "up", "down", "left", "right"]
        elif pattern == "info_card":
            priority = ["back", "info", "select", "down", "up", "left", "right", "home"]
        else:
            priority = []
        rank = {a: i for i, a in enumerate(priority)}
        ordered = sorted(actions, key=lambda a: (rank.get(str(a).lower(), 99), actions.index(a)))
        ordered = self.demonstration_next_actions(state_id, ordered)
        suggestion = self.sequence_learner.suggest_next_action(list(self.recent_actions))
        if suggestion:
            suggested, conf = suggestion
            if suggested in ordered and conf >= 0.20:
                ordered = [suggested] + [a for a in ordered if a != suggested]
                self.event("info", "sequence learner suggested next action", action=suggested, confidence=round(float(conf), 3), recent=list(self.recent_actions))
        return ordered

    def build_frontier(self) -> Deque[Tuple[str, int, float]]:
        depths = self.graph.depths_from_root()
        if self.graph.root_state and self.graph.root_state not in depths:
            depths[self.graph.root_state] = 0
        candidates: List[Tuple[float, str, int]] = []
        cfg = self.config
        for sid in self.graph.nodes:
            depth = depths.get(sid, 99)
            # v38-fix: In continuous mode, treat unreachable/orphaned nodes as
            # depth=max_depth (low priority) instead of filtering them out entirely.
            # Without this, disconnected subgraphs are never visited after a
            # root-change or crash, causing the frontier to collapse to 1 node.
            if depth > cfg.max_depth:
                if cfg.continuous_exploration_enabled:
                    depth = cfg.max_depth
                else:
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
            demo_score = self.demonstration_state_score(sid)
            score = len(remaining) * 2.0 + self.state_confidence(sid) + max(-2.0, min(5.0, avg_reward)) + demo_score - depth * 0.12
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
            # v38-fix: Invalid keys in anchor_sequences must not crash the crawler.
            try:
                self.safe_send(key)
            except (ValueError, KeyError) as exc:
                self.event("warning", "reseed skipped invalid key", key=key, error=str(exc))
                continue
            time.sleep(self.brain.expected_settle_s(key, cfg))
        try:
            sid, created, cmp = self.current_state_id()
            self.graph.root_state = self.graph.root_state or sid
            # v38-fix: Create a synthetic edge root→reseeded_state so the new
            # state becomes reachable in depths_from_root() on the next cycle.
            # This bridges the gap caused by graph fragmentation after restarts.
            if sid and sid != self.graph.root_state and sid in self.graph.nodes:
                _synthetic_action = f"__reseed_{cycle % 100}"
                self.graph.record_edge(
                    self.graph.root_state, _synthetic_action, sid,
                    changed=True, success=True, confidence=0.3,
                    sample={"source": "reseed_synthetic", "cycle": cycle},
                )
            self.graph.save()
            # v16-fix: Force the reseeded state back into the frontier.
            # Without this, states already saturated at max_action_attempts_per_state
            # are permanently excluded from build_frontier() even after a reseed,
            # causing continuous reseeding with zero actual exploration.
            if sid and sid in self.graph.nodes:
                for _reseed_action in self.config.enabled_keys:
                    _key = self.brain.state_action_key(sid, _reseed_action)
                    _stat = self.brain.state_actions.get(_key)
                    if _stat and _stat.attempts >= self.config.max_action_attempts_per_state:
                        _stat.attempts = max(0, _stat.attempts - 1)
            self.event("info", "reseed classified screen", state=sid, created=created, similarity=cmp)
            return sid
        except Exception as exc:
            self.event("warning", "reseed classify failed", error=str(exc))
            return None

    def run(self) -> None:
        cfg = self.config
        self.restore_start_context()
        if getattr(cfg, "sysdiag_bootstrap_enabled", False):
            self.bootstrap_sysdiag_then_live()
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
                    node = self.graph.nodes.get(state_id)
                    self.persistence_tracker.mark_navigation_failed(
                        state_id,
                        route=[],
                        reason="unable_to_restore_frontier_state",
                        context={"label": node.label if node else state_id, "pattern": self._pattern_for_state(state_id), "depth": depth},
                    )
                    self.event("warning", "unable to restore target state; skipping", state=state_id)
                    continue
                else:
                    self.persistence_tracker.mark_navigation_succeeded(state_id)

                actions = self.brain.order_actions(remaining_actions) if cfg.self_explore_enabled else list(remaining_actions)
                actions = self.apply_pattern_action_order(state_id, actions)
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
                    budget = self.action_budget_for_state(state_id, action)
                    if attempts >= max(1, budget) and avg_reward < cfg.repeat_reward_floor_for_retry:
                        continue
                    result = self.try_action(state_id, action)
                    reward = float(result.get("reward", 0.0))
                    to_state = result.get("to_state")
                    # New states, or known states with fresh remaining actions, become next frontier.
                    if to_state and to_state in self.graph.nodes and to_state != state_id:
                        rem = self.remaining_actions_for_state(to_state)
                        if rem and depth + 1 <= cfg.max_depth:
                            frontier.append((to_state, depth + 1, reward))
                    self.mark_learning_dirty()
                    self.maybe_save_hot_loop()
            if cfg.continuous_exploration_enabled and getattr(cfg, "demo_practice_enabled", True):
                try:
                    self.practice_demonstration_paths(cycles)
                except Exception as exc:
                    self.event("warning", "demonstration practice failed", error=str(exc))
            cycles += 1
            if not cfg.continuous_exploration_enabled:
                self._set_stop_reason("single_pass_complete")
                break
            # In continuous mode, re-seed after each pass. This prevents the
            # worker from looking idle just because the current root was swept.
            # v38-fix: Wrap in try/except — a bad key must not kill the main loop.
            if cfg.reseed_when_idle:
                try:
                    self.reseed_exploration(cycles)
                except Exception as _reseed_exc:
                    self.event("warning", "reseed failed in main loop", error=str(_reseed_exc))
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
            if self._stop.is_set() or (cfg.max_steps and self._steps >= cfg.max_steps):
                break
            if not self.navigate_to_state(root_id):
                self.event("warning", "unable to restore root before channel scan", channel=ch)
            result = self.try_action(root_id, f"CH_{ch}", force_settle_s=cfg.channel_tune_settle_s)
            self.event("info", "channel scan result", channel=ch, result=result)
            # Return to the configured start/root context before the next channel.
            self.restore_start_context()

    def execution_policy_summary(self) -> Dict[str, Any]:
        cfg = self.config
        return {
            "execution_mode": cfg.execution_mode,
            "fast_known_path_enabled": cfg.fast_known_path_enabled,
            "fast_known_action_min_attempts": cfg.fast_known_action_min_attempts,
            "fast_known_action_min_reward": cfg.fast_known_action_min_reward,
            "deep_ocr_every_n_steps": cfg.deep_ocr_every_n_steps,
            "max_adaptive_observe_s": cfg.max_adaptive_observe_s,
            "timing_outlier_clip_s": cfg.timing_outlier_clip_s,
            "route_replay_gap_s": cfg.route_replay_gap_s,
        }

    def state_action_is_confident(self, state_id: str, action: str) -> bool:
        cfg = self.config
        stat = self.brain.state_actions.get(f"{state_id}|{action}")
        if not stat or stat.attempts < max(1, cfg.fast_known_action_min_attempts):
            return False
        success_ratio = stat.successes / max(1, stat.attempts)
        return success_ratio >= cfg.fast_known_action_success_ratio and stat.avg_reward >= cfg.fast_known_action_min_reward

    def should_use_fast_perception(self, state_id: str, action: str) -> bool:
        cfg = self.config
        mode = str(cfg.execution_mode or "balanced").lower()
        if mode == "deep":
            return False
        if mode == "tunnel":
            return str(action).lower() != "select" or not cfg.deep_ocr_on_select
        if self._steps > 0 and cfg.deep_ocr_every_n_steps > 0 and self._steps % cfg.deep_ocr_every_n_steps == 0:
            return False
        if str(action).lower() == "select" and cfg.deep_ocr_on_select:
            return False
        return self.state_action_is_confident(state_id, action)

    def _status_is_acceptable_video(self, status: Dict[str, Any]) -> bool:
        """v19: color bars/static UI count as active input; black does not."""
        if not self.config.min_active_required:
            return True
        if bool(status.get("active", False)):
            return True
        return str(status.get("signal_class") or "").lower() in {
            "color_bars",
            "active_video",
            "active_static_ui",
        }

    def recover_black_screen(self, reason: str = "black_screen") -> Dict[str, Any]:
        """Try to recover an STB black-screen condition with CH+/CH-/Live.

        The capture input itself can be active while the STB renders black. A human
        would note the fault and try another channel before declaring the input dead.
        """
        cfg = self.config
        if not getattr(cfg, "video_black_screen_recovery_enabled", True):
            return {"ok": False, "skipped": True, "reason": "recovery_disabled"}
        if self._black_screen_recoveries >= int(getattr(cfg, "video_black_screen_max_recoveries", 3)):
            return {"ok": False, "skipped": True, "reason": "max_recoveries_reached", "count": self._black_screen_recoveries}

        self._black_screen_recoveries += 1
        sequence = list(getattr(cfg, "video_black_screen_recovery_sequence", []) or ["ch_up", "ch_down", "live"])
        self.event(
            "warning",
            "black screen detected; attempting channel recovery",
            reason=reason,
            sequence=sequence,
            recovery_count=self._black_screen_recoveries,
        )
        results = []
        for key in sequence:
            if self._stop.is_set():
                break
            try:
                results.append({"key": key, "result": self.fast_send(key)})
            except Exception as exc:
                results.append({"key": key, "error": str(exc)})
            time.sleep(max(0.1, float(getattr(cfg, "video_black_screen_recovery_wait_s", 1.6))))
        return {"ok": True, "sequence": sequence, "results": results, "count": self._black_screen_recoveries}

    def wait_for_good_frame(self, timeout_s: float = 8.0) -> Tuple[np.ndarray, Dict[str, Any]]:
        deadline = time.time() + timeout_s
        last_status: Dict[str, Any] = {}
        black_seen = 0
        while time.time() < deadline:
            frame = self.capture_frame()
            status = self.capture_status()
            last_status = status
            if frame is not None and frame.size:
                if self._status_is_acceptable_video(status):
                    # Successful active/color/static frame resets the local black counter.
                    return frame, status
                if str(status.get("signal_class") or "").lower() == "black_screen" or status.get("likely_black_screen"):
                    black_seen += 1
                    if black_seen >= 2:
                        self.recover_black_screen(reason="wait_for_good_frame")
                        black_seen = 0
                        # Extend the deadline a little after active recovery.
                        deadline = max(deadline, time.time() + max(1.5, float(getattr(self.config, "video_black_screen_recovery_wait_s", 1.6))))
            time.sleep(0.15)
        raise RuntimeError(f"no active video frame available; last_status={last_status}")
    def capture_fingerprint(self, hint_prefix: str = "screen", perception: str = "full") -> ScreenFingerprint:
        frame, status = self.wait_for_good_frame()
        hint = f"{hint_prefix}_{uuid.uuid4().hex[:10]}"
        extractor = self.fast_extractor if str(perception).lower() in {"fast", "visual", "noocr"} else self.extractor
        fp = extractor.extract(frame, hint_id=hint)
        # Preserve capture status in the OCR text if there is no OCR, useful for labels/debugging.
        if not fp.ocr_text:
            fp.ocr_text = ""
        try:
            pc = self.pattern_recognizer.classify_screen(fp, fp.focus)
            pattern = getattr(pc, "pattern", None)
            fp.ui_pattern = getattr(pattern, "value", str(pattern or "unknown"))
            fp.pattern_confidence = float(getattr(pc, "confidence", 0.0) or 0.0)
            fp.pattern_reasons = list(getattr(pc, "reasons", []) or [])[:10]
            rc = fp.focus.get("region_first") if isinstance(getattr(fp, "focus", {}), dict) and isinstance(fp.focus.get("region_first"), dict) else {}
            region_pattern = pattern_from_region_family(str(rc.get("screen_family") or ""))
            if region_pattern != "unknown" and (fp.ui_pattern == "unknown" or fp.pattern_confidence < 0.35):
                fp.ui_pattern = region_pattern
                fp.pattern_confidence = max(fp.pattern_confidence, float(rc.get("confidence") or 0.0))
                fp.pattern_reasons = (fp.pattern_reasons or []) + [f"region_first:{rc.get('screen_family')}"]
        except Exception:
            log.debug("pattern classification failed", exc_info=True)
        return fp

    def safe_send(self, key: str) -> Dict[str, Any]:
        key = str(key).strip()
        # v38-fix: Guard against accidentally-concatenated multi-key strings
        # (e.g. "back,back,info,guide" stored in learned_sequences). Split and
        # send each sub-key individually so the SGS lookup never sees a compound.
        if "," in key:
            result: Dict[str, Any] = {"ok": False, "error": "empty sequence"}
            for sub_key in key.split(","):
                sub_key = sub_key.strip()
                if sub_key:
                    result = self.safe_send(sub_key)
            return result
        self.event("debug", "send key", key=key)
        result = self.send_key(key)
        time.sleep(self.config.between_key_s)
        return result

    def fast_send(self, key: str) -> Dict[str, Any]:
        """Send without the crawler's extra inter-key sleep. Used for replaying
        already-learned paths and timed sequences."""
        key = str(key).strip()
        self.event("debug", "fast send key", key=key)
        return self.send_key(key)

    def quick_fingerprint(self, hint_prefix: str = "probe") -> ScreenFingerprint:
        frame, _ = self.wait_for_good_frame(timeout_s=max(1.0, self.config.timing_poll_s * 4))
        return self.probe_extractor.extract(frame, hint_id=f"{hint_prefix}_{uuid.uuid4().hex[:8]}")

    @staticmethod
    def _action_is_menu_like(action: str) -> bool:
        a = str(action or "").lower()
        return a in {
            "guide", "home", "dvr", "apps", "settings", "options", "info", "input",
            "select", "back", "recall", "menu", "live", "ddiamond", "diamond"
        }

    @staticmethod
    def _text_has_final_modal_or_menu(text: str) -> bool:
        low = str(text or "").lower()
        return bool(re.search(
            r"\b(attention|ok|cancel|settings|options|guide|search|dvr|parental|diagnostics|"
            r"locked|channels|tv viewing|program|episode|live tv|home|on demand|apps)\b",
            low,
        ))

    @staticmethod
    def _text_has_loading(text: str) -> bool:
        return bool(re.search(r"\b(loading|please wait|processing|retrieving|starting|connecting|refreshing)\b", str(text or ""), re.I))

    def fingerprint_looks_incomplete(self, fp: ScreenFingerprint, action: str) -> Tuple[bool, List[str]]:
        """Detect snapshots that look like the first flicker of a transition rather
        than a completed screen.

        This deliberately stays conservative: video playback screens may have no focus
        and little OCR, but menu-like actions should usually settle into a focusable UI,
        a titled modal, or recognizable page/menu text.
        """
        reasons: List[str] = []
        text = fp.ocr_text or ""
        focus = fp.focus if isinstance(getattr(fp, "focus", {}), dict) else {}
        human = focus.get("human_cues") if isinstance(focus.get("human_cues"), dict) else {}
        if human.get("screen_kind") == "loading_interstitial" or human.get("is_transient"):
            reasons.append("human_loading_interstitial")
        if self._text_has_loading(text):
            reasons.append("loading_text")
        if focus.get("loading"):
            reasons.append("focus_loading_flag")
        # A high-confidence focus usually means the UI has settled, unless the
        # human observer identified the whole screen as a loading interstitial.
        if focus.get("found") and "human_loading_interstitial" not in reasons:
            return (bool(reasons), reasons)
        # A final Attention/OK modal may not have red focus, but it is a final state.
        if self._text_has_final_modal_or_menu(text):
            return (bool(reasons), reasons)
        # Dark/low-information frames immediately after menu-like actions are often
        # fade/spinner/interstitial frames.  Do not learn them as the destination.
        token_count = len(getattr(fp, "ocr_tokens", []) or [])
        if self._action_is_menu_like(action) and token_count < 6:
            if fp.brightness < 42 or fp.entropy < 3.2 or fp.edge_density < 0.018:
                reasons.append("low_information_menu_transition")
        if self._action_is_menu_like(action) and token_count < 3 and fp.entropy < 4.0:
            reasons.append("weak_menu_ocr_no_focus")
        return (bool(reasons), reasons)

    def wait_after_action(
        self,
        action: str,
        before_fp: ScreenFingerprint,
        force_settle_s: Optional[float] = None,
        perception: str = "full",
    ) -> Tuple[ScreenFingerprint, float, Dict[str, Any]]:
        cfg = self.config
        if force_settle_s is not None:
            start = time.time()
            time.sleep(max(cfg.min_settle_s, float(force_settle_s)))
            after = self.capture_fingerprint(hint_prefix="after", perception=perception)
            complete_s = time.time() - start
            phase = self.brain.update_timing_phase(
                action,
                start_s=complete_s,
                complete_s=complete_s,
                stable_s=0.0,
                cfg=cfg,
                flags=["forced_settle"],
            )
            return after, complete_s, {
                "mode": "forced",
                "perception": perception,
                "action_start_s": round(complete_s, 3),
                "action_complete_s": round(complete_s, 3),
                "response_s": round(complete_s, 3),
                "completion_s": round(complete_s, 3),
                "phase_learning": phase,
            }
        if not cfg.adaptive_timing_enabled:
            start = time.time()
            sleep_s = min(cfg.settle_s, cfg.max_completion_observe_s)
            time.sleep(sleep_s)
            after = self.capture_fingerprint(hint_prefix="after", perception=perception)
            complete_s = time.time() - start
            phase = self.brain.update_timing_phase(action, complete_s, complete_s, 0.0, cfg=cfg, flags=["fixed_settle"])
            return after, complete_s, {
                "mode": "fixed",
                "perception": perception,
                "action_start_s": round(complete_s, 3),
                "action_complete_s": round(complete_s, 3),
                "response_s": round(complete_s, 3),
                "completion_s": round(complete_s, 3),
                "phase_learning": phase,
            }

        expected_start = self.brain.expected_start_s(action, cfg)
        expected_complete = self.brain.expected_settle_s(action, cfg)
        start = time.time()
        # Completion timeout is intentionally larger than old max_adaptive_observe_s.
        # We still use quick visual fingerprints during the wait, so this does not
        # introduce OCR stalls between button presses.
        observe_cap = max(
            cfg.min_settle_s,
            min(float(cfg.max_completion_observe_s), max(expected_complete * 1.55 + 0.35, cfg.max_adaptive_observe_s)),
        )
        deadline = start + observe_cap
        min_complete_time = start + max(float(cfg.completion_min_observe_s), min(expected_start + cfg.completion_quiet_s, observe_cap))
        first_change_s: Optional[float] = None
        completion_s: Optional[float] = None
        stable_count = 0
        stable_window_s = 0.0
        previous: Optional[ScreenFingerprint] = None
        last: Optional[ScreenFingerprint] = None
        flags: List[str] = []
        debug: Dict[str, Any] = {
            "mode": "phased_adaptive",
            "expected_start_s": round(expected_start, 3),
            "expected_complete_s": round(expected_complete, 3),
            "observe_cap_s": round(observe_cap, 3),
            "samples": [],
        }

        while time.time() < deadline:
            time.sleep(max(0.05, cfg.timing_poll_s))
            try:
                current = self.quick_fingerprint("timing")
            except Exception as exc:
                flags.append("quick_fingerprint_failed")
                debug["last_quick_error"] = str(exc)
                continue
            now = time.time()
            last = current
            before_cmp = SimilarityModel.compare(before_fp, current)
            prev_cmp = SimilarityModel.compare(previous, current) if previous else {"score": 0.0}
            sample = {
                "t": round(now - start, 3),
                "before": before_cmp["score"],
                "previous": prev_cmp["score"],
                "brightness": current.brightness,
                "entropy": current.entropy,
                "edge_density": current.edge_density,
            }
            debug["samples"].append(sample)
            debug["samples"] = debug["samples"][-12:]
            if first_change_s is None and before_cmp["score"] < cfg.changed_similarity_threshold:
                first_change_s = now - start
            if previous and prev_cmp["score"] >= cfg.completion_stability_threshold:
                stable_count += 1
                stable_window_s += max(0.0, float(cfg.timing_poll_s))
            else:
                stable_count = 0
                stable_window_s = 0.0
            previous = current
            if first_change_s is not None and now >= min_complete_time and stable_count >= max(1, int(cfg.completion_stable_observations_required)):
                completion_s = now - start
                break

        if first_change_s is None:
            # No visible movement. This can be a legitimate no-op, so completion is
            # the observation duration rather than a fake large response.
            first_change_s = 0.0
            flags.append("no_visible_start")
        if completion_s is None:
            completion_s = time.time() - start
            flags.append("completion_uncertain")

        # Full/fast final perception only happens after the visual completion gate.
        after_fp = self.capture_fingerprint(hint_prefix="after", perception=perception) if last is not None else self.capture_fingerprint(hint_prefix="after", perception=perception)

        # If final capture still looks like a transient menu-loading frame, keep
        # watching briefly and recapture.  This is the direct fix for learning the
        # first half of a menu transition as the final destination.
        recovery: List[Dict[str, Any]] = []
        extra_attempts = max(0, int(cfg.completion_extra_attempts))
        if getattr(cfg, "human_observer_enabled", True):
            extra_attempts = max(extra_attempts, int(getattr(cfg, "human_loading_max_extra_attempts", extra_attempts)))
        for attempt in range(extra_attempts):
            incomplete, reasons = self.fingerprint_looks_incomplete(after_fp, action)
            if not incomplete:
                break
            flags.extend([r for r in reasons if r not in flags])
            wait_s = max(0.10, float(cfg.completion_extra_wait_on_incomplete_s))
            if "human_loading_interstitial" in reasons:
                wait_s = max(wait_s, float(getattr(cfg, "human_loading_extra_wait_s", wait_s)))
            time.sleep(wait_s)
            after_fp = self.capture_fingerprint(hint_prefix="after_complete", perception=perception)
            completion_s = time.time() - start
            recovery.append({"attempt": attempt + 1, "wait_s": wait_s, "reasons": reasons, "completion_s": round(completion_s, 3)})
        if recovery:
            flags.append("post_completion_recapture")

        phase = self.brain.update_timing_phase(
            action,
            start_s=first_change_s,
            complete_s=completion_s,
            stable_s=stable_window_s,
            cfg=cfg,
            flags=flags,
        )
        debug.update({
            "perception": perception,
            "action_start_s": round(float(first_change_s), 3),
            "action_complete_s": round(float(completion_s), 3),
            "stable_window_s": round(float(stable_window_s), 3),
            # Legacy field names remain, but response is now explicitly the start.
            "response_s": round(float(first_change_s), 3),
            "raw_response_s": round(float(first_change_s), 3),
            "completion_s": round(float(completion_s), 3),
            "raw_completion_s": round(float(completion_s), 3),
            "stable_count": stable_count,
            "flags": list(dict.fromkeys(flags))[:16],
            "recovery": recovery,
            "phase_learning": phase,
        })
        if phase.get("remarkable"):
            self.event("warning", "remarkable action timing", action=action, timing=debug)
        return after_fp, float(completion_s), debug

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
        # v38-fix: In continuous mode, skip the full retry loop for nodes that have
        # no path from root — each retry costs restore_start_context + capture (~5s).
        # With 900+ orphaned nodes this was burning hours before any useful work.
        # Instead we do a fast O(1) path check and opportunistically accept the
        # node if it happens to already be on-screen right now.
        if cfg.continuous_exploration_enabled and target_state != self.graph.root_state:
            has_path = self.graph.shortest_path(self.graph.root_state, target_state) is not None
            if not has_path:
                try:
                    sid, _, _ = self.current_state_id()
                    if sid == target_state:
                        return True
                except Exception:
                    pass
                return False
        for attempt in range(max(1, cfg.replay_retries)):
            self.restore_start_context()
            sid, _, cmp = self.current_state_id()
            if target_state == sid:
                return True
            path = self.graph.shortest_path(sid, target_state) or self.graph.shortest_path(self.graph.root_state, target_state)
            if not path:
                if target_state != self.graph.root_state:
                    node = self.graph.nodes.get(target_state)
                    self.persistence_tracker.mark_navigation_failed(
                        target_state,
                        route=[],
                        reason="no_learned_route_to_state",
                        context={"label": node.label if node else target_state, "pattern": self._pattern_for_state(target_state)},
                    )
                return target_state == self.graph.root_state
            self.event("info", "replaying path", target=target_state, path=path, attempt=attempt + 1, fast=cfg.fast_known_path_enabled)
            if cfg.fast_known_path_enabled and len(path) > 1:
                # Known path replay is command execution, not exploration. Press quickly,
                # then verify once at the checkpoint so screen timeouts do not eat us.
                for key in path:
                    self.fast_send(key)
                    time.sleep(max(0.02, float(cfg.route_replay_gap_s)))
                time.sleep(max(0.05, float(cfg.route_replay_checkpoint_s)))
            else:
                for key in path:
                    self.safe_send(key)
                    time.sleep(min(self.brain.expected_settle_s(key, cfg), cfg.max_adaptive_observe_s))
            sid, _, cmp = self.current_state_id()
            if sid == target_state or cmp.get("score", 0.0) >= cfg.state_similarity_threshold:
                return True
        self.persistence_tracker.mark_navigation_failed(target_state, route=[], reason="replay_verification_failed", context={"pattern": self._pattern_for_state(target_state)})
        return False

    def try_action(self, from_state: str, action: str, force_settle_s: Optional[float] = None) -> Dict[str, Any]:
        cfg = self.config
        self._steps += 1
        action_norm = str(action).strip()
        action_lower = action_norm.lower()
        self._governor.action_start()
        self.event("info", "try action", from_state=from_state, action=action_norm, step=self._steps)

        # For confident known state/actions, use a visual-only pre-check so command
        # pacing remains quick. Risky SELECT still forces deep OCR for safety.
        fast_pre = self.should_use_fast_perception(from_state, action_norm)
        before_fp = self.capture_fingerprint(hint_prefix="before", perception="fast" if fast_pre else "full")
        before_id, _, _ = self.graph.upsert_state(before_fp, cfg.state_similarity_threshold)
        if before_id != from_state:
            # The live UI drifted. Learn from what we see rather than lying to the graph.
            self.event("warning", "state drift before action", expected=from_state, actual=before_id)
            from_state = before_id

        if action_lower == "select" and not cfg.allow_select_on_dangerous_text:
            node = self.graph.nodes.get(from_state)
            text = " ".join([before_fp.ocr_text, node.representative.ocr_text if node else ""])
            human = (before_fp.focus or {}).get("human_cues") if isinstance(getattr(before_fp, "focus", {}), dict) else {}
            human_risky_select = isinstance(human, dict) and (
                human.get("screen_kind") in {"purchase_or_ppv", "pin_prompt"}
                or bool(set(human.get("risk_flags", []) or []) & {"purchase_flow", "pin_required"})
            )
            if DANGEROUS_TEXT.search(text) or human_risky_select:
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
        if cfg.min_active_required and not self._status_is_acceptable_video(status):
            if str(status.get("signal_class") or "").lower() == "black_screen" or status.get("likely_black_screen"):
                recovery = self.recover_black_screen(reason=f"after_action:{action_norm}")
                status = self.capture_status()
                if self._status_is_acceptable_video(status):
                    self.event("info", "black screen recovered after action", from_state=from_state, action=action_norm, recovery=recovery, status=status)
                else:
                    self.event("warning", "black screen recovery did not restore active video", from_state=from_state, action=action_norm, recovery=recovery, status=status)

        if cfg.min_active_required and not self._status_is_acceptable_video(status):
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

        fast_after = self.should_use_fast_perception(from_state, action_norm) and force_settle_s is None
        after_fp, response_s, timing_debug = self.wait_after_action(action_norm, before_fp, force_settle_s=force_settle_s, perception="fast" if fast_after else "full")
        after_id, created, cmp_to_known = self.graph.upsert_state(after_fp, cfg.state_similarity_threshold)
        # If the fast visual checkpoint found something new or uncertain, immediately
        # re-read it deeply so the graph gains OCR/context, but keep known-path steps fast.
        if fast_after and (created or cmp_to_known.get("score", 0.0) < cfg.state_similarity_threshold or self._steps % max(1, cfg.deep_ocr_every_n_steps) == 0):
            deep_fp = self.capture_fingerprint(hint_prefix="after_deep", perception="full")
            deep_id, deep_created, deep_cmp = self.graph.upsert_state(deep_fp, cfg.state_similarity_threshold)
            after_fp, after_id, created, cmp_to_known = deep_fp, deep_id, bool(created or deep_created), deep_cmp
            timing_debug["deep_checkpoint"] = True
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
        try:
            self.recent_actions.append(action_norm)
            self.sequence_learner.record_action(from_state, action_norm, after_id, reward=reward, time_s=round(time.time() - send_started, 3), source="autonomous", weight=1.0)
            mine_every = max(1, int(getattr(cfg, "sequence_mining_every_n_steps", 24) or 24))
            if self._steps % mine_every == 0:
                learned_sequences = self.sequence_learner.mine_sequences()
                if learned_sequences:
                    self.event("info", "learned useful action sequences", count=len(learned_sequences), top=self.sequence_learner.get_stats().get("top_sequences", [])[:3])
        except Exception:
            log.debug("sequence learner update failed", exc_info=True)

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
        self._governor.action_end()
        _gov_changes = self._governor.maybe_tune(self._steps)
        if _gov_changes:
            self.event("info", "governor tuned", **_gov_changes)
        self.mark_learning_dirty()
        self.maybe_save_hot_loop()

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



    def analyze_region_first_current(self) -> Dict[str, Any]:
        """Run the v23 region-first reader on the live frame without updating the graph.

        This is useful for debugging the fast human-like perception path: known
        regions first, broaden only if expectations are missing.
        """
        frame, status = self.wait_for_good_frame(timeout_s=4.0)
        ctx = self.extractor.region_perceiver.perceive(frame, min_confidence=self.config.region_first_min_confidence)
        return {
            "ok": True,
            "region_first": ctx,
            "video": status,
            "ocr_available": bool(self.extractor._pytesseract),
        }

    def review_context_quality(self, max_nodes: int = 0, auto_enrich: bool = False) -> Dict[str, Any]:
        """Find questionable learned screenshots and optionally re-OCR them.

        This is the operator-facing QA pass: it looks for missing focus, weak OCR,
        missing title, low focus confidence, and popup/PIN screens. With
        auto_enrich=True it reprocesses the saved screenshots using the latest
        focus/context recovery logic and updates the graph.
        """
        if auto_enrich:
            enrich = self.enrich_existing_context(max_nodes=max_nodes)
        else:
            enrich = None
        findings: List[Dict[str, Any]] = []
        counts: Dict[str, int] = {}
        attempted = 0
        limit = int(max_nodes or 0)
        for sid, node in list(self.graph.nodes.items()):
            if limit and attempted >= limit:
                break
            attempted += 1
            fp = node.representative
            focus = fp.focus or {}
            flags = list(focus.get("quality_flags") or [])
            if not focus.get("found"):
                flags.append("no_focus_detected")
            if focus.get("confidence", 1.0) < 0.25:
                flags.append("low_focus_confidence")
            if not (focus.get("screen_title") or focus.get("page_name") or focus.get("block_title")):
                flags.append("missing_screen_title")
            if focus.get("popup_type"):
                flags.append(f"popup:{focus.get('popup_type')}")
            flags = sorted(set(flags))
            for f in flags:
                counts[f] = counts.get(f, 0) + 1
            if flags and len(findings) < 80:
                findings.append({
                    "state_id": sid,
                    "label": node.label,
                    "screenshot": fp.screenshot,
                    "flags": flags,
                    "title": focus.get("screen_title") or focus.get("page_name") or focus.get("block_title") or "",
                    "page_name": focus.get("page_name") or "",
                    "block_title": focus.get("block_title") or "",
                    "focused_item": focus.get("focused_item") or "",
                    "human_label": focus.get("human_label") or "",
                    "popup_type": focus.get("popup_type") or "",
                    "pin_required": bool(focus.get("pin_required")),
                    "context_confidence": focus.get("context_confidence") or 0,
                    "image_url": f"/api/crawl/state/{sid}/image",
                })
        return {
            "ok": True,
            "attempted": attempted,
            "auto_enrich": bool(auto_enrich),
            "enrich": enrich,
            "issue_counts": dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))),
            "questionable_count": sum(1 for _ in findings),
            "findings": findings,
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
            for key in ("screen_title", "page_name", "block_title", "human_label", "focused_item", "focused_value", "channel_number", "channel_name", "popup_type", "row_text", "context_text", "header_text", "action_bar_text"):
                val = str(focus.get(key) or "").strip()
                if val:
                    parts.append(val)
            ui = focus.get("ui_context") or {}
            if isinstance(ui, dict):
                for key in ("context_summary", "screen_title", "page_name", "block_title", "focused_item", "focused_value", "row_text"):
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

    def _map_state_subset(self, max_nodes: int = 240) -> Tuple[set, Dict[str, int], Dict[str, Any]]:
        """Choose a UI-friendly slice of a large learned graph.

        The full graph can be thousands of nodes. Rendering every screenshot,
        outgoing edge and transition card on /intelligence will pin the browser
        and can starve Flask's request threads. This selector keeps the map
        useful by showing root/current/recent/frontier/high-confidence states,
        while still reporting the full graph totals.
        """
        depths = self.graph.depths_from_root()
        for sid in self.graph.nodes:
            depths.setdefault(sid, 999)
        total_nodes = len(self.graph.nodes)
        max_nodes = max(20, int(max_nodes or 240))
        if total_nodes <= max_nodes:
            return set(self.graph.nodes.keys()), depths, {"truncated": False, "selected_nodes": total_nodes, "total_nodes": total_nodes}

        selected: List[str] = []
        seen = set()

        def add(sid: Optional[str]):
            if sid and sid in self.graph.nodes and sid not in seen and len(selected) < max_nodes:
                seen.add(sid)
                selected.append(sid)

        add(self.graph.root_state)
        add(self._last_state)

        # Include recently active states first; this is where the operator/crawler
        # is most likely looking when the page is open.
        recent_edges = sorted(self.graph.edges.values(), key=lambda e: e.last_seen or "", reverse=True)
        for e in recent_edges[: max(40, max_nodes // 3)]:
            add(e.from_state)
            add(e.to_state)

        # Include frontier states with unexplored actions.
        frontier = []
        for sid in self.graph.nodes:
            try:
                rem = len(self.remaining_actions_for_state(sid))
            except Exception:
                rem = 0
            if rem:
                frontier.append((rem, self.state_confidence(sid), self.graph.nodes[sid].last_seen or "", sid))
        frontier.sort(reverse=True)
        for _, _, _, sid in frontier[: max(40, max_nodes // 3)]:
            add(sid)

        # Fill with reachable/high-confidence states, then recent orphans.
        ordered = sorted(
            self.graph.nodes.keys(),
            key=lambda sid: (
                depths.get(sid, 999) == 999,
                depths.get(sid, 999),
                -float(self.state_confidence(sid)),
                -(self.graph.nodes[sid].observation_count or 0),
                self.graph.nodes[sid].label or "",
            ),
        )
        for sid in ordered:
            add(sid)
            if len(selected) >= max_nodes:
                break

        return set(selected), depths, {
            "truncated": True,
            "selected_nodes": len(selected),
            "total_nodes": total_nodes,
            "reason": "large_graph_ui_slice",
        }

    def visual_map(self, max_nodes: int = 240, max_edges: int = 420, include_transitions: bool = False, transition_limit: int = 120) -> Dict[str, Any]:
        selected_sids, depths, slice_info = self._map_state_subset(max_nodes=max_nodes)

        # Flowchart lanes are vertical columns by graph depth. Unreachable/passive discoveries
        # get their own wrapped columns instead of being crushed into one tiny bottom row.
        levels: Dict[int, List[str]] = {}
        for sid, depth in depths.items():
            if sid in selected_sids:
                levels.setdefault(depth, []).append(sid)
        for level_nodes in levels.values():
            level_nodes.sort(key=lambda sid: (-self.state_confidence(sid), self.state_kind(sid), self.graph.nodes[sid].label, sid))

        nodes: List[Dict[str, Any]] = []
        channels_by_state: Dict[str, List[Dict[str, Any]]] = {}
        for rec in self.brain.channels.values():
            if rec.state_id in selected_sids:
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
        edge_candidates = [e for e in self.graph.edges.items() if e[1].from_state in selected_sids and e[1].to_state in selected_sids]
        edge_candidates.sort(key=lambda kv: (kv[1].last_seen or "", float(kv[1].confidence or 0.0), int(kv[1].attempts or 0)), reverse=True)
        edge_candidates = edge_candidates[: max(1, int(max_edges or 420))]
        for eid, edge in edge_candidates:
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
        transitions = self.transition_cards(limit=transition_limit) if include_transitions else []
        return {
            "ok": True,
            "schema": "jamboree_visual_flow_map_v5_ui_friendly",
            "updated_at": self._now(),
            "root_state": self.graph.root_state,
            "current_state": self._last_state,
            "node_count": len(self.graph.nodes),
            "edge_count": len(self.graph.edges),
            "visible_node_count": len(nodes),
            "visible_edge_count": len(edges),
            "transition_count": len(transitions),
            "map_slice": slice_info,
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
            "patterns": self.pattern_recognizer.get_pattern_stats(),
            "adaptive_thresholds": self.graph.adaptive_thresholds.get_stats(),
            "sequences": self.sequence_learner.get_stats(),
            "persistence": self.persistence_tracker.get_stats(),
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

