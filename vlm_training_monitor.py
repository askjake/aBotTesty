#!/usr/bin/env python3
"""VLM learning/training telemetry for aBotTesty.

Reads local exported datasets, local prepared VLM job plans, and remote
LLaMA-Factory job directories. Produces dashboard-friendly JSON without
requiring external packages.
"""
from __future__ import annotations

import json
import math
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SFT_FILES = {
    "screen_perception": "sft/screen_perception.jsonl",
    "action_policy": "sft/action_policy.jsonl",
    "outcome_verifier": "sft/outcome_verifier.jsonl",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path, default: Any) -> Any:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        pass
    return default


def count_lines(path: Path) -> int:
    try:
        if path.is_file():
            with path.open("r", encoding="utf-8", errors="ignore") as f:
                return sum(1 for line in f if line.strip())
    except Exception:
        return 0
    return 0


def count_images(path: Path) -> int:
    if not path.exists():
        return 0
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    try:
        return sum(1 for p in path.rglob("*") if p.is_file() and p.suffix.lower() in exts)
    except Exception:
        return 0


def dir_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    try:
        for p in path.rglob("*"):
            if p.is_file():
                total += p.stat().st_size
    except Exception:
        return total
    return total


def human_bytes(n: int) -> str:
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024.0
    return f"{n:.1f} TB"


def parse_ts(value: Any) -> float:
    s = str(value or "").strip()
    if not s:
        return 0.0
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        pass
    m = re.search(r"(20\d{6})[_-](\d{6})", s)
    if m:
        try:
            return datetime.strptime("".join(m.groups()), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).timestamp()
        except Exception:
            return 0.0
    return 0.0


