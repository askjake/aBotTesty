#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore


SAFE_ACTIONS = {
    "up", "down", "left", "right", "guide", "back", "home", "info",
    "live", "recall", "input", "options", "dvr", "ch_up", "ch_down",
    "play", "pause", "stop", "fwd", "rwd",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
}

RISKY_SELECT_TEXT = {
    "purchase", "rent", "buy", "order", "subscribe", "delete",
    "factory", "reset", "format", "payment", "pin", "adult",
}


def _now_s() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _json_load(path: Path, default: Any) -> Any:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _json_save(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _norm_action(action: Any) -> str:
    text = str(action or "").strip().lower()
    aliases = {
        "ok": "select",
        "enter": "select",
        "key_ok": "select",
        "key_up": "up",
        "key_down": "down",
        "key_left": "left",
        "key_right": "right",
        "channel_up": "ch_up",
        "channel_down": "ch_down",
        "ch+": "ch_up",
        "ch-": "ch_down",
        "live tv": "live",
        "exit": "back",
    }
    return aliases.get(text, text)


def _parse_jsonish(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    text = str(value or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            pass
    return {"text": text}


def _remote_root_abs(remote_root: str, user: str) -> str:
    rr = str(remote_root or "~/aBotTesty_vlm_jobs")
    if rr.startswith("~/"):
        return f"/home/{user}/{rr[2:]}"
    return rr


class VLMModelManager:
    """Runtime manager for trained VLM policy/perception/verifier usage.

    This class intentionally keeps model output behind a safety gate. It never
    sends a key. It only returns an accepted/rejected policy suggestion.
    """

    def __init__(self, root_dir: str | Path, cfg: Dict[str, Any]) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.cfg = cfg
        self.state_path = self.root_dir / "models" / "vlm_runtime_state.json"
        self.local_adapter_root = self.root_dir / "models" / "vlm_adapters"
        self.local_adapter_root.mkdir(parents=True, exist_ok=True)

    def default_state(self) -> Dict[str, Any]:
        host = str(self.cfg.get("vlm_remote_host", "10.79.85.35"))
        return {
            "enabled": bool(self.cfg.get("vlm_policy_enabled", False)),
            "mode": str(self.cfg.get("vlm_policy_mode", "shadow")),
            "server_url": str(self.cfg.get("vlm_policy_server_url", f"http://{host}:8765")),
            "active_run": "",
            "active_adapter_path": "",
            "base_model": str(self.cfg.get("vlm_default_model_3090", "Qwen/Qwen3-VL-8B-Instruct")),
            "min_confidence": float(self.cfg.get("vlm_policy_min_confidence", 0.65)),
            "max_risk": float(self.cfg.get("vlm_policy_max_risk", 0.35)),
            "allow_select": bool(self.cfg.get("vlm_policy_allow_select", False)),
            "timeout_s": float(self.cfg.get("vlm_policy_timeout_s", 30.0)),
            "last_update": "",
            "last_health": {},
            "last_policy": {},
            "stats": {
                "calls": 0,
                "accepted": 0,
                "rejected": 0,
                "errors": 0,
                "shadow_logged": 0,
                "assist_reordered": 0,
                "autonomous_chosen": 0,
                "last_error": "",
                "last_latency_s": 0.0,
            },
        }

    def load_state(self) -> Dict[str, Any]:
        state = self.default_state()
        saved = _json_load(self.state_path, {})
        if isinstance(saved, dict):
            state.update(saved)
            state["stats"] = {**self.default_state()["stats"], **(saved.get("stats") or {})}
        return state

    def save_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        state["last_update"] = _now_s()
        _json_save(self.state_path, state)
        return state

    def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        state = self.load_state()
        allowed = {
            "enabled", "mode", "server_url", "active_run", "active_adapter_path",
            "base_model", "min_confidence", "max_risk", "allow_select", "timeout_s",
        }
        for key, value in updates.items():
            if key not in allowed:
                continue
            if key in {"enabled", "allow_select"}:
                value = str(value).lower() in {"1", "true", "yes", "on"} if isinstance(value, str) else bool(value)
            elif key in {"min_confidence", "max_risk", "timeout_s"}:
                value = float(value)
            elif key == "mode":
                value = str(value or "shadow").lower()
                if value not in {"off", "shadow", "assist", "autonomous"}:
                    value = "shadow"
            else:
                value = str(value or "")
            state[key] = value
        return self.save_state(state)

    def _record(self, **stats: Any) -> None:
        state = self.load_state()
        st = state.setdefault("stats", {})
        for key, value in stats.items():
            if isinstance(value, int):
                st[key] = int(st.get(key) or 0) + value
            else:
                st[key] = value
        self.save_state(state)

    def health(self) -> Dict[str, Any]:
        state = self.load_state()
        url = str(state.get("server_url") or "").rstrip("/")
        if not url:
            return {"ok": False, "error": "no server_url configured"}
        try:
            r = requests.get(url + "/health", timeout=5)
            payload = r.json()
            payload["http_status"] = r.status_code
            payload["server_url"] = url
            state["last_health"] = payload
            self.save_state(state)
            return payload
        except Exception as exc:
            out = {"ok": False, "error": str(exc), "server_url": url}
            state["last_health"] = out
            self.save_state(state)
            return out

    def infer_frame(
        self,
        frame: Any,
        task: str,
        goal: str = "",
        action: str = "",
        timeout_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        if cv2 is None:
            raise RuntimeError("cv2 is not available")
        if frame is None or not getattr(frame, "size", 0):
            raise RuntimeError("no frame available for VLM inference")

        state = self.load_state()
        url = str(state.get("server_url") or "").rstrip("/") + "/infer"
        timeout = float(timeout_s if timeout_s is not None else state.get("timeout_s", 30.0))

        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
        if not ok:
            raise RuntimeError("failed to encode frame as JPEG")

        t0 = time.time()
        files = {"image": ("snapshot.jpg", buf.tobytes(), "image/jpeg")}
        data = {"task": task, "goal": goal, "action": action}
        resp = requests.post(url, data=data, files=files, timeout=timeout)
        latency = time.time() - t0

        try:
            payload = resp.json()
        except Exception:
            payload = {"ok": False, "text": resp.text}

        payload["http_status"] = resp.status_code
        payload["latency_s"] = round(latency, 3)
        resp.raise_for_status()
        return payload

    def policy_from_frame(self, frame: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        state = self.load_state()
        mode = str(state.get("mode") or "shadow").lower()
        enabled = bool(state.get("enabled")) and mode != "off"

        allowed = [_norm_action(x) for x in (context.get("allowed_actions") or [])]
        allowed = [x for x in allowed if x]
        allowed_set = set(allowed)

        base = {
            "ok": True,
            "enabled": enabled,
            "mode": mode,
            "accepted": False,
            "suggested_action": "",
            "action_sequence": [],
            "reason": "",
            "confidence": 0.0,
            "risk": "",
            "raw": {},
            "allowed_actions": allowed,
        }

        if not enabled:
            base["reason"] = "vlm_policy_disabled"
            return base
        if not allowed:
            base["reason"] = "no_allowed_actions"
            return base

        try:
            self._record(calls=1)
            goal = str(context.get("goal") or self.cfg.get("vlm_policy_goal") or "Explore the TV UI safely. Do not purchase, rent, subscribe, delete, reset, or confirm anything.")
            state_hint = json.dumps({
                "state_id": context.get("state_id"),
                "label": context.get("label"),
                "screen_kind": context.get("screen_kind"),
                "allowed_actions": allowed,
                "safety": {
                    "select_allowed": bool(state.get("allow_select")),
                    "allowed_only": True,
                },
            }, ensure_ascii=False)
            full_goal = f"{goal}\nAllowed remote actions: {allowed}. Choose only one of those actions. Context: {state_hint}"

            resp = self.infer_frame(frame, task="policy", goal=full_goal, timeout_s=float(state.get("timeout_s", 30.0)))
            parsed = _parse_jsonish(resp.get("json") or resp.get("text") or resp)

            seq = parsed.get("action_sequence") or parsed.get("actions") or parsed.get("action") or []
            if isinstance(seq, str):
                seq = [seq]
            seq = [_norm_action(x) for x in seq if _norm_action(x)]

            suggested = seq[0] if seq else ""
            confidence = float(parsed.get("confidence") or resp.get("confidence") or 0.0)

            risk_raw = parsed.get("risk", parsed.get("risk_score", ""))
            risk_score = 0.0
            risk_text = str(risk_raw).lower()
            if isinstance(risk_raw, (int, float)):
                risk_score = float(risk_raw)
            elif risk_text in {"blocked", "danger", "dangerous", "unsafe", "high"}:
                risk_score = 1.0
            elif risk_text in {"medium", "warn", "warning"}:
                risk_score = 0.5
            elif risk_text in {"safe", "low", "0", "none", ""}:
                risk_score = 0.0
            else:
                risk_score = 0.25

            reason = ""
            accepted = True
            if not suggested:
                accepted = False
                reason = "no_action_sequence"
            elif suggested not in allowed_set:
                accepted = False
                reason = f"suggested_action_not_allowed:{suggested}"
            elif suggested == "select" and not bool(state.get("allow_select")):
                accepted = False
                reason = "select_blocked_by_policy"
            elif confidence < float(state.get("min_confidence", 0.65)):
                accepted = False
                reason = f"confidence_below_threshold:{confidence:.3f}"
            elif risk_score > float(state.get("max_risk", 0.35)):
                accepted = False
                reason = f"risk_above_threshold:{risk_score:.3f}"

            # Extra text safety: do not trust a select on purchase/rent/etc.
            text_blob = json.dumps(parsed, ensure_ascii=False).lower()
            if suggested == "select" and any(tok in text_blob for tok in RISKY_SELECT_TEXT):
                accepted = False
                reason = "select_blocked_due_to_risky_text"

            out = {
                **base,
                "accepted": accepted,
                "suggested_action": suggested if accepted else "",
                "raw_suggested_action": suggested,
                "action_sequence": seq,
                "confidence": round(confidence, 4),
                "risk": risk_raw,
                "risk_score": round(risk_score, 4),
                "reason": reason or "accepted",
                "raw": parsed,
                "latency_s": resp.get("latency_s"),
                "health_hint": state.get("last_health") or {},
            }

            state["last_policy"] = out
            self.save_state(state)
            self._record(
                accepted=1 if accepted else 0,
                rejected=0 if accepted else 1,
                last_latency_s=float(resp.get("latency_s") or 0.0),
            )
            return out

        except Exception as exc:
            self._record(errors=1, last_error=str(exc))
            return {**base, "ok": False, "accepted": False, "reason": str(exc), "error": str(exc)}

    def apply_policy_to_actions(self, actions: List[str], decision: Dict[str, Any]) -> List[str]:
        mode = str(decision.get("mode") or "shadow").lower()
        action = _norm_action(decision.get("suggested_action"))
        if not decision.get("accepted") or not action or action not in actions:
            return actions
        if mode == "shadow":
            self._record(shadow_logged=1)
            return actions
        if mode == "assist":
            self._record(assist_reordered=1)
            return [action] + [a for a in actions if a != action]
        if mode == "autonomous":
            self._record(autonomous_chosen=1)
            return [action]
        return actions


    def remote_runs(self, limit: int = 40) -> Dict[str, Any]:
        """List available remote VLM training runs with promotion-ready stats."""
        user = str(self.cfg.get("vlm_remote_user", "montjac"))
        host = str(self.cfg.get("vlm_remote_host", "10.79.85.35"))
        remote_root = _remote_root_abs(str(self.cfg.get("vlm_remote_root", "~/aBotTesty_vlm_jobs")), user)
        limit = max(1, min(200, int(limit or 40)))

        script = r"""
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
limit = int(sys.argv[2])

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

def read_json(path, default=None):
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def count_lines(path):
    try:
        if not path.is_file():
            return 0
        n = 0
        with path.open("rb") as f:
            for _ in f:
                n += 1
        return n
    except Exception:
        return 0

def count_images(path):
    try:
        if not path.exists():
            return 0
        return sum(1 for x in path.rglob("*") if x.is_file() and x.suffix.lower() in IMAGE_EXTS)
    except Exception:
        return 0

def tail_text(path, max_bytes=220000):
    try:
        if not path.is_file():
            return ""
        data = path.read_bytes()
        return data[-max_bytes:].decode("utf-8", errors="replace")
    except Exception:
        return ""

def first_float(*vals):
    for v in vals:
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            vv = v.replace(",", "")
            m = re.search(r"[-+]?\d+(?:\.\d+)?", vv)
            if m:
                try:
                    return float(m.group(0))
                except Exception:
                    pass
    return None

def first_int(*vals):
    f = first_float(*vals)
    return int(f) if f is not None else None

def job_summary(d):
    name = d.name
    dataset = d / "dataset"
    sft = dataset / "sft"
    out = d / "outputs" / name
    logp = d / "train.log"
    log = tail_text(logp)

    counts = {
        "screen_perception": count_lines(sft / "screen_perception.jsonl"),
        "action_policy": count_lines(sft / "action_policy.jsonl"),
        "outcome_verifier": count_lines(sft / "outcome_verifier.jsonl"),
        "episodes": count_lines(dataset / "episodes.jsonl"),
        "images": count_images(dataset / "images"),
    }

    train_results = read_json(out / "train_results.json", {}) or {}
    all_results = read_json(out / "all_results.json", {}) or {}
    trainer_state = read_json(out / "trainer_state.json", {}) or {}

    metrics = {}
    for src in (all_results, train_results):
        if isinstance(src, dict):
            metrics.update(src)

    log_history = trainer_state.get("log_history") if isinstance(trainer_state, dict) else []
    losses = []
    if isinstance(log_history, list):
        for item in log_history:
            if isinstance(item, dict) and item.get("loss") is not None:
                try:
                    losses.append(float(item["loss"]))
                except Exception:
                    pass

    adapter = out / "adapter_model.safetensors"
    has_adapter = adapter.is_file()

    train_loss = first_float(
        metrics.get("train_loss"),
        metrics.get("loss"),
        min(losses) if losses else None,
    )
    steps = first_int(
        metrics.get("global_step"),
        metrics.get("total_steps"),
        trainer_state.get("global_step") if isinstance(trainer_state, dict) else None,
    )
    runtime_s = first_float(
        metrics.get("train_runtime"),
        metrics.get("train_runtime_s"),
    )
    samples_s = first_float(
        metrics.get("train_samples_per_second"),
        metrics.get("samples_per_second"),
    )

    total_sft = counts["screen_perception"] + counts["action_policy"] + counts["outcome_verifier"]

    if has_adapter:
        status = "completed"
    elif "Dataset is not trainable" in log or "ERROR line" in log or "Traceback" in log or "ValueError" in log:
        status = "failed"
    elif "starting llamafactory-cli train" in log or "Running training" in log:
        status = "running_or_interrupted"
    elif logp.is_file():
        status = "incomplete"
    else:
        status = "unknown"

    score = 0
    if status == "completed":
        score += 100000
    if has_adapter:
        score += 50000
    score += total_sft
    if train_loss is not None:
        score += int(max(0, 10_000 - train_loss * 1000))

    mtime = d.stat().st_mtime if d.exists() else 0
    return {
        "run_name": name,
        "remote_dir": str(d),
        "output_dir": str(out),
        "status": status,
        "has_adapter": has_adapter,
        "adapter_model": str(adapter) if has_adapter else "",
        "adapter_size_mb": round(adapter.stat().st_size / 1048576, 1) if has_adapter else 0,
        "dataset_counts": counts,
        "total_sft_rows": total_sft,
        "metrics": {
            "train_loss": train_loss,
            "best_loss": train_loss,
            "total_steps": steps,
            "train_runtime_s": runtime_s,
            "train_samples_per_second": samples_s,
        },
        "mtime": mtime,
        "score": score,
        "log_tail_hint": log[-1200:],
    }

jobs = []
if root.exists():
    dirs = [d for d in root.glob("abot_vlm_*") if d.is_dir()]
    dirs.sort(key=lambda x: x.stat().st_mtime if x.exists() else 0, reverse=True)
    for d in dirs[:limit]:
        jobs.append(job_summary(d))

print(json.dumps({"ok": True, "remote_root": str(root), "remote_runs": jobs}, ensure_ascii=False))
"""
        cmd = f"python3 - {shlex.quote(remote_root)} {limit} <<'PYREMOTE'\n{script}\nPYREMOTE"
        p = subprocess.run(["ssh", f"{user}@{host}", cmd], text=True, capture_output=True, timeout=60)

        if p.returncode != 0:
            return {
                "ok": False,
                "host": host,
                "remote_root": remote_root,
                "returncode": p.returncode,
                "stdout": p.stdout[-4000:],
                "stderr": p.stderr[-4000:],
                "remote_runs": [],
            }

        try:
            payload = json.loads(p.stdout.strip() or "{}")
        except Exception as exc:
            return {
                "ok": False,
                "error": f"unable to parse remote run list: {exc}",
                "stdout": p.stdout[-4000:],
                "stderr": p.stderr[-4000:],
                "remote_runs": [],
            }

        state = self.load_state()
        active = str(state.get("active_run") or "")
        health = state.get("last_health") or {}
        health_adapter = str(health.get("adapter_path") or "")

        for run in payload.get("remote_runs", []) or []:
            rn = str(run.get("run_name") or "")
            run["is_active_run"] = bool(active and rn == active)
            run["is_health_adapter"] = bool(health_adapter and rn in health_adapter)
            local = self.local_adapter_root / rn / "adapter_model.safetensors"
            run["is_pulled_local"] = local.is_file()

        payload["host"] = host
        payload["active_run"] = active
        payload["health_adapter_path"] = health_adapter
        return payload


    def local_adapters(self) -> List[Dict[str, Any]]:
        out = []
        root = self.local_adapter_root
        for d in sorted(root.glob("*"), key=lambda x: x.stat().st_mtime if x.exists() else 0, reverse=True):
            if not d.is_dir():
                continue
            adapter = d / "adapter_model.safetensors"
            cfg = d / "adapter_config.json"
            if adapter.is_file():
                out.append({
                    "run_name": d.name,
                    "path": str(d),
                    "adapter_model": str(adapter),
                    "size_mb": round(adapter.stat().st_size / 1_048_576, 1),
                    "has_config": cfg.is_file(),
                    "mtime": d.stat().st_mtime,
                })
        return out

    def pull_remote_adapter(self, run_name: str) -> Dict[str, Any]:
        run_name = str(run_name or "").strip()
        if not run_name:
            return {"ok": False, "error": "run_name required"}

        user = str(self.cfg.get("vlm_remote_user", "montjac"))
        host = str(self.cfg.get("vlm_remote_host", "10.79.85.35"))
        remote_root = _remote_root_abs(str(self.cfg.get("vlm_remote_root", "~/aBotTesty_vlm_jobs")), user)
        src = f"{user}@{host}:{remote_root}/{run_name}/outputs/{run_name}/"
        dest = self.local_adapter_root / run_name
        dest.mkdir(parents=True, exist_ok=True)

        cmd = ["rsync", "-az", src, str(dest) + "/"]
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=1800)
        ok = p.returncode == 0 and (dest / "adapter_model.safetensors").is_file()
        return {
            "ok": ok,
            "run_name": run_name,
            "src": src,
            "dest": str(dest),
            "returncode": p.returncode,
            "stdout": p.stdout[-4000:],
            "stderr": p.stderr[-4000:],
        }

    def promote_remote_adapter(self, run_name: str, pull_local: bool = True, restart_shadow: bool = True) -> Dict[str, Any]:
        run_name = str(run_name or "").strip()
        if not run_name:
            return {"ok": False, "error": "run_name required"}

        state = self.load_state()
        user = str(self.cfg.get("vlm_remote_user", "montjac"))
        host = str(self.cfg.get("vlm_remote_host", "10.79.85.35"))
        remote_root = _remote_root_abs(str(self.cfg.get("vlm_remote_root", "~/aBotTesty_vlm_jobs")), user)
        base_model = str(state.get("base_model") or self.cfg.get("vlm_default_model_3090", "Qwen/Qwen3-VL-8B-Instruct"))
        adapter = f"{remote_root}/{run_name}/outputs/{run_name}"

        result: Dict[str, Any] = {
            "ok": True,
            "run_name": run_name,
            "remote_adapter": adapter,
            "pulled": None,
            "restart": None,
        }

        if pull_local:
            result["pulled"] = self.pull_remote_adapter(run_name)

        if restart_shadow:
            script = f'''
set -Eeuo pipefail
ROOT={shlex.quote(remote_root)}
VENV="$ROOT/.venv_shadow"
LOG="$ROOT/logs/vlm_shadow_server.log"
PIDFILE="$ROOT/logs/vlm_shadow_server.pid"
SERVER="$ROOT/vlm_shadow_server.py"
ADAPTER="$ROOT/{shlex.quote(run_name)}/outputs/{shlex.quote(run_name)}"
mkdir -p "$ROOT/logs"
test -f "$SERVER"
test -x "$VENV/bin/python"
test -f "$ADAPTER/adapter_model.safetensors"
if [ -f "$PIDFILE" ]; then
  OLD="$(cat "$PIDFILE" || true)"
  if [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null; then
    kill "$OLD" || true
    sleep 5
    kill -9 "$OLD" 2>/dev/null || true
  fi
fi
"$VENV/bin/python" -m py_compile "$SERVER"
: > "$LOG"
CUDA_VISIBLE_DEVICES=1 nohup "$VENV/bin/python" "$SERVER" \\
  --host 0.0.0.0 \\
  --port 8765 \\
  --base-model {shlex.quote(base_model)} \\
  --adapter "$ADAPTER" \\
  >> "$LOG" 2>&1 &
echo $! > "$PIDFILE"
echo "started pid=$(cat "$PIDFILE") adapter=$ADAPTER"
'''
            p = subprocess.run(["ssh", f"{user}@{host}", script], text=True, capture_output=True, timeout=180)
            result["restart"] = {
                "ok": p.returncode == 0,
                "returncode": p.returncode,
                "stdout": p.stdout[-4000:],
                "stderr": p.stderr[-4000:],
            }
            if p.returncode != 0:
                result["ok"] = False

        state["active_run"] = run_name
        state["active_adapter_path"] = adapter
        state["server_url"] = str(state.get("server_url") or f"http://{host}:8765")
        self.save_state(state)

        return result

    def status(self) -> Dict[str, Any]:
        state = self.load_state()
        return {
            "ok": True,
            "state": state,
            "health": self.health(),
            "local_adapters": self.local_adapters()[:20],
        }
