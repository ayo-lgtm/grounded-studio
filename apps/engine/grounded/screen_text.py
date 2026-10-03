"""Read what is on screen in a recording, locally, with timestamps.

Frames are sampled with ffmpeg (one every ``interval`` seconds, scaled down),
each frame goes through the selected :class:`ImageTextProvider` (local
tesseract, or Nova multimodal in aws-private mode), and consecutive frames
showing the same text collapse into one span. The result is a list of
segments ``{t_start_ms, t_end_ms, text}`` stored with ``speaker='screen'``
so chat can cite "on screen at 0:42" exactly like speech.

Nothing here invents text: OCR output is filtered (short or symbol-only
lines dropped) but never completed or corrected.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

_LINE = re.compile(r"[A-Za-z0-9]")


class ScreenTextError(RuntimeError):
    pass


def clean_lines(paragraphs: list[str]) -> list[str]:
    lines: list[str] = []
    for paragraph in paragraphs:
        for raw in paragraph.splitlines():
            line = " ".join(raw.split())
            letters = sum(ch.isalnum() for ch in line)
            if len(line) < 3 or letters < 3 or letters / max(len(line), 1) < 0.5:
                continue
            if line not in lines:
                lines.append(line)
    return lines


def _similar(a: list[str], b: list[str]) -> bool:
    if not a or not b:
        return a == b
    sa, sb = set(a), set(b)
    return len(sa & sb) / max(len(sa | sb), 1) >= 0.8


def sample_frames(video: Path, out_dir: Path, interval: float = 2.0, max_frames: int = 900) -> list[tuple[int, Path]]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise ScreenTextError("ffmpeg is required to read the screen")
    out_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            ffmpeg, "-v", "error", "-i", str(video),
            "-vf", f"fps=1/{interval},scale='min(1600,iw)':-2",
            "-frames:v", str(max_frames),
            str(out_dir / "f%05d.png"),
        ],
        capture_output=True,
        timeout=1800,
        check=False,
    )
    if proc.returncode != 0:
        raise ScreenTextError("could not sample frames from the recording")
    frames = sorted(out_dir.glob("f*.png"))
    return [(int(index * interval * 1000), path) for index, path in enumerate(frames)]


def read_screen(video: Path, provider: Any, *, interval: float = 2.0, duration_ms: int | None = None) -> list[dict[str, Any]]:
    """Timestamped on-screen text spans for a recording."""
    with tempfile.TemporaryDirectory() as tmp:
        frames = sample_frames(video, Path(tmp), interval=interval)
        spans: list[dict[str, Any]] = []
        current: list[str] = []
        start = 0
        last_t = 0
        for t_ms, frame in frames:
            try:
                lines = clean_lines(provider.extract_text(frame.read_bytes(), "png"))
            except Exception:  # noqa: BLE001 - one unreadable frame is skipped, not invented
                lines = []
            last_t = t_ms
            if _similar(lines, current):
                continue
            if current:
                spans.append({"t_start_ms": start, "t_end_ms": t_ms, "lines": current})
            current, start = lines, t_ms
        end = duration_ms or (last_t + int(interval * 1000))
        if current:
            spans.append({"t_start_ms": start, "t_end_ms": max(end, start + 200), "lines": current})
    out = []
    for span in spans:
        text = " · ".join(span["lines"])[:600]
        if text:
            out.append({"t_start_ms": span["t_start_ms"], "t_end_ms": span["t_end_ms"], "text": text})
    return out
