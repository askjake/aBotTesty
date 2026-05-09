#!/usr/bin/env python3
"""Merged active-video monitor + JAMboree Lite SGS controller.

Run from this folder:
    python merged_app.py

Default UI:
    http://127.0.0.1:8502/monitor

This keeps JAMboree Lite's original routes alive, including:
    /auto/<remote>/<stb>/<button>/<delay>
    /get-stb-list
    /sgs/pair/start
    /sgs/pair/complete

And adds monitor/control routes around the fixed STB alias `found1`.
"""
from __future__ import annotations

import io
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

# The JAMboree package reads JAMBOREE_BASE at import time.
ROOT = Path(__file__).resolve().parent
os.environ.setdefault("JAMBOREE_BASE", str(ROOT / "base.txt"))

from flask import Response, jsonify, request, send_file  # noqa: E402

from capture_monitor import CaptureMonitor  # noqa: E402
from auto_crawler import AutonomousCrawler, CrawlerConfig  # noqa: E402
from jamboree.app import app, ctl  # noqa: E402
from jamboree.stb_store import store  # noqa: E402

log = logging.getLogger("merged.app")

DEFAULT_CONFIG: Dict[str, Any] = {
    "server_host": "0.0.0.0",
    "server_port": 8502,
    "stb_alias": "found1",
    "remote": "sgs",
    "default_delay_ms": 120,
    "capture_device": 1,
    "capture_backend": "dshow",
    "capture_width": 1280,
    "capture_height": 720,
    "capture_fps": 30,
    "signal_min_brightness": 8.0,
    "signal_min_variance": 25.0,
    "motion_threshold": 2.0,
    "snapshot_dir": "snapshots",
    "log_dir": "logs",
    "crawler_dir": "crawler_data",
    "crawler_enabled_keys": ["up", "down", "left", "right", "guide", "back", "home", "info", "select"],
    "crawler_max_steps": 250,
    "crawler_max_states": 80,
    "crawler_max_depth": 7,
    "crawler_state_similarity_threshold": 0.86,
    "crawler_changed_similarity_threshold": 0.94,
    "crawler_ocr_enabled": True,
    "crawler_allow_select_on_dangerous_text": False,
    "crawler_start_sequence": [],
    "crawler_self_explore_enabled": True,
    "crawler_adaptive_timing_enabled": True,
    "crawler_min_settle_s": 0.35,
    "crawler_max_settle_s": 3.5,
    "crawler_channel_learning_enabled": False,
    "crawler_channel_scan_list": [200, 205, 206, 207, 208, 209, 210, 220, 230],
    "crawler_channel_digit_gap_s": 0.075,
    "crawler_channel_tune_settle_s": 2.2,
}


CONFIG_FILE = ROOT / "config.json"


def load_config() -> Dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.is_file():
        cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    return cfg


CFG = load_config()
if os.getenv("MERGED_SERVER_PORT"):
    CFG["server_port"] = int(os.getenv("MERGED_SERVER_PORT", CFG["server_port"]))
if os.getenv("MERGED_CAPTURE_DEVICE"):
    CFG["capture_device"] = int(os.getenv("MERGED_CAPTURE_DEVICE", CFG["capture_device"]))
SNAPSHOT_DIR = (ROOT / str(CFG["snapshot_dir"])).resolve()
LOG_DIR = (ROOT / str(CFG["log_dir"])).resolve()
CRAWLER_DIR = (ROOT / str(CFG["crawler_dir"])).resolve()
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
CRAWLER_DIR.mkdir(parents=True, exist_ok=True)

# Optional file logger in addition to JAMboree Lite's console logger.
try:
    file_handler = logging.FileHandler(LOG_DIR / "merged_app.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s"))
    logging.getLogger().addHandler(file_handler)
except Exception:
    log.exception("unable to attach file logger")

