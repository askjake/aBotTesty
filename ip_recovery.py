#!/usr/bin/env python3
"""ip_recovery.py — Automatic STB IP change detection and self-healing.

Problem
-------
The STB's DHCP lease renews overnight.  The new IP breaks SGS (which talks to
the STB over TCP) while the RTSP encoder stream (link-local 169.254.x.x) keeps
flowing undisturbed.  The mismatch looks like:
    • video_health  → active_video  (encoder is fine)
    • SGS command   → RuntimeError / subprocess returncode != 0

This module detects that exact divergence, uses an ARP MAC-address scan to locate the STB's new IP on the LAN
(the STB's MAC does not change on DHCP renewal).  As a secondary fallback it
navigates to the Network Settings screen via SGS and OCRs the IP from the live
frame.  Either way it writes the new IP to base.txt, and signals the rest of the app to reload —
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
import os
import re
import socket
import subprocess
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

# Backup HTTP controller — independent of STB IP, used when SGS is down.
# URL: {BACKUP_HTTP_BASE}/{command}/{duration_ms}
# e.g. http://10.79.85.47:5003/auto/14/Jim's%20STB/home/3000
BACKUP_HTTP_BASE: str        = "http://10.79.85.47:5003/auto/14/Jim's%20STB"
BACKUP_HTTP_DEFAULT_MS: int  = 80
BACKUP_HTTP_TIMEOUT_S: float = 10.0

# ── v39: how we recognise a *dead* SGS link ──────────────────────────────────
# The old code only accepted transport-level words ("connection refused",
# "timed out", ...).  The failure we actually hit in the field was an HTTP 403
# from the box that had taken over the STB's DHCP lease, which matched nothing
# and so recovery never fired.  Auth/permission failures are now first-class
# "SGS is dead" evidence, because on this rig they mean one of:
#   * base.txt points at a different device entirely (lease was reassigned)
#   * the receiver was factory-reset and the pairing credentials are gone
#   * network-remote opt-in got switched off
SGS_DEAD_MARKERS: tuple = (
    # transport
    "returncode", "sgs_remote error", "connection refused", "timed out",
    "timeout", "no route to host", "network unreachable", "failed to connect",
    "attach failed", "non-json", "connection reset", "connection aborted",
    "name or service not known", "host is unreachable", "broken pipe",
    # auth / opt-in / wrong-device  (v39)
    "auth_required_or_opt_in_disabled", "no valid crumb", "http_status\": 403",
    "http_status\": 401", "403", "401", "unauthorized", "forbidden",
    "json_parse_failed", "\"result\": -13", "\"result\": -3",
    "not_paired", "pair first", "no credentials",
    # explicit wrong-device verdict raised by _probe_device_identity()
    "not_an_stb",
)

# Consecutive-failure thresholds.  A definite auth/wrong-device verdict is
# strong evidence, so it needs fewer repeats than a flaky timeout.
_SGS_FAIL_THRESHOLD_AUTH: int = 2

# ── v39: STB identity fingerprinting ────────────────────────────────────────
# Recovery used to trust the ARP table blindly: whatever MAC answered at the
# stored IP became "the STB's MAC".  When the lease moved to a CI server the
# cache was poisoned with that server's MAC and every later ARP sweep happily
# re-discovered the wrong box.  We now fingerprint a candidate before believing
# it is a receiver.
IDENTITY_TIMEOUT_S: float = 3.0

# Response headers that prove the host is *not* a set-top box.
NON_STB_HEADER_MARKERS: tuple = (
    "x-jenkins", "x-hudson", "x-jenkins-session", "x-atlassian-token",
    "x-sonatype", "x-gitlab-feature-category", "x-influxdb-version",
)
# Body/banner substrings that prove the same thing.
NON_STB_BODY_MARKERS: tuple = (
    "crumbissuer", "jenkins", "hudson", "gitlab", "grafana", "kibana",
    "phpmyadmin", "it works!", "index.html.en", "tomcat", "nginx",
    "artifactory", "nexus repository",
)
# Server banners that belong to general-purpose web servers, not receivers.
NON_STB_SERVER_MARKERS: tuple = (
    "apache/", "nginx/", "gunicorn", "werkzeug", "iis/", "lighttpd",
)


def classify_sgs_failure(exc: Optional[BaseException]) -> Dict[str, Any]:
    """Describe an SGS exception so callers can pick a threshold and a message.

    Returns ``{"dead": bool, "kind": str, "threshold": int}`` where *kind* is one
    of ``transport`` / ``auth`` / ``wrong_device`` / ``unknown``.
    """
    msg = (str(exc) if exc is not None else "").lower()
    if not msg:
        return {"dead": True, "kind": "unknown", "threshold": _SGS_FAIL_THRESHOLD}

    if "not_an_stb" in msg:
        return {"dead": True, "kind": "wrong_device", "threshold": 1}

    auth_words = (
        "auth_required_or_opt_in_disabled", "no valid crumb", "403", "401",
        "unauthorized", "forbidden", "not_paired", "pair first",
        "no credentials", '"result": -13',
    )
    if any(w in msg for w in auth_words):
        return {"dead": True, "kind": "auth", "threshold": _SGS_FAIL_THRESHOLD_AUTH}

    if any(w in msg for w in SGS_DEAD_MARKERS):
        return {"dead": True, "kind": "transport", "threshold": _SGS_FAIL_THRESHOLD}

    return {"dead": False, "kind": "unknown", "threshold": _SGS_FAIL_THRESHOLD}


def _probe_device_identity(ip: str, timeout: float = IDENTITY_TIMEOUT_S) -> Dict[str, Any]:
    """Decide whether ``ip`` is plausibly a DISH receiver.

    Returns ``{"is_stb": True|False|None, "reason": str, "server": str}``.
    ``None`` means "cannot tell" -- we only ever *reject* on positive evidence
    that the host is something else, so an unreachable box is never mislabelled.

    This is the guard that would have caught the 2026-08-03 incident, where
    base.txt still pointed at a lease that had been handed to a Jenkins server.
    """
    try:
        import requests  # local import: keeps module import cheap
    except Exception:
        return {"is_stb": None, "reason": "requests_unavailable", "server": ""}

    server = ""
    saw_response = False
    for port, path in ((8080, "/www/sgs"), (80, "/www/sgs"), (8080, "/sgs_noauth")):
        url = f"http://{ip}:{port}{path}"
        try:
            resp = requests.post(
                url, json={"command": "get_version"},
                timeout=timeout,
                headers={"Content-Type": "application/json"},
            )
        except Exception:
            continue
        saw_response = True
        headers = {k.lower(): str(v).lower() for k, v in resp.headers.items()}
        server = headers.get("server", server)
        body = (resp.text or "")[:2000].lower()

        # 1) hard rejects -- unmistakable fingerprints of other software
        for marker in NON_STB_HEADER_MARKERS:
            if marker in headers:
                return {"is_stb": False, "reason": f"header:{marker}", "server": server}
        for marker in NON_STB_BODY_MARKERS:
            if marker in body:
                return {"is_stb": False, "reason": f"body:{marker}", "server": server}
        for marker in NON_STB_SERVER_MARKERS:
            if marker in headers.get("server", ""):
                return {"is_stb": False, "reason": f"server:{marker}", "server": server}

        # 2) positive evidence -- an SGS endpoint answers with a result envelope
        try:
            data = resp.json()
            if isinstance(data, dict) and "result" in data:
                return {"is_stb": True, "reason": "sgs_result_envelope", "server": server}
        except Exception:
            pass

        # 3) a digest challenge from the receiver's own realm is good evidence
        if "digest" in headers.get("www-authenticate", ""):
            return {"is_stb": True, "reason": "digest_challenge", "server": server}

    return {
        "is_stb": None,
        "reason": "inconclusive" if saw_response else "unreachable",
        "server": server,
    }


def verify_stored_ip_identity() -> Dict[str, Any]:
    """Fingerprint whatever currently lives at the stored STB IP.

    Exposed through ``/api/ip_recovery/status`` so an operator can see at a
    glance that base.txt is pointing at the wrong machine.
    """
    if _store is None or _CFG is None:
        return {"is_stb": None, "reason": "dependencies_unset", "ip": None}
    alias = str(_CFG.get("stb_alias", "found1"))
    ip = ((_store.get(alias) or {}).get("ip") or "").strip()
    if not ip:
        return {"is_stb": None, "reason": "no_stored_ip", "ip": None}
    out = _probe_device_identity(ip)
    out["ip"] = ip
    if out.get("is_stb") is False:
        log.error(
            "ip_recovery: stored IP %s is NOT a set-top box (%s, server=%r) - "
            "base.txt is stale, the DHCP lease belongs to another host",
            ip, out.get("reason"), out.get("server"),
        )
    return out


# ─────────────────────────────────────────────────────────────────────────────
#  State
# ─────────────────────────────────────────────────────────────────────────────

_lock = threading.Lock()
_recovery_active = False
_last_attempt_ts: float = 0.0
_last_result: Dict[str, Any] = {}
_consecutive_sgs_failures: int = 0
_SGS_FAIL_THRESHOLD: int = 3       # need N consecutive fails before triggering
_last_sgs_failure: Dict[str, Any] = {}   # v39: classification of the latest failure

# Dependency handles — filled by set_dependencies()
_get_frame: Optional[Callable[[], Optional[np.ndarray]]] = None
_get_status: Optional[Callable[[], Dict[str, Any]]] = None
_store: Any = None
_ctl: Any = None
_CFG: Optional[Dict[str, Any]] = None
_known_stb_mac: Optional[str] = None   # cached while SGS is healthy


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
    # Prime the MAC cache: one immediate attempt, then a background retry loop.
    # The immediate attempt usually misses because ARP hasn't resolved yet;
    # the background thread catches it within a few seconds of the first
    # successful SGS call (note_sgs_success also refreshes the cache).
    try:
        mac = _get_stb_mac()
        if mac:
            global _known_stb_mac
            _known_stb_mac = mac
            log.info("ip_recovery: primed STB MAC cache: %s", mac)
    except Exception:
        pass

    # v39: fingerprint whatever is at the stored IP at startup.  If base.txt is
    # already pointing at the wrong machine, say so once, loudly, instead of
    # letting every subsequent key press fail with an opaque 403.
    def _startup_identity_check() -> None:
        time.sleep(3.0)
        try:
            ident = verify_stored_ip_identity()
            if ident.get("is_stb") is False:
                log.error(
                    "ip_recovery: STARTUP CHECK FAILED — base.txt IP %s is not a "
                    "receiver (%s). SGS commands will fail until the IP is "
                    "corrected; RF fallback will carry traffic meanwhile.",
                    ident.get("ip"), ident.get("reason"),
                )
                maybe_trigger_recovery()
            elif ident.get("is_stb") is True:
                log.info("ip_recovery: startup identity check OK for %s", ident.get("ip"))
        except Exception as exc:
            log.debug("ip_recovery: startup identity check error: %s", exc)

    threading.Thread(
        target=_startup_identity_check, name="STBIdentityCheck", daemon=True
    ).start()

    def _delayed_mac_prime() -> None:
        """Retry MAC priming at 5 s, 20 s, and 60 s after startup."""
        global _known_stb_mac
        for wait_s in (5.0, 15.0, 40.0):
            time.sleep(wait_s)
            if _known_stb_mac:
                return   # already primed by note_sgs_success or earlier attempt
            try:
                mac = _get_stb_mac()
                if mac:
                    _known_stb_mac = mac
                    log.info(
                        "ip_recovery: delayed MAC prime succeeded (wait=%.0fs): %s",
                        wait_s, mac,
                    )
                    return
            except Exception:
                pass
        log.warning("ip_recovery: delayed MAC prime exhausted all attempts — MAC still unknown")

    threading.Thread(target=_delayed_mac_prime, name="MACPrimeWorker", daemon=True).start()


# ─────────────────────────────────────────────────────────────────────────────
#  Public helpers
# ─────────────────────────────────────────────────────────────────────────────

def is_sgs_dead_but_video_alive(exc: Optional[BaseException] = None) -> bool:
    """Return True when video is streaming but the last SGS call raised an error.

    Callers can pass the caught exception for richer logging; it is not required.

    v39: classification moved to :func:`classify_sgs_failure` so that auth /
    opt-in / wrong-device failures count as evidence.  Previously the keyword
    list only knew about transport errors, so an HTTP 403 from a host that had
    taken over the STB's DHCP lease scored zero matches and recovery never ran.
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
        if exc is not None and not classify_sgs_failure(exc)["dead"]:
            return False
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  Auto-pair escalation (v39)
# ─────────────────────────────────────────────────────────────────────────────
#  A 403 / result:-13 from a host that fingerprints as a genuine receiver is a
#  CREDENTIALS problem, not an IP problem.  Moving the IP around cannot fix it
#  and actively makes things worse (we chase Apache/Jenkins boxes on the same
#  subnet).  The correct response is to re-run the on-screen-PIN pairing
#  handshake, which is what sgs_autopair does.  This module only escalates; all
#  pairing logic lives in sgs_autopair so it stays independently testable.

