import json
import os
import types
import unittest
from unittest import mock

from prompt2shell_agent.openai_helper import OpenAIHelper


class OpenAIHelperTests(unittest.TestCase):
    def test_get_commands_parses_function_call_payload(self):
        fake_responses = [
            types.SimpleNamespace(
                id="resp_1",
                usage=types.SimpleNamespace(input_tokens=10, output_tokens=20, total_tokens=30),
                output=[
                    types.SimpleNamespace(
                        type="function_call",
                        name="get_commands",
                        arguments=json.dumps(
                            {
                                "commands": [{"command": "ls -la", "description": "List files"}],
                                "response": "Here is the command.",
                            }
                        ),
                        call_id="call_1",
                        id="item_1",
                    )
                ],
                output_text=None,
            ),
            types.SimpleNamespace(
                id="resp_2",
                usage=types.SimpleNamespace(input_tokens=2, output_tokens=3, total_tokens=5),
                output=[],
                output_text="Done",
            ),
        ]

        class FakeResponsesAPI:
            def __init__(self, queue):
                self.queue = queue
                self.calls = []

            def create(self, **kwargs):
                self.calls.append(kwargs)
                return self.queue.pop(0)

        fake_api = FakeResponsesAPI(fake_responses)
        fake_client = types.SimpleNamespace(responses=fake_api)

        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False):
            with mock.patch("prompt2shell_agent.openai_helper.OpenAI", return_value=fake_client):
                helper = OpenAIHelper(model_name="gpt-test", max_output_tokens=200)
                payload = helper.get_commands("show files")

        self.assertIsNotNone(payload)
        self.assertEqual(payload["commands"][0]["command"], "ls -la")
        self.assertEqual(payload["response"], "Here is the command.")
        self.assertEqual(helper.last_response_id, "resp_2")

        self.assertEqual(fake_api.calls[0]["tool_choice"], {"type": "function", "name": "get_commands"})
        self.assertEqual(fake_api.calls[1]["tool_choice"], "none")


if __name__ == "__main__":
    unittest.main()
