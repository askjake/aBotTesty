"""Tests for sgs_autopair: PIN OCR, handshake, credential persistence.

Synthetic 1080p pairing dialogs are rendered with OpenCV so the OCR path can be
exercised without a receiver.  The HTTP handshake is stubbed.

Run:  .venv/bin/python tests/test_autopair.py
"""
import json, os, sys, tempfile, shutil, time, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FAILS = []
def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"   {detail}" if detail else ""))
    if not cond:
        FAILS.append(name)

tmp = Path(tempfile.mkdtemp(prefix="autopair_"))
base = tmp / "base.txt"
base.write_text(json.dumps({
    "default_stb": "found1",
    "operator_note": "must survive pairing",
    "stbs": {
        "found1": {"alias": "found1", "stb": "R1956409151-66", "ip": "10.73.185.34",
                   "protocol": "SGS", "remote": "14", "com_port": "/dev/ttyACM0",
                   "role": "hopper", "host": "found1", "model": "Hopper3"},
        "joey1": {"alias": "joey1", "role": "joey", "host": "found1"},
    },
}, indent=4))
os.environ["JAMBOREE_BASE"] = str(base)

import cv2, numpy as np
import sgs_autopair as A
from jamboree.stb_store import STBStore
from jamboree import base_io


# ---------------------------------------------------------------------------
# Fixture note: the first version of this file drew the dialog with OpenCV's
# FONT_HERSHEY_SIMPLEX.  That is a stroke/vector font whose digits are not
# shaped like any real TV UI font -- tesseract read its "3" as "5" and its "5"
# as "9" even with no character whitelist at all, so the test was measuring the
# fixture, not the reader.  We now render with real TrueType faces via PIL and
# exercise several of them, which is both a fair test and a harder one.
# ---------------------------------------------------------------------------
from PIL import Image, ImageDraw, ImageFont

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
FONTS = [p for p in _FONT_CANDIDATES if Path(p).is_file()]
if not FONTS:
    print("SKIP: no TrueType fonts available for the OCR fixture")
    sys.exit(0)


def make_pairing_frame(pin="418052", label="Pairing Code", style="modal",
                       font_path=None, noise=True):
    """Render a plausible receiver pairing dialog at 1920x1080."""
    font_path = font_path or FONTS[0]
    img = Image.new("RGB", (1920, 1080), (18, 14, 12))
    d = ImageDraw.Draw(img)
    big = ImageFont.truetype(font_path, 120)
    mid = ImageFont.truetype(font_path, 46)
    hdr = ImageFont.truetype(font_path, 58)
    if style == "modal":
        d.rectangle([520, 330, 1400, 780], fill=(46, 40, 36),
                    outline=(150, 150, 150), width=3)
        d.text((600, 385), "Authorize Device", font=hdr, fill=(235, 235, 235))
        d.text((600, 490), f"{label}:", font=mid, fill=(215, 215, 215))
        d.text((600, 570), pin, font=big, fill=(255, 255, 255))
    else:  # bottom banner
        d.rectangle([200, 800, 1720, 990], fill=(40, 40, 50))
        d.text((240, 830), f"Enter {label} {pin} to pair JAMboree",
               font=mid, fill=(250, 250, 250))
        d.text((240, 880), pin, font=big, fill=(255, 255, 255))
    arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    if noise:
        # Emulate capture-card noise so the test is not solved by a pristine
        # synthetic bitmap that a real encoder would never produce.
        # zlib.crc32, not hash(): PYTHONHASHSEED randomisation made the
        # noise differ between runs, so accuracy wobbled 24-26/32 for no
        # reason and the test was not reproducible.
        rng = np.random.default_rng(zlib.crc32(pin.encode()) & 0xFFFFFFFF)
        arr = np.clip(arr.astype(np.int16) +
                      rng.normal(0, 4.0, arr.shape).astype(np.int16), 0, 255
                      ).astype(np.uint8)
    return arr


_T1_PINS = ("730914", "555038", "901234", "672310", "418052", "148967", "80512", "1234")

print(f"T1  single-frame OCR accuracy across {len(FONTS)} font(s)")
_per_font = {}
for fp in FONTS:
    hits = 0
    for pin in _T1_PINS:
        ranked = A.score_pin_candidates(make_pairing_frame(pin, font_path=fp))
        if ranked and ranked[0]["pin"] == pin:
            hits += 1
    _per_font[Path(fp).stem] = hits
    print(f"       {Path(fp).stem:26s} top-1 {hits}/{len(_T1_PINS)}")
