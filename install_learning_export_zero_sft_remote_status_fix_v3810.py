#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
import py_compile

PATCH_MARKER = "v38.10-learning-export-zero-sft-remote-status-20260602"

PATCH_BLOCK = r'''
# ---- aBotTesty learning export / zero-SFT / remote status repair (v38.10-learning-export-zero-sft-remote-status-20260602) ----

def _abot_v3810_count_jsonl(path):
    try:
        p = Path(path)
        if not p.is_file():
            return 0
        n = 0
        with p.open("r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if line.strip():
                    n += 1
        return n
    except Exception:
        return 0


def _abot_v3810_dataset_counts(export_dir):
    root = Path(export_dir)
    screen = _abot_v3810_count_jsonl(root / "sft" / "screen_perception.jsonl")
    policy = _abot_v3810_count_jsonl(root / "sft" / "action_policy.jsonl")
    verify = _abot_v3810_count_jsonl(root / "sft" / "outcome_verifier.jsonl")
    try:
        images = sum(1 for p in (root / "images").rglob("*") if p.is_file()) if (root / "images").is_dir() else 0
    except Exception:
        images = 0
    episodes = _abot_v3810_count_jsonl(root / "episodes.jsonl")
    return {
        "episodes": int(episodes),
        "screen_perception": int(screen),
        "action_policy": int(policy),
        "outcome_verifier": int(verify),
        "total_sft_rows": int(screen + policy + verify),
        "images": int(images),
        "trainable": bool((screen + policy + verify) > 0 and images > 0),
    }


def _abot_v3810_normalize_max_records(value):
    # HTML/JSON often sends 0 for "all". Treat None, blank, 0, and negative as unlimited.
    if value is None:
        return None
    if isinstance(value, str):
        if not value.strip():
            return None
        try:
            value = int(float(value.strip()))
        except Exception:
            return None
    try:
        value = int(value)
    except Exception:
        return None
    return value if value > 0 else None


def _abot_v3810_unique_run_id(run_id):
    requested = str(run_id or "latest").strip() or "latest"
    dataset_root = ROOT / str(CFG.get("learning_dataset_dir", "learning_datasets"))
    candidate = requested
    if not (dataset_root / candidate).exists():
        return requested, candidate, ""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = f"{requested}_{stamp}"
    idx = 2
    while (dataset_root / candidate).exists():
        candidate = f"{requested}_{stamp}_{idx}"
        idx += 1
    note = f"requested run_id '{requested}' already existed; exported as '{candidate}'"
    return requested, candidate, note


def _abot_safe_learning_export(run_id="latest", max_records=None, include_raw=True, overwrite=False):
    # Safe export override. max_records <= 0 means unlimited, not zero rows.
    import shutil

    requested = str(run_id or "latest").strip() or "latest"
    max_records_norm = _abot_v3810_normalize_max_records(max_records)
    dataset_root = ROOT / str(CFG.get("learning_dataset_dir", "learning_datasets"))
    target = dataset_root / requested

    effective = requested
    note = ""
    if target.exists():
        if overwrite:
            shutil.rmtree(target)
            note = f"overwrote existing dataset export '{requested}'"
        else:
            requested, effective, note = _abot_v3810_unique_run_id(requested)

    result = _learning_writer().export(
        run_id=effective,
        max_records=max_records_norm,
        include_raw=bool(include_raw),
    )
    if isinstance(result, dict):
        result["ok"] = bool(result.get("ok", True))
        result["safe_export"] = True
        result["requested_run_id"] = requested
        result["effective_run_id"] = effective
        result["max_records_requested"] = max_records
        result["max_records_effective"] = max_records_norm
        result["include_raw"] = bool(include_raw)
        if note:
            result["note"] = note
        try:
            counts = _abot_v3810_dataset_counts(result.get("dataset_dir") or (dataset_root / effective))
            result["trainability"] = counts
            if not counts.get("trainable"):
                result["warning"] = (
                    "Export is not trainable for VLM yet: requires images plus nonzero SFT rows. "
                    "If you sent max_records=0 before v38.10, re-export with max_records omitted or null."
                )
        except Exception as exc:
            result["trainability_error"] = str(exc)
    return result


def _abot_find_latest_dataset_export(dataset_root):
    # Prefer the newest trainable dataset over newer zero-SFT/zero-image scratch exports.
    root = Path(dataset_root)
    if not root.exists():
        return None
    candidates = []
    try:
        roots = [root] + [x for x in root.iterdir() if x.is_dir()]
    except Exception:
        roots = [root]
    for p in roots:
        has_data = (p / "episodes.jsonl").is_file() or (p / "manifest.json").is_file() or (p / "sft").is_dir()
        if not has_data:
            continue
        try:
            files = [x for x in p.rglob("*") if x.is_file()]
            mt = max([x.stat().st_mtime for x in files] or [p.stat().st_mtime])
        except Exception:
            try:
                mt = p.stat().st_mtime
            except Exception:
                mt = 0.0
        counts = _abot_v3810_dataset_counts(p)
        score = (1 if counts.get("trainable") else 0, float(mt))
        candidates.append((score, p))
    if not candidates:
        return None
    return sorted(candidates, key=lambda x: x[0], reverse=True)[0][1]


@app.route("/api/learning/remote/diagnose", methods=["GET", "POST"])
def api_learning_remote_diagnose():
    # Truthful remote training status based on processes, artifacts, and logs.
    import subprocess
    data = request.get_json(silent=True) or {}
    host = str(data.get("host") or CFG.get("vlm_remote_host", "10.79.85.35"))
    user = str(data.get("user") or CFG.get("vlm_remote_user", "montjac"))
    port = int(data.get("ssh_port") or CFG.get("vlm_remote_ssh_port", 22))
    remote_root = str(data.get("remote_root") or CFG.get("vlm_remote_root", "~/aBotTesty_vlm_jobs"))
    timeout_s = float(data.get("timeout_s") or 25)

    remote_cmd = f"""
set +e
ROOT="{remote_root}"
ROOT="${{ROOT/#\\~/$HOME}}"
echo "__ABOT_SECTION__ processes"
pgrep -af "[t]orchrun|[l]lamafactory|effective_train_config|train_remote.sh" || true
echo "__ABOT_SECTION__ jobs"
ls -td "$ROOT"/abot_vlm_* 2>/dev/null | head -12 || true
echo "__ABOT_SECTION__ adapters"
find "$ROOT" -path "*/outputs/*/adapter_model.safetensors" -printf "%TY-%Tm-%Td %TH:%TM:%TS %s %p\\n" 2>/dev/null | sort -r | head -12 || true
echo "__ABOT_SECTION__ latest_log"
latest=$(ls -td "$ROOT"/abot_vlm_* 2>/dev/null | head -1)
echo "latest=$latest"
if [ -n "$latest" ]; then
  f=$(find "$latest" -maxdepth 3 -type f \\( -name "*.log" -o -name "*train*.txt" -o -name "*monitor*" \\) -print 2>/dev/null | head -1)
  echo "log=$f"
  if [ -n "$f" ]; then tail -120 "$f"; fi
fi
"""
    cmd = ["ssh", "-p", str(port), f"{user}@{host}", remote_cmd]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        stdout = res.stdout or ""
        stderr = res.stderr or ""
        combined = stdout + "\n" + stderr
        oom = ("OutOfMemoryError" in combined) or ("CUDA out of memory" in combined)
        failed = oom or ("Traceback" in combined) or ("ChildFailedError" in combined) or ("exit status 1" in combined)
        adapter_present = "adapter_model.safetensors" in combined
        proc_section = combined.split("__ABOT_SECTION__ processes", 1)[-1].split("__ABOT_SECTION__ jobs", 1)[0]
        running = any(x in proc_section for x in ("torchrun", "llamafactory-cli", "effective_train_config.yaml", "train_remote.sh"))
        status = "running" if running else ("completed_adapter_available" if adapter_present and not failed else ("failed_oom" if oom else ("failed" if failed else "idle_no_active_training")))
        return jsonify(
            ok=(res.returncode == 0),
            status=status,
            remote={"host": host, "user": user, "remote_root": remote_root},
            returncode=res.returncode,
            running=running,
            adapter_present=adapter_present,
            oom=oom,
            failed=failed,
            stdout=stdout,
            stderr=stderr,
            command=" ".join(cmd[:4]) + " ...",
            ts=datetime.now().isoformat(timespec="seconds"),
        )
    except Exception as exc:
        return jsonify(ok=False, status="diagnose_error", error=str(exc), remote={"host": host, "user": user, "remote_root": remote_root}), 500

# ---- end aBotTesty v38.10 learning export / remote status repair ----
'''


