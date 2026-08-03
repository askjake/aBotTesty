# jamboree/serial_bridge.py
"""Serial helpers routed through the global serial_mgr (no direct pyserial)."""
import logging, time
from .commands import get_button_codes, get_button_number
from .serial_hub import serial_mgr  # <- import from neutral hub, not app


def _enqueue(alias_or_com: str, line: str) -> bool:
    ok = serial_mgr.write(alias_or_com, line.encode())
    if not ok:
        logging.warning("serial write enqueue failed for %s (%r)", alias_or_com, line.strip())
    return ok


def rf_available(alias_or_com: str) -> bool:
    """True when the RF/DART serial line for this alias has a live worker.

    The controller consults this before falling back from SGS to RF so that a
    fallback which cannot possibly work is reported as a failure rather than
    silently swallowed.
    """
    try:
        return bool(serial_mgr.has_port(alias_or_com))
    except Exception:
        return False


def send_rf(alias_or_com: str, remote_num: str, button_id: str, delay_ms: int) -> str:
    delay_ms = max(int(delay_ms), 80)
    codes = get_button_codes(button_id)
    if not codes:
        raise ValueError(f"Unknown button_id '{button_id}'")
    line = f"{remote_num} {codes['KEY_CMD']} {codes['KEY_RELEASE']} {delay_ms}\n"
    _enqueue(alias_or_com, line)
    time.sleep((delay_ms + 50) / 1000.0)
    logging.debug("-> [%s] %s", alias_or_com, line.strip())
    return line.strip()


def send_rf_strict(alias_or_com: str, remote_num: str, button_id: str, delay_ms: int) -> str:
    """Like :func:`send_rf` but raises when the byte stream could not be queued.

    ``send_rf`` only logs a warning on enqueue failure and still returns the
    line, which makes a dead Arduino look like a successful press.  The SGS->RF
    fallback path needs to know the difference, otherwise a broken serial line
    would mask a broken SGS link and the caller would think the key landed.
    """
    delay_ms = max(int(delay_ms), 80)
    codes = get_button_codes(button_id)
    if not codes:
        raise ValueError(f"Unknown button_id '{button_id}'")
    if not rf_available(alias_or_com):
        raise RuntimeError(f"no RF serial worker registered for '{alias_or_com}'")
    line = f"{remote_num} {codes['KEY_CMD']} {codes['KEY_RELEASE']} {delay_ms}\n"
    if not _enqueue(alias_or_com, line):
        raise RuntimeError(f"RF write to '{alias_or_com}' could not be queued")
    time.sleep((delay_ms + 50) / 1000.0)
    logging.debug("-> [%s] %s (strict)", alias_or_com, line.strip())
    return line.strip()


def send_quick_dart(alias_or_com: str, remote_num: str, button_id: str, action: str) -> str:
    num = get_button_number(button_id)
    if not num:
        raise ValueError(f"Unknown button_id '{button_id}'")
    line = f"{remote_num} {num} {action}\n"
    _enqueue(alias_or_com, line)
    logging.debug("-> [%s] %s", alias_or_com, line.strip())
    return line.strip()
