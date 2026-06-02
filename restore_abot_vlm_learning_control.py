#!/usr/bin/env python3
"""Surgically restore aBotTesty VLM Control + richer Learning/Training UI."""
from __future__ import annotations

import re
import sys
import py_compile
from datetime import datetime
from pathlib import Path

PATCH_VERSION = "v38.6-vlm-control-learning-restore-20260602"

VLM_CONTROL_BLOCK = r"""

# ---------------------------------------------------------------------------
# v38.6 restored VLM Control + shadow/promotion helpers
# ---------------------------------------------------------------------------

def _vlm_json_file() -> Path:
    root = ROOT / str(CFG.get("vlm_adapter_dir", "models/vlm_adapters"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "active_vlm.json"


def _vlm_mode_file() -> Path:
    p = CRAWLER_DIR / "vlm_mode.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _vlm_adapter_root() -> Path:
    p = ROOT / str(CFG.get("vlm_adapter_dir", "models/vlm_adapters"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def _vlm_remote_root() -> str:
    raw = str(CFG.get("vlm_remote_root", "~/aBotTesty_vlm_jobs"))
    if raw.startswith("~/"):
        return "/home/" + str(CFG.get("vlm_remote_user", "montjac")) + "/" + raw[2:]
    return raw


def _vlm_load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        log.exception("failed reading %s", path)
    return default


def _vlm_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _vlm_adapter_metrics(adapter_dir: Path) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {}
    trainer_state = adapter_dir / "trainer_state.json"
    if trainer_state.exists():
        try:
            st = json.loads(trainer_state.read_text(encoding="utf-8"))
            metrics["global_step"] = st.get("global_step")
            metrics["best_metric"] = st.get("best_metric")
            if st.get("log_history"):
                last = st.get("log_history")[-1]
                metrics["epoch"] = last.get("epoch")
                metrics["train_loss"] = last.get("train_loss", last.get("loss"))
        except Exception as exc:
            metrics["metrics_error"] = str(exc)
    return metrics


def _vlm_list_local_adapters() -> List[Dict[str, Any]]:
    root = _vlm_adapter_root()
    active = _vlm_load_json(_vlm_json_file(), {})
    active_run = str(active.get("run_name") or "")
    out: List[Dict[str, Any]] = []
    for d in sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True):
        model = d / "adapter_model.safetensors"
        cfg = d / "adapter_config.json"
        out.append({
            "run_name": d.name,
            "local_dir": str(d),
            "adapter_model": str(model) if model.exists() else "",
            "adapter_config": str(cfg) if cfg.exists() else "",
            "has_adapter": model.exists(),
            "adapter_size_mb": round(model.stat().st_size / 1024 / 1024, 2) if model.exists() else 0,
            "mtime": d.stat().st_mtime,
            "is_active": d.name == active_run,
            "metrics": _vlm_adapter_metrics(d),
        })
    return out


def _vlm_shadow_health(server_url: str | None = None, timeout_s: float = 2.5) -> Dict[str, Any]:
    import urllib.request
    url = (server_url or str(CFG.get("vlm_shadow_server_url", "http://10.79.85.35:8765"))).rstrip("/") + "/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout_s) as r:
            body = r.read().decode("utf-8", "replace")
        data = json.loads(body) if body.strip().startswith("{") else {"raw": body}
        data.setdefault("ok", True)
        data["url"] = url
        return data
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)}


def _vlm_remote_adapter_path(run_name: str) -> str:
    rr = _vlm_remote_root().rstrip("/")
    return f"{rr}/{run_name}/outputs/{run_name}"


def _vlm_restart_shadow_server(run_name: str, adapter_path: str = "", model_name: str = "", server_port: int = 8765) -> Dict[str, Any]:
    import subprocess
    import shlex
    host = str(CFG.get("vlm_remote_host", "10.79.85.35"))
    user = str(CFG.get("vlm_remote_user", "montjac"))
    rr = _vlm_remote_root().rstrip("/")
    adapter = adapter_path or _vlm_remote_adapter_path(run_name)
    model = model_name or str(CFG.get("vlm_default_model_3090", "Qwen/Qwen3-VL-8B-Instruct"))
    gpu = str(CFG.get("vlm_shadow_cuda_visible_devices", "1"))
    remote_script = f'''
set -Eeuo pipefail
ROOT={shlex.quote(rr)}
VENV="$ROOT/.venv_shadow"
LOG="$ROOT/logs/vlm_shadow_server.log"
PIDFILE="$ROOT/logs/vlm_shadow_server.pid"
mkdir -p "$ROOT/logs"
if [ -f "$PIDFILE" ]; then
  OLD_PID="$(cat "$PIDFILE" || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    kill "$OLD_PID" || true
    sleep 4
    kill -9 "$OLD_PID" 2>/dev/null || true
  fi
fi
"$VENV/bin/python" -m py_compile "$ROOT/vlm_shadow_server.py"
: > "$LOG"
CUDA_VISIBLE_DEVICES={shlex.quote(gpu)} nohup "$VENV/bin/python" "$ROOT/vlm_shadow_server.py" \
  --host 0.0.0.0 \
  --port {int(server_port)} \
  --base-model {shlex.quote(model)} \
  --adapter {shlex.quote(adapter)} \
  >> "$LOG" 2>&1 &
echo $! > "$PIDFILE"
echo "started pid=$(cat "$PIDFILE") adapter={adapter}"
sleep 2
ps -fp "$(cat "$PIDFILE")" || true
'''
    cmd = ["ssh", f"{user}@{host}", remote_script]
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=90)
    return {"ok": proc.returncode == 0, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr, "host": host, "adapter": adapter}


def _vlm_call_shadow(task: str, goal: str = "Explore the guide safely. Do not purchase or confirm anything.", action: str = "") -> Dict[str, Any]:
    import tempfile
    import subprocess
    import sys
    frame = monitor.get_jpeg()
    if not frame:
        return {"ok": False, "error": "no frame available", "video": monitor.get_status()}
    snap = Path(tempfile.gettempdir()) / "abot_shadow_snapshot.jpg"
    snap.write_bytes(frame)
    client = ROOT / "vlm_shadow_client.py"
    if not client.exists():
        return {"ok": False, "error": f"missing {client}"}
    server_url = str(CFG.get("vlm_shadow_server_url", "http://10.79.85.35:8765"))
    cmd = [sys.executable, str(client), "--server-url", server_url, "--image", str(snap), "--task", task]
    if goal:
        cmd += ["--goal", goal]
    if action:
        cmd += ["--action", action]
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=120)
    raw = proc.stdout.strip()
    parsed: Any = raw
    try:
        parsed = json.loads(raw)
    except Exception:
        pass
    rec = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "task": task,
        "goal": goal,
        "action": action,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": parsed,
        "stderr": proc.stderr,
        "snapshot": str(snap),
    }
    try:
        log_path = CRAWLER_DIR / "vlm_shadow_log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")
    except Exception:
        log.exception("failed writing vlm shadow log")
    return rec


@app.route("/vlmcontrol")
@app.route("/vlm_control")
@app.route("/vlm-control")
def vlm_control_page() -> Response:
    return Response(
        r'''
<!doctype html><html><head><meta charset="utf-8"><title>aBotTesty VLM Control</title>
<style>
:root{--bg:#071018;--panel:#111a25;--panel2:#0d1620;--line:#29384a;--text:#e6edf5;--muted:#9fb2c7;--good:#22c55e;--warn:#f59e0b;--bad:#ef4444;--blue:#2563eb;--purple:#7c3aed}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top,#122338,#071018 55%);color:var(--text);font-family:Segoe UI,Arial,sans-serif}header{padding:16px 20px;background:rgba(10,17,26,.9);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:10}a{color:#93c5fd}.wrap{padding:16px;display:grid;grid-template-columns:1.05fr .95fr;gap:16px}.card{background:linear-gradient(180deg,var(--panel),var(--panel2));border:1px solid var(--line);border-radius:16px;padding:14px;box-shadow:0 14px 34px rgba(0,0,0,.26)}button{background:var(--blue);color:white;border:0;border-radius:10px;padding:9px 12px;margin:4px;cursor:pointer;font-weight:750}button.warn{background:#b45309}button.good{background:#15803d}button.purple{background:var(--purple)}input,select,textarea{background:#07101a;color:var(--text);border:1px solid #3c4d62;border-radius:9px;padding:8px;width:100%;margin:4px 0}label{font-size:12px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.04em}.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}.pill{display:inline-block;padding:4px 8px;border:1px solid var(--line);border-radius:999px;color:var(--muted);font-size:12px;margin:2px}.active{color:#bbf7d0;border-color:#15803d}.bad{color:#fecaca;border-color:#991b1b}.adapter{border:1px solid var(--line);border-radius:12px;padding:10px;margin:8px 0;background:#0a121c}.adapter b{font-size:14px}pre{white-space:pre-wrap;word-break:break-word;color:#cbd5e1;max-height:440px;overflow:auto;background:#060b11;border:1px solid #223246;border-radius:12px;padding:10px}.wide{grid-column:1/-1}@media(max-width:1000px){.wrap{grid-template-columns:1fr}.row{grid-template-columns:1fr}}</style></head>
<body><header><b>aBotTesty VLM Control</b> · <a href="/monitor">monitor</a> · <a href="/learning">learning/training</a> · <span id="top" class="pill">loading</span><br><span style="color:#9fb2c7">Select adapters, promote locally, restart shadow inference, and run non-actuating perception/policy/verify checks.</span></header>
<div class="wrap">
<section class="card"><h2>Adapter inventory</h2><div id="adapters">loading...</div><button onclick="refresh()">Refresh</button></section>
<section class="card"><h2>Active / promote</h2><label>Run name</label><input id="run_name" placeholder="abot_vlm_20260601_154726"><label>Source</label><select id="source"><option value="local">local adapter cache</option><option value="remote">remote 3090 output; rsync local first</option></select><label>Model</label><input id="model" value="Qwen/Qwen3-VL-8B-Instruct"><label><input id="restart_shadow" type="checkbox" style="width:auto" checked> restart shadow server after promote</label><br><button class="good" onclick="promote()">Promote selected</button><button class="purple" onclick="restartShadow()">Restart shadow only</button><pre id="promote_out">ready</pre></section>
<section class="card"><h2>Mode</h2><label>VLM operating mode</label><select id="mode"><option value="off">off</option><option value="shadow" selected>shadow - observe/recommend only</option><option value="perception">perception only</option><option value="policy">policy suggestions only</option><option value="verify">outcome verifier only</option><option value="ranker">candidate ranker dry-run</option></select><label>Goal / safety instruction</label><textarea id="goal" rows="3">Explore the guide safely. Do not purchase, rent, subscribe, delete, reset, or confirm anything.</textarea><button onclick="setMode()">Save mode</button><button onclick="shadow('perception')">Analyze screen</button><button onclick="shadow('policy')">Policy suggestion</button><label>Verify action</label><input id="verify_action" placeholder="e.g. down, guide, back"><button onclick="shadow('verify')">Verify action outcome</button></section>
<section class="card"><h2>Shadow server</h2><button onclick="health()">Health</button><pre id="shadow_out">ready</pre></section>
<section class="card wide"><h2>Overview JSON</h2><pre id="overview">loading...</pre></section>
</div>
<script>
async function api(u,b=null){let opt=b?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}:{};let r=await fetch(u,opt);let t=await r.text();try{return JSON.parse(t)}catch(e){return {ok:false,status:r.status,raw:t}}}
function pick(run){run_name.value=run; window.scrollTo({top:0,behavior:'smooth'});}
function renderAdapters(rows){adapters.innerHTML=''; if(!rows||!rows.length){adapters.textContent='No local adapters found';return} rows.forEach(a=>{let div=document.createElement('div');div.className='adapter';div.innerHTML=`<b>${a.run_name}</b> ${a.is_active?'<span class="pill active">ACTIVE</span>':''} ${a.has_adapter?'<span class="pill active">adapter</span>':'<span class="pill bad">missing</span>'}<br><span style="color:#9fb2c7">${a.local_dir}</span><br><span class="pill">${a.adapter_size_mb||0} MB</span><span class="pill">step ${(a.metrics&&a.metrics.global_step)||''}</span><button onclick="pick('${a.run_name}')">Select</button>`; adapters.appendChild(div);});}
async function refresh(){let j=await api('/api/vlm/control/overview'); overview.textContent=JSON.stringify(j,null,2); renderAdapters(j.local_runs||[]); top.textContent=j.active_run?'active '+j.active_run:'no active adapter'; top.className='pill '+(j.active_run?'active':'bad'); if(j.mode&&j.mode.mode) mode.value=j.mode.mode; if(j.active_run&&!run_name.value) run_name.value=j.active_run;}
async function health(){shadow_out.textContent=JSON.stringify(await api('/api/vlm/control/shadow/status'),null,2)}
async function setMode(){shadow_out.textContent=JSON.stringify(await api('/api/vlm/mode/set',{mode:mode.value,goal:goal.value}),null,2); await refresh();}
async function promote(){promote_out.textContent='promoting...'; promote_out.textContent=JSON.stringify(await api('/api/vlm/control/promote',{run_name:run_name.value,source:source.value,model:model.value,restart_shadow:restart_shadow.checked}),null,2); await refresh();}
async function restartShadow(){promote_out.textContent='restarting shadow server...'; promote_out.textContent=JSON.stringify(await api('/api/vlm/control/shadow/restart',{run_name:run_name.value,model:model.value}),null,2); await refresh();}
async function shadow(task){shadow_out.textContent='running '+task+'...'; shadow_out.textContent=JSON.stringify(await api('/api/vlm/shadow/'+(task==='perception'?'analyze':task),{goal:goal.value,action:verify_action.value}),null,2)}
refresh(); health();
</script></body></html>
        ''',
        mimetype="text/html",
    )


@app.route("/api/vlm/control/overview", methods=["GET"])
def api_vlm_control_overview():
    active = _vlm_load_json(_vlm_json_file(), {})
    mode = _vlm_load_json(_vlm_mode_file(), {"mode": "shadow", "goal": "Explore safely", "actuation": "disabled"})
    local_runs = _vlm_list_local_adapters()
    active_run = str(active.get("run_name") or "")
    if not active_run:
        for row in local_runs:
            if row.get("is_active"):
                active_run = str(row.get("run_name") or "")
                break
    return jsonify({
        "ok": True,
        "patch_version": "v38.6-vlm-control-learning-restore-20260602",
        "host": CFG.get("vlm_remote_host", "10.79.85.35"),
        "remote_root": _vlm_remote_root(),
        "local_adapter_root": str(_vlm_adapter_root()),
        "active_run": active_run,
        "active": active,
        "mode": mode,
        "local_runs": local_runs,
        "shadow_health": _vlm_shadow_health(timeout_s=1.25),
    })


@app.route("/api/vlm/mode/get", methods=["GET"])
def api_vlm_mode_get():
    return jsonify(ok=True, mode=_vlm_load_json(_vlm_mode_file(), {"mode": "shadow", "actuation": "disabled"}))


@app.route("/api/vlm/mode/set", methods=["POST"])
def api_vlm_mode_set():
    data = request.get_json(silent=True) or {}
    mode = str(data.get("mode") or "shadow").strip().lower()
    allowed = {"off", "shadow", "perception", "policy", "verify", "ranker"}
    if mode not in allowed:
        return jsonify(ok=False, error=f"unsupported mode {mode}", allowed=sorted(allowed)), 400
    rec = {
        "mode": mode,
        "goal": str(data.get("goal") or "Explore safely. Do not purchase, rent, subscribe, delete, reset, or confirm anything."),
        "actuation": "disabled",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "note": "VLM modes are shadow/non-actuating. The app/crawler remains execution authority.",
    }
    _vlm_write_json(_vlm_mode_file(), rec)
    return jsonify(ok=True, mode=rec)


@app.route("/api/vlm/control/promote", methods=["POST"])
def api_vlm_control_promote():
    import subprocess
    data = request.get_json(silent=True) or {}
    run_name = str(data.get("run_name") or "").strip().rstrip("/")
    if not run_name:
        return jsonify(ok=False, error="run_name is required"), 400
    source = str(data.get("source") or "local").lower()
    host = str(data.get("host") or CFG.get("vlm_remote_host", "10.79.85.35"))
    user = str(data.get("user") or CFG.get("vlm_remote_user", "montjac"))
    local_dir = _vlm_adapter_root() / run_name
    remote_adapter = str(data.get("remote_adapter") or _vlm_remote_adapter_path(run_name))
    pulled = None
    if source == "remote":
        local_dir.mkdir(parents=True, exist_ok=True)
        src = f"{user}@{host}:{remote_adapter.rstrip('/')}/"
        proc = subprocess.run(["rsync", "-az", src, str(local_dir) + "/"], text=True, capture_output=True, timeout=300)
        pulled = {"ok": proc.returncode == 0, "returncode": proc.returncode, "src": src, "dest": str(local_dir), "stdout": proc.stdout, "stderr": proc.stderr}
        if proc.returncode != 0:
            return jsonify(ok=False, error="rsync failed", pulled=pulled), 500
    model = local_dir / "adapter_model.safetensors"
    if not model.exists():
        return jsonify(ok=False, error=f"local adapter_model.safetensors not found for {run_name}", local_dir=str(local_dir), hint="select source=remote to pull it first"), 404
    active = {
        "run_name": run_name,
        "local_dir": str(local_dir),
        "adapter_model": str(model),
        "remote_adapter": remote_adapter,
        "model": str(data.get("model") or CFG.get("vlm_default_model_3090", "Qwen/Qwen3-VL-8B-Instruct")),
        "promoted_at": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "actuation": "disabled",
    }
    _vlm_write_json(_vlm_json_file(), active)
    restart = None
    if bool(data.get("restart_shadow", False)):
        restart = _vlm_restart_shadow_server(run_name=run_name, adapter_path=remote_adapter, model_name=active["model"])
    return jsonify(ok=True, active=active, pulled=pulled, restart=restart)


@app.route("/api/vlm/control/shadow/status", methods=["GET"])
@app.route("/api/vlm/shadow/status", methods=["GET"])
def api_vlm_shadow_status():
    return jsonify(_vlm_shadow_health())


@app.route("/api/vlm/control/shadow/restart", methods=["POST"])
def api_vlm_shadow_restart():
    data = request.get_json(silent=True) or {}
    run_name = str(data.get("run_name") or "").strip()
    active = _vlm_load_json(_vlm_json_file(), {})
    if not run_name:
        run_name = str(active.get("run_name") or "")
    if not run_name:
        return jsonify(ok=False, error="run_name is required; no active adapter found"), 400
    adapter = str(data.get("adapter") or active.get("remote_adapter") or _vlm_remote_adapter_path(run_name))
    model = str(data.get("model") or active.get("model") or CFG.get("vlm_default_model_3090", "Qwen/Qwen3-VL-8B-Instruct"))
    return jsonify(_vlm_restart_shadow_server(run_name=run_name, adapter_path=adapter, model_name=model))


@app.route("/api/vlm/shadow/analyze", methods=["POST", "GET"])
def api_vlm_shadow_analyze():
    data = request.get_json(silent=True) or {}
    return jsonify(_vlm_call_shadow("perception", goal=str(data.get("goal") or "Describe the current TV screen as compact JSON.")))


@app.route("/api/vlm/shadow/policy", methods=["POST", "GET"])
def api_vlm_shadow_policy():
    data = request.get_json(silent=True) or {}
    return jsonify(_vlm_call_shadow("policy", goal=str(data.get("goal") or "Explore the guide safely. Do not purchase or confirm anything.")))


@app.route("/api/vlm/shadow/verify", methods=["POST", "GET"])
def api_vlm_shadow_verify():
    data = request.get_json(silent=True) or {}
    return jsonify(_vlm_call_shadow("verify", goal=str(data.get("goal") or "Verify the requested action outcome."), action=str(data.get("action") or "")))


@app.route("/api/learning/train_from_latest", methods=["POST"])
def api_learning_train_from_latest():
    data = request.get_json(silent=True) or {}
    run_id = str(data.get("run_id") or "latest").strip() or "latest"
    execute = bool(data.get("execute", False))
    try:
        export = _learning_writer().export(
            run_id=run_id,
            max_records=int(data.get("max_records") or 0),
            include_raw=bool(data.get("include_raw", False)),
        )
        dataset_dir = str(export.get("dataset_dir") or (ROOT / str(CFG.get("learning_dataset_dir", "learning_datasets")) / run_id))
        data2 = dict(data)
        data2["dataset_dir"] = dataset_dir
        data2["execute"] = execute
        job = _remote_job_from_request(data2)
        hardware = str(data.get("hardware") or "2x3090")
        out_dir = ROOT / "vlm_jobs" / job.run_name
        plan = prepare_job_files(job, out_dir=out_dir, hardware=hardware)
        if execute:
            submit = submit_job(job, prepared_dir=out_dir)
        else:
            submit = {"ok": True, "dry_run": True, "note": "Set execute=true to launch remote training."}
        return jsonify(ok=True, export=export, plan=plan, submit=submit)
    except Exception as exc:
        log.exception("learning train_from_latest failed")
        return jsonify(ok=False, error=str(exc)), 500
"""

