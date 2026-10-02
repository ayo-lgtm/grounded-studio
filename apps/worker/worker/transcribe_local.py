"""Local-only transcription.

The model must be provisioned on disk before the worker starts. This module
never downloads a model and never sends audio over the network.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class LocalTranscribeError(RuntimeError):
    pass


def transcribe_file(
    media_path: Path,
    model_path: str,
    *,
    device: str = "cpu",
    language: str | None = None,
) -> list[dict[str, Any]]:
    model_dir = Path(model_path)
    if not model_path or not model_dir.exists():
        raise LocalTranscribeError(
            "WHISPER_MODEL_PATH must point to a pre-provisioned local faster-whisper model"
        )
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise LocalTranscribeError("faster-whisper is not installed") from exc

    try:
        model = WhisperModel(str(model_dir), device=device, local_files_only=True)
        segments, _info = model.transcribe(
            str(media_path),
            language=language or None,
            vad_filter=True,
        )
        out: list[dict[str, Any]] = []
        for segment in segments:
            text = str(segment.text or "").strip()
            if not text:
                continue
            out.append(
                {
                    "t_start_ms": int(float(segment.start) * 1000),
                    "t_end_ms": int(float(segment.end) * 1000),
                    "text": text,
                }
            )
        if not out:
            raise LocalTranscribeError("local transcription produced no segments")
        return out
    except LocalTranscribeError:
        raise
    except Exception as exc:
        raise LocalTranscribeError(f"local transcription failed: {exc}") from exc
