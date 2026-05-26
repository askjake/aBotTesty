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

from flask import Response, abort, jsonify, request, send_file  # noqa: E402

from capture_monitor import CaptureMonitor  # noqa: E402
from auto_crawler import AutonomousCrawler, CrawlerConfig  # noqa: E402
from focus_detector import detect_focus, draw_focus_overlay  # noqa: E402
from parental_control_agent import ParentalControlAgent  # noqa: E402
from manual_teaching_recorder import ManualTeachingRecorder  # noqa: E402
from dashboard_analytics import DashboardDataset  # noqa: E402
from human_playbooks import all_playbooks, playbooks_for_cues, backlog_from_graph  # noqa: E402
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
    "crawler_execution_mode": "balanced",
    "crawler_fast_known_path_enabled": True,
    "crawler_max_adaptive_observe_s": 1.8,
    "crawler_timing_outlier_clip_s": 4.0,
    "crawler_route_replay_gap_s": 0.075,
    "crawler_deep_ocr_every_n_steps": 6,
    "teacher_fast_recording_enabled": True,
    "teacher_burst_idle_s": 0.75,
    "crawler_channel_learning_enabled": False,
    "crawler_channel_scan_list": [200, 205, 206, 207, 208, 209, 210, 220, 230],
    "crawler_channel_digit_gap_s": 0.075,
    "crawler_channel_tune_settle_s": 2.2,
    "crawler_continuous_exploration_enabled": True,
    "crawler_continuous_idle_s": 2.0,
    "crawler_max_cycles": 0,
    "crawler_reseed_when_idle": True,
    "crawler_idle_reseed_every_cycles": 1,
    "crawler_anchor_sequences": [["back"], ["home"], ["home", "guide"], ["live"], ["guide"], ["home", "dvr"], ["home", "settings"], ["info"], ["options"], ["input"]],
    "crawler_max_action_attempts_per_state": 2,
    "crawler_reward_new_edge": 3.0,
    "crawler_reward_leads_to_unexplored": 4.0,
    "crawler_penalty_repeat_transition": -1.25,
    "crawler_penalty_same_state_loop": -2.0,
    "crawler_repeat_reward_floor_for_retry": 3.0,
    "crawler_curiosity_randomness": 0.12,
    "crawler_transition_sample_limit": 30,
    "crawler_flow_lane_card_w": 280,
    "crawler_flow_lane_card_h": 190,
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
    _dev = os.getenv("MERGED_CAPTURE_DEVICE", str(CFG["capture_device"]))
    # Keep as string if it looks like a URL, otherwise convert to int (device index)
    try:
        CFG["capture_device"] = int(_dev) if not _dev.startswith(("rtsp://", "rtmp://", "http://", "https://")) else _dev
    except ValueError:
        CFG["capture_device"] = _dev  # Keep as string (URL or path)
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
    seq = list(keys)
    for idx, key in enumerate(seq):
        sent.append(press_button(key, delay_ms=delay_ms))
        if idx < len(seq) - 1 and gap_s > 0:
            time.sleep(gap_s)
    return {"ok": True, "sent": sent, "count": len(sent), "gap_s": gap_s}


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
        gap_s=float(crawler.config.channel_digit_gap_s if is_channel and "crawler" in globals() else crawler.config.route_replay_gap_s if "crawler" in globals() else 0.075),
    )


def send_requested_key_direct(key: str, delay_ms: int | None = None, gap_s: float = 0.2) -> Dict[str, Any]:
    """Send a requested key through SGS without invoking teacher recursion."""
    seq = key_sequence_for(str(key))
    result = press_sequence(
        seq,
        delay_ms=int(delay_ms if delay_ms is not None else CFG["default_delay_ms"]),
        gap_s=float(gap_s),
    )
    result.update(requested_key=key, normalized_sequence=seq)
    return result


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
        execution_mode=str(CFG.get("crawler_execution_mode", "balanced")),
        fast_known_path_enabled=bool(CFG.get("crawler_fast_known_path_enabled", True)),
        max_adaptive_observe_s=float(CFG.get("crawler_max_adaptive_observe_s", 1.8)),
        timing_outlier_clip_s=float(CFG.get("crawler_timing_outlier_clip_s", 4.0)),
        route_replay_gap_s=float(CFG.get("crawler_route_replay_gap_s", 0.075)),
        deep_ocr_every_n_steps=int(CFG.get("crawler_deep_ocr_every_n_steps", 6)),
        channel_learning_enabled=bool(CFG.get("crawler_channel_learning_enabled", False)),
        channel_scan_list=list(CFG.get("crawler_channel_scan_list", [])),
        channel_digit_gap_s=float(CFG.get("crawler_channel_digit_gap_s", 0.075)),
        channel_tune_settle_s=float(CFG.get("crawler_channel_tune_settle_s", 2.2)),
        continuous_exploration_enabled=bool(CFG.get("crawler_continuous_exploration_enabled", True)),
        continuous_idle_s=float(CFG.get("crawler_continuous_idle_s", 2.0)),
        max_cycles=int(CFG.get("crawler_max_cycles", 0)),
        reseed_when_idle=bool(CFG.get("crawler_reseed_when_idle", True)),
        idle_reseed_every_cycles=int(CFG.get("crawler_idle_reseed_every_cycles", 1)),
        anchor_sequences=list(CFG.get("crawler_anchor_sequences", [["back"], ["home"], ["home", "guide"], ["live"], ["guide"]])),
        max_action_attempts_per_state=int(CFG.get("crawler_max_action_attempts_per_state", 2)),
        reward_new_edge=float(CFG.get("crawler_reward_new_edge", 3.0)),
        reward_leads_to_unexplored=float(CFG.get("crawler_reward_leads_to_unexplored", 4.0)),
        penalty_repeat_transition=float(CFG.get("crawler_penalty_repeat_transition", -1.25)),
        penalty_same_state_loop=float(CFG.get("crawler_penalty_same_state_loop", -2.0)),
        repeat_reward_floor_for_retry=float(CFG.get("crawler_repeat_reward_floor_for_retry", 3.0)),
        curiosity_randomness=float(CFG.get("crawler_curiosity_randomness", 0.12)),
        transition_sample_limit=int(CFG.get("crawler_transition_sample_limit", 30)),
        flow_lane_card_w=int(CFG.get("crawler_flow_lane_card_w", 280)),
        flow_lane_card_h=int(CFG.get("crawler_flow_lane_card_h", 190)),
    ),
)


parental_agent = ParentalControlAgent(crawler, CRAWLER_DIR)
teacher = ManualTeachingRecorder(
    data_dir=CRAWLER_DIR,
    crawler=crawler,
    capture_frame=monitor.get_frame,
    capture_status=monitor.get_status,
    send_requested_key=send_requested_key_direct,
)
teacher.fast_recording_enabled = bool(CFG.get("teacher_fast_recording_enabled", True))
teacher.burst_idle_s = float(CFG.get("teacher_burst_idle_s", 0.75))

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
      <button class="secondary" onclick="window.location='/teach'">Teacher Mode</button>
    </p>
    <div class="card" style="padding:10px;margin:10px 0;background:#11161b">
      <h3 style="margin-top:0">Teacher Recording</h3>
      <input id="teach_name" placeholder="feature/test name" style="width:190px;padding:8px;border-radius:8px;border:1px solid #444;background:#0f1113;color:white;">
      <button onclick="teachStart()">Start Recording</button>
      <button class="warn" onclick="teachStop()">Stop</button>
      <button class="secondary" onclick="teachExplore()">Explore from here</button>
      <div id="teach_pill" class="pill inactive">not recording</div>
      <pre id="teach_status">teacher loading…</pre>
    </div>
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
async function teachStart() {{ const name=document.getElementById('teach_name').value||'Manual feature demo'; const r=await fetch('/api/teach/start',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{name}})}}); document.getElementById('teach_status').textContent=JSON.stringify(await r.json(),null,2); }}
async function teachStop() {{ const r=await fetch('/api/teach/stop',{{method:'POST'}}); document.getElementById('teach_status').textContent=JSON.stringify(await r.json(),null,2); }}
async function teachExplore() {{ const r=await fetch('/api/teach/explore_from_here',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{max_steps:0,max_states:0,max_depth:18}})}}); document.getElementById('teach_status').textContent=JSON.stringify(await r.json(),null,2); }}
async function refreshTeach() {{ const r=await fetch('/api/teach/status'); const j=await r.json(); const p=document.getElementById('teach_pill'); p.textContent=j.active?'RECORDING':'not recording'; p.className='pill '+(j.active?'active':'inactive'); document.getElementById('teach_status').textContent=JSON.stringify({{active:j.active,latest_session:j.latest_session,last_error:j.last_error}},null,2); }}
async function refresh() {{
  const r = await fetch('/api/status');
  const j = await r.json();
  const sig = document.getElementById('signal');
  sig.textContent = j.video.active ? 'video active' : 'no/weak video';
  sig.className = 'pill ' + (j.video.active ? 'active' : 'inactive');
  document.getElementById('status').textContent = JSON.stringify(j,null,2);
}}
setInterval(refresh, 1000); setInterval(refreshTeach, 1500); refresh(); refreshTeach();
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
        teacher={k: v for k, v in teacher.status().items() if k != "active_session"},
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
        if teacher.active:
            learn_mode = str(data.get("learn_mode") or request.args.get("learn_mode") or ("fast" if teacher.fast_recording_enabled else "sync")).lower()
            if learn_mode in {"sync", "deep", "blocking"}:
                result = teacher.record_button(str(key), delay_ms=int(delay_ms), gap_s=gap_s)
            else:
                result = teacher.record_button_fast(str(key), delay_ms=int(delay_ms), gap_s=gap_s)
            result["sent_via_teacher"] = True
            result["learn_mode"] = learn_mode
            return jsonify(result)
        result = send_requested_key_direct(str(key), delay_ms=int(delay_ms), gap_s=gap_s)
        return jsonify(result)
    except Exception as exc:
        log.exception("send_key failed")
        return jsonify(ok=False, error=str(exc), requested_key=key), 500


