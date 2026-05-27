#!/usr/bin/env python3
"""DISH channel/program metadata extraction for channel surfing.

v25 adds hyphenated-channel support and live-banner validation on top of trusted-field gating so broad region-first/OCR fallbacks cannot
promote noisy video texture into program titles.

The generic focus/OCR layer is intentionally broad.  Channel surfing needs a
more opinionated reader because the same UI exposes specific facts in stable
places:

* Live banner: program title/description/channel/time in the top overlay.
* Guide: selected row/tile plus the right-side detail panel.
* TV Show / Info: title, channel, number, episode/info, and action buttons.

This module uses geometry first and text second.  It avoids the old failure mode
where a random phone number, time, or noisy OCR token became the "channel name".
"""
from __future__ import annotations

import re
import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import cv2
import numpy as np

try:  # Optional at runtime.
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    pytesseract = None  # type: ignore


TIME_RX = re.compile(r"\b(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)\s+\d{1,2}/\d{1,2}\s*(?:[|+\-–]+\s*)?\d{1,2}:\d{2}\s*[ap]m?\b", re.I)
TIME_ONLY_RX = re.compile(r"\b\d{1,2}:\d{2}\s*[ap]m?\b", re.I)
RANGE_RX = re.compile(r"\b\d{1,2}:\d{2}\s*[ap]?\s*[-–]\s*\d{1,2}:\d{2}\s*[ap]?\b", re.I)
CHANNEL_NUM_RX_PART = r"\d{2,4}(?:[-–]\d{1,3})?"
CHANNEL_LINE_RX = re.compile(
    rf"\b(?:(?P<num1>{CHANNEL_NUM_RX_PART})\s+(?P<code1>[A-Z][A-Z0-9&+!]{{1,10}})|(?P<code2>[A-Z][A-Z0-9&+!]{{1,10}})\s+(?P<num2>{CHANNEL_NUM_RX_PART}))\b"
)
PHONEISH_RX = re.compile(r"\b\d{3}[-\s]?\d{3}[-\s]?\d{4}\b")
BAD_CHANNEL_CODES = {"SAT", "TODAY", "LIVE", "GUIDE", "DISH", "HD", "TV", "SHOW", "S1", "EP", "CC", "MINS", "MIN", "REMAINING", "FIRST", "AIRED", "NOW", "ON", "WATCH", "RECORD"}
STOP_WORDS = {
    "dish", "guide", "live", "tv", "show", "summary", "episodes", "cast", "parental", "guide",
    "today", "showing", "all", "subscribed", "press", "watch", "record", "this", "series", "mins", "remaining",
}




@dataclass
class GuideProgramCell:
    row_index: int
    col_index: int
    title: str = ""
    raw_text: str = ""
    time_label: str = ""
    channel_number: str = ""
    channel_code: str = ""
    selected: bool = False
    bbox_norm: List[float] = field(default_factory=list)
    button_sequence: List[str] = field(default_factory=list)


