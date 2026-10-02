"""Local-only voiceover narration using Piper.

Grounded Studio never sends narration text to a cloud TTS provider.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

MAX_CHUNK_CHARS = 3000


class NarrationError(RuntimeError):
    pass


def split_chunks(text: str, limit: int = MAX_CHUNK_CHARS) -> list[str]:
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


def narrate_script(
    script: dict[str, Any],
    out_path: Path,
    *,
    piper_bin: str = "piper",
    model_path: str = "",
) -> Path:
    """Write narration with a pre-provisioned local Piper voice model."""
    texts = [str(beat.get("text") or "") for beat in script.get("beats") or []]
    full = "\n".join(text for text in texts if text.strip())
    if not full:
        raise NarrationError("script has no narration text")

    model = Path(model_path)
    if not model_path or not model.exists():
        raise NarrationError("PIPER_MODEL_PATH must point to a pre-provisioned local voice model")
    binary = shutil.which(piper_bin) or (piper_bin if Path(piper_bin).exists() else None)
    if not binary:
        raise NarrationError("local Piper binary is not installed")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "voiceover.wav"
        try:
            proc = subprocess.run(
                [str(binary), "--model", str(model), "--output_file", str(wav)],
                input=full,
                text=True,
                capture_output=True,
                timeout=600,
            )
        except Exception as exc:
            raise NarrationError(f"local Piper failed: {exc}") from exc
        if proc.returncode != 0 or not wav.exists():
            tail = (proc.stderr or proc.stdout or "").strip()[-800:]
            raise NarrationError(f"local Piper failed: {tail or 'no audio produced'}")

        if out_path.suffix.lower() == ".wav":
            shutil.copyfile(wav, out_path)
            return out_path

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise NarrationError("ffmpeg is required to convert local Piper WAV to MP3")
        proc = subprocess.run(
            [ffmpeg, "-y", "-i", str(wav), "-codec:a", "libmp3lame", str(out_path)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 or not out_path.exists():
            raise NarrationError("ffmpeg failed to encode local narration")
    return out_path
