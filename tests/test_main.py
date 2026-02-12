import unittest
from unittest import mock

from prompt2shell import main as main_module


class MainEntrypointTests(unittest.TestCase):
    def test_main_runs_without_initial_prompt_when_no_argv(self):
        fake_app = mock.Mock()
        with mock.patch("prompt2shell.main.build_application", return_value=fake_app):
            main_module.main([])

        fake_app.run.assert_called_once_with(initial_prompt=None, exit_after_initial_prompt=False)

    def test_main_passes_joined_argv_as_initial_prompt(self):
        fake_app = mock.Mock()
        with mock.patch("prompt2shell.main.build_application", return_value=fake_app):
            main_module.main(["find", "largest", "files"])

        fake_app.run.assert_called_once_with(
            initial_prompt="find largest files",
            exit_after_initial_prompt=False,
        )

    def test_main_ignores_blank_initial_prompt(self):
        fake_app = mock.Mock()
        with mock.patch("prompt2shell.main.build_application", return_value=fake_app):
            main_module.main(["   "])

        fake_app.run.assert_called_once_with(initial_prompt=None, exit_after_initial_prompt=False)

    def test_main_enables_once_mode_from_environment(self):
        fake_app = mock.Mock()
        with mock.patch.dict("os.environ", {"PROMPT2SHELL_ONCE": "1"}, clear=False):
            with mock.patch("prompt2shell.main.build_application", return_value=fake_app):
                main_module.main(["quick check"])

        fake_app.run.assert_called_once_with(
            initial_prompt="quick check",
            exit_after_initial_prompt=True,
        )


if __name__ == "__main__":
    unittest.main()