@app.route("/key/<path:key>", methods=["POST", "GET"])
def send_key_path(key: str):
    delay_ms = int(request.args.get("delay_ms", CFG["default_delay_ms"]))
    try:
        if teacher.active:
            learn_mode = str(request.args.get("learn_mode") or ("fast" if teacher.fast_recording_enabled else "sync")).lower()
            if learn_mode in {"sync", "deep", "blocking"}:
                result = teacher.record_button(str(key), delay_ms=delay_ms, gap_s=0.2)
            else:
                result = teacher.record_button_fast(str(key), delay_ms=delay_ms, gap_s=float(request.args.get("gap_s", 0.075)))
            result["sent_via_teacher"] = True
            result["learn_mode"] = learn_mode
            return jsonify(result)
        result = send_requested_key_direct(str(key), delay_ms=delay_ms, gap_s=0.2)
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
        gap_s = float(data.get("gap_s", CFG.get("crawler_channel_digit_gap_s", 0.075)))
        requested = f"CH_{ch}"
        if teacher.active:
            learn_mode = str(data.get("learn_mode") or ("fast" if teacher.fast_recording_enabled else "sync")).lower()
            if learn_mode in {"sync", "deep", "blocking"}:
                result = teacher.record_button(requested, delay_ms=int(data.get("delay_ms", CFG["default_delay_ms"])), gap_s=gap_s)
            else:
                result = teacher.record_button_fast(requested, delay_ms=int(data.get("delay_ms", CFG["default_delay_ms"])), gap_s=gap_s)
            result.update(channel=ch, sent_via_teacher=True, learn_mode=learn_mode)
            return jsonify(result)
        result = send_requested_key_direct(requested, delay_ms=int(data.get("delay_ms", CFG["default_delay_ms"])), gap_s=gap_s)
        result.update(channel=ch, gap_s=gap_s)
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




