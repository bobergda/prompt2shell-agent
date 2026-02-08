#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQ_FILE="$SCRIPT_DIR/requirements.txt"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_DEPS=0
CREATED_VENV=0
FORWARDED_ARGS=()

for arg in "$@"; do
  if [ "$arg" = "install" ] || [ "$arg" = "--install" ]; then
    INSTALL_DEPS=1
    continue
  fi
  FORWARDED_ARGS+=("$arg")
done

if [ ! -d "$VENV_DIR" ]; then
  echo "[prompt2shell-agent] Creating virtualenv in $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  CREATED_VENV=1
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

if [ "$INSTALL_DEPS" -eq 1 ] || [ "$CREATED_VENV" -eq 1 ]; then
  if [ -f "$REQ_FILE" ]; then
    echo "[prompt2shell-agent] Installing dependencies from requirements.txt"
    python -m pip install -r "$REQ_FILE"
  else
    echo "[prompt2shell-agent] Missing $REQ_FILE - skipping dependency installation" >&2
  fi
fi

exec python "$SCRIPT_DIR/prompt2shell-agent.py" "${FORWARDED_ARGS[@]}"
