import unittest
from pathlib import Path
import tempfile

from worker.store import StoreError, download_file


class FakeBody:
    def __init__(self, data):
        self._data = data

    def read(self, n=-1):
        if n is None or n < 0:
            n = len(self._data)
        chunk, self._data = self._data[:n], self._data[n:]
        return chunk


class FakeS3:
    def __init__(self, data=b""):
        self.data = data
        self.requested = None

    def get_object(self, **kwargs):
        self.requested = kwargs
        return {"Body": FakeBody(self.data)}


class BrokenS3:
    def get_object(self, **kwargs):
        raise RuntimeError("no store here")


class StoreTest(unittest.TestCase):
    def test_download_writes_bytes_in_chunks(self):
        payload = bytes((i % 251 for i in range(3 * 1024 * 1024 + 7)))
        s3 = FakeS3(payload)
        with tempfile.TemporaryDirectory() as tmp:
            dest = download_file(
                "http://store:9000", "grounded", "briefings/x/upload.mp4",
                "ak", "sk", Path(tmp) / "sub" / "upload.mp4", client=s3,
            )
            self.assertEqual(dest.read_bytes(), payload)
        self.assertEqual(s3.requested, {"Bucket": "grounded", "Key": "briefings/x/upload.mp4"})

    def test_client_failure_raises_store_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(StoreError):
                download_file(
                    "http://store:9000", "b", "k", "a", "s",
                    Path(tmp) / "f.mp4", client=BrokenS3(),
                )

    def test_real_client_failure_raises_store_error(self):
        # No injectable client: without boto3 this raises for the missing
        # dep; with boto3 it raises when the bogus endpoint is unreachable.
        # Either way the caller sees StoreError, never a raw exception.
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(StoreError):
                download_file(
                    "http://127.0.0.1:9", "b", "k", "a", "s", Path(tmp) / "f.mp4"
                )


if __name__ == "__main__":
    unittest.main()
