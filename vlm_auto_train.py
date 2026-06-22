#!/usr/bin/env python3
"""vlm_auto_train.py — Automated VLM export + async training orchestrator.

Run by the cron job every Friday afternoon (or manually at any time).

Usage
-----
  python3 vlm_auto_train.py [--root PATH] [--execute] [--min-screen N]
                             [--min-policy N] [--min-verify N] [--min-images N]
                             [--hardware 2x3090|2x3080] [--dry-run-export]
                             [--log-file PATH]

Exit codes
----------
  0  Training job submitted (or dry-run succeeded)
  1  Dataset not ready / below quality threshold (not an error; cron treats as skip)
  2  Hard failure (bad args, filesystem error, SSH error)

This module is also importable so merged_app.py can call
  from vlm_auto_train import auto_train_pipeline
from an API route or a background thread.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Thresholds — override via env vars or CLI flags so cron scripts can tune
# them without editing this file.
# ---------------------------------------------------------------------------
DEFAULT_MIN_SCREEN  = int(os.environ.get("MIN_SCREEN",  "250"))
DEFAULT_MIN_POLICY  = int(os.environ.get("MIN_POLICY",  "250"))
DEFAULT_MIN_VERIFY  = int(os.environ.get("MIN_VERIFY",  "250"))
DEFAULT_MIN_IMAGES  = int(os.environ.get("MIN_IMAGES",  "100"))
DEFAULT_HARDWARE    = os.environ.get("VLM_HARDWARE",    "2x3090")
DEFAULT_HOST        = os.environ.get("VLM_HOST",        "10.79.85.35")
DEFAULT_USER        = os.environ.get("VLM_USER",        "montjac")
DEFAULT_REMOTE_ROOT = os.environ.get("VLM_REMOTE_ROOT", "~/aBotTesty_vlm_jobs")
DEFAULT_MODEL_3090  = "Qwen/Qwen3-VL-8B-Instruct"
DEFAULT_MODEL_3080  = "Qwen/Qwen2.5-VL-7B-Instruct"
LOG_FMT = "%(asctime)s [vlm_auto_train] %(levelname)s %(message)s"


def _setup_logging(log_file: Optional[str] = None) -> logging.Logger:
    log = logging.getLogger("vlm_auto_train")
    log.setLevel(logging.DEBUG)
    if not log.handlers:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(logging.Formatter(LOG_FMT))
        log.addHandler(sh)
        if log_file:
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setFormatter(logging.Formatter(LOG_FMT))
            log.addHandler(fh)
    return log


def _resolve_root(root: Optional[str] = None) -> Path:
    if root:
        return Path(root).resolve()
    # Walk up from this file's location to find the project root.
    here = Path(__file__).resolve().parent
    for candidate in (here, here.parent):
        if (candidate / "vlm_remote_trainer.py").is_file():
            return candidate
    return here


def _import_project_modules(root: Path):
    """Import vlm_remote_trainer and learning_dataset_writer from root."""
    import importlib.util
    mods = {}
    for name, fname in (
        ("vlm_remote_trainer", "vlm_remote_trainer.py"),
        ("learning_dataset_writer", "learning_dataset_writer.py"),
        ("vlm_training_monitor", "vlm_training_monitor.py"),
    ):
        spec = importlib.util.spec_from_file_location(name, str(root / fname))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        mods[name] = mod
    return mods


# ---------------------------------------------------------------------------
# Step 1 — Export the latest dataset
# ---------------------------------------------------------------------------

def export_latest_dataset(
    root: Path,
    mods: Dict[str, Any],
    run_id: Optional[str] = None,
    dry_run: bool = False,
    log: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """Call LearningDatasetWriter.export() and return the result dict."""
    log = log or logging.getLogger("vlm_auto_train")
    LDW = mods["learning_dataset_writer"].LearningDatasetWriter
    writer = LDW(
        root_dir=root,
        out_dir=root / "learning_datasets",
    )
    if dry_run:
        log.info("[DRY-RUN] would call writer.export(run_id=%s)", run_id)
        # Return a plausible stub so downstream checks can still run.
        latest = root / "learning_datasets" / "latest"
        return {
            "ok": True,
            "dry_run": True,
            "dataset_dir": str(latest),
            "run_id": run_id,
        }
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    effective_run_id = run_id or f"auto_friday_{ts}"
    log.info("Exporting dataset run_id=%s …", effective_run_id)
    result = writer.export(run_id=effective_run_id)
    log.info("Export result: ok=%s dataset_dir=%s", result.get("ok"), result.get("dataset_dir"))
    return result


# ---------------------------------------------------------------------------
# Step 2 — Evaluate dataset readiness
# ---------------------------------------------------------------------------

def check_readiness(
    dataset_dir: Path,
    mods: Dict[str, Any],
    min_screen: int = DEFAULT_MIN_SCREEN,
    min_policy: int = DEFAULT_MIN_POLICY,
    min_verify: int = DEFAULT_MIN_VERIFY,
    min_images: int = DEFAULT_MIN_IMAGES,
    log: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """Return a dict with ok=True/False plus detailed counts."""
    log = log or logging.getLogger("vlm_auto_train")
    mon = mods["vlm_training_monitor"]
    summary = mon.dataset_summary(dataset_dir)

    sft   = summary.get("sft_counts", {})
    screen  = sft.get("screen_perception", 0)
    policy  = sft.get("action_policy", 0)
    verify  = sft.get("outcome_verifier", 0)
    images  = summary.get("images_found", 0) or summary.get("image_count", 0)
    score   = summary.get("readiness_score", 0)
    flags   = summary.get("quality_flags", [])

    failures = []
    if screen  < min_screen:  failures.append(f"screen_perception {screen} < {min_screen}")
    if policy  < min_policy:  failures.append(f"action_policy {policy} < {min_policy}")
    if verify  < min_verify:  failures.append(f"outcome_verifier {verify} < {min_verify}")
    if images  < min_images:  failures.append(f"images {images} < {min_images}")

    ok = len(failures) == 0
    result = {
        "ok": ok,
        "dataset_dir": str(dataset_dir),
        "screen_perception": screen,
        "action_policy": policy,
        "outcome_verifier": verify,
        "images": images,
        "readiness_score": score,
        "quality_flags": flags,
        "failures": failures,
        "thresholds": {
            "min_screen": min_screen,
            "min_policy": min_policy,
            "min_verify": min_verify,
            "min_images": min_images,
        },
    }
    if ok:
        log.info("Dataset ready  score=%s  screen=%s policy=%s verify=%s images=%s",
                 score, screen, policy, verify, images)
    else:
        log.warning("Dataset NOT ready: %s", "; ".join(failures))
    return result


# ---------------------------------------------------------------------------
# Step 3 — Prepare & submit async training job
# ---------------------------------------------------------------------------

def submit_training_async(
    root: Path,
    dataset_dir: Path,
    mods: Dict[str, Any],
    hardware: str = DEFAULT_HARDWARE,
    host: str = DEFAULT_HOST,
    user: str = DEFAULT_USER,
    remote_root: str = DEFAULT_REMOTE_ROOT,
    execute: bool = False,
    log: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """Prepare job files and launch async SSH training. Returns result dict."""
    log = log or logging.getLogger("vlm_auto_train")
    vrt = mods["vlm_remote_trainer"]

    model = DEFAULT_MODEL_3090 if "3090" in hardware else DEFAULT_MODEL_3080
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_name = f"abot_vlm_friday_{ts}"

    job = vrt.VLMRemoteJob(
        dataset_dir=str(dataset_dir),
        host=host,
        user=user,
        remote_root=remote_root,
        model_name=model,
        run_name=run_name,
        dry_run=not execute,
    )

    out_dir = root / "vlm_jobs" / run_name
    log.info("Preparing job files in %s (dry_run=%s) …", out_dir, job.dry_run)
    plan = vrt.prepare_job_files(job, out_dir=out_dir, hardware=hardware)
    log.info("Job files prepared. Submitting …")

    result = vrt.submit_job(job, prepared_dir=out_dir)
    result["run_name"] = run_name
    result["plan"] = plan
    result["hardware"] = hardware

    if result.get("ok"):
        log.info("Training job submitted OK  run_name=%s  remote_dir=%s",
                 run_name, result.get("remote_dir"))
        log.info("Tail logs with: %s", result.get("tail_logs", ""))
    else:
        log.error("Training job submission FAILED: %s", json.dumps(result, indent=2, default=str))

    return result


# ---------------------------------------------------------------------------
# Step 4 — Persist a run record to disk for dashboard visibility
# ---------------------------------------------------------------------------

def _persist_run_record(root: Path, record: Dict[str, Any]) -> None:
    record_dir = root / "vlm_auto_train_history"
    record_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = record_dir / f"run_{ts}.json"
    path.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
    # Keep a rolling "latest" pointer
    latest = record_dir / "latest.json"
    try:
        if latest.exists() or latest.is_symlink():
            latest.unlink()
        latest.symlink_to(path.name)
    except Exception:
        latest.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")


# ---------------------------------------------------------------------------
# Top-level pipeline — importable by merged_app.py
# ---------------------------------------------------------------------------

def auto_train_pipeline(
    root: Optional[str] = None,
    execute: bool = False,
    dry_run_export: bool = False,
    min_screen: int = DEFAULT_MIN_SCREEN,
    min_policy: int = DEFAULT_MIN_POLICY,
    min_verify: int = DEFAULT_MIN_VERIFY,
    min_images: int = DEFAULT_MIN_IMAGES,
    hardware: str = DEFAULT_HARDWARE,
    host: str = DEFAULT_HOST,
    user: str = DEFAULT_USER,
    remote_root: str = DEFAULT_REMOTE_ROOT,
    log_file: Optional[str] = None,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Full pipeline: export → readiness check → async training submit.

    Returns a dict with keys: ok, skipped, stage, readiness, submit_result.
    """
    project_root = _resolve_root(root)
    log = _setup_logging(log_file)
    log.info("=== VLM Auto-Train Pipeline start  root=%s  execute=%s ===", project_root, execute)
    t0 = time.time()

    record: Dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "root": str(project_root),
        "execute": execute,
        "hardware": hardware,
    }

    # ── Step 1: Import project modules ──────────────────────────────────────
    try:
        mods = _import_project_modules(project_root)
    except Exception as exc:
        log.error("Failed to import project modules: %s", exc)
        record.update({"ok": False, "stage": "import", "error": str(exc)})
        _persist_run_record(project_root, record)
        return record

    # ── Step 2: Export latest dataset ───────────────────────────────────────
    try:
        export_result = export_latest_dataset(
            project_root, mods,
            run_id=run_id,
            dry_run=dry_run_export,
            log=log,
        )
        record["export"] = export_result
        if not export_result.get("ok"):
            log.error("Export failed: %s", export_result)
            record.update({"ok": False, "stage": "export"})
            _persist_run_record(project_root, record)
            return record
    except Exception as exc:
        log.error("Export raised exception: %s", exc)
        record.update({"ok": False, "stage": "export", "error": str(exc)})
        _persist_run_record(project_root, record)
        return record

    # ── Step 3: Resolve the exported dataset directory ──────────────────────
    dataset_dir_str = export_result.get("dataset_dir") or ""
    if not dataset_dir_str:
        # Fall back to learning_datasets/latest symlink
        dataset_dir_str = str(project_root / "learning_datasets" / "latest")
    dataset_dir = Path(dataset_dir_str)
    if dataset_dir.is_symlink():
        dataset_dir = dataset_dir.resolve()
    log.info("Dataset dir resolved: %s", dataset_dir)

    # ── Step 4: Readiness check ──────────────────────────────────────────────
    try:
        readiness = check_readiness(
            dataset_dir, mods,
            min_screen=min_screen, min_policy=min_policy,
            min_verify=min_verify,  min_images=min_images,
            log=log,
        )
        record["readiness"] = readiness
        if not readiness["ok"]:
            log.warning("Skipping training — dataset below threshold.")
            record.update({"ok": True, "skipped": True, "stage": "readiness_check",
                           "skip_reason": readiness["failures"]})
            _persist_run_record(project_root, record)
            return record
    except Exception as exc:
        log.error("Readiness check raised exception: %s", exc)
        record.update({"ok": False, "stage": "readiness_check", "error": str(exc)})
        _persist_run_record(project_root, record)
        return record

    # ── Step 5: Submit async training job ───────────────────────────────────
    try:
        submit_result = submit_training_async(
            project_root, dataset_dir, mods,
            hardware=hardware, host=host, user=user, remote_root=remote_root,
            execute=execute,
            log=log,
        )
        record["submit_result"] = submit_result
        record["ok"] = submit_result.get("ok", False)
        record["skipped"] = False
        record["stage"] = "submitted"
    except Exception as exc:
        log.error("Submit raised exception: %s", exc)
        record.update({"ok": False, "stage": "submit", "error": str(exc)})

    elapsed = round(time.time() - t0, 2)
    record["elapsed_s"] = elapsed
    record["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    log.info("=== Pipeline complete  ok=%s  skipped=%s  elapsed=%.1fs ===",
             record.get("ok"), record.get("skipped"), elapsed)
    _persist_run_record(project_root, record)
    return record


