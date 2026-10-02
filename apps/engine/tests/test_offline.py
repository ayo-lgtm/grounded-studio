"""Fail-closed offline profile: no public chat, TTS, ASR, or object store."""

import json
import os
import re
import tempfile
import unittest
from pathlib import Path

from grounded.brand import brand_lock
from grounded.catalog import load_catalog, load_crafts
from grounded.compile_deck import CompileError
from grounded.compile_recording import compile_recording
from grounded.compile_sources import compile_uploaded
from grounded.continuity import apply_carry
from grounded.egress import (
    assert_object_store,
    assert_private_model,
    health_report,
    is_private_host,
    is_public_host,
    EgressError,
)
from grounded.formats import scale_filter
from grounded import house
from grounded.knowledge import embed, search_knowledge
from grounded.quality import clipping_warning, gate_script, refine_actions
from grounded.render_recording import timeline

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
APPS = ROOT / "apps"

FORBIDDEN_CALLS = (
    "bedrock-runtime",
    "jsdelivr",
    "api.openai.com",
    "urlopen",
)


class EgressTest(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("EGRESS_MODE", None)
        os.environ.pop("MODEL_BASE_URL", None)

    def test_private_and_public_hosts(self):
        self.assertTrue(is_private_host("127.0.0.1"))
        self.assertTrue(is_private_host("store"))
        self.assertTrue(is_private_host("minio.grounded.internal"))
        self.assertFalse(is_public_host("minio.grounded.internal"))
        # Railway is a third-party hosted runtime; its private DNS is not ours.
        self.assertFalse(is_private_host("minio.railway.internal"))
        for host in (
            "t3.storageapi.dev",
            "s3.us-east-1.amazonaws.com",
            "api.openai.com",
        ):
            self.assertTrue(is_public_host(host), host)

    def test_offline_refuses_public_object_store(self):
        os.environ["EGRESS_MODE"] = "offline"
        with self.assertRaises(EgressError):
            assert_object_store("https://t3.storageapi.dev")
        assert_object_store("http://store:9000")
        assert_object_store("http://127.0.0.1:9000")

    def test_health_reports_offline_or_blocked(self):
        os.environ["EGRESS_MODE"] = "offline"
        offline = health_report(True, "http://minio.grounded.internal:9000")
        self.assertEqual(offline["egress"], "offline")
        self.assertTrue(offline["ok"])
        self.assertEqual(offline["chat"], "retrieval")
        self.assertEqual(offline["narration"], "local")
        self.assertEqual(offline["transcription"], "local")
        self.assertEqual(offline["object_store"], "private")
        blocked = health_report(True, "https://t3.storageapi.dev")
        self.assertEqual(blocked["egress"], "blocked")
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["object_store"], "public-refused")
        os.environ["EGRESS_MODE"] = "aws-in-region"
        retired = health_report(True, "https://t3.storageapi.dev")
        self.assertFalse(retired["ok"])
        self.assertEqual(retired["egress"], "misconfigured")

    def test_public_model_url_is_refused(self):
        with self.assertRaises(EgressError):
            assert_private_model("https://api.openai.com/v1")


class CatalogAndSkillsTest(unittest.TestCase):
    def test_catalog_is_offline_and_has_no_scenario_ids(self):
        skills = load_catalog(ROOT / "skills")
        ids = {item["id"] for item in skills}
        self.assertIn("continuous-take-demo", ids)
        self.assertIn("narration-room-mix", ids)
        self.assertIn("offline-quality-gate", ids)
        self.assertTrue(all(item["offline"] is True for item in skills))
        self.assertFalse(any(str(item["id"]).startswith("scenario-") for item in skills))
        crafts = {item["id"] for item in load_crafts(ROOT / "skills")}
        self.assertIn("carry-boundary", crafts)
        self.assertGreaterEqual(len(skills), 75)

    def test_knowledge_search_finds_a_local_skill(self):
        hits = search_knowledge("continuous take survivor", root=ROOT)
        self.assertTrue(hits)
        self.assertTrue(any("continuous-take" in hit["path"] for hit in hits))
        self.assertEqual(len(embed("offline retrieval")), 768)


class ContinuityAndDecksTest(unittest.TestCase):
    def test_walkthrough_carries_and_slideshow_does_not(self):
        fixture = json.loads((FIXTURES / "walkthrough.json").read_text(encoding="utf-8"))
        walk = compile_recording(fixture["segments"], skill_id="product-walkthrough")
        self.assertEqual(walk["edit"]["continuity"]["mode"], "carry-boundary")
        self.assertEqual(len(walk["edit"]["continuity"]["boundaries"]), 2)
        slides = compile_recording(fixture["segments"], skill_id="still-sequence-slideshow")
        self.assertNotIn("continuity", slides["edit"])

    def test_carry_timeline_holds_the_outgoing_frame(self):
        script = {
            "beats": [],
            "edit": {
                "cuts": [
                    {"screen": "Settings", "src_in_ms": 0, "src_out_ms": 1000, "text": "Open."},
                    {"screen": "Billing", "src_in_ms": 1000, "src_out_ms": 2000, "text": "Pay."},
                ]
            },
        }
        apply_carry(script)
        kinds = [item["type"] for item in timeline(script)]
        self.assertEqual(kinds[0], "cut")
        self.assertIn("carry", kinds)
        self.assertNotIn("chapter", kinds)

    def test_executive_deck_caps_slides_and_empty_kpi_fails(self):
        raw = (FIXTURES / "weekly.json").read_bytes()
        script = compile_uploaded(skill_id="wbr-executive", title="Monday", workbook=raw)
        self.assertLessEqual(len(script["beats"]), 6)
        self.assertEqual(script["renderer"], "deck")
        self.assertEqual(script["brand"]["paper"], house.PAPER)
        pack = json.loads(raw)
        pack["kpis"][0]["value"] = None
        with self.assertRaises(CompileError):
            compile_uploaded(
                skill_id="wbr-executive",
                title="Monday",
                workbook=json.dumps(pack).encode(),
            )
        pack = json.loads(raw)
        pack["risks"] = [
            {"sheet": "Notes", "addr": "A3", "text": "Collections slipped."},
            {"sheet": "Notes", "addr": "A4", "text": "A second risk."},
        ]
        with self.assertRaises(CompileError):
            compile_uploaded(
                skill_id="wbr-executive",
                title="Monday",
                workbook=json.dumps(pack).encode(),
            )

    def test_quality_gate_and_formats(self):
        report = gate_script({"skill_id": "weekly-ops-review", "beats": [{"ord": 1, "text": "Hi", "citations": []}]})
        self.assertEqual(report["status"], "fail")
        actions = refine_actions({"errors": ["missing citation"], "warnings": ["clipped audio"]})
        self.assertTrue(all(action["where"] == "local" for action in actions))
        self.assertEqual(clipping_warning(-0.2), "clipped audio (max_volume -0.2 dB)")
        self.assertIsNone(clipping_warning(-3.0))
        vf = scale_filter("9:16")
        self.assertIn("pad=", vf)
        self.assertIn("0x241f1a", vf)
        self.assertEqual(brand_lock()["paper"], house.PAPER)


if __name__ == "__main__":
    unittest.main()