_AUTOPAIR_COOLDOWN_S: float = 180.0
_autopair_last_ts: float = 0.0
_autopair_last: Dict[str, Any] = {}


def _maybe_trigger_autopair(reason: str, ip: str = "") -> Dict[str, Any]:
    """Kick off a background auto-pair run, at most once per cooldown window.

    Returns a dict describing what was decided so the caller (and
    /api/ip_recovery/status) can report it honestly.
    """
    global _autopair_last_ts, _autopair_last

    if str(os.environ.get("JAMBOREE_AUTOPAIR", "1")).lower() in ("0", "false", "no", "off"):
        out = {"triggered": False, "reason": "disabled_by_env"}
        with _lock:
            _autopair_last = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **out}
        log.warning("ip_recovery: auto-pair suppressed (JAMBOREE_AUTOPAIR=0)")
        return out

    now = time.time()
    with _lock:
        since = now - _autopair_last_ts
        if _autopair_last_ts and since < _AUTOPAIR_COOLDOWN_S:
            out = {"triggered": False, "reason": "cooldown",
                   "retry_in_s": round(_AUTOPAIR_COOLDOWN_S - since, 1)}
            _autopair_last = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **out}
            return out
        _autopair_last_ts = now

    try:
        import sgs_autopair
    except Exception as exc:
        out = {"triggered": False, "reason": f"import_failed: {exc}"}
        with _lock:
            _autopair_last = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **out}
        log.error("ip_recovery: cannot auto-pair, sgs_autopair unavailable: %s", exc)
        return out

    alias = str((_CFG or {}).get("stb_alias", "found1"))
    log.error(
        "ip_recovery: %s IS a receiver but rejects our commands (%s) — this is a "
        "PAIRING problem, not an IP problem. Launching auto-pair for alias %s.",
        ip or "stored IP", reason, alias,
    )
    started = False
    try:
        started = bool(sgs_autopair.auto_pair_async(alias))
    except Exception as exc:
        log.exception("ip_recovery: auto-pair launch failed")
        out = {"triggered": False, "reason": f"launch_failed: {exc}", "alias": alias}
        with _lock:
            _autopair_last = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **out}
        return out

    out = {"triggered": started, "alias": alias,
           "reason": reason if started else "already_running"}
    with _lock:
        _autopair_last = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **out}
    return out


