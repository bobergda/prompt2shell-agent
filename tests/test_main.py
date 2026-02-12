import unittest
from unittest import mock

from prompt2shell import main as main_module


class MainEntrypointTests(unittest.TestCase):
    @staticmethod
    def _stdin_patch(is_tty=True, text=""):
        fake_stdin = mock.Mock()
        fake_stdin.isatty.return_value = is_tty
        fake_stdin.read.return_value = text
        return mock.patch("prompt2shell.main.sys.stdin", fake_stdin)

    def test_main_runs_without_initial_prompt_when_no_argv(self):
        fake_app = mock.Mock()
        with self._stdin_patch(is_tty=True):
            with mock.patch("prompt2shell.main.build_application", return_value=fake_app):
                main_module.main([])

        fake_app.run.assert_called_once_with(initial_prompt=None, exit_after_initial_prompt=False)

    def test_main_passes_joined_argv_as_initial_prompt(self):
        fake_app = mock.Mock()
        with self._stdin_patch(is_tty=True):
            with mock.patch("prompt2shell.main.build_application", return_value=fake_app):
                main_module.main(["find", "largest", "files"])

        fake_app.run.assert_called_once_with(
            initial_prompt="find largest files",
            exit_after_initial_prompt=False,
        )

    def test_main_ignores_blank_initial_prompt(self):
        fake_app = mock.Mock()
        with self._stdin_patch(is_tty=True):
            with mock.patch("prompt2shell.main.build_application", return_value=fake_app):
                main_module.main(["   "])

        fake_app.run.assert_called_once_with(initial_prompt=None, exit_after_initial_prompt=False)

    def test_main_enables_once_mode_from_environment(self):
        fake_app = mock.Mock()
        with self._stdin_patch(is_tty=True):
            with mock.patch.dict("os.environ", {"PROMPT2SHELL_ONCE": "1"}, clear=False):
                with mock.patch("prompt2shell.main.build_application", return_value=fake_app):
                    main_module.main(["quick check"])

        fake_app.run.assert_called_once_with(
            initial_prompt="quick check",
            exit_after_initial_prompt=True,
        )

    def test_main_uses_piped_input_as_initial_prompt_without_auto_once(self):
        fake_app = mock.Mock()
        with self._stdin_patch(is_tty=False, text="file1\nfile2\n"):
            with mock.patch("prompt2shell.main.build_application", return_value=fake_app):
                main_module.main([])

        fake_app.run.assert_called_once_with(
            initial_prompt="file1\nfile2",
            exit_after_initial_prompt=False,
        )

    def test_main_combines_prompt_args_with_piped_input(self):
        fake_app = mock.Mock()
        with self._stdin_patch(is_tty=False, text="a.txt\nb.txt\n"):
            with mock.patch("prompt2shell.main.build_application", return_value=fake_app):
                main_module.main(["summarize"])

        fake_app.run.assert_called_once_with(
            initial_prompt="summarize\n\nPiped input:\na.txt\nb.txt",
            exit_after_initial_prompt=False,
        )

    def test_main_respects_explicit_once_env_value_when_piped(self):
        fake_app = mock.Mock()
        with self._stdin_patch(is_tty=False, text="hello\n"):
            with mock.patch.dict("os.environ", {"PROMPT2SHELL_ONCE": "0"}, clear=False):
                with mock.patch("prompt2shell.main.build_application", return_value=fake_app):
                    main_module.main([])

        fake_app.run.assert_called_once_with(
            initial_prompt="hello",
            exit_after_initial_prompt=False,
        )


if __name__ == "__main__":
    unittest.main()
