import json
import os
import sys
import threading
from datetime import datetime, timezone

from .command_helper import CommandHelper
from .common import colored, env_flag_with_legacy, getenv_with_legacy


class InteractionLogger:
    """Helper class for logging user queries and assistant responses."""

    def __init__(self, log_file=None, enabled=None):
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        default_path = os.path.join(app_dir, "logs", "prompt2shell.log")
        configured_path = log_file or getenv_with_legacy(
            "PROMPT2SHELL_LOG_FILE",
            "GPT_SHELL_LOG_FILE",
            default_path,
        )
        resolved_path = os.path.expanduser(configured_path)
        if not os.path.isabs(resolved_path):
            resolved_path = os.path.join(app_dir, resolved_path)

        if enabled is None:
            self.enabled = env_flag_with_legacy(
                "PROMPT2SHELL_LOG_ENABLED",
                "GPT_SHELL_LOG_ENABLED",
                False,
            )
        else:
            self.enabled = bool(enabled)

        self.log_file = resolved_path
        self._lock = threading.Lock()

        if not self.enabled:
            return

        log_dir = os.path.dirname(self.log_file)
        if log_dir:
            try:
                os.makedirs(log_dir, exist_ok=True)
            except OSError as exc:
                print(colored(f"Warning: unable to create log directory: {exc}", "yellow"), file=sys.stderr)

    @staticmethod
    def _sanitize_for_log(value):
        if isinstance(value, str):
            return CommandHelper.redact_sensitive_text(value)
        if isinstance(value, dict):
            return {str(key): InteractionLogger._sanitize_for_log(item) for key, item in value.items()}
        if isinstance(value, list):
            return [InteractionLogger._sanitize_for_log(item) for item in value]
        if isinstance(value, tuple):
            return [InteractionLogger._sanitize_for_log(item) for item in value]
        return value

    def _write_entry(self, entry):
        if not self.enabled:
            return

        flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
        with self._lock:
            file_descriptor = os.open(self.log_file, flags, 0o600)
            try:
                os.fchmod(file_descriptor, 0o600)
            except OSError:
                pass
            try:
                file_handle = os.fdopen(file_descriptor, "a", encoding="utf-8")
            except Exception:
                os.close(file_descriptor)
                raise
            with file_handle:
                file_handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def log(self, role, text):
        if not self.enabled:
            return
        if not isinstance(text, str) or text.strip() == "":
            return

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "text": self._sanitize_for_log(text),
        }

        try:
            self._write_entry(entry)
        except OSError as exc:
            print(colored(f"Warning: unable to write log: {exc}", "yellow"), file=sys.stderr)

    def log_event(self, event_name, data=None):
        if not self.enabled:
            return
        if not isinstance(event_name, str) or event_name.strip() == "":
            return

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "event",
            "event": event_name,
            "data": self._sanitize_for_log(data),
        }

        try:
            self._write_entry(entry)
        except OSError as exc:
            print(colored(f"Warning: unable to write log: {exc}", "yellow"), file=sys.stderr)
