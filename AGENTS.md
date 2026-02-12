# Repository Guidelines

## Project Structure & Module Organization
- `prompt2shell/`: main Python package. Key modules include `application.py` (CLI flow), `openai_helper.py` (Responses API calls), `command_helper.py` (command safety/runtime), and `interaction_logger.py` (JSONL logging/redaction).
- `tests/`: unit tests (`test_*.py`) covering command handling, runtime behavior, logging, and OpenAI helper behavior.
- Root entrypoints: `prompt2shell.sh` (recommended launcher) and `prompt2shell.py` (Python entry script).
- Supporting files: `requirements.txt` (pinned dependencies), `logs/` (runtime logs), `README.md` (usage and flags).

## Build, Test, and Development Commands
- `./prompt2shell.sh --install`: create `.venv` if needed and install dependencies.
- `./prompt2shell.sh`: run the interactive CLI locally.
- `./prompt2shell.sh --tests`: run the full unit suite (`unittest discover`).
- `./.venv/bin/python -m unittest discover -s tests -v`: run tests directly from the venv.
- `./prompt2shell.sh --update-requirements`: upgrade core packages and rewrite `requirements.txt` with pinned versions.

Set `OPENAI_API_KEY` before running the app.

## Coding Style & Naming Conventions
- Python style follows existing PEP 8-oriented conventions: 4-space indentation, clear small functions, and explicit imports.
- Use `snake_case` for modules/functions/variables and `PascalCase` for classes (for example, `OpenAIHelper`, `CommandHelper`).
- Keep shell changes consistent with `prompt2shell.sh` patterns (`set -euo pipefail`, defensive checks, readable flags).
- Prefer extending existing helpers instead of duplicating logic across modules.

## Testing Guidelines
- Framework: built-in `unittest` with `unittest.mock` for external API isolation.
- Naming: files `tests/test_*.py`, test methods `test_*`, and grouped `*Tests` classes.
- Add or update tests for any behavior change, especially command safety rules and process execution edge cases.
- No enforced coverage threshold is configured; maintain practical regression coverage for touched code.

## Commit & Pull Request Guidelines
- Follow the repository's commit style: conventional prefixes like `feat(scope): ...`, `fix(scope): ...`, `docs: ...`, `refactor: ...`, `chore: ...`.
- Keep commits focused and descriptive; one logical change per commit when possible.
- PRs should include: concise summary, user-visible impact, tests run (with command), and linked issue/context.
- For CLI behavior changes, include a short terminal snippet showing before/after behavior.
