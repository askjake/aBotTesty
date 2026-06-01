#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

APP_FILE="$APP_DIR/merged_app.py"
LOG_DIR="$APP_DIR/logs"
mkdir -p "$LOG_DIR"

echo "=== aBotTesty merged app restart ==="
echo "app_dir=$APP_DIR"
echo "time=$(date)"

echo
echo "=== stopping old merged_app.py processes ==="

# Match old app processes without matching this grep/pkill command itself.
OLD_PIDS="$(
  pgrep -af "[p]ython.*merged_app.py" 2>/dev/null \
    | awk '{print $1}' \
    | sort -u \
    || true
)"

if [ -n "$OLD_PIDS" ]; then
  echo "$OLD_PIDS" | while read -r pid; do
    [ -z "$pid" ] && continue
    echo "stopping pid=$pid"
    kill "$pid" 2>/dev/null || true
  done

  sleep 3

  echo "$OLD_PIDS" | while read -r pid; do
    [ -z "$pid" ] && continue
    if kill -0 "$pid" 2>/dev/null; then
      echo "force killing pid=$pid"
      kill -9 "$pid" 2>/dev/null || true
    fi
  done
else
  echo "no old merged_app.py process found"
fi

echo
echo "=== checking app ports ==="
for port in 8503 8504 8505; do
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp 2>/dev/null | grep ":$port " || true
  fi
done

echo
echo "=== python environment ==="
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

export JAMBOREE_BASE="$APP_DIR/base.txt"

echo
echo "=== compile check ==="
python -m py_compile merged_app.py

echo
echo "=== starting merged_app.py ==="
echo "JAMBOREE_BASE=$JAMBOREE_BASE"

exec python merged_app.py