# ---------------------------------------------------------------------------
# Latest auto-train run summary (for dashboard API)
# ---------------------------------------------------------------------------

def latest_auto_train_record(root: Optional[str] = None) -> Dict[str, Any]:
    """Return the most recent auto-train run record, or an empty dict."""
    project_root = _resolve_root(root)
    latest = project_root / "vlm_auto_train_history" / "latest.json"
    try:
        if latest.exists() or latest.is_symlink():
            target = latest.resolve() if latest.is_symlink() else latest
            return json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Automated VLM export + async training — Friday cron orchestrator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--root",       default="",   help="Project root (auto-detected if omitted)")
    p.add_argument("--execute",    action="store_true",
                   help="Actually run SSH/rsync/training. Default is dry-run.")
    p.add_argument("--dry-run-export", action="store_true",
                   help="Skip the real export step (use existing latest dataset).")
    p.add_argument("--min-screen", type=int, default=DEFAULT_MIN_SCREEN,
                   help="Minimum screen_perception rows required")
    p.add_argument("--min-policy", type=int, default=DEFAULT_MIN_POLICY,
                   help="Minimum action_policy rows required")
    p.add_argument("--min-verify", type=int, default=DEFAULT_MIN_VERIFY,
                   help="Minimum outcome_verifier rows required")
    p.add_argument("--min-images", type=int, default=DEFAULT_MIN_IMAGES,
                   help="Minimum image count required")
    p.add_argument("--hardware",   default=DEFAULT_HARDWARE,
                   choices=["2x3090", "2x3080"],
                   help="Remote GPU hardware spec")
    p.add_argument("--host",       default=DEFAULT_HOST,
                   help="Remote training host")
    p.add_argument("--user",       default=DEFAULT_USER,
                   help="SSH user on remote host")
    p.add_argument("--remote-root", default=DEFAULT_REMOTE_ROOT,
                   help="Remote VLM jobs root directory")
    p.add_argument("--log-file",   default="",
                   help="Optional log file path (appended)")
    p.add_argument("--run-id",     default="",
                   help="Optional dataset run_id override")
    p.add_argument("--show-latest", action="store_true",
                   help="Print the latest auto-train run record and exit.")
    return p


def main(argv=None) -> int:
    p = _build_parser()
    args = p.parse_args(argv)

    if args.show_latest:
        record = latest_auto_train_record(args.root or None)
        print(json.dumps(record, indent=2, default=str))
        return 0

    result = auto_train_pipeline(
        root=args.root or None,
        execute=args.execute,
        dry_run_export=args.dry_run_export,
        min_screen=args.min_screen,
        min_policy=args.min_policy,
        min_verify=args.min_verify,
        min_images=args.min_images,
        hardware=args.hardware,
        host=args.host,
        user=args.user,
        remote_root=args.remote_root,
        log_file=args.log_file or None,
        run_id=args.run_id or None,
    )
    print(json.dumps(result, indent=2, default=str))

    if result.get("skipped"):
        # Exit 1 = dataset not ready; cron treats this as a quiet skip, not a failure
        return 1
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
