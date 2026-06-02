#!/usr/bin/env python3
"""Focus/highlight + semantic context perception for Dish/STB UI screens.

v9 upgrades Jake's original red-highlight work into a richer perception layer:
- detect the red focus parallelogram/rectangle
- OCR the focused crop, row, neighbors, header/title band, and action bar
- infer screen/menu title, focused item, setting/value pairs, semantic tags, and risk flags
- return a human-readable context label suitable for maps and navigation learning
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

import cv2
import numpy as np

log = logging.getLogger("merged.focus")


@dataclass
class FocusObservation:
    found: bool = False
    confidence: float = 0.0
    bbox: Optional[List[int]] = None  # x,y,w,h
    bbox_norm: Optional[List[float]] = None
    center_norm: Optional[List[float]] = None
    corners: List[List[int]] = field(default_factory=list)
    area: float = 0.0
    aspect: float = 0.0
    red_density: float = 0.0
    contour_vertices: int = 0
    focus_text: str = ""
    context_text: str = ""
    label_text: str = ""
    row_text: str = ""
    header_text: str = ""
    action_bar_text: str = ""
    screen_title: str = ""
    menu_title: str = ""
    # v10: DISH UI-specific semantic anchors.
    # page_name is the small top-left text immediately after the DISH logo.
    # block_title is the title at the top of a smaller grey menu/block panel.
    page_name: str = ""
    block_title: str = ""
    title_source: str = ""
    grey_box_bbox: Optional[List[int]] = None
    active_tab: str = ""
    focused_item: str = ""
    focused_value: str = ""
    human_label: str = ""
    focus_role: str = ""
    context_confidence: float = 0.0
    neighbor_text: Dict[str, str] = field(default_factory=dict)
    setting_pairs: List[Dict[str, str]] = field(default_factory=list)
    semantic_tags: List[str] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)
    quality_flags: List[str] = field(default_factory=list)
    recovery_text: str = ""
    popup_type: str = ""
    pin_required: bool = False
    channel_number: str = ""
    channel_name: str = ""
    nearby_words: List[str] = field(default_factory=list)
    tokens: List[str] = field(default_factory=list)
    ui_context: Dict[str, Any] = field(default_factory=dict)
    row_guess: Optional[int] = None
    col_guess: Optional[int] = None
    region: str = ""
    warning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Duplicate the most useful fields under ui_context so future callers can
        # treat focus geometry and semantic context independently.
        if not d.get("ui_context"):
            d["ui_context"] = {
                "screen_title": d.get("screen_title", ""),
                "menu_title": d.get("menu_title", ""),
                "page_name": d.get("page_name", ""),
                "block_title": d.get("block_title", ""),
                "title_source": d.get("title_source", ""),
                "grey_box_bbox": d.get("grey_box_bbox"),
                "active_tab": d.get("active_tab", ""),
                "focused_item": d.get("focused_item", ""),
                "focused_value": d.get("focused_value", ""),
                "focus_role": d.get("focus_role", ""),
                "human_label": d.get("human_label", ""),
                "context_summary": build_context_summary(d),
                "row_text": d.get("row_text", ""),
                "neighbor_text": d.get("neighbor_text", {}),
                "setting_pairs": d.get("setting_pairs", []),
                "semantic_tags": d.get("semantic_tags", []),
                "risk_flags": d.get("risk_flags", []),
                "quality_flags": d.get("quality_flags", []),
                "popup_type": d.get("popup_type", ""),
                "pin_required": d.get("pin_required", False),
                "channel_number": d.get("channel_number", ""),
                "channel_name": d.get("channel_name", ""),
                "context_confidence": d.get("context_confidence", 0.0),
            }
        return d


_STOP = {
    "the", "and", "for", "you", "your", "are", "with", "this", "that", "press", "select",
    "sun", "mon", "tue", "wed", "thu", "fri", "sat", "dish", "dsh", "d:sh", "sh", "eee",
    "ee", "aa", "ae", "oe", "re", "se", "te", "ii", "iii", "mm", "mmm", "mmmm", "oo",
}

_RISK_TERMS = {
    "purchase", "purchases", "rent", "subscribe", "delete", "factory", "reset", "payment",
    "pin", "passcode", "parental", "lock", "locked", "adult", "unpair", "format", "restart",
}

_COMMON_TITLES: List[Tuple[str, str]] = [
    ("Locked Channels", r"\blocked\s+channels?\b|\block(?:ed)?\s+channels?\b|\blocked\s+channels?\b"),
    ("Closed Captioning", r"\bclosed\s+caption(?:ing)?\b|\bcc\b"),
    ("Picture In Picture", r"\bpicture\s+in\s+picture\b|\bpip\b"),
    ("Display Format", r"\bdisplay\s+format\b"),
    ("Accessibility", r"\baccessibility\b"),
    ("TV Activity", r"\btv\s+activity\b"),
    ("Parental Control Settings", r"\b(?:p|f|ar)?arental\s+controls?\s+(?:settings?|setting)|\bparental\s+controls?\b"),
    ("TV Viewing Options", r"\btv\s+(?:view(?:ing)?\s+options?|options?\s+viewing)\b|\bviewing\s+options?\b"),
    ("Diagnostics", r"\bdiagnostics?\b"),
    ("Remote Diagnostics", r"\bremote\s+status\b|\bpair\s+a\s+dish\s+remote\b"),
    ("Guide", r"\bguide\b|\bshowing:\s*(?:all|subscribed)\b|\btoday\s+\d{1,2}:\d{2}"),
    ("Search", r"\bsearch\b.*\bquickly\s+find\b|\bmost\s+popular\s+searches\b|\brecent\s+searches\b"),
    ("Home", r"\bhome\b.*(?:\bshows\b|\bstows\b|\bsports\b|\bmovies\b)|\bhome\b.*\bdvr\b.*\bsettings\b|\bhome\b"),
    ("DVR", r"\bdvr\b|\brecorded\s+date\b|\bprimetime\s+anytime\b|\bhopper\b"),
    ("Live TV", r"\blive\s+tv\b"),
    ("TV Show Details", r"\btv\s+show\s+(?:summary|episodes)\b|\bparental\s+guide\b|\bfirst\s+aired\b"),
    ("Options", r"\boptions\b"),
    ("Settings", r"\bsettings?\b"),
    ("Apps", r"\bapps\b"),
    ("On Demand", r"\bon\s+demand\b"),
]

_SEMANTIC_PATTERNS: List[Tuple[str, str]] = [
    ("settings", r"\bsettings?|preferences?|setup|system|display|audio|caption|accessibility|remote|network\b"),
    ("parental", r"\bparental|passcode|locked|adult|restrict|children\b"),
    ("guide", r"\bguide|showing:|subscribed|today|channel\b"),
    ("dvr", r"\bdvr|recorded|recording|primetime|hopper|timer\b"),
    ("search", r"\bsearch|keyboard|popular searches|recent searches\b"),
    ("channel", r"\blive tv|\b\d{2,4}\b|[A-Z]{2,8}\b"),
    ("actions", r"\boptions|close|record|apps|cc|favorite|delete|space|clear\b"),
    ("diagnostics", r"\bdiagnostics?|receiver|firmware|hardware|moca|network|remote status\b"),
    ("content", r"\bmovie|episode|series|season|cast|summary|first aired\b"),
]

_VALUE_RE = re.compile(
    r"\b(?P<value>On|Off|None|Yes|No|Enabled|Disabled|Locked|Unlocked|All|Subscribed|"
    r"\d+\s+channels?|Favorite\s+[A-Z0-9]+|Recorded\s+Date|HD|SD|Normal|Stretch|Zoom)\b",
    re.I,
)


# ─────────────────────────────────────────────────────────────────────────────
# Text helpers
# ─────────────────────────────────────────────────────────────────────────────

def clean_text(text: str, limit: int = 1200) -> str:
    s = str(text or "")
    s = s.replace("\n", " ").replace("\r", " ")
    s = re.sub(r"[\x00-\x1f]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Keep most UI punctuation, but collapse OCR quote confetti.
    s = s.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
    return s[:limit]


def tokenize(text: str, limit: int = 140) -> List[str]:
    words = re.findall(r"[a-zA-Z0-9]{2,}", str(text or "").lower())
    return sorted(set(w for w in words if w not in _STOP))[:limit]


def meaningful(text: str) -> bool:
    toks = tokenize(text, limit=12)
    return bool(toks) and not all(len(t) <= 2 or t in _STOP for t in toks)


def build_context_summary(d: Dict[str, Any]) -> str:
    title = d.get("page_name") or d.get("screen_title") or d.get("menu_title") or "Unknown screen"
    block = d.get("block_title") or ""
    item = d.get("focused_item") or d.get("label_text") or d.get("focus_text") or d.get("row_text")
    value = d.get("focused_value")
    role = d.get("focus_role")
    parts = [str(title).strip()]
    if block and str(block).strip().lower() != str(title).strip().lower():
        parts.append(f"block: {str(block).strip()[:70]}")
    if item:
        parts.append(f"focus: {str(item).strip()[:90]}")
    if value:
        parts.append(f"value: {str(value).strip()[:40]}")
    if role:
        parts.append(f"role: {role}")
    return " · ".join(p for p in parts if p)


def _words_text(words: Iterable[Dict[str, Any]], max_words: int = 80) -> str:
    rows = sorted(words, key=lambda w: (w.get("cy", 0), w.get("x", 0)))
    return clean_text(" ".join(w["text"] for w in rows if w.get("text")), limit=max_words * 16)


# ─────────────────────────────────────────────────────────────────────────────
# OCR helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_pytesseract(pytesseract_mod: Any = None) -> Any:
    # v14: False is an explicit no-OCR sentinel used by fast visual checkpoints.
    if pytesseract_mod is False:
        return None
    if pytesseract_mod is not None:
        return pytesseract_mod
    try:
        import pytesseract as pytesseract_mod  # type: ignore
        return pytesseract_mod
    except Exception:
        return None


def _prep_for_ocr(img: np.ndarray, scale: float = 2.0) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    if scale and abs(scale - 1.0) > 0.01:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    gray = cv2.bilateralFilter(gray, 5, 35, 35)
    return gray


def _ocr_image(img: np.ndarray, pytesseract_mod: Any = None, psm: int = 6, whitelist: Optional[str] = None) -> str:
    if img is None or not getattr(img, "size", 0):
        return ""
    pytesseract_mod = _get_pytesseract(pytesseract_mod)
    if pytesseract_mod is None:
        return ""
    try:
        scaled = _prep_for_ocr(img, scale=2.0)
        _, bw = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cfg = f"--oem 3 --psm {int(psm)} -c user_defined_dpi=300"
        if whitelist:
            # Tesseract config is shell-split by pytesseract. A literal space in
            # tessedit_char_whitelist becomes a new argv item; if the next chars
            # start with -, Tesseract throws: unknown command line argument.
            # Keep the whitelist compact and let Tesseract still separate words.
            safe_whitelist = re.sub(r"\s+", "", str(whitelist))
            cfg += f" -c tessedit_char_whitelist={safe_whitelist}"
        return clean_text(pytesseract_mod.image_to_string(bw, config=cfg), limit=1200)
    except Exception as exc:
        log.debug("focus OCR failed: %s", exc)
        return ""



def _ocr_image_multi(img: np.ndarray, pytesseract_mod: Any = None, psms: Tuple[int, ...] = (6, 7, 11), whitelist: Optional[str] = None) -> str:
    """Recover text from difficult STB regions using several human-like OCR passes.

    A human would zoom, invert, crop tighter, and read again. This does the same
    mechanically: CLAHE/threshold, inverted threshold, adaptive threshold, and
    multiple PSM modes. It returns the candidate with the most useful tokens,
    not necessarily the longest garbage string.
    """
    if img is None or not getattr(img, "size", 0):
        return ""
    pytesseract_mod = _get_pytesseract(pytesseract_mod)
    if pytesseract_mod is None:
        return ""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    variants: List[np.ndarray] = []
    for scale in (2.0, 3.0):
        g = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        g = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(g)
        g = cv2.bilateralFilter(g, 5, 35, 35)
        _, otsu = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _, inv = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        adapt = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 7)
        variants.extend([g, otsu, inv, adapt])
    candidates: List[str] = []
    for v in variants:
        for psm in psms:
            cfg = f"--oem 3 --psm {int(psm)} -c user_defined_dpi=300"
            if whitelist:
                cfg += f" -c tessedit_char_whitelist={re.sub(r'\\s+', '', str(whitelist))}"
            try:
                txt = clean_text(pytesseract_mod.image_to_string(v, config=cfg), limit=1000)
            except Exception as exc:
                log.debug("focus recovery OCR failed: %s", exc)
                continue
            if txt and txt not in candidates:
                candidates.append(txt)
    def score(txt: str) -> Tuple[int, int, int]:
        toks = tokenize(txt, limit=80)
        useful = [t for t in toks if len(t) >= 3 and not t.isdigit()]
        known = 0
        for title, rx in _COMMON_TITLES:
            if re.search(rx, txt, re.I):
                known += 3
        for _, rx in _SEMANTIC_PATTERNS:
            if re.search(rx, txt, re.I):
                known += 1
        # Penalize punctuation confetti.
        garbage = len(re.findall(r"[^A-Za-z0-9\s:/.-]", txt))
        return (known, len(useful), -garbage)
    candidates.sort(key=score, reverse=True)
    return candidates[0] if candidates else ""

def _ocr_words(frame: np.ndarray, pytesseract_mod: Any = None) -> List[Dict[str, Any]]:
    pytesseract_mod = _get_pytesseract(pytesseract_mod)
    if pytesseract_mod is None or frame is None or not getattr(frame, "size", 0):
        return []
    scale = 1.6
    try:
        img = _prep_for_ocr(frame, scale=scale)
        data = pytesseract_mod.image_to_data(img, config="--oem 3 --psm 6 -c user_defined_dpi=300", output_type=pytesseract_mod.Output.DICT)
    except Exception as exc:
        log.debug("focus OCR data failed: %s", exc)
        return []
    out: List[Dict[str, Any]] = []
    n = len(data.get("text", []))
    for i in range(n):
        txt = clean_text(data["text"][i], limit=60)
        if not txt or not re.search(r"[A-Za-z0-9]", txt):
            continue
        try:
            conf = float(data.get("conf", [0])[i])
        except Exception:
            conf = 0.0
        # Tesseract returns -1 for structural entries.
        if conf < 20 and len(tokenize(txt, limit=2)) == 0:
            continue
        x = int(float(data["left"][i]) / scale)
        y = int(float(data["top"][i]) / scale)
        w = int(float(data["width"][i]) / scale)
        h = int(float(data["height"][i]) / scale)
        out.append({"text": txt, "x": x, "y": y, "w": w, "h": h, "cx": x + w / 2, "cy": y + h / 2, "conf": round(conf, 1)})
    return out


def _words_in_rect(words: Iterable[Dict[str, Any]], rect: Tuple[int, int, int, int], pad: int = 0) -> List[Dict[str, Any]]:
    x, y, w, h = rect
    x1, y1, x2, y2 = x - pad, y - pad, x + w + pad, y + h + pad
    return [wd for wd in words if x1 <= wd.get("cx", 0) <= x2 and y1 <= wd.get("cy", 0) <= y2]


def _line_groups(words: Iterable[Dict[str, Any]], y_tol: int = 18) -> List[List[Dict[str, Any]]]:
    rows: List[List[Dict[str, Any]]] = []
    for w in sorted(words, key=lambda wd: (wd.get("cy", 0), wd.get("x", 0))):
        if not rows:
            rows.append([w])
            continue
        row_y = sum(float(a.get("cy", 0)) for a in rows[-1]) / max(1, len(rows[-1]))
        if abs(float(w.get("cy", 0)) - row_y) <= y_tol:
            rows[-1].append(w)
        else:
            rows.append([w])
    return [sorted(r, key=lambda wd: wd.get("x", 0)) for r in rows]


def _safe_crop(frame: np.ndarray, rect: Tuple[int, int, int, int], pad: int = 0) -> np.ndarray:
    x, y, w, h = rect
    H, W = frame.shape[:2]
    x1 = max(0, int(x - pad))
    y1 = max(0, int(y - pad))
    x2 = min(W, int(x + w + pad))
    y2 = min(H, int(y + h + pad))
    if x2 <= x1 or y2 <= y1:
        return frame[0:0, 0:0]
    return frame[y1:y2, x1:x2]


# ─────────────────────────────────────────────────────────────────────────────
# Focus detection
# ─────────────────────────────────────────────────────────────────────────────

def red_focus_mask(bgr: np.ndarray) -> np.ndarray:
    """Strict-ish red focus mask, generalized from Jake's aBitTesty scripts."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, np.array((0, 115, 110)), np.array((13, 255, 255)))
    m2 = cv2.inRange(hsv, np.array((158, 115, 110)), np.array((180, 255, 255)))
    mask = cv2.bitwise_or(m1, m2)
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=1)
    return mask