@app.route("/intelligence")
@app.route("/crawl")
def crawler_page() -> Response:
    return Response(
        r"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>STB Intelligence Console v8</title>
  <style>
    :root { --bg:#070a0f; --panel:#111821; --panel2:#17212c; --panel3:#1d2a37; --line:#2d3b4b; --text:#eef6ff; --muted:#9db0c3; --good:#34d399; --warn:#fbbf24; --bad:#fb7185; --blue:#60a5fa; --violet:#a78bfa; --cyan:#67e8f9; }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--bg); color:var(--text); font-family:Segoe UI,Arial,sans-serif; }
    header { padding:14px 18px; background:#0f1620; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; align-items:center; gap:16px; position:sticky; top:0; z-index:20; }
    h1 { margin:0; font-size:20px; } h2 { margin:0 0 10px 0; font-size:16px; } h3 { margin:12px 0 8px 0; font-size:14px; color:#d7e3ee; }
    main { display:grid; grid-template-columns: 390px minmax(760px,1fr) 430px; gap:14px; padding:14px; }
    .card { background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:14px; box-shadow:0 14px 34px rgba(0,0,0,.22); }
    .stack { display:flex; flex-direction:column; gap:14px; }
    .metrics { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }
    .metric { background:var(--panel2); border:1px solid var(--line); border-radius:12px; padding:9px; }
    .metric b { display:block; font-size:18px; color:#fff; }
    .metric span { color:var(--muted); font-size:11px; }
    label { display:block; color:#cfdae5; font-size:12px; margin-top:8px; }
    input, textarea, select { width:100%; margin-top:4px; padding:8px; border-radius:10px; background:#081018; color:var(--text); border:1px solid #344456; }
    textarea { min-height:54px; resize:vertical; }
    button { cursor:pointer; border:1px solid #36506a; background:#1c3045; color:white; border-radius:10px; padding:8px 10px; margin:4px 4px 4px 0; }
    button:hover { filter:brightness(1.15); } button.primary { background:#155e75; } button.good { background:#166534; } button.bad { background:#7f1d1d; } button.warn { background:#854d0e; }
    .pill { padding:6px 10px; border-radius:999px; border:1px solid var(--line); font-size:12px; } .active { background:#073b2a; color:#a7f3d0; } .inactive { background:#301a22; color:#fecdd3; }
    .hint { color:var(--muted); font-size:12px; line-height:1.35; }
    .tabs { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:10px; } .tab { padding:7px 10px; border-radius:999px; background:#0b1118; border:1px solid var(--line); cursor:pointer; } .tab.on { background:#1d4ed8; }
    .hidden { display:none; }
    pre { background:#071018; border:1px solid var(--line); border-radius:10px; padding:10px; overflow:auto; max-height:330px; font-size:12px; }
    table { width:100%; border-collapse:collapse; font-size:12px; } td,th { border-bottom:1px solid #263443; padding:5px; text-align:left; } th { color:#cbd5e1; }

    .mapTools { display:flex; flex-wrap:wrap; align-items:center; gap:8px; margin-bottom:10px; }
    .mapWrap { height:760px; overflow:auto; background:radial-gradient(circle at 20% 20%,#101b2a,#06090e 70%); border:1px solid var(--line); border-radius:16px; position:relative; }
    svg { min-width:1200px; min-height:900px; display:block; }
    .laneLabel { fill:#93a4b8; font-size:13px; font-weight:700; opacity:.75; }
    .edge { fill:none; stroke:#93a4b8; stroke-width:2.2; marker-end:url(#arrow); opacity:.75; }
    .edge.good { stroke:var(--good); } .edge.warn { stroke:var(--warn); } .edge.bad { stroke:var(--bad); }
    .edgeLabelBg { fill:#071018; stroke:#243447; stroke-width:1; rx:8; opacity:.95; }
    .edgeLabel { fill:#dbeafe; font-size:12px; pointer-events:none; }
    .node rect { stroke:#405164; fill:#121c26; stroke-width:1.5; filter:drop-shadow(0 10px 12px rgba(0,0,0,.25)); }
    .node.current rect { stroke:#67e8f9; stroke-width:3; }
    .node.selected rect { stroke:#fbbf24; stroke-width:3; }
    .node.menu rect { fill:#102033; } .node.settings rect { fill:#221c36; } .node.channel rect { fill:#0e2a24; } .node.risky rect { fill:#33131d; }
    .node text { fill:#f8fbff; font-size:12px; pointer-events:none; } .node .title { font-size:13px; font-weight:700; } .node .sub { fill:#a9bacb; font-size:11px; }
    .node .badge { fill:#0a1118; stroke:#304256; stroke-width:1; } .node .badgeText { fill:#d7e3ee; font-size:10px; }
    .thumbBorder { fill:#071018; stroke:#2b3c4f; stroke-width:1; }

    .transitionList { display:grid; grid-template-columns:repeat(auto-fill,minmax(520px,1fr)); gap:12px; }
    .transitionCard { background:#0d141d; border:1px solid var(--line); border-radius:14px; padding:10px; }
    .transitionGrid { display:grid; grid-template-columns:1fr 118px 1fr; gap:10px; align-items:center; }
    .screenMini { border:1px solid #314458; border-radius:12px; overflow:hidden; background:#071018; min-height:132px; }
    .screenMini img { width:100%; height:112px; object-fit:cover; display:block; }
    .screenMini div { padding:7px; font-size:12px; color:#d8e5f0; }
    .arrowBox { text-align:center; color:#dbeafe; }
    .arrowBox .btnName { font-size:18px; font-weight:800; color:#fff; }
    .arrowBox .seq { color:#9fb0bf; font-size:11px; word-break:break-word; }
    .rewardGood { color:#86efac; } .rewardBad { color:#fca5a5; } .rewardWarn { color:#fde68a; }
    #selected_img { width:100%; max-height:220px; object-fit:contain; border:1px solid var(--line); border-radius:12px; background:#05080c; }
    .focusPill { display:inline-block; margin:3px 4px 3px 0; padding:3px 7px; border-radius:999px; background:#3b1116; color:#fecdd3; border:1px solid #7f1d1d; font-size:11px; }
    .focusBox { margin-top:8px; padding:8px; background:#100b0b; border:1px solid #5f2028; border-radius:10px; color:#ffd6d6; }
  </style>
</head>
<body>
<header>
  <h1>STB Intelligence Console <span class="hint">v9 · semantic focus/context + title-aware learning map</span></h1>
  <div><span id="runpill" class="pill inactive">idle</span> <a href="/monitor" style="color:#93c5fd">monitor</a> · <a href="/parental" style="color:#93c5fd">parental lab</a> · <a href="/api/crawl/export" style="color:#93c5fd">export graph</a></div>
</header>
<main>
<section class="stack">
  <div class="card">
    <h2>Continuous explorer</h2>
    <div class="hint">Set max steps to <b>0</b> for endless exploration. It scores each state/button pair, retries useful hallways, and penalizes loops unless they lead to new rooms.</div>
    <label>Starting button / sequence</label><input id="start_sequence" placeholder="home, guide or apps">
    <label>Buttons to explore</label><textarea id="enabled_keys">up,down,left,right,guide,back,home,info,select,live,recall,input,diamond,ddiamond,options</textarea>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
      <label>Max steps<input id="max_steps" type="number" value="0"></label>
      <label>Max states<input id="max_states" type="number" value="350"></label>
      <label>Max depth<input id="max_depth" type="number" value="18"></label>
      <label>Attempts/action<input id="max_action_attempts_per_state" type="number" value="3"></label>
      <label>Idle sweep seconds<input id="continuous_idle_s" type="number" step="0.1" value="1.5"></label>
      <label>Curiosity<input id="curiosity_randomness" type="number" step="0.01" value="0.14"></label>
      <label>Max cycles<input id="max_cycles" type="number" value="0"></label>
      <label>Reseed every cycles<input id="idle_reseed_every_cycles" type="number" value="1"></label>
    </div>
    <label>Idle/reseed anchor sequences <span class="hint">semicolon separated</span></label><textarea id="anchor_sequences">back; home; home,guide; live; guide; home,dvr; home,settings; info; options; input</textarea>
    <label><input id="continuous_exploration_enabled" type="checkbox" checked style="width:auto"> Continually explore until stopped</label>
    <label><input id="reseed_when_idle" type="checkbox" checked style="width:auto"> When frontier runs dry, actively reseed from Home/Guide/Live/etc.</label>
    <label><input id="self_explore_enabled" type="checkbox" checked style="width:auto"> Rewarded self-exploration</label>
    <label><input id="adaptive_timing_enabled" type="checkbox" checked style="width:auto"> Learn button response timing</label>
    <label><input id="allow_select_on_dangerous_text" type="checkbox" style="width:auto"> Allow risky SELECT screens</label>
    <button class="good" onclick="startCrawl()">Start / continue exploring</button><button class="bad" onclick="stopCrawl()">Stop</button><button onclick="classifyNow()">Classify current screen</button><button onclick="focusNow()">Detect focus/context</button><button onclick="enrichContext()">Enrich saved graph context</button>
  </div>

  <div class="card">
    <h2>Channel learning</h2>
    <label>Channels</label><textarea id="channel_scan_list">200,205,206,207,208,209,210,220,230</textarea>
    <label><input id="channel_learning_enabled" type="checkbox" style="width:auto"> Scan channels on next crawl start</label>
    <label>Digit gap seconds<input id="channel_digit_gap_s" type="number" step="0.005" value="0.075"></label>
  </div>

  <div class="card">
    <h2>Coverage</h2>
    <div class="metrics">
      <div class="metric"><b id="m_nodes">0</b><span>states</span></div>
      <div class="metric"><b id="m_edges">0</b><span>edges</span></div>
      <div class="metric"><b id="m_trans">0</b><span>transitions</span></div>
      <div class="metric"><b id="m_cov">0%</b><span>coverage</span></div>
      <div class="metric"><b id="m_remaining">0</b><span>remaining</span></div>
      <div class="metric"><b id="m_discoveries">0</b><span>discoveries</span></div>
      <div class="metric"><b id="m_reach">0</b><span>reachable</span></div>
      <div class="metric"><b id="m_current">—</b><span>current</span></div>
    </div>
    <pre id="brain_notes"></pre>
  </div>
</section>

<section class="stack">
  <div class="card">
    <div class="mapTools">
      <h2 style="margin-right:auto">Readable learned flowchart</h2>
      <button onclick="setView('flow')">Flowchart</button><button onclick="setView('transitions')">Before/Button/After</button><button onclick="setView('frontier')">Frontier</button>
      <button onclick="zoom(0.85)">−</button><button onclick="zoom(1.15)">+</button><button onclick="fitTop()">Top</button><button onclick="refreshAll()">Refresh</button>
    </div>
    <div id="flowView" class="mapWrap"><svg id="mapSvg"></svg></div>
    <div id="transitionView" class="hidden"><div class="hint" style="margin-bottom:10px">Every card is the causal memory: <b>before screen → exact button/sequence → after screen</b>.</div><div id="transitionList" class="transitionList"></div></div>
    <div id="frontierView" class="hidden"><div id="frontierList" class="transitionList"></div></div>
  </div>
</section>

<section class="stack">
  <div class="card">
    <h2>Selected screen / route test</h2>
    <img id="selected_img" alt="selected screen">
    <div id="selected_text" class="hint">Click a screen card in the map.</div>
    <label>Target state</label><input id="target_state">
    <label>Or search learned menus/settings</label><input id="target_query" placeholder="settings, captions, audio, guide">
    <label>Or channel</label><input id="target_channel" placeholder="206">
    <button onclick="planRoute()">Plan route</button><button class="primary" onclick="navigateTarget()">Navigate there</button><button onclick="tuneChannel()">Tune channel</button>
    <pre id="route_result"></pre>
  </div>

  <div class="card">
    <h2>Human-like settings goal</h2>
    <div class="hint">It will route to the best learned screen, then run only the final sequence you explicitly provide.</div>
    <label>Goal screen</label><input id="goal_query" placeholder="caption settings">
    <label>Desired value / note</label><input id="goal_value" placeholder="captions on">
    <label>Final sequence after reaching screen</label><input id="goal_sequence" placeholder="down,select">
    <button onclick="goalDryRun()">Dry run</button><button class="warn" onclick="goalExecute()">Execute goal</button>
  </div>

  <div class="card">
    <div class="tabs"><span id="tab_conf" class="tab on" onclick="showTab('conf')">Confidence</span><span id="tab_channels" class="tab" onclick="showTab('channels')">Channels</span><span id="tab_events" class="tab" onclick="showTab('events')">Events</span><span id="tab_json" class="tab" onclick="showTab('json')">JSON</span></div>
    <div id="panel_conf"><div id="confidence_table"></div></div>
    <div id="panel_channels" class="hidden"><div id="channels_table"></div></div>
    <div id="panel_events" class="hidden"><pre id="events"></pre></div>
    <div id="panel_json" class="hidden"><pre id="status"></pre></div>
  </div>
</section>
</main>
<script>
let MAP={nodes:[],edges:[],transitions:[]}, selectedNode=null, scale=1, view='flow';
const qs=id=>document.getElementById(id);
function esc(s){return String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
function short(s,n=38){s=String(s||''); return s.length>n?s.slice(0,n-1)+'…':s;}
function seqVal(id){return qs(id).value.split(/[ ,]+/).map(x=>x.trim()).filter(Boolean);}
async function api(url, body){const opt=body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{}; const r=await fetch(url,opt); return await r.json();}
function crawlBody(){return {start_sequence:seqVal('start_sequence'), enabled_keys:seqVal('enabled_keys'), max_steps:+qs('max_steps').value, max_states:+qs('max_states').value, max_depth:+qs('max_depth').value, max_action_attempts_per_state:+qs('max_action_attempts_per_state').value, continuous_idle_s:+qs('continuous_idle_s').value, curiosity_randomness:+qs('curiosity_randomness').value, max_cycles:+qs('max_cycles').value, idle_reseed_every_cycles:+qs('idle_reseed_every_cycles').value, anchor_sequences:qs('anchor_sequences').value, continuous_exploration_enabled:qs('continuous_exploration_enabled').checked, reseed_when_idle:qs('reseed_when_idle').checked, self_explore_enabled:qs('self_explore_enabled').checked, adaptive_timing_enabled:qs('adaptive_timing_enabled').checked, allow_select_on_dangerous_text:qs('allow_select_on_dangerous_text').checked, channel_learning_enabled:qs('channel_learning_enabled').checked, channel_scan_list:qs('channel_scan_list').value, channel_digit_gap_s:+qs('channel_digit_gap_s').value};}
async function startCrawl(){qs('status').textContent=JSON.stringify(await api('/api/crawl/start', crawlBody()),null,2); setTimeout(refreshAll,900)}
async function stopCrawl(){qs('status').textContent=JSON.stringify(await api('/api/crawl/stop',{}),null,2); setTimeout(refreshAll,600)}
async function classifyNow(){qs('route_result').textContent=JSON.stringify(await api('/api/crawl/classify',{}),null,2); setTimeout(refreshAll,600)}
async function focusNow(){qs('route_result').textContent=JSON.stringify(await api('/api/crawl/focus',{}),null,2); setTimeout(refreshAll,600)}
async function enrichContext(){qs('route_result').textContent='Enriching saved screenshots with v9 context...'; qs('route_result').textContent=JSON.stringify(await api('/api/crawl/enrich_context',{max_nodes:0}),null,2); setTimeout(refreshAll,800)}
function nodeClass(kind){return ['node',kind||'screen'].join(' ')}
function edgeClass(c){return c>.72?'good':c>.38?'warn':'bad'}
function rewardClass(r){r=Number(r||0); return r>2?'rewardGood':r<0?'rewardBad':'rewardWarn'}
function renderMap(map){
  MAP=map; qs('m_nodes').textContent=map.node_count||0; qs('m_edges').textContent=map.edge_count||0; qs('m_trans').textContent=map.transition_count||0; qs('m_reach').textContent=map.reachable_from_root||0; qs('m_current').textContent=(map.current_state||'—').replace('screen_','').replace('root_','root:');
  const cov=map.coverage||{}; qs('m_cov').textContent=(cov.completion_pct??0)+'%'; qs('m_remaining').textContent=cov.remaining_state_actions??0; qs('m_discoveries').textContent=cov.discoveries??0;
  const svg=qs('mapSvg'), nodes=map.nodes||[], edges=map.edges||[], by=Object.fromEntries(nodes.map(n=>[n.id,n]));
  let maxX=1200,maxY=900; nodes.forEach(n=>{maxX=Math.max(maxX,n.x+(n.w||280)+120); maxY=Math.max(maxY,n.y+(n.h||190)+120)}); svg.setAttribute('viewBox',`0 0 ${maxX} ${maxY}`); svg.style.width=(maxX*scale)+'px'; svg.style.height=(maxY*scale)+'px';
  let html='<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="#94a3b8"/></marker></defs>';
  const lanes={}; nodes.forEach(n=>{lanes[n.lane]=n.lane_label||('Lane '+n.lane)}); Object.entries(lanes).forEach(([lane,label])=>{const x=80+(+lane)*(map.layout?.x_gap||370); html+=`<text class="laneLabel" x="${x}" y="44">${esc(label)}</text><line x1="${x-28}" y1="58" x2="${x-28}" y2="${maxY-40}" stroke="#1e293b" stroke-width="1"/>`;});
  edges.forEach(e=>{const a=by[e.from], b=by[e.to]; if(!a||!b)return; const aw=a.w||280, ah=a.h||190, bw=b.w||280, bh=b.h||190; let path,lx,ly; const ci=e.curve_index||0, bend=(ci%5)*24*(ci%2?-1:1); if(e.is_self_loop||e.from===e.to){const x=a.x+aw-8,y=a.y+ah/2; path=`M ${x} ${y} C ${x+120} ${y-100}, ${x+150} ${y+110}, ${x} ${y+80}`; lx=x+78; ly=y-10+bend;} else {const x1=a.x+aw, y1=a.y+ah/2, x2=b.x, y2=b.y+bh/2; const midX=(x1+x2)/2+bend; path=`M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`; lx=midX-46; ly=(y1+y2)/2-9;} const r=(e.avg_state_action_reward??e.reward??0); const lab=`${e.action} · c:${(e.confidence||0).toFixed(2)} · r:${Number(r||0).toFixed(1)} · ${e.attempts||0}x`; html+=`<path class="edge ${edgeClass(e.confidence||0)}" d="${path}"></path><rect class="edgeLabelBg" x="${lx-6}" y="${ly-15}" width="${Math.max(120,lab.length*6.3)}" height="22" rx="8"></rect><text class="edgeLabel" x="${lx}" y="${ly}">${esc(lab)}</text>`;});
  nodes.forEach(n=>{const selected=selectedNode&&selectedNode.id===n.id?' selected':''; const current=map.current_state===n.id?' current':''; const w=n.w||280,h=n.h||190; const img=n.image_url?`<rect class="thumbBorder" x="10" y="10" width="150" height="86" rx="8"></rect><image href="${esc(n.image_url)}" x="11" y="11" width="148" height="84" preserveAspectRatio="xMidYMid slice"></image>`:''; const rem=n.remaining_count??0; const title=short(n.human_label||n.label||n.screen_title||n.id,30); html+=`<g class="${nodeClass(n.kind)}${selected}${current}" data-id="${esc(n.id)}" transform="translate(${n.x},${n.y})" onclick="selectNode('${esc(n.id)}')"><rect rx="16" width="${w}" height="${h}"></rect>${img}<text class="title" x="172" y="24">${esc(title)}</text><text class="sub" x="172" y="44">${esc(n.kind)} · conf ${(n.confidence||0).toFixed(2)}</text><text class="sub" x="172" y="62">obs ${n.observations} · rem ${rem}</text><text class="sub" x="172" y="80">frontier ${(n.frontier_score||0).toFixed(1)}</text><rect class="badge" x="10" y="108" width="${w-20}" height="24" rx="8"></rect><text class="badgeText" x="20" y="124">${esc(short(n.human_label||n.focus_label||n.screen_title||((n.ocr_tokens||[]).slice(0,9).join(' ')),44))}</text><text class="sub" x="12" y="154">${esc(short(n.id,42))}</text><text class="sub" x="12" y="174">${esc((n.channels||[]).length?'channels: '+n.channels.map(c=>c.channel).join(', '):'')}</text></g>`;});
  svg.innerHTML=html; renderTransitions(map.transitions||[]); renderFrontier(nodes); renderConfidence(map.action_confidence||{}); renderChannels(map.channels||{});
}
function renderTransitions(items){let html=''; (items||[]).forEach(t=>{const r=t.avg_state_action_reward??t.reward??0; html+=`<div class="transitionCard"><div class="transitionGrid"><div class="screenMini">${t.before?.image_url?`<img src="${esc(t.before.image_url)}">`:''}<div><b>Before</b><br>${esc(short(t.before?.label||t.before_state,70))}<br><span class="hint">${esc(short(t.before_state,36))}</span></div></div><div class="arrowBox"><div class="btnName">${esc(t.button)}</div><div style="font-size:32px">→</div><div class="seq">${esc((t.button_sequence||[]).join(' · '))}</div><div class="${rewardClass(r)}">reward ${Number(r||0).toFixed(2)}</div><div class="hint">conf ${(t.confidence||0).toFixed(2)} · ${t.attempts||0}x</div></div><div class="screenMini">${t.after?.image_url?`<img src="${esc(t.after.image_url)}">`:''}<div><b>After</b><br>${esc(short(t.after?.label||t.after_state,70))}<br><span class="hint">${esc(short(t.after_state,36))}</span></div></div></div><div class="hint" style="margin-top:8px">focus: ${esc(short(t.before?.human_label||(t.ocr_delta||{}).before_focus||'',55))} → ${esc(short(t.after?.human_label||(t.ocr_delta||{}).after_focus||'',55))}<br>new: ${esc(short(((t.ocr_delta||{}).new_tokens||[]).join(' '),120))} · response ${t.response_s??'?'}s · reversible ${esc(t.reversible_with||'unknown')}</div></div>`}); qs('transitionList').innerHTML=html || '<div class="hint">No transitions learned yet.</div>';}
function renderFrontier(nodes){const arr=[...(nodes||[])].sort((a,b)=>(b.remaining_count-a.remaining_count)||((b.frontier_score||0)-(a.frontier_score||0))).slice(0,30); let html=''; arr.forEach(n=>{html+=`<div class="transitionCard"><div style="display:flex;gap:10px"><div class="screenMini" style="width:180px">${n.image_url?`<img src="${esc(n.image_url)}">`:''}<div>${esc(short(n.label,50))}</div></div><div><b>${esc(n.kind)}</b><br><span class="focusPill">focus: ${esc(short(n.focus_label||'unknown',48))}</span><br>remaining: ${(n.remaining_actions||[]).map(esc).join(', ')}<br>confidence ${(n.confidence||0).toFixed(2)} · observations ${n.observations}<br><button onclick="selectNode('${esc(n.id)}');navigateTarget()">Test navigate</button></div></div></div>`}); qs('frontierList').innerHTML=html || '<div class="hint">No frontier left under current limits.</div>';}
function focusHtml(f){if(!f)return '<div class="focusBox">No focus/context data yet.</div>'; const ui=f.ui_context||{}; const title=f.screen_title||ui.screen_title||''; const item=f.focused_item||ui.focused_item||f.label_text||f.focus_text||''; const value=f.focused_value||ui.focused_value||''; const role=f.focus_role||ui.focus_role||''; const pairs=f.setting_pairs||ui.setting_pairs||[]; const risks=f.risk_flags||ui.risk_flags||[]; const tags=f.semantic_tags||ui.semantic_tags||[]; if(!f.found&&!title)return '<div class="focusBox">Focus not detected yet.</div>'; return `<div class="focusBox"><b>${esc(short(title||'Focused region',90))}</b><br>item: ${esc(short(item||'',120))}${value?' = '+esc(short(value,50)):''}<br>role: ${esc(role||'')} · focus conf ${Number(f.confidence||0).toFixed(2)} · context conf ${Number(f.context_confidence||ui.context_confidence||0).toFixed(2)}<br>row: ${esc(short(f.row_text||ui.row_text||'',220))}<br>pairs: ${esc(short((pairs||[]).map(p=>(p.label||'')+'='+ (p.value||'')).join(' · '),180))}<br>tags: ${esc((tags||[]).join(', '))}${risks.length?' · risks: '+esc(risks.join(', ')):''}</div>`;}
function selectNode(id){selectedNode=(MAP.nodes||[]).find(n=>n.id===id); qs('target_state').value=id; if(selectedNode){qs('selected_img').src=selectedNode.image_url||''; qs('selected_text').innerHTML=`<b>${esc(selectedNode.label||id)}</b><br>${esc(selectedNode.kind)} · title ${esc(selectedNode.screen_title||'')} · confidence ${(selectedNode.confidence||0).toFixed(3)} · remaining ${(selectedNode.remaining_actions||[]).join(', ')}<br>${focusHtml(selectedNode.focus)}<br><b>OCR</b><br>${esc(short(selectedNode.ocr_text||'',700))}`;} renderMap(MAP);}
function setView(v){view=v; qs('flowView').className=v==='flow'?'mapWrap':'hidden'; qs('transitionView').className=v==='transitions'?'':'hidden'; qs('frontierView').className=v==='frontier'?'':'hidden';}
function zoom(f){scale=Math.max(.35,Math.min(2.2,scale*f)); renderMap(MAP)} function fitTop(){qs('flowView').scrollTo({left:0,top:0,behavior:'smooth'});}
async function loadStatus(){const j=await api('/api/crawl/status'); const cont=j.config&&j.config.continuous_exploration_enabled; qs('runpill').textContent=j.running?(cont?'continuous ':'running ')+j.steps+' steps':'idle'+(j.last_stop_reason?' · '+j.last_stop_reason:''); qs('runpill').className='pill '+(j.running?'active':'inactive'); qs('status').textContent=JSON.stringify(j,null,2); qs('events').textContent=JSON.stringify(j.recent_events||[],null,2); const learning=j.learning||{}; qs('brain_notes').textContent=JSON.stringify({stop_reason:j.last_stop_reason,last_error:j.last_error,coverage:learning.coverage, known_concepts:learning.known_concepts, known_titles:learning.known_menu_titles, known_focus_items:(learning.known_focus_items||[]).slice(0,20), known_setting_pairs:(learning.known_setting_pairs||[]).slice(0,20), known_token_count:learning.known_token_count, graph_file:j.graph_file, brain_file:j.brain_file},null,2);}
async function loadMap(){const j=await api('/api/crawl/map'); renderMap(j);} 
function renderConfidence(rows){let arr=Object.values(rows); if(!arr.length){qs('confidence_table').innerHTML='<span class="hint">No transitions learned yet.</span>';return;} let html='<table><tr><th>button</th><th>conf</th><th>attempts</th><th>noop</th><th>avg s</th><th>reward</th></tr>'; arr.slice(0,26).forEach(r=>html+=`<tr><td>${esc(r.action)}</td><td>${r.confidence}</td><td>${r.attempts}</td><td>${r.noops}</td><td>${r.avg_response_s??''}</td><td>${r.avg_reward??''}</td></tr>`); qs('confidence_table').innerHTML=html+'</table>';}
function renderChannels(rows){let arr=Object.values(rows); if(!arr.length){qs('channels_table').innerHTML='<span class="hint">No channels learned yet.</span>';return;} let html='<table><tr><th>ch</th><th>name guess</th><th>symbols</th><th>conf</th><th>go</th></tr>'; arr.forEach(r=>html+=`<tr><td>${r.channel}</td><td>${esc(r.name_guess||'')}</td><td>${esc((r.symbols||[]).join(','))}</td><td>${r.confidence}</td><td><button onclick="tuneChannel(${r.channel})">Tune</button></td></tr>`); qs('channels_table').innerHTML=html+'</table>';}
async function planRoute(){const body={target_state:qs('target_state').value.trim()||undefined, query:qs('target_query').value.trim()||undefined}; const ch=parseInt(qs('target_channel').value.trim()); if(!Number.isNaN(ch)) body.channel=ch; qs('route_result').textContent=JSON.stringify(await api('/api/crawl/plan',body),null,2);}
async function navigateTarget(){const body={target_state:qs('target_state').value.trim()||undefined, query:qs('target_query').value.trim()||undefined, dry_run:false}; qs('route_result').textContent=JSON.stringify(await api('/api/crawl/navigate',body),null,2); setTimeout(refreshAll,800)}
async function tuneChannel(ch){let channel=ch||parseInt(qs('target_channel').value.trim()); if(Number.isNaN(channel)){alert('Enter a channel number'); return;} qs('route_result').textContent=JSON.stringify(await api('/api/crawl/navigate',{channel:channel,dry_run:false}),null,2); setTimeout(refreshAll,1000)}
async function goalDryRun(){const body={query:qs('goal_query').value, desired_value:qs('goal_value').value, final_sequence:seqVal('goal_sequence'), dry_run:true}; qs('route_result').textContent=JSON.stringify(await api('/api/crawl/goal',body),null,2);}
async function goalExecute(){const body={query:qs('goal_query').value, desired_value:qs('goal_value').value, final_sequence:seqVal('goal_sequence'), dry_run:false}; qs('route_result').textContent=JSON.stringify(await api('/api/crawl/goal',body),null,2); setTimeout(refreshAll,1000)}
function showTab(name){['conf','channels','events','json'].forEach(t=>{qs('panel_'+t).className=t===name?'':'hidden'; qs('tab_'+t).className='tab '+(t===name?'on':'');});}
async function refreshAll(){await loadStatus(); await loadMap();}
setInterval(loadStatus,1500); setInterval(loadMap,7000); refreshAll();
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


@app.route("/api/crawl/focus", methods=["POST", "GET"])
def api_crawl_focus():
    try:
        return jsonify(crawler.analyze_focus_current())
    except Exception as exc:
        log.exception("focus detection failed")
        return jsonify(ok=False, error=str(exc), status=crawler.status(), video=monitor.get_status()), 500


@app.route("/api/crawl/enrich_context", methods=["POST", "GET"])
def api_crawl_enrich_context():
    try:
        data = request.get_json(silent=True) or {}
        return jsonify(crawler.enrich_existing_context(int(data.get("max_nodes") or 0)))
    except Exception as exc:
        log.exception("context enrichment failed")
        return jsonify(ok=False, error=str(exc), status=crawler.status(), video=monitor.get_status()), 500


@app.route("/api/crawl/review_context_quality", methods=["POST", "GET"])
def api_crawl_review_context_quality():
    try:
        data = request.get_json(silent=True) or {}
        max_nodes = int(data.get("max_nodes") or request.args.get("max_nodes") or 0)
        auto_enrich = str(data.get("auto_enrich", request.args.get("auto_enrich", "false"))).lower() in {"1", "true", "yes", "on"}
        return jsonify(crawler.review_context_quality(max_nodes=max_nodes, auto_enrich=auto_enrich))
    except Exception as exc:
        log.exception("context quality review failed")
        return jsonify(ok=False, error=str(exc), status=crawler.status()), 500


@app.route("/teach")
def teach_page() -> Response:
    alias = CFG["stb_alias"]
    html = """
<!doctype html>
<html>
<head>
<meta charset="utf-8"><title>Teacher Mode — __ALIAS__</title>
<style>
body { margin:0; background:#0d1117; color:#e5edf5; font-family:Segoe UI,Arial,sans-serif; }
header { padding:14px 18px; background:#151b23; display:flex; justify-content:space-between; align-items:center; }
main { display:grid; grid-template-columns:minmax(680px,1fr) 430px; gap:16px; padding:16px; }
.card { background:#161b22; border:1px solid #30363d; border-radius:14px; padding:14px; }
.stream { width:100%; border-radius:12px; background:#000; }
button { background:#2563eb; color:white; border:0; border-radius:10px; padding:9px 11px; margin:3px; cursor:pointer; font-weight:700; }
button.secondary { background:#374151; } button.warn { background:#b45309; } button.danger { background:#b91c1c; }
.grid3,.digits { display:grid; grid-template-columns:repeat(3,1fr); gap:6px; }
.pill { padding:4px 8px; border-radius:999px; background:#374151; display:inline-block; } .active { background:#166534; } .inactive { background:#7f1d1d; }
pre { white-space:pre-wrap; word-break:break-word; color:#b6c2cf; max-height:360px; overflow:auto; }
input,textarea { background:#0b1016; color:#e5edf5; border:1px solid #3b4450; border-radius:8px; padding:8px; width:95%; }
.transition { border:1px solid #30363d; border-radius:10px; padding:8px; margin:8px 0; background:#0f1720; }
.small { color:#94a3b8; font-size:12px; }
</style>
</head>
<body>
<header><div><b>Teacher Mode</b> <span class="pill">STB: __ALIAS__</span> <a href="/monitor" style="color:#93c5fd">monitor</a> · <a href="/intelligence" style="color:#93c5fd">intelligence</a></div><div id="pill" class="pill inactive">idle</div></header>
<main>
<section class="card"><img class="stream" src="/video.mjpg"><h3>Recent demonstrated transitions</h3><div id="recent"></div></section>
<aside class="card">
<h2>Manual Demonstration Recorder</h2>
<p class="small">Start recording, drive the box normally, and every button becomes a high-confidence before → button → after transition in the crawler graph.</p>
<input id="name" placeholder="Feature/test name, e.g. Parental Controls PIN setup"><br><br>
<textarea id="notes" rows="3" placeholder="What are you trying to demonstrate?"></textarea><br>
<button onclick="startRec()">Start recording</button><button class="danger" onclick="stopRec()">Stop</button><button class="secondary" onclick="annotate()">Add note</button>
<button class="warn" onclick="exploreHere()">Start crawler from current screen</button>
<hr>
<h3>Remote</h3>
<div class="grid3"><span></span><button onclick="sendKey('up')">↑</button><span></span><button onclick="sendKey('left')">←</button><button onclick="sendKey('select')">OK</button><button onclick="sendKey('right')">→</button><span></span><button onclick="sendKey('down')">↓</button><span></span></div>
<p><button onclick="sendKey('home')">Home</button><button onclick="sendKey('guide')">Guide</button><button onclick="sendKey('back')">Back</button><button onclick="sendKey('info')">Info</button><button onclick="sendKey('live')">Live</button><button onclick="sendKey('input')">Input</button><button onclick="sendKey('options')">Options</button></p>
<p><button onclick="sendKey('dvr')">DVR</button><button onclick="sendKey('recall')">Recall</button><button onclick="sendKey('ch_up')">CH +</button><button onclick="sendKey('ch_down')">CH −</button></p>
<div class="digits"><button onclick="sendKey('1')">1</button><button onclick="sendKey('2')">2</button><button onclick="sendKey('3')">3</button><button onclick="sendKey('4')">4</button><button onclick="sendKey('5')">5</button><button onclick="sendKey('6')">6</button><button onclick="sendKey('7')">7</button><button onclick="sendKey('8')">8</button><button onclick="sendKey('9')">9</button><button onclick="sendKey('back')">Back</button><button onclick="sendKey('0')">0</button><button onclick="sendKey('select')">Enter</button></div>
<p><input id="direct" placeholder="CH_206 or home,guide or select"><button onclick="sendDirect()">Send</button></p>
<h3>Status / last result</h3><pre id="out">loading...</pre>
</aside>
</main>
<script>
const qs=id=>document.getElementById(id); async function api(u,b=null){const opt=b?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}:{}; const r=await fetch(u,opt); return await r.json();}
function seq(v){return String(v||'').split(/[ ,]+/).map(x=>x.trim()).filter(Boolean)}
async function startRec(){qs('out').textContent='Starting...'; qs('out').textContent=JSON.stringify(await api('/api/teach/start',{name:qs('name').value,notes:qs('notes').value}),null,2); refresh();}
async function stopRec(){qs('out').textContent=JSON.stringify(await api('/api/teach/stop',{}),null,2); refresh();}
async function flushTeach(){qs('out').textContent=JSON.stringify(await api('/api/teach/flush',{}),null,2); refresh();}
async function annotate(){const text=qs('notes').value||prompt('Note?')||''; qs('out').textContent=JSON.stringify(await api('/api/teach/annotate',{text}),null,2); refresh();}
async function exploreHere(){qs('out').textContent=JSON.stringify(await api('/api/teach/explore_from_here',{max_steps:0,max_states:0,max_depth:18}),null,2); refresh();}
async function sendKey(k){qs('out').textContent='Sending '+k+'...'; const j=await api('/send_key',{key:k}); qs('out').textContent=JSON.stringify(j,null,2); refresh();}
async function sendDirect(){const v=qs('direct').value.trim(); if(!v)return; if(v.includes(',')){for(const k of seq(v)) await sendKey(k);} else await sendKey(v);}
function esc(s){return String(s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
function transitionHtml(e){return `<div class="transition"><b>${esc(e.button)}</b> · ${esc(e.before_label||e.before_state)} → ${esc(e.after_label||e.after_state)}<br><span class="small">focus: ${esc((e.before_focus||'').slice(0,90))} → ${esc((e.after_focus||'').slice(0,90))}<br>changed ${e.changed} · new edge ${e.new_edge} · reward ${e.reward} · response ${e.response_s}s</span></div>`}
async function refresh(){const j=await api('/api/teach/status'); qs('pill').textContent=j.active?'RECORDING':'idle'; qs('pill').className='pill '+(j.active?'active':'inactive'); const s=j.active_session||j.latest_session||{}; const events=(j.active_session&&j.active_session.events)||[]; qs('recent').innerHTML=events.filter(e=>e.type==='button_transition').slice(-8).reverse().map(transitionHtml).join('')||'<span class="small">No recorded buttons yet.</span>'; qs('out').textContent=JSON.stringify({active:j.active,summary:(s.summary||{}),latest:j.latest_session,last_error:j.last_error},null,2);}
setInterval(refresh,1500); refresh();
</script></body></html>
""".replace("__ALIAS__", str(alias))
    return Response(html, mimetype="text/html")


@app.route("/api/teach/start", methods=["POST"])
def api_teach_start():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(teacher.start(name=str(data.get("name") or ""), notes=str(data.get("notes") or ""), operator=str(data.get("operator") or "human")))
    except Exception as exc:
        log.exception("teacher start failed")
        return jsonify(ok=False, error=str(exc), status=teacher.status()), 500


@app.route("/api/teach/stop", methods=["POST", "GET"])
def api_teach_stop():
    try:
        return jsonify(teacher.stop())
    except Exception as exc:
        log.exception("teacher stop failed")
        return jsonify(ok=False, error=str(exc), status=teacher.status()), 500


@app.route("/api/teach/status")
def api_teach_status():
    return jsonify(teacher.status())


@app.route("/api/teach/sessions")
def api_teach_sessions():
    return jsonify(teacher.list_sessions(limit=int(request.args.get("limit", 20))))


@app.route("/api/teach/flush", methods=["POST", "GET"])
def api_teach_flush():
    try:
        return jsonify(teacher.flush_pending())
    except Exception as exc:
        log.exception("teacher flush failed")
        return jsonify(ok=False, error=str(exc), status=teacher.status()), 500


@app.route("/api/teach/annotate", methods=["POST"])
def api_teach_annotate():
    data = request.get_json(silent=True) or {}
    try:
        tags = data.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        return jsonify(teacher.annotate(str(data.get("text") or ""), tags=tags))
    except Exception as exc:
        log.exception("teacher annotate failed")
        return jsonify(ok=False, error=str(exc), status=teacher.status()), 500


@app.route("/api/teach/record_key", methods=["POST"])
def api_teach_record_key():
    data = request.get_json(silent=True) or {}
    key = data.get("key")
    if not key:
        return jsonify(ok=False, error="key is required"), 400
    try:
        learn_mode = str(data.get("learn_mode") or ("fast" if teacher.fast_recording_enabled else "sync")).lower()
        if learn_mode in {"sync", "deep", "blocking"}:
            return jsonify(teacher.record_button(str(key), delay_ms=data.get("delay_ms"), gap_s=float(data.get("gap_s", 0.2)), note=str(data.get("note") or "")))
        return jsonify(teacher.record_button_fast(str(key), delay_ms=data.get("delay_ms"), gap_s=float(data.get("gap_s", 0.075)), note=str(data.get("note") or "")))
    except Exception as exc:
        log.exception("teacher record key failed")
        return jsonify(ok=False, error=str(exc), status=teacher.status()), 500


@app.route("/api/teach/explore_from_here", methods=["POST"])
def api_teach_explore_from_here():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(teacher.start_autonomous_from_current(data))
    except Exception as exc:
        log.exception("teacher explore-from-here failed")
        return jsonify(ok=False, error=str(exc), teacher=teacher.status(), crawler=crawler.status()), 500



@app.route("/human")
def human_page() -> Response:
    return Response("""<!doctype html><html><head><title>Human Observer</title><style>
body{font-family:Segoe UI,Arial;background:#101318;color:#f4f4f5;margin:24px}.card{background:#181d25;border:1px solid #303746;border-radius:14px;padding:16px;margin:12px 0}button{background:#2563eb;color:#fff;border:0;border-radius:9px;padding:9px 12px;margin:4px;cursor:pointer}pre{white-space:pre-wrap;background:#0b0e13;border:1px solid #2b3240;border-radius:10px;padding:12px;max-height:520px;overflow:auto}.pill{display:inline-block;padding:4px 9px;border-radius:999px;background:#263449}.small{color:#a1a1aa}.row{display:flex;gap:14px;flex-wrap:wrap}.col{flex:1;min-width:360px}</style></head><body>
<h1>Human Observer</h1><p class=small>Shows what the crawler thinks a careful human would notice: transient loading, passive video, PIN/PPV/timer/settings cues, risks, annoyance flags, and matching test playbooks.</p>
<div class=row><div class=col><div class=card><button onclick="current()">Analyze current screen</button><button onclick="backlog()">Load goal backlog</button><button onclick="playbooks()">Show playbooks</button><button onclick="location.href='/intelligence'">Intelligence</button><button onclick="location.href='/dashboards'">Dashboards</button><pre id=out>ready</pre></div></div><div class=col><div class=card><h3>Current snapshot</h3><img id=img src="/snapshot.jpg" style="max-width:100%;border-radius:12px;border:1px solid #333"><p class=small>Refresh current screen after analysis.</p></div></div></div>
<script>
async function post(u,b={}){let r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});return await r.json()}
async function get(u){let r=await fetch(u); return await r.json()}
async function current(){document.getElementById('out').textContent='analyzing...';let j=await get('/api/human/current');document.getElementById('out').textContent=JSON.stringify(j,null,2);document.getElementById('img').src='/snapshot.jpg?t='+Date.now()}
async function backlog(){document.getElementById('out').textContent=JSON.stringify(await get('/api/human/backlog?limit=80'),null,2)}
async function playbooks(){document.getElementById('out').textContent=JSON.stringify(await get('/api/human/playbooks'),null,2)}
current();
</script></body></html>""", mimetype="text/html")


@app.route("/api/human/playbooks")
def api_human_playbooks():
    return jsonify(ok=True, playbooks=all_playbooks())


@app.route("/api/human/backlog")
def api_human_backlog():
    limit = int(request.args.get("limit", 100))
    return jsonify(ok=True, backlog=backlog_from_graph(CRAWLER_DIR, limit=limit))


@app.route("/api/human/current", methods=["GET", "POST"])
def api_human_current():
    try:
        fp = crawler.capture_fingerprint("human_current", perception="full")
        focus = fp.focus if isinstance(fp.focus, dict) else {}
        cues = focus.get("human_cues") if isinstance(focus.get("human_cues"), dict) else {}
        return jsonify(ok=True, state={"label": crawler.focus_label(fp), "ocr_text": fp.ocr_text, "tokens": fp.ocr_tokens[:80], "focus": focus}, human_cues=cues, playbooks=playbooks_for_cues(cues))
    except Exception as exc:
        log.exception("human current analysis failed")
        return jsonify(ok=False, error=str(exc)), 500


@app.route("/parental")
def parental_page() -> Response:
    return Response("""
<!doctype html><html><head><meta charset="utf-8"><title>Parental Control Lab</title>
<style>body{font-family:Segoe UI,Arial,sans-serif;background:#0f1720;color:#e5edf5;margin:0;padding:18px}.card{background:#182231;border:1px solid #304156;border-radius:14px;padding:14px;margin:12px 0}button{background:#2563eb;color:white;border:0;border-radius:10px;padding:9px 12px;margin:4px;cursor:pointer}button.warn{background:#b45309}input{background:#0b1220;color:#e5edf5;border:1px solid #3b4b61;border-radius:8px;padding:8px;margin:4px}pre{white-space:pre-wrap;background:#09111c;border:1px solid #253548;border-radius:12px;padding:12px;max-height:520px;overflow:auto}.hint{color:#9fb0c6}</style></head>
<body><h1>Parental Control Lab <span class=hint>v12 active fallback</span></h1>
<p class=hint>This page uses the learned map first. If no learned route exists, v12 actively tries HOME → focused Settings → focused Parental/Locks. Dry-run does not move the STB. PIN is stored locally in crawler_data/parental_control_memory.json.</p>
<div class=card><label>PIN <input id=pin value="1234"></label><label>Test blocked channel <input id=channel value="125"></label><br><label>Final setup sequence <input id=setupseq placeholder="optional exact keys after reaching PC settings: down,select,1,2,3,4,select" size=80></label><br><label>Final disable sequence <input id=disseq placeholder="optional exact keys after reaching PC settings: down,select,..." size=80></label></div>
<div class=card><button onclick="status()">Status</button><button onclick="focusNow()">Current Focus</button><button onclick="find(false)">Active find PC Settings</button><button onclick="setup(true)">Dry-run setup plan</button><button class=warn onclick="setup(false)">Active setup/find</button><button onclick="verify(false)">Verify blocked channel / unlock</button><button onclick="disable(true)">Dry-run disable plan</button><button class=warn onclick="disable(false)">Active disable/find</button><button onclick="pinprompt()">Detect/enter PIN if prompted</button></div>
<div class=card><b>Expected workflow:</b><ol><li>Dry-run setup plan: confirms route or active fallback plan.</li><li>Active find/setup: moves the STB. It may stop at the parental-control area unless you provide an exact final setup sequence.</li><li>Verify blocked channel: numeric tunes the channel and watches for the PIN popup.</li><li>Disable: navigates back to PC settings, enters PIN if prompted, and applies optional final disable sequence.</li></ol></div>
<pre id=out>{}</pre>
<script>const qs=id=>document.getElementById(id); const seq=id=>qs(id).value.split(/[
,]+/).map(x=>x.trim()).filter(Boolean); async function post(u,b={}){qs('out').textContent='Working...';let r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}); let j=await r.json(); qs('out').textContent=JSON.stringify(j,null,2); return j;} async function status(){let r=await fetch('/api/parental/status'); qs('out').textContent=JSON.stringify(await r.json(),null,2);} async function focusNow(){let r=await fetch('/api/crawl/focus'); qs('out').textContent=JSON.stringify(await r.json(),null,2);} async function find(dry){return post('/api/parental/find',{dry_run:dry});} async function setup(dry){return post('/api/parental/setup',{pin:qs('pin').value,blocked_channel:parseInt(qs('channel').value),dry_run:dry,final_sequence:seq('setupseq')});} async function verify(dry){return post('/api/parental/verify',{pin:qs('pin').value,channel:parseInt(qs('channel').value),dry_run:dry});} async function disable(dry){return post('/api/parental/disable',{pin:qs('pin').value,dry_run:dry,final_sequence:seq('disseq')});} async function pinprompt(){return post('/api/parental/enter_pin_if_prompt',{pin:qs('pin').value});} status();</script></body></html>
""", mimetype="text/html")


@app.route("/api/parental/status")
def api_parental_status():
    return jsonify(parental_agent.status())


@app.route("/api/parental/remember_pin", methods=["POST"])
def api_parental_remember_pin():
    data = request.get_json(silent=True) or {}
    return jsonify(parental_agent.remember_pin(str(data.get("pin") or "")))


@app.route("/api/parental/enter_pin_if_prompt", methods=["POST"])
def api_parental_enter_pin_if_prompt():
    data = request.get_json(silent=True) or {}
    pin = str(data.get("pin") or "") or None
    return jsonify(parental_agent.maybe_enter_pin(pin=pin))


@app.route("/api/parental/setup", methods=["POST"])
def api_parental_setup():
    data = request.get_json(silent=True) or {}
    seq = data.get("final_sequence") or []
    if isinstance(seq, str):
        seq = [x.strip() for x in seq.replace("\n", ",").split(",") if x.strip()]
    return jsonify(parental_agent.setup_parental_controls(
        pin=str(data.get("pin") or ""),
        blocked_channel=data.get("blocked_channel"),
        dry_run=bool(data.get("dry_run", True)),
        final_sequence=seq,
    ))


@app.route("/api/parental/verify", methods=["POST"])
def api_parental_verify():
    data = request.get_json(silent=True) or {}
    return jsonify(parental_agent.verify_blocked_channel(
        channel=int(data.get("channel") or data.get("blocked_channel") or parental_agent.memory.last_blocked_channel or 0),
        pin=str(data.get("pin") or "") or None,
        dry_run=bool(data.get("dry_run", False)),
    ))


@app.route("/api/parental/disable", methods=["POST"])
def api_parental_disable():
    data = request.get_json(silent=True) or {}
    seq = data.get("final_sequence") or []
    if isinstance(seq, str):
        seq = [x.strip() for x in seq.replace("\n", ",").split(",") if x.strip()]
    return jsonify(parental_agent.disable_parental_controls(
        pin=str(data.get("pin") or "") or None,
        dry_run=bool(data.get("dry_run", True)),
        final_sequence=seq,
    ))


@app.route("/api/crawl/focus/overlay.jpg")
def api_crawl_focus_overlay():
    frame = monitor.get_frame()
    if frame is None or not getattr(frame, "size", 0):
        abort(404)
    focus = detect_focus(frame)
    overlay = draw_focus_overlay(frame, focus)
    ok, buf = __import__("cv2").imencode(".jpg", overlay, [int(__import__("cv2").IMWRITE_JPEG_QUALITY), 88])
    if not ok:
        abort(500)
    return Response(buf.tobytes(), mimetype="image/jpeg")


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



@app.route("/api/crawl/map")
def api_crawl_map():
    return jsonify(crawler.visual_map())


@app.route("/api/crawl/transitions")
def api_crawl_transitions():
    limit = request.args.get("limit", "300")
    try:
        limit_i = max(1, min(1000, int(limit)))
    except Exception:
        limit_i = 300
    return jsonify(ok=True, transitions=crawler.transition_cards(limit=limit_i))


@app.route("/api/crawl/state/<state_id>/image")
def api_crawl_state_image(state_id: str):
    node = crawler.graph.nodes.get(state_id)
    if not node or not node.representative.screenshot:
        abort(404)
    path = (CRAWLER_DIR / node.representative.screenshot).resolve()
    if CRAWLER_DIR not in path.parents and path != CRAWLER_DIR:
        abort(404)
    if not path.is_file():
        abort(404)
    return send_file(path, mimetype="image/jpeg")


@app.route("/api/crawl/candidates", methods=["GET", "POST"])
def api_crawl_candidates():
    data = request.get_json(silent=True) or {}
    query = request.args.get("q") or data.get("query") or ""
    limit = int(request.args.get("limit") or data.get("limit") or 10)
    return jsonify(ok=True, query=query, candidates=crawler.find_state_candidates(query, limit=limit))


@app.route("/api/crawl/plan", methods=["POST"])
def api_crawl_plan():
    data = request.get_json(silent=True) or {}
    channel = data.get("channel")
    if channel in ("", None):
        channel = None
    else:
        try:
            channel = int(channel)
        except Exception:
            channel = None
    return jsonify(crawler.plan_route(
        target_state=data.get("target_state") or None,
        query=data.get("query") or None,
        channel=channel,
    ))


@app.route("/api/crawl/navigate", methods=["POST"])
def api_crawl_navigate():
    data = request.get_json(silent=True) or {}
    channel = data.get("channel")
    if channel in ("", None):
        channel = None
    else:
        try:
            channel = int(channel)
        except Exception:
            channel = None
    dry_run = bool(data.get("dry_run", False))
    try:
        return jsonify(crawler.navigate_to_target(
            target_state=data.get("target_state") or None,
            query=data.get("query") or None,
            channel=channel,
            dry_run=dry_run,
        ))
    except Exception as exc:
        log.exception("crawl navigate failed")
        return jsonify(ok=False, error=str(exc), status=crawler.status()), 500


@app.route("/api/crawl/goal", methods=["POST"])
def api_crawl_goal():
    data = request.get_json(silent=True) or {}
    seq = data.get("final_sequence") or []
    if isinstance(seq, str):
        seq = [x.strip() for x in seq.replace("\n", ",").split(",") if x.strip()]
    dry_run = bool(data.get("dry_run", True))
    try:
        return jsonify(crawler.run_goal(
            query=str(data.get("query") or ""),
            desired_value=str(data.get("desired_value") or ""),
            final_sequence=seq,
            dry_run=dry_run,
        ))
    except Exception as exc:
        log.exception("crawl goal failed")
        return jsonify(ok=False, error=str(exc), status=crawler.status()), 500




# ──────────────────────────────────────────────────────────────────────────────
# Learning / Superset-style dashboards
# ──────────────────────────────────────────────────────────────────────────────

def _dash_data() -> DashboardDataset:
    return DashboardDataset.load(CRAWLER_DIR)


def _json_dumps_for_html(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def _dashboard_shell(title: str, mode: str, payload: Dict[str, Any]) -> str:
    """Self-contained, no-CDN dashboard page that feels Superset-ish."""
    data = _json_dumps_for_html(payload)
    return f"""<!doctype html>
<html>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>{title}</title>
<style>
  :root {{ --bg:#0b1020; --panel:#121a2f; --panel2:#18223b; --ink:#eef3ff; --muted:#9fb0d0; --line:#2b3a62; --good:#4ade80; --warn:#fbbf24; --bad:#fb7185; --info:#60a5fa; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family: Inter, Segoe UI, Arial, sans-serif; background:linear-gradient(180deg,#071024,#0b1020 35%,#080b14); color:var(--ink); }}
  header {{ padding:18px 22px; border-bottom:1px solid var(--line); background:rgba(8,12,24,.92); position:sticky; top:0; z-index:3; backdrop-filter: blur(8px); }}
  .top {{ display:flex; justify-content:space-between; gap:18px; align-items:center; flex-wrap:wrap; }}
  h1 {{ margin:0; font-size:22px; }}
  .subtitle {{ color:var(--muted); margin-top:4px; font-size:13px; }}
  .nav a {{ color:#cfe2ff; text-decoration:none; padding:8px 10px; border:1px solid var(--line); border-radius:9px; margin-left:6px; background:#10182a; }}
  main {{ padding:18px 22px 40px; }}
  .grid {{ display:grid; grid-template-columns:repeat(12,1fr); gap:14px; }}
  .card {{ background:linear-gradient(180deg,var(--panel),#0f172a); border:1px solid var(--line); border-radius:16px; padding:15px; box-shadow:0 8px 24px rgba(0,0,0,.22); }}
  .span-12 {{ grid-column:span 12; }} .span-8 {{ grid-column:span 8; }} .span-6 {{ grid-column:span 6; }} .span-4 {{ grid-column:span 4; }} .span-3 {{ grid-column:span 3; }}
  @media(max-width:1000px) {{ .span-8,.span-6,.span-4,.span-3 {{ grid-column:span 12; }} }}
  .kpi {{ font-size:30px; font-weight:800; line-height:1.1; }} .kpi small {{ color:var(--muted); font-size:13px; font-weight:600; display:block; margin-top:6px; }}
  .label {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
  .pill {{ display:inline-block; padding:3px 8px; border-radius:999px; background:#17233f; color:#dbeafe; border:1px solid #2c3e66; font-size:12px; margin:2px; }}
  .good {{ color:var(--good); }} .warn {{ color:var(--warn); }} .bad {{ color:var(--bad); }} .info {{ color:var(--info); }}
  table {{ width:100%; border-collapse:collapse; font-size:12px; }} th,td {{ padding:8px 7px; border-bottom:1px solid #223150; text-align:left; vertical-align:top; }} th {{ color:#bfd2f4; font-weight:700; position:sticky; top:74px; background:#111a2e; z-index:1; }}
  tr:hover td {{ background:#121d34; }}
  .bar {{ height:10px; background:#1d2946; border-radius:999px; overflow:hidden; }} .bar > i {{ display:block; height:100%; background:linear-gradient(90deg,#60a5fa,#4ade80); }}
  .miniBars {{ display:flex; align-items:flex-end; gap:3px; height:120px; border-left:1px solid #26385f; border-bottom:1px solid #26385f; padding:8px; }}
  .miniBars span {{ flex:1; min-width:4px; background:linear-gradient(180deg,#60a5fa,#2563eb); border-radius:4px 4px 0 0; position:relative; }}
  .miniBars span:hover::after {{ content:attr(data-tip); position:absolute; bottom:105%; left:0; background:#020617; color:#fff; padding:5px 6px; border:1px solid #334155; border-radius:6px; white-space:nowrap; z-index:5; }}
  .heat {{ display:grid; grid-template-columns:220px repeat(9, minmax(38px,1fr)); gap:2px; overflow:auto; }} .heat div {{ padding:5px; background:#111b31; font-size:11px; border-radius:4px; }} .heat .on {{ background:#14532d; }} .heat .off {{ background:#3f1722; }} .heat .head {{ background:#263557; color:#dbeafe; font-weight:700; }}
  details summary {{ cursor:pointer; color:#bfdbfe; }}
  code {{ background:#111827; padding:2px 5px; border-radius:5px; color:#dbeafe; }}
</style>
</head>
<body>
<header>
  <div class='top'>
    <div><h1>{title}</h1><div class='subtitle'>Autonomous set-top learning, training, known-knowns, known-unknowns, and progress history. Generated <span id='gen'></span>.</div></div>
    <div class='nav'>
      <a href='/dashboards'>Hub</a><a href='/dashboard/exec'>Exec</a><a href='/dashboard/eng'>Engineering</a><a href='/intelligence'>Intelligence</a><a href='/api/dashboards/superset.zip'>Superset Export</a>
    </div>
  </div>
</header>
<main id='app'></main>
<script>
const DATA = {data};
const MODE = {json.dumps(mode)};
const app = document.getElementById('app');
document.getElementById('gen').textContent = DATA.generated_at || (DATA.exec && DATA.exec.generated_at) || '';
function pct(v) {{ return (Number(v)||0).toFixed(1)+'%'; }}
function esc(s) {{ return String(s ?? '').replace(/[&<>]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c])); }}
function kpi(label, value, cls='') {{ return `<section class='card span-3'><div class='label'>${{esc(label)}}</div><div class='kpi ${{cls}}'>${{esc(value)}}<small>${{esc(label)}}</small></div></section>`; }}
function table(title, rows, cols, span='span-12', limit=80) {{
  rows = rows || [];
  const body = rows.slice(0,limit).map(r => `<tr>${{cols.map(c => `<td>${{esc(typeof c.f==='function'?c.f(r):r[c.k])}}</td>`).join('')}}</tr>`).join('');
  return `<section class='card ${{span}}'><h3>${{esc(title)}} <span class='pill'>${{rows.length}} rows</span></h3><div style='max-height:520px;overflow:auto'><table><thead><tr>${{cols.map(c=>`<th>${{esc(c.t||c.k)}}</th>`).join('')}}</tr></thead><tbody>${{body}}</tbody></table></div></section>`;
}}
function bars(title, rows, labelKey, valueKey, span='span-6') {{
  rows = (rows||[]).slice(0,40); const max = Math.max(1,...rows.map(r=>Number(r[valueKey])||0));
  return `<section class='card ${{span}}'><h3>${{esc(title)}}</h3><div class='miniBars'>${{rows.map(r=>`<span style='height:${{Math.max(3,(Number(r[valueKey])||0)/max*100)}}%' data-tip='${{esc(r[labelKey])}}: ${{esc(r[valueKey])}}'></span>`).join('')}}</div></section>`;
}}
function progress(label, val) {{ return `<div style='margin:8px 0'><div class='label'>${{esc(label)}} ${{pct(val)}}</div><div class='bar'><i style='width:${{Math.max(0,Math.min(100,Number(val)||0))}}%'></i></div></div>`; }}
function renderExec() {{
  const d = DATA.exec || DATA; const h=d.headline||{{}};
  let html = `<div class='grid'>`;
  html += kpi('Learning maturity', pct(h.learning_maturity_pct), h.learning_maturity_pct>70?'good':h.learning_maturity_pct>35?'warn':'bad');
  html += kpi('States', h.states||0); html += kpi('Transitions', h.transitions||0); html += kpi('Known unknowns', h.known_unknowns||0, h.known_unknowns?'warn':'good');
  html += `<section class='card span-6'><h3>Executive readout</h3>${{(d.narrative||[]).map(x=>`<p>${{esc(x)}}</p>`).join('')}}${{progress('Coverage',h.coverage_pct)}}${{progress('Perception quality',h.perception_quality_pct)}}${{progress('Avg transition confidence',(h.avg_transition_confidence||0)*100)}}${{progress('Avg focus confidence',(h.avg_focus_confidence||0)*100)}}</section>`;
  html += bars('Learning history: new states/hour', d.timeline||[], 'bucket', 'new_states', 'span-6');
  html += table('Top learned menus', (d.top_known_menus||[]).map(x=>({{menu:x[0], count:x[1]}})), [{{k:'menu',t:'Menu/Page'}},{{k:'count',t:'Seen'}}], 'span-6', 30);
  html += table('Known channels', d.channels||[], [{{k:'channel'}},{{k:'name_guess',t:'Name guess'}},{{k:'symbols'}},{{k:'confidence'}}], 'span-6', 80);
  html += table('Highest priority known-unknowns', d.known_unknowns||[], [{{k:'unknown_type',t:'Type'}},{{k:'label'}},{{k:'action'}},{{k:'priority'}}], 'span-12', 60);
  html += `</div>`; app.innerHTML=html;
}}
function renderEng() {{
  const d = DATA.eng || DATA; const h=d.headline||{{}};
  let html = `<div class='grid'>`;
  html += kpi('States', h.states||0); html += kpi('Edges', h.transitions||0); html += kpi('Coverage', pct(h.coverage_pct)); html += kpi('Quality', pct(h.perception_quality_pct));
  html += table('Per-action coverage', d.per_action_coverage||[], [{{k:'action'}},{{k:'tried'}},{{k:'total'}},{{k:'coverage_pct',t:'coverage %'}}], 'span-6', 30);
  html += table('Action timing / rewards', d.actions||[], [{{k:'action'}},{{k:'avg_reward'}},{{k:'reward_attempts'}},{{k:'avg_start_s'}},{{k:'avg_complete_s'}},{{k:'remarkable_count'}},{{k:'last_flags'}}], 'span-6', 40);
  html += bars('Exploration history: edges seen/hour', d.timeline||[], 'bucket', 'edge_seen', 'span-6');
  html += table('Quality breakdown', d.quality_breakdown||[], [{{k:'quality'}},{{k:'count'}}], 'span-3', 10);
  html += table('Pattern breakdown', d.pattern_breakdown||[], [{{k:'pattern'}},{{k:'count'}}], 'span-3', 20);
  html += table('Low-confidence transitions', d.edges_low_confidence||[], [{{k:'from_label',t:'From'}},{{k:'action'}},{{k:'to_label',t:'To'}},{{k:'confidence'}},{{k:'attempts'}}], 'span-12', 100);
  html += table('Known-unknown / training backlog', d.known_unknowns||[], [{{k:'unknown_type',t:'Type'}},{{k:'label'}},{{k:'action'}},{{k:'coverage_state'}},{{k:'priority'}}], 'span-12', 160);
  html += table('Questionable state perception', d.state_quality||[], [{{k:'quality'}},{{k:'label'}},{{k:'quality_reasons'}},{{k:'focus_confidence'}},{{k:'page_name'}},{{k:'focused_item'}}], 'span-12', 160);
  html += `</div>`; app.innerHTML=html;
}}
if (MODE === 'exec') renderExec(); else renderEng();
</script>
</body>
</html>"""


@app.route("/dashboards")
def dashboards_home():
    ds = _dash_data()
    ex = ds.executive()["headline"]
    html = f"""<!doctype html><html><head><meta charset='utf-8'><title>STB Learning Dashboards</title>
    <style>body{{font-family:Segoe UI,Arial;background:#0b1020;color:#eef3ff;margin:0;padding:30px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px}}.card{{background:#121a2f;border:1px solid #2b3a62;border-radius:16px;padding:22px}}a{{color:#bfdbfe;font-size:20px}}.k{{font-size:34px;font-weight:800}}.muted{{color:#9fb0d0}}</style></head><body>
    <h1>STB Autonomous Learning Dashboards</h1><p class='muted'>Two Superset-style views over the crawler's training brain, graph, known-knowns, known-unknowns, progress and history.</p>
    <div class='grid'><div class='card'><a href='/dashboard/exec'>Executive dashboard</a><p>Leadership view: maturity, progress, confidence, risk, known channels, and remaining unknowns.</p><div class='k'>{ex.get('learning_maturity_pct',0)}%</div><p class='muted'>learning maturity</p></div>
    <div class='card'><a href='/dashboard/eng'>Engineering dashboard</a><p>Debug view: coverage, OCR/focus quality, low-confidence transitions, action timing/rewards, and training backlog.</p><div class='k'>{ex.get('states',0)} / {ex.get('transitions',0)}</div><p class='muted'>states / transitions</p></div>
    <div class='card'><a href='/api/dashboards/superset.zip'>Download Superset export</a><p>CSV datasets, SQL helper views, and dashboard manifests for Superset import.</p><div class='k'>{ex.get('known_unknowns',0)}</div><p class='muted'>known unknowns</p></div></div>
    </body></html>"""
    return Response(html, mimetype="text/html")


@app.route("/dashboard/exec")
def dashboard_exec():
    ds = _dash_data()
    return Response(_dashboard_shell("STB Autonomous Learning — Executive", "exec", ds.executive()), mimetype="text/html")


@app.route("/dashboard/eng")
def dashboard_eng():
    ds = _dash_data()
    return Response(_dashboard_shell("STB Autonomous Learning — Engineering", "eng", ds.engineering()), mimetype="text/html")


@app.route("/api/dashboards/summary")
def api_dashboards_summary():
    ds = _dash_data()
    return jsonify(ok=True, generated_at=datetime.utcnow().isoformat() + "Z", headline=ds.executive().get("headline", {}))


@app.route("/api/dashboards/exec")
def api_dashboards_exec():
    return jsonify(_dash_data().executive())


@app.route("/api/dashboards/eng")
def api_dashboards_eng():
    return jsonify(_dash_data().engineering())


@app.route("/api/dashboards/tables")
def api_dashboards_tables():
    tables = _dash_data().superset_tables()
    return jsonify(ok=True, tables=tables)


@app.route("/api/dashboards/superset.zip")
def api_dashboards_superset_zip():
    blob = _dash_data().export_zip_bytes()
    return send_file(io.BytesIO(blob), mimetype="application/zip", as_attachment=True, download_name="stb_learning_superset_dashboards.zip")


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
