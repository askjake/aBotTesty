"""Tests for the v39 SGS failure classifier + device identity probe.

The classifier tests are offline.  The identity tests hit the real hosts on the
bench, so they are marked LIVE and skipped cleanly when unreachable.

Run:  .venv/bin/python tests/test_ip_recovery_classify.py
"""
import sys, os, json, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("JAMBOREE_BASE", str(ROOT / "base.txt"))

FAILS = []
def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"   {detail}" if detail else ""))
    if not cond:
        FAILS.append(name)

import ip_recovery as R

# The exact exception text from the 2026-08-03 production log.
REAL_403 = '''{"command": "remote_key", "receiver": "XAFa8a15990d1ba", "stb": "R1956409151-66", "tv_id": 0, "key_name": "Home"}
remote_key failed -> {
  "result": -13,
  "error": "auth_required_or_opt_in_disabled",
  "http_status": 403,
  "url": "http://10.73.185.34:8080/www/sgs",
  "text": "<html>Error 403 No valid crumb was included in the request</html>"
}'''

print("T1  the exact production 403 is now classified as SGS-dead")
v = R.classify_sgs_failure(RuntimeError(REAL_403))
check("T1.1 dead=True (was False before the fix)", v["dead"] is True, str(v))
check("T1.2 kind=auth", v["kind"] == "auth", str(v))
check("T1.3 auth threshold is lower than transport",
      v["threshold"] == R._SGS_FAIL_THRESHOLD_AUTH < R._SGS_FAIL_THRESHOLD, str(v))

print("T2  transport errors still classified correctly")
for msg, kind in [
    ("Command returned non-zero returncode 1", "transport"),
    ("[Errno 111] Connection refused", "transport"),
    ("HTTPConnectionPool: Read timed out", "transport"),
    ("No route to host", "transport"),
    ("attach failed: {'result': 20}", "transport"),
]:
    v = R.classify_sgs_failure(RuntimeError(msg))
    check(f"T2 {kind:9s} <- {msg[:38]!r}", v["dead"] and v["kind"] == kind, str(v))

print("T3  wrong-device verdict short-circuits to threshold 1")
v = R.classify_sgs_failure(RuntimeError("not_an_stb: host is jenkins"))
check("T3.1 kind=wrong_device", v["kind"] == "wrong_device", str(v))
check("T3.2 threshold=1", v["threshold"] == 1, str(v))

print("T4  unrelated errors must NOT trigger IP recovery")
for msg in ["Unknown button_id 'flurb'", "STB 'nope' not found in base.txt",
            "no RF serial worker registered for 'found1'"]:
    v = R.classify_sgs_failure(ValueError(msg))
    check(f"T4 not-dead <- {msg[:40]!r}", v["dead"] is False, str(v))

print("T5  is_sgs_dead_but_video_alive respects video health")
R._get_status = lambda: {"active": False, "signal_class": "black_screen"}
check("T5.1 dead video -> False", R.is_sgs_dead_but_video_alive(RuntimeError(REAL_403)) is False)
R._get_status = lambda: {"active": True, "signal_class": "active_video"}
check("T5.2 live video + 403 -> True (the fix)",
      R.is_sgs_dead_but_video_alive(RuntimeError(REAL_403)) is True)
check("T5.3 live video + unrelated error -> False",
      R.is_sgs_dead_but_video_alive(ValueError("Unknown button_id")) is False)

print("T6  RF helpers exist (the section used to be an empty stub)")
for fn in ("rf_ready", "_rf_press", "_rf_press_confirmed",
           "classify_sgs_failure", "_probe_device_identity",
           "verify_stored_ip_identity", "find_stb_ip_by_sgs_probe"):
    check(f"T6 {fn} defined", callable(getattr(R, fn, None)))

print("T7  LIVE identity probe against the bench hosts")
ident = R._probe_device_identity("10.73.185.34")
print(f"       10.73.185.34 -> {ident}")
if ident.get("reason") == "unreachable":
    print("  SKIP  host unreachable right now")
else:
    check("T7.1 stale base.txt IP identified as NOT a receiver",
          ident.get("is_stb") is False, str(ident))
    check("T7.2 reason names the offending software",
          any(k in str(ident.get("reason")) for k in ("jenkins", "hudson", "apache", "crumb")),
          str(ident))

unused = R._probe_device_identity("10.73.185.253")
print(f"       10.73.185.253 (likely unused) -> {unused}")
check("T7.3 unreachable host is 'unknown', never falsely rejected",
      unused.get("is_stb") is None, str(unused))

print()
if FAILS:
    print(f"RESULT: {len(FAILS)} FAILURE(S): {FAILS}")
    sys.exit(1)
print("RESULT: ALL CLASSIFIER / IDENTITY TESTS PASSED")
