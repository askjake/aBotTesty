# v37 Phase 1 — Learning Dataset + Remote VLM Training Scaffold

This patch starts the first safe phase of multimodal learning for aBotTesty.

It does **not** let a model control the STB. It exports the app's existing before/action/after learning records into a trainable vision-language dataset, then optionally packages that dataset for SSH/rsync submission to a remote GPU machine.

## Why the 2x3090 box is better

The local 2x3080 machine can train small/medium VLM LoRAs, but the 2x3090 box is the better trainer because each RTX 3090 has 24 GB of VRAM and 3090 supports NVLink/SLI-ready configurations. That still does not magically make every trainer see one simple 48 GB pool, but it gives far more practical room for Qwen3-VL-8B or Qwen2.5-VL-7B QLoRA than 10–12 GB 3080 cards.

## Files added

- `learning_dataset_writer.py` — exports episodes and SFT JSONL files.
- `vlm_remote_trainer.py` — packages/submits remote training jobs over SSH/rsync.
- `tools/apply_v37_phase1_patch.py` — idempotently adds Flask endpoints/UI hooks to `merged_app.py`.
- `scripts/setup_vlm_remote_3090.sh` — setup script for `montjac@10.79.85.35`.
- `scripts/setup_vlm_local_3080.sh` — fallback local setup script.
- `scripts/export_learning_dataset.sh` — CLI export helper.
- `scripts/submit_vlm_train_3090.sh` — dry-run remote submit helper.
- `configs/vlm/*.yaml` — initial LLaMA-Factory LoRA config templates.
- `test_learning_dataset_v37.py` and `test_remote_vlm_job_v37.py` — synthetic tests.

## Install patch into repo

From the repo root:

```bash
unzip -o v37_phase1_learning_remote_vlm_patch.zip
python3 tools/apply_v37_phase1_patch.py
python3 -m py_compile learning_dataset_writer.py vlm_remote_trainer.py merged_app.py
python3 test_learning_dataset_v37.py
python3 test_remote_vlm_job_v37.py
```

## Phase 1 runbook

### 1. Export dataset locally

```bash
python3 learning_dataset_writer.py --root . --stats
python3 learning_dataset_writer.py --root . --run-id first_vlm_dataset
```

Expected outputs:

```text
learning_datasets/first_vlm_dataset/manifest.json
learning_datasets/first_vlm_dataset/episodes.jsonl
learning_datasets/first_vlm_dataset/sft/screen_perception.jsonl
learning_datasets/first_vlm_dataset/sft/action_policy.jsonl
learning_datasets/first_vlm_dataset/sft/outcome_verifier.jsonl
learning_datasets/first_vlm_dataset/images/
```

### 2. Use the Flask UI/API

After applying the patch and restarting the app:

```text
http://127.0.0.1:8502/learning
```

API smoke tests:

```bash
curl http://127.0.0.1:8502/api/learning/stats
curl -X POST http://127.0.0.1:8502/api/learning/export \
  -H 'Content-Type: application/json' \
  -d '{"run_id":"api_smoke","max_records":25}'
```

### 3. Prepare SSH to the 2x3090 host

From the app/capture machine:

```bash
ssh-keygen -t ed25519 -C "abot-vlm-trainer" -f ~/.ssh/abot_vlm_ed25519
ssh-copy-id -i ~/.ssh/abot_vlm_ed25519.pub montjac@10.79.85.35
ssh -i ~/.ssh/abot_vlm_ed25519 montjac@10.79.85.35 'hostname && nvidia-smi'
```

If you prefer your default SSH key, skip `-i` and use:

```bash
ssh montjac@10.79.85.35 'hostname && nvidia-smi'
```

### 4. Set up the 2x3090 VLM environment

Copy and run setup:

```bash
scp scripts/setup_vlm_remote_3090.sh montjac@10.79.85.35:/tmp/setup_vlm_remote_3090.sh
ssh montjac@10.79.85.35 'bash /tmp/setup_vlm_remote_3090.sh'
```

### 5. Dry-run remote training job

```bash
python3 vlm_remote_trainer.py submit \
  --dataset-dir learning_datasets/first_vlm_dataset \
  --host 10.79.85.35 \
  --user montjac \
  --model Qwen/Qwen3-VL-8B-Instruct \
  --hardware 2x3090
```

This prints the exact SSH/rsync/train commands without executing them.

### 6. Execute only after dry-run looks right

```bash
python3 vlm_remote_trainer.py submit \
  --dataset-dir learning_datasets/first_vlm_dataset \
  --host 10.79.85.35 \
  --user montjac \
  --model Qwen/Qwen3-VL-8B-Instruct \
  --hardware 2x3090 \
  --execute
```

Tail logs:

```bash
ssh montjac@10.79.85.35 'tail -f ~/aBotTesty_vlm_jobs/<run_name>/train.log'
```

## Model choice

Recommended remote 2x3090 first pass:

```text
Qwen/Qwen3-VL-8B-Instruct
```

Fallback local 2x3080 first pass:

```text
Qwen/Qwen2.5-VL-7B-Instruct
```

Training begins with `screen_perception` only. Do not train action policy or outcome verifier into live control until perception JSON validity, guide recognition, and risky-screen recall are proven on a held-out set.

## Promotion gates

A model is not allowed to influence live actions until:

- JSON validity is > 95%.
- screen_type accuracy is > 90%.
- risky-screen recall is effectively 100%.
- guide-grid row/cell extraction agrees with deterministic parser on held-out samples.
- shadow-mode action ranking improves discovery/loop metrics without unsafe suggestions.

## Next phases

- v38: Add shadow-mode VLM inference endpoint that observes but does not press keys.
- v39: Add held-out evaluation harness and dashboard metrics.
- v40: Use VLM only to rank safe actions; deterministic guardrails still execute.
- v41: Verified guide/program selection with deterministic+VLM agreement.
