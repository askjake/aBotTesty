#!/usr/bin/env python3
"""sgs_autopair.py — fully automated SGS PIN pairing for DISH receivers.

How PIN pairing actually works
=============================
SGS (Set-top Gateway Service) exposes two endpoint families on the receiver's
embedded Jetty server:

    http://<stb_ip>:8080/sgs_noauth   unauthenticated: pairing handshake only
    http://<stb_ip>:8080/www/sgs      HTTP-digest authenticated: everything else
    https://<stb_ip>/www/sgs          same, over TLS with a client certificate

Every request carries an envelope identifying *this* PC as a "receiver"
(a third-party controller) plus the target set-top's CAID:

    {"command": "...",
     "receiver": "XAF<pc-mac>",       # us; see sgs_lib.sgs_get_receiver_id()
     "stb":      "R1956409151-66",    # the receiver's CAID from base.txt
     "app": "JAMboree", "name": "JAMboree", "type": "python", "id": "S9",
     "mac": "<pc-mac>"}

The handshake is three steps:

  1. **start**     POST ``device_pairing_start`` to ``/sgs_noauth``.
                   On success (``result == 1``) the receiver draws a PIN on the
                   TV.  The same value is written to the box's own log as
                   ``"Pairing code is <pin>"`` in
                   ``/mnt/MISC_HD/esosal_log/stbCtrl/stbCtrl.0``.
                   The PIN is short-lived — read it promptly.

  2. **complete**  POST ``device_pairing_complete``: the identical envelope plus
                   ``"pin": "<pin>"``.  On success the reply contains
                   ``{"result": 1, "name": "<login>", "passwd": "<password>"}``.
                   Those are permanent HTTP-digest credentials tied to the
                   ``receiver`` id we sent, and they must be persisted —
                   they are never re-issued.

  3. **attach**    POST ``{"command": "attach", ...}`` to the authenticated
                   endpoint to obtain a ``cid`` (connection id).  Remote-key
                   traffic for a Joey must carry the cid; a Hopper accepts keys
                   without one.  The cid expires after roughly 150 s idle.

Why this module exists
======================
``sgs_lib.STB.pair()`` implemented the handshake but called
``input("Please enter PIN: ")`` in the middle, so it could only ever be driven
by a human at a terminal, and ``STB.__init__`` used to lose the credentials
afterwards anyway.  This module closes the loop:

    request pairing -> OCR the PIN off the live video -> complete pairing
    -> persist credentials additively to base.txt -> attach -> prove that
    remote keys are really landing on the box.

Nothing here rewrites base.txt: credentials are written with
``jamboree.base_io.update_stb_fields``, which updates or adds individual fields
and preserves everything else.

Usage
-----
As a library (this is how merged_app drives it)::

    import sgs_autopair
    sgs_autopair.set_dependencies(get_frame=monitor.get_frame, store=store,
                                  ctl=ctl, CFG=CFG)
    result = sgs_autopair.auto_pair("found1")

Standalone (needs a frame source, so ``--pin`` is usually supplied)::

    python -m sgs_autopair --alias found1 --pin 123456
    python -m sgs_autopair --alias found1 --status
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

log = logging.getLogger("merged.sgs_autopair")

# ─────────────────────────────────────────────────────────────────────────────
#  Tunables
# ─────────────────────────────────────────────────────────────────────────────

SGS_PORTS: Tuple[int, ...] = (8080, 80)        # noauth endpoint probe order
HTTP_TIMEOUT_S: float = 8.0

# PIN geometry.  Sling/SGS issues 6 digits on current firmware, but older
# images used 4, so accept a range and prefer the longest plausible match.
PIN_MIN_DIGITS: int = 4
PIN_MAX_DIGITS: int = 8
PIN_PREFERRED_DIGITS: int = 6

# How long to keep looking for the PIN after device_pairing_start.
PIN_READ_TIMEOUT_S: float = 45.0
PIN_READ_INTERVAL_S: float = 1.5
# A candidate must be read this many times before we trust it.  OCR on a 1080p
# capture of a TV panel is noisy; agreement across independent frames is the
# cheapest reliable confidence signal we have.
PIN_STABLE_READS: int = 2
# A rejected PIN invalidates the pairing session, so the whole handshake is
# restarted (fresh PIN on screen) rather than resubmitting a guess.
MAX_PIN_ATTEMPTS: int = 3

# Verification
VERIFY_SETTLE_S: float = 2.0
# Mean absolute pixel difference above which we call the screen "changed".
SCREEN_CHANGE_THRESHOLD: float = 1.5

# Words that appear on the pairing dialog; used to find the right screen and to
# anchor the digit search.
PAIR_SCREEN_KEYWORDS: Tuple[str, ...] = (
    "pair", "pairing", "code", "pin", "authorize", "authorise",
    "remote access", "device", "connect",
)

# ─────────────────────────────────────────────────────────────────────────────
#  Dependencies (injected by merged_app.py, mirroring ip_recovery)
# ─────────────────────────────────────────────────────────────────────────────

_get_frame: Optional[Callable[[], Any]] = None
_store: Any = None
_ctl: Any = None
_CFG: Optional[Dict[str, Any]] = None

_lock = threading.RLock()
_state: Dict[str, Any] = {
    "phase": "idle",
    "active": False,
    "last_result": {},
    "history": [],
}


def set_dependencies(
    *,
    get_frame: Optional[Callable[[], Any]] = None,
    store: Any = None,
    ctl: Any = None,
    CFG: Optional[Dict[str, Any]] = None,
) -> None:
    """Register the app singletons.  Safe to call more than once."""
    global _get_frame, _store, _ctl, _CFG
    if get_frame is not None:
        _get_frame = get_frame
    if store is not None:
        _store = store
    if ctl is not None:
        _ctl = ctl
    if CFG is not None:
        _CFG = CFG
    log.info("sgs_autopair: dependencies registered (frame=%s ctl=%s store=%s)",
             _get_frame is not None, _ctl is not None, _store is not None)


def _set_phase(phase: str, **detail: Any) -> None:
    with _lock:
        _state["phase"] = phase
        if detail:
            _state.setdefault("detail", {}).update(detail)
        _state["history"] = (_state.get("history") or [])[-40:] + [
            {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "phase": phase, **detail}
        ]
    log.info("sgs_autopair: phase=%s %s", phase,
             " ".join(f"{k}={v}" for k, v in detail.items()) if detail else "")


def get_status() -> Dict[str, Any]:
    with _lock:
        return {
            "phase": _state.get("phase"),
            "active": _state.get("active"),
            "detail": dict(_state.get("detail") or {}),
            "last_result": dict(_state.get("last_result") or {}),
            "history": list(_state.get("history") or [])[-15:],
        }


# ─────────────────────────────────────────────────────────────────────────────
#  base.txt helpers  (always additive — never rewrite the document)
# ─────────────────────────────────────────────────────────────────────────────

def _base_path() -> Path:
    from jamboree.paths import BASE_PATH
    return Path(BASE_PATH)


def _entry(alias: str) -> Dict[str, Any]:
    if _store is not None:
        return dict(_store.get(alias) or {})
    from jamboree import base_io
    return dict((base_io.read_document(_base_path()).get("stbs", {}) or {}).get(alias, {}))


def _save_fields(alias: str, fields: Dict[str, Any]) -> bool:
    """Update/add fields on one STB entry.  Never removes anything."""
    try:
        if _store is not None and hasattr(_store, "update_stb"):
            _store.update_stb(alias, fields)
            _store.reload()
        else:
            from jamboree import base_io
            base_io.update_stb_fields(_base_path(), alias, fields)
        log.info("sgs_autopair: base.txt updated for %s: %s",
                 alias, ", ".join(sorted(fields)))
        return True
    except Exception:
        log.exception("sgs_autopair: failed to persist %s for %s", sorted(fields), alias)
        return False


def _receiver_id() -> str:
    from jamboree.sgs_lib import sgs_get_receiver_id
    return sgs_get_receiver_id()


def _local_mac() -> str:
    from jamboree.sgs_lib import get_local_iface_mac
    return get_local_iface_mac()


def credentials_status(alias: str) -> Dict[str, Any]:
    """Report whether stored credentials exist and still belong to this PC.

    The credentials the receiver hands out are bound to the ``receiver`` id we
    presented during pairing (``XAF`` + this host's MAC).  If that id changes —
    a NIC swap, or ``uuid.getnode()`` picking a different interface — the stored
    login/password are dead and the box will answer 403 forever.  Detecting that
    explicitly saves a long debugging session.
    """
    entry = _entry(alias)
    stored_rid = entry.get("pair_rid")
    current_rid = _receiver_id()
    have = bool(entry.get("lname")) and bool(entry.get("passwd"))
    return {
        "alias": alias,
        "paired": have,
        "lname": entry.get("lname"),
        "passwd_present": bool(entry.get("passwd")),
        "paired_ts": entry.get("paired_ts"),
        "pair_rid": stored_rid,
        "current_rid": current_rid,
        "rid_matches": (stored_rid == current_rid) if stored_rid else None,
        "stale_rid": bool(stored_rid and stored_rid != current_rid),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Transport
# ─────────────────────────────────────────────────────────────────────────────

def _pair_envelope(stb_id: str, command: str, **extra: Any) -> Dict[str, Any]:
    payload = {
        "command":  command,
        "receiver": _receiver_id(),
        "stb":      stb_id,
        "app":      "JAMboree",
        "name":     "JAMboree",
        "type":     "python",
        "id":       "S9",
        "mac":      _local_mac(),
    }
    payload.update(extra)
    return payload


def _post_noauth(ip: str, payload: Dict[str, Any], port_hint: Any = None) -> Dict[str, Any]:
    """POST to /sgs_noauth, trying the configured port then the usual suspects.

    Returns the parsed JSON, or a synthetic error envelope so callers never have
    to deal with ``None``.
    """
    import requests

    ports: List[int] = []
    try:
        if port_hint:
            ports.append(int(port_hint))
    except Exception:
        pass
    ports += [p for p in SGS_PORTS if p not in ports]

    last: Dict[str, Any] = {"result": -1, "error": "no_endpoint_tried"}
    for port in ports:
        url = f"http://{ip}:{port}/sgs_noauth"
        try:
            resp = requests.post(
                url, json=payload, timeout=HTTP_TIMEOUT_S,
                headers={"Content-Type": "application/json"},
            )
        except Exception as exc:
            last = {"result": -1, "error": "transport", "detail": str(exc), "url": url}
            log.debug("sgs_autopair: %s unreachable: %s", url, exc)
            continue

        try:
            data = resp.json()
            if isinstance(data, dict):
                data.setdefault("_url", url)
                data.setdefault("_http_status", resp.status_code)
                if data.get("result") == 1:
                    return data
                last = data
                continue
        except Exception:
            pass

        last = {
            "result": -13 if resp.status_code in (401, 403) else -3,
            "error": ("auth_required_or_opt_in_disabled"
                      if resp.status_code in (401, 403) else "json_parse_failed"),
            "http_status": resp.status_code,
            "url": url,
            "text": (resp.text or "")[:500],
        }
        log.debug("sgs_autopair: %s -> HTTP %s (non-JSON)", url, resp.status_code)

    return last


# ─────────────────────────────────────────────────────────────────────────────
#  On-screen PIN OCR
# ─────────────────────────────────────────────────────────────────────────────

# Tesseract confuses these glyphs constantly on TV captures.
_DIGIT_FIXUPS = {
    "O": "0", "o": "0", "D": "0", "Q": "0",
    "I": "1", "l": "1", "|": "1", "i": "1", "!": "1",
    "Z": "2", "z": "2",
    "A": "4",
    "S": "5", "s": "5",
    "G": "6", "b": "6",
    "T": "7",
    "B": "8",
    "g": "9", "q": "9",
}

# "Pairing code is 123456", "Enter code: 1234", "PIN 123456"
_LABELLED_PIN_RE = re.compile(
    r"(?:pair(?:ing)?[\s_-]*(?:code|pin)?|code|pin|passcode)"
    r"[\s:=.\-]{0,14}"
    r"([0-9OoDIl|SsBGgbqZzAT]{%d,%d})" % (PIN_MIN_DIGITS, PIN_MAX_DIGITS),
    re.I,
)
_BARE_DIGITS_RE = re.compile(r"(?<![0-9])([0-9]{%d,%d})(?![0-9])"
                             % (PIN_MIN_DIGITS, PIN_MAX_DIGITS))


def _normalise_digits(raw: str) -> str:
    """Map OCR look-alikes to digits and strip everything else."""
    fixed = "".join(_DIGIT_FIXUPS.get(ch, ch) for ch in (raw or ""))
    return re.sub(r"[^0-9]", "", fixed)


def _ocr(img, psm: int = 6, digits_only: bool = False, strict: bool = False) -> str:
    try:
        import pytesseract
    except Exception:
        return ""
    cfg = f"--oem 3 --psm {psm} -c user_defined_dpi=300"
    if digits_only:
        # strict: digits only, so the classifier must choose the nearest digit.
        # loose:  also allow look-alike letters, repaired by _normalise_digits().
        cfg += (" -c tessedit_char_whitelist=0123456789" if strict
                else " -c tessedit_char_whitelist=0123456789OoDdIl|SsBGgbqZzAT")
    try:
        return pytesseract.image_to_string(img, config=cfg) or ""
    except Exception as exc:
        log.debug("sgs_autopair: OCR error: %s", exc)
        return ""


# Tesseract cost scales with pixel count, and a 0.5x0.4 crop of a 1080p frame
# upscaled 2.6x is already 2496 px wide.  Cap it: beyond ~1800 px the OCR gets
# slower without getting better on TV-sized glyphs.
MAX_OCR_WIDTH: int = 1800


def has_text_like_content(img) -> bool:
    """Cheap gate: does this crop plausibly contain rendered glyphs?

    Running the full pass matrix over an empty region is what made a single poll
    take ~40 s on a banner-style pairing screen: the centred-modal crop held
    nothing but capture noise, and tesseract spends a long time hunting for text
    in noise before giving up.

    A first version of this gate only counted connected components and passed
    pure noise as "text-like", so it never actually skipped anything.  Two
    signals are needed:

      * **class separation** -- real text is bimodal, so the mean of the pixels
        above Otsu's threshold sits far from the mean of those below it.  Sensor
        noise on a flat panel is unimodal and separates by only a few levels.
      * **glyph-shaped, baseline-aligned blobs** -- at least a few components of
        plausible size that share a horizontal band, which digits in a PIN do and
        scattered noise speckle does not.
    """
    try:
        import cv2
        import numpy as np

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        h, w = gray.shape[:2]
        if h < 16 or w < 16:
            return False

        thr, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        hi = gray[gray >= thr]
        lo = gray[gray < thr]
        if hi.size == 0 or lo.size == 0:
            return False
        separation = float(hi.mean()) - float(lo.mean())
        if separation < 28.0:
            # Unimodal: flat panel, gradient or pure noise. No text here.
            return False

        # Glyph-shaped components, on any polarity, roughly sharing a baseline.
        for polarity in (th, cv2.bitwise_not(th)):
            n, _lbl, stats, cent = cv2.connectedComponentsWithStats(polarity, 8)
            boxes = []
            for i in range(1, n):
                cw = int(stats[i, cv2.CC_STAT_WIDTH])
                ch = int(stats[i, cv2.CC_STAT_HEIGHT])
                area = int(stats[i, cv2.CC_STAT_AREA])
                if not (0.03 * h <= ch <= 0.80 * h):
                    continue
                if not (0.004 * w <= cw <= 0.45 * w):
                    continue
                if area < 0.25 * cw * ch * 0.35:      # too sparse to be a glyph
                    continue
                boxes.append((float(cent[i][1]), ch))
            if len(boxes) < 2:
                continue
            # Baseline alignment: several blobs whose centres fall in one band.
            boxes.sort()
            for idx, (cy, ch) in enumerate(boxes):
                band = max(6.0, 0.6 * ch)
                same_line = sum(1 for cy2, _ in boxes if abs(cy2 - cy) <= band)
                if same_line >= 2:
                    return True
        return False
    except Exception:
        return True      # never skip a region because the gate itself failed


def _variants(img, scale: float):
    """Yield ``(name, image)`` preprocessing variants for one crop.

    A single threshold pass is not good enough: on a real TV capture the PIN can
    be light-on-dark or dark-on-light, and Otsu picks the wrong polarity often
    enough that individual digits flip (3<->5, 8<->6).  Running several variants
    and voting is what makes the reader reliable, and it costs a few hundred ms
    once per pairing attempt.
    """
    out = []
    try:
        import cv2
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        # Clamp the effective scale so the OCR image never exceeds MAX_OCR_WIDTH.
        if gray.shape[1] > 0:
            scale = min(float(scale), MAX_OCR_WIDTH / float(gray.shape[1]))
            scale = max(scale, 1.0)
        up = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        out.append(("gray", up))
        _, otsu = cv2.threshold(up, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        out.append(("otsu", otsu))
        out.append(("otsu_inv", cv2.bitwise_not(otsu)))
        # Fixed high threshold: isolates bright dialog text from a dark panel.
        _, bright = cv2.threshold(up, 165, 255, cv2.THRESH_BINARY)
        out.append(("bright_inv", cv2.bitwise_not(bright)))
        # Mild blur before Otsu smooths compression noise on the capture.
        _, blurred = cv2.threshold(
            cv2.GaussianBlur(up, (3, 3), 0), 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )
        out.append(("blur_otsu_inv", cv2.bitwise_not(blurred)))
        # Adaptive threshold copes with a gradient/backlit dialog panel where a
        # single global cutoff loses either the top or the bottom of the digits.
        try:
            adap = cv2.adaptiveThreshold(
                up, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 31, 5,
            )
            out.append(("adaptive_inv", cv2.bitwise_not(adap)))
        except Exception:
            pass
        # Closing repairs hairline breaks in anti-aliased strokes, which is the
        # single most common cause of a digit being read as a letter.
        try:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            closed = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel)
            out.append(("closed_inv", cv2.bitwise_not(closed)))
        except Exception:
            pass
    except Exception:
        out.append(("raw", img))
    return out


def _prep(img, scale: float = 2.6):
    """Single best-effort preprocessing pass (kept for pairing_screen_visible)."""
    try:
        import cv2
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        up = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        _, th = cv2.threshold(up, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return th
    except Exception:
        return img


def _crop(frame, box: Tuple[float, float, float, float]):
    h, w = frame.shape[:2]
    x0, y0, x1, y1 = box
    return frame[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]


# Regions to search, best-first, with a confidence weight.  A PIN found inside
# the centred modal is far more trustworthy than digits scraped off the whole
# frame, which could be a clock or a channel number.
_PIN_REGIONS: Tuple[Tuple[Tuple[float, float, float, float], float], ...] = (
    ((0.25, 0.30, 0.75, 0.70), 3.0),   # centred modal
    ((0.20, 0.35, 0.80, 0.65), 2.5),   # slightly wider
    ((0.10, 0.25, 0.90, 0.75), 2.0),   # generous centre band
    ((0.05, 0.70, 0.95, 1.00), 1.5),   # bottom banner
    ((0.00, 0.00, 1.00, 1.00), 0.6),   # whole frame, last resort
)

_SCALES: Tuple[float, ...] = (2.0, 2.6, 4.0)

# How a match was obtained, and how much we trust it.
_METHOD_WEIGHT = {
    "labelled": 3.0,    # sat next to the words "code"/"pin" -- strongest signal
    "whitelist": 1.4,   # digit-only pass over the crop
    "bare": 0.8,        # loose digit run
}


# OCR effort tiers.  A single tesseract invocation costs ~100 ms, so the number
# of passes has to be budgeted explicitly: the first version of this reader tried
# every region x scale x variant x psm x whitelist combination, which came to
# ~1050 calls and 108 s for ONE frame.  wait_for_pin() polls repeatedly, so the
# per-frame cost must stay near a second and depth comes from cross-frame voting
# instead.
#
# Each plan entry is (region_index, scale, variant_names, passes) where a pass is
# ("labelled", psm) or ("strict"|"loose", psm).
_EFFORT_PLANS: Dict[str, Dict[str, Any]] = {
    # ~9 calls (~0.9 s) - the centred modal, the layouts that matter most.
    "fast": {
        "regions": (0,),
        "scales": (2.6,),
        "variants": ("otsu_inv", "gray", "adaptive_inv"),
        "passes": (("labelled", 6), ("strict", 8), ("strict", 7)),
        "max_calls": 12,
        "time_budget_s": 4.0,
    },
    # ~40 calls - MORE DEPTH ON THE SAME REGION, not a wider crop.
    #
    # Measured on a 4-font x 8-PIN synthetic sweep: an earlier "deep" tier that
    # widened the crop to regions (0,1,3) scored 78% top-1, *worse* than the
    # 81% of the narrow "fast" tier, because digits from the banner and the
    # clock got into the vote and outranked the real PIN.  Escalation therefore
    # adds polarities, scales and PSMs over the centred dialog; widening the
    # search area is reserved for the exhaustive tier, where the region weights
    # keep peripheral digits from winning.
    "deep": {
        "regions": (0, 1),
        "scales": (2.6, 4.0),
        "variants": ("otsu_inv", "gray", "closed_inv", "adaptive_inv"),
        "passes": (("labelled", 6), ("strict", 8), ("strict", 7), ("strict", 13), ("loose", 6)),
        "max_calls": 44,
        "time_budget_s": 12.0,
    },
    # ~80 calls (~8 s) - last resort, includes the whole frame.
    "exhaustive": {
        "regions": (0, 1, 2, 3, 4),
        "scales": (2.0, 2.6, 4.0),
        "variants": ("otsu", "otsu_inv", "gray", "adaptive_inv", "closed_inv"),
        "passes": (("labelled", 6), ("labelled", 11), ("strict", 8),
                   ("strict", 7), ("strict", 13), ("loose", 6)),
        "max_calls": 70,
        "time_budget_s": 25.0,
    },
}


def score_pin_candidates(
    frame=None,
    effort: str = "fast",
    time_budget_s: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Score every PIN candidate visible in one frame, within a call budget.

    Returns ``[{"pin", "score", "hits", "sources"}, ...]`` sorted best-first.
    Voting across regions/scales/polarities/PSMs is what corrects the individual
    digit confusions a single OCR pass gets wrong; ``effort`` bounds how much of
    that matrix is explored.
    """
    if frame is None:
        if _get_frame is None:
            return []
        frame = _get_frame()
    if frame is None or not getattr(frame, "size", 0):
        return []

    plan = _EFFORT_PLANS.get(effort) or _EFFORT_PLANS["fast"]
    # Budget is allocated PER REGION, not globally.  A single global counter is
    # consumed in region order, so on the exhaustive tier region 0 alone wanted
    # 3 scales x 5 variants x 6 passes = 90 calls and the bottom-banner region
    # was never reached at all -- a banner-style pairing screen returned no
    # candidates whatsoever.
    regions = tuple(plan["regions"])
    per_region = max(3, int(plan["max_calls"]) // max(1, len(regions)))
    calls_used = 0
    # Hard wall-clock stop.  Without this a single call could run for ~40 s and
    # blow straight through wait_for_pin's overall timeout, because the deadline
    # used to be checked only between polls.
    if time_budget_s is None:
        time_budget_s = float(plan.get("time_budget_s") or 0) or None
    hard_deadline = (time.time() + float(time_budget_s)) if time_budget_s else None

    def _out_of_time() -> bool:
        return hard_deadline is not None and time.time() >= hard_deadline

    scores: Dict[str, float] = {}
    hits: Dict[str, int] = {}
    sources: Dict[str, List[str]] = {}

    def _add(pin: str, weight: float, source: str) -> None:
        if not pin or not (PIN_MIN_DIGITS <= len(pin) <= PIN_MAX_DIGITS):
            return
        if len(pin) == PIN_PREFERRED_DIGITS:
            weight *= 1.6                     # firmware issues 6 digits today
        scores[pin] = scores.get(pin, 0.0) + weight
        hits[pin] = hits.get(pin, 0) + 1
        sources.setdefault(pin, [])
        if len(sources[pin]) < 5:
            sources[pin].append(source)

    for region_idx in regions:
        if _out_of_time():
            log.debug("sgs_autopair: OCR time budget reached, stopping at region %d", region_idx)
            break
        budget = per_region
        try:
            box, region_w = _PIN_REGIONS[region_idx]
            crop = _crop(frame, box)
        except Exception:
            continue
        if crop is None or not getattr(crop, "size", 0):
            continue
        # Skip regions that clearly hold no glyphs (see has_text_like_content).
        if not has_text_like_content(crop):
            log.debug("sgs_autopair: region %d has no glyph-like content, skipping", region_idx)
            continue

        for scale in plan["scales"]:
            if budget <= 0 or _out_of_time():
                break
            available = dict(_variants(crop, scale))
            for vname in plan["variants"]:
                image = available.get(vname)
                if image is None or budget <= 0:
                    continue
                for kind, psm in plan["passes"]:
                    if budget <= 0 or _out_of_time():
                        break
                    budget -= 1
                    calls_used += 1
                    tag = f"{kind}/{vname}/x{scale}/psm{psm}/r{region_idx}"

                    if kind == "labelled":
                        # Unconstrained OCR, then pull the digits that sit next
                        # to the words "code"/"pin" - the strongest signal, since
                        # it cannot be a clock or a channel number.
                        for m in _LABELLED_PIN_RE.finditer(_ocr(image, psm=psm)):
                            _add(_normalise_digits(m.group(1)),
                                 region_w * _METHOD_WEIGHT["labelled"], tag)
                        continue

                    strict = kind == "strict"
                    text = _ocr(image, psm=psm, digits_only=True, strict=strict)
                    whole = _normalise_digits(text)
                    weight = region_w * _METHOD_WEIGHT["whitelist"] * (1.5 if strict else 0.7)
                    if PIN_MIN_DIGITS <= len(whole) <= PIN_MAX_DIGITS:
                        _add(whole, weight, tag)
                    else:
                        for m in _BARE_DIGITS_RE.finditer(whole):
                            _add(m.group(1), region_w * _METHOD_WEIGHT["bare"], tag)

        # A clear winner from the centred dialog is enough; going wider only
        # invites clock/channel digits into the vote.
        if scores and region_idx <= 1:
            ranked = sorted(scores.values(), reverse=True)
            if len(ranked) == 1 or ranked[0] >= 2.0 * ranked[1]:
                break

    out = [
        {"pin": pin, "score": round(score, 2), "hits": hits[pin], "sources": sources[pin]}
        for pin, score in sorted(scores.items(), key=lambda kv: -kv[1])
    ]
    if out:
        log.debug("sgs_autopair: PIN candidates (%s, %d calls used): %s",
                  effort, calls_used,
                  [(c["pin"], c["score"], c["hits"]) for c in out[:4]])
    return out


def read_pin_candidates(frame=None, effort: str = "exhaustive") -> List[Tuple[str, str]]:
    """Back-compatible one-shot view of :func:`score_pin_candidates`.

    Defaults to the exhaustive tier because this is a single explicit read (an
    operator asking "what PIN can you see?"), not a poll inside a loop, so it
    should search every region -- including the bottom-banner layout that the
    fast/deep tiers skip on purpose.
    """
    return [(c["pin"], c["sources"][0] if c["sources"] else "?")
            for c in score_pin_candidates(frame, effort=effort)]


def pairing_screen_visible(frame=None) -> bool:
    """True when the current frame looks like the pairing dialog."""
    if frame is None and _get_frame is not None:
        frame = _get_frame()
    if frame is None or not getattr(frame, "size", 0):
        return False
    text = _ocr(_prep(_crop(frame, (0.10, 0.20, 0.90, 0.80))), psm=6).lower()
    return any(k in text for k in PAIR_SCREEN_KEYWORDS)


def wait_for_pin(
    timeout_s: float = PIN_READ_TIMEOUT_S,
    stable_reads: int = PIN_STABLE_READS,
) -> Optional[str]:
    """Poll the video feed until one PIN clearly wins.

    Two conditions must both hold before a PIN is returned:

      * it has been seen in at least ``stable_reads`` *different frames*, and
      * its accumulated score leads the runner-up by a clear margin.

    Requiring cross-frame agreement matters because the receiver invalidates the
    PIN after a rejected ``device_pairing_complete``, so a single misread digit
    costs a whole pairing session.
    """
    if _get_frame is None:
        log.error("sgs_autopair: no frame source registered — cannot OCR the PIN")
        return None

    deadline = time.time() + float(timeout_s)
    total: Dict[str, float] = {}
    frames_seen: Dict[str, int] = {}
    example: Dict[str, str] = {}
    polls = 0

    while time.time() < deadline:
        polls += 1
        # Escalate effort: cheap passes first (cross-frame voting usually settles
        # it), heavier passes only if the cheap ones are not converging.
        if polls <= 3:
            effort = "fast"
        elif polls <= 8:
            effort = "deep"
        else:
            effort = "exhaustive"
        remaining = max(1.0, deadline - time.time())
        tier_budget = float(_EFFORT_PLANS.get(effort, {}).get("time_budget_s") or remaining)
        for cand in score_pin_candidates(
            effort=effort, time_budget_s=min(tier_budget, remaining)
        ):
            pin = cand["pin"]
            total[pin] = total.get(pin, 0.0) + cand["score"]
            frames_seen[pin] = frames_seen.get(pin, 0) + 1
            example.setdefault(pin, (cand["sources"] or ["?"])[0])

        ranked = sorted(total.items(), key=lambda kv: -kv[1])
        if ranked:
            best_pin, best_score = ranked[0]
            runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
            clear = best_score >= 1.5 * runner_up if runner_up else True
            if frames_seen.get(best_pin, 0) >= stable_reads and clear:
                log.info(
                    "sgs_autopair: PIN %s confirmed — score %.1f vs runner-up %.1f, "
                    "seen in %d frame(s), first via %s (%d polls, effort=%s)",
                    best_pin, best_score, runner_up,
                    frames_seen[best_pin], example.get(best_pin), polls, effort,
                )
                _set_phase("pin_read", pin_digits=len(best_pin),
                           frames=frames_seen[best_pin], polls=polls)
                return best_pin

        if polls % 5 == 0:
            log.info("sgs_autopair: still hunting the PIN (%d polls, leaders=%s)",
                     polls, [(p, round(s, 1)) for p, s in ranked[:4]])
        time.sleep(PIN_READ_INTERVAL_S)

    if total:
        best_pin, best_score = max(total.items(), key=lambda kv: kv[1])
        log.warning(
            "sgs_autopair: no PIN met the confidence bar in %.0fs; best guess %s "
            "(score %.1f, %d frame(s)) — trying it anyway",
            timeout_s, best_pin, best_score, frames_seen.get(best_pin, 0),
        )
        return best_pin

    log.error("sgs_autopair: PIN never read from screen after %.0fs (%d polls)",
              timeout_s, polls)
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Handshake steps
# ─────────────────────────────────────────────────────────────────────────────

def pair_start(alias: str) -> Dict[str, Any]:
    """Step 1 — ask the receiver to display a pairing PIN."""
    entry = _entry(alias)
    ip, stb_id = entry.get("ip"), entry.get("stb")
    if not ip or not stb_id:
        return {"ok": False, "error": "alias %r has no ip/stb in base.txt" % alias}

    payload = _pair_envelope(str(stb_id), "device_pairing_start")
    log.info("sgs_autopair: device_pairing_start -> %s (stb=%s receiver=%s)",
             ip, stb_id, payload["receiver"])
    resp = _post_noauth(str(ip), payload, port_hint=entry.get("port"))
    ok = resp.get("result") == 1
    if not ok:
        log.error("sgs_autopair: device_pairing_start failed: %s",
                  json.dumps(resp)[:400])
    return {"ok": ok, "response": resp, "payload": payload, "ip": ip, "stb": stb_id}


def pair_complete(alias: str, pin: str) -> Dict[str, Any]:
    """Step 2 — submit the PIN and capture the issued credentials."""
    entry = _entry(alias)
    ip, stb_id = entry.get("ip"), entry.get("stb")
    if not ip or not stb_id:
        return {"ok": False, "error": "alias %r has no ip/stb in base.txt" % alias}

    payload = _pair_envelope(str(stb_id), "device_pairing_complete",
                             pin=str(pin).strip())
    log.info("sgs_autopair: device_pairing_complete -> %s (pin=%s)", ip, pin)
    resp = _post_noauth(str(ip), payload, port_hint=entry.get("port"))
    if resp.get("result") != 1:
        log.error("sgs_autopair: device_pairing_complete failed: %s",
                  json.dumps(resp)[:400])
        return {"ok": False, "response": resp}

    login, passwd = resp.get("name"), resp.get("passwd")
    if not login or not passwd:
        log.error("sgs_autopair: pairing reported success but returned no "
                  "credentials: %s", json.dumps(resp)[:300])
        return {"ok": False, "response": resp, "error": "no_credentials_in_response"}

    saved = _save_fields(alias, {
        "lname": str(login),
        "passwd": str(passwd),
        "prod": True,
        "protocol": entry.get("protocol", "SGS"),
        "pair_rid": payload["receiver"],
        "paired_ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    if not saved:
        # Surface the credentials so a human can still rescue them: the receiver
        # will not re-issue this pair.
        log.error("sgs_autopair: COULD NOT PERSIST credentials — record them now: "
                  "lname=%s passwd=%s", login, passwd)
        return {"ok": False, "error": "persist_failed",
                "lname": login, "passwd": passwd, "response": resp}

    return {"ok": True, "lname": login, "passwd_present": True, "response": resp}


def attach(alias: str) -> Dict[str, Any]:
    """Step 3 — authenticated attach to obtain a connection id (cid)."""
    entry = _entry(alias)
    creds = (entry.get("lname"), entry.get("passwd"))
    if not all(creds):
        return {"ok": False, "error": "not_paired"}

    from jamboree.sgs_bridge import _attach, CID_CACHE  # reuse the TLS/cert logic
    ip, stb_id = str(entry.get("ip")), str(entry.get("stb"))
    try:
        cid = _attach(stb_id, ip, (str(creds[0]), str(creds[1])), verbose=False)
    except Exception as exc:
        log.warning("sgs_autopair: attach failed: %s", exc)
        return {"ok": False, "error": "attach_failed", "detail": str(exc)}
    _save_fields(alias, {"cid": int(cid)})
    return {"ok": True, "cid": int(cid)}


# ─────────────────────────────────────────────────────────────────────────────
#  Verification — "did the pair actually work and are commands active?"
# ─────────────────────────────────────────────────────────────────────────────

def _frame_delta(a, b) -> float:
    try:
        import cv2, numpy as np
        if a is None or b is None:
            return -1.0
        ga = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY) if len(a.shape) == 3 else a
        gb = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY) if len(b.shape) == 3 else b
        if ga.shape != gb.shape:
            gb = cv2.resize(gb, (ga.shape[1], ga.shape[0]))
        return float(np.mean(cv2.absdiff(ga, gb)))
    except Exception as exc:
        log.debug("sgs_autopair: frame delta error: %s", exc)
        return -1.0


def verify_commands_active(alias: str, cleanup: bool = True) -> Dict[str, Any]:
    """Prove that authenticated SGS remote keys are reaching the receiver.

    Two independent signals, reported separately so a partial result is not
    mistaken for a pass:

      ``sgs_accepted``  the box returned result==1 for a real remote_key
      ``screen_changed`` the captured video visibly changed afterwards

    ``sgs_accepted`` alone only proves the HTTP/auth layer works.  The screen
    delta is what proves the keypress actually did something, which is the part
    that silently regressed before.
    """
    out: Dict[str, Any] = {
        "alias": alias,
        "sgs_accepted": False,
        "screen_changed": None,
        "frame_delta": None,
        "cid": None,
        "errors": [],
    }
    entry = _entry(alias)
    if not (entry.get("lname") and entry.get("passwd")):
        out["errors"].append("not_paired")
        return out

    att = attach(alias)
    out["cid"] = att.get("cid")
    if not att.get("ok"):
        out["errors"].append(f"attach: {att.get('error')}: {att.get('detail','')}")
        # A Hopper can still take remote keys without a cid, so keep going.

    before = _get_frame() if _get_frame is not None else None

    # Send a benign, reversible key over SGS *only* — force="sgs" so the v39 RF
    # fallback cannot make a broken SGS link look healthy.
    if _ctl is None:
        out["errors"].append("no controller registered")
        return out
    remote = str(entry.get("remote") or "14")
    delay = int((_CFG or {}).get("default_delay_ms", 120))
    try:
        try:
            _ctl.handle_auto_remote(remote, alias, "info", delay, force="sgs")
        except TypeError:
            _ctl.handle_auto_remote(remote, alias, "info", delay)
        out["sgs_accepted"] = True
        log.info("sgs_autopair: verification key accepted over SGS")
    except Exception as exc:
        out["errors"].append(f"remote_key: {exc}")
        log.warning("sgs_autopair: verification key rejected: %s", exc)

    if out["sgs_accepted"] and before is not None:
        time.sleep(VERIFY_SETTLE_S)
        after = _get_frame() if _get_frame is not None else None
        delta = _frame_delta(before, after)
        out["frame_delta"] = round(delta, 3) if delta >= 0 else None
        if delta >= 0:
            out["screen_changed"] = delta >= SCREEN_CHANGE_THRESHOLD
            log.info("sgs_autopair: screen delta after key = %.3f (threshold %.2f) -> changed=%s",
                     delta, SCREEN_CHANGE_THRESHOLD, out["screen_changed"])

    if cleanup and out["sgs_accepted"]:
        for key in ("back", "cancel"):
            try:
                try:
                    _ctl.handle_auto_remote(remote, alias, key, delay, force="sgs")
                except TypeError:
                    _ctl.handle_auto_remote(remote, alias, key, delay)
                break
            except Exception:
                continue

    out["ok"] = bool(out["sgs_accepted"])
    out["fully_verified"] = bool(out["sgs_accepted"] and out["screen_changed"])
    return out


def verify_credentials_persisted(alias: str, expect_login: Optional[str] = None) -> Dict[str, Any]:
    """Re-read base.txt from disk and confirm the credentials are really there.

    Deliberately bypasses the in-memory store so this checks the *file*, which
    is what survives a restart.
    """
    from jamboree import base_io
    doc = base_io.read_document(_base_path())
    entry = (doc.get("stbs", {}) or {}).get(alias, {}) or {}
    out = {
        "alias": alias,
        "on_disk": bool(entry.get("lname")) and bool(entry.get("passwd")),
        "lname": entry.get("lname"),
        "paired_ts": entry.get("paired_ts"),
        "pair_rid": entry.get("pair_rid"),
        "other_top_level_keys": sorted(k for k in doc if k != "stbs"),
        "sibling_aliases": sorted(k for k in (doc.get("stbs") or {}) if k != alias),
    }
    if expect_login is not None:
        out["matches_expected_login"] = (entry.get("lname") == expect_login)
    # Fields that must have survived the credential write.
    out["identity_intact"] = all(entry.get(f) for f in ("ip", "stb"))
    return out


# ─────────────────────────────────────────────────────────────────────────────
#  Orchestration
# ─────────────────────────────────────────────────────────────────────────────

def auto_pair(
    alias: Optional[str] = None,
    *,
    pin: Optional[str] = None,
    force: bool = False,
    verify: bool = True,
    pin_timeout_s: float = PIN_READ_TIMEOUT_S,
    max_pin_attempts: int = MAX_PIN_ATTEMPTS,
) -> Dict[str, Any]:
    """Run the whole flow: start -> read PIN -> complete -> persist -> verify.

    ``pin`` skips OCR (useful for a human-assisted run or a unit test).
    ``force`` re-pairs even when usable credentials already exist.
    """
    alias = alias or str((_CFG or {}).get("stb_alias", "found1"))
    result: Dict[str, Any] = {
        "alias": alias,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "ok": False,
        "steps": {},
        "detail": "",
    }

    with _lock:
        if _state.get("active"):
            return {**result, "detail": "another pairing run is already active"}
        _state["active"] = True
        _state["detail"] = {}

    try:
        _set_phase("preflight", alias=alias)
        entry = _entry(alias)
        if not entry:
            result["detail"] = f"alias {alias!r} not found in base.txt"
            _set_phase("failed", reason="unknown_alias")
            return result
        result["steps"]["preflight"] = {
            "ip": entry.get("ip"), "stb": entry.get("stb"),
            "credentials": credentials_status(alias),
        }

        # Already paired and the credentials belong to this PC?
        cs = credentials_status(alias)
        if cs["paired"] and not cs["stale_rid"] and not force:
            _set_phase("verifying_existing")
            v = verify_commands_active(alias)
            result["steps"]["verify_existing"] = v
            if v.get("ok"):
                result["ok"] = True
                result["detail"] = "already paired; existing credentials work"
                _set_phase("done", reason="already_paired")
                return result
            log.warning("sgs_autopair: stored credentials no longer work (%s) — re-pairing",
                        v.get("errors"))
        elif cs["stale_rid"]:
            log.warning(
                "sgs_autopair: stored credentials were issued to receiver id %s but "
                "this host is now %s — they cannot work, re-pairing",
                cs["pair_rid"], cs["current_rid"],
            )

        # Confirm we are talking to an actual receiver before starting.
        try:
            import ip_recovery
            ident = ip_recovery._probe_device_identity(str(entry.get("ip")))
            result["steps"]["identity"] = ident
            if ident.get("is_stb") is False:
                result["detail"] = (
                    f"{entry.get('ip')} is not a set-top box ({ident.get('reason')}) — "
                    "fix the IP in base.txt (or let ip_recovery find it) before pairing"
                )
                _set_phase("failed", reason="not_an_stb")
                return result
        except Exception as exc:
            log.debug("sgs_autopair: identity probe skipped: %s", exc)

        # ── Steps 1-3, retried as a unit ────────────────────────────────
        # The receiver invalidates the displayed PIN as soon as a
        # device_pairing_complete is rejected, so a misread digit cannot be
        # retried on its own -- the whole handshake has to start again and a
        # fresh PIN gets drawn.  That is why this is one retry loop rather than
        # a retry around the OCR call.
        done: Dict[str, Any] = {}
        use_pin = ""
        attempts = 1 if pin else max(1, int(max_pin_attempts))
        rejected: List[str] = []

        for attempt in range(1, attempts + 1):
            result["steps"].setdefault("attempts", [])

            _set_phase("pair_start", attempt=attempt)
            start = pair_start(alias)
            if attempt == 1:
                result["steps"]["pair_start"] = start
            if not start.get("ok"):
                result["detail"] = "device_pairing_start rejected: %s" % json.dumps(
                    start.get("response", {}))[:300]
                _set_phase("failed", reason="pair_start")
                return result

            # ── obtain the PIN ──────────────────────────────────────────
            if pin:
                _set_phase("pin_supplied")
                use_pin = str(pin).strip()
            else:
                _set_phase("pin_ocr", attempt=attempt)
                # Give the box a moment to actually draw the dialog.
                time.sleep(1.5)
                use_pin = wait_for_pin(timeout_s=pin_timeout_s) or ""
                # Do not resubmit a PIN the receiver already rejected.
                if use_pin and use_pin in rejected:
                    log.warning(
                        "sgs_autopair: OCR produced the already-rejected PIN %s again; "
                        "re-reading with a stricter confidence bar", use_pin,
                    )
                    use_pin = wait_for_pin(
                        timeout_s=min(pin_timeout_s, 20.0),
                        stable_reads=PIN_STABLE_READS + 1,
                    ) or ""

            result["steps"]["attempts"].append({
                "attempt": attempt,
                "pin_digits": len(use_pin),
                "pin_source": "supplied" if pin else "ocr",
            })

            if not use_pin:
                result["detail"] = (
                    "pairing started and the PIN is on screen, but OCR could not "
                    "read it — resubmit with an explicit pin="
                )
                _set_phase("failed", reason="pin_unreadable")
                return result

            # ── complete pairing (credentials are persisted here) ───────
            _set_phase("pair_complete", attempt=attempt)
            done = pair_complete(alias, use_pin)
            result["steps"]["pair_complete"] = {
                k: v for k, v in done.items() if k != "response"
            }
            if done.get("ok"):
                break

            rejected.append(use_pin)
            log.warning(
                "sgs_autopair: attempt %d/%d rejected PIN (%s) — restarting the "
                "handshake for a fresh code",
                attempt, attempts, json.dumps(done.get("response", {}))[:160],
            )
            if attempt < attempts:
                time.sleep(2.0)

        result["steps"]["pin"] = {
            "source": "supplied" if pin else "ocr",
            "digits": len(use_pin),
            "value": use_pin if pin else ("*" * len(use_pin)),
            "rejected_count": len(rejected),
        }
        if not done.get("ok"):
            result["detail"] = (
                "device_pairing_complete failed after %d attempt(s): %s"
                % (attempts, json.dumps(done.get("response", {}))[:280])
            )
            _set_phase("failed", reason="pair_complete")
            return result

        # ── Step 4: prove the credentials survived to disk ──────────────
        _set_phase("verify_persistence")
        persisted = verify_credentials_persisted(alias, expect_login=done.get("lname"))
        result["steps"]["persistence"] = persisted
        if not persisted.get("on_disk"):
            result["detail"] = "credentials were issued but are not in base.txt on disk"
            _set_phase("failed", reason="not_persisted")
            return result

        # ── Step 5: prove commands are actually active ──────────────────
        if verify:
            _set_phase("verify_commands")
            v = verify_commands_active(alias)
            result["steps"]["verify_commands"] = v
            result["ok"] = bool(v.get("ok"))
            result["detail"] = (
                "paired and verified (screen responded)" if v.get("fully_verified")
                else "paired; SGS accepted the key but the screen did not visibly change"
                if v.get("ok")
                else "paired and credentials stored, but SGS commands still fail: %s"
                % v.get("errors")
            )
        else:
            result["ok"] = True
            result["detail"] = "paired; verification skipped by request"

        _set_phase("done" if result["ok"] else "failed", reason=result["detail"][:80])
        return result

    except Exception as exc:
        log.exception("sgs_autopair: unhandled error")
        result["detail"] = f"exception: {exc}"
        _set_phase("failed", reason="exception")
        return result
    finally:
        with _lock:
            _state["active"] = False
            _state["last_result"] = dict(result)


def auto_pair_async(alias: Optional[str] = None, **kwargs: Any) -> bool:
    """Kick off :func:`auto_pair` on a daemon thread (for the HTTP route)."""
    with _lock:
        if _state.get("active"):
            return False
    threading.Thread(
        target=lambda: auto_pair(alias, **kwargs),
        name="SGSAutoPairWorker", daemon=True,
    ).start()
    return True


# ─────────────────────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────────────────────

def _main() -> int:
    ap = argparse.ArgumentParser(description="Automated SGS PIN pairing")
    ap.add_argument("--alias", default="found1", help="STB alias in base.txt")
    ap.add_argument("--pin", help="supply the PIN manually (skips OCR)")
    ap.add_argument("--force", action="store_true", help="re-pair even if already paired")
    ap.add_argument("--attempts", type=int, default=MAX_PIN_ATTEMPTS,
                    help="handshake restarts allowed when the PIN is rejected")
    ap.add_argument("--no-verify", action="store_true", help="skip command verification")
    ap.add_argument("--status", action="store_true", help="show pairing status and exit")
    ap.add_argument("--verify-only", action="store_true",
                    help="only check existing credentials/commands")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(levelname)s] %(asctime)s - %(name)s - %(message)s",
    )

    from jamboree.stb_store import store as _s
    from jamboree.app import ctl as _c
    set_dependencies(store=_s, ctl=_c, CFG={"stb_alias": args.alias, "default_delay_ms": 120})

    if args.status:
        print(json.dumps({
            "credentials": credentials_status(args.alias),
            "persistence": verify_credentials_persisted(args.alias),
        }, indent=2))
        return 0

    if args.verify_only:
        print(json.dumps(verify_commands_active(args.alias), indent=2))
        return 0

    out = auto_pair(args.alias, pin=args.pin, force=args.force,
                    verify=not args.no_verify, max_pin_attempts=args.attempts)
    print(json.dumps(out, indent=2, default=str))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(_main())
