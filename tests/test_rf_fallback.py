"""Tests for the SGS -> RF fallback in jamboree.controller (no hardware needed).

Run:  .venv/bin/python tests/test_rf_fallback.py
"""
import json, sys, tempfile, shutil, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FAILS = []
def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"   {detail}" if detail else ""))
    if not cond:
        FAILS.append(name)

tmp = Path(tempfile.mkdtemp(prefix="rf_fallback_"))
base = tmp / "base.txt"
base.write_text(json.dumps({"stbs": {"found1": {
    "alias": "found1", "stb": "R1956409151-66", "ip": "10.73.185.34",
    "protocol": "SGS", "remote": "14", "com_port": "/dev/ttyACM0",
    "role": "hopper", "host": "found1"}}}, indent=4))
os.environ["JAMBOREE_BASE"] = str(base)

# ---- stub the two leaf transports before controller imports them -------------
import jamboree.serial_bridge as sb
import jamboree.sgs_bridge as sgsb

CALLS = []
SGS_SHOULD_FAIL = {"v": True}
RF_SHOULD_FAIL = {"v": False}
RF_PRESENT = {"v": True}

REAL_403 = ('{"command": "remote_key", "key_name": "Home"}\n'
            'remote_key failed -> {\n  "result": -13,\n'
            '  "error": "auth_required_or_opt_in_disabled",\n'
            '  "http_status": 403,\n'
            '  "text": "Error 403 No valid crumb was included in the request"\n}')

def fake_send_sgs(stb_name, stb_ip, rxid, button_id, delay_ms, **kw):
    CALLS.append(("sgs", button_id))
    if SGS_SHOULD_FAIL["v"]:
        raise RuntimeError(REAL_403)
    return "key accepted"

def fake_send_rf_strict(alias, remote, button, delay):
    CALLS.append(("rf", button))
    if not RF_PRESENT["v"]:
        raise RuntimeError(f"no RF serial worker registered for '{alias}'")
    if RF_SHOULD_FAIL["v"]:
        raise RuntimeError("RF write could not be queued")
    return f"{remote} CMD REL {delay}"

def fake_send_rf(alias, remote, button, delay):
    CALLS.append(("rf", button))
    return f"{remote} CMD REL {delay}"

def fake_rf_available(alias):
    return RF_PRESENT["v"]

sgsb.send_sgs = fake_send_sgs
sb.send_rf_strict = fake_send_rf_strict
sb.send_rf = fake_send_rf
sb.rf_available = fake_rf_available

import jamboree.controller as C
C.send_sgs = fake_send_sgs
C.send_rf_strict = fake_send_rf_strict
C.send_rf = fake_send_rf
C.rf_available = fake_rf_available

try:
    ctl = C.Controller()

    # ---- T1: the reported bug -- SGS 403 must degrade to RF, not raise
    print("T1  SGS failure degrades to RF instead of raising")
    CALLS.clear(); SGS_SHOULD_FAIL["v"] = True; RF_PRESENT["v"] = True; RF_SHOULD_FAIL["v"] = False
    try:
        r = ctl.handle_auto_remote("14", "found1", "home", 120)
        raised = None
    except Exception as e:
        r, raised = None, e
    check("T1.1 no exception escaped", raised is None, f"raised {raised!r}")
    check("T1.2 SGS was attempted first", CALLS and CALLS[0][0] == "sgs", str(CALLS))
    check("T1.3 RF was actually used", ("rf", "home") in CALLS, str(CALLS))
    check("T1.4 result marks via=rf_fallback", bool(r) and r.get("via") == "rf_fallback", str(r))
    check("T1.5 original SGS error preserved", bool(r) and "403" in str(r.get("sgs_error")))

    # ---- T2: healthy SGS must NOT touch RF
    print("T2  healthy SGS does not touch the RF line")
    CALLS.clear(); SGS_SHOULD_FAIL["v"] = False
    r = ctl.handle_auto_remote("14", "found1", "home", 120)
    check("T2.1 via=sgs", r.get("via") == "sgs")
    check("T2.2 RF untouched", not any(c[0] == "rf" for c in CALLS), str(CALLS))

    # ---- T3: force="rf" bypasses SGS entirely (what ip_recovery needs)
    print("T3  force='rf' bypasses SGS entirely")
    CALLS.clear(); SGS_SHOULD_FAIL["v"] = True
    r = ctl.handle_auto_remote("14", "found1", "home", 120, force="rf")
    check("T3.1 SGS never called", not any(c[0] == "sgs" for c in CALLS), str(CALLS))
    check("T3.2 RF called", ("rf", "home") in CALLS)
    check("T3.3 via=rf", r.get("via") == "rf")

    # ---- T4: force="sgs" must still raise (no silent masking)
    print("T4  force='sgs' still raises so real SGS breakage stays visible")
    CALLS.clear()
    try:
        ctl.handle_auto_remote("14", "found1", "home", 120, force="sgs"); raised = None
    except Exception as e:
        raised = e
    check("T4.1 exception propagated", raised is not None)
    check("T4.2 RF not used", not any(c[0] == "rf" for c in CALLS))

    # ---- T5: no RF hardware -> must raise, never pretend success
    print("T5  no RF line -> failure is reported, not faked")
    CALLS.clear(); RF_PRESENT["v"] = False
    try:
        ctl.handle_auto_remote("14", "found1", "home", 120); raised = None
    except Exception as e:
        raised = e
    check("T5.1 exception propagated", raised is not None)
    check("T5.2 rf_ready() reports False", ctl.rf_ready("found1") is False)

    # ---- T6: both transports dead -> combined, explicit error
    print("T6  both transports dead -> combined error mentions both")
    RF_PRESENT["v"] = True; RF_SHOULD_FAIL["v"] = True
    try:
        ctl.handle_auto_remote("14", "found1", "home", 120); raised = None
    except Exception as e:
        raised = e
    check("T6.1 raised", raised is not None)
    check("T6.2 mentions rf_error", "rf_error" in str(raised), str(raised)[:120])
    check("T6.3 mentions sgs_error", "sgs_error" in str(raised))

    # ---- T7: transports() introspection
    print("T7  transports() reports capability honestly")
    RF_SHOULD_FAIL["v"] = False
    tr = ctl.transports("found1")
    check("T7.1 protocol SGS", tr["protocol"] == "SGS")
    check("T7.2 sgs_configured", tr["sgs_configured"] is True)
    check("T7.3 sgs_paired False (no creds in base.txt)", tr["sgs_paired"] is False)
    check("T7.4 rf_ready True", tr["rf_ready"] is True)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
if FAILS:
    print(f"RESULT: {len(FAILS)} FAILURE(S): {FAILS}")
    sys.exit(1)
print("RESULT: ALL RF-FALLBACK TESTS PASSED")
