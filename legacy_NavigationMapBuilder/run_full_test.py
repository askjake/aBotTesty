import json, os, time, urllib.request, logging, hashlib
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)
SGS = "http://127.0.0.1:8080"
OUTDIR = r"C:\Users\Systems1\Documents\aBitTesty\NavigationMapBuilder\nav_maps"
os.makedirs(OUTDIR, exist_ok=True)

def sgs_get(path):
    return json.loads(urllib.request.urlopen(SGS+path, timeout=6).read().decode())

def sgs_post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(SGS+path, data=data,
          headers={"Content-Type":"application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=6).read().decode())

def grab(label):
    r = urllib.request.urlopen(SGS+"/screenshot", timeout=8)
    ct = r.headers.get("Content-Type","")
    ext = "jpg" if "jpeg" in ct else "png"
    path = os.path.join(OUTDIR, f"{label}.{ext}")
    raw = r.read()
    open(path,"wb").write(raw)
    md5 = hashlib.md5(raw).hexdigest()[:8]
    return path, len(raw), md5

results = []

# ── SECTION 1: Reset to CH 206 ───────────────────────────────────
log.info("=== SECTION 1: Reset to CH 206 ===")
sgs_post("/key", {"key": "CH_206", "input": 6})
time.sleep(0.5)
s = sgs_get("/screen")
log.info("Reset: channel=%s input=%s", s["channel"], s["input"])
assert s["channel"] == 206, f"Reset failed: got {s[chr(99)+chr(104)+chr(97)+chr(110)+chr(110)+chr(101)+chr(108)]}"

# ── SECTION 2: CH_UP x3 (206->209) ──────────────────────────────
log.info("=== SECTION 2: CH_UP x3 ===")
path, sz, md5 = grab("ch206_baseline")
results.append({"test":"baseline", "ch":206, "file":os.path.basename(path), "bytes":sz, "md5":md5, "pass":True})
log.info("baseline CH206 %s %d bytes", md5, sz)

for i in range(3):
    sgs_post("/key", {"key": "CH_UP", "input": 6})
    time.sleep(1.0)
    s = sgs_get("/screen")
    expected = 207 + i
    ok = s["channel"] == expected
    path, sz, md5 = grab(f"ch{s[chr(99)+chr(104)+chr(97)+chr(110)+chr(110)+chr(101)+chr(108)]}_up{i+1}")
    results.append({"test":f"CH_UP#{i+1}", "ch":s["channel"], "expected":expected, "file":os.path.basename(path), "bytes":sz, "md5":md5, "pass":ok})
    log.info("CH_UP#%d -> ch%s expected=%d %s %s", i+1, s["channel"], expected, "PASS" if ok else "FAIL", md5)

# ── SECTION 3: CH_DOWN x3 round-trip (209->206) ──────────────────
log.info("=== SECTION 3: CH_DOWN x3 round-trip ===")
for i in range(3):
    sgs_post("/key", {"key": "CH_DOWN", "input": 6})
    time.sleep(1.0)
    s = sgs_get("/screen")
    expected = 208 - i
    ok = s["channel"] == expected
    path, sz, md5 = grab(f"ch{s[chr(99)+chr(104)+chr(97)+chr(110)+chr(110)+chr(101)+chr(108)]}_down{i+1}")
    results.append({"test":f"CH_DOWN#{i+1}", "ch":s["channel"], "expected":expected, "file":os.path.basename(path), "bytes":sz, "md5":md5, "pass":ok})
    log.info("CH_DOWN#%d -> ch%s expected=%d %s %s", i+1, s["channel"], expected, "PASS" if ok else "FAIL", md5)

# ── SECTION 4: Direct tune verification ──────────────────────────
log.info("=== SECTION 4: Direct tune ===")
for ch in [200, 210, 220, 230]:
    sgs_post("/key", {"key": f"CH_{ch}", "input": 6})
    time.sleep(0.8)
    s = sgs_get("/screen")
    ok = s["channel"] == ch
    path, sz, md5 = grab(f"ch{ch}_direct")
    results.append({"test":f"DIRECT_{ch}", "ch":s["channel"], "expected":ch, "file":os.path.basename(path), "bytes":sz, "md5":md5, "pass":ok})
    log.info("DIRECT %d -> ch%s %s %s", ch, s["channel"], "PASS" if ok else "FAIL", md5)

# ── SECTION 5: Channel sweep 200-230 every 5 ─────────────────────
log.info("=== SECTION 5: Channel sweep 200-230 ===")
sweep = []
for ch in range(200, 231, 5):
    sgs_post("/key", {"key": f"CH_{ch}", "input": 6})
    time.sleep(0.6)
    s = sgs_get("/screen")
    ok = s["channel"] == ch
    path, sz, md5 = grab(f"sweep_ch{ch}")
    sweep.append({"ch":ch, "actual":s["channel"], "file":os.path.basename(path), "bytes":sz, "md5":md5, "pass":ok})
    log.info("SWEEP ch%d actual=%s %s %s", ch, s["channel"], "PASS" if ok else "FAIL", md5)

# ── RESULTS ──────────────────────────────────────────────────────
print("\n" + "="*60)
print("  NAVIGATION MAP TEST RESULTS")
print("="*60)
passed = sum(1 for r in results if r["pass"])
print(f"\nSections 1-4: {passed}/{len(results)} passed")
print(f"{'Test':<12} {'CH':<6} {'Expected':<10} {'Pass':<6} {'MD5':<10} {'Bytes':<8}")
print("-"*60)
for r in results:
    exp = str(r.get("expected","-"))
    print(f"{r[chr(116)+chr(101)+chr(115)+chr(116)]:<12} {r[chr(99)+chr(104)]:<6} {exp:<10} {str(r[chr(112)+chr(97)+chr(115)+chr(115)]):<6} {r[chr(109)+chr(100)+chr(53)]:<10} {r[chr(98)+chr(121)+chr(116)+chr(101)+chr(115)]:<8}")
print("\n" + "-"*60)
print("  CHANNEL SWEEP 200-230")
print("-"*60)
for s in sweep:
    bar = "#" * (s["bytes"] // 200)
    print(f"  CH{s[chr(99)+chr(104)]:>3}  {str(s[chr(112)+chr(97)+chr(115)+chr(115)]):>5}  {s[chr(109)+chr(100)+chr(53)]}  {s[chr(102)+chr(105)+chr(108)+chr(101)]}")

# Save full results
all_results = {"section_tests": results, "sweep": sweep}
open(os.path.join(OUTDIR, "test_results.json"), "w").write(json.dumps(all_results, indent=2))
log.info("Results saved to test_results.json")