def patch_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if PATCH_MARKER in text:
        print(f"Already patched: {path}")
        return

    positions = [p for p in [
        text.find('if __name__ == "__main__":'),
        text.find("if __name__ == '__main__':"),
    ] if p >= 0]
    if not positions:
        raise SystemExit("Could not find __main__ guard. Refusing to patch.")
    insert_at = min(positions)

    backup = path.with_suffix(path.suffix + ".bak-v3810-learning-export-status-" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    backup.write_text(text, encoding="utf-8")

    new_text = text[:insert_at].rstrip() + PATCH_BLOCK + "\n\n" + text[insert_at:].lstrip()
    path.write_text(new_text, encoding="utf-8")
    print(f"Patched: {path}")
    print(f"Backup:  {backup}")


def main() -> int:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "merged_app.py").resolve()
    if not target.is_file():
        print(f"ERROR: not found: {target}", file=sys.stderr)
        return 2

    patch_file(target)

    updated = target.read_text(encoding="utf-8")
    checks = {
        "patch_marker": PATCH_MARKER in updated,
        "safe_export_override": "def _abot_safe_learning_export" in updated,
        "max_records_normalizer": "def _abot_v3810_normalize_max_records" in updated,
        "latest_dataset_override": "Prefer the newest trainable dataset" in updated,
        "remote_diagnose_route": '/api/learning/remote/diagnose' in updated,
    }
    for name, ok in checks.items():
        print(f"check {name}: {'OK' if ok else 'MISSING'}")
    if not all(checks.values()):
        return 3

    try:
        py_compile.compile(str(target), doraise=True)
        print("py_compile target: OK")
    except Exception as exc:
        print(f"py_compile target: FAILED: {exc}", file=sys.stderr)
        return 4

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

