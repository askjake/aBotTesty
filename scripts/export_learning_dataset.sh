#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="${1:-.}"
RUN_ID="${2:-}"
cd "$ROOT"
python3 learning_dataset_writer.py --root . ${RUN_ID:+--run-id "$RUN_ID"}