@dataclass
class GuideChannelRow:
    row_index: int
    channel_number: str = ""
    channel_code: str = ""
    channel_name: str = ""
    channel_logo_text: str = ""
    icon_signature: str = ""
    bbox_norm: List[float] = field(default_factory=list)
    programs: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class GuideGridAnalysis:
    screen_type: str = "guide_grid"
    detected: bool = False
    confidence: float = 0.0
    selected: Dict[str, Any] = field(default_factory=dict)
    rows: List[Dict[str, Any]] = field(default_factory=list)
    programs: List[Dict[str, Any]] = field(default_factory=list)
    timeline_headers: List[str] = field(default_factory=list)
    geometry: Dict[str, Any] = field(default_factory=dict)
    counts: Dict[str, int] = field(default_factory=dict)
    source: str = "guide_grid_geometry_v34"
    quality_flags: List[str] = field(default_factory=list)
    interpretation: str = (
        "The DISH guide is a selectable grid: each visible row is a channel, "
        "the left strip contains the channel number/code/logo/icon identity, "
        "and each time cell in that row is a selectable program option."
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChannelMetadata:
    screen_type: str = "unknown"  # live_banner, guide, info, unknown
    channel_number: str = ""
    channel_code: str = ""
    channel_name: str = ""
    channel_logo_text: str = ""
    program_title: str = ""
    program_subtitle: str = ""
    program_description: str = ""
    program_time_range: str = ""
    displayed_datetime_text: str = ""
    focused_program: str = ""
    confidence: float = 0.0
    source: str = ""
    raw_regions: Dict[str, str] = field(default_factory=dict)
    quality_flags: List[str] = field(default_factory=list)
    # v25: Live banner QA. Present on all metadata records so dashboard CSVs are stable.
    banner_valid: bool = False
    banner_validation_score: float = 0.0
    banner_validation_flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clean_text(text: Any, limit: int = 600) -> str:
    s = str(text or "")
    repl = {
        "|": " | ", "\n": " ", "\r": " ", "\t": " ", "…": "...", "“": '"', "”": '"',
        "‘": "'", "’": "'", "—": "-", "–": "-", "·": " ", "•": " ",
    }
    for a, b in repl.items():
        s = s.replace(a, b)
    s = re.sub(r"\s+", " ", s).strip()
    # Repair common OCR variants seen in DISH screenshots.
    s = re.sub(r"\bL[i1]ve\s*TV\b", "Live TV", s, flags=re.I)
    s = re.sub(r"\bd[=\-]?s\s*h\b", "dish", s, flags=re.I)
    s = re.sub(r"\bHow\s*[|1l]\s*Met\b", "How I Met", s, flags=re.I)
    s = re.sub(r"^[-~_>7\s]+(?=[A-Za-z])", "", s).strip()
    return s[:limit]


def _norm_box(frame: np.ndarray, box: Tuple[float, float, float, float]) -> np.ndarray:
    h, w = frame.shape[:2]
    x1 = max(0, min(w, int(round(box[0] * w))))
    y1 = max(0, min(h, int(round(box[1] * h))))
    x2 = max(0, min(w, int(round(box[2] * w))))
    y2 = max(0, min(h, int(round(box[3] * h))))
    if x2 <= x1 or y2 <= y1:
        return frame[0:0, 0:0]
    return frame[y1:y2, x1:x2]


def _px_box(frame: np.ndarray, box: Iterable[int], pad: int = 0) -> np.ndarray:
    h, w = frame.shape[:2]
    x, y, bw, bh = [int(v) for v in list(box)[:4]]
    x1 = max(0, x - pad); y1 = max(0, y - pad)
    x2 = min(w, x + bw + pad); y2 = min(h, y + bh + pad)
    if x2 <= x1 or y2 <= y1:
        return frame[0:0, 0:0]
    return frame[y1:y2, x1:x2]


def _prep_for_ocr(img: np.ndarray) -> np.ndarray:
    if img is None or not getattr(img, "size", 0):
        return img
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()
    # Keep antialiased white UI text but normalize contrast.
    gray = cv2.resize(gray, None, fx=2.4, fy=2.4, interpolation=cv2.INTER_CUBIC)
    gray = cv2.bilateralFilter(gray, 5, 35, 35)
    gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    return gray


def _ocr(img: np.ndarray, psm: int = 6, whitelist: Optional[str] = None) -> str:
    if pytesseract is None or img is None or not getattr(img, "size", 0):
        return ""
    cfg = f"--oem 3 --psm {int(psm)} -c user_defined_dpi=300"
    if whitelist:
        wl = "".join(str(whitelist).split())
        if wl:
            cfg += f" -c tessedit_char_whitelist={wl}"
    try:
        return _clean_text(pytesseract.image_to_string(_prep_for_ocr(img), config=cfg, timeout=1.2))
    except Exception:
        return ""


def _ocr_words(img: np.ndarray, psm: int = 6) -> List[Dict[str, Any]]:
    """Fast one-pass OCR returning word boxes in the input image coordinate space."""
    if pytesseract is None or img is None or not getattr(img, "size", 0):
        return []
    try:
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        scale = 2.0
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        gray = cv2.bilateralFilter(gray, 5, 35, 35)
        gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
        cfg = f"--oem 3 --psm {int(psm)} -c user_defined_dpi=300"
        data = pytesseract.image_to_data(gray, config=cfg, timeout=2.8, output_type=pytesseract.Output.DICT)
        out: List[Dict[str, Any]] = []
        for i, raw in enumerate(data.get("text") or []):
            txt = _clean_text(raw, 80)
            if not txt:
                continue
            try:
                conf = float(data.get("conf", [0])[i])
            except Exception:
                conf = 0.0
            if conf < 5:
                continue
            x = int(float(data["left"][i]) / scale); y = int(float(data["top"][i]) / scale)
            bw = int(float(data["width"][i]) / scale); bh = int(float(data["height"][i]) / scale)
            out.append({"text": txt, "conf": conf, "x": x, "y": y, "w": bw, "h": bh, "cx": x + bw / 2.0, "cy": y + bh / 2.0})
        return out
    except Exception:
        return []


def _words_text_in_box(words: List[Dict[str, Any]], x1: int, y1: int, x2: int, y2: int) -> str:
    picked = []
    for word in words:
        cx = float(word.get("cx") or 0.0); cy = float(word.get("cy") or 0.0)
        if x1 <= cx < x2 and y1 <= cy < y2:
            picked.append(word)
    picked.sort(key=lambda d: (int((float(d.get("cy") or 0) - y1) / 16), float(d.get("cx") or 0)))
    return _clean_text(" ".join(str(w.get("text") or "") for w in picked), 400)


def _best_line(text: str, min_alpha: int = 3) -> str:
    lines = [_clean_text(x, 160) for x in re.split(r"[\n\r]| {3,}", str(text or ""))]
    lines = [x for x in lines if sum(c.isalpha() for c in x) >= min_alpha]
    if not lines:
        return ""
    # Prefer title-like line that is not mostly UI chrome.
    scored = []
    for line in lines:
        low = line.lower()
        bad = sum(1 for w in STOP_WORDS if w in low)
        score = len(line) - bad * 18
        scored.append((score, line))
    return sorted(scored, reverse=True)[0][1]




def _clean_program_title(text: str) -> str:
    s = _clean_text(text, 160)
    # Remove stray red-annotation/OCR symbols while preserving normal title punctuation.
    s = s.replace("»", " ").replace("›", " ").replace("|", " ")
    s = re.sub(r"^[^A-Za-z0-9']+", "", s)
    s = re.sub(r"\s+", " ", s).strip(" -_.,")
    s = re.sub(r"\bHow\s+[|1l]\s+Met\b", "How I Met", s, flags=re.I)
    # Remove duplicate separators/noisy leading glyphs.
    s = re.sub(r"\b([A-Z][a-z]+)\s+\1\b", r"\1", s)
    return s


def _extract_datetime(text: str) -> str:
    clean = _clean_text(text)
    m = TIME_RX.search(clean)
    if m:
        val = _clean_text(m.group(0), 80)
        val = re.sub(r"\s*[|+\-–]+\s*", " | ", val, count=1)
        return val
    return ""


def _extract_time_range(text: str) -> str:
    clean = _clean_text(text)
    m = RANGE_RX.search(clean)
    return _clean_text(m.group(0), 80) if m else ""




def _normalize_channel_number(num: Any) -> str:
    """Normalize DISH channel numbers while preserving hyphenated subchannels.

    Examples:
      "092-14" -> "092-14"
      "092–14" -> "092-14"
      " 111 "  -> "111"
    """
    s = _clean_text(num, 40).replace("–", "-").strip()
    m = re.search(r"\b(\d{1,4}(?:-\d{1,3})?)\b", s)
    return m.group(1) if m else ""


def _channel_base_int(num: Any) -> int:
    s = _normalize_channel_number(num)
    if not s:
        return 0
    try:
        return int(s.split("-", 1)[0])
    except Exception:
        return 0


def is_plausible_channel_number(num: Any) -> bool:
    s = _normalize_channel_number(num)
    if not s:
        return False
    base = _channel_base_int(s)
    return 2 <= base <= 9999


def _channel_matches_requested(num: Any, requested: Optional[int]) -> bool:
    if requested is None:
        return False
    return _channel_base_int(num) == int(requested)

def _parse_channel_line(text: str, requested: Optional[int] = None) -> Tuple[str, str]:
    clean = PHONEISH_RX.sub(" ", _clean_text(text, 1000)).replace("–", "-")
    candidates: List[Tuple[int, str, str]] = []
    for m in CHANNEL_LINE_RX.finditer(clean):
        num = _normalize_channel_number(m.group("num1") or m.group("num2") or "")
        code = m.group("code1") or m.group("code2") or ""
        code = re.sub(r"[^A-Z0-9&+!-]", "", code.upper())
        if not (is_plausible_channel_number(num) and code):
            continue
        if code in BAD_CHANNEL_CODES:
            continue
        # Penalize dates/times accidentally paired with words.
        score = 10
        if _channel_matches_requested(num, requested):
            score += 10
        if len(code) >= 3:
            score += 2
        if re.search(rf"\b{re.escape(code)}\s+{re.escape(num)}\b", clean):
            score += 3
        if "-" in num:
            # Hyphenated channel numbers are high-value because they are easy to miss.
            score += 3
        candidates.append((score, num, code))
    if not candidates:
        return "", ""
    candidates.sort(reverse=True)
    return candidates[0][1], candidates[0][2]

def _parse_channel_number_only(text: str, requested: Optional[int] = None) -> str:
    """Return the first plausible channel number in a row/cluster, ignoring times/dates.

    Supports DISH hyphenated/subchannel forms such as 092-14.
    """
    clean = PHONEISH_RX.sub(" ", _clean_text(text, 1000)).replace("–", "-")
    # Remove times and dates so 12:30 or 5/23 do not become channels.
    clean = TIME_RX.sub(" ", clean)
    clean = RANGE_RX.sub(" ", clean)
    clean = re.sub(r"\b\d{1,2}/\d{1,2}\b", " ", clean)
    candidates = []
    for m in re.finditer(r"\b(\d{2,4}(?:-\d{1,3})?)\b", clean):
        num = _normalize_channel_number(m.group(1))
        if not is_plausible_channel_number(num):
            continue
        # Exclude common durations like 20 mins, 30 min.
        after = clean[m.end():m.end()+16].lower()
        if re.match(r"\s*(mins?|minutes?|remaining|left)\b", after):
            continue
        score = 10 - m.start() / 100.0
        if _channel_matches_requested(num, requested):
            score += 10
        if "-" in num:
            score += 3
        candidates.append((score, num))
    if not candidates:
        return ""
    candidates.sort(reverse=True)
    return candidates[0][1]

def _guess_channel_code_from_row_text(text: str, channel_number: str = "") -> str:
    clean = _clean_text(text, 240)
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9&+!]{1,10}", clean)
    bad = BAD_CHANNEL_CODES | {"SD", "HD", "IONSD", "GLIV", "TURBO", "BONUS"}
    scored: List[Tuple[int, str]] = []
    for idx, tok in enumerate(tokens):
        up = tok.upper()
        if up in bad or up.isdigit() or up == str(channel_number).upper():
            continue
        score = idx
        if tok.isupper():
            score += 5
        if len(up) >= 3:
            score += 2
        # Common guide OCR includes logo word then channel code; prefer repeated/last tokens.
        if tokens.count(tok) > 1 or tokens.count(up) > 1:
            score += 2
        scored.append((score, up))
    if not scored:
        return ""
    return sorted(scored, reverse=True)[0][1]


