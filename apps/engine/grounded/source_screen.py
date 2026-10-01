"""Paint a source recording, then the editor cuts it. The source is the product UI."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from .house import ACCENT, INK, PAPER, RULE


def slices(segments: list[dict[str, Any]], duration_ms: int) -> list[tuple[int, int, str]]:
    ordered = sorted(segments, key=lambda segment: int(segment["t_start_ms"]))
    screen = ""
    cursor = 0
    raw: list[tuple[int, int, str]] = []
    for segment in ordered:
        start = int(segment["t_start_ms"])
        end = int(segment["t_end_ms"])
        if start > cursor:
            raw.append((cursor, start, screen or "Recording"))
        if segment.get("screen"):
            screen = segment["screen"]
        if end > start:
            raw.append((start, end, screen or "Recording"))
        cursor = max(cursor, end)
    if duration_ms > cursor:
        raw.append((cursor, duration_ms, screen or "Recording"))
    merged: list[tuple[int, int, str]] = []
    for start, end, label in raw:
        if merged and merged[-1][2] == label and merged[-1][1] == start:
            merged[-1] = (merged[-1][0], end, label)
        elif end > start:
            merged.append((start, end, label))
    return merged


def build_source(segments: list[dict[str, Any]], duration_ms: int, dest: Path) -> str | None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return "ffmpeg is not on PATH"
    font = _font("georgia.ttf", "Georgia.ttf", "times.ttf")
    ui = _font("segoeui.ttf", "arial.ttf")
    if font is None or ui is None:
        return "house fonts are not installed"
    parts = slices(segments, duration_ms)
    if not parts:
        return "source has no timeline"
    screens = []
    for _, _, label in parts:
        if label not in screens:
            screens.append(label)
    work = dest.parent / "_source"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    paths: list[Path] = []
    try:
        for index, (start, end, label) in enumerate(parts):
            clip = work / f"src{index:02d}.mp4"
            seconds = max(end - start, 200) / 1000
            error = _clip(
                ffmpeg,
                clip,
                seconds,
                _screen_filter(label, screens, font, ui),
            )
            if error:
                return error
            paths.append(clip)
        return _concat(ffmpeg, paths, dest)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _screen_filter(active: str, screens: list[str], font: Path, ui: Path) -> str:
    font_path = _filter_path(font)
    ui_path = _filter_path(ui)
    ink = _ff(INK)
    paper = _ff(PAPER)
    accent = _ff(ACCENT)
    parts = [
        f"drawbox=x=0:y=0:w=280:h=1080:color={ink}@1:t=fill",
        f"drawtext=fontfile='{ui_path}':text='GROUNDED':fontsize=18:fontcolor={paper}:x=36:y=48",
    ]
    for index, name in enumerate(screens[:8]):
        y = 140 + index * 56
        color = accent if name == active else paper
        parts.append(
            f"drawtext=fontfile='{ui_path}':text='{_esc(name)}':fontsize=24:fontcolor={color}:x=36:y={y}"
        )
    parts.extend(
        [
            f"drawtext=fontfile='{font_path}':text='{_esc(active)}':fontsize=60:fontcolor={ink}:x=360:y=140",
            f"drawbox=x=360:y=250:w=760:h=72:color={_ff(RULE)}@1:t=fill",
            f"drawtext=fontfile='{ui_path}':text='{_esc(active)}':fontsize=28:fontcolor={ink}:x=384:y=270",
            f"drawbox=x=360:y=380:w=200:h=56:color={accent}@1:t=fill",
            f"drawtext=fontfile='{ui_path}':text='Save':fontsize=24:fontcolor={paper}:x=424:y=396",
        ]
    )
    return ",".join(parts)


def _clip(ffmpeg: str, dest: Path, seconds: float, vf: str) -> str | None:
    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi", "-i", f"color=c={_ff(PAPER)}:s=1920x1080:r=30:d={seconds:.3f}",
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-vf", vf,
        "-shortest",
        "-t", f"{seconds:.3f}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        str(dest),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()
        return " | ".join(tail[-3:]) if tail else "ffmpeg failed to paint the source"
    return None


def _concat(ffmpeg: str, paths: list[Path], dest: Path) -> str | None:
    listing = dest.parent / "_source_list.txt"
    listing.write_text("".join(f"file '{path.as_posix()}'\n" for path in paths), encoding="utf-8")
    proc = subprocess.run(
        [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(dest)],
        capture_output=True,
        text=True,
    )
    listing.unlink(missing_ok=True)
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()
        return " | ".join(tail[-3:]) if tail else "ffmpeg failed to join the source"
    return None


def _font(*names: str) -> Path | None:
    windir = Path(__import__("os").environ.get("WINDIR", r"C:\Windows"))
    folder = windir / "Fonts"
    for name in names:
        path = folder / name
        if path.exists():
            return path
    return None


def _filter_path(path: Path) -> str:
    return path.as_posix().replace(":", "\\:")


def _ff(token: str) -> str:
    return "0x" + token.lstrip("#")


def _esc(text: str) -> str:
    return (
        text.replace("\\", "")
        .replace(":", "\\:")
        .replace("'", "")
        .replace("%", "\\%")
        .replace(",", "\\,")
    )
