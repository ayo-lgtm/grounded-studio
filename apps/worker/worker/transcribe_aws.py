"""Transcription via AWS Transcribe.

Audio is read from the app's S3-compatible store, staged to a real S3
bucket (Transcribe requires one), transcribed in-region, and written back
as transcript segments. Credentials come from the standard boto3 chain —
on EC2 that means the instance profile, never checked-in keys.
"""

from __future__ import annotations

import time
import urllib.request
from typing import Any

MAX_SEGMENT_MS = 8000


class TranscribeError(Exception):
    pass


def parse_transcribe_json(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse a Transcribe GetTranscriptionJob transcript payload into segments."""
    try:
        items = payload["results"]["items"]
    except (KeyError, TypeError) as exc:
        raise TranscribeError(f"unexpected transcribe payload: {exc}") from exc
    segments: list[dict[str, Any]] = []
    words: list[str] = []
    start_ms: int | None = None
    end_ms = 0
    def flush() -> None:
        nonlocal words, start_ms, end_ms
        text = " ".join(words).replace(" .", ".").replace(" ,", ",").strip()
        if words and start_ms is not None and text:
            segments.append({"t_start_ms": start_ms, "t_end_ms": end_ms, "text": text})
        words, start_ms = [], None
    for item in items:
        alternatives = item.get("alternatives") or []
        content = str((alternatives[0].get("content") if alternatives else "") or "")
        if not content:
            continue
        if item.get("type") == "punctuation":
            if words:
                words[-1] = words[-1] + content
                if content in (".", "?", "!"):
                    flush()
            continue
        try:
            item_start = int(float(item["start_time"]) * 1000)
            item_end = int(float(item["end_time"]) * 1000)
        except (KeyError, TypeError, ValueError):
            continue
        if start_ms is None:
            start_ms = item_start
        if item_start - end_ms > MAX_SEGMENT_MS and words:
            flush()
            start_ms = item_start
        words.append(content)
        end_ms = item_end
        if end_ms - (start_ms or 0) >= MAX_SEGMENT_MS:
            flush()
    flush()
    return segments


def _boto3():
    try:
        import boto3  # lazy: importable without AWS deps in unit tests
    except ImportError as exc:
        raise TranscribeError("boto3 is not installed") from exc
    return boto3


def stage_from_store(
    minio_endpoint: str,
    bucket: str,
    key: str,
    access_key: str,
    secret_key: str,
    dest_bucket: str,
    dest_key: str,
    region: str,
) -> str:
    """Copy an object from the S3-compatible store to real S3. Returns the S3 URI."""
    boto3 = _boto3()
    try:
        store = boto3.client(
            "s3",
            endpoint_url=minio_endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
        )
        body = store.get_object(Bucket=bucket, Key=key)["Body"].read()
        s3 = boto3.client("s3", region_name=region)
        s3.put_object(Bucket=dest_bucket, Key=dest_key, Body=body)
    except Exception as exc:
        raise TranscribeError(f"audio staging failed: {exc}") from exc
    return f"s3://{dest_bucket}/{dest_key}"


def transcribe_media(
    media_uri: str,
    job_name: str,
    language: str,
    region: str,
    timeout_s: int = 1800,
    poll_s: int = 5,
) -> dict[str, Any]:
    """Run a Transcribe job and return the parsed transcript payload."""
    boto3 = _boto3()
    try:
        client = boto3.client("transcribe", region_name=region)
        client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": media_uri},
            LanguageCode=language,
            Settings={"ShowSpeakerLabels": False},
        )
        waited = 0
        while True:
            job = client.get_transcription_job(TranscriptionJobName=job_name)["TranscriptionJob"]
            status = job["TranscriptionJobStatus"]
            if status == "COMPLETED":
                uri = job["Transcript"]["TranscriptFileUri"]
                break
            if status == "FAILED":
                reason = job.get("FailureReason", "unknown")
                raise TranscribeError(f"transcribe job failed: {reason}")
            if waited >= timeout_s:
                raise TranscribeError("transcribe job timed out")
            time.sleep(poll_s)
            waited += poll_s
        with urllib.request.urlopen(uri, timeout=60) as response:
            import json as _json

            return _json.loads(response.read().decode("utf-8"))
    except TranscribeError:
        raise
    except Exception as exc:
        raise TranscribeError(f"transcribe failed: {exc}") from exc
