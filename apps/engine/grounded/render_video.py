"""Narrated video from a deck script: onboarding, training, launches, briefs, WBRs.

Each beat becomes a house-style 16:9 frame drawn locally (Pillow, DejaVu
fonts), held for as long as its narration (local Piper/Kokoro) or a reading
time when narration is off. ffmpeg assembles the segments with a short fade.
The same timeline is written as ``edl.json`` chapters and ``captions.vtt``,
so the studio's film player, chapter strip, captions and "show me" all work.

Nothing is generated beyond the script: the frame shows the beat's own text,
figures and citations; narration speaks the beat's own text.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any, Callable

from .house import ACCENT, INK, MUTED, NEGATIVE, PAPER, RULE

W, H = 1920, 1080
FPS = 25
FONT_DIRS = (Path("/usr/share/fonts/truetype/dejavu"), Path("/usr/share/fonts/dejavu"), Path("/usr/local/share/fonts"))

Speak = Callable[[str, Path], Path]


class VideoError(RuntimeError):
    pass


def _font(name: str, size: int):
    from PIL import ImageFont

    for base in FONT_DIRS:
        path = base / name
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size)


def _rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _wrap(draw, text: str, font, width: int, max_lines: int) -> list[str]:
    words = str(text or "").split()
    lines: list[str] = []
    line = ""
    for word in words:
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= width:
            line = trial
            continue
        if line:
            lines.append(line)
        line = word
        if len(lines) == max_lines:
            break
    if line and len(lines) < max_lines:
        lines.append(line)
    if len(lines) == max_lines and " ".join(lines) != " ".join(words):
        lines[-1] = lines[-1].rstrip(" .,;") + "…"
    return lines


def _cites(beat: dict[str, Any]) -> str:
    labels = []
    for cite in beat.get("citations") or []:
        kind = cite.get("kind")
        if kind == "workbook":
            labels.append(f"{cite.get('sheet')}!{cite.get('addr')}")
        elif kind == "document":
            labels.append(f"block {cite.get('block_id')}" + (f" · p.{cite['page']}" if cite.get("page") else ""))
        elif kind == "recording":
            labels.append(f"{_clock(cite.get('t_start_ms'))}–{_clock(cite.get('t_end_ms'))}")
    text = " · ".join(dict.fromkeys(labels))
    return text if len(text) < 140 else text[:137] + "…"


def _clock(ms: Any) -> str:
    total = max(0, int(ms or 0)) // 1000
    return f"{total // 60}:{total % 60:02d}"


def eyebrow(script: dict[str, Any], beat: dict[str, Any]) -> str:
    from .render_deck import _EYEBROW

    slots = beat.get("slots") or {}
    if beat.get("layout") == "cover":
        return _EYEBROW.get(script.get("skill_id") or "", "Briefing")
    if beat.get("layout") == "step":
        return f"Step {slots.get('step') or beat.get('ord')}"
    return str(slots.get("eyebrow") or {"movers": "Movers", "source-range": "Source data"}.get(beat.get("layout"), ""))


def draw_frame(script: dict[str, Any], beat: dict[str, Any], index: int, total: int, dest: Path, reveal: bool = False) -> Path:
    from PIL import Image, ImageDraw

    paper, ink, muted, rule = _rgb(PAPER), _rgb(INK), _rgb(MUTED), _rgb(RULE)
    accent, negative = _rgb(ACCENT), _rgb(NEGATIVE)
    image = Image.new("RGB", (W, H), paper)
    draw = ImageDraw.Draw(image)
    left, right, top = 150, W - 150, 140
    width = right - left
    layout = beat.get("layout") or "statement"
    slots = beat.get("slots") or {}
    ui_bold = _font("DejaVuSans-Bold.ttf", 26)
    eyebrow_text = eyebrow(script, beat).upper()
    text = str(beat.get("text") or "")
    textual = layout in {"cover", "step", "statement", "ask", "risk"} and not slots.get("answer")
    if layout == "step":
        numeral = f"{int(slots.get('step') or beat.get('ord') or 0):02d}"
        num_font = _font("DejaVuSerif.ttf", 300)
        title_font = _font("DejaVuSerif.ttf", 72 if len(text) < 110 else 58)
        lines = _wrap(draw, text, title_font, width - 470, 6)
        block_h = len(lines) * int(title_font.size * 1.24)
        y0 = max(top + 60, (H - 120 - block_h) // 2)
        draw.text((left - 10, (H - 120) // 2 - 210), numeral, font=num_font, fill=_mix(accent, paper, 0.82))
        draw.text((left + 470, y0 - 60), " ".join(eyebrow_text), font=ui_bold, fill=accent)
        for line in lines:
            draw.text((left + 470, y0), line, font=title_font, fill=ink)
            y0 += int(title_font.size * 1.24)
        y = y0 + 20
    else:
        title_size = 112 if layout == "cover" else (66 if len(text) < 140 else 54)
        title_font = _font("DejaVuSerif.ttf", title_size)
        lines = _wrap(draw, text, title_font, width if layout != "cover" else int(width * 0.82), 6 if layout != "cover" else 3)
        line_h = int(title_size * 1.22)
        y = top + 70
        if textual:
            y = max(top + 70, (H - 140 - len(lines) * line_h) // 2)
        draw.text((left, y - 70), " ".join(eyebrow_text), font=ui_bold, fill=negative if layout == "risk" else accent)
        if layout == "cover":
            draw.line((left, y - 100, left + 120, y - 100), fill=accent, width=6)
        for line in lines:
            draw.text((left, y), line, font=title_font, fill=ink)
            y += line_h
        y += 30
    if layout == "cover" and slots.get("period"):
        draw.text((left, y), str(slots["period"]), font=_font("DejaVuSerif.ttf", 44), fill=muted)
    elif layout == "big-number":
        draw.text((left, y + 10), str(slots.get("actual") or ""), font=_font("DejaVuSerif.ttf", 190), fill=ink)
    elif layout == "versus-target":
        label = _font("DejaVuSans.ttf", 24)
        big = _font("DejaVuSerif.ttf", 128)
        for offset, (name, key) in enumerate((("ACTUAL", "actual"), ("TARGET", "target"))):
            x = left + offset * (width // 2)
            draw.text((x, y), name, font=label, fill=muted)
            draw.text((x, y + 40), str(slots.get(key) or ""), font=big, fill=ink)
        down = slots.get("direction") == "below"
        draw.text((left, y + 220), str(slots.get("delta") or ""), font=_font("DejaVuSans-Bold.ttf", 36), fill=negative if down else accent)
    elif layout in {"movers", "source-range"}:
        rows: list[list[str]] = []
        if layout == "movers":
            rows.append(["Line", "This week", "Last week", "Delta"])
            for row in slots.get("rows") or []:
                rows.append([str(row.get(k) or "") for k in ("line", "this_week", "last_week", "delta")])
        else:
            for row in (beat.get("visual") or {}).get("rows") or []:
                rows.append([str(cell.get("display") or "") for cell in row])
        cell_font = _font("DejaVuSans.ttf", 30)
        head_font = _font("DejaVuSans-Bold.ttf", 22)
        cols = max((len(r) for r in rows), default=1)
        col_w = width // max(cols, 1)
        for r, row in enumerate(rows[:10]):
            for c, value in enumerate(row):
                font = head_font if r == 0 else cell_font
                text = value.upper() if r == 0 else value
                tw = draw.textlength(text, font=font)
                x = left + c * col_w + (0 if c == 0 else col_w - tw - 10)
                color = negative if (r and c == cols - 1 and value.startswith("-")) else (muted if r == 0 else ink)
                draw.text((x, y), text, font=font, fill=color)
            y += 58 if r == 0 else 54
            draw.line((left, y - 12, right, y - 12), fill=ink if r == 0 else rule, width=2 if r == 0 else 1)
    elif layout == "step" and slots.get("screen"):
        draw.text((left, y), str(slots["screen"]), font=_font("DejaVuSerif.ttf", 40), fill=muted)
    if slots.get("answer"):
        label_font = _font("DejaVuSans-Bold.ttf", 24)
        if reveal:
            draw.text((left, y + 10), "ANSWER", font=label_font, fill=accent)
            answer_font = _font("DejaVuSerif.ttf", 46)
            yy = y + 52
            for line in _wrap(draw, str(slots["answer"]), answer_font, width, 3):
                draw.text((left, yy), line, font=answer_font, fill=ink)
                yy += 58
        else:
            draw.text((left, y + 10), "PAUSE AND ANSWER — THE ANSWER FOLLOWS", font=label_font, fill=muted)
    footer_y = H - 110
    draw.line((left, footer_y, right, footer_y), fill=rule, width=2)
    draw.line((left, footer_y, left + int(width * index / max(total, 1)), footer_y), fill=accent, width=4)
    small = _font("DejaVuSans.ttf", 22)
    draw.text((left, footer_y + 22), _cites(beat), font=small, fill=muted)
    page = f"{index} / {total}"
    draw.text((right - draw.textlength(page, font=small), footer_y + 22), page, font=small, fill=muted)
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest, "PNG", optimize=True)
    return dest


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))  # type: ignore[return-value]


def _wav_ms(path: Path) -> int:
    try:
        with wave.open(str(path), "rb") as handle:
            return int(handle.getnframes() * 1000 / handle.getframerate())
    except (wave.Error, OSError, ZeroDivisionError):
        probe = shutil.which("ffprobe")
        if not probe:
            return 0
        proc = subprocess.run(
            [probe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, check=False,
        )
        try:
            return int(float(proc.stdout.strip()) * 1000)
        except ValueError:
            return 0


def reading_ms(text: str) -> int:
    words = len(str(text or "").split())
    return int(max(3.2, words / 2.6 + 1.3) * 1000)


def spoken_text(script: dict[str, Any], beat: dict[str, Any]) -> str:
    text = str(beat.get("text") or "")
    if beat.get("layout") == "step":
        return f"Step {(beat.get('slots') or {}).get('step') or beat.get('ord')}. {text}"
    return text


def render_narrated_video(script: dict[str, Any], out_dir: Path, speak: Speak | None = None) -> dict[str, Any]:
    """Write walkthrough.mp4, edl.json and captions.vtt for a deck script."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise VideoError("ffmpeg is required for narrated video")
    beats = list(script.get("beats") or [])
    if not beats:
        raise VideoError("script has no beats")
    out_dir.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    clock = 0
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        segments: list[Path] = []
        for index, beat in enumerate(beats, start=1):
            parts = [(False, spoken_text(script, beat))]
            if (beat.get("slots") or {}).get("answer"):
                parts.append((True, "The answer: " + str(beat["slots"]["answer"])))
            for part_no, (reveal, words) in enumerate(parts):
                frame = draw_frame(script, beat, index, len(beats), work / f"f{index:03d}_{part_no}.png", reveal=reveal)
                audio = work / f"a{index:03d}_{part_no}.wav"
                voiced = False
                if speak is not None:
                    try:
                        speak(words, audio)
                        voiced = audio.is_file() and audio.stat().st_size > 0
                    except Exception as exc:  # noqa: BLE001 - narration selected but failed: fail the render
                        raise VideoError(f"local narration failed ({type(exc).__name__})") from None
                duration = (_wav_ms(audio) + 700) if voiced else reading_ms(words)
                if reveal is False and len(parts) > 1:
                    duration += 2500  # time to think before the answer
                segment = work / f"s{index:03d}_{part_no}.mp4"
                cmd = [
                    ffmpeg, "-y", "-v", "error", "-loop", "1", "-framerate", str(FPS), "-t", f"{duration / 1000:.3f}", "-i", str(frame),
                ]
                if voiced:
                    cmd += ["-i", str(audio), "-af", "apad", "-shortest"]
                else:
                    cmd += ["-f", "lavfi", "-t", f"{duration / 1000:.3f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
                cmd += [
                    # The opening frame is the poster, so it must not start black.
                    "-vf", "format=yuv420p" if len(segments) == 0 else "fade=t=in:st=0:d=0.35,format=yuv420p",
                    "-c:v", "libx264", "-tune", "stillimage", "-preset", "veryfast", "-crf", "20", "-r", str(FPS),
                    "-c:a", "aac", "-ar", "48000", "-ac", "2", "-t", f"{duration / 1000:.3f}",
                    str(segment),
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if proc.returncode != 0:
                    raise VideoError("could not encode a video segment")
                segments.append(segment)
                if part_no == 0:
                    items.append({"type": "chapter", "title": _chapter(script, beat), "text": str(beat.get("text") or ""),
                                  "ord": beat.get("ord"), "out_in_ms": clock, "duration_ms": duration})
                items.append({"type": "cut", "title": _chapter(script, beat), "text": words if reveal else str(beat.get("text") or ""),
                              "ord": beat.get("ord"), "out_in_ms": clock, "duration_ms": duration})
                clock += duration
        listing = work / "list.txt"
        listing.write_text("".join(f"file '{path.as_posix()}'\n" for path in segments), encoding="utf-8")
        video = out_dir / "walkthrough.mp4"
        proc = subprocess.run(
            [ffmpeg, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(video)],
            capture_output=True, text=True, check=False,
        )
        if proc.returncode != 0:
            raise VideoError("could not join the video segments")
    (out_dir / "edl.json").write_text(json.dumps({"title": script.get("title"), "kind": "narrated-deck", "items": items}, indent=2), encoding="utf-8")
    (out_dir / "captions.vtt").write_text(_vtt(items), encoding="utf-8")
    return {"video": video, "edl": out_dir / "edl.json", "vtt": out_dir / "captions.vtt", "duration_ms": clock, "narrated": speak is not None}


def _chapter(script: dict[str, Any], beat: dict[str, Any]) -> str:
    if beat.get("layout") == "cover":
        return "Introduction"
    label = eyebrow(script, beat)
    return label or str(beat.get("text") or "")[:40]


def _vtt(items: list[dict[str, Any]]) -> str:
    def stamp(ms: int) -> str:
        hours, rem = divmod(ms, 3_600_000)
        minutes, rem = divmod(rem, 60_000)
        seconds, millis = divmod(rem, 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"

    lines = ["WEBVTT", ""]
    for n, item in enumerate((i for i in items if i["type"] == "cut"), start=1):
        lines += [str(n), f"{stamp(item['out_in_ms'])} --> {stamp(item['out_in_ms'] + item['duration_ms'])}", item["text"], ""]
    return "\n".join(lines)