def _detect_best_red_focus(frame: np.ndarray, words: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    H, W = frame.shape[:2]
    mask = red_focus_mask(frame)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best: Optional[Dict[str, Any]] = None
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if w <= 0 or h <= 0:
            continue
        area = float(cv2.contourArea(c))
        bbox_area = float(w * h)
        aspect = float(w / h)
        if area < 220 or bbox_area < 600 or bbox_area > 0.48 * W * H:
            continue
        if not (0.22 <= aspect <= 12.0):
            continue
        roi_mask = mask[y:y + h, x:x + w]
        red_density = float(np.mean(roi_mask > 0))
        if red_density < 0.03:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.035 * peri, True)
        rect = cv2.minAreaRect(c)
        box = cv2.boxPoints(rect).astype(int).tolist()
        vertices = int(len(approx))
        # True focus is usually a red outline/parallelogram: large bbox, 4-ish
        # corners, moderate red density. Solid red app/logo art (hearts, logos,
        # network bugs) is dense and often has many vertices. Score accordingly.
        quad_bonus = 0.30 if 4 <= vertices <= 5 else (0.08 if 6 <= vertices <= 8 else 0.0)
        density_score = min(1.0, red_density * 3.8)
        area_score = min(1.0, bbox_area / max(1.0, W * H * 0.08))
        outline_bonus = 0.12 if (0.035 <= red_density <= 0.24 and bbox_area > W * H * 0.006) else 0.0
        solid_art_penalty = 0.0
        if red_density > 0.34 and bbox_area < W * H * 0.02 and vertices > 5:
            solid_art_penalty = 0.24
        score = 0.52 * area_score + 0.26 * density_score + quad_bonus + outline_bonus - solid_art_penalty
        cx = (x + w / 2) / W
        cy = (y + h / 2) / H
        if 0.02 < cx < 0.98 and 0.02 < cy < 0.98:
            score += 0.05
        # Avoid the static red DISH logo being mistaken for focus.
        if x < W * 0.085 and y < H * 0.13 and bbox_area < W * H * 0.004:
            score -= 0.45
        # Avoid red TV network bugs in the live content unless very strong.
        if bbox_area < W * H * 0.002 and cy < 0.18:
            score -= 0.10
        # v11: word-aware focus selection. Network logos and red art often have
        # red blobs but no coherent UI label. True focus usually has text inside,
        # immediately below, or in the same row.
        if words:
            label_rect = (x - 6, y - 6, w + 12, int(h * 1.95))
            nearby_rect = (x - int(0.35 * w), y - int(0.30 * h), int(1.75 * w), int(1.70 * h))
            label_txt = _words_text(_words_in_rect(words, label_rect, pad=4), max_words=18)
            nearby_txt = _words_text(_words_in_rect(words, nearby_rect, pad=4), max_words=24)
            if meaningful(label_txt):
                score += 0.34
            elif meaningful(nearby_txt):
                score += 0.14
            # Bottom carousels/recent/recall overlays commonly put focus in the
            # bottom quarter. Prefer red rectangles there over red program logos.
            if y > H * 0.70 and h > H * 0.07 and 0.35 <= aspect <= 1.35:
                score += 0.22
            # Red text/logo inside live video should not beat a labeled tile.
            if not meaningful(label_txt) and 0.20 < cy < 0.78 and bbox_area < W * H * 0.015:
                score -= 0.10
        if best is None or score > best["score"]:
            best = {
                "score": max(0.0, score),
                "bbox": (x, y, w, h),
                "area": area,
                "aspect": aspect,
                "red_density": red_density,
                "corners": box,
                "vertices": vertices,
            }
    return best



