"""Private object storage for the API. Policy + bucket are checked first.

Objects are never exposed through presigned URLs to browsers (the store is
not reachable from user networks); the API streams them after auth.
"""

from __future__ import annotations

import hashlib
from typing import Any, BinaryIO

from .settings import settings
from .validation import MAX_UPLOAD_BYTES, UploadTooLarge


def _config():
    from grounded.objectstore import StoreConfig

    return StoreConfig(
        settings.minio_endpoint,
        settings.minio_bucket,
        settings.minio_access_key,
        settings.minio_secret_key,
        settings.minio_region,
    )


def _client(client=None):
    from grounded.objectstore import StoreError, client as make

    try:
        return make(_config(), client)
    except StoreError as exc:
        raise RuntimeError(str(exc)) from exc


def _error_code(exc):
    try:
        return exc.response.get("Error", {}).get("Code")
    except AttributeError:
        return None


def ensure_bucket(client=None) -> None:
    s3 = _client(client)
    try:
        existing = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
    except Exception as exc:
        if _error_code(exc) in {"AccessDenied", "Forbidden"}:
            # Scoped credentials (e.g. a provisioned bucket): listing is
            # forbidden but the bucket exists, so there is nothing to do.
            return
        raise
    if settings.minio_bucket not in existing:
        s3.create_bucket(Bucket=settings.minio_bucket)


def put_bytes(key: str, data: bytes, content_type: str, client=None) -> None:
    from grounded.objectstore import write_args

    ensure_bucket(client)
    _client(client).put_object(Bucket=settings.minio_bucket, Key=key, Body=data, **write_args(content_type))


class HashingReader:
    """Wrap a file object: SHA-256 and size while boto3 streams it, cap enforced."""

    def __init__(self, raw: BinaryIO, limit: int = MAX_UPLOAD_BYTES) -> None:
        self.raw = raw
        self.limit = limit
        self.size = 0
        self._digest = hashlib.sha256()
        self.head = b""

    def read(self, size: int = -1) -> bytes:
        chunk = self.raw.read(size)
        if chunk:
            if len(self.head) < 64:
                self.head += chunk[: 64 - len(self.head)]
            self.size += len(chunk)
            if self.size > self.limit:
                raise UploadTooLarge(f"asset exceeds {self.limit} bytes")
            self._digest.update(chunk)
        return chunk

    @property
    def sha256(self) -> str:
        return self._digest.hexdigest()


def put_fileobj(key: str, fileobj, content_type: str, client=None) -> HashingReader:
    """Stream an upload to private storage in one pass, hashing as it goes."""
    from grounded.objectstore import write_args

    ensure_bucket(client)
    reader = fileobj if isinstance(fileobj, HashingReader) else HashingReader(fileobj)
    _client(client).upload_fileobj(reader, settings.minio_bucket, key, ExtraArgs=write_args(content_type))
    return reader


def delete_object(key: str, client=None) -> None:
    try:
        _client(client).delete_object(Bucket=settings.minio_bucket, Key=key)
    except Exception:  # noqa: BLE001 - best effort cleanup after a refused upload
        pass


def signed_url(key: str, expires: int = 300, client=None) -> str:
    """Kept for internal tooling only; the API never hands these to browsers."""
    return _client(client).generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.minio_bucket, "Key": key},
        ExpiresIn=expires,
    )


def object_size(key: str, client=None) -> int:
    try:
        head = _client(client).head_object(Bucket=settings.minio_bucket, Key=key)
    except Exception as exc:
        if _error_code(exc) in {"NoSuchKey", "NotFound", "404"}:
            raise FileNotFoundError(key) from exc
        raise
    return int(head["ContentLength"])


def open_range(key: str, start: int | None = None, end: int | None = None, client=None) -> Any:
    """Streaming body for the whole object or an inclusive byte span."""
    params: dict[str, Any] = {"Bucket": settings.minio_bucket, "Key": key}
    if start is not None:
        params["Range"] = f"bytes={start}-{'' if end is None else end}"
    try:
        return _client(client).get_object(**params)["Body"]
    except Exception as exc:
        if _error_code(exc) in {"NoSuchKey", "NotFound", "404"}:
            raise FileNotFoundError(key) from exc
        raise


def read_bytes(key: str, client=None) -> bytes:
    body = open_range(key, client=client)
    try:
        return body.read()
    finally:
        close = getattr(body, "close", None)
        if close:
            close()
