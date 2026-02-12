import os

from termcolor import colored as term_colored

APP_NAME = "Prompt2Shell Agent"


# Built-in visual theme (no env-based color overrides).
THEME_COLOR_MAP = {
    "green": "cyan",     # prompts and general app info
    "magenta": "white",  # assistant narrative text
    "blue": "blue",      # command lines
    "cyan": "cyan",
    "yellow": "yellow",
    "red": "red",
    "white": "white",
    "grey": "grey",
}

THEME_ATTRS_MAP = {
    "green": ["bold"],
    "blue": ["bold"],
}


def colored(text, color=None, on_color=None, attrs=None):
    mapped_color = color
    if isinstance(color, str):
        color_key = color.lower()
        mapped_color = THEME_COLOR_MAP.get(color_key, color_key)
        if attrs is None:
            attrs = THEME_ATTRS_MAP.get(color_key)
    return term_colored(text, mapped_color, on_color=on_color, attrs=attrs)


def getenv_with_legacy(primary_key, legacy_key, default=None):
    value = os.getenv(primary_key)
    if value is not None:
        return value
    return os.getenv(legacy_key, default)


def env_flag_with_legacy(primary_key, legacy_key, default=False):
    default_raw = "1" if default else "0"
    raw_value = str(getenv_with_legacy(primary_key, legacy_key, default_raw)).strip().lower()
    return raw_value not in {"0", "false", "off", "no"}
