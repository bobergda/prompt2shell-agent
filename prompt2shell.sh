#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQ_FILE="$SCRIPT_DIR/requirements.txt"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_DEPS=0
CREATED_VENV=0
NEED_DEPS=0
RUN_TESTS=0
UPDATE_REQUIREMENTS=0
SHOW_HELP=0
FORWARDED_ARGS=()

for arg in "$@"; do
  case "$arg" in
    install|--install)
      INSTALL_DEPS=1
      ;;
    tests|--tests)
      RUN_TESTS=1
      ;;
    update-requirements|--update-requirements)
      UPDATE_REQUIREMENTS=1
      ;;
    -h|--help|help)
      SHOW_HELP=1
      ;;
    *)
      FORWARDED_ARGS+=("$arg")
      ;;
  esac
done

if [ "$SHOW_HELP" -eq 1 ]; then
  cat <<'EOF'
Usage: ./prompt2shell.sh [options] [-- app_args...]

Options:
  --install               Create venv (if needed) and install deps from requirements.txt
  --tests                 Run unit tests (python -m unittest discover -s tests -v)
  --update-requirements   Upgrade required packages in .venv and rewrite requirements.txt
  --help                  Show this help message
EOF
  exit 0
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "[prompt2shell] Creating virtualenv in $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  CREATED_VENV=1
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

if ! python - <<'PY'
import importlib.util

required_modules = ("openai", "termcolor", "distro", "prompt_toolkit")
missing = [name for name in required_modules if importlib.util.find_spec(name) is None]
if missing:
    print("[prompt2shell] Missing Python modules: " + ", ".join(missing))
    raise SystemExit(1)
PY
then
  NEED_DEPS=1
fi

if [ "$INSTALL_DEPS" -eq 1 ] || [ "$CREATED_VENV" -eq 1 ] || [ "$NEED_DEPS" -eq 1 ]; then
  if [ -f "$REQ_FILE" ]; then
    echo "[prompt2shell] Installing dependencies from requirements.txt"
    python -m pip install -r "$REQ_FILE"
  else
    echo "[prompt2shell] Missing $REQ_FILE - cannot install dependencies" >&2
    exit 1
  fi
fi

if [ "$UPDATE_REQUIREMENTS" -eq 1 ]; then
  echo "[prompt2shell] Upgrading core packages in virtualenv"
  python -m pip install --upgrade openai termcolor distro prompt_toolkit
  echo "[prompt2shell] Writing pinned versions to requirements.txt"
  P2S_REQ_FILE="$REQ_FILE" python - <<'PY'
import os
from importlib.metadata import version

packages = ("openai", "termcolor", "distro", "prompt_toolkit")
req_file = os.environ["P2S_REQ_FILE"]
lines = [f"{name}=={version(name)}" for name in packages]
with open(req_file, "w", encoding="utf-8") as handle:
    handle.write("\n".join(lines) + "\n")
print("[prompt2shell] Updated:", ", ".join(lines))
PY
fi

if [ "$RUN_TESTS" -eq 1 ]; then
  echo "[prompt2shell] Running tests"
  python -m unittest discover -s "$SCRIPT_DIR/tests" -v
fi

if [ "$RUN_TESTS" -eq 1 ] || [ "$UPDATE_REQUIREMENTS" -eq 1 ]; then
  if [ "${#FORWARDED_ARGS[@]}" -eq 0 ]; then
    exit 0
  fi
fi

exec python "$SCRIPT_DIR/prompt2shell.py" "${FORWARDED_ARGS[@]}"
