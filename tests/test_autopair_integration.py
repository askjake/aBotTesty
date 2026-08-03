"""Integration tests for the auto-pair escalation wiring (v39).

Covers the three seams added on 2026-08-03:
  1. ip_recovery.note_sgs_failure -> sgs_autopair  (auth failure on a real
     receiver must PAIR, never hunt for a new IP)
  2. jamboree/routes_sgs.py pair_complete -> additive credential persistence
  3. merged_app.py exposes the /api/sgs/pair/* endpoints

Run:  .venv/bin/python tests/test_autopair_integration.py
"""
import ast, json, os, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FAILS = []
def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"   {detail}" if detail else ""))
    if not cond:
        FAILS.append(name)

AUTH_ERR = RuntimeError(
    'remote_key failed -> {"result": -13, "error": "auth_required_or_opt_in_disabled", '
    '"http_status": 403, "text": "Error 403 No valid crumb was included in the request"}'
)
TRANSPORT_ERR = RuntimeError("HTTPConnectionPool(host='10.73.185.37', port=8080): Read timed out")

import ip_recovery as ipr

# ── harness ──────────────────────────────────────────────────────────────────
class Spy:
    def __init__(self):
        self.pair_calls = []
        self.recovery_calls = 0

def install(spy, *, is_stb):
    """Redirect ip_recovery's collaborators at the seam, leaving logic intact."""
    ipr._consecutive_sgs_failures = 0
    ipr._autopair_last_ts = 0.0
    ipr._autopair_last = {}
    ipr.verify_stored_ip_identity = lambda *a, **k: {
        "is_stb": is_stb, "ip": "10.73.185.37", "reason": "digest_challenge"}
    ipr.maybe_trigger_recovery = lambda: (spy.__setattr__("recovery_calls", spy.recovery_calls + 1), True)[1]
    ipr.is_sgs_dead_but_video_alive = lambda exc=None: True
    ipr._CFG = {"stb_alias": "found1"}

    mod = type(sys)("sgs_autopair")
    def auto_pair_async(alias=None, **kw):
        spy.pair_calls.append(alias)
        return True
    mod.auto_pair_async = auto_pair_async
    sys.modules["sgs_autopair"] = mod

_real = {k: getattr(ipr, k) for k in
         ("verify_stored_ip_identity", "maybe_trigger_recovery", "is_sgs_dead_but_video_alive")}

print("T1  auth failure on a REAL receiver pairs instead of chasing an IP")
spy = Spy(); install(spy, is_stb=True)
ipr.note_sgs_failure(AUTH_ERR)
check("T1.1 one failure is below the auth threshold", spy.pair_calls == [], f"calls={spy.pair_calls}")
ipr.note_sgs_failure(AUTH_ERR)
check("T1.2 auto-pair launched at threshold", spy.pair_calls == ["found1"], f"calls={spy.pair_calls}")
check("T1.3 IP recovery NOT started (it cannot fix auth)", spy.recovery_calls == 0,
      f"recovery_calls={spy.recovery_calls}")
check("T1.4 status reports the trigger", ipr.get_recovery_status()["autopair"].get("triggered") is True,
      json.dumps(ipr.get_recovery_status()["autopair"]))

print("T2  cooldown stops a pairing storm")
before = len(spy.pair_calls)
ipr._consecutive_sgs_failures = 99
ipr.note_sgs_failure(AUTH_ERR)
check("T2.1 second attempt suppressed", len(spy.pair_calls) == before, f"calls={spy.pair_calls}")
check("T2.2 reason is cooldown", ipr._autopair_last.get("reason") == "cooldown",
      json.dumps(ipr._autopair_last))
check("T2.3 reports retry_in_s", isinstance(ipr._autopair_last.get("retry_in_s"), float),
      str(ipr._autopair_last.get("retry_in_s")))

print("T3  auth failure on a NON-receiver is an IP problem, not a pairing problem")
spy = Spy(); install(spy, is_stb=False)
ipr.note_sgs_failure(AUTH_ERR); ipr.note_sgs_failure(AUTH_ERR)
check("T3.1 no pairing attempted", spy.pair_calls == [], f"calls={spy.pair_calls}")
check("T3.2 IP recovery started instead", spy.recovery_calls == 1, f"recovery={spy.recovery_calls}")

print("T4  transport failures never trigger pairing")
spy = Spy(); install(spy, is_stb=True)
for _ in range(4):
    ipr.note_sgs_failure(TRANSPORT_ERR)
check("T4.1 no pairing attempted", spy.pair_calls == [], f"calls={spy.pair_calls}")
check("T4.2 IP recovery handled it", spy.recovery_calls >= 1, f"recovery={spy.recovery_calls}")

