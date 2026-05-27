# v37.3 Remote Training API + Heredoc Fixes

Fixes observed field issues:

- `/api/learning/remote/submit` now accepts either `execute: true` or `dry_run: false` semantics after reapplying the patcher and restarting the app.
- The generated `train_remote.sh` no longer uses an indented shell heredoc for `dataset_info.json`, which caused `wanted JSON` warnings and could skip the training launch.
- The remote train script now emits a dataset quick check before launching `llamafactory-cli train`.

Apply:

```bash
unzip -o v37_3_remote_training_api_and_heredoc_fix_patch.zip
python3 tools/apply_v37_phase1_patch.py
python3 -m py_compile vlm_remote_trainer.py learning_dataset_writer.py merged_app.py
python3 test_remote_vlm_job_v37.py
python3 test_learning_dataset_v37.py
```

Restart the Flask app after patching `merged_app.py`.