def dataset_summary(dataset_dir: Path) -> Dict[str, Any]:
    dataset_dir = Path(dataset_dir)
    manifest = read_json(dataset_dir / "manifest.json", {})
    sft_counts = {
        name: count_lines(dataset_dir / rel)
        for name, rel in SFT_FILES.items()
    }
    images = count_images(dataset_dir / "images")
    episodes = count_lines(dataset_dir / "episodes.jsonl")
    size_b = dir_size_bytes(dataset_dir)
    total_sft = sum(sft_counts.values())
    task_mix = [
        {
            "task": k,
            "count": v,
            "pct": round(v / max(1, total_sft) * 100.0, 2),
        }
        for k, v in sft_counts.items()
    ]

    created_at = manifest.get("created_at", "")
    if not created_at:
        try:
            created_at = datetime.fromtimestamp(dataset_dir.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds")
        except Exception:
            created_at = ""

    train_ready_smoke = total_sft >= 50 and images >= 25
    train_ready_useful = (
        sft_counts.get("screen_perception", 0) >= 250
        and sft_counts.get("action_policy", 0) >= 250
        and sft_counts.get("outcome_verifier", 0) >= 250
        and images >= 100
    )

    weak = []
    if images == 0:
        weak.append("no_images")
    if sft_counts.get("action_policy", 0) == 0:
        weak.append("no_policy_rows")
    if sft_counts.get("outcome_verifier", 0) == 0:
        weak.append("no_verifier_rows")
    if images and total_sft / max(1, images) > 8:
        weak.append("many_rows_per_image_possible_duplicate_pressure")
    if sft_counts.get("screen_perception", 0) > max(1, sft_counts.get("action_policy", 0)) * 5:
        weak.append("perception_heavy_dataset")

    score = 0
    score += min(35, int(images / 100 * 35))
    score += min(25, int(sft_counts.get("screen_perception", 0) / 500 * 25))
    score += min(20, int(sft_counts.get("action_policy", 0) / 500 * 20))
    score += min(20, int(sft_counts.get("outcome_verifier", 0) / 500 * 20))
    score = max(0, min(100, score))

    return {
        "name": dataset_dir.name,
        "path": str(dataset_dir),
        "exists": dataset_dir.is_dir(),
        "created_at": created_at,
        "created_ts": parse_ts(created_at) or (dataset_dir.stat().st_mtime if dataset_dir.exists() else 0),
        "schema": manifest.get("schema", ""),
        "episode_count": int(manifest.get("episode_count") or episodes),
        "image_count": int(manifest.get("image_count") or images),
        "images_found": images,
        "sft_counts": {**sft_counts},
        "total_sft_rows": total_sft,
        "task_mix": task_mix,
        "size_bytes": size_b,
        "size_human": human_bytes(size_b),
        "rows_per_image": round(total_sft / max(1, images), 3),
        "readiness_score": score,
        "train_ready_smoke": train_ready_smoke,
        "train_ready_useful": train_ready_useful,
        "quality_flags": weak,
    }


def local_dataset_timeline(root_dir: Path, limit: int = 24) -> List[Dict[str, Any]]:
    ds_root = Path(root_dir) / "learning_datasets"
    if not ds_root.exists():
        return []
    rows = []
    for d in ds_root.iterdir():
        if not d.is_dir() and not d.is_symlink():
            continue
        if d.name == "latest":
            continue
        if not (d / "manifest.json").exists() and not (d / "sft").exists():
            continue
        rows.append(dataset_summary(d.resolve()))
    rows.sort(key=lambda r: r.get("created_ts", 0), reverse=True)
    return rows[:limit]


def latest_dataset(root_dir: Path) -> Dict[str, Any]:
    """Return the newest usable exported dataset.

    Prefer learning_datasets/latest only when it actually contains rows/images.
    If latest is empty, stale, or broken, fall back to the newest non-empty
    dataset export. This prevents the dashboard top panel from showing 0 while
    the training table correctly sees older real datasets.
    """
    latest = Path(root_dir) / "learning_datasets" / "latest"
    if latest.exists():
        target = latest.resolve() if latest.is_symlink() else latest
        summary = dataset_summary(target)
        if summary.get("total_sft_rows", 0) > 0 or summary.get("image_count", 0) > 0 or summary.get("images_found", 0) > 0:
            summary["selection_source"] = "learning_datasets/latest"
            return summary
        summary["selection_warning"] = "learning_datasets/latest was empty; falling back to newest non-empty dataset"

    rows = local_dataset_timeline(root_dir, limit=50)
    for row in rows:
        if row.get("total_sft_rows", 0) > 0 or row.get("image_count", 0) > 0 or row.get("images_found", 0) > 0:
            row["selection_source"] = "newest_non_empty_dataset"
            return row

    return dataset_summary(latest)




def parse_loss_history_from_text(text: str) -> List[Dict[str, Any]]:
    """Extract LLaMA-Factory/HF Trainer loss records from log text."""
    out: List[Dict[str, Any]] = []
    for line in (text or "").splitlines():
        loss = None
        step = None
        epoch = None

        # JSON-ish HF logs, e.g. {'loss': 1.23, 'learning_rate': ..., 'epoch': 0.5}
        m = re.search(r"['\"]loss['\"]\s*:\s*([0-9.]+)", line)
        if m:
            try:
                loss = float(m.group(1))
            except Exception:
                loss = None
        m = re.search(r"['\"]epoch['\"]\s*:\s*([0-9.]+)", line)
        if m:
            try:
                epoch = float(m.group(1))
            except Exception:
                epoch = None
        m = re.search(r"step[=/ ]+(\d+)", line, re.I)
        if m:
            try:
                step = int(m.group(1))
            except Exception:
                step = None

        # tqdm line fallback: " 42%|...| 50/120 ... loss=1.23"
        if loss is None:
            m = re.search(r"\bloss[=:]\s*([0-9.]+)", line, re.I)
            if m:
                try:
                    loss = float(m.group(1))
                except Exception:
                    loss = None
        if step is None:
            m = re.search(r"\|\s*(\d+)/(\d+)\s*\[", line)
            if m:
                try:
                    step = int(m.group(1))
                except Exception:
                    step = None

        if loss is not None:
            out.append({
                "step": step if step is not None else len(out) + 1,
                "epoch": epoch,
                "loss": round(float(loss), 6),
                "raw": line[-240:],
            })
    return out[-400:]


def parse_train_log_metrics(text: str) -> Dict[str, Any]:
    text = text or ""
    losses = parse_loss_history_from_text(text)

    def find_float(pattern: str) -> Optional[float]:
        m = re.search(pattern, text, re.I)
        if not m:
            return None
        try:
            return float(m.group(1))
        except Exception:
            return None

    def find_int(pattern: str) -> Optional[int]:
        m = re.search(pattern, text, re.I)
        if not m:
            return None
        try:
            return int(float(m.group(1)))
        except Exception:
            return None

    train_loss = find_float(r"train_loss['\"]?\s*[:=]\s*([0-9.]+)")
    runtime = find_float(r"train_runtime['\"]?\s*[:=]\s*([0-9.]+)")
    samples_per_s = find_float(r"train_samples_per_second['\"]?\s*[:=]\s*([0-9.]+)")
    steps_per_s = find_float(r"train_steps_per_second['\"]?\s*[:=]\s*([0-9.]+)")
    examples = find_int(r"Num examples\s*=\s*([0-9]+)")
    total_steps = find_int(r"Total optimization steps\s*=\s*([0-9]+)")

    status = "unknown"
    if re.search(r"training finished|Training completed|train_loss", text, re.I):
        status = "completed"
    if re.search(r"Traceback|CalledProcessError|CUDA out of memory|ModuleNotFoundError|ValueError|FileNotFoundError", text, re.I):
        status = "failed"
    if re.search(r"Running training|starting llamafactory-cli train", text, re.I) and status == "unknown":
        status = "running_or_started"

    first_loss = losses[0]["loss"] if losses else None
    last_loss = losses[-1]["loss"] if losses else train_loss
    best_loss = min([x["loss"] for x in losses], default=train_loss)
    improvement_pct = None
    if first_loss and last_loss is not None and first_loss > 0:
        improvement_pct = round((first_loss - last_loss) / first_loss * 100.0, 2)

    progress_pct = 0.0
    if losses and total_steps:
        progress_pct = round(min(100.0, losses[-1].get("step", 0) / max(1, total_steps) * 100.0), 2)
    elif status == "completed":
        progress_pct = 100.0

    return {
        "status": status,
        "num_examples": examples,
        "total_steps": total_steps,
        "progress_pct": progress_pct,
        "train_loss": train_loss,
        "first_loss": first_loss,
        "last_loss": last_loss,
        "best_loss": best_loss,
        "loss_improvement_pct": improvement_pct,
        "train_runtime_s": runtime,
        "train_samples_per_second": samples_per_s,
        "train_steps_per_second": steps_per_s,
        "loss_history": losses,
        "log_lines": len(text.splitlines()),
    }


def run_local_cmd(cmd: List[str], timeout_s: float = 20.0) -> Dict[str, Any]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "cmd": " ".join(shlex.quote(x) for x in cmd),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "cmd": " ".join(shlex.quote(x) for x in cmd)}


