import unittest

from worker.compile_walkthrough import stub_from_transcript
from worker.qa import validate_script


class QaTest(unittest.TestCase):
    def test_valid_recording_script(self):
        script = stub_from_transcript(
            [{"t_start_ms": 0, "t_end_ms": 1200, "text": "Click Settings."}]
        )
        self.assertEqual(validate_script(script), [])

    def test_rejects_missing_citation(self):
        script = {
            "beats": [{"ord": 1, "kind": "step", "text": "Invented button", "citations": []}]
        }
        self.assertTrue(validate_script(script))


if __name__ == "__main__":
    unittest.main()
