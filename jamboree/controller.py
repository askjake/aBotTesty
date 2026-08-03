# --- jamboree/controller.py ---
"""Orchestrates RF, SGS and DART logic for Flask routes.

v39 SGS -> RF fallback (2026-08-03)
-----------------------------------
``handle_auto_remote`` used to dispatch on ``stb["protocol"]`` and, for an SGS
box, return ``self.sgs_remote(...)`` unconditionally.  When SGS broke -- stale
IP, unpaired box, 403 from the HTTP layer -- the exception propagated all the
way out to Flask and to the autonomous crawler, which died on it.  The RF4CE
line was sitting there working the whole time and was never tried.

Now every SGS press is wrapped: on failure, if the STB has a usable RF serial
line, the same button is re-sent over RF and the result records
``via="rf_fallback"`` plus the original SGS error.  Callers can force either
transport with ``force="sgs"`` / ``force="rf"``, which is what the IP-recovery
module needs when it has to drive the on-screen menus while SGS is dead.
"""

import logging, time
from datetime import datetime, timezone
from typing import Dict, Optional

from .serial_bridge import send_rf, send_rf_strict, send_quick_dart, rf_available
from .sgs_bridge import send_sgs
from .stb_store import store

log = logging.getLogger("jamboree.controller")

RESET_DEFAULT_MS = 500


