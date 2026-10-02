import unittest

from grounded.bedrock import BedrockChat, BedrockError
from grounded.chat import answer, answer_with_claude

SCRIPT = {
    "beats": [
        {
            "ord": 1,
            "kind": "step",
            "text": "Net revenue is $4.82M, $220,000 above the target of $4.60M.",
            "citations": [{"kind": "workbook", "sheet": "KPI", "addr": "B12"}],
        }
    ]
}


class OfflineChatTest(unittest.TestCase):
    def test_chat_returns_grounded_beat_without_model(self):
        result = answer(SCRIPT, "What was net revenue against target?")
        self.assertFalse(result["refused"])
        self.assertFalse(result["model_used"])
        self.assertEqual(result["citations"], SCRIPT["beats"][0]["citations"])

    def test_legacy_claude_wrapper_never_calls_client(self):
        class Explode:
            def complete(self, *args, **kwargs):
                raise AssertionError("network/model client must not be called")
        result = answer_with_claude(SCRIPT, "What was net revenue?", client=Explode())
        self.assertFalse(result["claude"])
        self.assertEqual(result["text"], SCRIPT["beats"][0]["text"])

    def test_bedrock_constructor_fails_closed(self):
        with self.assertRaises(BedrockError):
            BedrockChat()


if __name__ == "__main__":
    unittest.main()
