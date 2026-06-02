#!/usr/bin/env bash
set -Eeuo pipefail
echo "[v37] remote train job: abot_vlm_20260527_103513" | tee train.log
echo "[v37] model: Qwen/Qwen3-VL-8B-Instruct" | tee -a train.log
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
echo "[v37] starting llamafactory-cli train" | tee -a train.log
CUDA_VISIBLE_DEVICES=0,1 llamafactory-cli train effective_train_config.yaml 2>&1 | tee -a train.log
echo "[v37] training finished" | tee -a train.log
