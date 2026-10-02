"""Transcript JSON parsing.

The AWS Transcribe upload path is disabled. Workers transcribe with
local faster-whisper and never stage audio to a public bucket.
"""

from __future__ import annotations

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


def stage_from_store(*_args: Any, **_kwargs: Any) -> str:
    raise TranscribeError(
        "public AWS Transcribe staging is disabled; use local faster-whisper"
    )


def transcribe_media(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    raise TranscribeError(
        "public AWS Transcribe is disabled; use local faster-whisper"
    )
