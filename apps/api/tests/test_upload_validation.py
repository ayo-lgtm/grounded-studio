import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import validation
from app.validation import is_allowed_kind, read_limited, sanitize_filename


def _reader(chunks):
    it = iter(chunks)

    async def _read(_size):
        return next(it, b"")

    return _read


class ValidationTest(unittest.TestCase):
    def test_sanitize_strips_directories(self):
        self.assertEqual(sanitize_filename("../../etc/passwd"), "passwd")
        self.assertEqual(sanitize_filename("..\\..\\secret.txt"), "secret.txt")

    def test_sanitize_fallbacks(self):
        self.assertEqual(sanitize_filename(None), "upload.bin")
        self.assertEqual(sanitize_filename(""), "upload.bin")
        self.assertEqual(sanitize_filename(".."), "upload.bin")

    def test_kind_allowlist_matches_schema_enum(self):
        for kind in ("recording", "workbook", "document", "attachment"):
            self.assertTrue(is_allowed_kind(kind))
        self.assertFalse(is_allowed_kind("video"))
        self.assertFalse(is_allowed_kind(""))

    def test_read_limited_joins_chunks(self):
        data = asyncio.run(read_limited(_reader([b"ab", b"cd", b""])))
        self.assertEqual(data, b"abcd")

    def test_read_limited_rejects_oversize(self):
        old = validation.MAX_UPLOAD_BYTES
        validation.MAX_UPLOAD_BYTES = 3
        try:
            with self.assertRaises(validation.UploadTooLarge):
                asyncio.run(read_limited(_reader([b"ab", b"cd"])))
        finally:
            validation.MAX_UPLOAD_BYTES = old


if __name__ == "__main__":
    unittest.main()