# ─────────────────────────────────────────────────────────────────────────────
# v10 DISH layout semantic anchors
# ─────────────────────────────────────────────────────────────────────────────

_LOGO_WORD_RE = re.compile(r"^(?:d[:;.]?sh|dish|dsh|dzsh|dosh|dssh|d\s*sh)$", re.I)
_DATE_TIME_RE = re.compile(r"\b(?:sun|mon|tue|wed|thu|fri|sat)?\s*\d{1,2}/\d{1,2}|\d{1,2}:\d{2}\s*[ap]?\b", re.I)
_NAV_ROW_RE = re.compile(r"\bmenu\b.*\bhome\b.*\bshows?\b.*\bsports\b.*\bmovies\b", re.I)
_NAV_ONLY_TOKENS = {"menu", "home", "shows", "show", "sports", "movies", "movie", "stows", "mover", "users"}


def _canonicalize_ui_title(text: str) -> str:
    """Normalize noisy OCR into stable DISH UI titles where possible."""
    raw = clean_text(text, limit=180)
    raw = _DATE_TIME_RE.sub(" ", raw)
    raw = re.sub(r"\b(?:dish|d[:;]?sh|dzsh|dsh|pvr|on)\b", " ", raw, flags=re.I)
    raw = re.sub(r"[|\\/<>~^`]+", " ", raw)
    raw = clean_text(raw, limit=160).strip(" -:;,.|_")
    matched = _match_common_title(raw)
    if matched:
        return matched
    # Fix frequent OCR splits/corruptions for page names.
    fixes = [
        (r"\bparental\s+control\s+setting\b", "Parental Control Settings"),
        (r"\bparental\s+controls?\s+settings?\b", "Parental Control Settings"),
        (r"\btv\s+view(?:ing)?\s+options?\b", "TV Viewing Options"),
        (r"\bdiagnostics?\b", "Diagnostics"),
        (r"\blocked\s+channels?\b|\block(?:ed)?\s+channels?\b", "Locked Channels"),
    ]
    for rx, repl in fixes:
        if re.search(rx, raw, re.I):
            return repl
    return raw[:90]


def _looks_like_nav_tab_row(text: str) -> bool:
    low = clean_text(text, limit=240).lower()
    if _NAV_ROW_RE.search(low):
        return True
    toks = tokenize(low, limit=20)
    return len(toks) >= 3 and sum(t in _NAV_ONLY_TOKENS for t in toks) >= 3


def _dish_logo_present(frame: np.ndarray) -> bool:
    """Detect the small red DISH logo in the top-left title lane.

    This gates page-name crop fallback so grey-box titles don't masquerade as
    page names on overlay screens that have no DISH header.
    """
    if frame is None or not getattr(frame, "size", 0):
        return False
    H, W = frame.shape[:2]
    roi = frame[0:int(H * 0.13), 0:int(W * 0.12)]
    if roi.size == 0:
        return False
    mask = red_focus_mask(roi)
    # Logo is red but compact; require enough red pixels in the title lane.
    return int(np.count_nonzero(mask)) > max(45, int(roi.shape[0] * roi.shape[1] * 0.006))


