#!/usr/bin/env bash
set -Eeuo pipefail

cd /home/montjac/aBotTesty
source .venv/bin/activate

LOCK=/tmp/abot_vlm_train.lock
exec 9>"$LOCK"
if ! flock -n 9; then
  echo "another VLM train job is already running"
  exit 0
fi

MIN_SCREEN=${MIN_SCREEN:-250}
MIN_POLICY=${MIN_POLICY:-250}
MIN_VERIFY=${MIN_VERIFY:-250}
MIN_IMAGES=${MIN_IMAGES:-100}

RUN_ID="vlm_$(date +%Y%m%d_%H%M%S)"
DATASET_DIR="learning_datasets/$RUN_ID"

echo "=== exporting dataset $RUN_ID ==="
python3 learning_dataset_writer.py --root . --run-id "$RUN_ID"

SCREEN=$(wc -l < "$DATASET_DIR/sft/screen_perception.jsonl" || echo 0)
POLICY=$(wc -l < "$DATASET_DIR/sft/action_policy.jsonl" || echo 0)
VERIFY=$(wc -l < "$DATASET_DIR/sft/outcome_verifier.jsonl" || echo 0)
IMAGES=$(find "$DATASET_DIR/images" -type f 2>/dev/null | wc -l || echo 0)

echo "screen=$SCREEN policy=$POLICY verify=$VERIFY images=$IMAGES"

rm -rf learning_datasets/latest
ln -s "$(pwd)/$DATASET_DIR" learning_datasets/latest

if [ "$SCREEN" -lt "$MIN_SCREEN" ] || [ "$POLICY" -lt "$MIN_POLICY" ] || [ "$VERIFY" -lt "$MIN_VERIFY" ] || [ "$IMAGES" -lt "$MIN_IMAGES" ]; then
  echo "not enough VLM data yet; skipping train"
  exit 0
fi

OUT="logs/vlm_train_${RUN_ID}.json"

python3 vlm_remote_trainer.py submit \
  --dataset-dir "$DATASET_DIR" \
  --host 10.79.85.35 \
  --user montjac \
  --remote-root /home/montjac/aBotTesty_vlm_jobs \
  --model Qwen/Qwen3-VL-8B-Instruct \
  --hardware 2x3090 \
  --execute | tee "$OUT"

REMOTE_DIR=$(python3 - <<PY
import json
from pathlib import Path
data=json.loads(Path("$OUT").read_text())
print(data.get("remote_dir",""))
PY
)

if [ -z "$REMOTE_DIR" ]; then
  echo "could not determine remote_dir"
  exit 1
fi

ADAPTER_NAME=$(basename "$REMOTE_DIR")
mkdir -p "models/vlm_adapters/$ADAPTER_NAME"

rsync -az \
  "montjac@10.79.85.35:$REMOTE_DIR/outputs/$ADAPTER_NAME/" \
  "models/vlm_adapters/$ADAPTER_NAME/"

echo "$ADAPTER_NAME" > models/vlm_adapters/latest_adapter.txt
echo "adapter pulled: models/vlm_adapters/$ADAPTER_NAME"