def remote_python_summary_script(remote_root: str, limit: int) -> str:
    # Embedded script intentionally duplicates small helpers to keep SSH side independent.
    return f'''
import json, re, os, subprocess
from pathlib import Path

root = Path({remote_root!r}).expanduser()
limit = int({limit})
out = {{"root": str(root), "exists": root.exists(), "jobs": []}}

def read(p, n=300000):
    try:
        if p.is_file():
            txt = p.read_text(encoding="utf-8", errors="ignore")
            return txt[-n:]
    except Exception:
        return ""
    return ""

def count_lines(p):
    try:
        if p.is_file():
            return sum(1 for line in p.open("r", encoding="utf-8", errors="ignore") if line.strip())
    except Exception:
        pass
    return 0

def count_images(p):
    exts={{".jpg",".jpeg",".png",".webp"}}
    try:
        return sum(1 for x in p.rglob("*") if x.is_file() and x.suffix.lower() in exts)
    except Exception:
        return 0

def jread(p):
    try:
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        pass
    return {{}}

def parse_losses(txt):
    rows=[]
    for line in txt.splitlines():
        loss=None; step=None
        m=re.search(r"['\\"]loss['\\"]\\s*:\\s*([0-9.]+)", line)
        if m:
            try: loss=float(m.group(1))
            except Exception: loss=None
        if loss is None:
            m=re.search(r"\\bloss[=:]\\s*([0-9.]+)", line, re.I)
            if m:
                try: loss=float(m.group(1))
                except Exception: loss=None
        m=re.search(r"\\|\\s*(\\d+)/(\\d+)\\s*\\[", line)
        if m:
            try: step=int(m.group(1))
            except Exception: step=None
        if loss is not None:
            rows.append({{"step": step or len(rows)+1, "loss": round(loss,6), "raw": line[-240:]}})
    return rows[-400:]

def parse_metrics(txt):
    losses=parse_losses(txt)
    def fint(rx):
        m=re.search(rx, txt, re.I)
        if not m: return None
        try: return int(float(m.group(1)))
        except Exception: return None
    def ffloat(rx):
        m=re.search(rx, txt, re.I)
        if not m: return None
        try: return float(m.group(1))
        except Exception: return None
    status="unknown"
    if re.search(r"training finished|Training completed|train_loss", txt, re.I): status="completed"
    if re.search(r"Traceback|CalledProcessError|CUDA out of memory|ModuleNotFoundError|ValueError|FileNotFoundError", txt, re.I): status="failed"
    if re.search(r"Running training|starting llamafactory-cli train", txt, re.I) and status=="unknown": status="running_or_started"
    first=losses[0]["loss"] if losses else None
    last=losses[-1]["loss"] if losses else ffloat(r"train_loss['\\"]?\\s*[:=]\\s*([0-9.]+)")
    best=min([x["loss"] for x in losses], default=last)
    steps=fint(r"Total optimization steps\\s*=\\s*([0-9]+)")
    progress=100.0 if status=="completed" else 0.0
    if losses and steps:
        progress=round(min(100.0, losses[-1].get("step",0)/max(1,steps)*100.0),2)
    return {{
      "status": status,
      "num_examples": fint(r"Num examples\\s*=\\s*([0-9]+)"),
      "total_steps": steps,
      "progress_pct": progress,
      "train_loss": ffloat(r"train_loss['\\"]?\\s*[:=]\\s*([0-9.]+)"),
      "first_loss": first,
      "last_loss": last,
      "best_loss": best,
      "train_runtime_s": ffloat(r"train_runtime['\\"]?\\s*[:=]\\s*([0-9.]+)"),
      "train_samples_per_second": ffloat(r"train_samples_per_second['\\"]?\\s*[:=]\\s*([0-9.]+)"),
      "train_steps_per_second": ffloat(r"train_steps_per_second['\\"]?\\s*[:=]\\s*([0-9.]+)"),
      "loss_history": losses,
    }}

if root.exists():
    dirs=[p for p in root.glob("abot_vlm_*") if p.is_dir()]
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for d in dirs[:limit]:
        txt=read(d/"train.log")
        metrics=parse_metrics(txt)
        outs=list((d/"outputs").glob("*")) if (d/"outputs").exists() else []
        output=outs[0] if outs else None
        train_results=jread(output/"train_results.json") if output else {{}}
        all_results=jread(output/"all_results.json") if output else {{}}
        sft=d/"dataset"/"sft"
        dataset_counts={{
          "screen_perception": count_lines(sft/"screen_perception.jsonl"),
          "action_policy": count_lines(sft/"action_policy.jsonl"),
          "outcome_verifier": count_lines(sft/"outcome_verifier.jsonl"),
          "images": count_images(d/"dataset"/"images"),
        }}
        if train_results:
            metrics.update({{k:v for k,v in train_results.items() if k.startswith("train_")}})
        if all_results:
            metrics.update({{k:v for k,v in all_results.items() if k.startswith("train_")}})
        out["jobs"].append({{
          "run_name": d.name,
          "remote_dir": str(d),
          "mtime": d.stat().st_mtime,
          "dataset_counts": dataset_counts,
          "metrics": metrics,
          "tail": txt.splitlines()[-80:],
          "has_output": bool(output),
          "output_dir": str(output) if output else "",
        }})
try:
    p=subprocess.run(["pgrep","-af","torchrun|llamafactory|vlm_remote"], capture_output=True, text=True, timeout=3)
    out["processes"]=p.stdout.strip().splitlines()
except Exception as e:
    out["processes_error"]=str(e)
print(json.dumps(out))
'''


