#!/usr/bin/env bash
    set -Eeuo pipefail
    echo "[v37.3] remote train job: abot_vlm_20260527_123001" | tee train.log
    echo "[v37.3] model: Qwen/Qwen3-VL-8B-Instruct" | tee -a train.log
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

    python -m pip install --upgrade pip wheel setuptools
    python -m pip install --upgrade torch torchvision --index-url https://download.pytorch.org/whl/cu121
    python -m pip install --upgrade git+https://github.com/huggingface/transformers accelerate datasets peft bitsandbytes pillow qwen-vl-utils tensorboard
    python -m pip install --upgrade git+https://github.com/hiyouga/LLaMA-Factory.git

    rm -rf dataset dataset_registry
    mkdir -p dataset dataset_registry
    tar -xzf dataset.tar.gz -C dataset --strip-components=1

    python - <<'PY'
import json
from pathlib import Path
info = {
    "abot_screen_perception": {
        "file_name": "../dataset/sft/screen_perception.jsonl",
        "formatting": "sharegpt",
        "columns": {"messages": "messages", "images": "image"},
        "tags": {"role_tag": "role", "content_tag": "content", "user_tag": "user", "assistant_tag": "assistant"},
    },
    "abot_action_policy": {
        "file_name": "../dataset/sft/action_policy.jsonl",
        "formatting": "sharegpt",
        "columns": {"messages": "messages", "images": "image"},
        "tags": {"role_tag": "role", "content_tag": "content", "user_tag": "user", "assistant_tag": "assistant"},
    },
    "abot_outcome_verifier": {
        "file_name": "../dataset/sft/outcome_verifier.jsonl",
        "formatting": "sharegpt",
        "columns": {"messages": "messages", "images": "images"},
        "tags": {"role_tag": "role", "content_tag": "content", "user_tag": "user", "assistant_tag": "assistant"},
    },
}
Path("dataset_registry/dataset_info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
print("dataset_info_ok", Path("dataset_registry/dataset_info.json").resolve())
PY

    echo "[v37.3] dataset quick check" | tee -a train.log
    python - <<'PY' 2>&1 | tee -a train.log
from pathlib import Path
for rel in ["sft/screen_perception.jsonl", "sft/action_policy.jsonl", "sft/outcome_verifier.jsonl"]:
    p = Path("dataset") / rel
    n = sum(1 for _ in p.open("r", encoding="utf-8")) if p.exists() else 0
    print(rel, n)
PY

    cp train_config.yaml effective_train_config.yaml
    echo "[v37.3] starting llamafactory-cli train" | tee -a train.log
    CUDA_VISIBLE_DEVICES=0,1 llamafactory-cli train effective_train_config.yaml 2>&1 | tee -a train.log
    echo "[v37.3] training finished" | tee -a train.log
