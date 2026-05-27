#!/usr/bin/env bash
set -Eeuo pipefail
DATASET_DIR="${1:-learning_datasets/latest}"
MODEL="${2:-Qwen/Qwen3-VL-8B-Instruct}"
python3 vlm_remote_trainer.py submit \
  --dataset-dir "$DATASET_DIR" \
  --host 10.79.85.35 \
  --user montjac \
  --remote-root '~/aBotTesty_vlm_jobs' \
  --model "$MODEL" \
  --hardware 2x3090

echo

echo "Dry-run above. Add --execute to the python command after verifying ssh/rsync commands."