def remote_training_summary(cfg: Dict[str, Any], limit: int = 10, timeout_s: float = 25.0) -> Dict[str, Any]:
    host = str(cfg.get("vlm_remote_host", "10.79.85.35"))
    user = str(cfg.get("vlm_remote_user", "montjac"))
    port = str(cfg.get("vlm_remote_ssh_port", 22))
    root = str(cfg.get("vlm_remote_root", "~/aBotTesty_vlm_jobs"))
    if root.startswith("~/"):
        root = f"/home/{user}/{root[2:]}"
    elif root == "~":
        root = f"/home/{user}"

    script = remote_python_summary_script(root, limit)
    cmd = ["ssh", "-p", port, f"{user}@{host}", "python3 - <<'PY'\n" + script + "\nPY"]
    res = run_local_cmd(cmd, timeout_s=timeout_s)
    if not res.get("ok"):
        return {"ok": False, "error": res.get("stderr") or res.get("error") or res.get("stdout"), "cmd": res.get("cmd")}
    try:
        data = json.loads(res.get("stdout") or "{}")
        data["ok"] = True
        data["host"] = host
        data["user"] = user
        return data
    except Exception as exc:
        return {"ok": False, "error": f"remote JSON parse failed: {exc}", "stdout": res.get("stdout", "")[-2000:]}


