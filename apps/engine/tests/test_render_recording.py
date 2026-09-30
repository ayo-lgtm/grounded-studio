import unittest

from grounded.render_recording import _font, _vtt_clock, timeline


class RenderRecordingTest(unittest.TestCase):
    def test_missing_font_returns_none(self):
        self.assertIsNone(_font("no-such-font-xyz.ttf"))

    def test_vtt_clock_format(self):
        self.assertEqual(_vtt_clock(0), "00:00:00.000")
        self.assertEqual(_vtt_clock(3723123), "01:02:03.123")

    def test_timeline_chapters_and_cuts(self):
        script = {
            "beats": [],
            "edit": {
                "cuts": [
                    {"screen": "Settings", "src_in_ms": 0, "src_out_ms": 1000, "text": "Open."},
                    {"screen": "Settings", "src_in_ms": 1000, "src_out_ms": 2000, "text": "More."},
                    {"screen": "Billing", "src_in_ms": 2000, "src_out_ms": 3000, "text": "Pay."},
                ]
            },
        }
        items = timeline(script)
        kinds = [item["type"] for item in items]
        self.assertEqual(kinds, ["chapter", "cut", "cut", "chapter", "cut"])
        self.assertEqual(items[0]["title"], "Settings")
        self.assertEqual(items[3]["title"], "Billing")


if __name__ == "__main__":
    unittest.main()
