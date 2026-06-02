#!/usr/bin/env bash
    set -Eeuo pipefail
    trap 'rc=$?; echo "[v37-monitor] ERROR line ${LINENO} exit=${rc}" | tee -a train.log; exit ${rc}' ERR
    echo "[v37.1] remote train job: abot_vlm_20260528_090631" | tee train.log
    echo "[v37.1] model: Qwen/Qwen3-VL-8B-Instruct" | tee -a train.log
    nvidia-smi | tee -a train.log || true

    need_py311() {
      "$1" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
    }

    activate_vlm_env() {
      if [ -x "$HOME/aBotTesty_vlm_jobs/.venv/bin/python" ] && need_py311 "$HOME/aBotTesty_vlm_jobs/.venv/bin/python"; then
        source "$HOME/aBotTesty_vlm_jobs/.venv/bin/activate"
        return 0
      fi
      if command -v python3.11 >/dev/null 2>&1 && need_py311 python3.11; then
        python3.11 -m venv "$HOME/aBotTesty_vlm_jobs/.venv"
        source "$HOME/aBotTesty_vlm_jobs/.venv/bin/activate"
        return 0
      fi
      if command -v python3 >/dev/null 2>&1 && need_py311 python3; then
        python3 -m venv "$HOME/aBotTesty_vlm_jobs/.venv"
        source "$HOME/aBotTesty_vlm_jobs/.venv/bin/activate"
        return 0
      fi
      if command -v conda >/dev/null 2>&1; then
        CONDA_BASE="$(conda info --base)"
        source "$CONDA_BASE/etc/profile.d/conda.sh"
        if ! conda env list | awk '{print $1}' | grep -qx 'abot-vlm-py311'; then
          conda create -y -n abot-vlm-py311 python=3.11
        fi
        conda activate abot-vlm-py311
        return 0
      fi
      echo "ERROR: LLaMA-Factory requires Python >=3.11, but this host default is:" >&2
      python3 --version >&2 || true
      echo "Install python3.11/python3.11-venv or conda, then rerun setup." >&2
      exit 11
    }

    activate_vlm_env
    python --version
    python - <<'PY'
import sys
assert sys.version_info >= (3, 11), sys.version
print('python_ok', sys.version.split()[0])
PY

    echo "[v37-monitor] verifying training dependencies" | tee -a train.log
    python - <<'PYDEPS' 2>&1 | tee -a train.log
import torch, transformers, peft, bitsandbytes
print("torch", torch.__version__, "cuda", torch.version.cuda, "cuda_available", torch.cuda.is_available(), "gpus", torch.cuda.device_count())
print("transformers", transformers.__version__)
print("peft", peft.__version__)
print("bitsandbytes", bitsandbytes.__version__)
import peft.tuners.lora.bnb
print("peft.tuners.lora.bnb import OK")
PYDEPS

    echo "[v37-monitor] preparing dataset" | tee -a train.log
    rm -rf dataset dataset_registry images
    mkdir -p dataset dataset_registry

    echo "[v37-monitor] archive size" | tee -a train.log
    ls -lh dataset.tar.gz | tee -a train.log

    echo "[v37-monitor] extracting dataset" | tee -a train.log
    tar -xzf dataset.tar.gz -C dataset --strip-components=1

    ln -sfn dataset/images images

    echo "[v37-monitor] dataset tree sample" | tee -a train.log
    (find dataset -maxdepth 3 -type f | sort | head -120 | tee -a train.log) || true

    echo "[v37-monitor] dataset counts" | tee -a train.log
    python - <<'PYCOUNT' 2>&1 | tee -a train.log
from pathlib import Path
root = Path("dataset")
files = {
  "episodes": root / "episodes.jsonl",
  "screen": root / "sft" / "screen_perception.jsonl",
  "policy": root / "sft" / "action_policy.jsonl",
  "verify": root / "sft" / "outcome_verifier.jsonl",
}
def lines(p):
    return sum(1 for x in p.open("r", encoding="utf-8", errors="ignore") if x.strip()) if p.is_file() else 0
counts = {k: lines(v) for k, v in files.items()}
counts["images"] = sum(1 for p in (root / "images").rglob("*") if p.is_file()) if (root / "images").exists() else 0
print(counts)
if counts["screen"] <= 0 or counts["images"] <= 0:
    raise SystemExit("Dataset is not trainable: screen rows and images must be nonzero")
if counts["policy"] <= 0:
    print("WARNING: policy rows are zero")
if counts["verify"] <= 0:
    print("WARNING: verifier rows are zero")
PYCOUNT

    cat > dataset_registry/dataset_info.json <<'JSON'
    {
      "abot_screen_perception": {
        "file_name": "../dataset/sft/screen_perception.jsonl",
        "formatting": "sharegpt",
        "columns": {"messages": "messages", "images": "image"},
        "tags": {"role_tag": "role", "content_tag": "content", "user_tag": "user", "assistant_tag": "assistant"}
      },
      "abot_action_policy": {
        "file_name": "../dataset/sft/action_policy.jsonl",
        "formatting": "sharegpt",
        "columns": {"messages": "messages", "images": "image"},
        "tags": {"role_tag": "role", "content_tag": "content", "user_tag": "user", "assistant_tag": "assistant"}
      },
      "abot_outcome_verifier": {
        "file_name": "../dataset/sft/outcome_verifier.jsonl",
        "formatting": "sharegpt",
        "columns": {"messages": "messages", "images": "images"},
        "tags": {"role_tag": "role", "content_tag": "content", "user_tag": "user", "assistant_tag": "assistant"}
      }
    }
    JSON

    cp train_config.yaml effective_train_config.yaml

    echo "[v37-monitor] effective training config" | tee -a train.log
    cat effective_train_config.yaml | tee -a train.log

    echo "[v37-monitor] starting llamafactory-cli train" | tee -a train.log
    CUDA_VISIBLE_DEVICES=0,1 stdbuf -oL -eL llamafactory-cli train effective_train_config.yaml 2>&1 | tee -a train.log

    echo "[v37-monitor] training finished" | tee -a train.log