def tail_remote_train_log(remote_dir: str, cfg: Dict[str, Any], lines: int = 160, timeout_s: float = 15.0) -> Dict[str, Any]:
    host = str(cfg.get("vlm_remote_host", "10.79.85.35"))
    user = str(cfg.get("vlm_remote_user", "montjac"))
    port = str(cfg.get("vlm_remote_ssh_port", 22))
    remote_dir = str(remote_dir or "").strip()
    if not remote_dir:
        return {"ok": False, "error": "remote_dir required"}
    cmd = [
        "ssh", "-p", port, f"{user}@{host}",
        f"cd {shlex.quote(remote_dir)} && tail -n {int(lines)} train.log 2>/dev/null || true"
    ]
    res = run_local_cmd(cmd, timeout_s=timeout_s)
    return {
        "ok": bool(res.get("ok")),
        "remote_dir": remote_dir,
        "text": res.get("stdout", ""),
        "error": res.get("stderr") or res.get("error", ""),
        "cmd": res.get("cmd"),
    }


def local_prepared_jobs(root_dir: Path, limit: int = 20) -> List[Dict[str, Any]]:
    jobs_root = Path(root_dir) / "vlm_jobs"
    if not jobs_root.exists():
        return []
    rows = []
    for d in jobs_root.glob("abot_vlm_*"):
        if not d.is_dir():
            continue
        plan = read_json(d / "remote_plan.json", {})
        cfg = plan.get("job") or {}
        rows.append({
            "run_name": d.name,
            "local_dir": str(d),
            "mtime": d.stat().st_mtime,
            "dataset_dir": cfg.get("dataset_dir", ""),
            "remote_dir": (plan.get("commands") or {}).get("remote_dir", ""),
            "model_name": cfg.get("model_name", ""),
            "dry_run": cfg.get("dry_run", ""),
        })
    rows.sort(key=lambda r: r.get("mtime", 0), reverse=True)
    return rows[:limit]



def _metric_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    # remove thousands commas: 3,808 -> 3808
    text2 = text.replace(",", "")
    m = re.search(r"[-+]?\d+(?:\.\d+)?", text2)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def _metric_int(value: Any) -> Optional[int]:
    f = _metric_float(value)
    return int(f) if f is not None else None


