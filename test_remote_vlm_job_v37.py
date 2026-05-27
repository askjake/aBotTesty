#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from vlm_remote_trainer import VLMRemoteJob, prepare_job_files, submit_job


def test_prepare_remote_job_dry_run():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        ds = root / "learning_datasets" / "unit"
        (ds / "sft").mkdir(parents=True)
        (ds / "images").mkdir(parents=True)
        (ds / "manifest.json").write_text(json.dumps({"schema": "abot_learning_dataset_v37_phase1"}), encoding="utf-8")
        (ds / "episodes.jsonl").write_text("{}\n", encoding="utf-8")
        (ds / "sft" / "screen_perception.jsonl").write_text("{}\n", encoding="utf-8")
        job = VLMRemoteJob(dataset_dir=str(ds), run_name="unit", dry_run=True)
        out = root / "job"
        plan = prepare_job_files(job, out_dir=out, hardware="2x3090")
        assert Path(plan["archive"]).is_file()
        assert (out / "train_remote.sh").is_file()
        assert (out / "train_config.yaml").is_file()
        result = submit_job(job, prepared_dir=out)
        assert result["ok"] is True
        assert result["dry_run"] is True
        assert "ssh" in result["results"][0]["cmd"]


if __name__ == "__main__":
    test_prepare_remote_job_dry_run()
    print("REMOTE_VLM_JOB_V37_OK")
