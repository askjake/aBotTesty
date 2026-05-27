#!/usr/bin/env python3
"""Idempotently wires v37 Phase-1 dataset/remote-training APIs into merged_app.py.

Run from the repository root after copying this patch bundle in:
    python tools/apply_v37_phase1_patch.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "merged_app.py"

IMPORT_LINE = "from learning_dataset_writer import LearningDatasetWriter  # noqa: E402\nfrom vlm_remote_trainer import VLMRemoteJob, prepare_job_files, submit_job  # noqa: E402\n"
CONFIG_INSERT = '''
    "learning_dataset_dir": "learning_datasets",
    "learning_dataset_image_max_width": 960,
    "vlm_remote_host": "10.79.85.35",
    "vlm_remote_user": "montjac",
    "vlm_remote_root": "~/aBotTesty_vlm_jobs",
    "vlm_default_model_3090": "Qwen/Qwen3-VL-8B-Instruct",
    "vlm_default_model_3080": "Qwen/Qwen2.5-VL-7B-Instruct",
'''
ENDPOINT_BLOCK = r'''

# ---------------------------------------------------------------------------
# v37 Phase 1: multimodal learning dataset export + remote VLM training hooks
# ---------------------------------------------------------------------------

def _learning_writer() -> LearningDatasetWriter:
    return LearningDatasetWriter(
        root_dir=ROOT,
        crawler_dir=CRAWLER_DIR,
        out_dir=ROOT / str(CFG.get("learning_dataset_dir", "learning_datasets")),
        image_max_width=int(CFG.get("learning_dataset_image_max_width", 960)),
    )


@app.route("/learning")
def learning_page() -> Response:
    return Response(
        """
