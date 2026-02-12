import types
import unittest
from unittest import mock

from prompt2shell.application import Application


class ApplicationRunBannerTests(unittest.TestCase):
    def _build_app(self):
        app = Application.__new__(Application)
        app.openai_helper = types.SimpleNamespace(os_name="Linux", shell_name="bash", model_name="gpt-test")
        app.interaction_logger = mock.Mock()
        app.session = mock.Mock()
        app._process_user_input = mock.Mock(return_value=False)
        return app

    def test_run_shows_interactive_hint_without_initial_prompt(self):
        app = self._build_app()
        app.session.prompt.return_value = "q"

        with mock.patch("prompt2shell.application.colored", side_effect=lambda text, *_a, **_k: text):
            with mock.patch("builtins.print") as print_mock:
                app.run(initial_prompt=None)

        printed_lines = [str(call.args[0]) for call in print_mock.call_args_list if call.args]
        self.assertTrue(any("Your current environment: Shell=bash, OS=Linux, Model=gpt-test" in line for line in printed_lines))
        self.assertTrue(any("Type 'e' to enter manual command mode or 'q' to quit." in line for line in printed_lines))

    def test_run_hides_interactive_hint_with_initial_prompt(self):
        app = self._build_app()
        app._process_user_input = mock.Mock(return_value=True)

        with mock.patch("prompt2shell.application.colored", side_effect=lambda text, *_a, **_k: text):
            with mock.patch("builtins.print") as print_mock:
                app.run(initial_prompt="show files", exit_after_initial_prompt=True)

        printed_lines = [str(call.args[0]) for call in print_mock.call_args_list if call.args]
        self.assertFalse(any("Type 'e' to enter manual command mode or 'q' to quit." in line for line in printed_lines))
        self.assertTrue(any("Initial prompt: show files" in line for line in printed_lines))
        app._process_user_input.assert_called_once_with("show files")

    def test_run_shows_compact_preview_for_piped_initial_prompt(self):
        app = self._build_app()
        app._process_user_input = mock.Mock(return_value=True)
        initial_prompt = "summarize\n\nPipeline context: likely ls.\n\nPiped input:\nfile1\nfile2"

        with mock.patch("prompt2shell.application.colored", side_effect=lambda text, *_a, **_k: text):
            with mock.patch("builtins.print") as print_mock:
                app.run(initial_prompt=initial_prompt, exit_after_initial_prompt=True)

        printed_lines = [str(call.args[0]) for call in print_mock.call_args_list if call.args]
        self.assertTrue(any("[stdin attached]" in line for line in printed_lines))
        self.assertFalse(any("file1" in line for line in printed_lines))
        app._process_user_input.assert_called_once_with(initial_prompt)


class ApplicationInitTests(unittest.TestCase):
    def test_init_prefers_tty_io_for_prompt_session(self):
        fake_history = mock.Mock()
        fake_auto = mock.Mock()
        fake_input = mock.Mock()
        fake_output = mock.Mock()
        fake_session = mock.Mock()

        openai_helper = types.SimpleNamespace(os_name="Linux", shell_name="bash", model_name="gpt-test")
        command_helper = mock.Mock()
        interaction_logger = mock.Mock()

        with mock.patch("prompt2shell.application.FileHistoryPath.default", return_value="/tmp/default.hist"):
            with mock.patch("prompt2shell.application.FileHistoryPath.legacy", return_value="/tmp/legacy.hist"):
                with mock.patch("prompt2shell.application.FileHistoryPath.exists", return_value=True):
                    with mock.patch("prompt2shell.application.FileHistory", return_value=fake_history):
                        with mock.patch("prompt2shell.application.AutoSuggestFromHistory", return_value=fake_auto):
                            with mock.patch("prompt2shell.application.create_input", return_value=fake_input) as create_input_mock:
                                with mock.patch("prompt2shell.application.create_output", return_value=fake_output) as create_output_mock:
                                    with mock.patch("prompt2shell.application.PromptSession", return_value=fake_session) as prompt_session_mock:
                                        app = Application(openai_helper, command_helper, interaction_logger)

        create_input_mock.assert_called_once_with(always_prefer_tty=True)
        create_output_mock.assert_called_once_with(always_prefer_tty=True)
        prompt_session_mock.assert_called_once_with(
            history=fake_history,
            auto_suggest=fake_auto,
            input=fake_input,
            output=fake_output,
        )
        self.assertIs(app.session, fake_session)


if __name__ == "__main__":
    unittest.main()
