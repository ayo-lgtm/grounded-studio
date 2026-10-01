import unittest

from app.storage import ensure_bucket, put_bytes, read_bytes, signed_url


class FakeDenied(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class FakeS3:
    def __init__(self, buckets=(), error=None):
        self.buckets = list(buckets)
        self.error = error
        self.created = []
        self.puts = {}

    def list_buckets(self):
        if self.error is not None:
            raise self.error
        return {"Buckets": [{"Name": name} for name in self.buckets]}

    def create_bucket(self, Bucket):
        self.created.append(Bucket)

    def put_object(self, Bucket, Key, Body, ContentType):
        self.puts[Key] = (Bucket, Body, ContentType)

    def generate_presigned_url(self, operation, Params, ExpiresIn):
        return f"https://store.test/{Params['Key']}?exp={ExpiresIn}"

    def get_object(self, Bucket, Key):
        _bucket, body, content_type = self.puts[Key]

        class _Body:
            def read(self):
                return body

            def close(self):
                pass

        return {"Body": _Body(), "ContentType": content_type}


class StorageTest(unittest.TestCase):
    def test_denied_list_proceeds_without_create(self):
        s3 = FakeS3(error=FakeDenied("AccessDenied"))
        ensure_bucket(client=s3)
        self.assertEqual(s3.created, [])

    def test_missing_bucket_created(self):
        s3 = FakeS3(buckets=["other"])
        ensure_bucket(client=s3)
        self.assertEqual(len(s3.created), 1)

    def test_present_bucket_skipped(self):
        from app.storage import settings as _s

        s3 = FakeS3(buckets=[_s.minio_bucket])
        ensure_bucket(client=s3)
        self.assertEqual(s3.created, [])

    def test_unexpected_error_propagates(self):
        with self.assertRaises(RuntimeError):
            ensure_bucket(client=FakeS3(error=RuntimeError("boom")))

    def test_put_and_signed_url(self):
        s3 = FakeS3(error=FakeDenied("Forbidden"))
        put_bytes("k/v.mp4", b"data", "video/mp4", client=s3)
        self.assertIn("k/v.mp4", s3.puts)
        url = signed_url("k/v.mp4", client=s3)
        self.assertIn("k/v.mp4", url)
        self.assertEqual(read_bytes("k/v.mp4", client=s3), b"data")


if __name__ == "__main__":
    unittest.main()
