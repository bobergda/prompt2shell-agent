import os
import sys

from .application import Application
from .command_helper import CommandHelper
from .common import env_flag
from .interaction_logger import InteractionLogger
from .openai_helper import OpenAIHelper


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
    if initial_prompt is not None and piped_input is not None:
        initial_prompt = f"{initial_prompt}\n\nPiped input:\n{piped_input}"
    elif initial_prompt is None and piped_input is not None:
        initial_prompt = piped_input

    once_mode = env_flag("PROMPT2SHELL_ONCE", False)
    if piped_input is not None and os.getenv("PROMPT2SHELL_ONCE") is None:
        once_mode = True

    build_application().run(initial_prompt=initial_prompt, exit_after_initial_prompt=once_mode)


if __name__ == "__main__":
    main()
