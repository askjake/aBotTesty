#!/usr/bin/env python3
"""Patch aBotTesty learning export/training UX hardening.

Adds a safe export wrapper so /api/learning/export and /api/learning/train_from_latest
no longer fail when run_id=latest already exists. Instead, unless overwrite=true is
provided, it creates a timestamped dataset run like latest_20260602_120102.

Also improves the dataset overlay status pill so it does not sit at 'loading...' after
stats are already visible.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import sys

PATCH_MARKER = "v38.9-learning-export-safe-status-20260602"

HELPER_BLOCK = r'''

# ---- aBotTesty safe learning export helper (v38.9-learning-export-safe-status-20260602) ----
def _abot_dataset_run_dir(run_id):
    dataset_root = ROOT / str(CFG.get("learning_dataset_dir", "learning_datasets"))
    if not run_id:
        return None
    return dataset_root / str(run_id)


def _abot_unique_dataset_run_id(prefix="latest"):
    raw = str(prefix or "latest").strip() or "latest"
    raw = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in raw).strip("_") or "latest"
    return f"{raw}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _abot_learning_export_safe(run_id=None, max_records=0, include_raw=False, overwrite=False, unique_if_exists=True):
    """Export a learning dataset without wedging the UI on an existing run_id.

    learning_dataset_writer.export() intentionally refuses to overwrite an existing
    dataset directory. That is correct for reproducibility, but the UI often uses
    run_id=latest. If latest already exists, the button looks stuck and returns 500.
    This wrapper keeps reproducibility while making the UI usable: existing names are
    converted to a timestamped run unless overwrite=true is explicitly requested.
    """
    import shutil

    requested_run_id = str(run_id or "").strip() or None
    effective_run_id = requested_run_id
    note = ""

    if effective_run_id:
        out_dir = _abot_dataset_run_dir(effective_run_id)
        if out_dir is not None and out_dir.exists():
            if overwrite:
                if out_dir.is_symlink() or out_dir.is_file():
                    out_dir.unlink()
                else:
                    shutil.rmtree(out_dir)
                note = f"overwrote existing dataset export {out_dir}"
            elif unique_if_exists:
                old = effective_run_id
                effective_run_id = _abot_unique_dataset_run_id(old)
                note = f"requested run_id {old!r} already existed; exported as {effective_run_id!r}"
            else:
                raise FileExistsError(f"dataset export already exists: {out_dir}")

    try:
        export = _learning_writer().export(
            run_id=effective_run_id,
            max_records=int(max_records or 0),
            include_raw=bool(include_raw),
        )
    except FileExistsError:
        if not unique_if_exists:
            raise
        fallback = _abot_unique_dataset_run_id(effective_run_id or requested_run_id or "latest")
        export = _learning_writer().export(
            run_id=fallback,
            max_records=int(max_records or 0),
            include_raw=bool(include_raw),
        )
        note = f"fallback export used timestamped run_id {fallback!r} after FileExistsError"
        effective_run_id = fallback

    try:
        if isinstance(export, dict):
            export.setdefault("requested_run_id", requested_run_id)
            export.setdefault("effective_run_id", effective_run_id)
            export.setdefault("safe_export", True)
            if note:
                export.setdefault("note", note)
    except Exception:
        pass
    return export
# ---- end aBotTesty safe learning export helper ----
'''


def insert_helper(text: str) -> str:
    if PATCH_MARKER in text:
        return text
    anchor = '@app.route("/api/learning/export"'
    idx = text.find(anchor)
    if idx < 0:
        raise SystemExit("Could not find /api/learning/export route anchor")
    return text[:idx].rstrip() + HELPER_BLOCK + "\n\n" + text[idx:]


def patch_export_route(text: str) -> str:
    old = 'return jsonify(_learning_writer().export(run_id=run_id, max_records=max_records, include_raw=include_raw))'
    new = 'return jsonify(_abot_learning_export_safe(run_id=run_id, max_records=max_records, include_raw=include_raw, overwrite=str(data.get("overwrite", request.args.get("overwrite", "false"))).lower() in {"1", "true", "yes", "on"}, unique_if_exists=True))'
    if old in text:
        text = text.replace(old, new, 1)
    return text


def patch_train_from_latest(text: str) -> str:
    old = '''        export = _learning_writer().export(
            run_id=run_id,
            max_records=int(data.get("max_records") or 0),
            include_raw=bool(data.get("include_raw", False)),
        )'''
    new = '''        export = _abot_learning_export_safe(
            run_id=run_id,
            max_records=int(data.get("max_records") or 0),
            include_raw=bool(data.get("include_raw", False)),
            overwrite=bool(data.get("overwrite", False)),
            unique_if_exists=True,
        )'''
    if old in text:
        text = text.replace(old, new, 1)
    else:
        # Regex fallback for minor whitespace drift.
        pattern = re.compile(r'        export = _learning_writer\(\)\.export\(\n\s*run_id=run_id,\n\s*max_records=int\(data\.get\("max_records"\) or 0\),\n\s*include_raw=bool\(data\.get\("include_raw", False\)\),\n\s*\)', re.M)
        text = pattern.sub(new, text, count=1)
    return text


def patch_overlay_pill(text: str) -> str:
    # Make the panel header useful and remove the misleading permanent-looking 'loading'.
    replacements = {
        'pill.textContent = "updated " + (j.ts || "");': 'pill.textContent = "ready - " + fmt(e.total_sft_rows) + " SFT rows - " + fmt(avail.raw_files_new_since_latest_export) + " new files" + (j.ts ? " - " + j.ts : "");',
        'pill.textContent = "loading...";': 'pill.textContent = "refreshing...";',
        'pill.textContent = "loading.";': 'pill.textContent = "refreshing...";',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def patch_learning_js(text: str) -> str:
    # Make button feedback clearer in the existing learning page JS.
    text = text.replace("dataset_out.textContent='exporting.';", "dataset_out.textContent='exporting dataset; existing names will auto-version instead of failing.';")
    text = text.replace("pipeline_out.textContent='pipeline running.';", "pipeline_out.textContent='exporting dataset and preparing remote training; existing names will auto-version.';")
    return text


def patch_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    before = text
    text = insert_helper(text)
    text = patch_export_route(text)
    text = patch_train_from_latest(text)
    text = patch_overlay_pill(text)
    text = patch_learning_js(text)

    if text == before:
        print("No changes made; file may already be patched")
    backup = path.with_suffix(path.suffix + ".bak-learning-export-safe-" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    backup.write_text(before, encoding="utf-8")
    path.write_text(text, encoding="utf-8")
    print(f"Patched: {path}")
    print(f"Backup:  {backup}")

    checks = {
        "patch_marker": PATCH_MARKER in text,
        "safe_helper": "def _abot_learning_export_safe" in text,
        "export_route_uses_safe_helper": "jsonify(_abot_learning_export_safe" in text,
        "train_from_latest_uses_safe_helper": "export = _abot_learning_export_safe(" in text,
        "overlay_ready_pill": "ready - " in text,
    }
    for name, ok in checks.items():
        print(f"check {name}: {'OK' if ok else 'MISSING'}")
    return 0 if all(checks.values()) else 3


def main() -> int:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "merged_app.py").resolve()
    if not target.is_file():
        print(f"ERROR: not found: {target}", file=sys.stderr)
        return 2
    rc = patch_file(target)
    if rc:
        return rc
    import py_compile
    py_compile.compile(str(target), doraise=True)
    print("py_compile target: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

