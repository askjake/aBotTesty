#!/usr/bin/env bash
# scripts/train_vlm_if_ready.sh
# ──────────────────────────────────────────────────────────────────────────
# Friday afternoon VLM auto-trainer.
# Called by cron: 0 14 * * 5  (every Friday at 14:00 local time)
#
# What it does:
#   1. Exports the latest learning dataset from crawler_data
#   2. Checks it meets quality thresholds (MIN_SCREEN / MIN_POLICY / etc.)
#   3. If ready: packages & submits async remote training over SSH
#   4. Appends a timestamped JSON summary to logs/vlm_auto_train.log
#
# All heavy work is done by vlm_auto_train.py — this script just:
#   - sets up the environment
#   - translates exit code 1 (dataset not ready) into a quiet log message
#   - prevents two runs from stepping on each other via a lock file
#
# Env-var overrides (set in crontab or calling shell):
#   MIN_SCREEN    default 250
#   MIN_POLICY    default 250
#   MIN_VERIFY    default 250
#   MIN_IMAGES    default 100
#   VLM_HARDWARE  default 2x3090
#   VLM_HOST      default 10.79.85.35
#   VLM_USER      default montjac
#   VLM_EXECUTE   set to "1" to actually run SSH (default: dry-run)
# ──────────────────────────────────────────────────────────────────────────
set -Euo pipefail

# ── Resolve project root ──────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

# ── Logging ───────────────────────────────────────────────────────────────
mkdir -p "$ROOT/logs"
LOG="$ROOT/logs/vlm_auto_train.log"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
echo "[$TS] train_vlm_if_ready.sh START" | tee -a "$LOG"

# ── Lock file — prevent concurrent runs ──────────────────────────────────
LOCK="$ROOT/.vlm_auto_train.lock"
if [ -e "$LOCK" ]; then
    AGE=$(( $(date +%s) - $(stat -c %Y "$LOCK" 2>/dev/null || echo 0) ))
    if [ "$AGE" -lt 7200 ]; then   # 2h max run time
        echo "[$TS] SKIP: lock file exists (age=${AGE}s), previous run still active?" | tee -a "$LOG"
        exit 0
    else
        echo "[$TS] Stale lock (age=${AGE}s), removing." | tee -a "$LOG"
        rm -f "$LOCK"
    fi
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"; echo "[$(date -u +%Y%m%dT%H%M%SZ)] train_vlm_if_ready.sh END (exit $?)" | tee -a '"$LOG" EXIT

# ── Python interpreter — prefer conda env, fall back to python3 ──────────
PYTHON="${PYTHON_BIN:-}"
if [ -z "$PYTHON" ]; then
    # Try the aBotTesty venv if it exists
    if [ -x "$ROOT/.venv/bin/python3" ]; then
        PYTHON="$ROOT/.venv/bin/python3"
    elif [ -x "/opt/miniconda3/bin/python3" ]; then
        PYTHON="/opt/miniconda3/bin/python3"
    else
        PYTHON="$(command -v python3)"
    fi
fi
echo "[$TS] Using Python: $PYTHON ($($PYTHON --version 2>&1))" | tee -a "$LOG"

# ── Build argument list ───────────────────────────────────────────────────
ARGS=(
    "$ROOT/vlm_auto_train.py"
    --root "$ROOT"
    --log-file "$LOG"
    ${MIN_SCREEN:+--min-screen "$MIN_SCREEN"}
    ${MIN_POLICY:+--min-policy "$MIN_POLICY"}
    ${MIN_VERIFY:+--min-verify "$MIN_VERIFY"}
    ${MIN_IMAGES:+--min-images "$MIN_IMAGES"}
    ${VLM_HARDWARE:+--hardware "$VLM_HARDWARE"}
    ${VLM_HOST:+--host "$VLM_HOST"}
    ${VLM_USER:+--user "$VLM_USER"}
)

if [ "${VLM_EXECUTE:-0}" = "1" ]; then
    ARGS+=(--execute)
    echo "[$TS] EXECUTE mode — SSH/rsync/training will run for real" | tee -a "$LOG"
else
    echo "[$TS] DRY-RUN mode — set VLM_EXECUTE=1 in crontab to enable" | tee -a "$LOG"
fi

# ── Run the pipeline ──────────────────────────────────────────────────────
set +e
"$PYTHON" "${ARGS[@]}" 2>&1 | tee -a "$LOG"
EXIT_CODE=${PIPESTATUS[0]}
set -e

# ── Interpret exit codes ──────────────────────────────────────────────────
case "$EXIT_CODE" in
    0) echo "[$TS] SUCCESS: training job submitted." | tee -a "$LOG" ;;
    1) echo "[$TS] SKIP: dataset below quality threshold (not an error)." | tee -a "$LOG" ;;
    *) echo "[$TS] FAILURE: pipeline exited with code $EXIT_CODE" | tee -a "$LOG"
       exit "$EXIT_CODE" ;;
esac

exit 0