def note_sgs_failure(exc: Optional[BaseException] = None) -> None:
    """Increment consecutive-failure counter; trigger recovery when threshold hit."""
    global _consecutive_sgs_failures, _last_sgs_failure
    verdict = classify_sgs_failure(exc)
    with _lock:
        _consecutive_sgs_failures += 1
        count = _consecutive_sgs_failures
        _last_sgs_failure = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "kind": verdict["kind"],
            "dead": verdict["dead"],
            "threshold": verdict["threshold"],
            "error": (str(exc) or "")[:400],
        }
    log.debug(
        "ip_recovery: SGS failure #%d (kind=%s threshold=%d) (exc=%s)",
        count, verdict["kind"], verdict["threshold"], exc,
    )

    if count < verdict["threshold"]:
        return

    # An auth-shaped failure is ambiguous between "unpaired receiver" and
    # "wrong host entirely".  Fingerprint the stored IP once so the log says
    # which it is, and so recovery is not launched against a receiver that is
    # simply waiting to be paired.
    if verdict["kind"] == "auth":
        ident = verify_stored_ip_identity()
        if ident.get("is_stb") is True:
            # Credentials problem: pair, do not hunt for a new IP.
            _maybe_trigger_autopair(
                str(_last_sgs_failure.get("kind") or "auth"),
                str(ident.get("ip") or ""),
            )
            return
        if ident.get("is_stb") is False:
            log.error(
                "ip_recovery: stored IP %s belongs to another host (%s) - "
                "treating as an IP change and starting recovery",
                ident.get("ip"), ident.get("reason"),
            )

    if is_sgs_dead_but_video_alive(exc):
        maybe_trigger_recovery()


