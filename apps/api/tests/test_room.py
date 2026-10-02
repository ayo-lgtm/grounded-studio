import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ranges import content_type, parse_range, slice_body

ROOM = Path(__file__).resolve().parents[1] / "app" / "room.html"
HOUSE = {
    "#f3f0e8",
    "#1a1814",
    "#5e584e",
    "#d3cdc2",
    "#1d3c34",
    "#7a2e2e",
    "#241f1a",
}


class RangeTest(unittest.TestCase):
    def test_absent_range_is_the_whole_object(self):
        self.assertIsNone(parse_range(None, 10))
        self.assertIsNone(parse_range("  ", 10))
        status, body, headers = slice_body(b"abcdef", None)
        self.assertEqual(status, 200)
        self.assertEqual(body, b"abcdef")
        self.assertEqual(headers["Accept-Ranges"], "bytes")
        self.assertNotIn("Content-Range", headers)

    def test_closed_and_open_ranges(self):
        self.assertEqual(parse_range("bytes=0-3", 10), (0, 3))
        self.assertEqual(parse_range("bytes=4-", 10), (4, 9))
        self.assertEqual(parse_range("bytes=0-", 10), (0, 9))
        self.assertEqual(parse_range("bytes=-3", 10), (7, 9))
        status, body, headers = slice_body(b"abcdefghij", "bytes=2-5")
        self.assertEqual(status, 206)
        self.assertEqual(body, b"cdef")
        self.assertEqual(headers["Content-Range"], "bytes 2-5/10")

    def test_end_past_the_object_is_clamped(self):
        self.assertEqual(parse_range("bytes=0-999", 4), (0, 3))
        self.assertEqual(parse_range("bytes=-50", 4), (0, 3))

    def test_unsatisfiable_and_garbage(self):
        for header in ("bytes=10-20", "bytes=10-", "items=0-1", "bytes=5-2", "bytes=-", "bytes=no-1"):
            with self.assertRaises(ValueError):
                parse_range(header, 10)
        with self.assertRaises(ValueError):
            slice_body(b"abcd", "bytes=9-9")

    def test_first_of_several_ranges(self):
        self.assertEqual(parse_range("bytes=1-2,4-5", 10), (1, 2))

    def test_content_types(self):
        self.assertEqual(content_type("briefings/a/deck.html"), "text/html; charset=utf-8")
        self.assertEqual(content_type("walkthrough.mp4"), "video/mp4")
        self.assertEqual(content_type("edl.json"), "application/json")
        self.assertEqual(content_type("voiceover.mp3"), "audio/mpeg")
        self.assertEqual(content_type("notes.bin"), "application/octet-stream")


class RoomPageTest(unittest.TestCase):
    def setUp(self):
        self.html = ROOM.read_text(encoding="utf-8")

    def test_house_colors_only(self):
        found = set(re.findall(r"#[0-9a-fA-F]{3,8}", self.html))
        self.assertEqual(found, HOUSE)

    def test_docs_page_does_not_load_a_cdn(self):
        main = (ROOM.parent / "main.py").read_text(encoding="utf-8")
        self.assertIn("docs_url=None", main)
        self.assertNotIn("jsdelivr", main)
        self.assertNotIn("swagger", main.lower())

    def test_no_foreign_chrome(self):
        lowered = self.html.lower()
        self.assertNotIn("linear-gradient", lowered)
        self.assertNotIn("box-shadow", lowered)
        self.assertIsNone(re.search(r"\binter\b", lowered))
        self.assertNotIn("https://", lowered)
        self.assertNotIn("http://", lowered)
        for match in re.findall(r"border-radius\s*:\s*([^;]+)", lowered):
            self.assertEqual(match.strip(), "0")

    def test_the_room_is_a_theater(self):
        self.assertIn("What should the room watch?", self.html)
        self.assertIn('id="stage"', self.html)
        self.assertIn('for="q">Ask', self.html)
        self.assertIn("Listening to the recording.", self.html)
        self.assertIn("Writing the script.", self.html)
        self.assertIn("Projecting the briefing.", self.html)
        self.assertIn("Walkthrough", self.html)
        self.assertIn("Weekly", self.html)
        self.assertIn("Launch", self.html)

    def test_root_is_wired_to_the_room(self):
        source = (ROOM.parent / "main.py").read_text(encoding="utf-8")
        self.assertIn('@app.get("/")', source)
        self.assertIn("HTMLResponse(_ROOM", source)
        self.assertIn('Cache-Control": "no-store"', source)
        self.assertIn("room.html", source)


if __name__ == "__main__":
    unittest.main()
