import subprocess
import sys

from prompt_toolkit import ANSI, PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory

from .common import APP_NAME, colored, env_flag


class Application:
    """Main application class."""

    def __init__(self, openai_helper, command_helper, interaction_logger):
        """Initializes the application."""
        self.openai_helper = openai_helper
        self.command_helper = command_helper
        self.interaction_logger = interaction_logger
        self.safe_mode_enabled = self._read_safe_mode_from_env()
        self.safe_mode_strict = self._read_safe_mode_strict_from_env()
        self.show_tokens = self._read_show_tokens_from_env()

        default_history_path = FileHistoryPath.default()
        legacy_history_path = FileHistoryPath.legacy()
        history_path = default_history_path
        if not FileHistoryPath.exists(default_history_path) and FileHistoryPath.exists(legacy_history_path):
            history_path = legacy_history_path

        self.session = PromptSession(
            history=FileHistory(history_path),
            auto_suggest=AutoSuggestFromHistory(),
        )

    @staticmethod
    def _read_safe_mode_from_env():
        return env_flag("PROMPT2SHELL_SAFE_MODE", True)

    @staticmethod
    def _read_safe_mode_strict_from_env():
        return env_flag("PROMPT2SHELL_SAFE_MODE_STRICT", False)

    @staticmethod
    def _read_show_tokens_from_env():
        return env_flag("PROMPT2SHELL_SHOW_TOKENS", True)

    def _safe_mode_status_text(self):
        return "ON" if self.safe_mode_enabled else "OFF"

    def _safe_mode_strict_status_text(self):
        return "ON" if self.safe_mode_strict else "OFF"

    def _show_tokens_status_text(self):
        return "ON" if self.show_tokens else "OFF"

    def _set_safe_mode(self, enabled):
        self.safe_mode_enabled = enabled
        print(colored(f"Safe mode: {self._safe_mode_status_text()}", "green" if enabled else "yellow"))
        self.interaction_logger.log_event("safe_mode_changed", {"enabled": enabled})

    def _set_safe_mode_strict(self, enabled):
        self.safe_mode_strict = enabled
        print(colored(
            f"Strict safe mode (read-only allowlist): {self._safe_mode_strict_status_text()}",
            "green" if enabled else "yellow",
        ))
        self.interaction_logger.log_event("safe_mode_strict_changed", {"enabled": enabled})

    def _set_show_tokens(self, enabled):
        self.show_tokens = enabled
        print(colored(f"Token usage display: {self._show_tokens_status_text()}", "green" if enabled else "yellow"))
        self.interaction_logger.log_event("token_usage_display_changed", {"enabled": enabled})

    def _print_token_usage(self):
        if not self.show_tokens:
            return

        usage = self.openai_helper.get_last_usage_summary()
        if usage is None:
            return

        session_usage = self.openai_helper.get_session_usage_summary()
        max_output_tokens = self.openai_helper.max_output_tokens
        output_left = max(0, max_output_tokens - usage.get("output_tokens", 0))

        usage_text = (
            f"Tokens last: in={usage.get('input_tokens', 0)}, "
            f"out={usage.get('output_tokens', 0)}, total={usage.get('total_tokens', 0)}, "
            f"out_left={output_left}/{max_output_tokens} | "
            f"session: in={session_usage.get('input_tokens', 0)}, "
            f"out={session_usage.get('output_tokens', 0)}, "
            f"total={session_usage.get('total_tokens', 0)}, "
            f"calls={session_usage.get('api_calls', 0)}"
        )
        print(colored(usage_text, "cyan"))

    def _print_assistant_response(self, response):
        if not isinstance(response, str) or response.strip() == "":
            return
        print(colored(response, "magenta"))
        self.interaction_logger.log("assistant", response)

    def _print_commands_batch(self, commands):
        print(colored("\nProposed commands:", "green"))
        for index, command in enumerate(commands, start=1):
            command_str = command.get("command", "").strip()
            description = command.get("description", "").strip()
            print(colored(f"[{index}] {command_str}", "blue"))
            if description:
                print(colored(f"    {description}", "grey"))

    def _prompt_command_action(self, index, total):
        prompt_text = (
            f"Command {index}/{total} action "
            "[r=run, e=edit, s=skip, a=run all remaining, q=stop] (default s): "
        )
        while True:
            action = self.session.prompt(ANSI(colored(prompt_text, "green"))).strip().lower()
            if action == "":
                return "s"
            if action in {"r", "e", "s", "a", "q", "y", "n"}:
                return {"y": "r", "n": "s"}.get(action, action)
            print(colored("Invalid choice. Use r/e/s/a/q.", "yellow"))

    def _prompt_yes_no(self, text):
        while True:
            answer = self.session.prompt(ANSI(colored(text, "green"))).strip().lower()
            if answer in {"", "n", "no"}:
                return False
            if answer in {"y", "yes"}:
                return True
            print(colored("Please answer with y or n.", "yellow"))

    def _guard_command_with_safe_mode(self, command_str):
        candidate = command_str
        while True:
            if not self.safe_mode_enabled:
                return candidate, None

            if self.safe_mode_strict:
                strict_reason = self.command_helper.detect_non_readonly_command(candidate)
                if strict_reason is not None:
                    warning = f"Strict safe mode blocked command ({strict_reason}): {candidate}"
                    print(colored(warning, "red"))
                    self.interaction_logger.log_event(
                        "strict_safe_mode_blocked_command",
                        {"command": candidate, "reason": strict_reason},
                    )
                    prompt_text = "Strict safe mode action [e=edit, s=skip] (default s): "
                    action = self.session.prompt(ANSI(colored(prompt_text, "yellow"))).strip().lower()

                    if action in {"e", "edit"}:
                        edited = self.session.prompt(
                            ANSI(colored("Enter the modified command: ", "cyan")),
                            default=candidate,
                        ).strip()
                        if edited == "":
                            return None, "safe_mode_empty_after_edit"
                        candidate = edited
                        continue

                    return None, "blocked_by_strict_safe_mode"

            reason = self.command_helper.detect_destructive_command(candidate)
            if reason is None:
                return candidate, None

            warning = f"Safe mode blocked high-risk command ({reason}): {candidate}"
            print(colored(warning, "red"))
            self.interaction_logger.log_event(
                "safe_mode_blocked_command",
                {"command": candidate, "reason": reason},
            )
            prompt_text = "Safe mode action [run=execute once, e=edit, s=skip] (default s): "
            action = self.session.prompt(ANSI(colored(prompt_text, "yellow"))).strip().lower()

            if action in {"run", "r"}:
                self.interaction_logger.log_event(
                    "safe_mode_override",
                    {"command": candidate, "reason": reason},
                )
                return candidate, None

            if action in {"e", "edit"}:
                edited = self.session.prompt(
                    ANSI(colored("Enter the modified command: ", "cyan")),
                    default=candidate,
                ).strip()
                if edited == "":
                    return None, "safe_mode_empty_after_edit"
                candidate = edited
                continue

            return None, "blocked_by_safe_mode"

    def _handle_runtime_command(self, user_input):
        normalized = user_input.strip().lower()
        if normalized in {"safe", "/safe"}:
            print(colored(
                f"Safe mode is {self._safe_mode_status_text()} | strict read-only mode is {self._safe_mode_strict_status_text()}",
                "green" if self.safe_mode_enabled else "yellow",
            ))
            return True

        if normalized in {"safe on", "/safe on"}:
            self._set_safe_mode(True)
            return True

        if normalized in {"safe off", "/safe off"}:
            if self._prompt_yes_no("Disable safe mode? This can execute destructive commands. (y/N): "):
                self._set_safe_mode(False)
            else:
                print(colored("Safe mode stays ON.", "yellow"))
            return True

        if normalized in {"strict", "/strict"}:
            print(colored(
                f"Strict safe mode (read-only allowlist) is {self._safe_mode_strict_status_text()}",
                "green" if self.safe_mode_strict else "yellow",
            ))
            return True

        if normalized in {"strict on", "/strict on"}:
            self._set_safe_mode_strict(True)
            return True

        if normalized in {"strict off", "/strict off"}:
            self._set_safe_mode_strict(False)
            return True

        if normalized in {"tokens", "/tokens"}:
            print(colored(
                f"Token usage display: {self._show_tokens_status_text()}",
                "green" if self.show_tokens else "yellow",
            ))
            return True

        if normalized in {"tokens on", "/tokens on"}:
            self._set_show_tokens(True)
            return True

        if normalized in {"tokens off", "/tokens off"}:
            self._set_show_tokens(False)
            return True

        return False

    def interpret_and_execute_command(self, user_prompt):
        """Interprets and executes the command."""
        if user_prompt == "e":
            self.manual_command_mode()
        else:
            self.auto_command_mode(user_prompt)

    def manual_command_mode(self):
        """Manual command mode."""
        print(colored("Manual command mode activated. Please enter your command:", "green"))
        command_str = self.session.prompt("").strip()
        if command_str == "":
            print(colored("No command entered.", "yellow"))
            return

        if not self._prompt_yes_no(f"Run command `{command_str}`? (y/N): "):
            print(colored("Command canceled.", "yellow"))
            self.interaction_logger.log_event("command_skipped", {"command": command_str, "reason": "manual_mode_cancel"})
            return

        guarded_command, skip_reason = self._guard_command_with_safe_mode(command_str)
        if guarded_command is None:
            print(colored("Command canceled by safe mode.", "yellow"))
            self.interaction_logger.log_event(
                "command_skipped",
                {"command": command_str, "reason": skip_reason},
            )
            return

        command_output = self.command_helper.run_shell_command(guarded_command)
        self.interaction_logger.log_event("command_executed", command_output)
        outputs = [command_output]
        execution_summary = [{"command": guarded_command, "status": "executed"}]

        response, commands = self.openai_helper.send_commands_outputs(outputs, execution_summary=execution_summary)
        self._print_assistant_response(response)
        self._print_token_usage()
        if commands:
            self.execute_commands(commands)

    def auto_command_mode(self, user_prompt):
        """Auto command mode."""
        commands_payload = self.openai_helper.get_commands(user_prompt)
        self._print_token_usage()
        self.interaction_logger.log_event("auto_mode_commands_payload", commands_payload)
        if commands_payload and commands_payload.get("response"):
            self._print_assistant_response(commands_payload["response"])

        commands = commands_payload.get("commands") if commands_payload else None
        if commands:
            self.execute_commands(commands)
        elif commands_payload and commands_payload.get("response"):
            print(colored("No commands proposed.", "yellow"))
        else:
            print(colored("No commands found", "red"))

    def execute_commands(self, commands):
        """Executes the commands."""
        while commands:
            self._print_commands_batch(commands)
            self.interaction_logger.log_event("commands_batch", commands)

            outputs = []
            execution_summary = []
            run_all_remaining = False
            stop_after_batch = False

            for index, command in enumerate(commands, start=1):
                command_str = command.get("command", "").strip()
                if command_str == "":
                    execution_summary.append({"command": "", "status": "skipped_empty"})
                    continue

                action = "r" if run_all_remaining else self._prompt_command_action(index, len(commands))

                if action == "q":
                    stop_after_batch = True
                    execution_summary.append({"command": command_str, "status": "stopped_by_user"})
                    break

                if action == "a":
                    run_all_remaining = True
                    action = "r"

                if action == "e":
                    edited_command = self.session.prompt(
                        ANSI(colored("Enter the modified command: ", "cyan")),
                        default=command_str,
                    ).strip()
                    if edited_command == "":
                        print(colored("Empty command after edit, skipping.", "yellow"))
                        execution_summary.append({"command": command_str, "status": "skipped_empty_after_edit"})
                        self.interaction_logger.log_event(
                            "command_skipped",
                            {"command": command_str, "reason": "empty_after_edit"},
                        )
                        continue
                    command_str = edited_command
                    if not self._prompt_yes_no("Run the edited command? (y/N): "):
                        print(colored("Skipping command", "yellow"))
                        execution_summary.append({"command": command_str, "status": "skipped_after_edit"})
                        self.interaction_logger.log_event(
                            "command_skipped",
                            {"command": command_str, "reason": "skipped_after_edit"},
                        )
                        continue
                    action = "r"

                if action == "s":
                    print(colored("Skipping command", "yellow"))
                    execution_summary.append({"command": command_str, "status": "skipped"})
                    self.interaction_logger.log_event("command_skipped", {"command": command_str})
                    continue

                guarded_command, skip_reason = self._guard_command_with_safe_mode(command_str)
                if guarded_command is None:
                    print(colored("Skipping command (safe mode).", "yellow"))
                    execution_summary.append({"command": command_str, "status": "blocked_by_safe_mode"})
                    self.interaction_logger.log_event(
                        "command_skipped",
                        {"command": command_str, "reason": skip_reason},
                    )
                    continue

                output = self.command_helper.run_shell_command(guarded_command)
                outputs.append(output)
                execution_summary.append(
                    {
                        "command": guarded_command,
                        "status": "executed",
                        "returncode": output.get("returncode"),
                        "timed_out": output.get("timed_out"),
                        "interrupted": output.get("interrupted"),
                    }
                )
                self.interaction_logger.log_event("command_executed", output)

            self.interaction_logger.log_event("commands_execution_summary", execution_summary)

            if not outputs:
                print(colored("No commands were executed.", "yellow"))
                break

            response, next_commands = self.openai_helper.send_commands_outputs(
                outputs,
                execution_summary=execution_summary,
            )
            self._print_assistant_response(response)
            self._print_token_usage()
            if stop_after_batch:
                break
            commands = next_commands

    def _process_user_input(self, user_input):
        if user_input.lower() == "q":
            return False
        self.interaction_logger.log("user", user_input)
        if self._handle_runtime_command(user_input):
            return True
        self.interpret_and_execute_command(user_input)
        return True

    def run(self, initial_prompt=None, exit_after_initial_prompt=False):
        """Runs the application."""
        os_name, shell_name = self.openai_helper.os_name, self.openai_helper.shell_name
        model_name = getattr(self.openai_helper, "model_name", "unknown")
        has_initial_prompt = isinstance(initial_prompt, str) and initial_prompt.strip() != ""
        print(colored(f"Your current environment: Shell={shell_name}, OS={os_name}, Model={model_name}", "green"))
        if not has_initial_prompt:
            print(colored("Type 'e' to enter manual command mode or 'q' to quit.\n", "green"))

        if has_initial_prompt:
            print(colored(f"Initial prompt: {initial_prompt}", "green"))
            try:
                if not self._process_user_input(initial_prompt):
                    return
            except subprocess.CalledProcessError as exc:
                print(
                    colored(f"Error: Command failed with exit code {exc.returncode}: {exc.output}", "red"),
                    file=sys.stderr,
                )
            except KeyboardInterrupt:
                if exit_after_initial_prompt:
                    return
            except EOFError:
                return
            except Exception as exc:  # pylint: disable=broad-except
                print(colored(f"Error of type {type(exc).__name__}: {exc}", "red"))
                print(colored("Exiting...", "yellow"))
                return

            if exit_after_initial_prompt:
                return

        while True:
            try:
                user_input = self.session.prompt(ANSI(colored(f"{APP_NAME}: ", "green")))
                if not self._process_user_input(user_input):
                    break
            except subprocess.CalledProcessError as exc:
                print(
                    colored(f"Error: Command failed with exit code {exc.returncode}: {exc.output}", "red"),
                    file=sys.stderr,
                )
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            except Exception as exc:  # pylint: disable=broad-except
                print(colored(f"Error of type {type(exc).__name__}: {exc}", "red"))
                print(colored("Exiting...", "yellow"))
                break


class FileHistoryPath:
    @staticmethod
    def default():
        from os.path import expanduser

        return expanduser("~/.prompt2shell_history")

    @staticmethod
    def legacy():
        from os.path import expanduser

        return expanduser("~/.gpts_history")

    @staticmethod
    def exists(path):
        from os.path import exists

        return exists(path)