def note_sgs_success() -> None:
    """Reset consecutive-failure counter and refresh the cached STB MAC."""
    global _consecutive_sgs_failures, _known_stb_mac
    with _lock:
        _consecutive_sgs_failures = 0
    # Opportunistically refresh the MAC while we know the IP is correct.
    # This means recovery always has a fresh MAC even if the ARP entry goes STALE.
    try:
        mac = _get_stb_mac()
        if mac:
            _known_stb_mac = mac
    except Exception:
        pass


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
        payload = {
            "active": _recovery_active,
            "last_result": dict(_last_result),
            "consecutive_sgs_failures": _consecutive_sgs_failures,
            "last_attempt_ago_s": round(time.time() - _last_attempt_ts, 1) if _last_attempt_ts else None,
            # v39 diagnostics
            "last_sgs_failure": dict(_last_sgs_failure),
            "known_stb_mac": _known_stb_mac,
            "autopair": dict(_autopair_last),
            "thresholds": {
                "transport": _SGS_FAIL_THRESHOLD,
                "auth": _SGS_FAIL_THRESHOLD_AUTH,
            },
        }
    payload["rf_ready"] = rf_ready()
    return payload


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
#  This section was an empty stub: the module documented an "RF4CE reliability"
#  strategy but contained no RF code at all, and `_sgs_press()` -- despite the
#  name being used for "fallback" navigation -- called `ctl.handle_auto_remote()`,
#  which dispatches on base.txt's protocol field and therefore went straight
#  back out over SGS.  When SGS was down there was literally no way to move the
#  on-screen cursor, so the OCR strategy could never work.
#
#  RF4CE is the right transport for recovery: it is a local serial link to the
#  Arduino/RF dongle and is completely independent of the STB's IP address.

def rf_ready() -> bool:
    """True when the RF4CE serial line for the configured alias is usable."""
    if _ctl is None or _CFG is None:
        return False
    alias = str(_CFG.get("stb_alias", "found1"))
    try:
        return bool(_ctl.rf_ready(alias))
    except AttributeError:
        # Older Controller without transport introspection
        try:
            from jamboree.serial_bridge import rf_available
            return bool(rf_available(alias))
        except Exception:
            return False
    except Exception:
        return False


def _rf_press(button: str, delay_ms: int, settle_s: float = KEY_SETTLE_S) -> bool:
    """Send one button over RF4CE only -- never over SGS.

    ``force="rf"`` makes the controller bypass its protocol dispatch, which is
    essential here: the whole point is to drive the box while SGS is broken.
    """
    if _ctl is None or _CFG is None:
        return False
    alias = str(_CFG.get("stb_alias", "found1"))
    # NB: CFG["remote"] is the transport hint "sgs", not an RF slot number.
    # The real slot lives in base.txt; force="rf" makes the controller read it.
    remote = str((_store.get(alias) or {}).get("remote") or "14") if _store else "14"
    try:
        _ctl.handle_auto_remote(remote, alias, button, int(delay_ms), force="rf")
        log.info("ip_recovery: RF press %-6s %4dms (remote=%s)", button, int(delay_ms), remote)
        time.sleep(settle_s)
        return True
    except TypeError:
        # Controller predates the force= kwarg -- try the explicit RF method.
        try:
            _ctl.rf_remote(alias, button, int(delay_ms))
            time.sleep(settle_s)
            return True
        except Exception as exc:
            log.warning("ip_recovery: RF press %s failed (legacy path): %s", button, exc)
            return False
    except Exception as exc:
        log.warning("ip_recovery: RF press %s failed: %s", button, exc)
        return False


def _rf_press_confirmed(
    button: str,
    delay_ms: int,
    expect_keywords: list,
    attempts: int = MAX_KEY_ATTEMPTS,
    settle_s: float = KEY_SETTLE_S,
) -> bool:
    """Press over RF and OCR-confirm the expected screen, retrying if it missed.

    RF4CE presses genuinely do get dropped, which is what the module docstring
    always promised to handle but never implemented.
    """
    for attempt in range(1, int(attempts) + 1):
        if not _rf_press(button, delay_ms, settle_s=settle_s):
            return False
        if not expect_keywords:
            return True
        if _confirm_screen(expect_keywords):
            if attempt > 1:
                log.info("ip_recovery: RF '%s' confirmed on attempt %d", button, attempt)
            return True
        log.debug(
            "ip_recovery: RF '%s' attempt %d/%d did not reach %s - retrying",
            button, attempt, attempts, expect_keywords[:3],
        )
    log.warning("ip_recovery: RF '%s' never confirmed after %d attempts", button, attempts)
    return False


# ─────────────────────────────────────────────────────────────────────────────
#  ARP-based IP discovery  (primary strategy — no screen navigation needed)
# ─────────────────────────────────────────────────────────────────────────────

ARP_PING_TIMEOUT_S: float  = 0.6   # per-host ping timeout
ARP_SCAN_WORKERS:   int    = 64    # parallel ping threads
ARP_SCAN_RETRIES:   int    = 2     # full scan passes before giving up


def _get_stb_mac() -> Optional[str]:
    """Return the STB's MAC address, using three escalating strategies:

    1. Look up the currently-stored IP in the live ARP table.
    2. Fall back to the module-level cached MAC (_known_stb_mac) that was saved
       during the last successful SGS call — survives IP changes.
    3. Scan the full ARP table for any entry matching known MAC prefixes
       (Hopper/EchoStar OUIs) as a last resort.
    """
    if _store is None or _CFG is None:
        return _known_stb_mac

    alias = str(_CFG.get("stb_alias", "found1"))
    try:
        stb = _store.get(alias) or {}
        old_ip = stb.get("ip", "")
        result = subprocess.run(
            ["ip", "neigh", "show"],
            capture_output=True, text=True, timeout=5
        )
        # Strategy 1: match by current stored IP.
        #
        # v39: this used to return the MAC unconditionally.  On 2026-08-03 the
        # STB's DHCP lease had been reassigned to a Jenkins server, so the
        # "STB MAC" we cached was that server's MAC.  Every later ARP sweep then
        # rediscovered the same wrong host and recovery could never converge.
        # We now refuse to adopt a MAC from an IP that positively identifies as
        # something other than a receiver.
        for line in result.stdout.splitlines():
            if old_ip and old_ip in line and "lladdr" in line:
                parts = line.split()
                idx = parts.index("lladdr")
                mac = parts[idx + 1].lower()
                ident = _probe_device_identity(old_ip)
                if ident.get("is_stb") is False:
                    log.error(
                        "ip_recovery: refusing to cache MAC %s from %s — that host "
                        "is not a receiver (%s, server=%r). base.txt is stale.",
                        mac, old_ip, ident.get("reason"), ident.get("server"),
                    )
                    break   # fall through to the cached / OUI strategies
                log.info(
                    "ip_recovery: STB MAC from ARP (ip=%s): %s (identity=%s)",
                    old_ip, mac, ident.get("is_stb"),
                )
                return mac

        # Strategy 2: return cached MAC from last healthy SGS call
        if _known_stb_mac:
            log.info("ip_recovery: using cached STB MAC: %s", _known_stb_mac)
            return _known_stb_mac

    except Exception as exc:
        log.warning("ip_recovery: _get_stb_mac error: %s", exc)
        if _known_stb_mac:
            return _known_stb_mac
    return _known_stb_mac


