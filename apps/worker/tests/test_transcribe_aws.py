import unittest

from worker.transcribe_aws import TranscribeError, parse_transcribe_json

PAYLOAD = {
    "results": {
        "items": [
            {
                "start_time": "0.0",
                "end_time": "0.5",
                "type": "pronunciation",
                "alternatives": [{"content": "Open"}],
            },
            {
                "start_time": "0.5",
                "end_time": "1.2",
                "type": "pronunciation",
                "alternatives": [{"content": "Settings"}],
            },
            {"type": "punctuation", "alternatives": [{"content": "."}]},
            {
                "start_time": "4.7",
                "end_time": "8.6",
                "type": "pronunciation",
                "alternatives": [{"content": "Billing"}],
            },
        ]
    }
}


class TranscribeParseTest(unittest.TestCase):
    def test_groups_words_and_sentence_breaks(self):
        segments = parse_transcribe_json(PAYLOAD)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0], {"t_start_ms": 0, "t_end_ms": 1200, "text": "Open Settings."})
        self.assertEqual(segments[1]["t_start_ms"], 4700)

    def test_rejects_bad_payload(self):
        with self.assertRaises(TranscribeError):
            parse_transcribe_json({})

    def test_empty_items_yield_no_segments(self):
        self.assertEqual(parse_transcribe_json({"results": {"items": []}}), [])


if __name__ == "__main__":
    unittest.main()
