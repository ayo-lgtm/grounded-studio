"""Ask-me demos: smarter matching, screen reading, training courses, narrated video.

All fixtures are synthetic. Nothing here touches a network.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from grounded.chat import REFUSAL, answer_grounded
from grounded.compile_deck import CompileError, compile_training
from grounded.providers.base import InferenceResult, ProviderError
from grounded.retrieval import Candidate, concept, prepare, rank, stem, tokens
from grounded.screen_text import clean_lines, read_screen

HAVE_FFMPEG = shutil.which("ffmpeg") is not None
HAVE_TESSERACT = shutil.which("tesseract") is not None

DEMO = [
    {"text": "To find your invoices, open Billing in the left sidebar and choose Invoices.",
     "citation": {"kind": "recording", "t_start_ms": 12000, "t_end_ms": 19000, "asset_id": "v1"}, "source": "speech"},
    {"text": "Invite a teammate from Settings, then Members, then Invite.",
     "citation": {"kind": "recording", "t_start_ms": 30000, "t_end_ms": 37000, "asset_id": "v1"}, "source": "speech"},
    {"text": "Billing · Invoices · Download PDF",
     "citation": {"kind": "recording", "t_start_ms": 14000, "t_end_ms": 18000, "asset_id": "v1", "on_screen": True}, "source": "screen"},
    {"text": "Exports are limited to 50,000 rows per file.", "answer": "Exports are limited to 50,000 rows per file.",
     "citation": {"kind": "document", "block_id": "b7", "asset_id": "kb1"}, "source": "document"},
]


class RetrievalTest(unittest.TestCase):
    def test_stemming_and_synonyms(self):
        self.assertEqual(stem("billing"), "bill")
        self.assertEqual(concept(stem("invoices")), concept(stem("bills")))
        self.assertNotEqual(concept(stem("invoices")), concept(stem("teammates")))
        self.assertIn("login", tokens("How do I log in?"))

    def test_everyday_words_find_the_right_moment(self):
        result = answer_grounded({"beats": []}, "Where are my bills?", passages=DEMO, use_provider=False)
        self.assertFalse(result["refused"])
        self.assertEqual(result["citations"][0]["kind"], "recording")
        self.assertIn(result["citations"][0]["t_start_ms"], (12000, 14000))

    def test_knowledge_base_answers_directly(self):
        result = answer_grounded({"beats": []}, "How many rows can I export?", passages=DEMO, use_provider=False)
        self.assertFalse(result["refused"])
        self.assertEqual(result["source"], "document")
        self.assertIn("50,000", result["text"])

    def test_screen_text_is_cited_as_on_screen(self):
        result = answer_grounded({"beats": []}, "Where is the Download PDF button?", passages=DEMO, use_provider=False)
        self.assertFalse(result["refused"])
        self.assertEqual(result["source"], "screen")
        self.assertTrue(result["citations"][0]["on_screen"])

    def test_related_moments_are_offered(self):
        result = answer_grounded({"beats": []}, "How do I download my invoices?", passages=DEMO, use_provider=False)
        self.assertFalse(result["refused"])
        clips = [result["citations"][0]] + [m["citation"] for m in result["moments"]]
        self.assertTrue(any(c.get("kind") == "recording" for c in clips))
        for moment in result["moments"]:
            self.assertEqual(moment["citation"]["kind"], "recording")

    def test_one_shared_word_is_not_an_answer(self):
        for question in ("What is the CEO salary?", "Which invoices did legal dispute in 2019 and why?", "Tell me a joke"):
            result = answer_grounded({"beats": []}, question, passages=DEMO, use_provider=False)
            self.assertTrue(result["refused"], question)
            self.assertEqual(result["text"], REFUSAL)

    def test_semantic_embedder_can_rescue_a_paraphrase_but_answer_stays_verbatim(self):
        cands = prepare([Candidate(id="a", text="Exports are limited to 50,000 rows per file.", citation={"kind": "document", "block_id": "b"}, source="document")])

        def embed(texts):
            return [[1.0, 0.0] for _ in texts]  # everything "means" the same

        hits = rank("biggest spreadsheet I can pull out", cands, embedder=embed)
        self.assertTrue(hits and hits[0].accepted)
        self.assertEqual(hits[0].candidate.text, "Exports are limited to 50,000 rows per file.")

    def test_broken_embedder_falls_back_to_lexical(self):
        cands = prepare([Candidate(id="a", text="Invite a teammate from Settings.", citation={"kind": "document", "block_id": "b"}, source="document")])

        def embed(texts):
            raise RuntimeError("model missing")

        hits = rank("invite teammate", cands, embedder=embed)
        self.assertTrue(hits[0].accepted)
        self.assertIsNone(hits[0].semantic)

    def test_model_may_pick_a_passage_but_not_add_facts(self):
        class Picker:
            name, model_id = "local", "local-instruct"

            def complete(self, system, prompt, **kwargs):
                ident = next(line.split("]")[0][1:] for line in prompt.splitlines() if "50,000" in line)
                return InferenceResult(json.dumps({"id": ident, "text": "You can export up to 50,000 rows per file, or 80,000 on Pro."}), self.name, self.model_id)

        result = answer_grounded({"beats": []}, "What is the export limit?", passages=DEMO, provider=Picker())
        self.assertEqual(result["text"], "Exports are limited to 50,000 rows per file.")
        self.assertFalse(result["phrased"])

    def test_model_saying_none_answers_refuses_partial_match(self):
        class Nobody:
            name, model_id = "local", "local-instruct"

            def complete(self, system, prompt, **kwargs):
                return InferenceResult('{"id": null}', self.name, self.model_id)

        result = answer_grounded({"beats": []}, "Can I invite a contractor to billing approvals?", passages=DEMO, provider=Nobody())
        self.assertTrue(result["refused"])


class ScreenTextTest(unittest.TestCase):
    def test_clean_lines_drops_noise_and_never_adds(self):
        lines = clean_lines(["  Billing   Invoices \n|| ~ \n=-=\nDownload PDF\nDownload PDF"])
        self.assertEqual(lines, ["Billing Invoices", "Download PDF"])

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_read_screen_spans_follow_the_frames(self):
        class FakeOCR:
            calls = 0

            def extract_text(self, data, fmt):
                self.calls += 1
                return ["Members · Invite"] if self.calls > 2 else ["Billing", "Invoices"]

        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "demo.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=320x240:d=8", "-pix_fmt", "yuv420p", str(video)], check=True)
            spans = read_screen(video, FakeOCR(), interval=2.0, duration_ms=8000)
        self.assertEqual([s["text"] for s in spans], ["Billing · Invoices", "Members · Invite"])
        self.assertEqual(spans[0]["t_start_ms"], 0)
        self.assertEqual(spans[1]["t_start_ms"], 4000)
        self.assertEqual(spans[-1]["t_end_ms"], 8000)

    @unittest.skipUnless(HAVE_FFMPEG and HAVE_TESSERACT, "ffmpeg/tesseract not installed")
    def test_local_ocr_reads_a_synthetic_screen(self):
        from grounded.providers.local import LocalOCR

        font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if not Path(font).is_file():
            self.skipTest("DejaVu font not installed")
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "screen.mp4"
            subprocess.run(
                ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=white:s=1280x720:d=4",
                 "-vf", f"drawtext=fontfile={font}:text='Billing Invoices':fontsize=72:fontcolor=black:x=100:y=300",
                 "-pix_fmt", "yuv420p", str(video)],
                check=True,
            )
            spans = read_screen(video, LocalOCR(), interval=2.0, duration_ms=4000)
        self.assertTrue(spans)
        self.assertIn("Invoices", spans[0]["text"])


HANDBOOK = {
    "title": "Welcome to Northwind",
    "title_block": "b0",
    "blocks": [
        {"id": "b0", "text": "Welcome to Northwind", "role": "evidence"},
        {"id": "b1", "text": "Your first week", "heading_path": "Your first week", "role": "evidence"},
        {"id": "b2", "text": "1. Collect your laptop from the IT desk on floor 3.", "role": "evidence"},
        {"id": "b3", "text": "2. Sign in with your badge and set a password.", "role": "evidence"},
        {"id": "b4", "text": "3. Request access to the Ledgerly workspace.", "role": "ask"},
        {"id": "b5", "text": "4. Book a 30 minute intro with your manager.", "role": "evidence"},
        {"id": "b6", "text": "Expense claims over $500 need manager approval.", "role": "evidence"},
        {"id": "b7", "text": "Never share your badge with anyone.", "role": "risk"},
    ],
}


class TrainingTest(unittest.TestCase):
    def test_steps_sections_notes_and_checkpoints(self):
        script = compile_training(HANDBOOK, "training-course")
        kinds = [b["kind"] for b in script["beats"]]
        self.assertEqual(kinds[0], "cover")
        self.assertIn("section", kinds)
        self.assertEqual(script["course"]["steps"], 4)
        self.assertGreaterEqual(script["course"]["checkpoints"], 1)
        steps = [b for b in script["beats"] if b["kind"] == "step"]
        self.assertEqual([b["slots"]["step"] for b in steps], [1, 2, 3, 4])
        self.assertIn("Request access", steps[2]["text"])  # an instruction, not an ask
        self.assertIn("risk", kinds)

    def test_every_beat_is_cited_and_checkpoint_answers_are_quoted(self):
        script = compile_training(HANDBOOK, "onboarding-guide")
        texts = {b["text"] for b in HANDBOOK["blocks"]}
        for beat in script["beats"]:
            self.assertTrue(beat["citations"], beat)
            if beat["kind"] == "checkpoint":
                self.assertIn(beat["slots"]["answer"], texts)
                self.assertEqual(len(beat["citations"]), 2)

    def test_numbers_are_claimed(self):
        script = compile_training(HANDBOOK, "training-course")
        expense = next(b for b in script["beats"] if "$500" in b["text"])
        self.assertTrue(expense["claims"])

    def test_empty_document_is_refused(self):
        with self.assertRaises(CompileError):
            compile_training({"title": "x", "blocks": []}, "training-course")


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
class NarratedVideoTest(unittest.TestCase):
    def test_deck_becomes_a_chaptered_video_with_captions(self):
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest("Pillow not installed")
        from grounded.render_video import render_narrated_video

        script = compile_training(HANDBOOK, "onboarding-guide")
        with tempfile.TemporaryDirectory() as tmp:
            out = render_narrated_video(script, Path(tmp))
            self.assertTrue(out["video"].is_file())
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-of", "json", str(out["video"])],
                capture_output=True, text=True, check=True,
            )
            streams = json.loads(probe.stdout)["streams"]
            video = next(s for s in streams if s["codec_type"] == "video")
            self.assertEqual((video["width"], video["height"]), (1920, 1080))
            self.assertTrue(any(s["codec_type"] == "audio" for s in streams))
            edl = json.loads(out["edl"].read_text())
            chapters = [i for i in edl["items"] if i["type"] == "chapter"]
            self.assertEqual(len(chapters), len(script["beats"]))
            self.assertEqual([c["ord"] for c in chapters], [b["ord"] for b in script["beats"]])
            starts = [c["out_in_ms"] for c in chapters]
            self.assertEqual(starts, sorted(starts))
            vtt = out["vtt"].read_text()
            self.assertTrue(vtt.startswith("WEBVTT"))
            self.assertIn("The answer:", vtt)
            self.assertFalse(out["narrated"])

    def test_failed_voice_fails_the_render(self):
        from grounded.render_video import VideoError, render_narrated_video

        def speak(text, dest):
            raise OSError("voice missing")

        script = compile_training(HANDBOOK, "training-course")
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(VideoError):
            render_narrated_video(script, Path(tmp), speak=speak)


class OnnxEmbeddingsTest(unittest.TestCase):
    def test_missing_model_fails_closed(self):
        from grounded.providers.local import LocalOnnxEmbeddings

        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ProviderError):
            LocalOnnxEmbeddings(model_dir=tmp)
        with mock.patch.dict(os.environ, {"GROUNDED_EMBEDDING_MODEL_DIR": ""}), self.assertRaises(ProviderError):
            LocalOnnxEmbeddings()

    def test_tiny_local_model_embeds_and_normalizes(self):
        try:
            import numpy as np
            import onnx
            from onnx import TensorProto, helper
            from tokenizers import Tokenizer
            from tokenizers.models import WordLevel
            from tokenizers.pre_tokenizers import Whitespace
            import onnxruntime  # noqa: F401
        except ImportError:
            self.skipTest("onnx/onnxruntime/tokenizers not installed")
        from grounded.providers.local import LocalOnnxEmbeddings

        vocab = {"[PAD]": 0, "[UNK]": 1, "invoice": 2, "bill": 3, "teammate": 4, "probe": 5}
        table = np.zeros((len(vocab), 4), dtype=np.float32)
        table[2] = table[3] = [1, 0, 0, 0]  # invoice ~ bill
        table[4] = [0, 1, 0, 0]
        table[5] = [0, 0, 1, 0]
        table[1] = [0, 0, 0, 1]
        graph = helper.make_graph(
            [helper.make_node("Gather", ["emb", "input_ids"], ["last_hidden_state"])],
            "tiny",
            [helper.make_tensor_value_info("input_ids", TensorProto.INT64, ["b", "s"]),
             helper.make_tensor_value_info("attention_mask", TensorProto.INT64, ["b", "s"])],
            [helper.make_tensor_value_info("last_hidden_state", TensorProto.FLOAT, ["b", "s", 4])],
            [helper.make_tensor("emb", TensorProto.FLOAT, table.shape, table.flatten().tolist())],
        )
        model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
        model.ir_version = 8
        with tempfile.TemporaryDirectory() as tmp:
            onnx.save(model, os.path.join(tmp, "model.onnx"))
            tok = Tokenizer(WordLevel(vocab, unk_token="[UNK]"))
            tok.pre_tokenizer = Whitespace()
            tok.save(os.path.join(tmp, "tokenizer.json"))
            embedder = LocalOnnxEmbeddings(model_dir=tmp)
            a, b, c = embedder.embed(["invoice", "bill", "teammate"])
        self.assertEqual(embedder.dims, 4)
        self.assertAlmostEqual(sum(x * y for x, y in zip(a, b)), 1.0, places=5)
        self.assertAlmostEqual(sum(x * y for x, y in zip(a, c)), 0.0, places=5)


if __name__ == "__main__":
    unittest.main()
