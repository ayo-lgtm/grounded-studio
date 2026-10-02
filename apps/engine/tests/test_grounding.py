"""Model (Nova or local) output must pass deterministic grounding and QA."""

import copy
import json
import os
import unittest
from unittest import mock

from grounded.assist import assist_script, check_summary_sentence
from grounded.compile_deck import cell_index, compile_workbook
from grounded.dispatch import specialize_workbook
from grounded.grounding import check_rewrite, evaluate, recompute
from grounded.providers.base import InferenceResult
from grounded.qa import validate_script

PACK = {
    "title": {"text": "Weekly ops", "sheet": "Cover", "addr": "A1"},
    "period": {"text": "Week 32", "sheet": "Cover", "addr": "A2"},
    "kpis": [
        {"label": "Net revenue", "sheet": "KPI", "addr": "B12", "value": 4820000, "unit": "usd",
         "target": 4600000, "target_sheet": "KPI", "target_addr": "B13",
         "display": "$4,820,000", "target_display": "$4.60M"},
    ],
    "movers": [
        {"label": "Enterprise", "sheet": "KPI", "addr": "B20", "value": 3100000, "prior": 2900000,
         "prior_addr": "C20", "display": "$3,100,000", "prior_display": "$2,900,000"},
    ],
    "risks": [{"sheet": "Notes", "addr": "A5", "text": "Churn ticked up in March."}],
    "asks": [{"sheet": "Notes", "addr": "A6", "text": "Approve two support hires."}],
}

AWS_ENV = {
    "GROUNDED_DEPLOYMENT_MODE": "aws-private",
    "GROUNDED_AWS_REGIONS": "us-east-1",
    "AWS_REGION": "us-east-1",
    "GROUNDED_BEDROCK_MODELS": "amazon.nova-pro-v1:0",
    "GROUNDED_BEDROCK_TEXT_MODEL": "amazon.nova-pro-v1:0",
    "GROUNDED_INFERENCE_PROVIDER": "bedrock",
    "GROUNDED_ASSIST_FEATURES": "polish,summary",
    "GROUNDED_BEDROCK_ENDPOINT": "https://vpce-0abc-1.bedrock-runtime.us-east-1.vpce.amazonaws.com",
}


class FakeNova:
    """A Bedrock Converse client returning scripted replies (no network)."""

    def __init__(self, replies):
        self.replies = list(replies)

    def converse(self, **kwargs):
        reply = self.replies.pop(0) if self.replies else "{}"
        return {"output": {"message": {"content": [{"text": reply}]}}}


def nova(replies):
    from grounded.providers.bedrock import BedrockInference

    return BedrockInference(client=FakeNova(replies))


class RewriteGateTest(unittest.TestCase):
    SOURCE = "Net revenue is $4,820,000, $220,000 above the $4.60M target."

    def test_faithful_rephrase_passes(self):
        self.assertTrue(check_rewrite(self.SOURCE, "Net revenue came in at $4,820,000 — $220,000 above the $4.60M target.").ok)

    def test_invented_number_rejected(self):
        verdict = check_rewrite(self.SOURCE, "Net revenue is $4,820,000, $220,000 above the $4.60M target, up 12%.")
        self.assertEqual(verdict.reason, "numbers drifted")

    def test_invented_cause_rejected(self):
        verdict = check_rewrite(self.SOURCE, "Driven by enterprise renewals, net revenue is $4,820,000, $220,000 above the $4.60M target.")
        self.assertIn("causal", verdict.reason)

    def test_invented_recommendation_and_forecast_rejected(self):
        self.assertIn("recommendation", check_rewrite(self.SOURCE, self.SOURCE + " We should raise prices.").reason)
        self.assertIn("forecast", check_rewrite(self.SOURCE, "Net revenue is $4,820,000, $220,000 above the $4.60M target and will keep rising.").reason)

    def test_direction_flip_rejected(self):
        verdict = check_rewrite(self.SOURCE, "Net revenue is $4,820,000, $220,000 below the $4.60M target.")
        self.assertEqual(verdict.reason, "direction changed")

    def test_invented_entity_rejected(self):
        verdict = check_rewrite(self.SOURCE, "Net revenue in EMEA is $4,820,000, $220,000 above the $4.60M target.")
        self.assertIn("entity", verdict.reason)

    def test_identifier_drift_rejected(self):
        source = "Q3 net revenue is $4,820,000."
        self.assertEqual(check_rewrite(source, "Q4 net revenue is $4,820,000.").reason, "identifier changed")
        self.assertTrue(check_rewrite(source, "Net revenue in Q3 is $4,820,000.").ok)

    def test_surface_lock(self):
        verdict = check_rewrite(self.SOURCE, "Net revenue is $4.82M, $220,000 above the $4.60M target.", ["$4,820,000"])
        self.assertFalse(verdict.ok)


