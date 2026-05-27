import json, os, time, urllib.request, logging
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
    open(path,"wb").write(r.read())
    return path

# Reset channel to 206 first
sgs_post("/key", {"key": "CH_206", "input": 6})
time.sleep(0.5)

# Auto-detect
state = sgs_get("/screen")
inp = state["input"]
ch  = state["channel"]
log.info("Auto-detected: input=%s channel=%s signal=%s", inp, ch, state["signal"])

# Baseline
path = grab(f"screen_ch{ch}_baseline")
sz = os.path.getsize(path)
log.info("Baseline: %s (%d bytes)", os.path.basename(path), sz)
nav_map = [{"action":"baseline", "channel":ch, "file":os.path.basename(path), "bytes":sz}]

# Navigate CH_UP x3
for i in range(3):
    sgs_post("/key", {"key":"CH_UP", "input":inp})
    time.sleep(1.5)
    s = sgs_get("/screen")
    path = grab(f"screen_ch{s[chr(99)+chr(104)+chr(97)+chr(110)+chr(110)+chr(101)+chr(108)]}_step{i+1}")
    sz = os.path.getsize(path)
    nav_map.append({"action":f"CH_UP #{i+1}", "channel":s["channel"], "file":os.path.basename(path), "bytes":sz})
    log.info("Step %d -> CH%s  %s (%d bytes)", i+1, s["channel"], os.path.basename(path), sz)

open(os.path.join(OUTDIR,"nav_map.json"),"w").write(json.dumps(nav_map,indent=2))
print("\nNAVIGATION MAP")
print("-"*55)
for s in nav_map:
    print(f"  {s[chr(97)+chr(99)+chr(116)+chr(105)+chr(111)+chr(110)]:15s} | CH {s[chr(99)+chr(104)+chr(97)+chr(110)+chr(110)+chr(101)+chr(108)]:>4} | {s[chr(102)+chr(105)+chr(108)+chr(101)]} ({s[chr(98)+chr(121)+chr(116)+chr(101)+chr(115)]:,} bytes)")
print(f"\nDONE. input={inp} auto-detected")