LEARNING_PAGE_REPLACEMENT = r"""
@app.route("/learning")
def learning_page() -> Response:
    return Response(
        r'''
<!doctype html><html><head><meta charset="utf-8"><title>aBotTesty Learning + VLM Training</title>
<style>
:root{--bg:#071018;--panel:#111a25;--panel2:#0d1620;--line:#29384a;--text:#e6edf5;--muted:#9fb2c7;--blue:#2563eb;--green:#15803d;--orange:#b45309;--purple:#7c3aed}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top,#122338,#071018 55%);color:var(--text);font-family:Segoe UI,Arial,sans-serif}header{padding:16px 20px;background:rgba(10,17,26,.9);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:10}a{color:#93c5fd}.wrap{padding:16px;display:grid;grid-template-columns:1fr 1fr;gap:16px}.card{background:linear-gradient(180deg,var(--panel),var(--panel2));border:1px solid var(--line);border-radius:16px;padding:14px;box-shadow:0 14px 34px rgba(0,0,0,.26)}button{background:var(--blue);color:white;border:0;border-radius:10px;padding:9px 12px;margin:4px;cursor:pointer;font-weight:750}button.good{background:var(--green)}button.warn{background:var(--orange)}button.purple{background:var(--purple)}input,select,textarea{background:#07101a;color:var(--text);border:1px solid #3c4d62;border-radius:9px;padding:8px;width:100%;margin:4px 0}label{font-size:12px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.04em}.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}.pill{display:inline-block;padding:4px 8px;border:1px solid var(--line);border-radius:999px;color:var(--muted);font-size:12px;margin:2px}.wide{grid-column:1/-1}pre{white-space:pre-wrap;word-break:break-word;color:#cbd5e1;max-height:520px;overflow:auto;background:#060b11;border:1px solid #223246;border-radius:12px;padding:10px}@media(max-width:1000px){.wrap{grid-template-columns:1fr}.row{grid-template-columns:1fr}}</style></head>
<body><header><b>aBotTesty Learning + VLM Training</b> · <a href="/monitor">monitor</a> · <a href="/vlmcontrol">vlm control</a><br><span style="color:#9fb2c7">Update the image-backed dataset, plan/submit remote training, then promote the resulting adapter from VLM Control.</span></header>
<div class="wrap">
<section class="card"><h2>Dataset</h2><p>Exports crawler + teacher + channel-surf + graph experience into SFT JSONL. This still does not let the VLM press buttons.</p><label>Run ID</label><input id="run_id" value="latest"><label>Max records, 0 = all</label><input id="max_records" value="0"><label><input id="include_raw" type="checkbox" style="width:auto"> include raw records</label><br><button onclick="stats()">Stats</button><button class="good" onclick="exportData()">Update/export dataset</button><pre id="dataset_out">ready</pre></section>
<section class="card"><h2>Remote training</h2><label>Dataset dir</label><input id="dataset_dir" value="learning_datasets/latest"><label>Model</label><select id="model"><option>Qwen/Qwen3-VL-8B-Instruct</option><option>Qwen/Qwen2.5-VL-7B-Instruct</option></select><label>Hardware</label><select id="hardware"><option>2x3090</option><option>1x3090</option><option>local-3080</option></select><button onclick="planRemote()">Plan remote job</button><button class="warn" onclick="submitRemote(false)">Submit dry-run</button><button class="good" onclick="submitRemote(true)">Execute training</button><pre id="remote_out">ready</pre></section>
<section class="card"><h2>One-click pipeline</h2><p>Export/update dataset, generate job files, and optionally launch training.</p><label><input id="execute_pipeline" type="checkbox" style="width:auto"> execute remote training after export</label><button class="purple" onclick="trainFromLatest()">Update dataset -> initiate training</button><pre id="pipeline_out">ready</pre></section>
<section class="card"><h2>Training overview</h2><button onclick="overview()">Refresh overview</button><button onclick="location.href='/vlmcontrol'">Open VLM Control</button><pre id="overview_out">ready</pre></section>
<section class="card wide"><h2>Safety state</h2><p><span class="pill">VLM actuation disabled</span><span class="pill">shadow mode supported</span><span class="pill">crawler/app remains execution authority</span></p></section>
</div>
<script>
async function api(u,b=null){let opt=b?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}:{};let r=await fetch(u,opt);let t=await r.text();try{return JSON.parse(t)}catch(e){return {ok:false,status:r.status,raw:t}}}
async function stats(){dataset_out.textContent=JSON.stringify(await api('/api/learning/stats'),null,2)}
async function exportData(){dataset_out.textContent='exporting...';let j=await api('/api/learning/export',{run_id:run_id.value,max_records:+max_records.value,include_raw:include_raw.checked});dataset_out.textContent=JSON.stringify(j,null,2);if(j.dataset_dir)dataset_dir.value=j.dataset_dir;}
async function planRemote(){remote_out.textContent=JSON.stringify(await api('/api/learning/remote/plan',{dataset_dir:dataset_dir.value,model:model.value,hardware:hardware.value}),null,2)}
async function submitRemote(execute){remote_out.textContent=execute?'submitting training...':'dry-run submit...';remote_out.textContent=JSON.stringify(await api('/api/learning/remote/submit',{dataset_dir:dataset_dir.value,model:model.value,hardware:hardware.value,execute}),null,2)}
async function trainFromLatest(){pipeline_out.textContent='pipeline running...';let j=await api('/api/learning/train_from_latest',{run_id:run_id.value,max_records:+max_records.value,include_raw:include_raw.checked,model:model.value,hardware:hardware.value,execute:execute_pipeline.checked});pipeline_out.textContent=JSON.stringify(j,null,2);if(j.export&&j.export.dataset_dir)dataset_dir.value=j.export.dataset_dir;}
async function overview(){overview_out.textContent=JSON.stringify(await api('/api/learning/training/overview'),null,2)}
stats();overview();
</script></body></html>
        ''',
        mimetype="text/html",
    )

"""


