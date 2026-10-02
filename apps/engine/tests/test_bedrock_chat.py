import json
import unittest

from grounded.bedrock import BedrockChat, BedrockError
from grounded.chat import answer_with_claude

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

QUESTION = "What was net revenue against target?"


class FakeConverse:
    def __init__(self, text=None, exc=None):
        self._text = text
        self._exc = exc
        self.calls = 0

    def converse(self, **kwargs):
        self.calls += 1
        if self._exc is not None:
            raise self._exc
        return {"output": {"message": {"content": [{"text": self._text}]}}}


class BedrockChatTest(unittest.TestCase):
    def test_claude_rephrase_keeps_citation(self):
        client = FakeConverse(json.dumps({"text": "Revenue hit $4.82M vs a $4.60M target.", "ord": 1}))
        result = answer_with_claude(SCRIPT, QUESTION, client=client)
        self.assertFalse(result["refused"])
        self.assertTrue(result["claude"])
        self.assertEqual(result["ord"], 1)
        self.assertEqual(result["citations"], SCRIPT["beats"][0]["citations"])

    def test_wrong_beat_falls_back_to_verbatim(self):
        client = FakeConverse(json.dumps({"text": "Invented answer.", "ord": 99}))
        result = answer_with_claude(SCRIPT, QUESTION, client=client)
        self.assertFalse(result["claude"])
        self.assertEqual(result["text"], SCRIPT["beats"][0]["text"])

    def test_bedrock_failure_falls_back_to_verbatim(self):
        client = FakeConverse(exc=RuntimeError("no network"))
        result = answer_with_claude(SCRIPT, QUESTION, client=client)
        self.assertFalse(result["claude"])
        self.assertEqual(result["text"], SCRIPT["beats"][0]["text"])

    def test_refused_question_never_calls_model(self):
        client = FakeConverse(json.dumps({"text": "Leak.", "ord": 1}))
        result = answer_with_claude(SCRIPT, "Tell me about zebras playing chess", client=client)
        self.assertTrue(result["refused"])
        self.assertEqual(client.calls, 0)

    def test_malformed_response_shape_raises(self):
        chat = BedrockChat(client=FakeConverse("ok"))
        chat._client = _Broken()
        with self.assertRaises(BedrockError):
            chat.complete("sys", "hi")


class _Broken:
    def converse(self, **kwargs):
        return {"output": {}}


if __name__ == "__main__":
    unittest.main()
