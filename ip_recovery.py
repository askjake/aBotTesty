#!/usr/bin/env python3
"""ip_recovery.py — Automatic STB IP change detection and self-healing.

Problem
-------
The STB's DHCP lease renews overnight.  The new IP breaks SGS (which talks to
the STB over TCP) while the RTSP encoder stream (link-local 169.254.x.x) keeps
flowing undisturbed.  The mismatch looks like:
    • video_health  → active_video  (encoder is fine)
    • SGS command   → RuntimeError / subprocess returncode != 0

This module detects that exact divergence, uses JAMboreeLite's RF4CE path
(which does *not* need the STB's IP — it goes over the serial/RF4CE radio) to
navigate the STB to its Network Settings screen, OCRs the IP from the live
frame, writes it to base.txt, and signals the rest of the app to reload —
all without restarting Flask or the crawler.

RF4CE reliability note
-----------------------
RF4CE commands occasionally don't land.  After each navigation step we:
  1. Wait a generous settle window.
  2. Grab a fresh frame and OCR it.
  3. Confirm the expected text is present before moving on.
  4. Retry up to MAX_KEY_ATTEMPTS times if confirmation fails.

Integration points (set by merged_app.py after import):
    ip_recovery.set_dependencies(
        get_frame    = monitor.get_frame,
        get_status   = monitor.get_status,
        store        = store,
        ctl          = ctl,
        CFG          = CFG,
    )

Public API:
    is_sgs_dead_but_video_alive(exc) -> bool
    maybe_trigger_recovery()         -> bool   (idempotent, thread-safe)
    get_recovery_status()            -> dict
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import cv2
import numpy as np

log = logging.getLogger("merged.ip_recovery")

# ─────────────────────────────────────────────────────────────────────────────
#  Tunables
# ─────────────────────────────────────────────────────────────────────────────

# How long to hold HOME to reach Sys-Info / Network screen
HOME_HOLD_MS: int = 3000
# Short press for digit '2' (navigates to Network on most Hopper firmware)
DIGIT_PRESS_MS: int = 80
# How many seconds to wait after each RF4CE press before reading the screen
KEY_SETTLE_S: float = 2.2
# How many times to retry a single key if the screen hasn't changed
MAX_KEY_ATTEMPTS: int = 5
# How many full recovery cycles before giving up and staying paused
MAX_RECOVERY_CYCLES: int = 3
# Minimum seconds between two recovery attempts (avoid hammering)
RECOVERY_COOLDOWN_S: float = 30.0
# OCR prep: upscale factor for network-screen IP text
OCR_SCALE: float = 2.5
# Regex that matches a plausible STB LAN IP (10.x.x.x or 192.168.x.x etc.)
# Full 4-octet pattern with non-digit boundaries to avoid partial matches.
_OCT = r"(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)"
IP_RE = re.compile(
    r"(?<![\d.])("
    r"(?:10|172\.(?:1[6-9]|2\d|3[01])|192\.168)"
    r"\." + _OCT + r"\." + _OCT +
    r")(?![\d.])"
)
# Broader fallback: any dotted-quad that looks like a routable IP
IP_RE_BROAD = re.compile(
    r"(?<![\d.])(" + _OCT + r"\." + _OCT + r"\." + _OCT + r"\." + _OCT + r")(?![\d.])"
)

# ─────────────────────────────────────────────────────────────────────────────
#  State
# ─────────────────────────────────────────────────────────────────────────────

_lock = threading.Lock()
_recovery_active = False
_last_attempt_ts: float = 0.0
_last_result: Dict[str, Any] = {}
_consecutive_sgs_failures: int = 0
_SGS_FAIL_THRESHOLD: int = 3       # need N consecutive fails before triggering

# Dependency handles — filled by set_dependencies()
_get_frame: Optional[Callable[[], Optional[np.ndarray]]] = None
_get_status: Optional[Callable[[], Dict[str, Any]]] = None
_store: Any = None
_ctl: Any = None
_CFG: Optional[Dict[str, Any]] = None


def set_dependencies(
    *,
    get_frame: Callable[[], Optional[np.ndarray]],
    get_status: Callable[[], Dict[str, Any]],
    store: Any,
    ctl: Any,
    CFG: Dict[str, Any],
) -> None:
    """Called once from merged_app.py after all singletons are created."""
    global _get_frame, _get_status, _store, _ctl, _CFG
    _get_frame  = get_frame
    _get_status = get_status
    _store      = store
    _ctl        = ctl
    _CFG        = CFG
    log.info("ip_recovery: dependencies registered")


# ─────────────────────────────────────────────────────────────────────────────
#  Public helpers
# ─────────────────────────────────────────────────────────────────────────────

def is_sgs_dead_but_video_alive(exc: Optional[BaseException] = None) -> bool:
    """Return True when video is streaming but the last SGS call raised an error.

    Callers can pass the caught exception for richer logging; it is not required.
    """
    if _get_status is None:
        return False
    try:
        st = _get_status()
        video_ok = bool(st.get("active")) and st.get("signal_class") not in {
            "black_screen", "blank_or_no_signal", "no_frame", None
        }
        if not video_ok:
            return False
        if exc is not None:
            msg = str(exc).lower()
            # Positive signals: subprocess returncode, connection refused, timeout
            sgs_fail = any(k in msg for k in (
                "returncode", "sgs_remote error", "connection refused",
                "timed out", "timeout", "no route to host", "network unreachable",
                "failed to connect", "attach failed", "non-json",
            ))
            if not sgs_fail:
                return False
        return True
    except Exception:
        return False


def note_sgs_failure(exc: Optional[BaseException] = None) -> None:
    """Increment consecutive-failure counter; trigger recovery when threshold hit."""
    global _consecutive_sgs_failures
    with _lock:
        _consecutive_sgs_failures += 1
        count = _consecutive_sgs_failures
    log.debug("ip_recovery: SGS failure #%d (exc=%s)", count, exc)
    if count >= _SGS_FAIL_THRESHOLD:
        if is_sgs_dead_but_video_alive(exc):
            maybe_trigger_recovery()


def note_sgs_success() -> None:
    """Reset consecutive-failure counter on a clean SGS response."""
    global _consecutive_sgs_failures
    with _lock:
        _consecutive_sgs_failures = 0


def maybe_trigger_recovery() -> bool:
    """Idempotent entry point — starts recovery in a daemon thread if not already running."""
    global _recovery_active, _last_attempt_ts
    with _lock:
        now = time.time()
        if _recovery_active:
            log.debug("ip_recovery: already in progress, skipping duplicate trigger")
            return False
        if now - _last_attempt_ts < RECOVERY_COOLDOWN_S:
            remaining = RECOVERY_COOLDOWN_S - (now - _last_attempt_ts)
            log.debug("ip_recovery: cooldown active (%.0fs remaining)", remaining)
            return False
        _recovery_active = True
        _last_attempt_ts = now

    if _ctl is None or _get_frame is None or _store is None or _CFG is None:
        log.warning("ip_recovery: maybe_trigger_recovery called but dependencies not set — skipping")
        with _lock:
            _recovery_active = False
        return False
    log.warning("ip_recovery: triggering autonomous IP recovery")
    t = threading.Thread(target=_recovery_worker, name="IPRecoveryWorker", daemon=True)
    t.start()
    return True


def get_recovery_status() -> Dict[str, Any]:
    with _lock:
        return {
            "active": _recovery_active,
            "last_result": dict(_last_result),
            "consecutive_sgs_failures": _consecutive_sgs_failures,
            "last_attempt_ago_s": round(time.time() - _last_attempt_ts, 1) if _last_attempt_ts else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
#  OCR helpers (self-contained, no pytesseract import at module level)
# ─────────────────────────────────────────────────────────────────────────────

def _get_pytesseract() -> Any:
    try:
        import pytesseract  # type: ignore
        return pytesseract
    except Exception:
        return None


def _prep_ocr(img: np.ndarray, scale: float = OCR_SCALE) -> np.ndarray:
    """Upscale + sharpen + normalize — mirrors region_first_perception.prep_for_ocr."""
    if img is None or not getattr(img, "size", 0):
        return img
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()
    gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.bilateralFilter(gray, 5, 35, 35)
    return cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)


def _ocr_frame(frame: np.ndarray, psm: int = 6) -> str:
    """Full-frame OCR via pytesseract, returns clean string."""
    pt = _get_pytesseract()
    if pt is None or frame is None or not getattr(frame, "size", 0):
        return ""
    try:
        prepped = _prep_ocr(frame)
        raw = pt.image_to_string(
            prepped,
            config=f"--oem 3 --psm {psm} -c user_defined_dpi=300",
        )
        # Normalise whitespace
        return re.sub(r"\s+", " ", str(raw or "")).strip()
    except Exception as exc:
        log.debug("ip_recovery: OCR failed: %s", exc)
        return ""


def _ocr_region(frame: np.ndarray, box_norm: tuple, psm: int = 6) -> str:
    """OCR a normalised (x0,y0,x1,y1) crop of frame."""
    if frame is None or not getattr(frame, "size", 0):
        return ""
    h, w = frame.shape[:2]
    x0, y0, x1, y1 = box_norm
    crop = frame[
        max(0, int(y0 * h)): min(h, int(y1 * h)),
        max(0, int(x0 * w)): min(w, int(x1 * w)),
    ]
    if not getattr(crop, "size", 0):
        return ""
    return _ocr_frame(crop, psm=psm)


def _extract_ip(text: str) -> Optional[str]:
    """Return the first plausible STB LAN IP from OCR text, or None."""
    # Prefer private-range match first
    m = IP_RE.search(text)
    if m:
        return m.group(1)
    # Broader fallback — filter out clearly invalid octets
    for m in IP_RE_BROAD.finditer(text):
        parts = m.group(1).split(".")
        if all(0 <= int(p) <= 255 for p in parts) and parts[0] not in ("0", "255", "127"):
            return m.group(1)
    return None


def _screen_contains(frame: np.ndarray, keywords: list) -> bool:
    """Quick check: does full OCR of frame contain any of these keywords?"""
    text = _ocr_frame(frame, psm=11).lower()
    return any(k.lower() in text for k in keywords)


# ─────────────────────────────────────────────────────────────────────────────
#  RF4CE navigation helpers
# ─────────────────────────────────────────────────────────────────────────────

def _rf4ce_press(button: str, delay_ms: int, *, attempts: int = MAX_KEY_ATTEMPTS, settle_s: float = KEY_SETTLE_S) -> bool:
    """Send an RF4CE key via JAMboreeLite with retry logic.

    Uses ctl.handle_auto_remote() directly — same path as the /auto/ HTTP route
    but without the HTTP overhead.  Returns True if the call succeeded at least once.
    """
    if _ctl is None or _CFG is None or _store is None:
        log.error("ip_recovery: dependencies not set — cannot press RF4CE key")
        return False

    alias = str(_CFG.get("stb_alias", "found1"))
    remote = str(_CFG.get("remote", "14"))

    for attempt in range(1, attempts + 1):
        try:
            result = _ctl.handle_auto_remote(remote, alias, button, delay_ms)
            log.debug(
                "ip_recovery: RF4CE %s/%dms attempt %d → %s",
                button, delay_ms, attempt, result,
            )
            time.sleep(settle_s)
            return True
        except Exception as exc:
            log.warning(
                "ip_recovery: RF4CE %s attempt %d failed: %s",
                button, attempt, exc,
            )
            time.sleep(1.0)

    return False


def _confirm_screen(expected_keywords: list, settle_extra_s: float = 0.5) -> bool:
    """Grab a frame and confirm the screen matches expected keywords."""
    time.sleep(settle_extra_s)
    if _get_frame is None:
        return False
    frame = _get_frame()
    if frame is None:
        return False
    return _screen_contains(frame, expected_keywords)


# ─────────────────────────────────────────────────────────────────────────────
#  Core recovery worker
# ─────────────────────────────────────────────────────────────────────────────

def _navigate_to_network_screen() -> bool:
    """Navigate the STB to the Network Settings / IP info screen.

    Sequence mirrors what the operator does manually:
        HOME held 3 s  → opens System Info / Settings overlay
        2 (80 ms)      → selects Network item

    Returns True if we land on a screen that contains network/IP text.
    """
    log.info("ip_recovery: step 1 — sending HOME (3 s hold) via RF4CE")
    if not _rf4ce_press("home", HOME_HOLD_MS, settle_s=2.5):
        log.warning("ip_recovery: HOME press failed completely")
        return False

    # Confirm we left live-TV / whatever the crawler was on.
    # The Sys-Info overlay usually says "Settings", "Network", or "Diagnostics".
    for attempt in range(1, MAX_KEY_ATTEMPTS + 1):
        if _confirm_screen(["settings", "network", "diagnostics", "system", "info"], settle_extra_s=0.3):
            log.info("ip_recovery: HOME confirmed — overlay visible")
            break
        log.debug("ip_recovery: HOME confirmation attempt %d — retrying press", attempt)
        _rf4ce_press("home", HOME_HOLD_MS, attempts=1, settle_s=2.0)
    else:
        log.warning("ip_recovery: could not confirm HOME overlay after %d attempts", MAX_KEY_ATTEMPTS)
        # Continue anyway — the STB may be on a screen where the overlay keywords
        # are not visible but the key still worked (e.g. certain guide states).

    log.info("ip_recovery: step 2 — pressing '2' to select Network")
    if not _rf4ce_press("2", DIGIT_PRESS_MS, settle_s=2.5):
        log.warning("ip_recovery: '2' press failed completely")
        return False

    # Confirm network screen
    for attempt in range(1, MAX_KEY_ATTEMPTS + 1):
        if _confirm_screen(["network", "ip address", "ip:", "ethernet", "wifi", "wireless", "internet"], settle_extra_s=0.3):
            log.info("ip_recovery: network screen confirmed")
            return True
        log.debug("ip_recovery: network screen confirmation attempt %d — retrying '2'", attempt)
        _rf4ce_press("2", DIGIT_PRESS_MS, attempts=1, settle_s=2.0)

    # One last check
    return _confirm_screen(["network", "ip", "ethernet", "address"], settle_extra_s=0.5)


def _read_ip_from_screen() -> Optional[str]:
    """OCR the current frame and extract the STB's IP address.

    Strategy:
      1. OCR the centre portion of the screen (where IP values appear on Hopper UI).
      2. Fall back to full-frame sparse OCR if centre yields nothing.
    """
    if _get_frame is None:
        return None
    frame = _get_frame()
    if frame is None:
        return None

    # Centre band — IP labels and values live here on Hopper Network screens
    for box, psm in [
        ((0.08, 0.20, 0.92, 0.85), 6),   # main content area
        ((0.08, 0.30, 0.70, 0.75), 6),   # tighter centre
        ((0.0,  0.0,  1.0,  1.0),  11),  # full frame sparse fallback
    ]:
        text = _ocr_region(frame, box, psm=psm)
        log.debug("ip_recovery: OCR box=%s text=%r", box, text[:200])
        ip = _extract_ip(text)
        if ip:
            log.info("ip_recovery: found IP %s in OCR text: %r", ip, text[:200])
            return ip

    return None


def _update_base_txt(new_ip: str) -> bool:
    """Write new IP into base.txt via store.save() and trigger store.reload()."""
    if _store is None or _CFG is None:
        return False
    alias = str(_CFG.get("stb_alias", "found1"))
    try:
        all_stbs = dict(_store.all())
        stb_info = dict(all_stbs.get(alias) or {})
        old_ip = stb_info.get("ip", "unknown")
        stb_info["ip"] = new_ip
        all_stbs[alias] = stb_info
        _store.save({"stbs": all_stbs})
        _store.reload()
        log.info("ip_recovery: base.txt updated — %s → %s (alias=%s)", old_ip, new_ip, alias)
        return True
    except Exception as exc:
        log.error("ip_recovery: failed to update base.txt: %s", exc)
        return False


def _verify_sgs_with_new_ip() -> bool:
    """Send a benign SGS command to confirm the new IP actually works."""
    if _ctl is None or _CFG is None or _store is None:
        return False
    alias = str(_CFG.get("stb_alias", "found1"))
    remote = str(_CFG.get("remote", "sgs"))
    stb = _store.get(alias) or {}
    try:
        # 'info' is a safe read-only key — it just shows channel info on screen
        result = _ctl.handle_auto_remote(remote, alias, "info", 120)
        log.info("ip_recovery: SGS verify succeeded: %s", result)
        return True
    except Exception as exc:
        log.warning("ip_recovery: SGS verify failed with new IP: %s", exc)
        return False


def _escape_to_live_tv() -> None:
    """Best-effort attempt to navigate the STB back to live TV after recovery."""
    log.info("ip_recovery: navigating back to live TV")
    for btn, ms in [("back", 120), ("back", 120), ("home", 120), ("live", 120)]:
        try:
            _rf4ce_press(btn, ms, attempts=2, settle_s=1.0)
        except Exception:
            pass


def _recovery_worker() -> None:
    """Background thread: detect new IP, update base.txt, verify, resume."""
    global _recovery_active, _last_result, _consecutive_sgs_failures

    result: Dict[str, Any] = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "success": False,
        "new_ip": None,
        "cycles": 0,
        "detail": "",
    }

    try:
        for cycle in range(1, MAX_RECOVERY_CYCLES + 1):
            result["cycles"] = cycle
            log.info("ip_recovery: === CYCLE %d / %d ===", cycle, MAX_RECOVERY_CYCLES)

            # ── Step 1: navigate to network screen ──────────────────────────
            if not _navigate_to_network_screen():
                result["detail"] = f"cycle {cycle}: failed to reach network screen"
                log.warning("ip_recovery: %s", result["detail"])
                time.sleep(3.0)
                continue

            # ── Step 2: OCR the IP ───────────────────────────────────────────
            new_ip: Optional[str] = None
            for read_attempt in range(1, 4):
                new_ip = _read_ip_from_screen()
                if new_ip:
                    break
                log.debug("ip_recovery: OCR attempt %d yielded no IP; waiting…", read_attempt)
                time.sleep(1.5)

            if not new_ip:
                result["detail"] = f"cycle {cycle}: could not OCR an IP address from screen"
                log.warning("ip_recovery: %s", result["detail"])
                # Try pressing info/down to scroll to a row that shows the IP
                _rf4ce_press("down", 120, attempts=2, settle_s=1.5)
                continue

            # ── Step 3: update base.txt (hot reload) ─────────────────────────
            if not _update_base_txt(new_ip):
                result["detail"] = f"cycle {cycle}: base.txt update failed for IP {new_ip}"
                log.error("ip_recovery: %s", result["detail"])
                break   # Not a retryable error

            # ── Step 4: escape back to live TV ────────────────────────────────
            _escape_to_live_tv()
            time.sleep(2.0)

            # ── Step 5: verify SGS works with the new IP ──────────────────────
            if _verify_sgs_with_new_ip():
                result["success"] = True
                result["new_ip"] = new_ip
                result["detail"] = f"recovered — new IP {new_ip}"
                # Reset failure counter so the watchdog stops thinking the crawler is sick
                with _lock:
                    _consecutive_sgs_failures = 0
                log.info("ip_recovery: ✓ RECOVERY COMPLETE — STB IP is now %s", new_ip)
                break
            else:
                result["detail"] = f"cycle {cycle}: IP {new_ip} found but SGS verify failed"
                log.warning("ip_recovery: %s", result["detail"])
                time.sleep(5.0)

    except Exception as exc:
        result["detail"] = f"unexpected error: {exc}"
        log.exception("ip_recovery: unexpected error in recovery worker")
    finally:
        with _lock:
            _recovery_active = False
            _last_result = result
        if result["success"]:
            log.info("ip_recovery: worker finished successfully")
        else:
            log.error("ip_recovery: worker finished WITHOUT success — manual intervention may be needed")