def patch_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text
    if PATCH_VERSION in text:
        print(f"{PATCH_VERSION} already present; no changes needed")
        return False

    text = re.sub(
        r"\n# ---- Compatibility alias: old UI link used /vlmcontrol without underscore ----\n@app\.route\(\"/vlmcontrol\".*?return redirect\(\"/vlm_control\", code=302\)\n",
        "\n",
        text,
        flags=re.S,
    )

    learning_pat = r"@app\.route\(\"/learning\"\)\ndef learning_page\(\) -> Response:\n.*?\n\n@app\.route\(\"/api/learning/stats\", methods=\[\"GET\"\]\)"
    text2, n = re.subn(learning_pat, LEARNING_PAGE_REPLACEMENT + '@app.route("/api/learning/stats", methods=["GET"])', text, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f"Expected to replace exactly one /learning page block; replaced {n}")
    text = text2

    marker = '@app.route("/learning")\ndef learning_page() -> Response:'
    idx = text.find(marker)
    if idx == -1:
        raise SystemExit("Could not find learning page insertion marker after replacement")
    text = text[:idx] + VLM_CONTROL_BLOCK + "\n" + text[idx:]

    backup = path.with_suffix(path.suffix + ".bak-restore-vlm-ui-" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    backup.write_text(original, encoding="utf-8")
    path.write_text(text, encoding="utf-8")
    print(f"Patched: {path}")
    print(f"Backup:  {backup}")
    return True


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "merged_app.py").resolve()
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        return 2
    changed = patch_file(path)
    py_compile.compile(str(path), doraise=True)
    print("py_compile: OK")
    txt = path.read_text(encoding="utf-8")
    checks = [
        '/vlmcontrol', '/vlm_control', '/api/vlm/control/overview', '/api/vlm/control/promote',
        '/api/vlm/control/shadow/restart', '/api/vlm/shadow/analyze', '/api/vlm/shadow/policy',
        '/api/learning/train_from_latest', 'Update dataset -> initiate training', PATCH_VERSION,
    ]
    for c in checks:
        print(f"check {c}: {'OK' if c in txt else 'MISSING'}")
    print("Restart Flask app, then verify on the actual Werkzeug port, usually 8503:")
    print("  curl -s http://127.0.0.1:8503/api/vlm/control/overview | python3 -m json.tool")
    print("  curl -I http://127.0.0.1:8503/vlmcontrol")
    print("  curl -s http://127.0.0.1:8503/api/learning/train_from_latest -H 'Content-Type: application/json' -d '{\"run_id\":\"latest\",\"execute\":false}' | python3 -m json.tool")
    return 0 if changed else 0


if __name__ == "__main__":
    raise SystemExit(main())

