"""Local transcription with faster-whisper. No cloud ASR and no runtime download."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class LocalTranscribeError(Exception):
    pass


def transcribe_file(path: Path, model_name: str, cache_dir: str) -> list[dict[str, Any]]:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise LocalTranscribeError(
            "faster-whisper is not installed; public ASR is disabled"
        ) from exc
    cache = cache_dir or "/opt/whisper"
    try:
        model = WhisperModel(
            model_name or "base",
            device="cpu",
            compute_type="int8",
            download_root=cache,
            local_files_only=True,
        )
    except TypeError:
        model = WhisperModel(
            model_name or "base",
            device="cpu",
            compute_type="int8",
            download_root=cache,
        )
    except Exception as exc:
        raise LocalTranscribeError(
            f"faster-whisper weights are not preloaded ({exc})"
        ) from exc
    try:
        segments, _info = model.transcribe(str(path), language="en", vad_filter=True)
        rows = list(segments)
    except Exception as exc:
        raise LocalTranscribeError(f"local transcription failed: {exc}") from exc
    parsed: list[dict[str, Any]] = []
    for segment in rows:
        text = str(getattr(segment, "text", "") or "").strip()
        if not text:
            continue
        start = float(getattr(segment, "start", 0.0))
        end = float(getattr(segment, "end", start))
        parsed.append(
            {
                "t_start_ms": int(start * 1000),
                "t_end_ms": int(max(end, start + 0.2) * 1000),
                "text": text,
            }
        )
    if not parsed:
        raise LocalTranscribeError("local transcription returned no speech")
    return parsed