_total = sum(_per_font.values())
_max = len(FONTS) * len(_T1_PINS)
print(f"       overall single-frame top-1: {_total}/{_max}")
check("T1.1 single-frame top-1 accuracy >= 75%", _total >= 0.75 * _max,
      f"{_total}/{_max} {_per_font}")

print("T1b multi-frame + multi-font voting must resolve the PIN exactly")
_voted = 0
for pin in _T1_PINS:
    # Different fonts per frame is the harshest realistic case: it forces the
    # vote to come from genuine agreement rather than a repeated identical read.
    frames = [make_pairing_frame(pin, font_path=fp) for fp in (FONTS * 3)[:4]]
    i = {"n": 0}
    def _f(frames=frames, i=i):
        f = frames[min(i["n"], len(frames) - 1)]; i["n"] += 1; return f
    A.set_dependencies(get_frame=_f, CFG={"stb_alias": "found1", "default_delay_ms": 120})
    A.PIN_READ_INTERVAL_S = 0.01
    got = A.wait_for_pin(timeout_s=25.0, stable_reads=2)
    ok = (got == pin)
    _voted += 1 if ok else 0
    check(f"T1b pin {pin} resolved", ok, f"got {got!r}")
print(f"       voting accuracy: {_voted}/{len(_T1_PINS)}")

print("T2  OCR reads a PIN from a bottom banner layout")
frame = make_pairing_frame("552901", style="banner")
got = [c[0] for c in A.read_pin_candidates(frame)]   # one-shot => exhaustive
check("T2.1 banner pin found by one-shot read", "552901" in got, str(got[:5]))
# The fast tier intentionally ignores the banner region; escalation must cover it.
fast_only = [c["pin"] for c in A.score_pin_candidates(frame, effort="fast")]
check("T2.2 fast tier correctly ignores the banner region",
      "552901" not in fast_only, str(fast_only[:4]))
i = {"n": 0}
def _bf(i=i, frame=frame):
    i["n"] += 1; return frame
A.set_dependencies(get_frame=_bf, CFG={"stb_alias": "found1", "default_delay_ms": 120})
A.PIN_READ_INTERVAL_S = 0.01
got_wait = A.wait_for_pin(timeout_s=90.0, stable_reads=2)
check("T2.3 wait_for_pin escalates and finds the banner PIN",
      got_wait == "552901", f"got {got_wait!r} after {i['n']} polls")

print("T3  digit normalisation repairs classic OCR confusions")
check("T3.1 O->0 I->1 S->5 B->8", A._normalise_digits("4I8O5B") == "418058",
      A._normalise_digits("4I8O5B"))
check("T3.2 strips separators", A._normalise_digits("41 80-52") == "418052")
check("T3.3 pipe -> 1", A._normalise_digits("4|8052") == "418052")

print("T4  pairing screen detection")
check("T4.1 pairing dialog recognised", A.pairing_screen_visible(make_pairing_frame()) is True)
blank = np.zeros((1080, 1920, 3), np.uint8)
check("T4.2 blank screen not mistaken for pairing", A.pairing_screen_visible(blank) is False)

print("T5  wait_for_pin requires agreement across frames")
seq = [make_pairing_frame("418052") for _ in range(4)]
idx = {"i": 0}
def frames():
    f = seq[min(idx["i"], len(seq) - 1)]; idx["i"] += 1; return f
A.set_dependencies(get_frame=frames, CFG={"stb_alias": "found1", "default_delay_ms": 120})
A.PIN_READ_INTERVAL_S = 0.01
got = A.wait_for_pin(timeout_s=6.0, stable_reads=2)
check("T5.1 stable PIN returned", got == "418052", repr(got))

print("T6  no frame source -> honest failure, not a fake PIN")
A._get_frame = None
check("T6.1 returns None", A.wait_for_pin(timeout_s=0.5) is None)

print("T7  handshake persists credentials additively (base.txt integrity)")
store = STBStore(base)
A.set_dependencies(store=store, CFG={"stb_alias": "found1", "default_delay_ms": 120})

CALLS = []
def fake_post(ip, payload, port_hint=None):
    CALLS.append(payload["command"])
    if payload["command"] == "device_pairing_start":
        return {"result": 1}
    if payload["command"] == "device_pairing_complete":
        if payload.get("pin") != "418052":
            return {"result": -7, "error": "bad_pin"}
        return {"result": 1, "name": "jamboree_u17", "passwd": "S3cretFromStb"}
    return {"result": -1}
