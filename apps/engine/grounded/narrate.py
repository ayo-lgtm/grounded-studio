"""Voiceover narration via Amazon Polly.

Beats are synthesized in order and concatenated to one MP3 per briefing.
Narration reads the accepted script aloud — it never adds words.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Protocol

MAX_CHUNK_CHARS = 3000

VOICES = {"en": "Joanna", "fr": "Celine", "de": "Vicki", "es": "Lucia"}


class PollyError(Exception):
    pass


class PollyClient(Protocol):
    def synthesize_speech(self, **kwargs: Any) -> dict[str, Any]: ...


def split_chunks(text: str, limit: int = MAX_CHUNK_CHARS) -> list[str]:
    """Split narration text into Polly-sized chunks on sentence boundaries."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > limit:
            if current:
                chunks.append(current)
                current = ""
            for index in range(0, len(sentence), limit):
                chunks.append(sentence[index : index + limit])
        elif len(current) + len(sentence) + 1 > limit:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return chunks


def voice_for(language: str) -> str:
    return VOICES.get((language or "en").lower(), "Joanna")


def _client_or_create(client: PollyClient | None, region: str) -> PollyClient:
    if client is not None:
        return client
    try:
        import boto3  # lazy: engine stays dependency-light for tests
    except ImportError as exc:
        raise PollyError("boto3 is not installed") from exc
    try:
        return boto3.client("polly", region_name=region)  # type: ignore[return-value]
    except Exception as exc:
        raise PollyError(f"cannot create polly client: {exc}") from exc


def synthesize(text: str, voice_id: str, region: str, client: PollyClient | None = None) -> bytes:
    polly = _client_or_create(client, region)
    audio = b""
    try:
        for chunk in split_chunks(text):
            response = polly.synthesize_speech(
                Text=chunk, OutputFormat="mp3", VoiceId=voice_id
            )
            stream = response.get("AudioStream")
            data = stream.read() if stream is not None else b""
            if not data:
                raise PollyError("polly returned empty audio")
            audio += data
    except PollyError:
        raise
    except Exception as exc:
        raise PollyError(f"polly synthesize failed: {exc}") from exc
    return audio


def narrate_script(
    script: dict[str, Any],
    out_path: Path,
    region: str | None = None,
    client: PollyClient | None = None,
) -> Path:
    """Write the briefing voiceover MP3. Raises PollyError on failure."""
    region = region or os.environ.get("AWS_REGION", "us-east-1")
    voice_id = os.environ.get("NARRATION_VOICE") or voice_for(script.get("language", "en"))
    texts = [str(beat.get("text") or "") for beat in script.get("beats") or []]
    full = "\n".join(text for text in texts if text.strip())
    if not full:
        raise PollyError("script has no narration text")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(synthesize(full, voice_id, region, client))
    return out_path