def _title_candidate_ok(text: str) -> bool:
    t = clean_text(text, limit=120)
    if not t or len(t) < 3:
        return False
    if _looks_like_nav_tab_row(t):
        return False
    toks = tokenize(t, limit=10)
    if not toks:
        return False
    # Page/block titles are usually compact. Reject long instruction sentences.
    if len(toks) > 6 and not _match_common_title(t):
        return False
    bad = {"sun", "pvr", "sat", "button", "press", "remote", "control"}
    if all(tok in bad for tok in toks):
        return False
    return True


def _extract_active_tab_from_nav(words: List[Dict[str, Any]], frame_shape: Tuple[int, int, int]) -> str:
    """Infer active top nav tab from the DISH home nav row, if present."""
    H, W = frame_shape[:2]
    top = [w for w in words if w.get("cy", 9999) < H * 0.16 and w.get("x", 0) < W * 0.55]
    txt = _words_text(top, max_words=40).lower()
    if not _looks_like_nav_tab_row(txt):
        return ""
    # If focus is on top nav, the caller will know; here choose Home when the
    # navigation row is present and no page title exists, because that row is the
    # Home shell in DISH's UI.
    if "home" in txt:
        return "Home"
    return ""


def _line_text_without_dates(line: List[Dict[str, Any]]) -> str:
    txt = _words_text(line, max_words=20)
    txt = _DATE_TIME_RE.sub(" ", txt)
    return clean_text(txt, limit=160)


def _extract_page_name_after_dish(frame: np.ndarray, words: List[Dict[str, Any]], pytesseract_mod: Any = None) -> Tuple[str, str, str]:
    """Find the page name in the top-left, immediately after the DISH logo.

    On Hopper-style screens the page title is commonly rendered as:
        DISH  <Page Name>                         Sun 5/10 | 10:27a
    The old heuristic searched all header OCR and could be hijacked by live video
    or grid text. This routine deliberately looks in the small top-left title lane.
    Returns (canonical_page_name, raw_text, source).
    """
    H, W = frame.shape[:2]
    top_left = [w for w in words if w.get("cy", 9999) < H * 0.16 and w.get("x", 0) < W * 0.62]
    for line in _line_groups(top_left, y_tol=16):
        line = sorted(line, key=lambda wd: wd.get("x", 0))
        # Find a normal OCR logo token; if OCR splits d:sh into d/S/h, fall back to crop OCR below.
        logo_idx = None
        for i, wd in enumerate(line):
            if _LOGO_WORD_RE.match(clean_text(wd.get("text", "")).replace(" ", "")):
                logo_idx = i
                break
        if logo_idx is None:
            continue
        after: List[Dict[str, Any]] = []
        for wd in line[logo_idx + 1:]:
            if wd.get("x", 0) > W * 0.52:
                break
            if _DATE_TIME_RE.search(str(wd.get("text", ""))):
                break
            after.append(wd)
        raw = _line_text_without_dates(after)
        cand = _canonicalize_ui_title(raw)
        if _title_candidate_ok(cand):
            return cand, raw, "dish_after_logo_words"

    # Direct crop fallback: helps when Tesseract reads the logo as "d ~ S h".
    # Only use it when a red DISH logo is actually visible in the top-left;
    # otherwise grey panel titles such as "TV Viewing Options" can be falsely
    # promoted into page_name.
    if not _dish_logo_present(frame):
        return "", "", ""
    # Start just to the right of the logo and stay left of the clock/date area.
    crop = _safe_crop(frame, (int(W * 0.055), int(H * 0.018), int(W * 0.45), int(H * 0.13)), pad=0)
    raw = _ocr_image(crop, pytesseract_mod, psm=7) or _ocr_image(crop, pytesseract_mod, psm=6)
    raw = _DATE_TIME_RE.sub(" ", raw)
    raw = re.sub(r"^[^A-Za-z0-9]*(?:d\s*[:;.]?\s*s?\s*h|dish|dzsh|dsh|sh)\b", " ", raw, flags=re.I)
    raw = clean_text(raw, limit=160)
    cand = _canonicalize_ui_title(raw)
    if _title_candidate_ok(cand):
        return cand, raw, "dish_after_logo_crop"
    return "", raw, ""