def _merge_unique(*parts: str, limit: int = 220) -> str:
    out: List[str] = []
    seen = set()
    for p in parts:
        p = _clean_text(p, limit)
        if not p:
            continue
        key = p.lower()
        if key in seen:
            continue
        seen.add(key); out.append(p)
    return " ".join(out)[:limit]


def _screen_hint_from_text(text: str, hint: str = "") -> str:
    low = (str(hint or "") + " " + str(text or "")).lower()
    if "guide" in low and "showing" in low:
        return "guide"
    if "tv show" in low or "summary" in low and "episodes" in low:
        return "info"
    if "live tv" in low or "mins left" in low or "min left" in low:
        return "live_banner"
    return str(hint or "unknown")


def extract_channel_metadata(
    frame: np.ndarray,
    text: str = "",
    focus: Optional[Dict[str, Any]] = None,
    screen_hint: str = "unknown",
    requested_channel: Optional[int] = None,
) -> Dict[str, Any]:
    """Extract structured channel/program metadata from a DISH screen.

    Returns a plain dict so it can be stored directly in JSON logs.
    """
    focus = focus if isinstance(focus, dict) else {}
    if frame is None or not getattr(frame, "size", 0):
        return ChannelMetadata(screen_type="no_frame", quality_flags=["no_frame"]).to_dict()

    # Use quick OCR from broad UI regions only when the caller does not already
    # know which surface it requested.  Channel-surf calls this with explicit
    # live/info/guide hints, so avoid wasting seconds on broad OCR.
    h, w = frame.shape[:2]
    explicit_hint = str(screen_hint or "").lower() in {"live_banner", "guide", "info"}
    if explicit_hint:
        combined = _clean_text(str(text or ""), 1800)
        hint = str(screen_hint or "unknown").lower()
    else:
        top_text = _ocr(_norm_box(frame, (0.00, 0.00, 1.00, 0.24)), psm=6)
        right_text = _ocr(_norm_box(frame, (0.72, 0.00, 1.00, 0.82)), psm=6)
        left_text = _ocr(_norm_box(frame, (0.00, 0.12, 0.30, 0.92)), psm=6)
        combined = _clean_text(" ".join([str(text or ""), top_text, right_text, left_text]), 1800)
        hint = _screen_hint_from_text(combined, screen_hint)

    if hint == "guide":
        meta = _extract_guide(frame, combined, focus, requested_channel=requested_channel)
    elif hint == "info":
        meta = _extract_info(frame, combined, focus, requested_channel=requested_channel)
    elif hint == "live_banner":
        meta = _extract_live_banner(frame, combined, focus, requested_channel=requested_channel)
    else:
        # Try all and return the highest confidence reader.
        candidates = [
            _extract_live_banner(frame, combined, focus, requested_channel=requested_channel),
            _extract_guide(frame, combined, focus, requested_channel=requested_channel),
            _extract_info(frame, combined, focus, requested_channel=requested_channel),
        ]
        meta = max(candidates, key=lambda d: float(d.get("confidence") or 0.0))
        if float(meta.get("confidence") or 0.0) < 0.25:
            meta["screen_type"] = "unknown"
    return meta




