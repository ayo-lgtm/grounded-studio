import tempfile
import unittest
from pathlib import Path

from grounded.skill_registry import (
    SkillRegistryError,
    execution_provenance,
    parse_contract,
    resolve_skill,
)


class SkillRegistryTest(unittest.TestCase):
    def test_contract_parser_reads_version_and_crafts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SKILL.md"
            path.write_text(
                "# skill: finance-wbr\n"
                "version: 2.1.0\n"
                "job: Review numbers.\n\n"
                "crafts_required:\n"
                "  - workbook-analysis\n"
                "  - chart-selection when workbook is present\n",
                encoding="utf-8",
            )
            contract = parse_contract(path)
        self.assertEqual(contract.id, "finance-wbr")
        self.assertEqual(contract.version, "2.1.0")
        self.assertEqual(contract.crafts, ("workbook-analysis", "chart-selection"))

    def test_repo_finance_skill_resolves_craft_versions(self):
        skill, crafts = resolve_skill("finance-wbr")
        self.assertEqual(skill.id, "finance-wbr")
        self.assertTrue(crafts)
        self.assertIn("workbook-analysis", {craft.id for craft in crafts})
        provenance = execution_provenance("finance-wbr")
        self.assertEqual(provenance["skill_version"], skill.version)
        self.assertIn("workbook-analysis", provenance["craft_versions"])

    def test_unknown_skill_fails_closed(self):
        with self.assertRaises(SkillRegistryError):
            resolve_skill("not-a-real-skill")


if __name__ == "__main__":
    unittest.main()
