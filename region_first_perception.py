#!/usr/bin/env python3
"""Region-first perception for STB UI screens.

The generic crawler historically treated every screen like an unknown image:
full-frame OCR, red-focus scan, broad graph matching, then inference.  Humans do
not do that.  We first look at the stable parts of the UI we already understand:
page title, guide selected row, right detail panel, top banner, action bar, etc.
Only when those expected regions fail do we broaden our view.

This module is intentionally standalone and optional.  If OCR/Tesseract is not
available it still returns visual/family hints; callers can fall back to the old
full perception path.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

import cv2
import numpy as np

try:  # Runtime optional.
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover
    pytesseract = None  # type: ignore


TIME_RX = re.compile(r"\b(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)\s+\d{1,2}/\d{1,2}\s*(?:[|+\-–]+\s*)?\d{1,2}:\d{2}\s*[ap]m?\b", re.I)
TIME_ONLY_RX = re.compile(r"\b\d{1,2}:\d{2}\s*[ap]m?\b", re.I)
CHANNEL_RX = re.compile(r"\b(?:(\d{2,4})\s+([A-Z][A-Z0-9&+]{1,8})|([A-Z][A-Z0-9&+]{1,8})\s+(\d{2,4}))\b")


@dataclass
class RegionRead:
    name: str
    box: Tuple[float, float, float, float]
    text: str = ""
    confidence: float = 0.0
    stage: str = "targeted"


@dataclass
class RegionFirstResult:
    schema: str = "region_first_perception_v1"
    strategy: str = "region_first_then_broaden"
    screen_family: str = "unknown"
    confidence: float = 0.0
    stage: str = "targeted"  # targeted, common, broad
    text: str = ""
    title: str = ""
    displayed_datetime_text: str = ""
    channel_number: str = ""
    channel_code: str = ""
    focused_item_hint: str = ""
    expected_regions: List[str] = field(default_factory=list)
    satisfied_regions: List[str] = field(default_factory=list)
    missing_expectations: List[str] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    avoid_actions: List[str] = field(default_factory=list)
    quality_flags: List[str] = field(default_factory=list)
    regions: Dict[str, str] = field(default_factory=dict)
    visual: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def clean_text(text: Any, limit: int = 1000) -> str:
    s = str(text or "")
    for a, b in {
        "\n": " ", "\r": " ", "\t": " ", "…": "...", "—": "-", "–": "-", "•": " ", "·": " ",
        "“": '"', "”": '"', "‘": "'", "’": "'",
    }.items():
        s = s.replace(a, b)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\bd[=\-]?s\s*h\b", "dish", s, flags=re.I)
    s = re.sub(r"\bL[i1]ve\s*TV\b", "Live TV", s, flags=re.I)
    return s[:limit]


def tokenize(text: str) -> List[str]:
    return sorted(set(re.findall(r"[a-zA-Z0-9]{2,}", clean_text(text).lower())))[:120]


def norm_crop(frame: np.ndarray, box: Tuple[float, float, float, float]) -> np.ndarray:
    h, w = frame.shape[:2]
    x1 = max(0, min(w, int(round(box[0] * w))))
    y1 = max(0, min(h, int(round(box[1] * h))))
    x2 = max(0, min(w, int(round(box[2] * w))))
    y2 = max(0, min(h, int(round(box[3] * h))))
    if x2 <= x1 or y2 <= y1:
        return frame[0:0, 0:0]
    return frame[y1:y2, x1:x2]


def px_crop(frame: np.ndarray, box: Iterable[int], pad: int = 0) -> np.ndarray:
    vals = list(box or [])[:4]
    if len(vals) != 4:
        return frame[0:0, 0:0]
    h, w = frame.shape[:2]
    x, y, bw, bh = [int(v) for v in vals]
    x1 = max(0, x - pad); y1 = max(0, y - pad)
    x2 = min(w, x + bw + pad); y2 = min(h, y + bh + pad)
    if x2 <= x1 or y2 <= y1:
        return frame[0:0, 0:0]
    return frame[y1:y2, x1:x2]


def prep_for_ocr(img: np.ndarray) -> np.ndarray:
    if img is None or not getattr(img, "size", 0):
        return img
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()
    gray = cv2.resize(gray, None, fx=2.2, fy=2.2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.bilateralFilter(gray, 5, 35, 35)
    return cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)


class RegionFirstPerceiver:
    """Target known UI regions first, then broaden only if expectations fail."""

    COMMON_REGIONS: Dict[str, Tuple[float, float, float, float]] = {
        "top_left_title": (0.02, 0.02, 0.58, 0.16),
        "top_right_clock": (0.66, 0.02, 0.99, 0.17),
        "top_banner": (0.00, 0.00, 1.00, 0.18),
        "left_channel_strip": (0.00, 0.12, 0.18, 0.82),
        "center_grid": (0.14, 0.14, 0.76, 0.84),
        "right_detail_panel": (0.72, 0.08, 0.995, 0.92),
        "action_bar": (0.00, 0.82, 1.00, 0.99),
        "grey_panel_header": (0.18, 0.05, 0.84, 0.22),
        "info_title_area": (0.22, 0.18, 0.62, 0.34),
        "info_channel_area": (0.20, 0.34, 0.52, 0.55),
        "info_description_area": (0.45, 0.23, 0.98, 0.52),
    }

    FAMILY_EXPECTATIONS: Dict[str, List[str]] = {
        "live_banner": ["top_banner", "top_right_clock"],
        "guide": ["left_channel_strip", "center_grid", "right_detail_panel", "top_right_clock"],
        "info": ["info_title_area", "info_channel_area", "info_description_area", "top_right_clock"],
        "menu": ["top_left_title", "grey_panel_header", "action_bar"],
        "settings": ["top_left_title", "grey_panel_header", "center_grid"],
        "ondemand": ["top_left_title", "center_grid", "right_detail_panel"],
        "dvr": ["top_left_title", "center_grid", "right_detail_panel"],
        "passive_video": ["top_banner"],
        "loading": ["top_left_title"],
        "unknown": ["top_left_title", "top_right_clock"],
    }

    ACTION_BIAS: Dict[str, Tuple[List[str], List[str]]] = {
        "loading": (["wait"], ["select", "up", "down", "left", "right"]),
        "passive_video": (["info", "guide", "ch_up", "ch_down", "options"], []),
        "live_banner": (["info", "guide", "ch_up", "ch_down", "options"], []),
        "guide": (["up", "down", "left", "right", "info", "select", "ch_up", "ch_down"], []),
        "info": (["down", "up", "right", "left", "back", "record", "select"], []),
        "menu": (["left", "right", "up", "down", "select", "info", "options"], []),
        "settings": (["down", "up", "right", "left", "select", "back"], []),
        "ondemand": (["left", "right", "up", "down", "info", "select", "back"], []),
        "dvr": (["left", "right", "up", "down", "play", "select", "info", "back"], []),
    }

    def __init__(self, pytesseract_mod: Any = None, timeout_s: float = 0.9) -> None:
        self.pytesseract = pytesseract_mod if pytesseract_mod not in {False, None} else pytesseract
        self.timeout_s = float(timeout_s)

    def ocr(self, img: np.ndarray, psm: int = 6) -> str:
        if self.pytesseract is None or img is None or not getattr(img, "size", 0):
            return ""
        try:
            return clean_text(self.pytesseract.image_to_string(prep_for_ocr(img), config=f"--oem 3 --psm {int(psm)} -c user_defined_dpi=300", timeout=self.timeout_s))
        except Exception:
            return ""

    def read_region(self, frame: np.ndarray, name: str, box: Tuple[float, float, float, float], psm: int = 6, stage: str = "targeted") -> RegionRead:
        text = self.ocr(norm_crop(frame, box), psm=psm)
        conf = min(1.0, 0.18 + len(tokenize(text)) / 14.0) if text else 0.0
        return RegionRead(name=name, box=box, text=text, confidence=round(conf, 3), stage=stage)

    def quick_visual(self, frame: np.ndarray) -> Dict[str, Any]:
        if frame is None or not getattr(frame, "size", 0):
            return {"no_frame": True}
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        top = gray[:max(1, int(h * 0.18)), :]
        mid = gray[int(h * 0.20):int(h * 0.82), int(w * 0.10):int(w * 0.90)]
        edges = cv2.Canny(cv2.resize(mid, (320, 180), interpolation=cv2.INTER_AREA), 80, 160)
        # Simple progress-dot detector in the central lower region.
        dot_roi = gray[int(h * 0.45):int(h * 0.68), int(w * 0.35):int(w * 0.65)]
        _, bw = cv2.threshold(dot_roi, 185, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        dots = []
        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)
            area = cv2.contourArea(c)
            if 6 <= cw <= 28 and 6 <= ch <= 28 and 10 <= area <= 450:
                dots.append((x, y, cw, ch))
        # Guide-like grids have vertical/horizontal line structure and lots of edges.
        guide_grid_score = float(np.mean(edges > 0))
        return {
            "top_brightness": round(float(np.mean(top)), 3),
            "mid_edge_density": round(guide_grid_score, 5),
            "progress_dot_count": len(dots),
            "progress_dots_likely": len(dots) >= 4,
            "black_fraction": round(float(np.mean(gray < 18)), 4),
        }

    def detect_red_focus_bbox(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        if frame is None or not getattr(frame, "size", 0):
            return None
        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, np.array([0, 70, 65]), np.array([12, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([168, 70, 65]), np.array([180, 255, 255]))
        mask = cv2.bitwise_or(mask1, mask2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=1)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates: List[Tuple[float, Tuple[int, int, int, int]]] = []
        for c in contours:
            x, y, bw, bh = cv2.boundingRect(c)
            area = cv2.contourArea(c)
            if area < 250 or bw < 18 or bh < 12:
                continue
            # Penalize DISH logo / tiny top-left logo fragments.
            if x < 190 and y < 115 and area < 2500:
                continue
            aspect = bw / max(1, bh)
            red_density = float(np.mean(mask[y:y+bh, x:x+bw] > 0))
            score = area * (0.6 + red_density) * (1.0 if 0.5 <= aspect <= 8.0 else 0.55)
            if 0.06 < y / max(1, h) < 0.92:
                score *= 1.1
            candidates.append((score, (x, y, bw, bh)))
        if not candidates:
            return None
        return sorted(candidates, reverse=True)[0][1]

    @staticmethod
    def classify_from_text(text: str, visual: Optional[Dict[str, Any]] = None) -> Tuple[str, float, List[str]]:
        visual = visual or {}
        clean = clean_text(text, 2400)
        low = clean.lower()
        reasons: List[str] = []
        scores = {
            "loading": 0.0, "live_banner": 0.0, "guide": 0.0, "info": 0.0,
            "settings": 0.0, "menu": 0.0, "ondemand": 0.0, "dvr": 0.0, "passive_video": 0.0,
        }
        if visual.get("progress_dots_likely"):
            scores["loading"] += 0.45; reasons.append("center progress dots")
        if re.search(r"\bguide\b|showing:\s*all|all subscribed|today\s+\d{1,2}:\d{2}", low):
            scores["guide"] += 0.55; reasons.append("guide chrome")
        if re.search(r"\blive\s*tv\b|mins?\s+left|\bmin\s+left\b", low):
            scores["live_banner"] += 0.55; reasons.append("live banner chrome")
        if re.search(r"\btv\s*show\b|\bsummary\b|\bepisodes\b|\brecord\s+this\b|\brecord\s+series\b", low):
            scores["info"] += 0.68; reasons.append("info/tv show chrome")
        if re.search(r"\bsettings\b|parental|diagnostics|preferences|locked channels|tv viewing options", low):
            scores["settings"] += 0.50; reasons.append("settings terms")
        if re.search(r"on\s*demand|rent|purchase|watch now|movies|shows|sports|search|apps", low):
            scores["ondemand"] += 0.35; reasons.append("content shelf terms")
        if re.search(r"\bdvr\b|recordings|recorded|my recordings|timer|reminder", low):
            scores["dvr"] += 0.45; reasons.append("dvr/timer terms")
        if re.search(r"\bdish\b|home|menu|help|search", low):
            scores["menu"] += 0.25; reasons.append("general menu chrome")
        if not clean and float(visual.get("mid_edge_density") or 0.0) < 0.04 and not visual.get("progress_dots_likely"):
            scores["passive_video"] += 0.25; reasons.append("little UI text/structure")
        family, score = max(scores.items(), key=lambda kv: kv[1])
        if score < 0.25:
            return "unknown", 0.0, reasons
        return family, min(1.0, score), reasons

    @staticmethod
    def extract_datetime(text: str) -> str:
        m = TIME_RX.search(clean_text(text, 1200))
        return clean_text(m.group(0), 80) if m else ""

    @staticmethod
    def extract_channel(text: str) -> Tuple[str, str]:
        clean = clean_text(text, 1200)
        for m in CHANNEL_RX.finditer(clean):
            num = m.group(1) or m.group(4) or ""
            code = m.group(2) or m.group(3) or ""
            if num.isdigit() and 2 <= int(num) <= 9999 and code.upper() not in {"SAT", "TODAY", "LIVE", "GUIDE", "DISH", "HD", "TV"}:
                return num, code.upper()
        return "", ""

    @staticmethod
    def extract_channel_number_only(text: str) -> str:
        clean = TIME_RX.sub(" ", clean_text(text, 1200))
        clean = TIME_ONLY_RX.sub(" ", clean)
        clean = re.sub(r"\b\d{1,2}/\d{1,2}\b", " ", clean)
        for m in re.finditer(r"\b(\d{2,4})\b", clean):
            n = int(m.group(1))
            if 2 <= n <= 9999:
                tail = clean[m.end():m.end()+18].lower()
                if re.match(r"\s*(mins?|minutes?|remaining|left)\b", tail):
                    continue
                return str(n)
        return ""

    @staticmethod
    def best_title(text: str) -> str:
        lines = [clean_text(x, 160) for x in re.split(r"\s{3,}|[\r\n]+|\s+[|]\s+", str(text or ""))]
        lines = [x for x in lines if sum(c.isalpha() for c in x) >= 3]
        if not lines:
            return ""
        bad = {"dish", "guide", "showing", "all subscribed", "today", "live tv", "summary", "episodes", "cast"}
        scored = []
        for line in lines:
            low = line.lower()
            score = len(line) - sum(22 for b in bad if b in low)
            scored.append((score, line))
        return sorted(scored, reverse=True)[0][1]

    def perceive(self, frame: np.ndarray, min_confidence: float = 0.62) -> Dict[str, Any]:
        if frame is None or not getattr(frame, "size", 0):
            return RegionFirstResult(screen_family="no_frame", quality_flags=["no_frame"]).to_dict()
        visual = self.quick_visual(frame)

        # Stage 1: cheap common chrome reads.
        reads: Dict[str, RegionRead] = {}
        for name in ("top_left_title", "top_right_clock", "top_banner", "grey_panel_header", "action_bar"):
            psm = 7 if name in {"top_right_clock", "top_left_title", "grey_panel_header"} else 6
            reads[name] = self.read_region(frame, name, self.COMMON_REGIONS[name], psm=psm, stage="targeted")
        bbox = self.detect_red_focus_bbox(frame)
        if bbox:
            # Read focus and same row. These are often enough to determine intent.
            x, y, bw, bh = bbox
            h, w = frame.shape[:2]
            reads["focus_box"] = RegionRead("focus_box", (x/w, y/h, (x+bw)/w, (y+bh)/h), self.ocr(px_crop(frame, bbox, pad=4), psm=6), 0.6, "targeted")
            row_box = (0.0, max(0.0, (y - bh * 0.65) / h), 1.0, min(1.0, (y + bh * 1.65) / h))
            reads["focus_row"] = self.read_region(frame, "focus_row", row_box, psm=6, stage="targeted")

        targeted_text = " ".join(r.text for r in reads.values() if r.text)
        family, family_score, reasons = self.classify_from_text(targeted_text, visual)
        stage = "targeted"

        # Stage 2: if known family, read expected regions. If still weak, broaden to the whole UI surface.
        expected = self.FAMILY_EXPECTATIONS.get(family, self.FAMILY_EXPECTATIONS["unknown"])
        for name in expected:
            if name not in reads and name in self.COMMON_REGIONS:
                psm = 7 if name in {"top_right_clock", "top_left_title", "grey_panel_header"} else 6
                reads[name] = self.read_region(frame, name, self.COMMON_REGIONS[name], psm=psm, stage="expected")
        expanded_text = " ".join(r.text for r in reads.values() if r.text)
        family2, score2, reasons2 = self.classify_from_text(expanded_text, visual)
        if score2 > family_score:
            family, family_score, reasons = family2, score2, reasons + reasons2

        satisfied = [name for name in expected if clean_text(reads.get(name).text if name in reads else "")]
        missing = [name for name in expected if name not in satisfied]

        if family_score < min_confidence or len(satisfied) < max(1, min(2, len(expected))):
            stage = "common"
            for name in ("left_channel_strip", "center_grid", "right_detail_panel", "info_title_area", "info_channel_area", "info_description_area"):
                if name not in reads:
                    reads[name] = self.read_region(frame, name, self.COMMON_REGIONS[name], psm=6, stage="common")
            expanded_text = " ".join(r.text for r in reads.values() if r.text)
            family3, score3, reasons3 = self.classify_from_text(expanded_text, visual)
            if score3 > family_score:
                family, family_score, reasons = family3, score3, reasons + reasons3
            expected = self.FAMILY_EXPECTATIONS.get(family, self.FAMILY_EXPECTATIONS["unknown"])
            satisfied = [name for name in expected if clean_text(reads.get(name).text if name in reads else "")]
            missing = [name for name in expected if name not in satisfied]

        if family_score < 0.42 and self.pytesseract is not None:
            stage = "broad"
            broad = self.ocr(frame, psm=11)
            reads["full_sparse"] = RegionRead("full_sparse", (0, 0, 1, 1), broad, 0.4 if broad else 0.0, "broad")
            expanded_text = " ".join(r.text for r in reads.values() if r.text)
            family4, score4, reasons4 = self.classify_from_text(expanded_text, visual)
            if score4 > family_score:
                family, family_score, reasons = family4, score4, reasons + reasons4

        regions = {name: clean_text(read.text, 500) for name, read in reads.items() if clean_text(read.text)}
        all_text = clean_text(" ".join(regions.values()), 2600)
        title = self.best_title(" ".join(regions.get(k, "") for k in ["top_left_title", "grey_panel_header", "info_title_area", "right_detail_panel"]))
        dt = self.extract_datetime(" ".join(regions.get(k, "") for k in ["top_right_clock", "top_banner", "right_detail_panel", "info_description_area", "full_sparse"]))
        channel_text = " ".join(regions.get(k, "") for k in ["focus_row", "left_channel_strip", "top_banner", "info_channel_area", "right_detail_panel", "full_sparse"])
        num, code = self.extract_channel(channel_text)
        if not num:
            num = self.extract_channel_number_only(channel_text)
        focus_hint = self.best_title(" ".join(regions.get(k, "") for k in ["focus_box", "focus_row", "center_grid"]))
        suggested, avoid = self.ACTION_BIAS.get(family, ([], []))
        qflags: List[str] = []
        if missing:
            qflags.append("region_expectations_missing")
        if stage != "targeted":
            qflags.append(f"broadened_to_{stage}")
        if visual.get("progress_dots_likely"):
            qflags.append("visual_progress_dots")
        if not title and family in {"menu", "settings", "info"}:
            qflags.append("missing_title_after_region_read")
        if not focus_hint and family in {"guide", "menu", "settings", "ondemand", "dvr"}:
            qflags.append("missing_focus_hint_after_region_read")

        return RegionFirstResult(
            screen_family=family,
            confidence=round(float(family_score), 4),
            stage=stage,
            text=all_text,
            title=title,
            displayed_datetime_text=dt,
            channel_number=num,
            channel_code=code,
            focused_item_hint=focus_hint,
            expected_regions=list(expected),
            satisfied_regions=satisfied,
            missing_expectations=missing,
            suggested_actions=list(suggested),
            avoid_actions=list(avoid),
            quality_flags=qflags,
            regions=regions,
            visual=visual,
        ).to_dict()


def pattern_from_region_family(family: str) -> str:
    family = str(family or "unknown").lower()
    if family in {"guide", "menu", "ondemand", "dvr"}:
        return "grid_menu"
    if family in {"settings"}:
        return "linear_menu"
    if family == "info":
        return "info_card"
    if family in {"live_banner", "passive_video"}:
        return "video_player"
    return "unknown"