def validate_live_banner_metadata(meta: Dict[str, Any], combined_text: str = "") -> Dict[str, Any]:
    """Validate whether the live banner read is trustworthy enough for dashboards.

    This is intentionally stricter than generic metadata confidence. A valid live
    banner should have the channel identity and at least one strong program/time
    cue from the top overlay, not from random full-screen OCR or video texture.
    """
    flags: List[str] = []
    score = 0.0
    title = sanitize_program_title(meta.get("program_title"))
    ch_num = _normalize_channel_number(meta.get("channel_number"))
    code = str(meta.get("channel_code") or "").strip().upper()
    displayed = _clean_text(meta.get("displayed_datetime_text"), 80)
    rng = _clean_text(meta.get("program_time_range"), 80)
    raw = meta.get("raw_regions") or {}
    title_raw = _clean_text(raw.get("title") or title, 160)
    channel_line_raw = _clean_text(raw.get("channel_line") or "", 120)
    progress_raw = _clean_text(raw.get("progress") or "", 160)
    source = str(meta.get("source") or "")

    if title:
        score += 0.25
    else:
        flags.append("banner_missing_program_title")
    if is_plausible_channel_number(ch_num):
        score += 0.22
    else:
        flags.append("banner_missing_channel_number")
    if is_plausible_channel_code(code):
        score += 0.16
    else:
        flags.append("banner_missing_channel_code")
    if displayed:
        score += 0.16
    else:
        flags.append("banner_missing_display_time")
    if rng or re.search(r"\bmins?\s+left\b|\d{1,2}:\d{2}", progress_raw, re.I):
        score += 0.08
    else:
        flags.append("banner_missing_progress_or_time_range")
    if "live_banner" in source:
        score += 0.05
    else:
        flags.append("banner_source_not_live_geometry")
    if re.search(r"\bLive\s*TV\b", combined_text, re.I):
        score += 0.04
    if title_raw and not title:
        flags.append("banner_rejected_noisy_title")
    if channel_line_raw and not (ch_num and code):
        flags.append("banner_channel_line_unparsed")
    if PHONEISH_RX.search(_clean_text(raw.get("description") or "", 200)):
        flags.append("banner_description_contains_phoneish_text")
        score -= 0.08
    score = max(0.0, min(1.0, score))
    valid = score >= 0.68 and not any(f in flags for f in (
        "banner_missing_program_title",
        "banner_missing_channel_number",
        "banner_missing_channel_code",
    ))
    return {"valid": bool(valid), "score": round(score, 4), "flags": sorted(set(flags))}

def _extract_live_banner(frame: np.ndarray, combined: str, focus: Dict[str, Any], requested_channel: Optional[int] = None) -> Dict[str, Any]:
    title = _ocr(_norm_box(frame, (0.14, 0.02, 0.58, 0.095)), psm=7)
    desc = _ocr(_norm_box(frame, (0.14, 0.085, 0.65, 0.145)), psm=7)
    channel_line = _ocr(_norm_box(frame, (0.13, 0.145, 0.28, 0.215)), psm=7)
    time_text = _ocr(_norm_box(frame, (0.70, 0.02, 0.99, 0.095)), psm=7)
    progress_text = _ocr(_norm_box(frame, (0.50, 0.08, 0.96, 0.21)), psm=6)
    logo_text = _ocr(_norm_box(frame, (0.74, 0.61, 0.98, 0.92)), psm=6)
    num, code = _parse_channel_line(channel_line, requested_channel)
    if not num:
        num, code = _parse_channel_line(combined, requested_channel)
    dt = _extract_datetime(time_text + " " + combined)
    title = _clean_program_title(title)
    # Remove Live TV/time leakage from the title crop.
    title = re.sub(r"\bLive\s*TV\b.*$", "", title, flags=re.I).strip(" -|_")
    if not title:
        title = _best_line(combined)
    raw_title = title
    title = sanitize_program_title(title)
    meta = ChannelMetadata(
        screen_type="live_banner",
        channel_number=num,
        channel_code=code,
        channel_name=code,
        channel_logo_text=_clean_text(logo_text, 80),
        program_title=title,
        program_subtitle=_clean_text(desc, 180),
        program_description=_clean_text(desc, 220),
        program_time_range=_extract_time_range(progress_text),
        displayed_datetime_text=dt,
        confidence=0.0,
        source="live_banner_geometry",
        raw_regions={"title": title, "description": desc, "channel_line": channel_line, "time": time_text, "progress": progress_text, "logo": logo_text},
    )
    if raw_title and not meta.program_title:
        meta.quality_flags.append("rejected_noisy_live_program_title")
    score = 0.15
    if meta.program_title: score += 0.25
    if meta.channel_number: score += 0.20
    if meta.channel_code: score += 0.15
    if meta.displayed_datetime_text: score += 0.15
    if re.search(r"\bLive\s*TV\b|mins? left", combined, re.I): score += 0.12
    meta.confidence = round(min(1.0, score), 4)
    if not meta.channel_number: meta.quality_flags.append("missing_channel_number")
    if not meta.program_title: meta.quality_flags.append("missing_program_title")
    banner = validate_live_banner_metadata(meta.to_dict(), combined)
    meta.banner_valid = bool(banner.get("valid"))
    meta.banner_validation_score = float(banner.get("score") or 0.0)
    meta.banner_validation_flags = list(banner.get("flags") or [])
    if not meta.banner_valid:
        meta.quality_flags.append("live_banner_validation_failed")
    return meta.to_dict()



