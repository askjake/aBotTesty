#!/usr/bin/env python3
"""
Surgical aBotTesty repair for VLM UI/API compatibility.

This script patches the *current* merged_app.py in-place. It does NOT replace your
repo with an older zip. It only adds missing compatibility routes:

  - GET /api/learning/training/overview
  - GET /vlm_control  -> lightweight redirect/alias to /learning

It also adds DEFAULT_CONFIG["vlm_adapter_dir"] if missing.
A timestamped backup is created before any write.
"""
from __future__ import annotations

import argparse
import py_compile
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


ROUTE_BLOCK = r'''

# ---- aBotTesty VLM compatibility routes: added by repair_abot_vlm_routes.py ----
def _abot_vlm_local_adapter_runs():
    """Best-effort scan of locally pulled VLM adapter directories."""
    runs = []
    try:
        adapter_root = (ROOT / str(CFG.get("vlm_adapter_dir", "models/vlm_adapters"))).resolve()
        if not adapter_root.exists():
            return runs
        for d in sorted([p for p in adapter_root.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True):
            adapter = d / "adapter_model.safetensors"
            cfg = d / "adapter_config.json"
            trainer_state = d / "trainer_state.json"
            metrics = {}
            if trainer_state.is_file():
                try:
                    state = json.loads(trainer_state.read_text(encoding="utf-8"))
                    metrics = {
                        "best_metric": state.get("best_metric"),
                        "global_step": state.get("global_step"),
                        "epoch": state.get("epoch"),
                    }
                except Exception:
                    metrics = {}
            runs.append({
                "run_name": d.name,
                "local_dir": str(d),
                "adapter_model": str(adapter) if adapter.is_file() else "",
                "adapter_config": str(cfg) if cfg.is_file() else "",
                "has_adapter": adapter.is_file(),
                "adapter_size_mb": round(adapter.stat().st_size / (1024 * 1024), 2) if adapter.is_file() else 0,
                "mtime": d.stat().st_mtime,
                "metrics": metrics,
            })
    except Exception as exc:
        log.exception("local adapter scan failed: %s", exc)
    return runs


@app.route("/api/learning/training/overview", methods=["GET"])
def api_learning_training_overview():
    """Compatibility endpoint for newer VLM training dashboard polling.

    This endpoint is intentionally local/best-effort so the UI does not break if
    the remote trainer is unavailable. Promotion/restart code can still return
    richer run data from its own endpoint when present.
    """
    local_runs = _abot_vlm_local_adapter_runs()
    active_adapter_path = str(
        CFG.get("vlm_active_adapter_path")
        or os.getenv("ABOT_VLM_ADAPTER")
        or os.getenv("VLM_ADAPTER_PATH")
        or ""
    )
    active_run = ""
    if active_adapter_path:
        active_run = Path(active_adapter_path).name
    elif local_runs:
        # Fallback: newest local adapter. This is a display hint, not a promotion action.
        active_run = local_runs[0].get("run_name", "")
        active_adapter_path = local_runs[0].get("local_dir", "")

    return jsonify({
        "ok": True,
        "source": "local_adapter_cache_compat",
        "active_run": active_run,
        "health_adapter_path": active_adapter_path,
        "host": str(CFG.get("vlm_remote_host", "")),
        "remote_root": str(CFG.get("vlm_remote_root", "")),
        "local_adapter_root": str((ROOT / str(CFG.get("vlm_adapter_dir", "models/vlm_adapters"))).resolve()),
        "local_runs": local_runs,
        "remote_runs": [],
        "note": "Compatibility route added locally; remote run inventory may be served by a newer trainer endpoint if present.",
    })


@app.route("/vlm_control", methods=["GET"])
def vlm_control_page():
    """Compatibility alias for UIs/bookmarks that still request /vlm_control."""
    return Response("""<!doctype html>
<html><head><meta charset=\"utf-8\"><title>aBotTesty VLM Control</title>
<meta http-equiv=\"refresh\" content=\"0; url=/learning\">
<style>body{font-family:system-ui,Arial,sans-serif;margin:2rem;line-height:1.4}</style></head>
<body><h2>aBotTesty VLM Control moved</h2>
<p>Opening <a href=\"/learning\">/learning</a>...</p>
<script>window.location.replace('/learning');</script>
</body></html>""", mimetype="text/html")
# ---- end aBotTesty VLM compatibility routes ----
'''


def has_route(text: str, route: str) -> bool:
    return bool(re.search(r"@app\.route\(\s*['\"]" + re.escape(route) + r"['\"]", text))


def patch_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text

    # Add config default only if missing.
    if '"vlm_adapter_dir"' not in text and "'vlm_adapter_dir'" not in text:
        needle = '"learning_dataset_image_max_width": 960,'
        if needle in text:
            text = text.replace(needle, needle + '\n    "vlm_adapter_dir": "models/vlm_adapters",', 1)
        else:
            # Non-fatal: the route itself still falls back to models/vlm_adapters.
            print("WARN: Could not find learning_dataset_image_max_width config anchor; route fallback still works.")

    need_training = not has_route(text, "/api/learning/training/overview")
    need_vlm_control = not has_route(text, "/vlm_control")

    if need_training or need_vlm_control:
        block = ROUTE_BLOCK
        if not need_training:
            # If only /vlm_control is missing, keep just the alias block.
            m = re.search(r'\n\n@app\.route\("/vlm_control"[\s\S]+?# ---- end aBotTesty VLM compatibility routes ----\n', block)
            block = m.group(0) if m else block
        elif not need_vlm_control:
            # If only training overview is missing, remove the /vlm_control function.
            block = re.sub(r'\n\n@app\.route\("/vlm_control"[\s\S]+?mimetype="text/html"\)\n', '\n', block)

        insert_markers = ["\ndef _find_available_port(", "\ndef main() -> None:", "\nif __name__ == \"__main__\":"]
        inserted = False
        for marker in insert_markers:
            idx = text.find(marker)
            if idx != -1:
                text = text[:idx] + block + text[idx:]
                inserted = True
                break
        if not inserted:
            text = text.rstrip() + block + "\n"

    if text == original:
        print("No changes needed: routes/config already present.")
        return False

    backup = path.with_suffix(path.suffix + ".bak-vlm-routes-" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(path, backup)
    path.write_text(text, encoding="utf-8")
    print(f"Patched: {path}")
    print(f"Backup:  {backup}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="merged_app.py", help="Path to merged_app.py; default: ./merged_app.py")
    args = ap.parse_args()

    path = Path(args.path).resolve()
    if not path.is_file():
        print(f"ERROR: not found: {path}", file=sys.stderr)
        return 2

    changed = patch_file(path)
    try:
        py_compile.compile(str(path), doraise=True)
        print("py_compile: OK")
    except Exception as exc:
        print(f"py_compile: FAILED: {exc}", file=sys.stderr)
        return 1

    text = path.read_text(encoding="utf-8")
    for route in ["/api/learning/training/overview", "/vlm_control"]:
        print(f"route {route}: {'OK' if has_route(text, route) else 'MISSING'}")

    if changed:
        print("Restart the app, then verify:")
        print("  curl -s http://127.0.0.1:8502/api/learning/training/overview | python3 -m json.tool")
        print("  curl -I http://127.0.0.1:8502/vlm_control")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

