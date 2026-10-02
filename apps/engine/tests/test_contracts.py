"""Skill contracts are executable: runtime fields, checks, provenance."""

import copy
import io
import unittest

from openpyxl import Workbook

from grounded.compile_deck import CompileError
from grounded.contracts import CHECKS, run_checks, runtime_for
from grounded.dispatch import SourceBundle, SourceDoc, compile_bundle
from grounded.skill_registry import SkillRegistryError, execution_provenance, parse_contract, resolve_skill

BUSINESS_REVIEWS = ("weekly-ops-review", "finance-wbr", "half-year-business-review", "executive-business-review")
CRAFTS = ("workbook-analysis", "variance-analysis", "data-narration", "chart-selection", "source-visualization")


def workbook():
    wb = Workbook()
    ws = wb.active
    ws.title = "KPI"
    ws.append(["Weekly Ops Review"])
    ws.append(["Metric", "This week", "Last week", "Target"])
    ws.append(["Orders", 1200, 1100, 1150])
    ws.append(["Fill rate", 0.95, 0.93, 0.96])
    for addr in ("B4", "C4", "D4"):
        ws[addr].number_format = "0.0%"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class ContractTest(unittest.TestCase):
    def test_business_review_skills_declare_runtime(self):
        for skill_id in BUSINESS_REVIEWS:
            skill, crafts = resolve_skill(skill_id)
            runtime = runtime_for(skill, crafts)
            self.assertTrue(runtime.declared, skill_id)
            self.assertIn("workbook", runtime.accepts)
            for check in ("citations-present", "numbers-cited", "derived-lineage", "recompute-derived", "no-unsourced-causal"):
                self.assertIn(check, runtime.checks, f"{skill_id} {check}")

    def test_crafts_resolve_with_versions(self):
        provenance = execution_provenance("finance-wbr")
        for craft in CRAFTS:
            if craft in provenance["craft_versions"]:
                self.assertRegex(provenance["craft_versions"][craft], r"^\d+\.\d+\.\d+$")
        self.assertEqual(provenance["skill_version"], "1.1.0")
        self.assertEqual(len(provenance["skill_sha256"]), 64)
        self.assertIn("runtime", provenance)

    def test_unknown_check_fails_closed(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SKILL.md"
            path.write_text("# skill: rogue\nversion: 1.0.0\njob: x\n\n## Runtime\nruntime_checks:\n  - trust-the-model\n")
            with self.assertRaises(SkillRegistryError):
                runtime_for(parse_contract(path))

    def test_checks_registry_covers_contracts(self):
        for skill_id in BUSINESS_REVIEWS:
            skill, crafts = resolve_skill(skill_id)
            for check in runtime_for(skill, crafts).checks:
                self.assertIn(check, CHECKS)

    def test_compile_records_provenance_and_checks(self):
        for skill_id in ("weekly-ops-review", "finance-wbr", "half-year-business-review", "executive-business-review"):
            script = compile_bundle(skill_id=skill_id, title="t", bundle=SourceBundle(workbook=workbook(), workbook_asset="asset-1"))
            self.assertEqual(script["skill_id"], skill_id)
            self.assertTrue(script["provenance"]["checks_run"])
            self.assertIn("craft_versions", script["provenance"])
            for beat in script["beats"]:
                for cite in beat["citations"]:
                    self.assertEqual(cite.get("asset_id"), "asset-1")

    def test_inputs_required_enforced(self):
        with self.assertRaises(CompileError) as caught:
            compile_bundle(skill_id="finance-wbr", title="t", bundle=SourceBundle(segments=[{"t_start_ms": 0, "t_end_ms": 900, "text": "Hello."}]))
        self.assertIn("needs one of: workbook", "; ".join(caught.exception.errors))

    def test_mixed_sources_cite_their_own_assets(self):
        memo = {"title": "Memo", "title_block": "p1", "blocks": [
            {"id": "p2", "text": "Risk: carrier capacity is tight in the west.", "role": "risk"},
            {"id": "p3", "text": "Approve weekend shifts.", "role": "ask"},
        ]}
        bundle = SourceBundle(workbook=workbook(), workbook_asset="wb-1", documents=[SourceDoc("doc-1", "document", memo)])
        script = compile_bundle(skill_id="finance-wbr", title="t", bundle=bundle)
        doc_beats = [b for b in script["beats"] if any(c["kind"] == "document" for c in b["citations"])]
        self.assertEqual({b["layout"] for b in doc_beats}, {"risk", "ask"})
        self.assertTrue(all(c["asset_id"] == "doc-1" for b in doc_beats for c in b["citations"]))

    def test_executive_review_cap_from_contract(self):
        script = compile_bundle(skill_id="executive-business-review", title="t", bundle=SourceBundle(workbook=workbook(), workbook_asset="w"))
        self.assertLessEqual(len(script["beats"]), 6)

    def test_causal_language_in_numeric_beat_fails(self):
        script = compile_bundle(skill_id="finance-wbr", title="t", bundle=SourceBundle(workbook=workbook(), workbook_asset="w"))
        bad = copy.deepcopy(script)
        kpi = next(b for b in bad["beats"] if b["kind"] == "kpi")
        kpi["text"] += " This was driven by the holiday promotion."
        skill, crafts = resolve_skill("finance-wbr")
        errors = run_checks(bad, runtime_for(skill, crafts), None)
        self.assertTrue(any("unsourced explanation" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
