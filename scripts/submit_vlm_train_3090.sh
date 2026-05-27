#!/usr/bin/env bash
set -Eeuo pipefail
DATASET_DIR="${1:-learning_datasets/latest}"
MODEL="${2:-Qwen/Qwen3-VL-8B-Instruct}"
EXECUTE="${3:-}"

ARGS=(submit
  --dataset-dir "$DATASET_DIR"
  --host 10.79.85.35
  --user montjac
  --remote-root /home/montjac/aBotTesty_vlm_jobs
  --model "$MODEL"
  --hardware 2x3090)

if [ "$EXECUTE" = "--execute" ] || [ "$EXECUTE" = "execute" ]; then
  ARGS+=(--execute)
fi

python3 vlm_remote_trainer.py "${ARGS[@]}"

echo
if [ "$EXECUTE" = "" ]; then
  echo "Dry-run above. Rerun with: scripts/submit_vlm_train_3090.sh $DATASET_DIR $MODEL --execute"
fi
