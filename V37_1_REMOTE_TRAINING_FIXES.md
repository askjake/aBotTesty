# v37.1 Remote Training Fixes

Fixes the first real setup issues from the VLM remote-trainer scaffold.

## Fixed

1. **LLaMA-Factory Python version failure**

   LLaMA-Factory requires Python >=3.11. The setup and remote training scripts now:

   - prefer `python3.11` when available,
   - accept an existing Python >=3.11 venv,
   - fall back to a conda env named `abot-vlm-py311`,
   - fail early with a clear message if only Python 3.10 is available.

2. **Remote rsync directory mismatch**

   The original dry-run used `~/aBotTesty_vlm_jobs/...`. During SSH mkdir that path was quoted, so `~` did not expand. During rsync, `~` did expand. Result: mkdir succeeded in the wrong place and rsync failed.

   v37.1 resolves `~/...` to `/home/<user>/...` before generating SSH/rsync commands.

3. **Friendlier dataset-missing error**

   If `learning_datasets/first_vlm_dataset` does not exist, the trainer now tells you exactly how to export it.

4. **New doctor command**

   ```bash
   python3 vlm_remote_trainer.py doctor --dataset-dir learning_datasets/latest --host 10.79.85.35 --user montjac --execute
   ```

## Recommended command sequence

```bash
python3 learning_dataset_writer.py --root . --run-id first_vlm_dataset

ssh montjac@10.79.85.35 'bash -s' < scripts/setup_vlm_remote_3090.sh

python3 vlm_remote_trainer.py doctor \
  --dataset-dir learning_datasets/first_vlm_dataset \
  --host 10.79.85.35 \
  --user montjac \
  --execute

python3 vlm_remote_trainer.py submit \
  --dataset-dir learning_datasets/first_vlm_dataset \
  --host 10.79.85.35 \
  --user montjac \
  --remote-root /home/montjac/aBotTesty_vlm_jobs \
  --model Qwen/Qwen3-VL-8B-Instruct \
  --hardware 2x3090

python3 vlm_remote_trainer.py submit \
  --dataset-dir learning_datasets/first_vlm_dataset \
  --host 10.79.85.35 \
  --user montjac \
  --remote-root /home/montjac/aBotTesty_vlm_jobs \
  --model Qwen/Qwen3-VL-8B-Instruct \
  --hardware 2x3090 \
  --execute
```
