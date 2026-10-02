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
    def put_object(self, **kwargs: Any) -> dict[str, Any]: ...


def download_file(
    endpoint: str,
    bucket: str,
    key: str,
    access_key: str,
    secret_key: str,
    dest: Path,
    region: str = "us-east-1",
    client: S3Client | None = None,
) -> Path:
    """Download one store object to dest. Returns dest."""
    client = _store_client(endpoint, access_key, secret_key, region, client, bucket)
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


ARTIFACT_KINDS = {
    "walkthrough.mp4": "video",
    "deck.html": "deck",
    "captions.vtt": "captions",
    "edl.json": "edl",
    "storyboard.html": "storyboard",
    "guide.md": "guide",
    "voiceover.mp3": "voiceover",
    "source.mp4": "source",
    "mix.json": "mix",
    "placement.json": "placement",
    "quality.json": "quality",
    "cell_audit.csv": "cell-audit",
    "calculation_audit.csv": "calculation-audit",
    "data_quality.json": "data-quality",
    "provenance.json": "provenance",
}

CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".vtt": "text/vtt",
    ".json": "application/json",
    ".html": "text/html",
    ".md": "text/markdown",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".csv": "text/csv",
}


def artifact_kind(filename: str) -> str | None:
    """Render output kind, or None for inputs and scratch (never persisted)."""
    return ARTIFACT_KINDS.get(filename)


def content_type_for(suffix: str) -> str:
    return CONTENT_TYPES.get(suffix.lower(), "application/octet-stream")


def upload_file(
    endpoint: str,
    bucket: str,
    key: str,
    access_key: str,
    secret_key: str,
    src: Path,
    content_type: str,
    region: str = "us-east-1",
    client: S3Client | None = None,
) -> int:
    """Upload one file, streaming from disk. Returns bytes written."""
    from grounded.objectstore import write_args

    s3 = _store_client(endpoint, access_key, secret_key, region, client, bucket)
    try:
        with open(src, "rb") as handle:
            s3.put_object(Bucket=bucket, Key=key, Body=handle, **write_args(content_type))
    except Exception as exc:
        raise StoreError(f"store upload failed: {exc}") from exc
    return src.stat().st_size


def _store_client(
    endpoint: str,
    access_key: str,
    secret_key: str,
    region: str,
    client: S3Client | None,
    bucket: str = "",
):
    from grounded.objectstore import StoreConfig, StoreError as _Err, client as _client

    try:
        return _client(StoreConfig(endpoint, bucket, access_key, secret_key, region), client)
    except _Err as exc:
        raise StoreError(str(exc)) from exc
