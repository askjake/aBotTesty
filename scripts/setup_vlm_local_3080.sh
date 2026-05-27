#!/usr/bin/env bash
set -Eeuo pipefail

echo "=== aBotTesty v37 local VLM setup: 2x3080 fallback profile ==="
command -v nvidia-smi >/dev/null || { echo "ERROR: nvidia-smi not found. Install NVIDIA driver first." >&2; exit 2; }
nvidia-smi
python3 -m venv .venv-vlm
source .venv-vlm/bin/activate
python -m pip install --upgrade pip wheel setuptools
python -m pip install --upgrade torch torchvision --index-url https://download.pytorch.org/whl/cu121
python -m pip install --upgrade git+https://github.com/huggingface/transformers accelerate datasets peft bitsandbytes pillow qwen-vl-utils tensorboard
python -m pip install --upgrade git+https://github.com/hiyouga/LLaMA-Factory.git
python - <<'PY'
import torch
print('torch', torch.__version__)
print('cuda available', torch.cuda.is_available())
print('gpu count', torch.cuda.device_count())
for i in range(torch.cuda.device_count()):
    print(i, torch.cuda.get_device_name(i), round(torch.cuda.get_device_properties(i).total_memory/1024**3, 1), 'GB')
PY