class RecomputeTest(unittest.TestCase):
    def test_formula_grammar(self):
        self.assertEqual(evaluate("abs(actual - target)", [10, 12]), 2)
        self.assertAlmostEqual(evaluate("(actual - prior) * 100", [0.95, 0.93]), 2.0)
        with self.assertRaises(ValueError):
            evaluate("__import__('os')", [1, 2])

    def test_wrong_derived_value_fails_qa(self):
        script = compile_workbook(copy.deepcopy(PACK))
        cells = cell_index(PACK)
        self.assertEqual(validate_script(script, cells=cells), [])
        tampered = copy.deepcopy(script)
        for beat in tampered["beats"]:
            for claim in beat["claims"]:
                if claim.get("derived") and claim.get("formula") == "abs(actual - target)":
                    claim["value"] = 250000  # a model's "calculation"
                    beat["text"] = beat["text"].replace("$220,000", "$250,000")
                    beat["slots"]["delta"] = beat["slots"]["delta"].replace("$220,000", "$250,000")
        errors = validate_script(tampered, cells=cells)
        self.assertTrue(any("does not recompute" in error for error in errors), errors)

    def test_recompute_needs_numeric_operands(self):
        claim = {"value": 1, "formula": "actual - prior", "operands": [{"sheet": "S", "addr": "A1"}, {"sheet": "S", "addr": "A2"}]}
        self.assertIn("not numeric", recompute(claim, {("S", "A1"): "n/a", ("S", "A2"): 1}))


class NovaAssistTest(unittest.TestCase):
    def _exec_script(self):
        script = specialize_workbook(copy.deepcopy(PACK), "executive-business-review")
        script["beats"] = script["beats"][:4]
        for index, beat in enumerate(script["beats"], start=1):
            beat["ord"] = index
        return script

    def test_nova_summary_with_cited_numbers_ships(self):
        script = self._exec_script()
        kpi = next(beat for beat in script["beats"] if beat["layout"] == "versus-target")
        reply = json.dumps({"sentences": [{"text": "Net revenue is $4,820,000, $220,000 above the $4.60M target.", "beats": [kpi["ord"]]}]})
        with mock.patch.dict(os.environ, {**AWS_ENV, "GROUNDED_ASSIST_FEATURES": "summary"}, clear=True):
            out = assist_script(script, provider=nova([reply]))
        summary = [beat for beat in out["beats"] if beat.get("kind") == "summary"]
        self.assertEqual(len(summary), 1, out.get("assist_notes"))
        self.assertTrue(summary[0]["citations"])
        self.assertEqual(validate_script(out, cells=cell_index(PACK)), [])
        self.assertEqual(out["providers"]["assist"], "bedrock:amazon.nova-pro-v1:0")

    def test_nova_uncited_number_is_dropped(self):
        script = self._exec_script()
        kpi = next(beat for beat in script["beats"] if beat["layout"] == "versus-target")
        reply = json.dumps({"sentences": [
            {"text": "Net revenue grew 18% year over year to $4,820,000.", "beats": [kpi["ord"]]},
            {"text": "Margin reached 31%.", "beats": []},
        ]})
        with mock.patch.dict(os.environ, {**AWS_ENV, "GROUNDED_ASSIST_FEATURES": "summary"}, clear=True):
            out = assist_script(script, provider=nova([reply]))
        self.assertFalse(any(beat.get("kind") == "summary" for beat in out["beats"]))
        self.assertTrue(any("dropped" in note for note in out["assist_notes"]))

    def test_nova_causal_or_risk_claim_is_dropped(self):
        script = self._exec_script()
        kpi = next(beat for beat in script["beats"] if beat["layout"] == "versus-target")
        for text in (
            "Because of enterprise renewals, net revenue is $4,820,000.",
            "Net revenue is $4,820,000, which creates a risk for next quarter.",
            "Net revenue is $4,820,000, so we recommend more hiring.",
        ):
            self.assertIsNotNone(check_summary_sentence(text, [kpi]), text)

    def test_nova_polish_that_changes_numbers_is_reverted(self):
        script = compile_workbook(copy.deepcopy(PACK))
        replies = [json.dumps({"text": "Net revenue is $4.9M, well above target."})] * 10
        with mock.patch.dict(os.environ, {**AWS_ENV, "GROUNDED_ASSIST_FEATURES": "polish"}, clear=True):
            out = assist_script(script, provider=nova(replies))
        self.assertEqual([b["text"] for b in out["beats"]], [b["text"] for b in script["beats"]])

    def test_assist_is_inert_in_offline_mode(self):
        script = compile_workbook(copy.deepcopy(PACK))
        with mock.patch.dict(os.environ, {}, clear=True):
            out = assist_script(script)
        self.assertIs(out, script)

    def test_assist_reverts_if_qa_fails(self):
        script = compile_workbook(copy.deepcopy(PACK))

        class Sneaky:
            name, model_id = "bedrock", "amazon.nova-pro-v1:0"

            def complete(self, system, prompt, **kwargs):
                return InferenceResult(json.dumps({"text": "Approve two support hires."}), self.name, self.model_id)

        with mock.patch.dict(os.environ, {**AWS_ENV, "GROUNDED_ASSIST_FEATURES": "polish"}, clear=True):
            out = assist_script(script, provider=Sneaky())
        # Every beat either kept its text or gained a faithful rewrite; QA still passes.
        self.assertEqual(validate_script(out, cells=cell_index(PACK)), [])
        for old, new in zip(script["beats"], out["beats"]):
            if old["text"] != new["text"]:
                self.assertTrue(check_rewrite(old["text"], new["text"]).ok)


if __name__ == "__main__":
    unittest.main()