monitor = CaptureMonitor(
    device=CFG["capture_device"],
    backend=str(CFG["capture_backend"]),
    width=int(CFG["capture_width"]),
    height=int(CFG["capture_height"]),
    fps=int(CFG["capture_fps"]),
    signal_min_brightness=float(CFG["signal_min_brightness"]),
    signal_min_variance=float(CFG["signal_min_variance"]),
    motion_threshold=float(CFG["motion_threshold"]),
)

# Start monitoring immediately; /monitor/stop can pause it.
monitor.start()


KEY_ALIASES = {
    "KEY_UP": "up",
    "UP": "up",
    "ARROWUP": "up",
    "KEY_DOWN": "down",
    "DOWN": "down",
    "ARROWDOWN": "down",
    "KEY_LEFT": "left",
    "LEFT": "left",
    "ARROWLEFT": "left",
    "KEY_RIGHT": "right",
    "RIGHT": "right",
    "ARROWRIGHT": "right",
    "OK": "select",
    "ENTER": "select",
    "SELECT": "select",
    "KEY_OK": "select",
    "BACK": "back",
    "KEY_BACK": "back",
    "HOME": "home",
    "KEY_HOME": "home",
    "MENU": "home",
    "GUIDE": "guide",
    "INFO": "info",
    "EXIT": "back",
    "CH_UP": "ch_up",
    "CHANNEL_UP": "ch_up",
    "CH+": "ch_up",
    "CH_DOWN": "ch_down",
    "CHANNEL_DOWN": "ch_down",
    "CH-": "ch_down",
    "VOL_UP": "vol+",
    "VOLUME_UP": "vol+",
    "VOL_DOWN": "vol-",
    "VOLUME_DOWN": "vol-",
    "MUTE": "mute",
    "INPUT": "input",
    "DVR": "dvr",
    "PLAY": "play",
    "PAUSE": "play",
    "PAUSEPLAY": "play",
    "STOP": "stop",
    "FF": "fwd",
    "FAST_FORWARD": "fwd",
    "RW": "rwd",
    "REWIND": "rwd",
    "RECALL": "recall",
    "LIVE": "live",
    "LIVE_TV": "live tv",
}

for digit in "0123456789":
    KEY_ALIASES[digit] = digit
    KEY_ALIASES[f"KEY_{digit}"] = digit


def normalize_button(key: str) -> str:
    raw = str(key or "").strip()
    if not raw:
        raise ValueError("empty key")
    return KEY_ALIASES.get(raw.upper(), raw.lower())


def key_sequence_for(key: str, channel_suffix_key: str = "select") -> List[str]:
    """Return one or more JAMboree button IDs for a requested key.

    CH_206 / channel:206 becomes 2,0,6,select so direct tune works through
    the same remote path. Numeric channel entry is intentionally represented as
    multiple short-gap button presses rather than one long command.
    """
    raw = str(key or "").strip()
    upper = raw.upper()
    channel = None
    for prefix in ("CH_", "CH:", "CHANNEL_", "CHANNEL:"):
        if upper.startswith(prefix) and upper[len(prefix):].isdigit():
            channel = upper[len(prefix):]
            break
    if channel is None and upper.startswith("CH") and upper[2:].isdigit():
        channel = upper[2:]
    if channel:
        suffix = normalize_button(channel_suffix_key) if channel_suffix_key else ""
        return [*channel, *([suffix] if suffix else [])]
    return [normalize_button(raw)]


def press_button(button: str, delay_ms: int | None = None) -> Dict[str, Any]:
    alias = str(CFG["stb_alias"])
    remote = str(CFG["remote"])
    delay = int(delay_ms if delay_ms is not None else CFG["default_delay_ms"])
    if not store.get(alias):
        raise ValueError(f"STB alias '{alias}' is not present in base.txt")
    result = ctl.handle_auto_remote(remote, alias, button, delay)
    return {"ok": True, "alias": alias, "button": button, "delay_ms": delay, "result": result}


def press_sequence(keys: Iterable[str], delay_ms: int | None = None, gap_s: float = 0.2) -> Dict[str, Any]:
    sent: List[Dict[str, Any]] = []
    for key in keys:
        sent.append(press_button(key, delay_ms=delay_ms))
        time.sleep(gap_s)
    return {"ok": True, "sent": sent, "count": len(sent)}