print("T5  JAMBOREE_AUTOPAIR=0 is honoured")
spy = Spy(); install(spy, is_stb=True)
os.environ["JAMBOREE_AUTOPAIR"] = "0"
try:
    ipr.note_sgs_failure(AUTH_ERR); ipr.note_sgs_failure(AUTH_ERR)
    check("T5.1 suppressed by env", spy.pair_calls == [], f"calls={spy.pair_calls}")
    check("T5.2 reason recorded", ipr._autopair_last.get("reason") == "disabled_by_env",
          json.dumps(ipr._autopair_last))
finally:
    os.environ.pop("JAMBOREE_AUTOPAIR", None)
for k, v in _real.items():
    setattr(ipr, k, v)

print("T6  a successful press clears the failure counter")
ipr._consecutive_sgs_failures = 5
ipr.note_sgs_success()
check("T6.1 counter reset", ipr._consecutive_sgs_failures == 0,
      str(ipr._consecutive_sgs_failures))

# ── T7: routes_sgs.py must not rewrite base.txt ──────────────────────────────
print("T7  pair_complete persists credentials ADDITIVELY")
src = (ROOT / "jamboree/routes_sgs.py").read_text()
tree = ast.parse(src)
fn = next(n for n in ast.walk(tree)
          if isinstance(n, ast.FunctionDef) and n.name == "pair_complete")
body = ast.dump(fn)
check("T7.1 full-document rewrite removed", "sgs_save_base" not in body)
check("T7.2 uses additive set_credentials", "set_credentials" in body)
check("T7.3 marks the box as paired (prod=True)", "prod" in body)
check("T7.4 records the receiver id used to pair", "pair_rid" in body)
check("T7.5 persistence failure is surfaced, not swallowed",
      "paired but failed to persist" in src)

print("T8  ...and the additive write really preserves everything else")
from jamboree import base_io
tmp = Path(tempfile.mkdtemp(prefix="pairint_")) / "base.txt"
tmp.write_text(json.dumps({
    "default_stb": "found1",
    "operator_note": "keep me",
    "stbs": {
        "found1": {"alias": "found1", "ip": "10.73.185.37", "stb": "R1956409151-66",
                   "com_port": "/dev/ttyACM0", "remote": "14", "model": "Hopper3"},
        "joey1": {"alias": "joey1", "role": "joey"},
    },
}, indent=4))
from jamboree.stb_store import STBStore
st = STBStore(tmp)
st.set_credentials("found1", "jamboree_u42", "pw42", prod=True, pair_rid="XAFaabbccddeeff")
doc = json.loads(tmp.read_text())
f1 = doc["stbs"]["found1"]
check("T8.1 lname written", f1.get("lname") == "jamboree_u42", str(f1.get("lname")))
check("T8.2 passwd written", f1.get("passwd") == "pw42")
check("T8.3 prod set", f1.get("prod") is True)
check("T8.4 ip preserved", f1.get("ip") == "10.73.185.37")
check("T8.5 com_port preserved", f1.get("com_port") == "/dev/ttyACM0")
check("T8.6 model preserved", f1.get("model") == "Hopper3")
check("T8.7 sibling alias preserved", doc["stbs"].get("joey1", {}).get("role") == "joey")
check("T8.8 top-level default_stb preserved", doc.get("default_stb") == "found1")
check("T8.9 top-level operator_note preserved", doc.get("operator_note") == "keep me")

# a later IP-only update must not evict the creds we just stored
st.update_stb("found1", {"ip": "10.73.185.99"})
doc = json.loads(tmp.read_text()); f1 = doc["stbs"]["found1"]
check("T8.10 creds survive a later ip write", f1.get("lname") == "jamboree_u42" and f1.get("passwd") == "pw42")
check("T8.11 new ip applied", f1.get("ip") == "10.73.185.99")

# ── T9: merged_app must actually expose the endpoints ────────────────────────
print("T9  merged_app.py exposes the auto-pair endpoints")
msrc = (ROOT / "merged_app.py").read_text()
mtree = ast.parse(msrc)
routes = set()
for node in ast.walk(mtree):
    if isinstance(node, ast.FunctionDef):
        for d in node.decorator_list:
            if isinstance(d, ast.Call) and d.args and isinstance(d.args[0], ast.Constant):
                routes.add(str(d.args[0].value))
for want in ("/api/sgs/pair/status", "/api/sgs/pair/auto", "/api/sgs/pair/verify"):
    check(f"T9 route {want} registered", want in routes)
check("T9.4 sgs_autopair imported", "import sgs_autopair" in msrc)
check("T9.5 dependencies injected", "sgs_autopair.set_dependencies(" in msrc)
check("T9.6 frame source wired (PIN OCR needs it)",
      "sgs_autopair.set_dependencies(\n    get_frame=monitor.get_frame," in msrc)

print()
if FAILS:
    print(f"RESULT: {len(FAILS)} INTEGRATION CHECK(S) FAILED -> {FAILS}")
    sys.exit(1)
print("RESULT: ALL AUTO-PAIR INTEGRATION TESTS PASSED")