def _detect_grey_menu_boxes(frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """Detect large grey menu panels/blocks.

    These are the smaller grey boxes used for screens such as TV Viewing Options.
    We look for low-saturation, mid-dark panels and return candidate rectangles.
    """
    if frame is None or not getattr(frame, "size", 0):
        return []
    H, W = frame.shape[:2]
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    # Low saturation, not pure black, not bright UI art. Tuned against the collected screenshots.
    mask = cv2.inRange(hsv, np.array((0, 0, 18)), np.array((180, 85, 115)))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: List[Tuple[int, int, int, int]] = []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        area = w * h
        if w < W * 0.18 or h < H * 0.12:
            continue
        if area < W * H * 0.025 or area > W * H * 0.72:
            continue
        # Avoid full-screen/dimmed video masks and tiny network bugs. A true menu
        # block may touch the bottom, but it rarely starts at y=0 and spans almost
        # the entire height.
        if (y <= 2 and h > H * 0.88) or y > H * 0.80 or x > W * 0.92:
            continue
        boxes.append((int(x), int(y), int(w), int(h)))
    # Largest/uppermost first, but prefer boxes near the focus later when used.
    boxes.sort(key=lambda b: (-(b[2] * b[3]), b[1], b[0]))
    return boxes[:6]


def _extract_block_title_from_grey_box(frame: np.ndarray, words: List[Dict[str, Any]], boxes: List[Tuple[int, int, int, int]], focus_bbox: Optional[Tuple[int, int, int, int]] = None, pytesseract_mod: Any = None) -> Tuple[str, str, Optional[List[int]], str]:
    """Read the title at the top of the smaller grey menu/block box."""
    if not boxes:
        return "", "", None, ""
    def contains_focus(b: Tuple[int, int, int, int]) -> int:
        if not focus_bbox:
            return 0
        x, y, w, h = b
        fx, fy, fw, fh = focus_bbox
        fcx, fcy = fx + fw / 2, fy + fh / 2
        return 1 if x <= fcx <= x + w and y <= fcy <= y + h else 0
    ordered = sorted(boxes, key=lambda b: (-contains_focus(b), b[1], -b[2] * b[3]))
    for b in ordered:
        x, y, w, h = b
        # Header strip at the top of the grey box. Keep it shallow so tile labels below do not hijack it.
        strip_h = max(28, min(int(0.16 * h), 74))
        title_rect = (x + int(0.03 * w), y + 4, int(0.72 * w), strip_h)
        title_words = _words_in_rect(words, title_rect, pad=6)
        raw = _words_text(title_words, max_words=16)
        if not meaningful(raw):
            raw = _ocr_image(_safe_crop(frame, title_rect, pad=2), pytesseract_mod, psm=7)
        cand = _canonicalize_ui_title(raw)
        if _title_candidate_ok(cand):
            return cand, clean_text(raw, 160), [int(v) for v in b], "grey_box_header"
    return "", "", [int(v) for v in ordered[0]], ""




def _extract_upper_block_title_from_words(words: List[Dict[str, Any]], frame_shape: Tuple[int, int, int]) -> Tuple[str, str, str]:
    """Fallback for semi-transparent overlays where grey-box contour is weak.

    Look for compact title-like text in the upper-center/upper-left content area,
    excluding the DISH title lane. This catches screens like TV Viewing Options
    when the background/video causes the panel mask to span the whole frame.
    """
    H, W = frame_shape[:2]
    candidates = []
    for line in _line_groups(words, y_tol=16):
        if not line:
            continue
        min_x = min(w.get("x", 0) for w in line)
        max_x = max(w.get("x", 0) + w.get("w", 0) for w in line)
        avg_y = sum(w.get("cy", 0) for w in line) / max(1, len(line))
        if not (H * 0.05 <= avg_y <= H * 0.24):
            continue
        # Exclude the left DISH logo/date lane unless this is clearly an overlay title.
        if max_x < W * 0.16:
            continue
        raw = _line_text_without_dates(line)
        cand = _canonicalize_ui_title(raw)
        if not _title_candidate_ok(cand):
            continue
        matched = _match_common_title(cand) or cand
        # Prefer canonical/common titles and short lines close to the top of a panel.
        common_bonus = 0 if not _match_common_title(cand) else -100
        candidates.append((common_bonus, abs(avg_y - H * 0.10), min_x, matched, raw))
    if not candidates:
        return "", "", ""
    candidates.sort(key=lambda x: (x[0], x[1], x[2]))
    _, _, _, title, raw = candidates[0]
    return title, clean_text(raw, 160), "upper_block_title_words"

def _pick_screen_and_menu_title(page_name: str, block_title: str, legacy_title: str) -> Tuple[str, str, str]:
    """Choose public screen/menu title fields while preserving separate v10 anchors."""
    if page_name:
        screen_title = page_name
        source = "page_name_after_dish"
    elif block_title:
        screen_title = block_title
        source = "grey_box_block_title"
    else:
        screen_title = legacy_title
        source = "legacy_header_ocr" if legacy_title else ""
    menu_title = block_title or page_name or legacy_title
    return screen_title, menu_title, source

# ─────────────────────────────────────────────────────────────────────────────
# Semantic/context inference
# ─────────────────────────────────────────────────────────────────────────────

def _match_common_title(text: str) -> str:
    low = clean_text(text, limit=3000).lower()
    # Prefer the title that appears earliest in the OCR stream. This matters on
    # screens like "TV Viewing Options ... Parental Controls ..." where several
    # known feature names appear, but the actual screen title is the first one.
    best: Optional[Tuple[int, int, str]] = None
    for title, pattern in _COMMON_TITLES:
        m = re.search(pattern, low, re.I)
        if not m:
            continue
        cand = (int(m.start()), -len(title), title)
        if best is None or cand < best:
            best = cand
    return best[2] if best else ""


def _extract_header_title(words: List[Dict[str, Any]], frame_shape: Tuple[int, int, int], fallback_text: str = "") -> Tuple[str, str, str]:
    H, W = frame_shape[:2]
    header_words = [w for w in words if w.get("cy", 9999) < H * 0.20]
    header_text = _words_text(header_words, max_words=80)
    specific_titles = {"TV Viewing Options", "Parental Control Settings", "Diagnostics", "Remote Diagnostics", "TV Show Details"}
    # First inspect header lines individually. A nav row may mention Home/Guide,
    # while the actual page title sits just below it; the line-level check prevents
    # the nav tab from stealing the title.
    for line in _line_groups(header_words, y_tol=14):
        line_txt = _words_text(line, max_words=20)
        m = _match_common_title(line_txt)
        if m in specific_titles:
            return m, header_text, ""
    matched = _match_common_title(" ".join([header_text, fallback_text]))
    if matched:
        active_tab = matched if matched in {"Home", "Guide", "Search", "DVR", "Apps", "On Demand"} else ""
        return matched, header_text, active_tab

    # Line-based fallback: pick first meaningful header line after removing date/time/logo garbage.
    date_re = re.compile(r"\b(?:sun|mon|tue|wed|thu|fri|sat)?\s*\d{1,2}/\d{1,2}|\d{1,2}:\d{2}[ap]?\b", re.I)
    best_line = ""
    for line in _line_groups(header_words, y_tol=14):
        txt = _words_text(line, max_words=12)
        txt = date_re.sub(" ", txt)
        txt = re.sub(r"\bd[:;]?sh\b|\bdish\b|\bpvr\b|\bon\b", " ", txt, flags=re.I)
        txt = clean_text(txt, limit=120)
        if len(tokenize(txt, limit=10)) >= 1 and len(txt) > len(best_line):
            best_line = txt
    # Normalize noisy header lines that contain a clear canonical tab/title.
    low_best = best_line.lower()
    for canonical in ("Home", "Guide", "Search", "DVR", "Settings", "Diagnostics", "Apps", "Options"):
        if canonical.lower() in low_best:
            return canonical, header_text, canonical if canonical in {"Home", "Guide", "Search", "DVR", "Apps"} else ""
    return best_line[:80], header_text, ""


def _semantic_tags(text: str) -> List[str]:
    low = str(text or "").lower()
    tags = [tag for tag, rx in _SEMANTIC_PATTERNS if re.search(rx, low, re.I)]
    return sorted(set(tags))


def _risk_flags(text: str) -> List[str]:
    low = str(text or "").lower()
    return sorted(term for term in _RISK_TERMS if re.search(rf"\b{re.escape(term)}\b", low))


def _infer_region(cx: float, cy: float, W: int, H: int) -> str:
    if cy < H * 0.22:
        return "top/nav"
    if cy > H * 0.78:
        return "bottom/action"
    if cx < W * 0.25:
        return "left-pane"
    if cx > W * 0.74:
        return "right-pane"
    return "center-grid"


def _clean_focus_candidate(text: str) -> str:
    txt = clean_text(text, limit=140)
    # Trim instruction/footer noise if present.
    txt = re.sub(r"\bpress\s+(?:select|page|back).*", "", txt, flags=re.I).strip(" -|:")
    # Menu tiles often OCR as "1 TV Activity" or "4 Picture In Picture".
    txt = re.sub(r"^\s*\d{1,2}\s+", "", txt).strip(" -|:_")
    # Remove leading single-character OCR crumbs like "e " but do not damage
    # real acronyms such as TV, DVR, CC.
    txt = re.sub(r"^(?:[A-Za-z]\s+){1,2}(?=[A-Za-z]{3,})", "", txt).strip(" -|:_")
    toks = tokenize(txt, limit=20)
    if not toks:
        return ""
    # If OCR produced mostly 1-2 char garbage, reject.
    meaningful_toks = [t for t in toks if len(t) >= 3 or t in {"cc", "on", "off", "ok"}]
    if not meaningful_toks and not re.search(r"\d{2,4}|cc|ok|on|off", txt, re.I):
        return ""
    # If a channel tile label is embedded in OCR junk, keep the clean channel label.
    m_ch = re.search(r"\b([A-Z]{2,8})\s+(\d{2,4})\b", txt)
    if m_ch:
        return f"{m_ch.group(1)} {m_ch.group(2)}"
    if len(txt) <= 3 and not re.search(r"\d{2,4}|cc|ok|on|off", txt, re.I):
        return ""
    return txt[:120]


def _extract_setting_pairs(row_text: str, left_text: str = "", right_text: str = "") -> List[Dict[str, str]]:
    candidates = []
    for src_name, src in [("row", row_text), ("left_right", f"{left_text} {right_text}")]:
        txt = clean_text(src, limit=240)
        if not txt:
            continue
        m = _VALUE_RE.search(txt)
        if not m:
            continue
        val = clean_text(m.group("value"), limit=50)
        label = clean_text(txt[: m.start()], limit=120).strip(" -|:?>")
        if not label:
            label = clean_text(left_text, limit=120).strip(" -|:?>")
        if label and val:
            candidates.append({"label": label[:90], "value": val[:50], "source": src_name})
    # de-dupe by label/value
    seen = set()
    out = []
    for c in candidates:
        key = (c["label"].lower(), c["value"].lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out[:4]




def _infer_home_top_nav_item(cx_norm: float, cy_norm: float) -> str:
    """Map the fixed DISH Home top navigation tab positions when OCR is bad."""
    if cy_norm > 0.17 or not (0.08 <= cx_norm <= 0.38):
        return ""
    tabs = [
        (0.105, 0.145, "Menu"),
        (0.145, 0.190, "Home"),
        (0.190, 0.245, "Shows"),
        (0.245, 0.305, "Sports"),
        (0.305, 0.370, "Movies"),
    ]
    for lo, hi, name in tabs:
        if lo <= cx_norm <= hi:
            return name
    return ""

def _infer_focus_role(region: str, title: str, tags: List[str], row_text: str, item: str, pairs: List[Dict[str, str]]) -> str:
    text = " ".join([title, row_text, item]).lower()
    if pairs or "settings" in tags or "parental" in tags:
        if re.search(r"\b(on|off|none|yes|no|channels?|passcode|locked|favorite)\b", text):
            return "setting-row"
        return "settings-item"
    if region == "bottom/action" or "actions" in tags:
        return "action-button"
    if "guide" in tags:
        return "guide-cell"
    if "channel" in tags or "live tv" in text:
        return "content/channel"
    if region in {"top/nav", "left-pane"}:
        return "navigation-item"
    return "menu-item"


def _choose_focused_item(focus_text: str, label_text: str, context_text: str, row_text: str, neighbor_text: Dict[str, str], pairs: List[Dict[str, str]]) -> Tuple[str, str]:
    # Prefer text physically inside/under the focus over same-row text. This is
    # the human interpretation: the focused tile label beats the entire row.
    for candidate in [focus_text, label_text]:
        c = _clean_focus_candidate(candidate)
        if c:
            return c, ""
    if pairs:
        return pairs[0].get("label", ""), pairs[0].get("value", "")
    for candidate in [context_text, row_text, neighbor_text.get("left", ""), neighbor_text.get("right", "")]:
        c = _clean_focus_candidate(candidate)
        if c:
            return c, ""
    return "", ""


def _context_confidence(focus_conf: float, title: str, item: str, row_text: str, pairs: List[Dict[str, str]], tags: List[str]) -> float:
    score = 0.32 * max(0.0, min(1.0, focus_conf))
    if title:
        score += 0.22
    if item:
        score += 0.18
    if row_text and meaningful(row_text):
        score += 0.12
    if pairs:
        score += 0.10
    if tags:
        score += 0.06
    return round(max(0.0, min(1.0, score)), 4)


def _build_human_label(title: str, item: str, value: str, role: str) -> str:
    parts = []
    if title:
        parts.append(title)
    if item:
        bits = item
        if value:
            bits += f" = {value}"
        parts.append(bits)
    elif role:
        parts.append(role)
    return " → ".join(parts)[:120]




# ─────────────────────────────────────────────────────────────────────────────
# v11 recovery / popup / live-TV understanding
# ─────────────────────────────────────────────────────────────────────────────

_PIN_POPUP_RE = re.compile(
    r"\b(enter|input|type|provide).{0,24}(pin|passcode|password)|\b(pin|passcode|password).{0,24}(required|needed|enter)|\bparental.{0,40}(locked|controls?|passcode|pin)|\blocked.{0,30}(channel|program|event|content)\b",
    re.I,
)
_CHANNEL_LINE_RE = re.compile(r"\b(?P<name>[A-Z][A-Z0-9&+ .'-]{1,18})\s+(?P<ch>\d{2,4})\b")
_LIVE_TV_RE = re.compile(r"\blive\s+tv\b|\b\d{1,2}:\d{2}\s*[ap]?\b|\b\d+h\s+\d{1,2}m\s+left\b|\bMoCA\b", re.I)




def _extract_left_strip_title(words: List[Dict[str, Any]], frame_shape: Tuple[int, int, int]) -> str:
    """Detect DISH overlay category labels in the left grey strip.

    Examples from collected data: "Recall", "Trending Live". These are not in
    the top DISH page lane and not inside a grey box header, but a human still
    reads them as the current block/menu title.
    """
    H, W = frame_shape[:2]
    left = [w for w in words if w.get("cx", 0) < W * 0.16 and w.get("cy", 0) > H * 0.55]
    txt = _words_text(left, max_words=18)
    txt = clean_text(txt, limit=100).strip(" -|:_")
    low = txt.lower()
    if "recall" in low:
        return "Recall"
    if "trending" in low and "live" in low:
        return "Trending Live"
    if "trending" in low:
        return "Trending"
    if len(tokenize(txt, 8)) in (1, 2, 3) and len(txt) <= 40:
        return txt
    return ""

def _detect_pin_popup_text(text: str) -> Tuple[str, bool]:
    t = clean_text(text, limit=3000)
    if _PIN_POPUP_RE.search(t):
        if re.search(r"\bparental\b", t, re.I):
            return "parental_pin_prompt", True
        return "pin_prompt", True
    return "", False


def _extract_live_tv_context(text: str) -> Dict[str, str]:
    t = clean_text(text, limit=2500)
    if not _LIVE_TV_RE.search(t):
        return {}
    # Prefer explicit channel-name + number pairs; ignore dates/times.
    best_name = ""
    best_ch = ""
    for m in _CHANNEL_LINE_RE.finditer(t):
        name = clean_text(m.group("name"), 40).strip(" -:|.")
        ch = m.group("ch")
        if ch and not re.match(r"20\d\d|10|11|12|13|14|15|16|17|18|19$", ch):
            best_name, best_ch = name, ch
            break
    # Program title often sits before "Live TV" or before the channel/time line.
    program = ""
    m = re.search(r"(?:Live TV\s+)?(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)?\s*\d{1,2}/\d{1,2}.*?\b(?:left|[AP]M)\s+(?P<prog>[A-Za-z0-9 '&,.:-]{3,70})\s+(?P<chname>[A-Z]{2,8})\s+(?P<ch>\d{2,4})", t, re.I)
    if m:
        program = clean_text(m.group("prog"), 70)
        best_name = best_name or clean_text(m.group("chname"), 20)
        best_ch = best_ch or m.group("ch")
    return {"screen_title": "Live TV", "channel_number": best_ch, "channel_name": best_name, "program_title": program}


def _quality_flags_for_observation(found: bool, conf: float, title: str, item: str, ocr_text: str, popup_type: str = "") -> List[str]:
    flags: List[str] = []
    if not found:
        flags.append("no_focus_detected")
    elif conf < 0.25:
        flags.append("low_focus_confidence")
    if not title and not popup_type:
        flags.append("missing_screen_title")
    if not item and found:
        flags.append("missing_focused_item")
    if item and (len(tokenize(item, 8)) == 0 or re.fullmatch(r"[\W_0-9a-zA-Z]{1,3}", item.strip())):
        flags.append("weak_focused_item_ocr")
    # OCR soup: many symbols, few useful words.
    useful = tokenize(ocr_text, 40)
    if ocr_text and len(useful) < 3 and len(ocr_text) > 80:
        flags.append("ocr_soup")
    if popup_type:
        flags.append(f"popup:{popup_type}")
    return sorted(set(flags))


def _recover_focus_label_with_context(frame: np.ndarray, bbox: Tuple[int, int, int, int], words: List[Dict[str, Any]], pytesseract_mod: Any = None) -> Tuple[str, str]:
    """Try harder to name the focused thing when normal inside/below OCR fails."""
    x, y, w, h = bbox
    H, W = frame.shape[:2]
    # A human reads the tile, the text immediately under it, then the row/pane.
    regions = [
        ("tile_plus_label", (x - 8, y - 8, w + 16, int(h * 1.95))),
        ("wide_row", (max(0, x - int(w * .9)), max(0, y - int(h * .45)), min(W, int(w * 2.8)), int(h * 2.1))),
        ("right_detail", (min(W-1, x + w), max(0, y - int(h * .6)), max(1, W - x - w), int(h * 2.6))),
        ("below", (max(0, x - int(w * .35)), y + h, int(w * 1.7), int(h * 1.3))),
    ]
    candidates: List[Tuple[str, str]] = []
    for name, rect in regions:
        crop = _safe_crop(frame, rect, pad=4)
        txt = _ocr_image_multi(crop, pytesseract_mod, psms=(7, 6, 11))
        txt = _clean_focus_candidate(txt)
        if txt:
            candidates.append((name, txt))
    # Word geometry fallback.
    for name, rect in regions[:2]:
        txt = _clean_focus_candidate(_words_text(_words_in_rect(words, rect, pad=8), max_words=20))
        if txt:
            candidates.append((name + "_words", txt))
    if not candidates:
        return "", ""
    # Prefer candidates containing known UI words or setting-like values.
    def score(pair: Tuple[str, str]) -> Tuple[int, int, int]:
        name, txt = pair
        common = 1 if _match_common_title(txt) else 0
        values = 1 if _VALUE_RE.search(txt) else 0
        toks = tokenize(txt, 30)
        return (common + values, len([t for t in toks if len(t) >= 3]), -len(txt))
    candidates.sort(key=score, reverse=True)
    return candidates[0]

# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def detect_focus(frame: np.ndarray, pytesseract_mod: Any = None) -> Dict[str, Any]:
    if frame is None or not getattr(frame, "size", 0):
        return FocusObservation(found=False, warning="empty frame").to_dict()

    H, W = frame.shape[:2]
    words = _ocr_words(frame, pytesseract_mod)
    best = _detect_best_red_focus(frame, words)
    whole_text_from_words = _words_text(words, max_words=260)
    legacy_title, header_text, active_tab = _extract_header_title(words, frame.shape, fallback_text=whole_text_from_words)
    live_ctx = _extract_live_tv_context(whole_text_from_words)
    popup_type, pin_required = _detect_pin_popup_text(whole_text_from_words)
    page_name, page_raw, page_source = _extract_page_name_after_dish(frame, words, pytesseract_mod)
    grey_boxes = _detect_grey_menu_boxes(frame)
    # best may not exist yet; block title can still be learned without a red focus.
    focus_bbox_for_title = tuple(best["bbox"]) if best else None
    block_title, block_raw, grey_box_bbox, block_source = _extract_block_title_from_grey_box(frame, words, grey_boxes, focus_bbox_for_title, pytesseract_mod)
    if not block_title and not page_name:
        block_title, block_raw, block_source = _extract_upper_block_title_from_words(words, frame.shape)
    if not block_title and not page_name:
        strip_title = _extract_left_strip_title(words, frame.shape)
        if strip_title:
            block_title, block_source = strip_title, "left_overlay_strip"
    # Only trust the legacy title when it matches a known UI title; otherwise
    # live video OCR can hallucinate page names from captions/background art.
    if not page_name and not block_title and live_ctx and legacy_title not in {"Guide", "Search", "DVR", "Home", "Settings", "Diagnostics", "Parental Control Settings", "TV Viewing Options", "Locked Channels"}:
        legacy_title = "Live TV"
    if popup_type:
        legacy_title = "Parental Control PIN Prompt" if popup_type == "parental_pin_prompt" else "PIN Prompt"
    title, menu_title, title_source = _pick_screen_and_menu_title(page_name, block_title, legacy_title)
    if page_name:
        title_source = page_source or "page_name_after_dish"
    elif block_title:
        title_source = block_source or "block_title"
    if not active_tab:
        active_tab = _extract_active_tab_from_nav(words, frame.shape)
    if not active_tab and title in {"Home", "Guide", "Search", "DVR", "Apps", "On Demand"}:
        active_tab = title
    action_bar_words = [w for w in words if w.get("cy", 0) > H * 0.82]
    action_bar_text = _words_text(action_bar_words, max_words=60)

    if not best:
        tags = _semantic_tags(" ".join([title, menu_title, page_name, block_title, header_text, whole_text_from_words, action_bar_text]))
        risks = _risk_flags(" ".join([title, menu_title, page_name, block_title, header_text, whole_text_from_words, action_bar_text]))
        quality_flags = _quality_flags_for_observation(False, 0.0, title or menu_title, "", whole_text_from_words, popup_type)
        obs = FocusObservation(
            found=False,
            confidence=0.0,
            header_text=header_text,
            action_bar_text=action_bar_text,
            screen_title=title,
            menu_title=menu_title,
            page_name=page_name,
            block_title=block_title,
            title_source=title_source,
            grey_box_bbox=grey_box_bbox,
            active_tab=active_tab,
            semantic_tags=tags,
            risk_flags=risks,
            quality_flags=quality_flags,
            recovery_text=whole_text_from_words[:1000],
            popup_type=popup_type,
            pin_required=pin_required,
            channel_number=live_ctx.get("channel_number", ""),
            channel_name=live_ctx.get("channel_name", ""),
            tokens=tokenize(" ".join([title, menu_title, page_name, block_title, header_text, whole_text_from_words, action_bar_text])),
            warning="red focus not detected",
        )
        obs.human_label = title or menu_title or ("PIN prompt" if pin_required else "No focus detected")
        obs.context_confidence = _context_confidence(0.0, title or menu_title, "", "", [], tags)
        return obs.to_dict()

    x, y, w, h = best["bbox"]
    cx = x + w / 2.0
    cy = y + h / 2.0
    region = _infer_region(cx, cy, W, H)

    focus_crop = _safe_crop(frame, (x, y, w, h), pad=6)
    label_rect = (x, y + h + int(0.04 * h), w, int(0.70 * h))
    label_crop = _safe_crop(frame, label_rect, pad=4)
    context_rect = (x - int(0.55 * w), y - int(0.55 * h), int(2.10 * w), int(2.20 * h))
    context_crop = _safe_crop(frame, context_rect, pad=8)
    row_rect = (0, y - int(0.35 * h), W, int(1.85 * h))
    left_rect = (0, y - int(0.35 * h), max(1, x), int(1.60 * h))
    right_rect = (x + w, y - int(0.35 * h), max(1, W - (x + w)), int(1.60 * h))
    above_rect = (max(0, x - int(0.35 * w)), max(0, y - int(1.10 * h)), int(1.70 * w), int(1.00 * h))
    below_rect = (max(0, x - int(0.35 * w)), y + h, int(1.70 * w), int(1.20 * h))

    # OCR both by geometry-word data and by direct crop OCR. They fail differently;
    # combining them gives much more human-readable context.
    inside_words = _words_in_rect(words, (x, y, w, h), pad=8)
    context_words = _words_in_rect(words, context_rect, pad=8)
    row_words = _words_in_rect(words, row_rect, pad=0)
    focus_text_ocr = _ocr_image(focus_crop, pytesseract_mod, psm=6)
    focus_text_words = _words_text(inside_words, max_words=18)
    # Prefer direct OCR only when it is meaningful. Icon-only crops often produce
    # tiny garbage like "e 7" while word-geometry correctly sees the tile label.
    focus_text = focus_text_ocr if _clean_focus_candidate(focus_text_ocr) else focus_text_words
    label_text = _ocr_image(label_crop, pytesseract_mod, psm=7, whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_&:+./")
    if not _clean_focus_candidate(label_text):
        label_words = _words_in_rect(words, label_rect, pad=8)
        label_text = _words_text(label_words, max_words=12)
    context_text = _ocr_image(context_crop, pytesseract_mod, psm=6) or _words_text(context_words, max_words=50)
    row_text = _ocr_image(_safe_crop(frame, row_rect), pytesseract_mod, psm=6) or _words_text(row_words, max_words=80)
    neighbor_text = {
        "left": _ocr_image(_safe_crop(frame, left_rect), pytesseract_mod, psm=6),
        "right": _ocr_image(_safe_crop(frame, right_rect), pytesseract_mod, psm=6),
        "above": _ocr_image(_safe_crop(frame, above_rect), pytesseract_mod, psm=6),
        "below": _ocr_image(_safe_crop(frame, below_rect), pytesseract_mod, psm=6),
    }
    # If direct OCR was noisy/empty, word geometry may still help.
    if not meaningful(row_text):
        row_text = _words_text(row_words, max_words=80)
    if not meaningful(context_text):
        context_text = _words_text(context_words, max_words=50)

    all_text = " ".join([
        title, menu_title, page_name, block_title, header_text, focus_text, label_text, context_text, row_text,
        neighbor_text.get("left", ""), neighbor_text.get("right", ""), action_bar_text,
    ])
    # Sometimes the common title appears outside the explicit page/block anchors; use it as fallback.
    if not title:
        legacy_fallback = _match_common_title(all_text)
        title, menu_title, title_source = _pick_screen_and_menu_title(page_name, block_title, legacy_fallback)
        if page_name:
            title_source = page_source or "page_name_after_dish"
        elif block_title:
            title_source = block_source or "block_title"
    if live_ctx and (not title or title == "Live TV"):
        title = "Live TV"
        menu_title = menu_title or "Live TV"
    if popup_type:
        title = "Parental Control PIN Prompt" if popup_type == "parental_pin_prompt" else "PIN Prompt"
        menu_title = title
        title_source = "popup_text"
    pairs = _extract_setting_pairs(row_text, neighbor_text.get("left", ""), neighbor_text.get("right", ""))
    item, value = _choose_focused_item(focus_text, label_text, context_text, row_text, neighbor_text, pairs)
    recovery_source = ""
    recovery_text = ""
    if not item or "weak_focused_item_ocr" in _quality_flags_for_observation(True, float(best["score"]), title, item, all_text, popup_type):
        recovery_source, recovery_text = _recover_focus_label_with_context(frame, (x, y, w, h), words, pytesseract_mod)
        if recovery_text and (not item or len(tokenize(recovery_text, 12)) >= len(tokenize(item, 12))):
            item = recovery_text
            value = ""
    top_nav_item = _infer_home_top_nav_item(cx / W, cy / H)
    if top_nav_item and (title == "Home" or active_tab == "Home" or _looks_like_nav_tab_row(header_text + " " + row_text)):
        item, value = top_nav_item, ""
    tags = _semantic_tags(all_text)
    risks = _risk_flags(all_text)
    role = _infer_focus_role(region, title, tags, row_text, item, pairs)
    human = _build_human_label(title, item, value, role)
    ctx_conf = _context_confidence(float(best["score"]), title, item, row_text, pairs, tags)
    nearby = tokenize(" ".join([focus_text, label_text, context_text, row_text]), limit=60)
    all_tokens = tokenize(all_text, limit=160)

    quality_flags = _quality_flags_for_observation(True, float(best["score"]), title, item, all_text, popup_type)
    obs = FocusObservation(
        found=True,
        confidence=round(max(0.0, min(1.0, best["score"])), 4),
        bbox=[int(x), int(y), int(w), int(h)],
        bbox_norm=[round(x / W, 4), round(y / H, 4), round(w / W, 4), round(h / H, 4)],
        center_norm=[round(cx / W, 4), round(cy / H, 4)],
        corners=[[int(a), int(b)] for a, b in best["corners"]],
        area=round(float(best["area"]), 2),
        aspect=round(float(best["aspect"]), 3),
        red_density=round(float(best["red_density"]), 4),
        contour_vertices=int(best["vertices"]),
        focus_text=clean_text(focus_text, 500),
        context_text=clean_text(context_text, 700),
        label_text=clean_text(label_text, 260),
        row_text=clean_text(row_text, 700),
        header_text=clean_text(header_text, 500),
        action_bar_text=clean_text(action_bar_text, 500),
        screen_title=clean_text(title, 120),
        menu_title=clean_text(menu_title, 120),
        page_name=clean_text(page_name, 120),
        block_title=clean_text(block_title, 120),
        title_source=title_source,
        grey_box_bbox=grey_box_bbox,
        active_tab=active_tab,
        focused_item=clean_text(item, 160),
        focused_value=clean_text(value, 80),
        human_label=human,
        focus_role=role,
        context_confidence=ctx_conf,
        neighbor_text={k: clean_text(v, 400) for k, v in neighbor_text.items()},
        setting_pairs=pairs,
        semantic_tags=tags,
        risk_flags=risks,
        quality_flags=quality_flags,
        recovery_text=clean_text(recovery_text or all_text, 1200),
        popup_type=popup_type,
        pin_required=pin_required,
        channel_number=live_ctx.get("channel_number", ""),
        channel_name=live_ctx.get("channel_name", ""),
        nearby_words=nearby,
        tokens=all_tokens,
        row_guess=int(min(5, max(0, cy / max(1, H) * 5))),
        col_guess=int(min(7, max(0, cx / max(1, W) * 7))),
        region=region,
    )
    return obs.to_dict()


def draw_focus_overlay(frame: np.ndarray, focus: Optional[Dict[str, Any]] = None) -> np.ndarray:
    if frame is None or not getattr(frame, "size", 0):
        return frame
    out = frame.copy()
    focus = focus or detect_focus(frame)
    H, W = out.shape[:2]
    ui0 = focus.get("ui_context") or {}
    title = str(focus.get("page_name") or focus.get("screen_title") or ui0.get("page_name") or ui0.get("screen_title") or "").strip()
    block_title = str(focus.get("block_title") or ui0.get("block_title") or "").strip()
    if not focus.get("found") or not focus.get("bbox"):
        cv2.putText(out, f"focus: not detected  page: {title[:42]}", (24, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 255), 2)
        return out
    x, y, w, h = [int(v) for v in focus["bbox"]]
    corners = focus.get("corners") or []
    if len(corners) >= 4:
        pts = np.array(corners, dtype=np.int32)
        cv2.polylines(out, [pts], True, (0, 255, 0), 4)
    else:
        cv2.rectangle(out, (x, y), (x + w, y + h), (0, 255, 0), 4)

    ui = focus.get("ui_context") or {}
    label = focus.get("human_label") or ui.get("human_label") or focus.get("focused_item") or focus.get("label_text") or focus.get("focus_text") or focus.get("region") or "focus"
    label = clean_text(str(label), 95)
    top_label = f"{focus.get('confidence', 0):.2f}/{focus.get('context_confidence', 0):.2f}  {label}"
    box_w = min(W - x - 4, max(260, len(top_label) * 10))
    cv2.rectangle(out, (x, max(0, y - 42)), (min(W - 1, x + box_w), y), (0, 0, 0), -1)
    cv2.putText(out, top_label[:90], (x + 6, max(24, y - 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)

    if title or block_title:
        title_line = f"PAGE: {title[:42]}" if title else "PAGE: ?"
        if block_title and block_title.lower() != title.lower():
            title_line += f"  BOX: {block_title[:36]}"
        cv2.rectangle(out, (16, 14), (min(W - 1, 900), 54), (0, 0, 0), -1)
        cv2.putText(out, title_line[:95], (24, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (190, 230, 255), 2)
    # Draw detected grey/menu box header region as cyan so the operator can see
    # which block supplied the block_title.
    gbb = focus.get("grey_box_bbox") or ui.get("grey_box_bbox")
    if gbb and len(gbb) == 4:
        gx, gy, gw, gh = [int(v) for v in gbb]
        cv2.rectangle(out, (gx, gy), (gx + gw, gy + gh), (255, 220, 0), 2)
    row = clean_text(str(focus.get("row_text") or ""), 90)
    if row:
        cv2.rectangle(out, (16, H - 46), (min(W - 1, 1100), H - 10), (0, 0, 0), -1)
        cv2.putText(out, f"ROW: {row[:100]}", (24, H - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 255, 220), 1)
    return out