def crawler_send_key(key: str) -> Dict[str, Any]:
    """Callback used by the autonomous crawler.

    It deliberately routes through the same normalization/SGS path as the public
    endpoints, so crawler behavior matches manual operation. Channel actions use
    a short digit gap so 2-0-6 behaves like a human quick-tuning a channel.
    """
    seq = key_sequence_for(key, channel_suffix_key=str(crawler.config.channel_suffix_key if "crawler" in globals() else "select"))
    is_channel = len(seq) >= 3 and all(x.isdigit() for x in seq[:-1])
    return press_sequence(
        seq,
        delay_ms=int(CFG["default_delay_ms"]),
        gap_s=float(crawler.config.channel_digit_gap_s if is_channel and "crawler" in globals() else 0.2),
    )


crawler = AutonomousCrawler(
    data_dir=CRAWLER_DIR,
    capture_frame=monitor.get_frame,
    capture_status=monitor.get_status,
    send_key=crawler_send_key,
    config=CrawlerConfig(
        enabled_keys=list(CFG.get("crawler_enabled_keys", [])),
        max_steps=int(CFG.get("crawler_max_steps", 250)),
        max_states=int(CFG.get("crawler_max_states", 80)),
        max_depth=int(CFG.get("crawler_max_depth", 7)),
        state_similarity_threshold=float(CFG.get("crawler_state_similarity_threshold", 0.86)),
        changed_similarity_threshold=float(CFG.get("crawler_changed_similarity_threshold", 0.94)),
        ocr_enabled=bool(CFG.get("crawler_ocr_enabled", True)),
        allow_select_on_dangerous_text=bool(CFG.get("crawler_allow_select_on_dangerous_text", False)),
        start_sequence=list(CFG.get("crawler_start_sequence", [])),
        self_explore_enabled=bool(CFG.get("crawler_self_explore_enabled", True)),
        adaptive_timing_enabled=bool(CFG.get("crawler_adaptive_timing_enabled", True)),
        min_settle_s=float(CFG.get("crawler_min_settle_s", 0.35)),
        max_settle_s=float(CFG.get("crawler_max_settle_s", 3.5)),
        channel_learning_enabled=bool(CFG.get("crawler_channel_learning_enabled", False)),
        channel_scan_list=list(CFG.get("crawler_channel_scan_list", [])),
        channel_digit_gap_s=float(CFG.get("crawler_channel_digit_gap_s", 0.075)),
        channel_tune_settle_s=float(CFG.get("crawler_channel_tune_settle_s", 2.2)),
    ),
)


def placeholder_jpeg(message: str = "No active frame") -> bytes:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (960, 540), (25, 25, 25))
    draw = ImageDraw.Draw(img)
    draw.text((32, 32), message, fill=(240, 240, 240))
    draw.text((32, 64), datetime.now().isoformat(timespec="seconds"), fill=(180, 180, 180))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return buf.getvalue()