A._post_noauth = fake_post

start = A.pair_start("found1")
check("T7.1 pair_start ok", start["ok"] is True, str(start))
env = start["payload"]
check("T7.2 envelope has receiver id", str(env["receiver"]).startswith("XAF"), str(env["receiver"]))
check("T7.3 envelope targets the CAID", env["stb"] == "R1956409151-66")
check("T7.4 envelope app id S9", env["id"] == "S9")

bad = A.pair_complete("found1", "999999")
check("T7.5 wrong PIN rejected", bad["ok"] is False, str(bad))
disk_after_bad = base_io.read_document(base)["stbs"]["found1"]
check("T7.6 no creds written on failure", "passwd" not in disk_after_bad)

good = A.pair_complete("found1", "418052")
check("T7.7 correct PIN accepted", good["ok"] is True, str(good))

d = base_io.read_document(base)
e = d["stbs"]["found1"]
check("T8.1 lname on disk", e.get("lname") == "jamboree_u17", str(e.get("lname")))
check("T8.2 passwd on disk", e.get("passwd") == "S3cretFromStb")
check("T8.3 prod flag set", e.get("prod") is True)
check("T8.4 pair_rid recorded", str(e.get("pair_rid", "")).startswith("XAF"))
check("T8.5 paired_ts recorded", bool(e.get("paired_ts")))
print("T8  ...and nothing else was disturbed")
check("T8.6 ip preserved", e.get("ip") == "10.73.185.34")
check("T8.7 stb preserved", e.get("stb") == "R1956409151-66")
check("T8.8 com_port preserved", e.get("com_port") == "/dev/ttyACM0")
check("T8.9 model preserved", e.get("model") == "Hopper3")
check("T8.10 sibling joey1 preserved", "joey1" in d["stbs"])
check("T8.11 top-level default_stb preserved", d.get("default_stb") == "found1")
check("T8.12 top-level operator_note preserved", d.get("operator_note") == "must survive pairing")

print("T9  credentials survive a later IP-recovery style write")
store.reload()
store.update_stb("found1", {"ip": "10.79.85.120"})
e2 = base_io.read_document(base)["stbs"]["found1"]
check("T9.1 creds still there after ip change", e2.get("passwd") == "S3cretFromStb")
check("T9.2 new ip applied", e2.get("ip") == "10.79.85.120")
check("T9.3 top-level still intact",
      base_io.read_document(base).get("operator_note") == "must survive pairing")

print("T10 verify_credentials_persisted reads the FILE, not the cache")
v = A.verify_credentials_persisted("found1", expect_login="jamboree_u17")
check("T10.1 on_disk True", v["on_disk"] is True)
check("T10.2 login matches", v["matches_expected_login"] is True)
check("T10.3 identity intact", v["identity_intact"] is True)
check("T10.4 reports siblings", v["sibling_aliases"] == ["joey1"], str(v["sibling_aliases"]))
check("T10.5 reports other top-level keys",
      set(v["other_top_level_keys"]) == {"default_stb", "operator_note"},
      str(v["other_top_level_keys"]))

print("T11 stale receiver-id detection (NIC change invalidates credentials)")
store.update_stb("found1", {"pair_rid": "XAFdeadbeef0000"})
store.reload()
cs = A.credentials_status("found1")
check("T11.1 paired True", cs["paired"] is True)
check("T11.2 stale_rid detected", cs["stale_rid"] is True, str(cs))
store.update_stb("found1", {"pair_rid": A._receiver_id()})
store.reload()
check("T11.3 matching rid is not stale", A.credentials_status("found1")["stale_rid"] is False)

print("T12 auto_pair refuses to pair a non-receiver")
import ip_recovery
ip_recovery._probe_device_identity = lambda ip, timeout=3.0: {
    "is_stb": False, "reason": "header:x-jenkins", "server": "jetty"}
out = A.auto_pair("found1", pin="418052", force=True, verify=False)
check("T12.1 refused", out["ok"] is False, str(out.get("detail"))[:90])
check("T12.2 reason explains why", "not a set-top box" in out["detail"], out["detail"][:90])
check("T12.3 pair_start never sent", "device_pairing_start" not in CALLS[-1:], str(CALLS[-3:]))

shutil.rmtree(tmp, ignore_errors=True)
print()
if FAILS:
    print(f"RESULT: {len(FAILS)} FAILURE(S): {FAILS}")
    sys.exit(1)
print("RESULT: ALL AUTOPAIR TESTS PASSED")
