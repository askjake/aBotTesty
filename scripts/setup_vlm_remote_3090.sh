#!/usr/bin/env bash
set -Eeuo pipefail

echo "=== aBotTesty v37 remote VLM setup: 2x3090 profile ==="
HOSTNAME=$(hostname || true)
echo "host=${HOSTNAME} user=${USER} pwd=${PWD}"

command -v nvidia-smi >/dev/null || { echo "ERROR: nvidia-smi not found. Install NVIDIA driver first." >&2; exit 2; }
nvidia-smi

python3 --version
mkdir -p ~/aBotTesty_vlm_jobs ~/models ~/.cache/huggingface
cd ~/aBotTesty_vlm_jobs

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools

# Ampere-friendly baseline. If your host already has a known-good CUDA/PyTorch
# stack, keep it and skip this install line.
python -m pip install --upgrade torch torchvision --index-url https://download.pytorch.org/whl/cu121
python -m pip install --upgrade \
  git+https://github.com/huggingface/transformers \
  accelerate datasets peft bitsandbytes pillow qwen-vl-utils tensorboard \
  deepspeed ninja packaging scipy scikit-learn
python -m pip install --upgrade git+https://github.com/hiyouga/LLaMA-Factory.git

python - <<'PY'
import torch
print('torch', torch.__version__)
print('cuda available', torch.cuda.is_available())
print('gpu count', torch.cuda.device_count())
for i in range(torch.cuda.device_count()):
    print(i, torch.cuda.get_device_name(i), round(torch.cuda.get_device_properties(i).total_memory/1024**3, 1), 'GB')
PY

echo "OK: remote VLM environment ready in ~/aBotTesty_vlm_jobs/.venv"
