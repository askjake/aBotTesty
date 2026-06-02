#!/usr/bin/env bash
set -Eeuo pipefail

# aBotTesty v37.2 remote VLM setup
# Fixes:
# - LLaMA-Factory requires Python >= 3.11.
# - Non-interactive SSH sessions often do not expose `conda` even when the login
#   shell prompt shows `(base)` locally.
# - Existing .venv / conda envs may have been created with Python 3.10 and must
#   be rejected/recreated instead of blindly activated.

echo "=== aBotTesty v37.2 remote VLM setup: 2x3090 profile ==="
echo "host=$(hostname || true) user=${USER:-unknown} pwd=${PWD}"

command -v nvidia-smi >/dev/null || { echo "ERROR: nvidia-smi not found. Install NVIDIA driver first." >&2; exit 2; }
nvidia-smi

ROOT="${ABOT_VLM_ROOT:-$HOME/aBotTesty_vlm_jobs}"
VENV="$ROOT/.venv"
CONDA_ENV="${ABOT_VLM_CONDA_ENV:-abot-vlm-py311}"
PYTHON_BIN=""
mkdir -p "$ROOT" "$HOME/models" "$HOME/.cache/huggingface"
cd "$ROOT"

need_py311() {
  "$1" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
}

show_py() {
  "$1" - <<'PY'
import sys
print(sys.version.split()[0])
PY
}

activate_conda_if_available() {
  if command -v conda >/dev/null 2>&1; then
    CONDA_BASE="$(conda info --base 2>/dev/null || true)"
    if [ -n "${CONDA_BASE:-}" ] && [ -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
      # shellcheck source=/dev/null
      source "$CONDA_BASE/etc/profile.d/conda.sh"
      return 0
    fi
  fi

  for candidate in \
    "$HOME/miniconda3" \
    "$HOME/anaconda3" \
    "$HOME/mambaforge" \
    "$HOME/miniforge3" \
    "/opt/conda" \
    "/usr/local/conda" \
    "/usr/local/miniconda3" \
    "/usr/local/anaconda3"; do
    if [ -f "$candidate/etc/profile.d/conda.sh" ]; then
      # shellcheck source=/dev/null
      source "$candidate/etc/profile.d/conda.sh"
      return 0
    fi
  done
  return 1
}

create_or_reuse_conda_env() {
  activate_conda_if_available || return 1
  if conda env list | awk '{print $1}' | grep -qx "$CONDA_ENV"; then
    if conda run -n "$CONDA_ENV" python - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
    then
      echo "Using existing conda env $CONDA_ENV with Python $(conda run -n "$CONDA_ENV" python -c 'import sys; print(sys.version.split()[0])')"
    else
      echo "Existing conda env $CONDA_ENV is not Python >=3.11; recreating it."
      conda env remove -y -n "$CONDA_ENV"
      conda create -y -n "$CONDA_ENV" python=3.11
    fi
  else
    conda create -y -n "$CONDA_ENV" python=3.11
  fi
  conda activate "$CONDA_ENV"
  PYTHON_BIN="python"
  return 0
}

# 1) Reuse a valid venv only if it is already Python >=3.11.
if [ -x "$VENV/bin/python" ]; then
  if need_py311 "$VENV/bin/python"; then
    echo "Using existing venv $VENV with Python $(show_py "$VENV/bin/python")"
    # shellcheck source=/dev/null
    source "$VENV/bin/activate"
    PYTHON_BIN="python"
  else
    echo "Existing venv $VENV is Python $(show_py "$VENV/bin/python") and cannot install LLaMA-Factory; removing it."
    rm -rf "$VENV"
  fi
fi

# 2) Prefer system python3.11 when available.
if [ -z "$PYTHON_BIN" ] && command -v python3.11 >/dev/null 2>&1 && need_py311 python3.11; then
  python3.11 -m venv "$VENV"
  # shellcheck source=/dev/null
  source "$VENV/bin/activate"
  PYTHON_BIN="python"
fi

# 3) Accept python3 only if it is actually >=3.11.
if [ -z "$PYTHON_BIN" ] && command -v python3 >/dev/null 2>&1 && need_py311 python3; then
  python3 -m venv "$VENV"
  # shellcheck source=/dev/null
  source "$VENV/bin/activate"
  PYTHON_BIN="python"
fi

# 4) Use conda/miniconda/anaconda from non-interactive SSH if system Python is old.
if [ -z "$PYTHON_BIN" ]; then
  if ! create_or_reuse_conda_env; then
    echo "ERROR: LLaMA-Factory requires Python >=3.11." >&2
    echo "Current python3: $(python3 --version 2>&1 || true)" >&2
    echo "No usable python3.11 or conda installation was found in this non-interactive SSH session." >&2
    echo "Fix options:" >&2
    echo "  sudo apt-get update && sudo apt-get install -y python3.11 python3.11-venv" >&2
    echo "  OR install Miniconda/Miniforge, then rerun this script." >&2
    exit 11
  fi
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

