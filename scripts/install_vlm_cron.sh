#!/usr/bin/env bash
# scripts/install_vlm_cron.sh
# ──────────────────────────────────────────────────────────────────────────
# Installs (or updates) the Friday afternoon VLM auto-training cron job.
#
# Usage:
#   bash scripts/install_vlm_cron.sh [--execute]   # adds --execute flag to cron
#   bash scripts/install_vlm_cron.sh --remove       # removes the cron entry
#   bash scripts/install_vlm_cron.sh --show         # prints current crontab
#
# Default schedule: every Friday at 14:00 local time (0 14 * * 5)
# Override schedule: CRON_SCHEDULE="0 15 * * 5" bash scripts/install_vlm_cron.sh
# ──────────────────────────────────────────────────────────────────────────
set -Euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

CRON_SCHEDULE="${CRON_SCHEDULE:-0 14 * * 5}"
CRON_MARKER="# aBotTesty VLM auto-train"
EXECUTE_FLAG=""
REMOVE=0
SHOW=0

for arg in "$@"; do
    case "$arg" in
        --execute)  EXECUTE_FLAG="VLM_EXECUTE=1 " ;;
        --remove)   REMOVE=1 ;;
        --show)     SHOW=1 ;;
    esac
done

if [ "$SHOW" = "1" ]; then
    crontab -l 2>/dev/null || echo "(no crontab)"
    exit 0
fi

# Build the cron line
CRON_CMD="cd $ROOT && ${EXECUTE_FLAG}MIN_SCREEN=250 MIN_POLICY=250 MIN_VERIFY=250 MIN_IMAGES=100 bash scripts/train_vlm_if_ready.sh >> logs/vlm_auto_train.log 2>&1"
NEW_CRON_LINE="$CRON_SCHEDULE $CRON_CMD  $CRON_MARKER"

# Load current crontab (tolerates empty)
CURRENT_TAB="$(crontab -l 2>/dev/null || true)"

if [ "$REMOVE" = "1" ]; then
    echo "Removing VLM auto-train cron entry…"
    NEW_TAB="$(echo "$CURRENT_TAB" | grep -v "$CRON_MARKER" || true)"
    echo "$NEW_TAB" | crontab -
    echo "Done. Current crontab:"
    crontab -l 2>/dev/null || echo "(empty)"
    exit 0
fi

# Remove any old version of the line, then append fresh
NEW_TAB="$(echo "$CURRENT_TAB" | grep -v "$CRON_MARKER" || true)"
if [ -n "$NEW_TAB" ]; then
    NEW_TAB="${NEW_TAB}"$'\n'"${NEW_CRON_LINE}"
else
    NEW_TAB="${NEW_CRON_LINE}"
fi
echo "$NEW_TAB" | crontab -

echo "Cron job installed:"
echo "  $NEW_CRON_LINE"
echo ""
echo "Verify with: crontab -l"
echo ""
echo "To enable live SSH execution, rerun with: bash scripts/install_vlm_cron.sh --execute"
