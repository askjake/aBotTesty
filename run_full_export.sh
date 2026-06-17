#!/bin/bash
# Full dataset export — run this once after app restart to build a complete latest dataset.
# Usage: bash run_full_export.sh
set -e
cd /home/montjac/aBotTesty
source .venv/bin/activate
echo "Starting full export at $(date)"
python3 - << 'PY'
import sys, json
from datetime import datetime
from pathlib import Path
sys.path.insert(0, "/home/montjac/aBotTesty")
import learning_dataset_writer as ldw

writer = ldw.LearningDatasetWriter(
    root_dir="/home/montjac/aBotTesty",
    crawler_dir="/home/montjac/aBotTesty/crawler_data",
    out_dir="/home/montjac/aBotTesty/learning_datasets",
)
run_id = "full_" + datetime.now().strftime("%Y%m%d_%H%M%S")
result = writer.export(run_id=run_id, max_records=0)
print(json.dumps({k: v for k, v in result.items() if k != "artifacts"}, indent=2))
if result.get("trainable"):
    import subprocess
    subprocess.run(["ln", "-sfn", result["dataset_dir"], "/home/montjac/aBotTesty/learning_datasets/latest"])
    print(f"latest -> {result['dataset_dir']}")
else:
    print("WARNING: export not trainable, latest not updated")
PY
echo "Done at $(date)"
