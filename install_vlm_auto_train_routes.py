#!/usr/bin/env python3
from __future__ import annotations
import py_compile, re, shutil, sys
from datetime import datetime
from pathlib import Path

PATCH_MARKER = "# vlm-auto-train-routes-20260617"

# Route code injected into merged_app.py
NEW_ROUTES = '\n# ── VLM Auto-Train API routes (vlm-auto-train-routes-20260617) ──────────\n\n@app.route("/api/learning/auto_train/history", methods=["GET"])\ndef api_vlm_auto_train_history():\n    try:\n        from vlm_auto_train import latest_auto_train_record\n        record = latest_auto_train_record(root=str(ROOT))\n        return jsonify(ok=True, record=record)\n    except Exception as exc:\n        log.exception("auto_train history error")\n        return jsonify(ok=False, error=str(exc)), 500\n\n\n@app.route("/api/learning/auto_train/trigger", methods=["POST"])\ndef api_vlm_auto_train_trigger():\n    import threading\n    try:\n        from vlm_auto_train import auto_train_pipeline\n        data = request.get_json(silent=True) or {}\n        execute        = bool(data.get("execute",        False))\n        dry_run_export = bool(data.get("dry_run_export", False))\n        kwargs = dict(\n            root           = str(ROOT),\n            execute        = execute,\n            dry_run_export = dry_run_export,\n            min_screen     = int(data.get("min_screen",  250)),\n            min_policy     = int(data.get("min_policy",  250)),\n            min_verify     = int(data.get("min_verify",  250)),\n            min_images     = int(data.get("min_images",  100)),\n            hardware       = str(data.get("hardware",    "2x3090")),\n            log_file       = str(ROOT / "logs" / "vlm_auto_train.log"),\n        )\n        t = threading.Thread(target=auto_train_pipeline, kwargs=kwargs, daemon=True)\n        t.start()\n        return jsonify(\n            ok=True,\n            message="Auto-train pipeline started in background.",\n            execute=execute,\n            dry_run_export=dry_run_export,\n        )\n    except Exception as exc:\n        log.exception("auto_train trigger error")\n        return jsonify(ok=False, error=str(exc)), 500\n\n# vlm-auto-train-routes-20260617\n'


def patch_merged_app(path):
    text = path.read_text(encoding="utf-8")
    if PATCH_MARKER in text:
        print(f"{path.name}: already patched")
        return
    anchor = re.search(r"^if __name__", text, re.M)
    if anchor:
        pos = anchor.start()
        text = text[:pos] + NEW_ROUTES + text[pos:]
    else:
        text += NEW_ROUTES
    path.write_text(text, encoding="utf-8")
    print(f"Patched {path.name}: added auto-train API routes")


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    app_path = root / "merged_app.py"
    if not app_path.is_file():
        print(f"ERROR: merged_app.py not found under {root}", file=sys.stderr)
        return 2
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = app_path.with_name(f"merged_app.py.bak-vlm-auto-train-{stamp}")
    shutil.copy2(app_path, backup)
    print(f"Backup: {backup}")
    patch_merged_app(app_path)
    py_compile.compile(str(app_path), doraise=True)
    print(f"py_compile OK: {app_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
