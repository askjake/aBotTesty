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
    width: int = 0
    height: int = 0


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
            ocr_text=text,
            ocr_tokens=self.tokenize(text),
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
        bright_sim = 1.0 - min(1.0, abs(a.brightness - b.brightness) / 96.0)
        var_sim = 1.0 - min(1.0, abs(math.sqrt(max(a.variance, 0.0)) - math.sqrt(max(b.variance, 0.0))) / 80.0)
        edge_sim = 1.0 - min(1.0, abs(a.edge_density - b.edge_density) / 0.25)
        metric_sim = (bright_sim + var_sim + edge_sim) / 3.0
        # OCR is useful when available but should not punish the model when absent.
        text_weight = 0.12 if (a.ocr_tokens or b.ocr_tokens) else 0.02
        visual_weight = 1.0 - text_weight
        visual = 0.36 * phash_sim + 0.22 * dhash_sim + 0.10 * ahash_sim + 0.22 * hist_sim + 0.10 * metric_sim
        score = visual_weight * visual + text_weight * text_sim
        return {
            "score": round(max(0.0, min(1.0, score)), 5),
            "phash": round(phash_sim, 5),
            "dhash": round(dhash_sim, 5),
            "ahash": round(ahash_sim, 5),
            "hist": round(hist_sim, 5),
            "text": round(text_sim, 5),
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

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def edge_key(from_state: str, action: str, to_state: str) -> str:
        return f"{from_state}|{action}|{to_state}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "jamboree_nav_graph_v1",
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
                    representative=ScreenFingerprint(**node["representative"]),
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
        text = fp.ocr_text.strip()
        if text:
            short = " ".join(text.split()[:6])
            return short[:80]
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
            edge.samples = edge.samples[-10:]
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
        self.known_tokens: set[str] = set()
        self.known_concepts: set[str] = set()
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
            self.known_tokens = set(raw.get("known_tokens", []))
            self.known_concepts = set(raw.get("known_concepts", []))
            self.channels = {
                k: ChannelRecord(**v) for k, v in raw.get("channels", {}).items()
            }
        except Exception:
            log.exception("Unable to load crawler brain; starting fresh")
            self.action_timing = {}
            self.action_rewards = {}
            self.known_tokens = set()
            self.known_concepts = set()
            self.channels = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": "jamboree_crawler_brain_v2",
            "updated_at": self.now(),
            "action_timing": {k: asdict(v) for k, v in self.action_timing.items()},
            "action_rewards": {k: asdict(v) for k, v in self.action_rewards.items()},
            "known_tokens": sorted(self.known_tokens),
            "known_concepts": sorted(self.known_concepts),
            "channels": {k: asdict(v) for k, v in sorted(self.channels.items(), key=lambda kv: int(kv[0]))},
        }

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def reset(self) -> None:
        self.action_timing.clear()
        self.action_rewards.clear()
        self.known_tokens.clear()
        self.known_concepts.clear()
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
        self.events: Deque[CrawlEvent] = deque(maxlen=300)
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._running = False
        self._run_id: Optional[str] = None
        self._steps = 0
        self._last_state: Optional[str] = None
        self._last_error = ""
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
                    "action_rewards": {k: asdict(v) for k, v in self.brain.action_rewards.items()},
                    "action_timing": {k: asdict(v) for k, v in self.brain.action_timing.items()},
                    "channels": self.brain.channel_summary(),
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
            )
            self.probe_extractor = FeatureExtractor(self.data_dir, save_screenshots=False, ocr_enabled=False)
            self._stop.clear()
            self._running = True
            self._run_id = f"crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self._started_at = self._now()
            self._finished_at = None
            self._last_error = ""
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
        }
        int_fields = {"max_steps", "max_states", "max_depth", "replay_retries", "stable_observations_required"}
        float_fields = {
            "settle_s", "reset_settle_s", "between_key_s", "state_similarity_threshold",
            "changed_similarity_threshold", "reward_new_state", "reward_new_menu", "reward_new_setting",
            "reward_new_feature", "reward_new_text_tokens", "penalty_noop", "penalty_inactive",
            "penalty_blocked", "min_settle_s", "max_settle_s", "timing_poll_s",
            "stable_similarity_threshold", "channel_digit_gap_s", "channel_tune_settle_s",
        }
        for key, value in overrides.items():
            if key not in allowed:
                continue
            if key in list_fields and isinstance(value, str):
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

        frontier: Deque[Tuple[str, int, float]] = deque([(root_id, 0, 0.0)])
        explored_actions: set[Tuple[str, str]] = set()

        while frontier and not self._stop.is_set():
            if self._steps >= cfg.max_steps:
                self.event("warning", "max steps reached", max_steps=cfg.max_steps)
                break
            if len(self.graph.nodes) >= cfg.max_states:
                self.event("warning", "max states reached", max_states=cfg.max_states)
                break

            # Rewarded exploration: prioritize frontiers that previously paid off.
            if cfg.self_explore_enabled and len(frontier) > 1:
                ordered = sorted(list(frontier), key=lambda item: item[2], reverse=True)
                frontier = deque(ordered)

            state_id, depth, inherited_reward = frontier.popleft()
            if depth > cfg.max_depth:
                continue

            if not self.navigate_to_state(state_id):
                self.event("warning", "unable to restore target state; skipping", state=state_id)
                continue

            actions = self.brain.order_actions(cfg.enabled_keys) if cfg.self_explore_enabled else list(cfg.enabled_keys)
            for action in actions:
                if self._stop.is_set() or self._steps >= cfg.max_steps:
                    break
                if (state_id, action) in explored_actions:
                    continue
                explored_actions.add((state_id, action))
                result = self.try_action(state_id, action)
                reward = float(result.get("reward", 0.0))
                if result.get("new_state") and result["to_state"] not in [s for s, _, _ in frontier]:
                    if result["to_state"] != state_id and depth + 1 <= cfg.max_depth:
                        frontier.append((result["to_state"], depth + 1, inherited_reward * 0.25 + reward))
                self.graph.save()
                self.brain.save()

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
        # Preserve capture status in the OCR text if there is no OCR, useful for labels/debugging.
        if not fp.ocr_text:
            fp.ocr_text = ""
        return fp

    def safe_send(self, key: str) -> Dict[str, Any]:
        key = str(key).strip()
        self.event("debug", "send key", key=key)
        result = self.send_key(key)
        time.sleep(self.config.between_key_s)
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

        reward, reward_details = self.brain.score_observation(
            cfg, action_norm, before_fp, after_fp, created=created, changed=changed
        )
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
                "before_after_similarity": cmp_before_after,
                "known_similarity": cmp_to_known,
                "send": send_result,
                "created_state": created,
                "reward": reward,
                "reward_details": reward_details,
                "timing": timing_debug,
                "elapsed_s": round(time.time() - send_started, 3),
                "channel": channel,
            },
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
            "edge": asdict(edge),
        }