<!doctype html><html><head><meta charset="utf-8"><title>aBotTesty v37 Learning Dataset</title>
<style>body{background:#0d1117;color:#e5edf5;font-family:Segoe UI,Arial,sans-serif;margin:0}header{padding:14px 18px;background:#151b23}main{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:16px}.card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:14px}button{background:#2563eb;color:white;border:0;border-radius:10px;padding:9px 12px;margin:4px;cursor:pointer;font-weight:700}button.warn{background:#b45309}input{background:#0b1016;color:#e5edf5;border:1px solid #3b4450;border-radius:8px;padding:8px;width:95%}pre{white-space:pre-wrap;word-break:break-word;color:#b6c2cf;max-height:560px;overflow:auto}</style></head>
<body><header><b>v37 Phase 1 — Learning Dataset + Remote VLM Trainer</b> · <a href="/monitor" style="color:#93c5fd">monitor</a> · <a href="/intelligence" style="color:#93c5fd">intelligence</a></header>
<main><section class="card"><h2>Dataset exporter</h2><p>Exports before/action/after episodes plus VLM SFT JSONL files. This does not let a model control the STB.</p><input id="run_id" placeholder="optional run id"><br><br><button onclick="stats()">Stats</button><button onclick="exportData()">Export dataset</button><pre id="out">ready</pre></section>
<section class="card"><h2>Remote 2x3090 trainer</h2><p>Default target: montjac@10.79.85.35. Dry-run first; execute only after SSH keys and dataset export are verified.</p><input id="dataset_dir" placeholder="dataset dir" value="learning_datasets/latest"><br><br><input id="model" value="Qwen/Qwen3-VL-8B-Instruct"><br><br><button onclick="planRemote()">Plan remote job</button><button onclick="submitRemote(false)">Submit dry-run</button><button class="warn" onclick="submitRemote(true)">Submit LIVE</button><pre id="remote">ready</pre></section></main>
<script>
async function api(u,b=null){const opt=b?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}:{};const r=await fetch(u,opt);return await r.json()}
async function stats(){out.textContent=JSON.stringify(await api('/api/learning/stats'),null,2)}
async function exportData(){out.textContent='exporting...';out.textContent=JSON.stringify(await api('/api/learning/export',{run_id:run_id.value}),null,2)}
async function planRemote(){remote.textContent=JSON.stringify(await api('/api/learning/remote/plan',{dataset_dir:dataset_dir.value,model:model.value}),null,2)}
async function submitRemote(execute){remote.textContent=JSON.stringify(await api('/api/learning/remote/submit',{dataset_dir:dataset_dir.value,model:model.value,execute,dry_run:!execute}),null,2)}
stats();
</script></body></html>
        """,
        mimetype="text/html",
    )


@app.route("/api/learning/stats", methods=["GET"])
def api_learning_stats():
    try:
        return jsonify(_learning_writer().stats())
    except Exception as exc:
        log.exception("learning stats failed")
        return jsonify(ok=False, error=str(exc)), 500


@app.route("/api/learning/export", methods=["POST", "GET"])
def api_learning_export():
    data = request.get_json(silent=True) or {}
    try:
        max_records = int(data.get("max_records") or request.args.get("max_records") or 0)
        run_id = str(data.get("run_id") or request.args.get("run_id") or "").strip() or None
        include_raw = str(data.get("include_raw", request.args.get("include_raw", "false"))).lower() in {"1", "true", "yes", "on"}
        return jsonify(_learning_writer().export(run_id=run_id, max_records=max_records, include_raw=include_raw))
    except Exception as exc:
        log.exception("learning export failed")
        return jsonify(ok=False, error=str(exc)), 500


def _remote_job_from_request(data: Dict[str, Any]) -> VLMRemoteJob:
    return VLMRemoteJob(
        dataset_dir=str(data.get("dataset_dir") or ROOT / str(CFG.get("learning_dataset_dir", "learning_datasets")) / "latest"),
        host=str(data.get("host") or CFG.get("vlm_remote_host", "10.79.85.35")),
        user=str(data.get("user") or CFG.get("vlm_remote_user", "montjac")),
        remote_root=str(data.get("remote_root") or CFG.get("vlm_remote_root", "~/aBotTesty_vlm_jobs")),
        model_name=str(data.get("model") or CFG.get("vlm_default_model_3090", "Qwen/Qwen3-VL-8B-Instruct")),
        run_name=str(data.get("run_name") or ""),
        ssh_port=int(data.get("ssh_port") or 22),
        dry_run=(bool(data.get("dry_run")) if "dry_run" in data else (not bool(data.get("execute", False)))),
    )


@app.route("/api/learning/remote/plan", methods=["POST", "GET"])
def api_learning_remote_plan():
    data = request.get_json(silent=True) or {}
    try:
        job = _remote_job_from_request(data)
        hardware = str(data.get("hardware") or "2x3090")
        out_dir = ROOT / "vlm_jobs" / job.run_name
        plan = prepare_job_files(job, out_dir=out_dir, hardware=hardware)
        return jsonify(ok=True, dry_run=True, plan=plan)
    except Exception as exc:
        log.exception("remote VLM plan failed")
        return jsonify(ok=False, error=str(exc)), 500


@app.route("/api/learning/remote/submit", methods=["POST"])
def api_learning_remote_submit():
    data = request.get_json(silent=True) or {}
    try:
        job = _remote_job_from_request(data)
        hardware = str(data.get("hardware") or "2x3090")
        out_dir = ROOT / "vlm_jobs" / job.run_name
        prepare_job_files(job, out_dir=out_dir, hardware=hardware)
        return jsonify(submit_job(job, prepared_dir=out_dir))
    except Exception as exc:
        log.exception("remote VLM submit failed")
        return jsonify(ok=False, error=str(exc)), 500

'''


def patch() -> None:
    if not APP.is_file():
        raise FileNotFoundError(APP)
    text = APP.read_text(encoding="utf-8")
    original = text
    if "from learning_dataset_writer import LearningDatasetWriter" not in text:
        anchor = "from jamboree.stb_store import store  # noqa: E402\n"
        if anchor not in text:
            raise RuntimeError("could not find import anchor")
        text = text.replace(anchor, anchor + IMPORT_LINE, 1)
    if '"learning_dataset_dir"' not in text:
        anchor = '    "crawler_flow_lane_card_h": 190,\n'
        if anchor not in text:
            raise RuntimeError("could not find config anchor")
        text = text.replace(anchor, anchor + CONFIG_INSERT, 1)
    if "v37 Phase 1: multimodal learning dataset export" not in text:
        anchor = '@app.route("/api/crawl/start", methods=["POST"])\n'
        if anchor not in text:
            anchor = "@app.route('/api/crawl/start', methods=['POST'])\n"
        if anchor not in text:
            raise RuntimeError("could not find crawl start endpoint anchor")
        text = text.replace(anchor, ENDPOINT_BLOCK + anchor, 1)
    # Add a lightweight monitor link/button only if the known dashboard button area exists.
    if 'window.location=\'/learning\'' not in text and 'window.location=\'/dashboards\'' in text:
        text = text.replace(
            '<button class="secondary" onclick="window.location=\'/dashboards\'">Dashboards</button>',
            '<button class="secondary" onclick="window.location=\'/dashboards\'">Dashboards</button>\n      <button class="secondary" onclick="window.location=\'/learning\'">Learning/VLM</button>',
            1,
        )
    if text != original:
        APP.write_text(text, encoding="utf-8")
        print(f"patched {APP}")
    else:
        print(f"already patched {APP}")


if __name__ == "__main__":
    patch()
