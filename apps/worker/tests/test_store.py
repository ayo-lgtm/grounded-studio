import unittest
from pathlib import Path
import tempfile

from worker.store import (
    StoreError,
    artifact_kind,
    content_type_for,
    download_file,
    upload_file,
)


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


class PutS3:
    def __init__(self):
        self.puts = {}

    def put_object(self, **kwargs):
        body = kwargs["Body"]
        self.puts[kwargs["Key"]] = (kwargs["Bucket"], body.read(), kwargs["ContentType"])
        return {}


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

    def test_artifact_kinds(self):
        self.assertEqual(artifact_kind("walkthrough.mp4"), "video")
        self.assertEqual(artifact_kind("deck.html"), "deck")
        self.assertEqual(artifact_kind("captions.vtt"), "captions")
        self.assertEqual(artifact_kind("voiceover.mp3"), "voiceover")
        self.assertIsNone(artifact_kind("upload.mp4"))
        self.assertIsNone(artifact_kind("script.json"))
        self.assertIsNone(artifact_kind("list.txt"))

    def test_content_types(self):
        self.assertEqual(content_type_for(".mp4"), "video/mp4")
        self.assertEqual(content_type_for(".HTML"), "text/html")
        self.assertEqual(content_type_for(".zzz"), "application/octet-stream")

    def test_upload_streams_file(self):
        s3 = PutS3()
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "walkthrough.mp4"
            src.write_bytes(b"fake-video-bytes")
            size = upload_file(
                "http://store:9000", "b", "k/v.mp4", "a", "s",
                src, "video/mp4", client=s3,
            )
        self.assertEqual(size, 16)
        self.assertEqual(s3.puts["k/v.mp4"], ("b", b"fake-video-bytes", "video/mp4"))

    def test_upload_failure_raises_store_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "f.mp4"
            src.write_bytes(b"x")
            with self.assertRaises(StoreError):
                upload_file("http://store:9000", "b", "k", "a", "s", src, "video/mp4",
                            client=BrokenS3())

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
