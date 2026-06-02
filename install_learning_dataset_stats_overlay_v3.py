#!/usr/bin/env python3
"""Install a lightweight dataset statistics overlay for aBotTesty.

Patches merged_app.py in-place by adding:
  - /api/learning/dataset/overview
  - an after_request HTML overlay injected into /learning and /vlmcontrol pages

v3 fix:
  - No str.format() around JavaScript/CSS braces.
  - Plain ASCII.
  - Installer validates its own output.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import py_compile
import sys

PATCH_MARKER = 'v38.8-learning-dataset-stats-overlay-20260602-v3'
PATCH_BLOCK = '\n# ---- aBotTesty learning dataset stats overlay (v38.8-learning-dataset-stats-overlay-20260602-v3) ----\ndef _abot_count_jsonl(path):\n    try:\n        p = Path(path)\n        if not p.is_file():\n            return 0\n        n = 0\n        with p.open("r", encoding="utf-8", errors="ignore") as fh:\n            for line in fh:\n                if line.strip():\n                    n += 1\n        return n\n    except Exception:\n        return 0\n\n\ndef _abot_file_stat(path):\n    try:\n        p = Path(path)\n        if not p.exists():\n            return {"exists": False, "path": str(p)}\n        st = p.stat()\n        return {\n            "exists": True,\n            "path": str(p),\n            "size_bytes": int(st.st_size),\n            "mtime": float(st.st_mtime),\n            "mtime_iso": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),\n        }\n    except Exception as exc:\n        return {"exists": False, "path": str(path), "error": str(exc)}\n\n\ndef _abot_find_latest_dataset_export(dataset_root):\n    root = Path(dataset_root)\n    if not root.exists():\n        return None\n    candidates = []\n    scan_roots = [root]\n    try:\n        scan_roots += [x for x in root.iterdir() if x.is_dir()]\n    except Exception:\n        pass\n    for p in scan_roots:\n        has_data = (p / "episodes.jsonl").is_file() or (p / "manifest.json").is_file() or (p / "sft").is_dir()\n        if has_data:\n            try:\n                mt = max([x.stat().st_mtime for x in p.rglob("*") if x.is_file()] or [p.stat().st_mtime])\n            except Exception:\n                try:\n                    mt = p.stat().st_mtime\n                except Exception:\n                    mt = 0.0\n            candidates.append((mt, p))\n    if not candidates:\n        return None\n    return sorted(candidates, key=lambda x: x[0], reverse=True)[0][1]\n\n\ndef _abot_count_dataset_export(export_dir):\n    if export_dir is None:\n        return {\n            "path": "",\n            "exists": False,\n            "episodes": 0,\n            "screen_perception": 0,\n            "action_policy": 0,\n            "outcome_verifier": 0,\n            "total_sft_rows": 0,\n            "images": 0,\n            "size_bytes": 0,\n            "size_mb": 0.0,\n            "mtime": 0.0,\n            "mtime_iso": "",\n        }\n    root = Path(export_dir)\n    screen = _abot_count_jsonl(root / "sft" / "screen_perception.jsonl")\n    policy = _abot_count_jsonl(root / "sft" / "action_policy.jsonl")\n    verify = _abot_count_jsonl(root / "sft" / "outcome_verifier.jsonl")\n    images_dir = root / "images"\n    try:\n        images = sum(1 for p in images_dir.rglob("*") if p.is_file()) if images_dir.is_dir() else 0\n    except Exception:\n        images = 0\n    try:\n        files = [p for p in root.rglob("*") if p.is_file()]\n        size = sum(p.stat().st_size for p in files)\n        mt = max([p.stat().st_mtime for p in files] or [root.stat().st_mtime])\n    except Exception:\n        size = 0\n        mt = 0.0\n    return {\n        "path": str(root),\n        "exists": True,\n        "episodes": _abot_count_jsonl(root / "episodes.jsonl"),\n        "screen_perception": screen,\n        "action_policy": policy,\n        "outcome_verifier": verify,\n        "total_sft_rows": screen + policy + verify,\n        "images": images,\n        "size_bytes": int(size),\n        "size_mb": round(float(size) / 1048576.0, 3),\n        "mtime": float(mt),\n        "mtime_iso": datetime.fromtimestamp(mt).isoformat(timespec="seconds") if mt else "",\n        "manifest": _abot_file_stat(root / "manifest.json"),\n    }\n\n\ndef _abot_raw_learning_inventory(latest_export_mtime=0.0):\n    crawler_root = Path(CRAWLER_DIR) if "CRAWLER_DIR" in globals() else (ROOT / "crawler_data")\n    out = {\n        "crawler_dir": str(crawler_root),\n        "files": 0,\n        "json_files": 0,\n        "jsonl_files": 0,\n        "jpg_png_files": 0,\n        "bytes": 0,\n        "new_files_since_latest_export": 0,\n        "new_bytes_since_latest_export": 0,\n        "newest_file_mtime": 0.0,\n        "newest_file_mtime_iso": "",\n    }\n    try:\n        for p in crawler_root.rglob("*"):\n            if not p.is_file():\n                continue\n            st = p.stat()\n            out["files"] += 1\n            out["bytes"] += int(st.st_size)\n            suffix = p.suffix.lower()\n            if suffix == ".json":\n                out["json_files"] += 1\n            elif suffix == ".jsonl":\n                out["jsonl_files"] += 1\n            elif suffix in (".jpg", ".jpeg", ".png", ".webp"):\n                out["jpg_png_files"] += 1\n            if st.st_mtime > latest_export_mtime:\n                out["new_files_since_latest_export"] += 1\n                out["new_bytes_since_latest_export"] += int(st.st_size)\n            if st.st_mtime > out["newest_file_mtime"]:\n                out["newest_file_mtime"] = float(st.st_mtime)\n        if out["newest_file_mtime"]:\n            out["newest_file_mtime_iso"] = datetime.fromtimestamp(out["newest_file_mtime"]).isoformat(timespec="seconds")\n        out["size_mb"] = round(float(out["bytes"]) / 1048576.0, 3)\n        out["new_size_mb_since_latest_export"] = round(float(out["new_bytes_since_latest_export"]) / 1048576.0, 3)\n    except Exception as exc:\n        out["error"] = str(exc)\n    return out\n\n\ndef _abot_graph_learning_stats():\n    stats = {"states": 0, "edges": 0, "actions": 0, "running": False, "steps": 0}\n    try:\n        st = crawler.status() if "crawler" in globals() else {}\n        stats["running"] = bool(st.get("running"))\n        stats["steps"] = int(st.get("steps") or 0)\n        stats["states"] = int(st.get("node_count") or st.get("states") or 0)\n        stats["edges"] = int(st.get("edge_count") or st.get("edges") or 0)\n        if not stats["states"] and "crawler" in globals() and hasattr(crawler, "graph"):\n            stats["states"] = len(getattr(crawler.graph, "states", {}) or {})\n        if not stats["edges"] and "crawler" in globals() and hasattr(crawler, "graph"):\n            stats["edges"] = len(getattr(crawler.graph, "edges", {}) or {})\n        if "crawler" in globals() and hasattr(crawler, "brain"):\n            q = getattr(crawler.brain, "q", None) or getattr(crawler.brain, "state_actions", None) or {}\n            try:\n                stats["actions"] = len(q)\n            except Exception:\n                stats["actions"] = 0\n    except Exception as exc:\n        stats["error"] = str(exc)\n    return stats\n\n\ndef _abot_active_vlm_summary():\n    p = ROOT / "models" / "vlm_adapters" / "active_vlm.json"\n    try:\n        if p.is_file():\n            data = json.loads(p.read_text(encoding="utf-8"))\n            return {\n                "exists": True,\n                "path": str(p),\n                "run_name": data.get("run_name", ""),\n                "model": data.get("model", ""),\n                "source": data.get("source", ""),\n                "promoted_at": data.get("promoted_at", ""),\n                "actuation": data.get("actuation", ""),\n            }\n    except Exception as exc:\n        return {"exists": False, "path": str(p), "error": str(exc)}\n    return {"exists": False, "path": str(p), "run_name": ""}\n\n\n@app.route("/api/learning/dataset/overview", methods=["GET"])\ndef api_learning_dataset_overview():\n    dataset_root = ROOT / str(CFG.get("learning_dataset_dir", "learning_datasets"))\n    latest = _abot_find_latest_dataset_export(dataset_root)\n    latest_export = _abot_count_dataset_export(latest)\n    raw = _abot_raw_learning_inventory(float(latest_export.get("mtime") or 0.0))\n    graph = _abot_graph_learning_stats()\n    derived_available = {\n        "raw_files_new_since_latest_export": raw.get("new_files_since_latest_export", 0),\n        "raw_mb_new_since_latest_export": raw.get("new_size_mb_since_latest_export", 0),\n        "graph_states_current": graph.get("states", 0),\n        "graph_edges_current": graph.get("edges", 0),\n        "latest_export_sft_rows": latest_export.get("total_sft_rows", 0),\n        "note": "Best-effort readiness signal. Exact trainable rows are finalized during export/update dataset.",\n    }\n    payload = {\n        "ok": True,\n        "patch_version": "v38.8-learning-dataset-stats-overlay-20260602-v3",\n        "dataset_root": str(dataset_root),\n        "latest_export": latest_export,\n        "raw_inventory": raw,\n        "graph": graph,\n        "available_to_train": derived_available,\n        "active_vlm": _abot_active_vlm_summary(),\n        "ts": datetime.now().isoformat(timespec="seconds"),\n    }\n    return jsonify(payload)\n\n\ndef _abot_dataset_stats_overlay_html():\n    return """\n<script id="abotDatasetStatsOverlay">\n(function(){\n  if (window.__abotDatasetStatsOverlayLoaded) return;\n  window.__abotDatasetStatsOverlayLoaded = true;\n  function fmt(n){\n    if(n === null || n === undefined || isNaN(Number(n))) return "0";\n    return Number(n).toLocaleString();\n  }\n  function esc(s){ return String(s === undefined || s === null ? "" : s).replace(/[&<>]/g, function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;"}[c];}); }\n  function makePanel(){\n    var panel = document.createElement("section");\n    panel.id = "abotDatasetStatsPanel";\n    panel.style.cssText = "margin:14px;padding:14px;border:1px solid #2d3b4b;border-radius:14px;background:#101821;color:#eef6ff;font-family:Segoe UI,Arial,sans-serif;box-shadow:0 8px 24px rgba(0,0,0,.22)";\n    panel.innerHTML = \'<div style="display:flex;justify-content:space-between;align-items:center;gap:8px"><b>Learning Dataset</b><span id="abotDsPill" style="font-size:12px;color:#9fb2c7">loading...</span></div><div id="abotDsGrid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin-top:10px"></div><div id="abotDsDetail" style="margin-top:10px;color:#9fb2c7;font-size:12px;white-space:pre-wrap"></div><button id="abotDsRefresh" style="margin-top:10px;background:#1c3045;color:white;border:1px solid #36506a;border-radius:10px;padding:7px 10px;cursor:pointer">Refresh dataset stats</button>\';\n    var main = document.querySelector("main") || document.body;\n    if (main.firstChild) main.insertBefore(panel, main.firstChild); else main.appendChild(panel);\n    document.getElementById("abotDsRefresh").onclick = loadStats;\n  }\n  function card(label, value, sub){\n    return \'<div style="background:#17212c;border:1px solid #2d3b4b;border-radius:12px;padding:9px"><div style="font-size:20px;font-weight:700">\'+esc(value)+\'</div><div style="font-size:12px;color:#9fb2c7">\'+esc(label)+\'</div>\'+(sub?\'<div style="font-size:11px;color:#7890a7;margin-top:3px">\'+esc(sub)+\'</div>\':\'\')+\'</div>\';\n  }\n  async function loadStats(){\n    var pill = document.getElementById("abotDsPill");\n    var grid = document.getElementById("abotDsGrid");\n    var detail = document.getElementById("abotDsDetail");\n    if(!pill || !grid || !detail) return;\n    pill.textContent = "loading...";\n    try{\n      var r = await fetch("/api/learning/dataset/overview", {cache:"no-store"});\n      var j = await r.json();\n      if(!j.ok) throw new Error(j.error || "dataset overview failed");\n      var e = j.latest_export || {};\n      var raw = j.raw_inventory || {};\n      var g = j.graph || {};\n      var avail = j.available_to_train || {};\n      var active = j.active_vlm || {};\n      grid.innerHTML = [\n        card("Episodes", fmt(e.episodes), "latest export"),\n        card("Images", fmt(e.images), "latest export"),\n        card("Screen rows", fmt(e.screen_perception), "SFT"),\n        card("Policy rows", fmt(e.action_policy), "SFT"),\n        card("Verifier rows", fmt(e.outcome_verifier), "SFT"),\n        card("Total SFT", fmt(e.total_sft_rows), "trainable rows"),\n        card("Graph states", fmt(g.states), "current crawler graph"),\n        card("Graph edges", fmt(g.edges), "current crawler graph"),\n        card("New raw files", fmt(avail.raw_files_new_since_latest_export), "since latest export"),\n        card("New raw MB", fmt(avail.raw_mb_new_since_latest_export), "since latest export")\n      ].join("");\n      pill.textContent = "updated " + (j.ts || "");\n      detail.textContent = "Latest export: " + (e.path || "none") + "\\\\n" +\n        "Latest export mtime: " + (e.mtime_iso || "") + "\\\\n" +\n        "Raw crawler data: " + (raw.crawler_dir || "") + " (" + fmt(raw.files) + " files, " + fmt(raw.size_mb) + " MB)\\\\n" +\n        "Active VLM: " + (active.run_name || "none") + " " + (active.model ? "(" + active.model + ")" : "") + "\\\\n" +\n        "Note: " + ((avail && avail.note) || "");\n    }catch(err){\n      pill.textContent = "error";\n      detail.textContent = String(err && err.stack ? err.stack : err);\n    }\n  }\n  function boot(){ makePanel(); loadStats(); setInterval(loadStats, 30000); }\n  if(document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();\n})();\n</script>\n"""\n\n\n@app.after_request\ndef _abot_inject_dataset_stats_overlay(resp):\n    try:\n        if request.path not in ("/learning", "/vlmcontrol", "/vlm_control", "/vlm-control"):\n            return resp\n        ctype = str(resp.headers.get("Content-Type", ""))\n        if "text/html" not in ctype.lower():\n            return resp\n        html = resp.get_data(as_text=True)\n        if "abotDatasetStatsOverlay" in html:\n            return resp\n        overlay = _abot_dataset_stats_overlay_html()\n        pos = html.lower().rfind("</body>")\n        if pos >= 0:\n            html = html[:pos] + overlay + html[pos:]\n        else:\n            html = html + overlay\n        resp.set_data(html)\n        resp.headers["Content-Length"] = str(len(resp.get_data()))\n    except Exception:\n        try:\n            log.exception("dataset stats overlay injection failed")\n        except Exception:\n            pass\n    return resp\n# ---- end aBotTesty learning dataset stats overlay ----\n'


def patch_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    old_markers = [
        "v38.8-learning-dataset-stats-overlay-20260602",
        "v38.8-learning-dataset-stats-overlay-20260602-v2",
        PATCH_MARKER,
    ]
    if any(m in text for m in old_markers):
        print(f"Already appears patched: {path}")
        return

    marker_positions = [
        text.find('if __name__ == "__main__":'),
        text.find("if __name__ == '__main__':"),
    ]
    positions = [p for p in marker_positions if p >= 0]
    if not positions:
        raise SystemExit("Could not find __main__ guard. Refusing to patch.")
    insert_at = min(positions)

    backup = path.with_suffix(path.suffix + ".bak-dataset-stats-v3-" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    backup.write_text(text, encoding="utf-8")

    new_text = text[:insert_at].rstrip() + "\n\n" + PATCH_BLOCK + "\n\n" + text[insert_at:].lstrip()
    path.write_text(new_text, encoding="utf-8")
    print(f"Patched: {path}")
    print(f"Backup:  {backup}")


def main() -> int:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "merged_app.py").resolve()
    if not target.is_file():
        print(f"ERROR: not found: {target}", file=sys.stderr)
        return 2

    # Validate installer before touching target.
    py_compile.compile(str(Path(__file__).resolve()), doraise=True)

    patch_file(target)

    updated = target.read_text(encoding="utf-8")
    checks = {
        "patch_marker": PATCH_MARKER in updated,
        "dataset_overview_route": '/api/learning/dataset/overview' in updated,
        "after_request_overlay": 'def _abot_inject_dataset_stats_overlay' in updated,
        "overlay_script": 'abotDatasetStatsOverlay' in updated,
    }
    for name, ok in checks.items():
        print(f"check {name}: {'OK' if ok else 'MISSING'}")
    if not all(checks.values()):
        return 3

    # Validate target syntax after patch.
    py_compile.compile(str(target), doraise=True)
    print("py_compile target: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