def _guide_layout(frame: np.ndarray) -> Dict[str, Any]:
    """Return stable DISH guide geometry in pixels and normalized boxes.

    The DISH guide layout is regular enough that geometry beats broad OCR:
    left row identity strip, program grid, right detail panel, bottom ad strip.
    These defaults are deliberately conservative and are also used as a fallback
    when red focus detection is unavailable.
    """
    h, w = frame.shape[:2]
    x_left = int(0.000 * w)
    x_grid = int(0.154 * w)
    x_right = int(0.758 * w)
    y_header = int(0.103 * h)
    y_rows = int(0.153 * h)
    y_bottom = int(0.828 * h)
    row_h = max(26, int(0.085 * h))
    # Time columns are detected visually as vertical separators; fixed anchors
    # are close enough for selecting/learning and much faster than Hough scans.
    col_edges = [
        x_grid,
        int(0.274 * w),
        int(0.394 * w),
        int(0.516 * w),
        int(0.638 * w),
        x_right,
    ]
    return {
        "width": w,
        "height": h,
        "x_left": x_left,
        "x_grid": x_grid,
        "x_right": x_right,
        "y_header": y_header,
        "y_rows": y_rows,
        "y_bottom": y_bottom,
        "row_h": row_h,
        "col_edges": col_edges,
        "max_rows": max(1, min(10, (y_bottom - y_rows) // row_h)),
    }


def _norm_from_px(frame: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> List[float]:
    h, w = frame.shape[:2]
    return [round(x1 / max(1, w), 5), round(y1 / max(1, h), 5), round(x2 / max(1, w), 5), round(y2 / max(1, h), 5)]


def _crop_px(frame: np.ndarray, x1: int, y1: int, x2: int, y2: int, pad: int = 0) -> np.ndarray:
    h, w = frame.shape[:2]
    x1 = max(0, min(w, int(x1) - pad)); y1 = max(0, min(h, int(y1) - pad))
    x2 = max(0, min(w, int(x2) + pad)); y2 = max(0, min(h, int(y2) + pad))
    if x2 <= x1 or y2 <= y1:
        return frame[0:0, 0:0]
    return frame[y1:y2, x1:x2]


def _image_signature(img: np.ndarray) -> str:
    """Return a stable, privacy-light visual signature for a channel logo/icon crop."""
    if img is None or not getattr(img, "size", 0):
        return ""
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()
        small = cv2.resize(gray, (16, 16), interpolation=cv2.INTER_AREA)
        bits = (small > float(np.mean(small))).astype(np.uint8).flatten()
        packed = np.packbits(bits).tobytes()
        # Prefix the perceptual hash with a tiny color summary so logos that are
        # visually similar in gray still remain distinct enough for learning.
        means = []
        if len(img.shape) == 3:
            means = [int(x) for x in cv2.mean(img)[:3]]
        digest = hashlib.sha1(packed + bytes(means)).hexdigest()[:16]
        return f"ah16:{digest}"
    except Exception:
        return ""


def _guide_cell_sequence(selected_row: int, selected_col: int, row: int, col: int, include_select: bool = True) -> List[str]:
    if selected_row < 0 or selected_col < 0:
        return []
    seq: List[str] = []
    if row > selected_row:
        seq.extend(["down"] * (row - selected_row))
    elif row < selected_row:
        seq.extend(["up"] * (selected_row - row))
    if col > selected_col:
        seq.extend(["right"] * (col - selected_col))
    elif col < selected_col:
        seq.extend(["left"] * (selected_col - col))
    if include_select:
        seq.append("select")
    return seq


def extract_guide_grid(frame: np.ndarray, text: str = "", focus: Optional[Dict[str, Any]] = None, max_rows: int = 8) -> Dict[str, Any]:
    """Extract visible DISH guide rows, selectable program cells, and logo/icon signatures.

    This is the v34 guide intelligence reader. It intentionally returns a plain
    dict because crawler brain, channel-surf logs, dashboards, and Flask routes
    all persist JSON directly.
    """
    focus = focus if isinstance(focus, dict) else {}
    if frame is None or not getattr(frame, "size", 0):
        return GuideGridAnalysis(screen_type="no_frame", detected=False, quality_flags=["no_frame"]).to_dict()
    layout = _guide_layout(frame)
    h, w = frame.shape[:2]
    max_rows = max(1, min(int(max_rows or 8), int(layout["max_rows"]), 10))
    col_edges: List[int] = list(layout["col_edges"])
    selected_bbox = focus.get("bbox") if isinstance(focus, dict) else None
    if not (selected_bbox and len(selected_bbox) >= 4):
        selected_bbox = _detect_red_focus_bbox_for_guide(frame)
    selected_row = -1
    selected_col = -1
    if selected_bbox and len(selected_bbox) >= 4:
        sx, sy, sw, sh = [int(v) for v in selected_bbox[:4]]
        cx = sx + sw / 2.0
        cy = sy + sh / 2.0
        selected_row = int(round((cy - layout["y_rows"] - layout["row_h"] / 2.0) / max(1, layout["row_h"])))
        selected_row = selected_row if 0 <= selected_row < max_rows else -1
        for ci in range(len(col_edges) - 1):
            if col_edges[ci] <= cx < col_edges[ci + 1]:
                selected_col = ci
                break

    # One OCR pass over the guide grid is far faster and more coherent than
    # spawning Tesseract once per visible cell. If it fails, the old per-crop
    # fallback below still produces data, just slower.
    guide_roi_y = layout["y_header"]
    guide_words = _ocr_words(_crop_px(frame, layout["x_left"], guide_roi_y, layout["x_right"], layout["y_bottom"], pad=0), psm=6)
    for word in guide_words:
        word["x"] = int(word.get("x") or 0) + layout["x_left"]
        word["y"] = int(word.get("y") or 0) + guide_roi_y
        word["cx"] = float(word.get("cx") or 0.0) + layout["x_left"]
        word["cy"] = float(word.get("cy") or 0.0) + guide_roi_y

    # Header/time labels.
    headers: List[str] = []
    for ci in range(len(col_edges) - 1):
        x1, x2 = col_edges[ci], col_edges[ci + 1]
        raw = _words_text_in_box(guide_words, x1, layout["y_header"], x2, layout["y_rows"])
        if not raw:
            raw = _ocr(_crop_px(frame, x1, layout["y_header"], x2, layout["y_rows"], pad=2), psm=7)
        headers.append(_clean_text(raw, 40))

    rows: List[Dict[str, Any]] = []
    flat_programs: List[Dict[str, Any]] = []
    flags: List[str] = []
    for ri in range(max_rows):
        y1 = layout["y_rows"] + ri * layout["row_h"]
        y2 = min(layout["y_bottom"], y1 + layout["row_h"])
        if y2 - y1 < 18:
            continue
        row_crop = _crop_px(frame, layout["x_left"], y1, layout["x_grid"], y2, pad=2)
        row_text = _words_text_in_box(guide_words, layout["x_left"], y1, layout["x_grid"], y2)
        if not row_text:
            row_text = _ocr(row_crop, psm=6)
        ch_num, ch_code = _parse_channel_line(row_text)
        if not ch_num:
            ch_num = _parse_channel_number_only(row_text)
        if ch_num and not ch_code:
            ch_code = _guess_channel_code_from_row_text(row_text, ch_num)
        logo_crop = _crop_px(frame, int(0.00 * w), y1, int(0.115 * w), y2, pad=1)
        icon_sig = _image_signature(logo_crop)
        programs: List[Dict[str, Any]] = []
        for ci in range(len(col_edges) - 1):
            x1, x2 = col_edges[ci], col_edges[ci + 1]
            cell_crop = _crop_px(frame, x1, y1, x2, y2, pad=2)
            raw_cell = _words_text_in_box(guide_words, x1, y1, x2, y2)
            if not raw_cell:
                raw_cell = _ocr(cell_crop, psm=6)
            title = sanitize_program_title(_clean_program_title(raw_cell))
            # OCR can drop short valid titles. Keep cleaned raw text as a fallback
            # but flag low alphabetic evidence so callers can choose how strict to be.
            if not title and sum(c.isalpha() for c in _clean_text(raw_cell)) >= 3:
                title = _clean_text(raw_cell, 90)
            selected = bool(ri == selected_row and ci == selected_col)
            cell = GuideProgramCell(
                row_index=ri,
                col_index=ci,
                title=title,
                raw_text=_clean_text(raw_cell, 160),
                time_label=headers[ci] if ci < len(headers) else "",
                channel_number=ch_num,
                channel_code=ch_code,
                selected=selected,
                bbox_norm=_norm_from_px(frame, x1, y1, x2, y2),
                button_sequence=_guide_cell_sequence(selected_row, selected_col, ri, ci, include_select=True),
            ).__dict__
            programs.append(cell)
            if title or selected:
                flat_programs.append(dict(cell))
        row = GuideChannelRow(
            row_index=ri,
            channel_number=ch_num,
            channel_code=ch_code,
            channel_name=ch_code,
            channel_logo_text=_clean_text(row_text, 180),
            icon_signature=icon_sig,
            bbox_norm=_norm_from_px(frame, layout["x_left"], y1, layout["x_right"], y2),
            programs=programs,
        ).__dict__
        rows.append(row)

    selected: Dict[str, Any] = {}
    if 0 <= selected_row < len(rows) and 0 <= selected_col < len(rows[selected_row].get("programs", [])):
        row = rows[selected_row]
        cell = dict(row["programs"][selected_col])
        selected = dict(cell)
        selected.update({
            "channel_number": row.get("channel_number") or cell.get("channel_number") or "",
            "channel_code": row.get("channel_code") or cell.get("channel_code") or "",
            "channel_name": row.get("channel_name") or "",
            "channel_logo_text": row.get("channel_logo_text") or "",
            "icon_signature": row.get("icon_signature") or "",
        })
    else:
        flags.append("selected_cell_not_detected")

    channel_count = len([r for r in rows if r.get("channel_number")])
    program_count = len([p for p in flat_programs if p.get("title")])
    conf = 0.12
    if selected:
        conf += 0.24
    if channel_count:
        conf += min(0.28, channel_count * 0.045)
    if program_count:
        conf += min(0.28, program_count * 0.018)
    if headers and any(headers):
        conf += 0.08
    if re.search(r"\bGuide\b|Showing:\s*All|Subscribed", str(text or ""), re.I):
        conf += 0.05
    detected = bool(channel_count >= 2 or selected or program_count >= 4)
    if not detected:
        flags.append("guide_grid_low_evidence")
    analysis = GuideGridAnalysis(
        detected=detected,
        confidence=round(min(1.0, conf), 4),
        selected=selected,
        rows=rows,
        programs=flat_programs,
        timeline_headers=headers,
        geometry={
            "x_grid": round(layout["x_grid"] / max(1, w), 5),
            "x_right": round(layout["x_right"] / max(1, w), 5),
            "y_rows": round(layout["y_rows"] / max(1, h), 5),
            "row_h": round(layout["row_h"] / max(1, h), 5),
            "columns": len(col_edges) - 1,
            "rows_scanned": len(rows),
            "selected_row": selected_row,
            "selected_col": selected_col,
        },
        counts={"rows": len(rows), "channels": channel_count, "programs": program_count, "program_options": sum(len(r.get("programs", [])) for r in rows)},
        quality_flags=flags,
    )
    return analysis.to_dict()


def _detect_red_focus_bbox_for_guide(frame: np.ndarray) -> Optional[List[int]]:
    """Small local fallback for guide screenshots when caller did not pass focus."""
    if frame is None or not getattr(frame, "size", 0):
        return None
    h, w = frame.shape[:2]
    # Guide grid is left/middle; ignore DISH logo and bottom ad strip.
    roi = frame[int(0.12*h):int(0.78*h), 0:int(0.76*w)]
    if roi.size == 0:
        return None
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, np.array([0, 80, 80]), np.array([12, 255, 255]))
    mask2 = cv2.inRange(hsv, np.array([165, 80, 80]), np.array([180, 255, 255]))
    mask = cv2.morphologyEx(mask1 | mask2, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=1)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates: List[Tuple[float, List[int]]] = []
    for c in contours:
        x, y, bw, bh = cv2.boundingRect(c)
        area = float(cv2.contourArea(c))
        if bw < 40 or bh < 18 or area < 120:
            continue
        # Favor red rectangular focus around program cells, not logos.
        aspect = bw / max(1, bh)
        if aspect < 1.2 or aspect > 8.0:
            continue
        score = area + bw * 4 + bh * 2
        candidates.append((score, [x, y + int(0.12*h), bw, bh]))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def jsonish_guide_summary(grid: Dict[str, Any]) -> str:
    try:
        parts = []
        for row in list(grid.get("rows") or [])[:8]:
            ch = row.get("channel_number") or "?"
            code = row.get("channel_code") or ""
            titles = [p.get("title") for p in list(row.get("programs") or [])[:5] if p.get("title")]
            parts.append(f"{ch} {code}: " + ", ".join(titles[:4]))
        return " | ".join(parts)
    except Exception:
        return ""

def _extract_guide(frame: np.ndarray, combined: str, focus: Dict[str, Any], requested_channel: Optional[int] = None) -> Dict[str, Any]:
    # Right detail panel is the most stable source for selected program info.
    right_panel = _norm_box(frame, (0.74, 0.08, 0.99, 0.92))
    right_text = _ocr(right_panel, psm=6)
    time_text = _ocr(_norm_box(frame, (0.75, 0.17, 0.99, 0.26)), psm=6)
    if not _extract_datetime(time_text):
        time_text = _ocr(_norm_box(frame, (0.73, 0.00, 0.99, 0.25)), psm=11)
    selected_text = ""
    row_text = ""
    bbox = focus.get("bbox") if isinstance(focus, dict) else None
    if not (bbox and len(bbox) >= 4):
        bbox = _detect_red_focus_bbox_for_guide(frame)
    if bbox and len(bbox) >= 4:
        selected_text = _ocr(_px_box(frame, bbox, pad=5), psm=6)
        x, y, bw, bh = [int(v) for v in bbox[:4]]
        # Channel logo/number/code live in the left strip aligned with the selected row.
        row_crop = frame[max(0, y - bh // 2):min(frame.shape[0], y + bh + bh // 2), 0:max(220, x)]
        row_text = _ocr(row_crop, psm=6)
    else:
        selected_text = _clean_text(focus.get("focused_item") or "")
    num, code = _parse_channel_line(row_text, requested_channel)
    if not num:
        num = _parse_channel_number_only(row_text, requested_channel)
    if num and not code:
        code = _guess_channel_code_from_row_text(row_text, num)
    if not num:
        num, code = _parse_channel_line(selected_text, requested_channel)
    if not num:
        num = _parse_channel_number_only(combined, requested_channel)

    # Program title: selected cell first, then right-panel first meaningful line.
    program = _clean_program_title(selected_text)
    if not program or sum(c.isalpha() for c in program) < 4:
        program = _best_line(right_text, min_alpha=4)
    # Right panel title often starts after the date/time header.
    if right_text:
        rt = _clean_text(TIME_RX.sub(" ", right_text), 800)
        # A quoted episode/title or the first title-like phrase after the time is usually the program detail title.
        quoted = re.search(r'"([^"\n]{4,80})"', rt)
        if quoted and not program:
            program = _clean_text(quoted.group(1), 140)
        if not program:
            lines = [x.strip() for x in re.split(r" {2,}|(?<=p)\s+(?=[A-Z])|\s+»\s+", rt) if x.strip()]
            for line in lines:
                if sum(c.isalpha() for c in line) >= 4 and not re.search(r"\b(HD|TV-\d+|Press|watch|Best Prom Ever|Ep\d+)\b", line, re.I):
                    program = _clean_program_title(line)
                    break
    raw_program = program
    program = sanitize_program_title(program)
    desc = _clean_text(right_text, 500)
    if program:
        desc = _clean_text(desc.replace(program, " "), 500)
    meta = ChannelMetadata(
        screen_type="guide",
        channel_number=num,
        channel_code=code,
        channel_name=code,
        channel_logo_text=_clean_text(row_text, 120),
        program_title=program,
        program_subtitle="",
        program_description=desc,
        program_time_range=_extract_time_range(right_text + " " + combined),
        displayed_datetime_text=_extract_datetime(time_text + " " + right_text + " " + combined),
        focused_program=_clean_text(selected_text, 160),
        confidence=0.0,
        source="guide_focus_row_and_detail_panel",
        raw_regions={"right_panel": right_text, "selected_cell": selected_text, "selected_row": row_text, "time": time_text},
    )
    if raw_program and not meta.program_title:
        meta.quality_flags.append("rejected_noisy_guide_program_title")
    score = 0.18
    if meta.focused_program: score += 0.18
    if meta.program_title: score += 0.20
    if meta.channel_number: score += 0.18
    if meta.channel_code: score += 0.12
    if meta.displayed_datetime_text: score += 0.12
    if re.search(r"\bGuide\b|Showing:\s*All", combined, re.I): score += 0.14
    meta.confidence = round(min(1.0, score), 4)
    if not meta.channel_number: meta.quality_flags.append("missing_selected_row_channel_number")
    if not meta.program_title: meta.quality_flags.append("missing_selected_program_title")
    # v34: attach a compact guide-grid read so channel surf and crawler logs can
    # learn all visible rows/program options, not only the focused detail panel.
    try:
        grid = extract_guide_grid(frame, text=combined, focus=focus, max_rows=8)
        meta.raw_regions["guide_grid_summary"] = _clean_text(jsonish_guide_summary(grid), 600)
    except Exception:
        pass
    return meta.to_dict()


def _extract_info(frame: np.ndarray, combined: str, focus: Dict[str, Any], requested_channel: Optional[int] = None) -> Dict[str, Any]:
    title = _ocr(_norm_box(frame, (0.24, 0.22, 0.52, 0.31)), psm=6)
    # Channel / time / metadata cluster under the title.
    channel_line = _ocr(_norm_box(frame, (0.24, 0.39, 0.49, 0.55)), psm=6)
    episode = _ocr(_norm_box(frame, (0.47, 0.24, 0.95, 0.36)), psm=6)
    desc = _ocr(_norm_box(frame, (0.47, 0.34, 0.96, 0.49)), psm=6)
    time_text = _ocr(_norm_box(frame, (0.70, 0.10, 0.98, 0.32)), psm=6)
    action_text = _ocr(_norm_box(frame, (0.04, 0.68, 0.26, 0.94)), psm=6)
    num, code = _parse_channel_line(channel_line, requested_channel)
    if not num:
        num, code = _parse_channel_line(combined, requested_channel)
    # Some info screens show POP 117, some show code before/after; fallback to explicit focus fields.
    if not num:
        for key in ("channel_number",):
            val = str(focus.get(key) or "").strip()
            if val.isdigit():
                num = val
    if not code:
        ch_name = str(focus.get("channel_name") or "").strip().upper()
        if re.fullmatch(r"[A-Z0-9&+]{2,8}", ch_name):
            code = ch_name
    title = _best_line(title) or _best_line(combined)
    # Keep the main show title before common secondary metadata.
    title = re.split(r"\bFirst Aired\b|\bS\d+\s*[+•-]\s*Ep\d+\b|\bAllez\b", title, maxsplit=1, flags=re.I)[0].strip(" -|_") or title
    meta = ChannelMetadata(
        screen_type="info",
        channel_number=num,
        channel_code=code,
        channel_name=code,
        channel_logo_text=_clean_text(channel_line, 120),
        program_title=sanitize_program_title(title),
        program_subtitle=_clean_text(episode, 180),
        program_description=_clean_text(desc, 500),
        program_time_range=_extract_time_range(channel_line + " " + combined),
        displayed_datetime_text=_extract_datetime(time_text + " " + combined),
        focused_program=_clean_text(focus.get("focused_item") or "", 160),
        confidence=0.0,
        source="info_screen_geometry",
        raw_regions={"title": title, "channel_line": channel_line, "episode": episode, "description": desc, "time": time_text, "actions": action_text},
    )
    if title and not meta.program_title:
        meta.quality_flags.append("rejected_noisy_info_program_title")
    score = 0.16
    if meta.program_title: score += 0.24
    if meta.program_subtitle or meta.program_description: score += 0.15
    if meta.channel_number: score += 0.15
    if meta.channel_code: score += 0.10
    if meta.displayed_datetime_text: score += 0.12
    if re.search(r"\bTV\s*Show\b|Summary|Episodes|Record This|Record Series", combined, re.I): score += 0.18
    meta.confidence = round(min(1.0, score), 4)
    if not meta.channel_number: meta.quality_flags.append("missing_info_channel_number")
    if not meta.program_title: meta.quality_flags.append("missing_info_program_title")
    return meta.to_dict()



NOISY_PROGRAM_RX = re.compile(
    r"(?:\bee\s+panes\s+site\b|\bfey\s*[§\\]|\\e\b|\bmutilets\b|\bm[ou]use\s+mutilets\b|[§\\]{1,})",
    re.I,
)
GOOD_TITLE_HINT_RX = re.compile(r"\b(the|of|and|in|on|with|how|my|your|mother|office|hunters|diner|drive|judd|creek|bargain|renovation|news|movie|sports|family|show|park|schitt|creek)\b", re.I)
UI_CHROME_PROGRAM_RX = re.compile(r"\b(live\s*tv|guide|showing|all\s+subscribed|press|watch|record\s+this|record\s+series|today|sat\s+\d|\d{1,2}:\d{2})\b", re.I)


def _tokenize_words(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9&+'.-]+", _clean_text(text, 240))


def _title_noise_score(text: str) -> float:
    """Return 0 good .. 1 terrible for title/program OCR strings."""
    s = _clean_text(text, 240)
    if not s:
        return 1.0
    score = 0.0
    if NOISY_PROGRAM_RX.search(s):
        score += 0.65
    chars = [c for c in s if not c.isspace()]
    if chars:
        odd = sum(1 for c in chars if not (c.isalnum() or c in "&+.'-:(),/")) / len(chars)
        score += min(0.35, odd * 1.4)
    words = _tokenize_words(s)
    if not words:
        return 1.0
    short_words = sum(1 for w in words if len(w.strip(".'-")) <= 2)
    if len(words) >= 3 and short_words / max(1, len(words)) > 0.55:
        score += 0.35
    low_words = [w.lower() for w in words]
    if len(low_words) >= 4:
        from collections import Counter
        most = Counter(low_words).most_common(1)[0][1]
        if most / len(low_words) >= 0.45:
            score += 0.35
    alpha = sum(c.isalpha() for c in s)
    if alpha < 3:
        score += 0.5
    if len(s) > 170:
        score += 0.25
    if s == s.lower() and len(words) <= 4 and not GOOD_TITLE_HINT_RX.search(s):
        score += 0.28
    stripped = UI_CHROME_PROGRAM_RX.sub(" ", s).strip()
    if not stripped or len(stripped) < 3:
        score += 0.45
    return min(1.0, score)


def is_plausible_program_title(text: Any) -> bool:
    s = _clean_program_title(str(text or ""))
    if not s:
        return False
    if _title_noise_score(s) >= 0.55:
        return False
    if len(s) > 120 and not re.search(r"[:'-]", s):
        return False
    return True


def sanitize_program_title(text: Any) -> str:
    s = _clean_program_title(str(text or ""))
    return s if is_plausible_program_title(s) else ""


def is_plausible_channel_code(text: Any) -> bool:
    s = _clean_text(text, 40).strip().upper()
    if not s or s in BAD_CHANNEL_CODES or len(s) > 10:
        return False
    compact = s.replace("!", "").replace("&", "").replace("+", "").replace("-", "")
    if not re.fullmatch(r"[A-Z0-9]{1,10}", compact):
        return False
    if len(s.split()) > 2:
        return False
    return True


def _metadata_reliability(meta: Dict[str, Any]) -> float:
    if not isinstance(meta, dict):
        return 0.0
    score = float(meta.get("confidence") or 0.0)
    source = str(meta.get("source") or "")
    if "geometry" in source or "detail_panel" in source or "info_screen" in source:
        score += 0.08
    if meta.get("channel_number"):
        score += 0.05
    if is_plausible_channel_code(meta.get("channel_code")):
        score += 0.04
    if is_plausible_program_title(meta.get("program_title")):
        score += 0.08
    flags = set(map(str, meta.get("quality_flags") or []))
    if any("missing" in f for f in flags):
        score -= 0.08
    if any("noise" in f or "untrusted" in f for f in flags):
        score -= 0.25
    if str(meta.get("screen_type") or "") == "live_banner":
        if meta.get("banner_valid"):
            score += 0.08
        elif meta.get("banner_validation_score") is not None:
            score -= 0.12
    return max(0.0, min(1.0, score))


def _pick_field_meta(metas: Iterable[Dict[str, Any]], field: str, preferred: List[str]) -> Dict[str, Any]:
    candidates = []
    for m in metas:
        if not isinstance(m, dict):
            continue
        val = m.get(field)
        if field == "program_title" and not is_plausible_program_title(val):
            continue
        if field == "channel_code" and not is_plausible_channel_code(val):
            continue
        if not str(val or "").strip():
            continue
        pref = preferred.index(m.get("screen_type")) if m.get("screen_type") in preferred else len(preferred)
        candidates.append((pref, -_metadata_reliability(m), m))
    if not candidates:
        return {}
    candidates.sort()
    return candidates[0][2]

def choose_best_metadata(metas: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge live/info/guide metadata into one trusted channel observation.

    v24 deliberately avoids promoting noisy legacy blob-OCR text into titles. A
    human reads channel facts from known screen regions; this merger does the
    same by preferring surface-specific geometry fields and by dropping program
    titles that look like video texture, ad copy, or OCR confetti.
    """
    metas = [m for m in metas if isinstance(m, dict)]
    if not metas:
        return ChannelMetadata().to_dict()
    ranked = sorted(metas, key=_metadata_reliability, reverse=True)
    best = dict(ranked[0]) if ranked else ChannelMetadata().to_dict()
    out = dict(best)
    for field in ("channel_number", "channel_code", "channel_name", "channel_logo_text"):
        src = _pick_field_meta(metas, field, ["guide", "info", "live_banner"])
        val = src.get(field, "") if src else ""
        if field == "channel_code" and not is_plausible_channel_code(val):
            val = ""
        if field == "channel_name" and not val:
            val = out.get("channel_code", "")
        out[field] = val or ""
    title_src = _pick_field_meta(metas, "program_title", ["info", "live_banner", "guide"])
    out["program_title"] = sanitize_program_title(title_src.get("program_title", "") if title_src else "")
    for field in ("program_subtitle", "program_description", "program_time_range"):
        src = _pick_field_meta(metas, field, ["info", "live_banner", "guide"])
        out[field] = _clean_text(src.get(field, "") if src else "", 500 if field == "program_description" else 180)
    time_src = _pick_field_meta(metas, "displayed_datetime_text", ["live_banner", "guide", "info"])
    out["displayed_datetime_text"] = _clean_text(time_src.get("displayed_datetime_text", "") if time_src else "", 80)
    out["confidence"] = round(max(_metadata_reliability(m) for m in metas), 4)
    out["source"] = "merged_channel_metadata_v25_trusted"
    out["raw_regions"] = {m.get("screen_type", f"meta{i}"): m.get("raw_regions", {}) for i, m in enumerate(metas)}
    flags: List[str] = []
    for m in metas:
        flags.extend([str(f) for f in m.get("quality_flags") or []])
        pt = str(m.get("program_title") or "")
        if pt and not is_plausible_program_title(pt):
            flags.append("rejected_noisy_program_title")
    if not out.get("program_title"):
        flags.append("missing_trusted_program_title")
    if not out.get("channel_number"):
        flags.append("missing_trusted_channel_number")
    out["quality_flags"] = sorted(set(flags))
    return out
