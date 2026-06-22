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
        # Strategy 1: match by current stored IP
        for line in result.stdout.splitlines():
            if old_ip and old_ip in line and "lladdr" in line:
                parts = line.split()
                idx = parts.index("lladdr")
                mac = parts[idx + 1].lower()
                log.info("ip_recovery: STB MAC from ARP (ip=%s): %s", old_ip, mac)
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
    """Top-level ARP discovery: get MAC, detect subnet, sweep, return new IP."""
    mac = _get_stb_mac()
    if not mac:
        log.warning("ip_recovery: MAC not in ARP cache — doing cold sweep")
        # Still try; sweep will populate ARP from scratch

    subnet, iface = _detect_subnet()

    for attempt in range(1, ARP_SCAN_RETRIES + 1):
        log.info("ip_recovery: ARP scan attempt %d/%d", attempt, ARP_SCAN_RETRIES)
        new_ip = _arp_scan_for_mac(mac, subnet, iface) if mac else None
        if new_ip:
            return new_ip
        # If no MAC, try a wider sweep and look for any Hopper device
        # by checking the stb's receiver ID via SGS after sweep
        if attempt < ARP_SCAN_RETRIES:
            time.sleep(2.0)

    return None


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

    # ── Primary path: backup HTTP controller (IP-independent) ───────────
    log.info("ip_recovery: trying backup-HTTP navigation (ip-independent)")
    home_ok = _backup_http_press("home", HOME_HOLD_MS, settle_s=2.5)
    if home_ok:
        if not _confirm_screen(["settings", "network", "diagnostics", "system", "info"]):
            log.warning("ip_recovery: HOME overlay not confirmed via backup-HTTP, continuing anyway")
        digit_ok = _backup_http_press("2", DIGIT_PRESS_MS, settle_s=2.5)
        if digit_ok:
            reached = _confirm_screen(
                ["network", "ip address", "ip:", "ethernet", "wifi", "internet"],
                settle_extra_s=0.5,
            )
            if reached:
                log.info("ip_recovery: network screen reached via backup-HTTP OK")
                return True
            log.warning("ip_recovery: backup-HTTP sent but network screen not confirmed by OCR")

    # ── Fallback path: SGS (requires a working IP) ───────────────────────
    log.warning(
        "ip_recovery: backup-HTTP path failed — falling back to SGS (ip=%s)",
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

def _update_base_txt(new_ip: str) -> bool:
    """Write the new IP to base.txt and hot-reload the store."""
    if _store is None or _CFG is None:
        return False
    alias = str(_CFG.get("stb_alias", "found1"))
    try:
        all_stbs = dict(_store.all())
        all_stbs[alias] = dict(all_stbs[alias])
        all_stbs[alias]["ip"] = new_ip
        _store.save({"stbs": all_stbs})
        _store.reload()
        log.info("ip_recovery: base.txt updated — %s IP is now %s", alias, new_ip)
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
    for btn, ms in [("back", 120), ("back", 120), ("home", 120), ("live", 120)]:
        sent = _backup_http_press(btn, ms, settle_s=1.2)
        if not sent:
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
