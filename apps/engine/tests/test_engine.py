import json
import tempfile
import unittest
from pathlib import Path

from grounded.compile_deck import CompileError, cell_index, compile_document, compile_workbook
from grounded.compile_recording import compile_delta, compile_recording
from grounded.source_screen import slices
from grounded.demo import run
from grounded.localize import localize
from grounded.numbers import format_usd, parse_numbers
from grounded.qa import validate_script

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _weekly():
    return json.loads((FIXTURES / "weekly.json").read_text(encoding="utf-8"))


class EngineTest(unittest.TestCase):
    def test_money_roundtrip(self):
        self.assertEqual(parse_numbers(format_usd(4820000)), [4820000])
        self.assertEqual(parse_numbers(format_usd(220000)), [220000])
        self.assertEqual(parse_numbers("41.2%"), [41.2])

    def test_weekly_deck_cites_cells(self):
        pack = _weekly()
        script = compile_workbook(pack)
        errors = validate_script(script, cells=cell_index(pack))
        self.assertEqual(errors, [])
        self.assertEqual(
            [beat["layout"] for beat in script["beats"]],
            ["cover", "versus-target", "versus-target", "movers", "risk", "ask"],
        )
        html = self._render(script)
        self.assertIn("KPI!B12", html)
        self.assertIn("#f3f0e8", html)
        self.assertNotIn("linear-gradient", html)
        self.assertNotIn("Inter", html)

    def test_empty_kpi_blocks_compile(self):
        pack = _weekly()
        pack["kpis"][0]["value"] = None
        with self.assertRaises(CompileError):
            compile_workbook(pack)

    def test_invented_layout_and_number_fail(self):
        pack = _weekly()
        script = compile_workbook(pack)
        script["beats"][1]["layout"] = "globe"
        errors = validate_script(script, cells=cell_index(pack))
        self.assertTrue(any("layout" in error for error in errors))
        script = compile_workbook(pack)
        script["beats"][1]["text"] = "Net revenue is $9.99M."
        errors = validate_script(script, cells=cell_index(pack))
        self.assertTrue(any("without a cited claim" in error for error in errors))

    def test_recording_drops_filler_and_gaps(self):
        fixture = json.loads((FIXTURES / "walkthrough.json").read_text(encoding="utf-8"))
        script = compile_recording(fixture["segments"], title=fixture["title"])
        texts = [beat["text"] for beat in script["beats"]]
        self.assertNotIn("um", texts)
        self.assertEqual(len(script["edit"]["cuts"]), 3)
        spans = [(cut["src_in_ms"], cut["src_out_ms"]) for cut in script["edit"]["cuts"]]
        self.assertNotIn((3200, 3900), spans)
        self.assertTrue(all(cut["src_in_ms"] >= 4700 or cut["src_out_ms"] <= 3200 for cut in script["edit"]["cuts"]))
        self.assertEqual(validate_script(script, duration_ms=script["source_duration_ms"]), [])

    def test_localize_locks_numbers(self):
        script = compile_workbook(_weekly())
        ok = localize(script, {2: "Le revenu net est de $4.82M, $220,000 au-dessus de l'objectif de $4.60M."}, "fr")
        self.assertEqual(validate_script(ok), [])
        with self.assertRaises(CompileError):
            localize(script, {2: "Net revenue is $5.10M."}, "fr")

    def test_leadership_uses_verbatim_sentences(self):
        doc = json.loads((FIXTURES / "leadership.json").read_text(encoding="utf-8"))
        script = compile_document(doc, "leadership-brief")
        evidence = next(beat for beat in script["beats"] if beat["kind"] == "evidence")
        self.assertEqual(evidence["text"], doc["blocks"][1]["text"])
        self.assertEqual(evidence["layout"], "statement")
        self.assertEqual(validate_script(script), [])

    def test_source_holds_through_dead_air(self):
        fixture = json.loads((FIXTURES / "walkthrough.json").read_text(encoding="utf-8"))
        parts = slices(fixture["segments"], 14800)
        self.assertEqual(parts[0], (0, 4700, "Settings"))
        self.assertEqual(parts[1][2], "Billing")
        self.assertEqual(parts[-1][2], "Card on file")

    def test_delta_appends_after_the_parent_recording(self):
        fixture = json.loads((FIXTURES / "walkthrough.json").read_text(encoding="utf-8"))
        parent = compile_recording(fixture["segments"], title=fixture["title"])
        merged = compile_delta(
            parent,
            [{"t_start_ms": 0, "t_end_ms": 3600, "text": "A receipt toggle now sits under Billing.", "screen": "Billing"}],
        )
        new_cut = merged["edit"]["cuts"][-1]
        self.assertEqual(new_cut["src_in_ms"], parent["source_duration_ms"])
        self.assertGreater(merged["source_duration_ms"], parent["source_duration_ms"])

    def test_demo_without_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = run(Path(tmp), with_video=False)
        self.assertTrue(all(item["status"] != "failed" for item in results))
        self.assertTrue(any(item["status"] == "blocked" for item in results))


    def _render(self, script):
        from grounded.render_deck import render_deck

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck.html"
            render_deck(script, path)
            return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
