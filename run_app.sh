#!/usr/bin/env zsh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing project interpreter: $PYTHON_BIN"
  echo "Create it with: python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt"
  exit 1
fi

exec "$PYTHON_BIN" "$PROJECT_DIR/main.py"
