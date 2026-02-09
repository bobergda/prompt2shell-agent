# Prompt2Shell Agent

`Prompt2Shell Agent` is a CLI assistant that turns natural-language requests into shell commands, runs them interactively, and explains the results.

This version uses the OpenAI **Responses API** with server-side conversation chaining via `previous_response_id`.

## Features

- Function calling for structured command suggestions (`get_commands`)
- Manual mode and guided execution mode
- Follow-up analysis of command output
- Safe mode with destructive-command detection
- Optional strict safe mode (read-only allowlist)
- Command timeout handling that terminates the full process group
- Opt-in JSONL logging with basic secret redaction and restrictive file permissions (`0600`)
- Modular code layout in `prompt2shell_agent/` for easier maintenance and testing

## Usage

1. One-time setup:
   ```shell
   ./prompt2shell-agent.sh --install
   export OPENAI_API_KEY="your-api-key"
   ```
2. Run:
   ```shell
   ./prompt2shell-agent.sh
   ```
3. Enter a task in plain language.
4. For each proposed command choose: run, edit, skip, run-all-remaining, or stop.
5. Runtime controls:
   - `safe on`, `safe off`, `safe`
   - `strict on`, `strict off`, `strict`
   - `tokens on`, `tokens off`, `tokens`
   - `e` to enter manual command mode, `q` to quit

Optional environment variables:

```shell
export OPENAI_MODEL="gpt-4o-mini"
export PROMPT2SHELL_LOG_ENABLED=1
export PROMPT2SHELL_LOG_FILE="./logs/custom.log"
export PROMPT2SHELL_SAFE_MODE=1
export PROMPT2SHELL_SAFE_MODE_STRICT=0
export PROMPT2SHELL_SHOW_TOKENS=1
export PROMPT2SHELL_MAX_OUTPUT_TOKENS=1200
export PROMPT2SHELL_COMMAND_TIMEOUT=300
```

## Example Session

Startup:

```console
Your current environment: Shell=bash, OS=Linux Ubuntu
Safe mode: ON (use `safe on`, `safe off`, `safe`).
Strict safe mode (read-only allowlist): OFF (use `strict on`, `strict off`, `strict`).
Token usage display: ON (use `tokens on`, `tokens off`, `tokens`).
Logging: OFF (set `PROMPT2SHELL_LOG_ENABLED=1` to enable).
Type 'e' to enter manual command mode or 'q' to quit.
```

Request and command:

```console
Prompt2Shell Agent: find the 3 biggest files in this project
Tokens last: in=..., out=..., total=..., out_left=.../... | session: in=..., out=..., total=..., calls=...
This command will search for files in the current directory, sort them by size, and display the top 3 largest files.
```

```shell
du -ah . | sort -rh | head -n 3
```

```console
Command 1/1 action [r=run, e=edit, s=skip, a=run all remaining, q=stop] (default s): a
```

## Development

Run tests:

```shell
./.venv/bin/python -m unittest discover -s tests -v
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
