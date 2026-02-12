import json
import os
import re
import sys

from .application import Application
from .command_helper import CommandHelper
from .common import env_flag
from .interaction_logger import InteractionLogger
from .openai_helper import OpenAIHelper


LS_LONG_ENTRY_PATTERN = re.compile(r"^[bcdlps-][rwxstST-]{9}\s+")


def read_piped_input():
    stdin = getattr(sys, "stdin", None)
    if stdin is None:
        return None
    try:
        if stdin.isatty():
            return None
    except (AttributeError, OSError):
        return None

    try:
        piped_text = stdin.read()
    except OSError:
        return None

    if not isinstance(piped_text, str):
        return None
    piped_text = piped_text.strip()
    if piped_text == "":
        return None
    return piped_text


def infer_piped_source_description(piped_text):
    lines = [line.strip() for line in piped_text.splitlines() if line.strip()]
    if not lines:
        return "shell command output"

    first_line = lines[0]

    try:
        parsed = json.loads(piped_text)
        if isinstance(parsed, (dict, list)):
            return "JSON data"
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    long_ls_entries = sum(1 for line in lines if LS_LONG_ENTRY_PATTERN.match(line))
    if first_line.startswith("total ") and long_ls_entries >= 1:
        return "likely `ls -l` or `ll` output (detailed directory listing)"

    if first_line.startswith("Filesystem") and ("Mounted on" in first_line or "Use%" in first_line):
        return "likely `df -h` output (filesystem usage)"

    if (first_line.startswith("PID") or first_line.startswith("USER")) and ("CMD" in first_line or "COMMAND" in first_line):
        return "likely `ps` output (process list)"

    if first_line.startswith("On branch ") or "nothing to commit" in piped_text:
        return "likely `git status` output"

    simple_name_lines = 0
    for line in lines:
        if " " in line or "\t" in line:
            continue
        simple_name_lines += 1
    if len(lines) >= 3 and simple_name_lines / len(lines) >= 0.7:
        return "likely `ls` output (list of names)"

    return "shell command output"


def build_prompt_from_pipe(user_prompt, piped_input):
    source_description = infer_piped_source_description(piped_input)

    if isinstance(user_prompt, str) and user_prompt.strip() != "":
        return (
            f"{user_prompt}\n\n"
            f"Pipeline context: {source_description}.\n"
            "Use the piped command output below as primary input.\n\n"
            f"Piped input:\n{piped_input}"
        )

    return (
        "Describe and analyze the following piped command output. "
        f"Inferred source: {source_description}.\n\n"
        f"Piped input:\n{piped_input}"
    )


def build_application():
    max_output_tokens_raw = os.getenv("PROMPT2SHELL_MAX_OUTPUT_TOKENS", "1200")
    try:
        max_output_tokens = int(max_output_tokens_raw)
        if max_output_tokens <= 0:
            max_output_tokens = 1200
    except (TypeError, ValueError):
        max_output_tokens = 1200

    interaction_logger = InteractionLogger()
    openai_helper = OpenAIHelper(
        model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        max_output_tokens=max_output_tokens,
        interaction_logger=interaction_logger,
    )
    command_helper = CommandHelper()
    return Application(openai_helper, command_helper, interaction_logger)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    initial_prompt = " ".join(argv).strip() if argv else None
    if initial_prompt == "":
        initial_prompt = None

    piped_input = read_piped_input()
    if piped_input is not None:
        initial_prompt = build_prompt_from_pipe(initial_prompt, piped_input)

    once_mode = env_flag("PROMPT2SHELL_ONCE", False)
    app = build_application()
    configure_context = getattr(getattr(app, "openai_helper", None), "configure_session_context", None)
    if callable(configure_context):
        configure_context(
            once_mode=once_mode,
            has_piped_input=piped_input is not None,
        )

    app.run(initial_prompt=initial_prompt, exit_after_initial_prompt=once_mode)


if __name__ == "__main__":
    main()
