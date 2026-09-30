"""Read back what the API stored.

Render cuts the real capture, so the worker downloads the recording
asset from the S3-compatible store before rendering. boto3 stays a lazy
import so unit tests run without AWS deps.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

_CHUNK = 1024 * 1024


class StoreError(Exception):
    pass


class S3Client(Protocol):
    def get_object(self, **kwargs: Any) -> dict[str, Any]: ...


def download_file(
    endpoint: str,
    bucket: str,
    key: str,
    access_key: str,
    secret_key: str,
    dest: Path,
    client: S3Client | None = None,
) -> Path:
    """Download one store object to dest. Returns dest."""
    if client is None:
        try:
            import boto3
        except ImportError as exc:
            raise StoreError("boto3 is not installed") from exc
        try:
            client = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name="us-east-1",
            )
        except Exception as exc:
            raise StoreError(f"cannot create store client: {exc}") from exc
    try:
        body = client.get_object(Bucket=bucket, Key=key)["Body"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as handle:
            for chunk in iter(lambda: body.read(_CHUNK), b""):
                handle.write(chunk)
    except StoreError:
        raise
    except Exception as exc:
        raise StoreError(f"store download failed: {exc}") from exc
    return dest
