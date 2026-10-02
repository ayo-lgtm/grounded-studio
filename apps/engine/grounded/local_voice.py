"""Local narration. Piper or Kokoro on the box, then a room mix.

Loudness is normalized, peaks are limited, and a source bed is ducked
12 dB under the voice. Public TTS is not a fallback.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

LOUDNESS = "loudnorm=I=-16:TP=-1.5:LRA=11,alimiter=limit=0.89"
ROOM = "aecho=0.8:0.9:12:0.08"
DUCK_DB = -12.0


class LocalVoiceError(Exception):
    pass


def duck_linear(duck_db: float = DUCK_DB) -> float:
    return 10 ** (duck_db / 20)


def finish_filter() -> str:
    return f"{ROOM},{LOUDNESS}"


def narrate_local(script: dict[str, Any], out_path: Path) -> Path:
    beats = [beat for beat in script.get("beats") or [] if str(beat.get("text") or "").strip()]
    if not beats:
        raise LocalVoiceError("script has no narration text")
    work = out_path.parent / "_voice"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    wavs: list[Path] = []
    try:
        for index, beat in enumerate(beats, start=1):
            wav = work / f"beat{int(beat.get('ord') or index):02d}.wav"
            synthesize(str(beat["text"]), wav)
            wavs.append(wav)
        joined = work / "joined.wav"
        _concat_wavs(wavs, joined)
        _render_mp3(joined, out_path)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    mix = {
        "engine": engine_name(),
        "loudness": {"I": -16, "TP": -1.5, "LRA": 11},
        "duck_db": DUCK_DB,
        "room": "short-local",
        "beats": [int(beat.get("ord") or index) for index, beat in enumerate(beats, start=1)],
    }
    (out_path.parent / "mix.json").write_text(json.dumps(mix, indent=2), encoding="utf-8")
    return out_path


def engine_name() -> str:
    if (os.environ.get("KOKORO_VOICE") or "").strip():
        return "kokoro"
    return "piper"


def synthesize(text: str, dest: Path) -> None:
    voice = (os.environ.get("KOKORO_VOICE") or "").strip()
    if voice:
        _kokoro(text, voice, dest)
        return
    binary, model = piper_paths()
    if binary is None or model is None:
        raise LocalVoiceError(
            "local Piper or Kokoro is not installed; public TTS is disabled"
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [str(binary), "--model", str(model), "--output_file", str(dest)],
        input=text.encode("utf-8"),
        capture_output=True,
    )
    if proc.returncode != 0 or not dest.is_file() or dest.stat().st_size == 0:
        tail = (proc.stderr or b"").decode("utf-8", errors="replace").strip().splitlines()
        detail = tail[-1] if tail else "piper failed"
        raise LocalVoiceError(detail)


def piper_paths() -> tuple[Path | None, Path | None]:
    binary = (os.environ.get("PIPER_BIN") or "").strip()
    model = (os.environ.get("PIPER_MODEL") or "").strip()
    bin_path = Path(binary) if binary else Path("/opt/piper/piper")
    if not bin_path.is_file():
        found = shutil.which("piper")
        bin_path = Path(found) if found else None
    model_path = Path(model) if model else Path("/opt/piper/en_US-lessac-medium.onnx")
    if bin_path is None or not bin_path.is_file():
        return None, None
    if not model_path.is_file():
        return None, None
    return bin_path, model_path


def mix_bed(video: Path, voice: Path, dest: Path) -> None:
    """Duck the capture bed 12 dB under the local voice and limit the sum."""
    ffmpeg = _ffmpeg()
    linear = f"{duck_linear():.4f}"
    if _has_audio(video):
        filt = (
            f"[0:a]volume={linear}[bed];"
            "[1:a]volume=1.0[vox];"
            "[bed][vox]amix=inputs=2:duration=first:dropout_transition=0,"
            f"{LOUDNESS}[a]"
        )
        cmd = [
            ffmpeg, "-y", "-i", str(video), "-i", str(voice),
            "-filter_complex", filt,
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-ac", "2",
            str(dest),
        ]
    else:
        cmd = [
            ffmpeg, "-y", "-i", str(video), "-i", str(voice),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-ac", "2",
            "-af", LOUDNESS,
            str(dest),
        ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()
        raise LocalVoiceError(tail[-1] if tail else "mix failed")


def max_volume_db(path: Path) -> float | None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not path.is_file():
        return None
    proc = subprocess.run(
        [ffmpeg, "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    for line in (proc.stderr or "").splitlines():
        if "max_volume:" in line:
            token = line.split("max_volume:", 1)[1].strip().split()[0]
            try:
                return float(token)
            except ValueError:
                return None
    return None


def _kokoro(text: str, voice: str, dest: Path) -> None:
    try:
        from kokoro import KPipeline  # type: ignore
    except ImportError as exc:
        raise LocalVoiceError("Kokoro is not installed; public TTS is disabled") from exc
    pipeline = KPipeline(lang_code=voice.split("-", 1)[0] if "-" in voice else "a")
    audio = None
    for _graph, _phon, chunk in pipeline(text, voice=voice):
        audio = chunk if audio is None else _cat(audio, chunk)
    if audio is None:
        raise LocalVoiceError("Kokoro returned no audio")
    try:
        import numpy as np
        import soundfile as sf
    except ImportError as exc:
        raise LocalVoiceError("soundfile is not installed") from exc
    dest.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(dest), np.asarray(audio), 24000)


def _cat(left: Any, right: Any) -> Any:
    import numpy as np

    return np.concatenate([np.asarray(left), np.asarray(right)])


def _concat_wavs(wavs: list[Path], dest: Path) -> None:
    ffmpeg = _ffmpeg()
    silence = dest.parent / "gap.wav"
    gap = subprocess.run(
        [
            ffmpeg, "-y", "-f", "lavfi", "-i", "anullsrc=channel_layout=mono:sample_rate=22050",
            "-t", "0.12", str(silence),
        ],
        capture_output=True,
        text=True,
    )
    if gap.returncode != 0:
        raise LocalVoiceError("could not build the beat gap")
    listing = dest.parent / "list.txt"
    lines = []
    for index, wav in enumerate(wavs):
        lines.append(f"file '{wav.resolve().as_posix()}'")
        if index != len(wavs) - 1:
            lines.append(f"file '{silence.resolve().as_posix()}'")
    listing.write_text("\n".join(lines) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(dest)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise LocalVoiceError("could not join beat wavs")


def _render_mp3(wav: Path, dest: Path) -> None:
    ffmpeg = _ffmpeg()
    dest.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [ffmpeg, "-y", "-i", str(wav), "-af", finish_filter(), "-c:a", "libmp3lame", "-q:a", "2", str(dest)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or not dest.is_file():
        tail = (proc.stderr or "").strip().splitlines()
        raise LocalVoiceError(tail[-1] if tail else "loudness pass failed")


def _has_audio(path: Path) -> bool:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return True
    proc = subprocess.run(
        [
            ffprobe, "-v", "error", "-select_streams", "a",
            "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path),
        ],
        capture_output=True,
        text=True,
    )
    return "audio" in (proc.stdout or "")


def _ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise LocalVoiceError("ffmpeg is not on PATH")
    return ffmpeg
