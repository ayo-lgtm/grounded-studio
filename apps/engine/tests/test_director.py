import copy
import json
import unittest

from grounded.compile_deck import cell_index, compile_workbook
from grounded.compile_recording import compile_recording
from grounded.director import (
    check_claims_shown,
    check_coverage,
    check_surfaces,
    direct,
    revise,
    surface_locks,
)
from grounded.qa import validate_script

PACK = {
    "title": {"text": "Weekly ops", "sheet": "Cover", "addr": "A1"},
    "period": {"text": "Week 32", "sheet": "Cover", "addr": "A2"},
    "kpis": [
        {
            "label": "Net revenue", "sheet": "KPI", "addr": "B12",
            "value": 4820000, "unit": "usd",
            "target": 4600000, "target_sheet": "KPI", "target_addr": "B13",
            "display": "$4,820,000", "target_display": "$4.60M",
            "required": True,
        },
        {
            "label": "Refunds", "sheet": "KPI", "addr": "B14",
            "value": 220000, "unit": "usd",
            "display": "$220000",
            "required": True,
        },
    ],
    "movers": [
        {
            "label": "Enterprise", "sheet": "KPI", "addr": "B20",
            "value": 3100000, "prior": 2900000, "prior_addr": "C20",
            "display": "$3,100,000", "prior_display": "$2,900,000",
        },
    ],
    "risks": [{"sheet": "Notes", "addr": "A5", "text": "Churn ticked up in March."}],
    "asks": [{"sheet": "Notes", "addr": "A6", "text": "Approve two support hires."}],
}


class FakeModel:
    """Stands in for any InferenceProvider (local or Bedrock/Nova)."""

    name = "fake"
    model_id = "fake-model"

    def __init__(self, texts):
        self._texts = list(texts)
        self.calls = 0

    def complete(self, system, prompt, **kwargs):
        from grounded.providers.base import InferenceResult

        self.calls += 1
        return InferenceResult(text=self._texts.pop(0), provider=self.name, model_id=self.model_id)


FakeConverse = FakeModel


def _script():
    return compile_workbook(copy.deepcopy(PACK))


def _cells():
    return cell_index(PACK)


