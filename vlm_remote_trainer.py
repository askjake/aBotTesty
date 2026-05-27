#!/usr/bin/env python3
"""Remote VLM training job helper for aBotTesty.

Phase 1 does not train inside the Flask app.  It packages an exported dataset and
submits it to a GPU host over SSH/rsync.  The trainer machine owns the heavy CUDA
stack; the capture machine stays focused on video/control/collection.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import tarfile
import textwrap
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_HOST = "10.79.85.35"
DEFAULT_USER = "montjac"
DEFAULT_REMOTE_ROOT = "~/aBotTesty_vlm_jobs"
DEFAULT_MODEL_3090 = "Qwen/Qwen3-VL-8B-Instruct"
DEFAULT_MODEL_3080 = "Qwen/Qwen2.5-VL-7B-Instruct"


@dataclass
class VLMRemoteJob:
    dataset_dir: str
    host: str = DEFAULT_HOST
    user: str = DEFAULT_USER
    remote_root: str = DEFAULT_REMOTE_ROOT
    model_name: str = DEFAULT_MODEL_3090
    trainer: str = "llamafactory"
    run_name: str = ""
    ssh_port: int = 22
    dry_run: bool = True
    extra_env: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.run_name:
            self.run_name = "abot_vlm_" + datetime.now().strftime("%Y%m%d_%H%M%S")

    @property
    def remote(self) -> str:
        return f"{self.user}@{self.host}"

    @property
    def remote_run_dir(self) -> str:
        return f"{self.remote_root.rstrip('/')}/{self.run_name}"

    def commands(self, archive_name: str = "dataset.tar.gz") -> Dict[str, Any]:
        ssh_base = ["ssh", "-p", str(self.ssh_port), self.remote]
        rsync_base = ["rsync", "-az", "-e", f"ssh -p {self.ssh_port}"]
        remote_dir = self.remote_run_dir
        train_cmd = f"cd {shlex.quote(remote_dir)} && bash train_remote.sh"
        return {
            "mkdir": ssh_base + [f"mkdir -p {shlex.quote(remote_dir)}"],
            "rsync_archive": rsync_base + [archive_name, f"{self.remote}:{remote_dir}/dataset.tar.gz"],
            "rsync_scripts": rsync_base + ["train_remote.sh", "train_config.yaml", f"{self.remote}:{remote_dir}/"],
            "train": ssh_base + [train_cmd],
            "tail_logs": ssh_base + [f"tail -f {shlex.quote(remote_dir)}/train.log"],
            "remote_dir": remote_dir,
        }


def run_cmd(cmd: List[str], dry_run: bool = True, cwd: Optional[Path] = None) -> Dict[str, Any]:
    printable = " ".join(shlex.quote(x) for x in cmd)
    if dry_run:
        return {"ok": True, "dry_run": True, "cmd": printable}
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True)
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "cmd": printable,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
    }


def make_training_config(job: VLMRemoteJob, hardware: str = "2x3090") -> str:
    # LLaMA-Factory config template.  Exact names can change between releases, so
    # keep it conservative and document it in the generated file.
    cutoff = 4096 if "3090" in hardware else 3072
    batch = 1
    grad_accum = 16 if "3090" in hardware else 24
    quant = 4
    return textwrap.dedent(f"""
    # aBotTesty v37 VLM LoRA training config
    # Intended trainer: LLaMA-Factory current release
    # Model: {job.model_name}
    # Hardware profile: {hardware}
    #
    # Dataset adapter expected:
    #   dataset/episodes.jsonl
    #   dataset/sft/screen_perception.jsonl
    #   dataset/sft/action_policy.jsonl
    #   dataset/sft/outcome_verifier.jsonl
    #
    # First pass target: perception only.  Add policy/verifier after the JSON
    # validity and risk-recall checks pass.
    model_name_or_path: {job.model_name}
    stage: sft
    do_train: true
    finetuning_type: lora
    lora_target: all
    template: qwen2_vl
    dataset: abot_screen_perception
    dataset_dir: dataset_registry
    cutoff_len: {cutoff}
    preprocessing_num_workers: 8
    output_dir: outputs/{job.run_name}
    logging_steps: 5
    save_steps: 100
    plot_loss: true
    overwrite_output_dir: true
    per_device_train_batch_size: {batch}
    gradient_accumulation_steps: {grad_accum}
    learning_rate: 2.0e-4
    num_train_epochs: 2.0
    lr_scheduler_type: cosine
    warmup_ratio: 0.05
    bf16: true
    quantization_bit: {quant}
    flash_attn: fa2
    report_to: none
    """).strip() + "\n"


def make_remote_train_script(job: VLMRemoteJob, hardware: str = "2x3090") -> str:
    model = shlex.quote(job.model_name)
    return textwrap.dedent(f"""
    #!/usr/bin/env bash
    set -Eeuo pipefail
    echo "[v37] remote train job: {job.run_name}" | tee train.log
    echo "[v37] model: {job.model_name}" | tee -a train.log
    nvidia-smi | tee -a train.log || true

    if [ ! -d .venv ]; then
      python3 -m venv .venv
    fi
    source .venv/bin/activate
    python -m pip install --upgrade pip wheel setuptools

    # CUDA 12.1 wheels are broadly compatible with Ampere cards. If your remote
    # already has a preferred CUDA/PyTorch stack, install that first and comment
    # this line out.
    python -m pip install --upgrade torch torchvision --index-url https://download.pytorch.org/whl/cu121
    python -m pip install --upgrade git+https://github.com/huggingface/transformers accelerate datasets peft bitsandbytes pillow qwen-vl-utils tensorboard
    python -m pip install --upgrade git+https://github.com/hiyouga/LLaMA-Factory.git

    rm -rf dataset dataset_registry
    mkdir -p dataset dataset_registry
    tar -xzf dataset.tar.gz -C dataset --strip-components=1

    cat > dataset_registry/dataset_info.json <<'JSON'
    {{
      "abot_screen_perception": {{
        "file_name": "../dataset/sft/screen_perception.jsonl",
        "formatting": "sharegpt",
        "columns": {{"messages": "messages", "images": "image"}},
        "tags": {{"role_tag": "role", "content_tag": "content", "user_tag": "user", "assistant_tag": "assistant"}}
      }},
      "abot_action_policy": {{
        "file_name": "../dataset/sft/action_policy.jsonl",
        "formatting": "sharegpt",
        "columns": {{"messages": "messages", "images": "image"}},
        "tags": {{"role_tag": "role", "content_tag": "content", "user_tag": "user", "assistant_tag": "assistant"}}
      }},
      "abot_outcome_verifier": {{
        "file_name": "../dataset/sft/outcome_verifier.jsonl",
        "formatting": "sharegpt",
        "columns": {{"messages": "messages", "images": "images"}},
        "tags": {{"role_tag": "role", "content_tag": "content", "user_tag": "user", "assistant_tag": "assistant"}}
      }}
    }}
    JSON

    cp train_config.yaml effective_train_config.yaml
    echo "[v37] starting llamafactory-cli train" | tee -a train.log
    CUDA_VISIBLE_DEVICES=0,1 llamafactory-cli train effective_train_config.yaml 2>&1 | tee -a train.log
    echo "[v37] training finished" | tee -a train.log
    """).strip() + "\n"


def package_dataset(dataset_dir: Path, work_dir: Path) -> Path:
    dataset_dir = dataset_dir.resolve()
    if not dataset_dir.is_dir():
        raise FileNotFoundError(f"dataset_dir not found: {dataset_dir}")
    archive = work_dir / "dataset.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(dataset_dir, arcname=dataset_dir.name)
    return archive


def prepare_job_files(job: VLMRemoteJob, out_dir: Path, hardware: str = "2x3090") -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = package_dataset(Path(job.dataset_dir), out_dir)
    train_script = out_dir / "train_remote.sh"
    config = out_dir / "train_config.yaml"
    train_script.write_text(make_remote_train_script(job, hardware=hardware), encoding="utf-8")
    train_script.chmod(0o755)
    config.write_text(make_training_config(job, hardware=hardware), encoding="utf-8")
    plan = {"job": asdict(job), "archive": str(archive), "train_script": str(train_script), "config": str(config), "commands": job.commands(archive.name)}
    (out_dir / "remote_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return plan


def submit_job(job: VLMRemoteJob, prepared_dir: Path) -> Dict[str, Any]:
    cmds = job.commands("dataset.tar.gz")
    results = []
    for name in ("mkdir", "rsync_archive", "rsync_scripts", "train"):
        results.append({"step": name, **run_cmd(cmds[name], dry_run=job.dry_run, cwd=prepared_dir)})
        if not results[-1].get("ok"):
            break
    return {"ok": all(r.get("ok") for r in results), "dry_run": job.dry_run, "remote_dir": cmds["remote_dir"], "results": results, "tail_logs": " ".join(shlex.quote(x) for x in cmds["tail_logs"])}


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Prepare/submit aBotTesty remote VLM training jobs")
    sub = p.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--dataset-dir", required=True)
    common.add_argument("--host", default=DEFAULT_HOST)
    common.add_argument("--user", default=DEFAULT_USER)
    common.add_argument("--remote-root", default=DEFAULT_REMOTE_ROOT)
    common.add_argument("--model", default=DEFAULT_MODEL_3090)
    common.add_argument("--run-name", default="")
    common.add_argument("--ssh-port", type=int, default=22)
    common.add_argument("--hardware", default="2x3090", choices=["2x3090", "2x3080"])
    common.add_argument("--out-dir", default="vlm_jobs/latest")
    sp = sub.add_parser("prepare", parents=[common])
    sp = sub.add_parser("submit", parents=[common])
    sp.add_argument("--execute", action="store_true", help="Actually run ssh/rsync/train. Default is dry-run.")
    args = p.parse_args(argv)
    job = VLMRemoteJob(
        dataset_dir=args.dataset_dir,
        host=args.host,
        user=args.user,
        remote_root=args.remote_root,
        model_name=args.model,
        run_name=args.run_name,
        ssh_port=args.ssh_port,
        dry_run=not getattr(args, "execute", False),
    )
    out_dir = Path(args.out_dir)
    plan = prepare_job_files(job, out_dir=out_dir, hardware=args.hardware)
    if args.cmd == "prepare":
        print(json.dumps({"ok": True, **plan}, indent=2))
        return 0
    result = submit_job(job, prepared_dir=out_dir)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
