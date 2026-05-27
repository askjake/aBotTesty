#!/usr/bin/env python3
"""Displayed clock extraction and drift checks for STB UI screenshots.

The goal is to distinguish the receiver's *current displayed time* from ordinary
program schedule times. We therefore prefer high-signal regions such as the
DISH top/header band OCR and date+time combinations. Time-only matches from the
body of Guide/OnDemand text are reported with lower confidence rather than
trusted blindly.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - Python <3.9 fallback
    ZoneInfo = None  # type: ignore

DAY_RX = r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)(?:day)?"
DATE_TIME_RX = re.compile(
    rf"\b(?:{DAY_RX}\s+)?(\d{{1,2}})/(\d{{1,2}})(?:/(\d{{2,4}}))?\s*(?:\||-|at)?\s*(\d{{1,2}}):(\d{{2}})\s*([ap])\.?m?\b",
    re.I,
)
TIME_RX = re.compile(r"\b(\d{1,2}):(\d{2})\s*([ap])\.?m?\b", re.I)

HIGH_SIGNAL_SOURCES = {
    "focus.header_text",
    "focus.page_name",
    "focus.screen_title",
    "focus.recovery_text_header",
}


@dataclass
class DisplayClockResult:
    found: bool
    displayed: str = ""
    displayed_iso: str = ""
    actual_iso: str = ""
    drift_minutes: Optional[float] = None
    source: str = ""
    confidence: float = 0.0
    severity: str = "unknown"  # ok, minor, major, unknown
    flags: List[str] = None  # type: ignore[assignment]
    candidates: List[Dict[str, Any]] = None  # type: ignore[assignment]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["flags"] = d.get("flags") or []
        d["candidates"] = d.get("candidates") or []
        return d


def _local_tz():
    name = os.getenv("ABOT_LOCAL_TZ") or os.getenv("TZ") or "America/Denver"
    if ZoneInfo is not None:
        try:
            return ZoneInfo(name)
        except Exception:
            pass
    return datetime.now().astimezone().tzinfo or timezone.utc


def parse_observed_at(value: Any = None) -> datetime:
    tz = _local_tz()
    if isinstance(value, datetime):
        dt = value
    elif value:
        s = str(value).strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except Exception:
            dt = datetime.now(timezone.utc)
    else:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def _hour_24(hour: int, ampm: str) -> int:
    h = int(hour)
    a = (ampm or "").lower()[0]
    if a == "p" and h != 12:
        h += 12
    if a == "a" and h == 12:
        h = 0
    return h


def _candidate_from_match(match: re.Match[str], source: str, ref: datetime, has_date: bool) -> Dict[str, Any]:
    if has_date:
        mo, day, year, hh, mm, ap = match.groups()
        yy = int(year) if year else ref.year
        if yy < 100:
            yy += 2000
        dt = datetime(yy, int(mo), int(day), _hour_24(int(hh), ap), int(mm), tzinfo=ref.tzinfo)
    else:
        hh, mm, ap = match.groups()
        dt = ref.replace(hour=_hour_24(int(hh), ap), minute=int(mm), second=0, microsecond=0)
        # Prefer the instance of the 12-hour time closest to the actual moment.
        alternates = [dt]
        try:
            alternates.append(dt.replace(hour=(dt.hour + 12) % 24))
        except Exception:
            pass
        dt = min(alternates, key=lambda x: abs((x - ref).total_seconds()))
    drift = round((dt - ref).total_seconds() / 60.0, 3)
    confidence = 0.95 if has_date else (0.82 if source in HIGH_SIGNAL_SOURCES else 0.35)
    raw = match.group(0)
    return {
        "raw": raw,
        "displayed_iso": dt.isoformat(timespec="seconds"),
        "drift_minutes": drift,
        "source": source,
        "has_date": has_date,
        "confidence": confidence,
    }


def _iter_source_text(screen_text: str, focus: Optional[Dict[str, Any]]) -> Iterable[Tuple[str, str]]:
    focus = focus if isinstance(focus, dict) else {}
    for key in ("header_text", "page_name", "screen_title"):
        val = str(focus.get(key) or "").strip()
        if val:
            yield f"focus.{key}", val
    # recovery_text often contains the full OCR text. If it begins with a header-like
    # phrase, let date+time patterns inside it count as high signal.
    recovery = str(focus.get("recovery_text") or "").strip()
    if recovery:
        first = " ".join(recovery.split()[:18])
        yield "focus.recovery_text_header", first
        yield "focus.recovery_text", recovery
    if screen_text:
        # Header hint: the first short run of words often contains DISH date/time.
        yield "text.header_hint", " ".join(str(screen_text).split()[:24])
        yield "text.full", str(screen_text)


def extract_display_clock(screen_text: str = "", focus: Optional[Dict[str, Any]] = None, observed_at: Any = None) -> Dict[str, Any]:
    """Extract displayed current clock and compare to real current time.

    Returns a dict intentionally friendly for JSON logs and Superset export.
    """
    ref = parse_observed_at(observed_at)
    candidates: List[Dict[str, Any]] = []
    seen = set()
    for source, text in _iter_source_text(screen_text or "", focus):
        compact = " ".join(str(text or "").replace("|", " | ").split())
        for m in DATE_TIME_RX.finditer(compact):
            cand = _candidate_from_match(m, source, ref, has_date=True)
            key = (cand["raw"], cand["source"])
            if key not in seen:
                seen.add(key); candidates.append(cand)
        # Only use time-only matches from high-signal/header sources. This avoids
        # treating Guide program start times as the receiver clock.
        if source in HIGH_SIGNAL_SOURCES:
            for m in TIME_RX.finditer(compact):
                cand = _candidate_from_match(m, source, ref, has_date=False)
                key = (cand["raw"], cand["source"])
                if key not in seen:
                    seen.add(key); candidates.append(cand)
    candidates.sort(key=lambda c: (float(c.get("confidence", 0)), -abs(float(c.get("drift_minutes", 999)))), reverse=True)
    actual_iso = ref.isoformat(timespec="seconds")
    if not candidates:
        return DisplayClockResult(found=False, actual_iso=actual_iso, flags=["display_clock_not_found"], candidates=[]).to_dict()
    best = candidates[0]
    drift_abs = abs(float(best.get("drift_minutes") or 0.0))
    flags: List[str] = []
    if best.get("confidence", 0) < 0.6:
        flags.append("low_confidence_display_clock")
    if drift_abs > 10:
        severity = "major"
        flags.append("display_clock_major_drift")
    elif drift_abs > 3:
        severity = "minor"
        flags.append("display_clock_minor_drift")
    else:
        severity = "ok"
    return DisplayClockResult(
        found=True,
        displayed=str(best.get("raw") or ""),
        displayed_iso=str(best.get("displayed_iso") or ""),
        actual_iso=actual_iso,
        drift_minutes=round(float(best.get("drift_minutes") or 0.0), 3),
        source=str(best.get("source") or ""),
        confidence=round(float(best.get("confidence") or 0.0), 3),
        severity=severity,
        flags=flags,
        candidates=candidates[:8],
    ).to_dict()