class DirectorTest(unittest.TestCase):
    def test_display_strings_shown_verbatim(self):
        script = _script()
        self.assertIn("$4,820,000", script["beats"][1]["text"])
        self.assertIn("$220000", script["beats"][2]["text"])
        table = script["beats"][3]["slots"]["rows"][0]
        self.assertEqual(table["this_week"], "$3,100,000")
        self.assertEqual(table["last_week"], "$2,900,000")
        self.assertEqual(validate_script(script, cells=_cells()), [])

    def test_director_approves_clean_cut(self):
        result = direct(_script(), PACK, _cells())
        self.assertEqual(result["errors"], [])
        notes = " ".join(result["notes"])
        self.assertIn("cover -> 3 evidence beats -> 2 closing beats", notes)
        self.assertIn("Emphasis: beat 2 carries the largest swing", notes)
        self.assertIn("Locked 5 authored number surfaces", notes)
        self.assertIn("all 5 required points present", notes)

    def test_tampered_surface_fails_director_but_passes_qa(self):
        script = _script()
        script["beats"][2]["text"] = "Refunds is $220,000."
        script["beats"][2]["slots"]["actual"] = "$220,000"
        self.assertEqual(validate_script(script, cells=_cells()), [])
        errors = check_surfaces(script, surface_locks(PACK))
        self.assertEqual(len(errors), 1)
        self.assertIn("not shown verbatim", errors[0])

    def test_dropped_beat_breaks_coverage(self):
        script = _script()
        del script["beats"][3]
        errors = check_coverage(PACK, script)
        self.assertEqual(len(errors), 1)
        self.assertIn("Enterprise", errors[0])

    def test_hidden_claim_breaks_director_but_passes_qa(self):
        script = _script()
        script["beats"][2]["text"] = "Refunds are fine."
        script["beats"][2]["slots"]["actual"] = ""
        self.assertEqual(validate_script(script, cells=_cells()), [])
        errors = check_claims_shown(script)
        self.assertEqual(len(errors), 1)
        self.assertIn("hides cited claim", errors[0])

    def test_focus_reorders_deck(self):
        script = _script()
        before = [beat["text"] for beat in script["beats"]]
        result = revise(script, "focus refunds", PACK, _cells())
        self.assertTrue(result["applied"])
        self.assertEqual(
            [beat["text"] for beat in result["script"]["beats"]],
            [before[0], before[2], before[1], before[3], before[4], before[5]],
        )
        self.assertEqual(
            [beat["ord"] for beat in result["script"]["beats"]], [1, 2, 3, 4, 5, 6]
        )
        self.assertEqual([beat["text"] for beat in script["beats"]], before)

    def test_focus_no_match_refuses_without_touching_script(self):
        script = _script()
        result = revise(script, "focus zebras", PACK, _cells())
        self.assertFalse(result["applied"])
        self.assertIs(result["script"], script)

    def test_drop_refuses(self):
        script = _script()
        result = revise(script, "drop the risk slide", PACK, _cells())
        self.assertFalse(result["applied"])
        self.assertIs(result["script"], script)
        self.assertIn("never drops", result["notes"][0])

    def test_focus_recording_refuses_to_protect_sync(self):
        script = compile_recording(
            [
                {"t_start_ms": 0, "t_end_ms": 2000, "text": "Open Settings.", "screen": "Settings"},
                {"t_start_ms": 2000, "t_end_ms": 5000, "text": "Choose Billing.", "screen": "Billing"},
            ]
        )
        result = revise(script, "focus billing")
        self.assertFalse(result["applied"])
        self.assertIs(result["script"], script)
        self.assertIn("unsync", result["notes"][0])

    def test_direct_recording_reads_pacing(self):
        script = compile_recording(
            [
                {"t_start_ms": 0, "t_end_ms": 2000, "text": "Open Settings.", "screen": "Settings"},
                {"t_start_ms": 2000, "t_end_ms": 5000, "text": "Choose Billing.", "screen": "Billing"},
            ]
        )
        result = direct(script)
        self.assertEqual(result["errors"], [])
        self.assertTrue(any("Pacing: 2 cuts" in note for note in result["notes"]))

    def test_polish_applies_clean_rephrase(self):
        client = FakeConverse(
            [json.dumps({"text": "Net revenue is $4,820,000 — $220,000 above the $4.60M target."})]
        )
        result = revise(_script(), "polish beat 2", PACK, _cells(), client=client)
        self.assertTrue(result["applied"])
        self.assertIn("— $220,000 above", result["script"]["beats"][1]["text"])

    def test_polish_rejects_dropped_number(self):
        client = FakeConverse(
            [json.dumps({"text": "Net revenue hit $4,820,000 against a $4.60M target."})]
        )
        script = _script()
        result = revise(script, "polish beat 2", PACK, _cells(), client=client)
        self.assertFalse(result["applied"])
        self.assertEqual(result["script"]["beats"][1]["text"], script["beats"][1]["text"])
        self.assertIn("numbers drifted", result["notes"][0])

    def test_polish_rejects_reformatted_surface(self):
        client = FakeConverse(
            [json.dumps({"text": "Net revenue is $4.82M, $220,000 above the $4.60M target."})]
        )
        script = _script()
        result = revise(script, "polish beat 2", PACK, _cells(), client=client)
        self.assertFalse(result["applied"])
        self.assertEqual(result["script"]["beats"][1]["text"], script["beats"][1]["text"])
        self.assertIn("dropped surface", result["notes"][0])

    def test_polish_without_client_keeps_verbatim(self):
        script = _script()
        result = revise(script, "polish beat 2", PACK, _cells())
        self.assertFalse(result["applied"])
        self.assertEqual(result["script"]["beats"][1]["text"], script["beats"][1]["text"])
        self.assertIn("kept verbatim", result["notes"][0])

    def test_unknown_instruction_refuses_with_usage(self):
        script = _script()
        result = revise(script, "make it jazzier", PACK, _cells())
        self.assertFalse(result["applied"])
        self.assertIs(result["script"], script)
        self.assertIn("focus", result["notes"][0])


if __name__ == "__main__":
    unittest.main()
