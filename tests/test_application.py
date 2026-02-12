import types
import unittest
from unittest import mock

from prompt2shell.application import Application


class ApplicationRunBannerTests(unittest.TestCase):
    def _build_app(self):
        app = Application.__new__(Application)
        app.openai_helper = types.SimpleNamespace(os_name="Linux", shell_name="bash")
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
        self.assertTrue(any("Type 'e' to enter manual command mode or 'q' to quit." in line for line in printed_lines))

    def test_run_hides_interactive_hint_with_initial_prompt(self):
        app = self._build_app()
        app._process_user_input = mock.Mock(return_value=True)

        with mock.patch("prompt2shell.application.colored", side_effect=lambda text, *_a, **_k: text):
            with mock.patch("builtins.print") as print_mock:
                app.run(initial_prompt="show files", exit_after_initial_prompt=True)

        printed_lines = [str(call.args[0]) for call in print_mock.call_args_list if call.args]
        self.assertFalse(any("Type 'e' to enter manual command mode or 'q' to quit." in line for line in printed_lines))
        app._process_user_input.assert_called_once_with("show files")


if __name__ == "__main__":
    unittest.main()
