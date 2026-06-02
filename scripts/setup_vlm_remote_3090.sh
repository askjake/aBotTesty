#!/usr/bin/env bash
set -Eeuo pipefail

echo "=== aBotTesty v37.1 remote VLM setup: 2x3090 profile ==="
echo "host=$(hostname || true) user=${USER} pwd=${PWD}"

command -v nvidia-smi >/dev/null || { echo "ERROR: nvidia-smi not found. Install NVIDIA driver first." >&2; exit 2; }
nvidia-smi

ROOT="$HOME/aBotTesty_vlm_jobs"
VENV="$ROOT/.venv"
mkdir -p "$ROOT" "$HOME/models" "$HOME/.cache/huggingface"
cd "$ROOT"

need_py311() {
  "$1" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
}

if [ -x "$VENV/bin/python" ] && need_py311 "$VENV/bin/python"; then
  source "$VENV/bin/activate"
elif command -v python3.11 >/dev/null 2>&1 && need_py311 python3.11; then
  python3.11 -m venv "$VENV"
  source "$VENV/bin/activate"
elif command -v python3 >/dev/null 2>&1 && need_py311 python3; then
  python3 -m venv "$VENV"
  source "$VENV/bin/activate"
elif command -v conda >/dev/null 2>&1; then
  CONDA_BASE="$(conda info --base)"
  # shellcheck source=/dev/null
  source "$CONDA_BASE/etc/profile.d/conda.sh"
  if ! conda env list | awk '{print $1}' | grep -qx 'abot-vlm-py311'; then
    conda create -y -n abot-vlm-py311 python=3.11
  fi
  conda activate abot-vlm-py311
else
  echo "ERROR: LLaMA-Factory requires Python >=3.11, but python3 is:" >&2
  python3 --version >&2 || true
  echo "Install python3.11/python3.11-venv or conda, then rerun this setup script." >&2
  exit 11
fi

python --version
python - <<'PY'
import sys
assert sys.version_info >= (3, 11), sys.version
print('python_ok', sys.version.split()[0])
PY

python -m pip install --upgrade pip wheel setuptools
python -m pip install --upgrade torch torchvision --index-url https://download.pytorch.org/whl/cu121
python -m pip install --upgrade \
  git+https://github.com/huggingface/transformers \
  accelerate datasets peft bitsandbytes pillow qwen-vl-utils tensorboard \
  deepspeed ninja packaging scipy scikit-learn
python -m pip install --upgrade git+https://github.com/hiyouga/LLaMA-Factory.git

python - <<'PY'
import torch, sys
print('python', sys.version.split()[0])
print('torch', torch.__version__)
print('cuda available', torch.cuda.is_available())
print('gpu count', torch.cuda.device_count())
for i in range(torch.cuda.device_count()):
    print(i, torch.cuda.get_device_name(i), round(torch.cuda.get_device_properties(i).total_memory/1024**3, 1), 'GB')
PY

echo "OK: remote VLM environment ready in $ROOT"
