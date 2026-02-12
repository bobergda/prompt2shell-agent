#!/usr/bin/env bash
set -euo pipefail
# This script manages the virtual environment, dependencies, and execution of prompt2shell.py.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQ_FILE="$SCRIPT_DIR/requirements.txt"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ENV_FILE="$SCRIPT_DIR/.env"

# Load optional local environment overrides from .env.
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

# Default values for environment variables
export PROMPT2SHELL_LOG_ENABLED=1
MODEL_VALUE="${OPENAI_MODEL:-gpt-4o-mini}"
TOKENS_VALUE="${PROMPT2SHELL_MAX_OUTPUT_TOKENS:-1200}"

# Flags to control script behavior
INSTALL_DEPS=0
CREATED_VENV=0
NEED_DEPS=0
RUN_TESTS=0
UPDATE_REQUIREMENTS=0
SHOW_HELP=0
ADD_ALIAS=0
ONCE_MODE=0
END_OF_OPTIONS=0
FORWARDED_ARGS=()

for arg in "$@"; do
  if [ "$END_OF_OPTIONS" -eq 1 ]; then
    FORWARDED_ARGS+=("$arg")
    continue
  fi

  case "$arg" in
    --)
      END_OF_OPTIONS=1
      ;;
    --install)
      INSTALL_DEPS=1
      ;;
    --tests)
      RUN_TESTS=1
      ;;
    --update-requirements)
      UPDATE_REQUIREMENTS=1
      ;;
    --add-alias)
      ADD_ALIAS=1
      ;;
    -o|--once)
      ONCE_MODE=1
      ;;
    -m5)
      MODEL_VALUE="gpt-5-mini"
      ;;
    --model=*)
      MODEL_VALUE="${arg#*=}"
      ;;
    --tokens=*)
      TOKENS_VALUE="${arg#*=}"
      ;;
    -h|--help)
      SHOW_HELP=1
      ;;
    -*)
      echo "[prompt2shell] Unknown option: $arg" >&2
      echo "[prompt2shell] Use --help to list options. For prompts starting with '-', use: ./prompt2shell.sh -- <prompt>" >&2
      exit 1
      ;;
    *)
      FORWARDED_ARGS+=("$arg")
      END_OF_OPTIONS=1
      ;;
  esac
done

add_p2s_alias() {
  local bashrc_file="${HOME}/.bashrc"
  local alias_name="p2s"
  local alias_target="$SCRIPT_DIR/prompt2shell.sh"
  local alias_value
  local alias_line

  alias_value="$(printf '%q' "$alias_target")"
  alias_line="alias ${alias_name}=${alias_value}"

  if [ ! -f "$bashrc_file" ]; then
    touch "$bashrc_file"
  fi

  if grep -Fqx "$alias_line" "$bashrc_file"; then
    echo "[prompt2shell] Alias ${alias_name} already configured in $bashrc_file"
    echo "[prompt2shell] Run 'source $bashrc_file' or restart your shell to use '${alias_name}'."
    return 0
  fi

  if grep -Eq "^[[:space:]]*alias[[:space:]]+${alias_name}=" "$bashrc_file"; then
    local tmp_file
    tmp_file="$(mktemp)"
    awk -v alias_name="$alias_name" -v alias_line="$alias_line" '
      BEGIN { replaced = 0 }
      $0 ~ "^[[:space:]]*alias[[:space:]]+" alias_name "=" {
        if (replaced == 0) {
          print alias_line
          replaced = 1
        }
        next
      }
      { print }
      END {
        if (replaced == 0) {
          print alias_line
        }
      }
    ' "$bashrc_file" > "$tmp_file"
    mv "$tmp_file" "$bashrc_file"
    echo "[prompt2shell] Updated alias ${alias_name} in $bashrc_file"
  else
    printf "\n%s\n" "$alias_line" >> "$bashrc_file"
    echo "[prompt2shell] Added alias ${alias_name} to $bashrc_file"
  fi

  echo "[prompt2shell] Run 'source $bashrc_file' or restart your shell to use '${alias_name}'."
}

if [ "$SHOW_HELP" -eq 1 ]; then
  cat <<'EOF'
Usage: ./prompt2shell.sh [options] [--] [prompt...]

Options:
  --install               Create venv (if needed) and install deps from requirements.txt
  --tests                 Run unit tests (python -m unittest discover -s tests -v)
  --update-requirements   Upgrade required packages in .venv and rewrite requirements.txt
  --add-alias             Add/update alias p2s in ~/.bashrc for this project launcher
  -o, --once              Exit after processing the initial CLI prompt
  -m5                     Shortcut for --model=gpt-5-mini
  --model=NAME            Set OPENAI_MODEL for this run (default: gpt-4o-mini)
  --tokens=NUMBER         Set PROMPT2SHELL_MAX_OUTPUT_TOKENS for this run (default: 1200)
  --help                  Show this help message

Prompt mode:
  ./prompt2shell.sh "find 3 largest files"
  ls | ./prompt2shell.sh
  ls | ./prompt2shell.sh "summarize this output"
  ./prompt2shell.sh -- "prompt that starts with -"
EOF
  exit 0
fi

if [ "$ADD_ALIAS" -eq 1 ]; then
  add_p2s_alias
fi

if [ "$ADD_ALIAS" -eq 1 ] && [ "$INSTALL_DEPS" -eq 0 ] && [ "$RUN_TESTS" -eq 0 ] && [ "$UPDATE_REQUIREMENTS" -eq 0 ] && [ "${#FORWARDED_ARGS[@]}" -eq 0 ]; then
  exit 0
fi

if ! [[ "$TOKENS_VALUE" =~ ^[0-9]+$ ]] || [ "$TOKENS_VALUE" -le 0 ]; then
  echo "[prompt2shell] Invalid --tokens value: $TOKENS_VALUE (expected positive integer)" >&2
  exit 1
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

OPENAI_MODEL="$MODEL_VALUE" \
PROMPT2SHELL_MAX_OUTPUT_TOKENS="$TOKENS_VALUE" \
PROMPT2SHELL_ONCE="$ONCE_MODE" \
exec python "$SCRIPT_DIR/prompt2shell.py" "${FORWARDED_ARGS[@]}"
