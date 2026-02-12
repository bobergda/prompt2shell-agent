import json
import os
import stat
import tempfile
import unittest
from unittest import mock

from prompt2shell.interaction_logger import InteractionLogger


class InteractionLoggerTests(unittest.TestCase):
    def test_logging_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = os.path.join(tmp_dir, "disabled.log")
            with mock.patch.dict(os.environ, {}, clear=True):
                logger = InteractionLogger(log_file=log_path)
                logger.log("user", "hello")

            self.assertFalse(os.path.exists(log_path))

    def test_logging_enabled_writes_redacted_entry_with_private_permissions(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = os.path.join(tmp_dir, "enabled.log")
            with mock.patch.dict(os.environ, {"PROMPT2SHELL_LOG_ENABLED": "1"}, clear=True):
                logger = InteractionLogger(log_file=log_path)
                logger.log("user", "Authorization: Bearer secret-token")

            self.assertTrue(os.path.exists(log_path))
            permissions = stat.S_IMODE(os.stat(log_path).st_mode)
            self.assertEqual(permissions, 0o600)

            with open(log_path, "r", encoding="utf-8") as handle:
                entry = json.loads(handle.readline())

            self.assertIn("<REDACTED>", entry["text"])
            self.assertNotIn("secret-token", entry["text"])


if __name__ == "__main__":
    unittest.main()
