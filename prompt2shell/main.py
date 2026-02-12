import os

from .application import Application
from .command_helper import CommandHelper
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


def main():
    build_application().run()


if __name__ == "__main__":
    main()