@app.route("/monitor")
def monitor_page() -> Response:
    alias = CFG["stb_alias"]
    return Response(
        f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Merged STB Monitor — {alias}</title>
  <style>
    body {{ margin:0; background:#101214; color:#f0f3f5; font-family:Segoe UI,Arial,sans-serif; }}
    header {{ padding:14px 18px; background:#191d21; display:flex; justify-content:space-between; align-items:center; }}
    main {{ display:grid; grid-template-columns: minmax(640px, 1fr) 360px; gap:16px; padding:16px; }}
    .card {{ background:#181c20; border:1px solid #2d333a; border-radius:14px; padding:14px; box-shadow:0 8px 24px rgba(0,0,0,.2); }}
    img.stream {{ width:100%; border-radius:10px; background:#000; }}
    button {{ background:#2b6cff; color:white; border:0; border-radius:10px; padding:10px 12px; margin:4px; cursor:pointer; font-weight:600; }}
    button.secondary {{ background:#34404c; }}
    button.warn {{ background:#b94b37; }}
    .grid3 {{ display:grid; grid-template-columns:repeat(3,1fr); gap:6px; }}
    .digits {{ display:grid; grid-template-columns:repeat(3,1fr); gap:6px; margin-top:10px; }}
    pre {{ white-space:pre-wrap; word-break:break-word; color:#b9c4cf; }}
    .pill {{ display:inline-block; padding:4px 8px; border-radius:999px; background:#27313b; }}
    .active {{ background:#1b7f45; }}
    .inactive {{ background:#7f2d1b; }}
  </style>
</head>
<body>
<header>
  <div><b>Merged Active Video + JAMboree Lite SGS</b> <span class="pill">STB: {alias}</span></div>
  <div id="signal" class="pill">checking…</div>
</header>
<main>
  <section class="card">
    <img class="stream" src="/video.mjpg" alt="live capture stream">
  </section>
  <aside class="card">
    <h2>Remote</h2>
    <div class="grid3">
      <span></span><button onclick="sendKey('up')">↑</button><span></span>
      <button onclick="sendKey('left')">←</button><button onclick="sendKey('select')">OK</button><button onclick="sendKey('right')">→</button>
      <span></span><button onclick="sendKey('down')">↓</button><span></span>
    </div>
    <p>
      <button onclick="sendKey('home')">Home</button>
      <button onclick="sendKey('guide')">Guide</button>
      <button onclick="sendKey('back')">Back</button>
      <button onclick="sendKey('info')">Info</button>
      <button onclick="sendKey('input')">Input</button>
    </p>
    <p>
      <button onclick="sendKey('ch_up')">CH +</button>
      <button onclick="sendKey('ch_down')">CH −</button>
      <button onclick="sendKey('recall')">Recall</button>
    </p>
    <div class="digits">
      <button onclick="sendKey('1')">1</button><button onclick="sendKey('2')">2</button><button onclick="sendKey('3')">3</button>
      <button onclick="sendKey('4')">4</button><button onclick="sendKey('5')">5</button><button onclick="sendKey('6')">6</button>
      <button onclick="sendKey('7')">7</button><button onclick="sendKey('8')">8</button><button onclick="sendKey('9')">9</button>
      <button onclick="sendKey('back')">Back</button><button onclick="sendKey('0')">0</button><button onclick="sendKey('select')">Enter</button>
    </div>
    <p>
      <input id="direct" placeholder="CH_206 or guide" style="width:190px;padding:10px;border-radius:8px;border:1px solid #444;background:#0f1113;color:white;">
      <button onclick="sendDirect()">Send</button>
    </p>
    <p>
      <button class="secondary" onclick="fetch('/monitor/start',{{method:'POST'}})">Start Video</button>
      <button class="warn" onclick="fetch('/monitor/stop',{{method:'POST'}})">Stop Video</button>
      <button class="secondary" onclick="fetch('/api/snapshot/save',{{method:'POST'}}).then(r=>r.json()).then(j=>alert(JSON.stringify(j,null,2)))">Save Snapshot</button>
      <button class="secondary" onclick="window.location='/crawl'">Autonomous Crawl</button>
    </p>
    <h3>Status</h3>
    <pre id="status">loading…</pre>
    <h3>Last command</h3>
    <pre id="last">none</pre>
  </aside>
</main>
<script>
async function sendKey(key) {{
  const r = await fetch('/send_key', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{key}})}});
  const j = await r.json();
  document.getElementById('last').textContent = JSON.stringify(j,null,2);
}}
function sendDirect() {{ const v=document.getElementById('direct').value; if(v) sendKey(v); }}
async function refresh() {{
  const r = await fetch('/api/status');
  const j = await r.json();
  const sig = document.getElementById('signal');
  sig.textContent = j.video.active ? 'video active' : 'no/weak video';
  sig.className = 'pill ' + (j.video.active ? 'active' : 'inactive');
  document.getElementById('status').textContent = JSON.stringify(j,null,2);
}}
setInterval(refresh, 1000); refresh();
</script>
</body>
</html>
""",
        mimetype="text/html",
    )


@app.route("/api/status")
def api_status():
    alias = str(CFG["stb_alias"])
    return jsonify(
        ok=True,
        config={k: v for k, v in CFG.items() if "pass" not in k.lower()},
        stb_alias=alias,
        stb=store.get(alias),
        jamboree_routes={
            "canonical_auto": f"/auto/{CFG['remote']}/{alias}/<button>/<delay>",
            "compat_send_key": "/send_key",
            "video_mjpeg": "/video.mjpg",
        },
        video=monitor.get_status(),
        crawler={k: v for k, v in crawler.status().items() if k != "recent_events"},
    )


@app.route("/api/active-video")
@app.route("/api/input/active")
def api_active_video():
    return jsonify(ok=True, video=monitor.get_status())


@app.route("/monitor/start", methods=["POST", "GET"])
def monitor_start():
    monitor.start()
    return jsonify(ok=True, video=monitor.get_status())


@app.route("/monitor/stop", methods=["POST", "GET"])
def monitor_stop():
    monitor.stop()
    return jsonify(ok=True, video=monitor.get_status())


@app.route("/snapshot.jpg")
def snapshot_jpg():
    jpg = monitor.get_jpeg() or placeholder_jpeg()
    return send_file(io.BytesIO(jpg), mimetype="image/jpeg", download_name="snapshot.jpg")


@app.route("/api/snapshot/save", methods=["POST", "GET"])
def save_snapshot():
    jpg = monitor.get_jpeg()
    if not jpg:
        return jsonify(ok=False, error="no frame available", video=monitor.get_status()), 503
    name = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    path = SNAPSHOT_DIR / name
    path.write_bytes(jpg)
    return jsonify(ok=True, file=str(path), bytes=len(jpg), video=monitor.get_status())


@app.route("/video.mjpg")
def video_mjpg():
    def stream():
        while True:
            jpg = monitor.get_jpeg() or placeholder_jpeg("Waiting for capture card frame")
            yield b"--frame\r\nContent-Type: image/jpeg\r\nCache-Control: no-cache\r\n\r\n" + jpg + b"\r\n"
            time.sleep(1.0 / 15.0)

    return Response(stream(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/send_key", methods=["POST", "GET"])
def compat_send_key():
    data = request.get_json(silent=True) or {}
    key = data.get("key") or request.args.get("key")
    delay_ms = data.get("delay_ms") or request.args.get("delay_ms") or CFG["default_delay_ms"]
    gap_s = float(data.get("gap_s", 0.2))
    if not key:
        return jsonify(ok=False, error="key is required"), 400
    try:
        seq = key_sequence_for(str(key))
        result = press_sequence(seq, delay_ms=int(delay_ms), gap_s=gap_s)
        result.update(requested_key=key, normalized_sequence=seq)
        return jsonify(result)
    except Exception as exc:
        log.exception("send_key failed")
        return jsonify(ok=False, error=str(exc), requested_key=key), 500


@app.route("/key/<path:key>", methods=["POST", "GET"])
def send_key_path(key: str):
    delay_ms = int(request.args.get("delay_ms", CFG["default_delay_ms"]))
    try:
        seq = key_sequence_for(key)
        result = press_sequence(seq, delay_ms=delay_ms)
        result.update(requested_key=key, normalized_sequence=seq)
        return jsonify(result)
    except Exception as exc:
        log.exception("key path failed")
        return jsonify(ok=False, error=str(exc), requested_key=key), 500


@app.route("/api/tune", methods=["POST", "GET"])
def api_tune():
    data = request.get_json(silent=True) or {}
    channel = data.get("channel") or request.args.get("channel")
    if channel is None:
        return jsonify(ok=False, error="channel is required"), 400
    try:
        ch = int(channel)
        seq = key_sequence_for(f"CH_{ch}")
        gap_s = float(data.get("gap_s", CFG.get("crawler_channel_digit_gap_s", 0.075)))
        result = press_sequence(seq, delay_ms=int(data.get("delay_ms", CFG["default_delay_ms"])), gap_s=gap_s)
        result.update(channel=ch, normalized_sequence=seq, gap_s=gap_s)
        return jsonify(result)
    except Exception as exc:
        log.exception("tune failed")
        return jsonify(ok=False, error=str(exc), channel=channel), 500


# Compatibility surface for NavigationMapBuilder/tune_verify style code.
@app.route("/screen")
def nmb_screen():
    video = monitor.get_status()
    return jsonify(
        input=CFG["capture_device"],
        channel=None,
        signal=bool(video.get("active")),
        audio=None,
        resolution=f"{video.get('width', 0)}x{video.get('height', 0)}",
        video=video,
        stb_alias=CFG["stb_alias"],
    )


@app.route("/key", methods=["POST"])
def nmb_key():
    data = request.get_json(force=True) or {}
    key = data.get("key")
    if not key:
        return jsonify(ok=False, error="key is required"), 400
    try:
        seq = key_sequence_for(str(key))
        result = press_sequence(seq, delay_ms=int(data.get("delay_ms", CFG["default_delay_ms"])))
        return jsonify(ok=True, key=key, normalized_sequence=seq, result=result, video=monitor.get_status())
    except Exception as exc:
        log.exception("NMB /key failed")
        return jsonify(ok=False, error=str(exc), key=key), 500


@app.route("/screenshot")
def nmb_screenshot():
    return snapshot_jpg()



@app.route("/crawl")
def crawler_page() -> Response:
    return Response(
        """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Autonomous STB Crawler</title>
  <style>
    body { margin:0; background:#101214; color:#f0f3f5; font-family:Segoe UI,Arial,sans-serif; }
    header { padding:14px 18px; background:#191d21; display:flex; justify-content:space-between; align-items:center; }
    main { display:grid; grid-template-columns:minmax(540px,1fr) minmax(420px,520px); gap:16px; padding:16px; }
    .card { background:#181c20; border:1px solid #2d333a; border-radius:14px; padding:14px; box-shadow:0 8px 24px rgba(0,0,0,.2); }
    img.stream { width:100%; border-radius:10px; background:#000; }
    button { background:#2b6cff; color:white; border:0; border-radius:10px; padding:10px 12px; margin:4px; cursor:pointer; font-weight:600; }
    button.secondary { background:#34404c; } button.warn { background:#b94b37; }
    input, textarea { width:100%; box-sizing:border-box; padding:10px; border-radius:8px; border:1px solid #444; background:#0f1113; color:white; }
    pre { white-space:pre-wrap; word-break:break-word; color:#b9c4cf; max-height:460px; overflow:auto; }
    .pill { display:inline-block; padding:4px 8px; border-radius:999px; background:#27313b; }
    .active { background:#1b7f45; } .inactive { background:#7f2d1b; }
    table { width:100%; border-collapse:collapse; } td,th { padding:6px; border-bottom:1px solid #2d333a; text-align:left; }
  </style>
</head>
<body>
<header>
  <div><b>Autonomous STB Crawler</b> <span class="pill">state graph learner</span></div>
  <div id="runpill" class="pill">idle</div>
</header>
<main>
  <section class="card">
    <h2>Live Input</h2>
    <img class="stream" src="/video.mjpg" alt="live capture stream">
    <p>
      <button onclick="startCrawl()">Start Crawl</button>
      <button class="warn" onclick="stopCrawl()">Stop</button>
      <button class="secondary" onclick="classifyNow()">Classify Current Screen</button>
      <button class="secondary" onclick="loadGraph()">Refresh Graph</button>
    </p>
    <p><b>Starting button / sequence</b> <span class="pill">optional</span></p>
    <input id="start_sequence" placeholder="Example: guide   or: home,guide" value="">
    <p style="color:#aab4bf;margin-top:6px;">This is pressed after HOME before learning the root screen. Use it to start from Guide, Menu, DVR, Apps, etc.</p>

    <p><b>Keys to explore</b></p>
    <input id="keys" value="up,down,left,right,guide,back,home,info,select">

    <p><b>Limits</b></p>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;">
      <label>Max steps<input id="max_steps" value="250"></label>
      <label>Max states<input id="max_states" value="80"></label>
      <label>Max depth<input id="max_depth" value="7"></label>
    </div>

    <p><b>Adaptive timing</b></p>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;">
      <label>Min settle s<input id="min_settle_s" value="0.35"></label>
      <label>Max settle s<input id="max_settle_s" value="3.5"></label>
      <label>Digit gap s<input id="channel_digit_gap_s" value="0.075"></label>
    </div>

    <p><b>Channel learning</b></p>
    <input id="channel_scan_list" value="200,205,206,207,208,209,210,220,230">
    <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-top:8px;">
      <label>Channel tune settle s<input id="channel_tune_settle_s" value="2.2"></label>
      <label>Channel suffix key<input id="channel_suffix_key" value="select"></label>
    </div>

    <p>
      <label><input id="self_explore" type="checkbox" checked> Self-explore with rewards for new menus, settings, features, and text</label><br>
      <label><input id="adaptive_timing" type="checkbox" checked> Dynamically learn button reaction timing</label><br>
      <label><input id="channel_learning" type="checkbox"> Learn channel numbers/names/symbols with direct number entry</label><br>
      <label><input id="allow_select" type="checkbox"> Allow SELECT on risky OCR screens</label><br>
      <label><input id="ocr_enabled" type="checkbox" checked> Use OCR if pytesseract/Tesseract are installed</label>
    </p>
  </section>
  <aside class="card">
    <h2>Status</h2>
    <pre id="status">loading…</pre>
    <h2>Graph Summary</h2>
    <pre id="graph">loading…</pre>
  </aside>
</main>
<script>
async function api(path, body) {
  const opts = body ? {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)} : {};
  const r = await fetch(path, opts); return await r.json();
}
async function startCrawl() {
  const body = {
    start_sequence: document.getElementById('start_sequence').value.split(/[\\s,]+/).map(x=>x.trim()).filter(Boolean),
    enabled_keys: document.getElementById('keys').value.split(',').map(x=>x.trim()).filter(Boolean),
    max_steps: parseInt(document.getElementById('max_steps').value || '250'),
    max_states: parseInt(document.getElementById('max_states').value || '80'),
    max_depth: parseInt(document.getElementById('max_depth').value || '7'),
    self_explore_enabled: document.getElementById('self_explore').checked,
    adaptive_timing_enabled: document.getElementById('adaptive_timing').checked,
    min_settle_s: parseFloat(document.getElementById('min_settle_s').value || '0.35'),
    max_settle_s: parseFloat(document.getElementById('max_settle_s').value || '3.5'),
    channel_learning_enabled: document.getElementById('channel_learning').checked,
    channel_scan_list: document.getElementById('channel_scan_list').value.split(',').map(x=>parseInt(x.trim())).filter(x=>!Number.isNaN(x)),
    channel_digit_gap_s: parseFloat(document.getElementById('channel_digit_gap_s').value || '0.075'),
    channel_tune_settle_s: parseFloat(document.getElementById('channel_tune_settle_s').value || '2.2'),
    channel_suffix_key: document.getElementById('channel_suffix_key').value.trim() || 'select',
    allow_select_on_dangerous_text: document.getElementById('allow_select').checked,
    ocr_enabled: document.getElementById('ocr_enabled').checked
  };
  document.getElementById('status').textContent = JSON.stringify(await api('/api/crawl/start', body), null, 2);
}
async function stopCrawl() { document.getElementById('status').textContent = JSON.stringify(await api('/api/crawl/stop', {}), null, 2); }
async function classifyNow() { document.getElementById('status').textContent = JSON.stringify(await api('/api/crawl/classify', {}), null, 2); loadGraph(); }
async function loadStatus() {
  const j = await api('/api/crawl/status');
  const pill = document.getElementById('runpill');
  pill.textContent = j.running ? 'running ' + j.steps + ' steps' : 'idle';
  pill.className = 'pill ' + (j.running ? 'active' : 'inactive');
  document.getElementById('status').textContent = JSON.stringify(j, null, 2);
}
async function loadGraph() {
  const j = await api('/api/crawl/graph');
  const summary = {
    root_state: j.root_state,
    node_count: Object.keys(j.nodes || {}).length,
    edge_count: Object.keys(j.edges || {}).length,
    nodes: Object.fromEntries(Object.entries(j.nodes || {}).slice(0, 12).map(([k,v]) => [k, {label:v.label, observations:v.observation_count, screenshot:v.representative && v.representative.screenshot}])),
    edges: Object.values(j.edges || {}).slice(0, 20).map(e => ({from:e.from_state, action:e.action, to:e.to_state, confidence:e.confidence, attempts:e.attempts, reward:e.samples && e.samples.length ? e.samples[e.samples.length-1].reward : undefined}))
  };
  document.getElementById('graph').textContent = JSON.stringify(summary, null, 2);
}
setInterval(loadStatus, 1500); loadStatus(); loadGraph();
</script>
</body>
</html>
""",
        mimetype="text/html",
    )


@app.route("/api/crawl/start", methods=["POST"])
def api_crawl_start():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(crawler.start(data))
    except Exception as exc:
        log.exception("crawl start failed")
        return jsonify(ok=False, error=str(exc), status=crawler.status()), 500


@app.route("/api/crawl/stop", methods=["POST", "GET"])
def api_crawl_stop():
    return jsonify(crawler.stop())


@app.route("/api/crawl/status")
def api_crawl_status():
    return jsonify(crawler.status())


@app.route("/api/crawl/graph")
def api_crawl_graph():
    return jsonify(crawler.graph.to_dict())


@app.route("/api/crawl/brain")
def api_crawl_brain():
    return jsonify(crawler.brain.to_dict())


@app.route("/api/crawl/channels")
def api_crawl_channels():
    return jsonify(ok=True, channels=crawler.brain.channel_summary())


@app.route("/api/crawl/classify", methods=["POST", "GET"])
def api_crawl_classify():
    try:
        return jsonify(crawler.classify_current())
    except Exception as exc:
        log.exception("crawl classify failed")
        return jsonify(ok=False, error=str(exc), status=crawler.status(), video=monitor.get_status()), 500


@app.route("/api/crawl/reset", methods=["POST"])
def api_crawl_reset():
    try:
        return jsonify(crawler.reset_graph())
    except Exception as exc:
        return jsonify(ok=False, error=str(exc), status=crawler.status()), 409


@app.route("/api/crawl/export")
def api_crawl_export():
    crawler.graph.save()
    return send_file(crawler.graph.graph_path, mimetype="application/json", download_name="nav_graph.json")


@app.route("/api/self-test")
def api_self_test():
    alias = str(CFG["stb_alias"])
    checks = {
        "base_file": Path(os.environ["JAMBOREE_BASE"]).is_file(),
        "stb_alias_present": store.get(alias) is not None,
        "video_thread_running": monitor.get_status().get("running", False),
        "video_enabled": monitor.get_status().get("enabled", False),
        "crawler_dir": CRAWLER_DIR.is_dir(),
        "crawler_graph_loaded": crawler.graph is not None,
    }
    return jsonify(ok=all(checks.values()), checks=checks, video=monitor.get_status(), stb=store.get(alias))


def main() -> None:
    host = str(CFG["server_host"])
    port = int(CFG["server_port"])
    log.info("Merged app starting on http://%s:%s/monitor", host, port)
    log.info("JAMBOREE_BASE=%s", os.environ.get("JAMBOREE_BASE"))
    log.info("Controlling STB alias=%s via remote=%s", CFG["stb_alias"], CFG["remote"])
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