class Controller:
    def __init__(self):
        logging.info("Controller initialised - %d STBs", len(store.all()))

    # ------------------------------ helpers (centralize special commands)
    def _stb_or_raise(self, stb_name: str) -> Dict:
        stb = store.get(stb_name)
        if not stb:
            raise ValueError(f"STB '{stb_name}' not found in base.txt")
        return stb

    def _per_remote_reset(self, stb_name: str) -> Dict:
        """Issue a per-remote reset through the DART line so Arduino handles it uniformly."""
        stb = self._stb_or_raise(stb_name)
        remote = stb["remote"]
        # Format B: "<remote> 99 reset" -> Arduino does per-remote reset
        sent = send_rf(stb_name, remote, "reset", "80")
        return {"reset_line": sent, "ts": datetime.now(timezone.utc).isoformat()}

    def _all_up(self, stb_name: str) -> Dict:
        """Release all pressed buttons on this remote."""
        stb = self._stb_or_raise(stb_name)
        remote = stb["remote"]
        sent = send_quick_dart(stb_name, remote, "allup", "allup")
        return {"allup_line": sent, "ts": datetime.now(timezone.utc).isoformat()}

    # ------------------------------ transport capability
    def rf_ready(self, stb_name: str) -> bool:
        """True when this STB can be driven over the RF4CE / DART serial line."""
        stb = store.get(stb_name) or {}
        if not stb.get("remote"):
            return False
        return rf_available(stb_name) or rf_available(str(stb.get("com_port") or ""))

    def transports(self, stb_name: str) -> Dict:
        """Report which transports are usable for this alias (for /api/status)."""
        stb = store.get(stb_name) or {}
        return {
            "alias": stb_name,
            "protocol": str(stb.get("protocol", "")).upper() or None,
            "sgs_configured": bool(stb.get("ip")) and bool(stb.get("stb")),
            "sgs_paired": bool(stb.get("lname")) and bool(stb.get("passwd")),
            "rf_ready": self.rf_ready(stb_name),
            "remote": stb.get("remote"),
            "com_port": stb.get("com_port"),
        }

    # ------------------------------ RF
    def rf_remote(self, stb_name: str, button_id: str, delay: int) -> Dict:
        """Explicit RF4CE press -- never touches SGS.

        This is the transport the IP-recovery worker uses to walk the on-screen
        menus, because it is completely independent of the STB's IP address.
        """
        stb = self._stb_or_raise(stb_name)
        remote = str(stb["remote"])
        ack = send_rf_strict(stb_name, remote, button_id, delay)
        return {
            "rf_line": ack,
            "via": "rf",
            "ts": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------ RF / AUTO
    def handle_auto_remote(
        self,
        remote: str,
        stb_name: str,
        button_id: str,
        delay: int,
        *,
        allow_rf_fallback: bool = True,
        force: Optional[str] = None,
    ) -> Dict:
        """Send one button, choosing the transport and falling back when needed.

        ``force`` may be ``"sgs"`` or ``"rf"`` to pin the transport.  Otherwise
        the STB's ``protocol`` field decides, and an SGS failure degrades to RF
        when the serial line is available.
        """
        stb = self._stb_or_raise(stb_name)

        # Normalize specials for both protocol families
        bid = (button_id or "").lower()
        if bid in ("reset", "rst"):
            return self._per_remote_reset(stb_name)
        if bid in ("allup", "all_up", "release"):
            return self._all_up(stb_name)

        want = (force or "").lower() or None
        if want == "rf":
            return self.rf_remote(stb_name, button_id, delay)

        use_sgs = want == "sgs" or (want is None and str(stb.get("protocol", "")).upper() == "SGS")

        if use_sgs:
            try:
                result = self.sgs_remote(stb_name, stb["ip"], stb["stb"], button_id, delay)
                result["via"] = "sgs"
                return result
            except Exception as sgs_exc:
                if want == "sgs" or not allow_rf_fallback:
                    raise
                if not self.rf_ready(stb_name):
                    log.error(
                        "SGS press '%s' on %s failed and no RF serial line is available "
                        "(remote=%s com_port=%s) - giving up: %s",
                        button_id, stb_name, stb.get("remote"), stb.get("com_port"),
                        str(sgs_exc).splitlines()[0] if str(sgs_exc) else sgs_exc,
                    )
                    raise
                log.warning(
                    "SGS press '%s' on %s failed - falling back to RF remote %s: %s",
                    button_id, stb_name, stb.get("remote"),
                    str(sgs_exc).splitlines()[0] if str(sgs_exc) else sgs_exc,
                )
                try:
                    result = self.rf_remote(stb_name, button_id, delay)
                except Exception as rf_exc:
                    # Both transports are down: surface the SGS error (the more
                    # actionable one) but say plainly that RF was tried too.
                    raise RuntimeError(
                        f"SGS failed and RF fallback also failed "
                        f"(rf_error={rf_exc}); sgs_error={sgs_exc}"
                    ) from sgs_exc
                result["via"] = "rf_fallback"
                result["sgs_error"] = str(sgs_exc)
                return result

        # default RF via serial_mgr using the STB alias.
        #
        # `remote` comes from the caller and in merged_app it is CFG["remote"],
        # which is the string "sgs" -- a transport hint, not an RF slot number.
        # Feeding that to the Arduino would emit the line "sgs <cmd> <rel> <ms>",
        # which the sketch cannot parse.  base.txt's per-STB `remote` field is
        # the authoritative slot number, so prefer it whenever the argument is
        # not numeric.
        slot = str(remote)
        if not slot.isdigit():
            slot = str(stb.get("remote") or slot)
            if slot != str(remote):
                log.debug(
                    "handle_auto_remote: remote=%r is not an RF slot; using base.txt remote=%r",
                    remote, slot,
                )
        ack = send_rf(stb_name, slot, button_id, delay)
        return {"rf_line": ack, "via": "rf", "ts": datetime.now(timezone.utc).isoformat()}

    # ------------------------------ SGS
    def sgs_remote(self, stb_name: str, stb_ip: str, rxid: str, button_id: str, delay: int):
        resp = send_sgs(stb_name, stb_ip, rxid, button_id, delay)
        return {"stdout": resp, "ts": datetime.now(timezone.utc).isoformat()}

    # ------------------------------ DART
    def dart(self, stb_name: str, button_id: str, action: str):
        """
        Accepts:
          action in {"down","up"} -> pass through
          action == "reset"       -> per-remote reset (ignores button_id)
          action == "allup"       -> release all (ignores button_id)
          action is numeric ms    -> Format A-style instantaneous DOWN+UP (legacy)
        """
        stb = self._stb_or_raise(stb_name)
        remote = stb["remote"]

        act = (action or "").lower()

        if act == "reset":
            sent = send_rf(stb_name, remote, "reset", "80")
            return {"dart_line": sent, "ts": datetime.now(timezone.utc).isoformat()}

        if act in ("allup", "all_up", "release"):
            sent = send_quick_dart(stb_name, remote, "allup", "allup")
            return {"dart_line": sent, "ts": datetime.now(timezone.utc).isoformat()}

        if act in ("down", "up"):
            sent = send_quick_dart(stb_name, remote, button_id, act)
            return {"dart_line": sent, "ts": datetime.now(timezone.utc).isoformat()}

        # Fallback: if action is a number, treat as a timed press
        try:
            ms = int(act)
            sent = send_rf(stb_name, remote, button_id, ms)
            return {"dart_line": sent, "ts": datetime.now(timezone.utc).isoformat()}
        except ValueError:
            raise ValueError(f"Unsupported DART action '{action}'. Use down|up|reset|allup|<ms>.")

    # ------------------------------ UNPAIR
    def unpair(self, stb_name: str):
        """SAT 3s (hold), then DVR+Guide 3s (hold), then release both."""
        stb = self._stb_or_raise(stb_name)
        remote = stb["remote"]

        # 1 - SAT hold 3 s
        self.dart(stb_name, "sat", "down")
        time.sleep(3.10)
        self.dart(stb_name, "sat", "up")

        # 2 - DVR & Guide down together via DART
        time.sleep(0.20)
        self.dart(stb_name, "dvr", "down")
        time.sleep(0.1)
        self.dart(stb_name, "guide", "down")

        time.sleep(3.50)

        # 3 - release both
        self.dart(stb_name, "dvr", "up")
        time.sleep(0.1)
        self.dart(stb_name, "guide", "up")

        return {"unpaired": stb_name, "ts": datetime.now(timezone.utc).isoformat()}
