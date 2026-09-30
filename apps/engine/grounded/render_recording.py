"""Turn an edit decision list into a storyboard, captions, and a fixture mp4."""

from __future__ import annotations

import html
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .house import ACCENT, CAPTION, CAPTION_INK, INK, PAPER, css
from .render_deck import guide_md
from .source_screen import build_source

CHAPTER_MS = 1200


def render_edit(
    script: dict[str, Any],
    out_dir: Path,
    with_video: bool = True,
    source_video: Path | None = None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    items = timeline(script)
    edl_path = out_dir / "edl.json"
    vtt_path = out_dir / "captions.vtt"
    story_path = out_dir / "storyboard.html"
    guide_path = out_dir / "guide.md"
    edl_path.write_text(json.dumps({"title": script.get("title"), "items": items}, indent=2), encoding="utf-8")
    vtt_path.write_text(_vtt(items), encoding="utf-8")
    story_path.write_text(_storyboard(script, items), encoding="utf-8")
    guide_path.write_text(guide_md(script), encoding="utf-8")
    video_path = out_dir / "walkthrough.mp4"
    video_error = _render_mp4(items, video_path, script, source_video) if with_video else None
    source_path = out_dir / "source.mp4"
    return {
        "edl": edl_path,
        "vtt": vtt_path,
        "storyboard": story_path,
        "guide": guide_path,
        "source": source_path if source_path.exists() else None,
        "video": None if video_error or not with_video else video_path,
        "video_error": video_error,
    }


def timeline(script: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    last_screen = None
    clock = 0
    for cut in (script.get("edit") or {}).get("cuts") or []:
        screen = (cut.get("screen") or "").strip()
        if screen and screen != last_screen:
            items.append(
                {
                    "type": "chapter",
                    "title": screen,
                    "out_in_ms": clock,
                    "duration_ms": CHAPTER_MS,
                }
            )
            clock += CHAPTER_MS
            last_screen = screen
        duration = int(cut["src_out_ms"]) - int(cut["src_in_ms"])
        items.append(
            {
                "type": "cut",
                "title": screen,
                "text": cut.get("text") or "",
                "src_in_ms": cut["src_in_ms"],
                "src_out_ms": cut["src_out_ms"],
                "out_in_ms": clock,
                "duration_ms": duration,
                "zoom": cut.get("zoom"),
            }
        )
        clock += duration
    for beat in script.get("beats") or []:
        if beat.get("layout") != "statement":
            continue
        items.append(
            {
                "type": "note",
                "title": beat.get("text") or "",
                "out_in_ms": clock,
                "duration_ms": 2800,
            }
        )
        clock += 2800
    return items


def _vtt(items: list[dict[str, Any]]) -> str:
    lines = ["WEBVTT", ""]
    for item in items:
        if item["type"] != "cut":
            continue
        start = item["out_in_ms"]
        end = start + item["duration_ms"]
        lines.append(f"{_vtt_clock(start)} --> {_vtt_clock(end)}")
        lines.append(item["text"])
        lines.append("")
    return "\n".join(lines)


def _storyboard(script: dict[str, Any], items: list[dict[str, Any]]) -> str:
    slides = []
    total = len(items) + 1
    slides.append(
        f"""<section class="slide"><article class="frame cover">
        <p class="eyebrow">Edit</p>
        <h1>{html.escape(script.get("title") or "Walkthrough")}</h1>
        <p class="lead">The edit keeps the source pixels. Filler and dead air are already out.</p>
        <footer class="footer"><span>Source recording</span><span>1 / {total}</span></footer>
        </article></section>"""
    )
    for index, item in enumerate(items, start=2):
        if item["type"] == "chapter":
            body = (
                f'<p class="eyebrow">Chapter</p><h1 class="screen">{html.escape(item["title"])}</h1>'
            )
        elif item["type"] == "note":
            body = (
                f'<p class="eyebrow">What changed</p><h1>{html.escape(item["title"])}</h1>'
            )
        else:
            zoom = item.get("zoom")
            zoom_html = ""
            if zoom:
                zoom_html = (
                    f'<p class="zoom">Zoom {zoom["scale"]} toward '
                    f'{zoom["x"]:.0%}, {zoom["y"]:.0%}</p>'
                )
            body = (
                f'<p class="eyebrow">Capture</p>'
                f'<h1 class="screen">{html.escape(item.get("title") or "Recording")}</h1>'
                f'{zoom_html}'
                f'<div class="caption-bar">{html.escape(item["text"])}</div>'
            )
        slides.append(
            f"""<section class="slide"><article class="frame">
            {body}
            <footer class="footer"><span>{_clock(item["out_in_ms"])}</span><span>{index} / {total}</span></footer>
            </article></section>"""
        )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>{html.escape(script.get("title") or "Edit")}</title>
<style>{css()}</style></head>
<body><main class="deck">{''.join(slides)}</main>
<script>
const slides = [...document.querySelectorAll(".slide")];
let index = 0;
function go(next) {{
  index = Math.max(0, Math.min(slides.length - 1, next));
  slides[index].scrollIntoView();
  history.replaceState(null, "", "#" + (index + 1));
}}
document.addEventListener("keydown", (event) => {{
  if (["ArrowRight", "ArrowDown", " "].includes(event.key)) {{ event.preventDefault(); go(index + 1); }}
  if (["ArrowLeft", "ArrowUp"].includes(event.key)) {{ event.preventDefault(); go(index - 1); }}
}});
const start = parseInt((location.hash || "#1").slice(1), 10);
if (!Number.isNaN(start)) go(start - 1);
</script>
</body></html>
"""


def _render_mp4(
    items: list[dict[str, Any]],
    dest: Path,
    script: dict[str, Any],
    source_video: Path | None,
) -> str | None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return "ffmpeg is not on PATH"
    font = _font("georgia.ttf", "Georgia.ttf", "times.ttf")
    ui = _font("segoeui.ttf", "arial.ttf")
    if font is None or ui is None:
        return "house fonts are not installed"
    source = source_video
    if source is None and script.get("source_segments"):
        source = dest.parent / "source.mp4"
        error = build_source(
            script["source_segments"],
            int(script.get("source_duration_ms") or 0),
            source,
        )
        if error:
            return error
    work = dest.parent / "_clips"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    paths: list[Path] = []
    try:
        for index, item in enumerate(items):
            clip = work / f"clip{index:02d}.mp4"
            if item["type"] == "cut" and source is not None:
                error = _cut_source(ffmpeg, source, item, clip, font, ui)
            else:
                error = _paint_card(ffmpeg, item, clip, font, ui)
            if error:
                return error
            paths.append(clip)
        concat = work / "list.txt"
        concat.write_text("".join(f"file '{path.as_posix()}'\n" for path in paths), encoding="utf-8")
        proc = subprocess.run(
            [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(dest)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            tail = (proc.stderr or "").strip().splitlines()
            return tail[-1] if tail else "ffmpeg concat failed"
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return None


def _paint_card(ffmpeg: str, item: dict[str, Any], dest: Path, font: Path, ui: Path) -> str | None:
    seconds = max(item["duration_ms"], 400) / 1000
    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi", "-i", f"color=c={_ff(PAPER)}:s=1920x1080:r=30:d={seconds:.3f}",
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-vf", _filter(item, font, ui),
        "-shortest",
        "-t", f"{seconds:.3f}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        str(dest),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()
        return tail[-1] if tail else "ffmpeg failed"
    return None


def _cut_source(
    ffmpeg: str,
    source: Path,
    item: dict[str, Any],
    dest: Path,
    font: Path,
    ui: Path,
) -> str | None:
    start = int(item["src_in_ms"]) / 1000
    end = int(item["src_out_ms"]) / 1000
    cmd = [
        ffmpeg, "-y",
        "-i", str(source),
        "-ss", f"{start:.3f}",
        "-to", f"{end:.3f}",
        "-vf", _caption_over_source(item, font, ui),
        "-r", "30",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        str(dest),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()
        return tail[-1] if tail else "ffmpeg failed to cut the source"
    return None


def _caption_over_source(item: dict[str, Any], font: Path, ui: Path) -> str:
    parts: list[str] = []
    zoom = item.get("zoom")
    if zoom:
        scale = float(zoom.get("scale") or 1.35)
        width = int(1920 / scale) // 2 * 2
        height = int(1080 / scale) // 2 * 2
        left = int(float(zoom["x"]) * 1920 - width / 2)
        top = int(float(zoom["y"]) * 1080 - height / 2)
        left = max(0, min(1920 - width, left))
        top = max(0, min(1080 - height, top))
        parts.append(f"crop={width}:{height}:{left}:{top}")
        parts.append("scale=1920:1080")
    caption = _esc(item.get("text") or "")
    font_path = _filter_path(font)
    parts.append(f"drawbox=x=0:y=900:w=1920:h=180:color={_ff(CAPTION)}@1:t=fill")
    parts.append(
        f"drawtext=fontfile='{font_path}':text='{caption}':fontsize=36:fontcolor={_ff(CAPTION_INK)}:x=80:y=960"
    )
    return ",".join(parts)


def _filter(item: dict[str, Any], font: Path, ui: Path) -> str:
    font_path = _filter_path(font)
    ui_path = _filter_path(ui)
    if item["type"] in {"chapter", "note"}:
        label = "WHAT CHANGED" if item["type"] == "note" else "CHAPTER"
        size = 48 if item["type"] == "note" else 84
        title = _esc(item["title"])
        return (
            f"drawtext=fontfile='{ui_path}':text='{label}':fontsize=28:fontcolor={_ff(ACCENT)}:"
            f"x=120:y=400,"
            f"drawtext=fontfile='{font_path}':text='{title}':fontsize={size}:fontcolor={_ff(INK)}:x=120:y=460"
        )
    screen = _esc(item.get("title") or "Recording")
    caption = _esc(item.get("text") or "")
    parts = [
        f"drawtext=fontfile='{ui_path}':text='CAPTURE':fontsize=28:fontcolor={_ff(ACCENT)}:x=120:y=120",
        f"drawtext=fontfile='{font_path}':text='{screen}':fontsize=72:fontcolor={_ff(INK)}:x=120:y=170",
        f"drawbox=x=0:y=900:w=1920:h=180:color={_ff(CAPTION)}@1:t=fill",
        f"drawtext=fontfile='{font_path}':text='{caption}':fontsize=36:fontcolor={_ff(CAPTION_INK)}:x=80:y=960",
    ]
    zoom = item.get("zoom")
    if zoom:
        x = int(float(zoom["x"]) * 1920)
        y = int(float(zoom["y"]) * 1080)
        parts.append(f"drawbox=x={x}:y={y}:w=320:h=90:color={_ff(ACCENT)}@1:t=4")
    return ",".join(parts)


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


def _clock(ms: int) -> str:
    total = max(0, int(ms)) / 1000
    minutes, seconds = divmod(total, 60)
    return f"{int(minutes)}:{seconds:04.1f}"


def _vtt_clock(ms: int) -> str:
    total = max(0, int(ms))
    hours, rem = divmod(total, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, milli = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02}.{milli:03}"
