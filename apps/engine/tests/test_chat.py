"""Chat answers only from this briefing's sources, or refuses."""

import os
import unittest
from unittest import mock

from grounded.chat import REFUSAL, answer_from_sources, answer_grounded
from grounded.providers.base import InferenceResult

SCRIPT = {
    "beats": [
        {"ord": 1, "kind": "cover", "layout": "cover", "text": "Weekly ops", "citations": [{"kind": "workbook", "sheet": "Cover", "addr": "A1"}]},
        {"ord": 2, "kind": "kpi", "layout": "versus-target", "text": "Net revenue is $4,820,000, $220,000 above the $4.60M target.",
         "slots": {"eyebrow": "Net revenue"}, "citations": [{"kind": "workbook", "sheet": "KPI", "addr": "B12"}]},
    ]
}
PASSAGES = [
    {"text": "Fulfilment backlog cleared in the Reno warehouse on Tuesday.", "citation": {"kind": "document", "block_id": "p4", "asset_id": "a1"}},
    {"text": "Orders - This week: 1,200; Last week: 1,100", "citation": {"kind": "workbook", "sheet": "KPI", "addr": "A3", "range": "A3:C3", "asset_id": "a2"}},
    {"text": "Next we open the billing screen.", "citation": {"kind": "recording", "t_start_ms": 1000, "t_end_ms": 3000, "asset_id": "a3"}},
]


class ChatTest(unittest.TestCase):
    def test_beat_answer_keeps_citation(self):
        result = answer_grounded(SCRIPT, "What was net revenue against target?", passages=[], use_provider=False)
        self.assertFalse(result["refused"])
        self.assertEqual(result["citations"], SCRIPT["beats"][1]["citations"])

    def test_unsupported_question_refused(self):
        for question in ("What is the CEO's salary?", "Tell me about zebras playing chess", "Will revenue grow next quarter in Europe?"):
            result = answer_grounded(SCRIPT, question, passages=PASSAGES, use_provider=False)
            self.assertTrue(result["refused"], question)
            self.assertEqual(result["text"], REFUSAL)
            self.assertEqual(result["citations"], [])

    def test_source_passages_answer_with_their_citation(self):
        doc = answer_grounded(SCRIPT, "Where was the fulfilment backlog cleared?", passages=PASSAGES, use_provider=False)
        self.assertEqual(doc["citations"][0]["block_id"], "p4")
        cell = answer_grounded(SCRIPT, "How many orders this week?", passages=PASSAGES, use_provider=False)
        self.assertEqual(cell["citations"][0]["range"], "A3:C3")
        rec = answer_grounded(SCRIPT, "When do we open the billing screen?", passages=PASSAGES, use_provider=False)
        self.assertEqual(rec["citations"][0]["t_start_ms"], 1000)

    def test_does_not_answer_from_product_docs(self):
        result = answer_grounded({"beats": []}, "How does the continuous take survivor skill work?", passages=[], use_provider=False)
        self.assertTrue(result["refused"])

    def test_passage_without_citation_is_ignored(self):
        self.assertTrue(answer_from_sources([{"text": "Orders this week 1,200"}], "orders this week")["refused"])

    def test_chat_does_not_call_external_models_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("grounded.providers.bedrock.BedrockInference") as bedrock, \
                 mock.patch("grounded.providers.local.LocalInference") as local, \
                 mock.patch("grounded.net.post_json") as http:
                result = answer_grounded(SCRIPT, "What was net revenue?", passages=[])
        bedrock.assert_not_called()
        local.assert_not_called()
        http.assert_not_called()
        self.assertEqual(result["provider"], "retrieval")

    def test_phrasing_that_adds_facts_is_discarded(self):
        class Model:
            name, model_id = "bedrock", "amazon.nova-lite-v1:0"

            def complete(self, system, prompt, **kwargs):
                return InferenceResult('{"text": "Net revenue was $4,820,000, $220,000 above the $4.60M target, because of EMEA renewals."}', self.name, self.model_id)

        result = answer_grounded(SCRIPT, "What was net revenue?", passages=[], provider=Model())
        self.assertEqual(result["text"], SCRIPT["beats"][1]["text"])
        self.assertFalse(result["phrased"])

    def test_faithful_phrasing_is_kept_and_attributed(self):
        class Model:
            name, model_id = "local", "local-instruct"

            def complete(self, system, prompt, **kwargs):
                return InferenceResult('{"text": "Net revenue came in at $4,820,000 — $220,000 above the $4.60M target."}', self.name, self.model_id)

        result = answer_grounded(SCRIPT, "What was net revenue?", passages=[], provider=Model())
        self.assertTrue(result["phrased"])
        self.assertEqual(result["citations"], SCRIPT["beats"][1]["citations"])


if __name__ == "__main__":
    unittest.main()
