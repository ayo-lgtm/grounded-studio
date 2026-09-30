import unittest
from pathlib import Path
import tempfile

from grounded.narrate import narrate_script, split_chunks, voice_for


class FakeStream:
    def __init__(self, data):
        self._data = data

    def read(self):
        return self._data


class FakePolly:
    def __init__(self, marker=b"AUDIO"):
        self.marker = marker
        self.texts = []

    def synthesize_speech(self, **kwargs):
        self.texts.append(kwargs["Text"])
        return {"AudioStream": FakeStream(self.marker)}


SCRIPT = {
    "language": "en",
    "beats": [
        {"ord": 1, "text": "Open Settings from the left nav."},
        {"ord": 2, "text": "Choose Billing, then Payment method."},
    ],
}


class NarrateTest(unittest.TestCase):
    def test_split_keeps_short_text_whole(self):
        self.assertEqual(split_chunks("Hello world."), ["Hello world."])

    def test_split_breaks_long_text(self):
        long_text = " ".join(f"Sentence {i}." for i in range(500))
        chunks = split_chunks(long_text, limit=1000)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 1000 for chunk in chunks))

    def test_voice_for_language(self):
        self.assertEqual(voice_for("en"), "Joanna")
        self.assertEqual(voice_for("fr"), "Celine")
        self.assertEqual(voice_for("xx"), "Joanna")

    def test_narrate_writes_mp3(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = narrate_script(SCRIPT, Path(tmp) / "voiceover.mp3", client=FakePolly())
            data = out.read_bytes()
        self.assertTrue(data.startswith(b"AUDIO"))

    def test_narrate_rejects_empty_script(self):
        from grounded.narrate import PollyError

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PollyError):
                narrate_script({"language": "en", "beats": []}, Path(tmp) / "v.mp3", client=FakePolly())


if __name__ == "__main__":
    unittest.main()