def _ping_host(ip: str, iface: Optional[str], timeout: float) -> None:
    """Fire a single ping to populate the ARP cache — result ignored."""
    try:
        cmd = ["ping", "-c1", f"-W{max(1, int(timeout))}"]
        if iface:
            cmd += ["-I", iface]
        cmd.append(ip)
        subprocess.run(cmd, capture_output=True, timeout=timeout + 1)
    except Exception:
        pass


def _arp_scan_for_mac(mac: str, subnet_cidr: str, iface: Optional[str] = None) -> Optional[str]:
    """Ping-sweep subnet, then search ARP table for the MAC.

    Returns the IP string if found, None otherwise.
    """
    import ipaddress, concurrent.futures
    mac = mac.lower()
    try:
        net = ipaddress.ip_network(subnet_cidr, strict=False)
    except ValueError as e:
        log.warning("ip_recovery: bad subnet_cidr %r: %s", subnet_cidr, e)
        return None

    hosts = list(net.hosts())
    log.info("ip_recovery: ARP sweep of %s (%d hosts, iface=%s)…", subnet_cidr, len(hosts), iface)

    with concurrent.futures.ThreadPoolExecutor(max_workers=ARP_SCAN_WORKERS) as pool:
        futures = [pool.submit(_ping_host, str(h), iface, ARP_PING_TIMEOUT_S) for h in hosts]
        concurrent.futures.wait(futures, timeout=ARP_PING_TIMEOUT_S * len(hosts) / ARP_SCAN_WORKERS + 5)

    # Read ARP table
    try:
        result = subprocess.run(
            ["ip", "neigh", "show"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if mac in line.lower() and "lladdr" in line:
                ip = line.split()[0]
                # Validate it's a real IP
                try:
                    socket.inet_aton(ip)
                    log.info("ip_recovery: ARP scan found MAC %s → IP %s", mac, ip)
                    return ip
                except OSError:
                    pass
    except Exception as exc:
        log.warning("ip_recovery: ARP table read error: %s", exc)
    return None


def _detect_subnet() -> tuple:
    """Return (subnet_cidr, iface) to ARP-sweep for the STB.

    Strategy (in order):
    1. Derive a /24 from the STB's last-known stored IP — almost always
       correct regardless of which NIC the host uses to reach it.
    2. Walk ``ip route`` for an explicit route matching that /24.
    3. Fall back to the first non-loopback, non-docker route on the host.
    """
    import ipaddress as _ipa

    # ── Strategy 1: subnet derived from the STB's stored IP ─────────────
    if _store is not None and _CFG is not None:
        try:
            alias     = str(_CFG.get("stb_alias", "found1"))
            stb       = _store.get(alias) or {}
            stored_ip = stb.get("ip", "")
            if stored_ip:
                net         = _ipa.ip_network(stored_ip + "/24", strict=False)
                subnet_cidr = str(net)
                prefix      = stored_ip.rsplit(".", 1)[0]   # e.g. "10.73.185"
                iface       = None
                try:
                    result = subprocess.run(
                        ["ip", "route", "show"],
                        capture_output=True, text=True, timeout=5,
                    )
                    for line in result.stdout.splitlines():
                        if prefix in line and "dev" in line:
                            parts   = line.split()
                            dev_idx = parts.index("dev")
                            iface   = parts[dev_idx + 1]
                            break
                except Exception:
                    pass
                log.info(
                    "ip_recovery: subnet derived from stored STB IP %s -> %s (iface=%s)",
                    stored_ip, subnet_cidr, iface,
                )
                return subnet_cidr, iface
        except Exception as exc:
            log.warning("ip_recovery: subnet-from-stored-IP failed: %s", exc)

    # ── Strategy 2/3: fall back to host route table ──────────────────────
    try:
        result = subprocess.run(
            ["ip", "route", "show"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            # Skip default, loopback, docker/bridge nets
            if "default" in line or "127." in line:
                continue
            if any(d in line for d in ["docker", "br-", "virbr", "veth"]):
                continue
            parts = line.split()
            if len(parts) >= 3 and "dev" in parts:
                subnet  = parts[0]
                dev_idx = parts.index("dev")
                iface   = parts[dev_idx + 1]
                if any(p in iface for p in ["wlp", "wlan", "eth", "enp", "ens"]):
                    log.debug(
                        "ip_recovery: detected subnet %s via %s (host-route fallback)",
                        subnet, iface,
                    )
                    return subnet, iface
    except Exception as exc:
        log.warning("ip_recovery: _detect_subnet error: %s", exc)
    return "10.0.0.0/8", None


def _find_stb_ip_by_arp() -> Optional[str]:
    """Top-level ARP discovery: get MAC, detect subnet, sweep, return new IP.

    v39 changes:
      * a candidate IP is fingerprinted before being accepted, so the sweep can
        no longer "find" a CI server that happens to hold the old lease;
      * the currently stored IP is rejected outright when it identifies as a
        non-receiver, otherwise a poisoned MAC cache makes the sweep converge
        straight back onto the wrong host.
    """
    mac = _get_stb_mac()
    if not mac:
        log.warning("ip_recovery: MAC not in ARP cache — doing cold sweep")
        # Still try; sweep will populate ARP from scratch

    stored_ip = ""
    if _store is not None and _CFG is not None:
        stored_ip = ((_store.get(str(_CFG.get("stb_alias", "found1"))) or {}).get("ip") or "")

    subnet, iface = _detect_subnet()

    for attempt in range(1, ARP_SCAN_RETRIES + 1):
        log.info("ip_recovery: ARP scan attempt %d/%d", attempt, ARP_SCAN_RETRIES)
        new_ip = _arp_scan_for_mac(mac, subnet, iface) if mac else None
        if new_ip:
            if new_ip == stored_ip:
                ident = _probe_device_identity(new_ip)
                if ident.get("is_stb") is False:
                    log.error(
                        "ip_recovery: ARP sweep converged back onto %s, which is not "
                        "a receiver (%s) — the cached MAC is poisoned, discarding it",
                        new_ip, ident.get("reason"),
                    )
                    global _known_stb_mac
                    _known_stb_mac = None
                    mac = None
                    if attempt < ARP_SCAN_RETRIES:
                        time.sleep(2.0)
                    continue
            ident = _probe_device_identity(new_ip)
            if ident.get("is_stb") is False:
                log.warning(
                    "ip_recovery: ARP candidate %s rejected — not a receiver (%s)",
                    new_ip, ident.get("reason"),
                )
            else:
                log.info(
                    "ip_recovery: ARP candidate %s accepted (identity=%s, %s)",
                    new_ip, ident.get("is_stb"), ident.get("reason"),
                )
                return new_ip

        if attempt < ARP_SCAN_RETRIES:
            time.sleep(2.0)

    return None


def find_stb_ip_by_sgs_probe(max_hosts: int = 512) -> Optional[str]:
    """Locate the receiver by probing the SGS port across the local subnet.

    Complements the ARP strategy: it needs no prior knowledge of the STB's MAC,
    which matters when the cache has been poisoned or the box has never been
    seen.  Only hosts that answer with an SGS result envelope (or the
    receiver's digest challenge) are accepted.
    """
    import concurrent.futures
    import ipaddress as _ipa

    subnet, iface = _detect_subnet()
    candidates: list = []
    try:
        net = _ipa.ip_network(subnet, strict=False)
        candidates = [str(h) for h in net.hosts()][:int(max_hosts)]
    except Exception as exc:
        log.warning("ip_recovery: SGS probe sweep - bad subnet %r: %s", subnet, exc)
        return None

    log.info(
        "ip_recovery: SGS identity sweep of %s (%d hosts, iface=%s)…",
        subnet, len(candidates), iface,
    )
    found: list = []

    def _check(ip: str) -> None:
        if _probe_device_identity(ip, timeout=1.5).get("is_stb") is True:
            found.append(ip)

    with concurrent.futures.ThreadPoolExecutor(max_workers=ARP_SCAN_WORKERS) as pool:
        list(pool.map(_check, candidates))

    if not found:
        log.warning("ip_recovery: SGS identity sweep found no receiver on %s", subnet)
        return None
    if len(found) > 1:
        log.warning(
            "ip_recovery: SGS identity sweep found %d receivers %s — using the first",
            len(found), found[:5],
        )
    log.info("ip_recovery: SGS identity sweep located receiver at %s", found[0])
    return found[0]


# ─────────────────────────────────────────────────────────────────────────────
#  SGS-based OCR fallback  (secondary strategy — uses screen navigation)
# ─────────────────────────────────────────────────────────────────────────────

def _sgs_press(button: str, delay_ms: int, ip_override: Optional[str] = None,
               settle_s: float = 2.5) -> bool:
    """Send one SGS key; optionally override the IP stored in base.txt.

    Used during OCR fallback when we have a candidate IP to test.
    """
    if _ctl is None or _CFG is None or _store is None:
        return False
    alias  = str(_CFG.get("stb_alias", "found1"))
    remote = str(_CFG.get("remote", "14"))
    delay  = int(_CFG.get("default_delay_ms", 120))

    # Temporarily patch the in-memory store IP if we have a candidate
    if ip_override:
        orig = _store.get(alias).get("ip")
        all_stbs = dict(_store.all())
        all_stbs[alias] = dict(all_stbs[alias])
        all_stbs[alias]["ip"] = ip_override
        _store.save({"stbs": all_stbs}); _store.reload()

    try:
        # force="sgs": the controller would otherwise silently fall back to RF,
        # which here would be a lie -- this helper exists to test whether an SGS
        # candidate IP actually works.
        try:
            _ctl.handle_auto_remote(remote, alias, button, delay_ms, force="sgs")
        except TypeError:
            _ctl.handle_auto_remote(remote, alias, button, delay_ms)
        time.sleep(settle_s)
        return True
    except Exception as exc:
        log.warning("ip_recovery: SGS press %s failed: %s", button, exc)
        return False
    finally:
        # Restore original IP to avoid side effects
        if ip_override:
            all_stbs = dict(_store.all())
            all_stbs[alias] = dict(all_stbs[alias])
            all_stbs[alias]["ip"] = orig
            _store.save({"stbs": all_stbs}); _store.reload()


def _backup_http_press(
    command: str,
    duration_ms: int = BACKUP_HTTP_DEFAULT_MS,
    settle_s: float = 2.5,
) -> bool:
    """Send a key via the backup HTTP controller — does NOT need the STB IP.

    URL: BACKUP_HTTP_BASE/{command}/{duration_ms}
    Normal press : http://10.79.85.47:5003/auto/14/Jim's%20STB/<cmd>/80
    Sys-Info hold: http://10.79.85.47:5003/auto/14/Jim's%20STB/home/3000
    """
    import urllib.request
    import urllib.parse
    url = f"{BACKUP_HTTP_BASE}/{urllib.parse.quote(str(command))}/{duration_ms}"
    try:
        log.info("ip_recovery: backup-HTTP %-6s %4dms -> %s", command, duration_ms, url)
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=BACKUP_HTTP_TIMEOUT_S) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            log.debug(
                "ip_recovery: backup-HTTP response [%d]: %s",
                resp.status, body[:200].strip(),
            )
        time.sleep(settle_s)
        return True
    except Exception as exc:
        log.warning("ip_recovery: backup-HTTP press '%s' failed: %s", command, exc)
        return False


def _navigate_to_network_screen(ip_override: Optional[str] = None) -> bool:
    """Navigate to the Network Settings screen to OCR the new STB IP.

    Tries the backup HTTP controller first — this path is fully independent
    of the STB's IP address and therefore works even when SGS is fully down.
    Falls back to SGS only if the backup controller itself is unreachable.

    Backup URL mapping:
        home / 3000  ->  long-hold Home  (sys-info / Network overlay)
        2    / 80    ->  digit 2          (Network tab on Hopper)
    """
    log.info("ip_recovery: OCR fallback — navigating to network screen")

    _MENU_KW = ["settings", "network", "diagnostics", "system", "info"]
    _NET_KW  = ["network", "ip address", "ip:", "ethernet", "wifi", "internet"]

    # ── Primary path: RF4CE over the local serial line (v39) ─────────────
    # RF is preferred over everything else because it needs neither the STB's
    # IP nor any other host on the network.  This is the path that was missing:
    # previously "fallback" navigation still went out over SGS, so a dead SGS
    # link meant no navigation at all.
    if rf_ready():
        log.info("ip_recovery: trying RF4CE navigation (local serial, ip-independent)")
        if _rf_press_confirmed("home", HOME_HOLD_MS, _MENU_KW):
            if _rf_press_confirmed("2", DIGIT_PRESS_MS, _NET_KW):
                log.info("ip_recovery: network screen reached via RF4CE OK")
                return True
            log.warning("ip_recovery: RF4CE reached the menu but not the network screen")
        else:
            log.warning("ip_recovery: RF4CE HOME hold did not reach the system menu")
    else:
        log.warning(
            "ip_recovery: RF4CE not available (no serial worker for alias %s) — "
            "skipping the preferred navigation path",
            str((_CFG or {}).get("stb_alias", "found1")),
        )

    # ── Secondary path: backup HTTP controller (IP-independent) ──────────
    log.info("ip_recovery: trying backup-HTTP navigation (ip-independent)")
    home_ok = _backup_http_press("home", HOME_HOLD_MS, settle_s=2.5)
    if home_ok:
        if not _confirm_screen(_MENU_KW):
            log.warning("ip_recovery: HOME overlay not confirmed via backup-HTTP, continuing anyway")
        digit_ok = _backup_http_press("2", DIGIT_PRESS_MS, settle_s=2.5)
        if digit_ok:
            if _confirm_screen(_NET_KW, settle_extra_s=0.5):
                log.info("ip_recovery: network screen reached via backup-HTTP OK")
                return True
            log.warning("ip_recovery: backup-HTTP sent but network screen not confirmed by OCR")

    # ── Last resort: SGS (requires a working IP, so usually pointless here) ──
    log.warning(
        "ip_recovery: RF and backup-HTTP both failed — last-resort SGS (ip=%s)",
        ip_override or "stored",
    )
    if not _sgs_press("home", HOME_HOLD_MS, ip_override=ip_override, settle_s=2.5):
        return False
    if not _confirm_screen(["settings", "network", "diagnostics", "system", "info"]):
        log.warning("ip_recovery: HOME overlay not confirmed via SGS, continuing anyway")
    if not _sgs_press("2", DIGIT_PRESS_MS, ip_override=ip_override, settle_s=2.5):
        return False
    return _confirm_screen(
        ["network", "ip address", "ip:", "ethernet", "wifi", "internet"],
        settle_extra_s=0.5,
    )


def _confirm_screen(expected_keywords: list, settle_extra_s: float = 0.5) -> bool:
    """Grab a frame and confirm the screen matches expected keywords."""
    time.sleep(settle_extra_s)
    if _get_frame is None:
        return False
    frame = _get_frame()
    if frame is None:
        return False
    return _screen_contains(frame, expected_keywords)


def _read_ip_from_screen() -> Optional[str]:
    """OCR the current frame and extract the STB IP address.

    Tries several crop regions — centre band first (where IP label lives on
    Hopper Network screen), then full-frame sparse OCR as fallback.
    """
    if _get_frame is None:
        return None
    frame = _get_frame()
    if frame is None:
        return None
    for box, psm in [
        ((0.08, 0.20, 0.92, 0.85), 6),
        ((0.08, 0.30, 0.70, 0.75), 6),
        ((0.0,  0.0,  1.0,  0.5),  6),
        ((0.0,  0.0,  1.0,  1.0),  11),
    ]:
        text = _ocr_region(frame, box, psm=psm)
        ip   = _extract_ip(text)
        if ip:
            log.info("ip_recovery: OCR found IP %s (box=%s psm=%d)", ip, box, psm)
            return ip
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _update_base_txt(new_ip: str, **extra_fields: Any) -> bool:
    """Write the new IP to base.txt and hot-reload the store.

    v39: uses ``store.update_stb()``, which updates/adds individual fields
    atomically.  The previous implementation rebuilt the whole document and
    called ``store.save({"stbs": ...})``, which replaced base.txt wholesale and
    dropped every top-level key -- including anything the pairing flow had
    written outside the STB entry.
    """
    if _store is None or _CFG is None:
        return False
    alias = str(_CFG.get("stb_alias", "found1"))
    fields: Dict[str, Any] = {"ip": new_ip}
    fields.update(extra_fields)
    try:
        if hasattr(_store, "update_stb"):
            _store.update_stb(alias, fields)
        else:                                   # legacy store -- merge by hand
            all_stbs = dict(_store.all())
            entry = dict(all_stbs.get(alias, {}))
            entry.update(fields)
            all_stbs[alias] = entry
            _store.save({"stbs": all_stbs})
        _store.reload()
        log.info(
            "ip_recovery: base.txt updated — %s %s (credentials and other fields preserved)",
            alias, ", ".join(f"{k}={v}" for k, v in fields.items()),
        )
        return True
    except Exception as exc:
        log.error("ip_recovery: base.txt update failed: %s", exc)
        return False


def _verify_sgs_with_new_ip() -> bool:
    """Send a benign SGS key to confirm the new IP is reachable."""
    if _ctl is None or _CFG is None:
        return False
    alias  = str(_CFG.get("stb_alias", "found1"))
    remote = str(_CFG.get("remote", "14"))
    delay  = int(_CFG.get("default_delay_ms", 120))
    try:
        # force="sgs" is critical: with the v39 RF fallback in place, a plain
        # call would succeed over RF even though SGS is still broken, and
        # recovery would declare victory with a wrong IP in base.txt.
        try:
            _ctl.handle_auto_remote(remote, alias, "info", delay, force="sgs")
        except TypeError:
            _ctl.handle_auto_remote(remote, alias, "info", delay)
        log.info("ip_recovery: SGS verify OK")
        return True
    except Exception as exc:
        log.warning("ip_recovery: SGS verify failed: %s", exc)
        return False


def _escape_to_live_tv(ip_override: Optional[str] = None) -> None:
    """Best-effort navigation back to live TV after recovery.

    Tries backup HTTP first (IP-independent), then falls back to SGS.
    Multiple presses because the STB may be several menus deep.
    """
    use_rf = rf_ready()
    for btn, ms in [("back", 120), ("back", 120), ("home", 120), ("live", 120)]:
        if use_rf and _rf_press(btn, ms, settle_s=1.2):
            continue
        if _backup_http_press(btn, ms, settle_s=1.2):
            continue
        _sgs_press(btn, ms, ip_override=ip_override, settle_s=1.2)


# ─────────────────────────────────────────────────────────────────────────────
#  Recovery worker
# ─────────────────────────────────────────────────────────────────────────────

def _recovery_worker() -> None:
    """Background thread: detect new IP via ARP scan, update base.txt, verify."""
    global _recovery_active, _last_result, _consecutive_sgs_failures

    result: Dict[str, Any] = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "success": False,
        "strategy": None,
        "new_ip": None,
        "cycles": 0,
        "detail": "",
    }

    try:
        for cycle in range(1, MAX_RECOVERY_CYCLES + 1):
            result["cycles"] = cycle
            log.info("ip_recovery: === CYCLE %d / %d ===", cycle, MAX_RECOVERY_CYCLES)

            # ── Strategy 1: ARP MAC scan (no SGS needed) ────────────────────
            log.info("ip_recovery: Strategy 1 — ARP MAC scan")
            new_ip = _find_stb_ip_by_arp()

            if new_ip:
                result["strategy"] = "arp_scan"
                log.info("ip_recovery: ARP scan found new IP: %s", new_ip)
            else:
                # ── Strategy 1b: SGS identity sweep (v39) ───────────────────
                # No MAC needed, and immune to a poisoned MAC cache.
                log.info("ip_recovery: Strategy 1b — SGS identity sweep")
                new_ip = find_stb_ip_by_sgs_probe()
                if new_ip:
                    result["strategy"] = "sgs_identity_sweep"
                    log.info("ip_recovery: identity sweep found receiver at %s", new_ip)

            if not new_ip:
                # ── Strategy 2: OCR via SGS navigation ──────────────────────
                log.info("ip_recovery: Strategy 2 — SGS screen navigation + OCR")
                # We need a working IP candidate for SGS. Try a broad ARP sweep
                # to find any recently-seen candidate IPs and try each.
                log.warning("ip_recovery: ARP scan yielded no result; falling back to OCR")
                if not _navigate_to_network_screen():
                    result["detail"] = "cycle %d: failed to reach network screen via SGS" % cycle
                    log.warning("ip_recovery: %s", result["detail"])
                    time.sleep(3.0)
                    continue

                for _read_attempt in range(1, 4):
                    new_ip = _read_ip_from_screen()
                    if new_ip:
                        break
                    log.debug("ip_recovery: OCR attempt %d yielded no IP", _read_attempt)
                    time.sleep(1.5)

                if not new_ip:
                    result["detail"] = "cycle %d: OCR could not extract IP" % cycle
                    log.warning("ip_recovery: %s", result["detail"])
                    continue
                result["strategy"] = "ocr_screen"

            # ── Update base.txt ──────────────────────────────────────────────
            if not _update_base_txt(new_ip):
                result["detail"] = "cycle %d: base.txt update failed for %s" % (cycle, new_ip)
                log.error("ip_recovery: %s", result["detail"])
                break

            # ── Escape back to live TV (best-effort) ─────────────────────────
            _escape_to_live_tv()
            time.sleep(2.0)

            # ── Verify SGS with new IP ───────────────────────────────────────
            if _verify_sgs_with_new_ip():
                result["success"] = True
                result["new_ip"]  = new_ip
                result["detail"]  = "recovered via %s — new IP %s" % (result["strategy"], new_ip)
                with _lock:
                    _consecutive_sgs_failures = 0
                log.info("ip_recovery: RECOVERY COMPLETE — STB IP is now %s", new_ip)
                break
            else:
                result["detail"] = "cycle %d: IP %s found but SGS verify failed" % (cycle, new_ip)
                log.warning("ip_recovery: %s", result["detail"])
                # Revert IP in store so we can retry cleanly
                _update_base_txt(_store.get(str(_CFG.get("stb_alias","found1"))).get("ip",""))
                time.sleep(5.0)

    except Exception as exc:
        log.exception("ip_recovery: unhandled exception in worker: %s", exc)
        result["detail"] = "exception: %s" % exc
    finally:
        _last_result = result
        _recovery_active = False
        log.info("ip_recovery: worker exiting — result: %s", result)