def _duration_seconds(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None

    # Handles "0:34:19.13", "34:19.13", or plain seconds.
    if ":" in text:
        parts = text.split(":")
        try:
            nums = [float(x) for x in parts]
            if len(nums) == 3:
                return nums[0] * 3600 + nums[1] * 60 + nums[2]
            if len(nums) == 2:
                return nums[0] * 60 + nums[1]
        except Exception:
            pass

    return _metric_float(text)


def normalize_remote_job_metrics(job: Dict[str, Any]) -> Dict[str, Any]:
    """Repair dashboard metrics from mixed HF/LLaMA-Factory log/json formats.

    Fixes:
    - Num examples with thousands commas, e.g. "3,808" -> 3808.
    - Runtime strings like 0:34:19.13.
    - Bad runtime fallback when samples/sec and dataset counts are available.
    """
    metrics = job.get("metrics") or {}
    counts = job.get("dataset_counts") or {}

    dataset_total = 0
    for key in ("screen_perception", "action_policy", "outcome_verifier"):
        try:
            dataset_total += int(counts.get(key) or 0)
        except Exception:
            pass

    current_examples = _metric_int(metrics.get("num_examples"))
    if dataset_total and (current_examples is None or current_examples < max(100, dataset_total // 2)):
        metrics["num_examples"] = dataset_total
    elif current_examples is not None:
        metrics["num_examples"] = current_examples

    # Normalize common scalar fields.
    for key in ("train_loss", "first_loss", "last_loss", "best_loss", "train_samples_per_second", "train_steps_per_second"):
        val = _metric_float(metrics.get(key))
        if val is not None:
            metrics[key] = val

    steps = _metric_int(metrics.get("total_steps"))
    if steps is not None:
        metrics["total_steps"] = steps

    runtime_candidates = [
        _duration_seconds(metrics.get("train_runtime_s")),
        _duration_seconds(metrics.get("train_runtime")),
    ]
    runtime_candidates = [x for x in runtime_candidates if x is not None and x > 0]
    runtime_s = max(runtime_candidates) if runtime_candidates else None

    sps = _metric_float(metrics.get("train_samples_per_second"))
    examples = _metric_int(metrics.get("num_examples"))
    if (runtime_s is None or runtime_s < 10) and sps and examples:
        runtime_s = examples / sps

    if runtime_s is not None:
        metrics["train_runtime_s"] = round(runtime_s, 2)

    # Mark old broken jobs more honestly.
    if metrics.get("status") == "unknown" and not job.get("has_output"):
        tail_text = "\n".join(job.get("tail") or [])
        if "dataset counts complete" in tail_text or "dataset counts" in tail_text:
            metrics["status"] = "incomplete"
        elif "Traceback" in tail_text or "ERROR line" in tail_text:
            metrics["status"] = "failed"

    job["metrics"] = metrics
    return job




def _json_len_guess(path: Path, *keys: str) -> int:
    data = read_json(path, None)
    if data is None:
        return 0
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in keys:
            val = data.get(key)
            if isinstance(val, list):
                return len(val)
            if isinstance(val, dict):
                return len(val)
        return len(data)
    return 0


def live_source_summary(root_dir: Path, crawler_dir: Path) -> Dict[str, Any]:
    """Summarize raw, still-growing crawler/teacher source data.

    This is intentionally separate from exported datasets. Exported datasets are
    immutable training snapshots; crawler_data is the live source that should
    grow while exploration runs.
    """
    root_dir = Path(root_dir)
    crawler_dir = Path(crawler_dir)

    state_dir = crawler_dir / "states"
    state_images = count_images(state_dir)

    newest_state_image = ""
    newest_state_image_ts = 0.0
    if state_dir.exists():
        try:
            imgs = [
                x for x in state_dir.rglob("*")
                if x.is_file() and x.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
            ]
            if imgs:
                newest = max(imgs, key=lambda x: x.stat().st_mtime)
                newest_state_image = str(newest)
                newest_state_image_ts = newest.stat().st_mtime
        except Exception:
            pass

    manual_dir = crawler_dir / "manual_sessions"
    teacher_files = sorted(manual_dir.glob("teach_*.json")) if manual_dir.exists() else []
    teacher_events = 0
    for fp in teacher_files:
        data = read_json(fp, {})
        ev = data.get("events") if isinstance(data, dict) else []
        if isinstance(ev, list):
            teacher_events += len(ev)

    nav_graph = crawler_dir / "nav_graph.json"
    nav = read_json(nav_graph, {})
    nodes = nav.get("nodes") if isinstance(nav, dict) else None
    edges = nav.get("edges") if isinstance(nav, dict) else None

    if isinstance(nodes, dict):
        node_count = len(nodes)
    elif isinstance(nodes, list):
        node_count = len(nodes)
    else:
        node_count = 0

    if isinstance(edges, dict):
        edge_count = sum(len(v) if isinstance(v, list) else 1 for v in edges.values())
    elif isinstance(edges, list):
        edge_count = len(edges)
    else:
        edge_count = 0

    channel_surf_count = max(
        _json_len_guess(crawler_dir / "channel_surf_log.json", "observations", "rows", "items"),
        _json_len_guess(root_dir / "channel_surf_log.json", "observations", "rows", "items"),
    )

    return {
        "crawler_dir": str(crawler_dir),
        "state_image_files": state_images,
        "newest_state_image": newest_state_image,
        "newest_state_image_ts": newest_state_image_ts,
        "teacher_files": len(teacher_files),
        "teacher_events": teacher_events,
        "nav_nodes": node_count,
        "nav_edges": edge_count,
        "channel_surf_observations": channel_surf_count,
        "note": "Live source counts grow during crawling; exported dataset counts grow only after Export dataset.",
    }



def build_training_dashboard_payload(
    root_dir: Path,
    crawler_dir: Path,
    cfg: Dict[str, Any],
    runtime_jobs: Optional[Dict[str, Any]] = None,
    include_remote: bool = True,
) -> Dict[str, Any]:
    latest = latest_dataset(root_dir)
    live_source = live_source_summary(root_dir, crawler_dir)
    timeline = local_dataset_timeline(root_dir, limit=30)
    local_jobs = local_prepared_jobs(root_dir, limit=30)

    remote = remote_training_summary(cfg, limit=10) if include_remote else {"ok": False, "skipped": True}
    remote_jobs = remote.get("jobs") if isinstance(remote, dict) else []
    remote_jobs = remote_jobs or []
    remote_jobs = [normalize_remote_job_metrics(j) for j in remote_jobs]

    completed = [j for j in remote_jobs if (j.get("metrics") or {}).get("status") == "completed"]
    failed = [j for j in remote_jobs if (j.get("metrics") or {}).get("status") == "failed"]
    running = [
        j for j in remote_jobs
        if (j.get("metrics") or {}).get("status") in {"running_or_started", "unknown"}
        and j.get("run_name") in "\n".join(remote.get("processes") or [])
    ]

    best = None
    if completed:
        best = sorted(completed, key=lambda j: ((j.get("metrics") or {}).get("train_loss") if (j.get("metrics") or {}).get("train_loss") is not None else 999999))[0]

    return {
        "ok": True,
        "generated_at": now_iso(),
        "latest_dataset": latest,
        "live_source": live_source,
        "dataset_timeline": timeline,
        "local_prepared_jobs": local_jobs,
        "runtime_jobs": list((runtime_jobs or {}).values()),
        "remote": remote,
        "remote_jobs": remote_jobs,
        "summary": {
            "datasets_seen": len(timeline),
            "remote_jobs_seen": len(remote_jobs),
            "completed_train_jobs": len(completed),
            "failed_train_jobs": len(failed),
            "running_train_jobs": len(running),
            "best_run_name": best.get("run_name") if best else "",
            "best_train_loss": (best.get("metrics") or {}).get("train_loss") if best else None,
            "latest_readiness_score": latest.get("readiness_score", 0),
            "latest_total_sft_rows": latest.get("total_sft_rows", 0),
            "latest_images": latest.get("image_count", 0),
        },
    }
