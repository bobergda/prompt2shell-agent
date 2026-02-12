import os
import sys

from .application import Application
from .command_helper import CommandHelper
from .common import env_flag
from .interaction_logger import InteractionLogger
from .openai_helper import OpenAIHelper


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

    once_mode = env_flag("PROMPT2SHELL_ONCE", False)
    build_application().run(initial_prompt=initial_prompt, exit_after_initial_prompt=once_mode)


if __name__ == "__main__":
    main()
