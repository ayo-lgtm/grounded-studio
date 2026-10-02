import tempfile
import unittest
from pathlib import Path

from grounded.narrate import NarrationError, narrate_script, split_chunks


class NarrateTest(unittest.TestCase):
    def test_split_keeps_short_text_whole(self):
        self.assertEqual(split_chunks("Hello world."), ["Hello world."])

    def test_split_breaks_long_text(self):
        long_text = " ".join(f"Sentence {i}." for i in range(500))
        chunks = split_chunks(long_text, limit=1000)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 1000 for chunk in chunks))

    def test_narration_requires_preprovisioned_local_model(self):
        script = {"beats": [{"ord": 1, "text": "Private narration."}]}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(NarrationError):
                narrate_script(
                    script,
                    Path(tmp) / "voiceover.mp3",
                    model_path=str(Path(tmp) / "missing.onnx"),
                )

    def test_narrate_rejects_empty_script_before_any_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(NarrationError):
                narrate_script(
                    {"beats": []},
                    Path(tmp) / "voiceover.mp3",
                    model_path=str(Path(tmp) / "missing.onnx"),
                )


if __name__ == "__main__":
    unittest.main()
