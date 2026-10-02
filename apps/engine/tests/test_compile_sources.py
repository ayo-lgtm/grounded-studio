import json
import unittest
from pathlib import Path

from grounded.compile_deck import CompileError
from grounded.compile_sources import compile_uploaded
from grounded.ingest import parse_docx
from grounded.qa import validate_script

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _docx_bytes():
    from test_ingest import _docx, _run

    return _docx([
        _run("Pricing change"),
        _run("Pipeline closed at $4.82M."),
        _run("Approve the collections standup."),
    ])


class CompileSourcesTest(unittest.TestCase):
    def test_docx_on_default_walkthrough_skill_becomes_a_brief(self):
        script = compile_uploaded(
            skill_id="product-walkthrough",
            title="Ignored",
            document=_docx_bytes(),
        )
        self.assertEqual(script["skill_id"], "leadership-brief")
        self.assertEqual(script["renderer"], "deck")
        self.assertEqual(validate_script(script), [])
        self.assertEqual(script["beats"][-1]["layout"], "ask")
        self.assertEqual([beat["text"] for beat in script["beats"]].count("Pricing change"), 1)

    def test_walkthrough_without_a_transcript_still_asks_to_transcribe(self):
        with self.assertRaises(CompileError) as caught:
            compile_uploaded(skill_id="product-walkthrough", title="Walk", segments=[])
        self.assertIn("transcribe first", caught.exception.errors)

    def test_transcript_compiles_as_the_briefing_skill(self):
        script = compile_uploaded(
            skill_id="sop-training",
            title="Weekly close",
            segments=[{"t_start_ms": 0, "t_end_ms": 2000, "text": "Export the pack."}],
        )
        self.assertEqual(script["skill_id"], "sop-training")
        self.assertEqual(script["title"], "Weekly close")
        self.assertEqual(validate_script(script, duration_ms=script["source_duration_ms"]), [])

    def test_workbook_json_compiles_the_weekly_deck(self):
        raw = (FIXTURES / "weekly.json").read_bytes()
        script = compile_uploaded(
            skill_id="weekly-ops-review",
            title="Monday",
            workbook=raw,
        )
        self.assertEqual(script["skill_id"], "weekly-ops-review")
        self.assertIn("versus-target", [beat["layout"] for beat in script["beats"]])
        self.assertEqual(validate_script(script), [])

    def test_workbook_wins_when_the_skill_is_weekly(self):
        pack = json.loads((FIXTURES / "weekly.json").read_text(encoding="utf-8"))
        script = compile_uploaded(
            skill_id="weekly-ops-review",
            title="Monday",
            workbook=json.dumps(pack).encode(),
            document=_docx_bytes(),
        )
        self.assertEqual(script["skill_id"], "weekly-ops-review")

    def test_bad_workbook_is_rejected(self):
        with self.assertRaises(CompileError) as caught:
            compile_uploaded(
                skill_id="weekly-ops-review",
                title="Monday",
                workbook=b"not-json",
            )
        self.assertTrue(any(term in caught.exception.errors[0] for term in ("CSV", "workbook")))


if __name__ == "__main__":
    unittest.main()
