"""Edit a transcript into cuts, chapter cards, and captions. The house style stays in the renderer."""

from __future__ import annotations

import re
from typing import Any

from .compile_deck import CompileError
from .layouts import SKILL_RENDERER
from .numbers import parse_numbers

_FILLER = re.compile(r"^(um+|uh+|er+|hmm+)\.?$", re.IGNORECASE)


def compile_recording(
    segments: list[dict[str, Any]],
    skill_id: str = "product-walkthrough",
    title: str = "Walkthrough",
) -> dict[str, Any]:
    kept = [segment for segment in segments if _keep(segment)]
    if not kept:
        raise CompileError(["recording has no spoken beats"])
    beats = []
    cuts = []
    for segment in kept:
        text = segment["text"].strip()
        cite = {
            "kind": "recording",
            "t_start_ms": int(segment["t_start_ms"]),
            "t_end_ms": int(segment["t_end_ms"]),
        }
        kind = "hook" if skill_id == "product-walkthrough" and not beats else "step"
        slots: dict[str, Any] = {}
        if segment.get("screen"):
            slots["screen"] = segment["screen"]
        beat: dict[str, Any] = {
            "kind": kind,
            "layout": "step",
            "text": text,
            "slots": slots,
            "claims": [],
            "citations": [cite],
        }
        beats.append(beat)
        cut: dict[str, Any] = {
            "src_in_ms": cite["t_start_ms"],
            "src_out_ms": cite["t_end_ms"],
            "text": text,
            "screen": segment.get("screen") or "",
        }
        if segment.get("click"):
            cut["zoom"] = {
                "x": float(segment["click"]["x"]),
                "y": float(segment["click"]["y"]),
                "scale": 1.35,
            }
        cuts.append(cut)
    duration = max(int(segment["t_end_ms"]) for segment in segments)
    script = {
        "skill_id": skill_id,
        "skill_version": "1.0.0",
        "language": "en",
        "title": title,
        "renderer": SKILL_RENDERER.get(skill_id, "recording"),
        "source_duration_ms": duration,
        "source_segments": [_segment_record(segment) for segment in segments],
        "beats": [],
        "edit": {"cuts": cuts},
    }
    for index, beat in enumerate(beats, start=1):
        beat["ord"] = index
        script["beats"].append(beat)
    return script


def compile_delta(
    parent: dict[str, Any],
    segments: list[dict[str, Any]],
    title: str | None = None,
    changelog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    extra = compile_recording(segments, skill_id="feature-delta", title=title or parent["title"])
    shift = int(parent.get("source_duration_ms") or 0)
    extra_cuts = []
    for cut in extra["edit"]["cuts"]:
        moved = dict(cut)
        moved["src_in_ms"] = int(cut["src_in_ms"]) + shift
        moved["src_out_ms"] = int(cut["src_out_ms"]) + shift
        extra_cuts.append(moved)
    extra_segments = []
    for segment in extra.get("source_segments") or []:
        extra_segments.append(
            {
                **segment,
                "t_start_ms": int(segment["t_start_ms"]) + shift,
                "t_end_ms": int(segment["t_end_ms"]) + shift,
            }
        )
    merged = {
        "skill_id": "feature-delta",
        "skill_version": "1.0.0",
        "language": parent.get("language", "en"),
        "title": title or parent["title"],
        "renderer": "recording",
        "source_duration_ms": shift + int(extra.get("source_duration_ms") or 0),
        "source_segments": list(parent.get("source_segments") or []) + extra_segments,
        "beats": [],
        "edit": {"cuts": list((parent.get("edit") or {}).get("cuts") or []) + extra_cuts},
    }
    beats = [dict(beat) for beat in parent["beats"]]
    start = len(beats)
    for offset, beat in enumerate(extra["beats"], start=1):
        copied = dict(beat)
        copied["ord"] = start + offset
        copied["kind"] = "step"
        citations = []
        for cite in beat.get("citations") or []:
            moved = dict(cite)
            if moved.get("kind") == "recording":
                moved["t_start_ms"] = int(moved["t_start_ms"]) + shift
                moved["t_end_ms"] = int(moved["t_end_ms"]) + shift
            citations.append(moved)
        copied["citations"] = citations
        beats.append(copied)
    if changelog and (changelog.get("text") or "").strip():
        text = changelog["text"].strip()
        block_id = changelog.get("id") or "changelog"
        beats.append(
            {
                "ord": 0,
                "kind": "statement",
                "layout": "statement",
                "text": text,
                "slots": {"eyebrow": "What changed"},
                "claims": [{"value": number, "block_id": block_id} for number in parse_numbers(text)],
                "citations": [{"kind": "document", "block_id": block_id}],
            }
        )
    for index, beat in enumerate(beats, start=1):
        beat["ord"] = index
        merged["beats"].append(beat)
    return merged


def _segment_record(segment: dict[str, Any]) -> dict[str, Any]:
    record = {
        "t_start_ms": int(segment["t_start_ms"]),
        "t_end_ms": int(segment["t_end_ms"]),
        "screen": segment.get("screen") or "",
        "text": (segment.get("text") or "").strip(),
    }
    if segment.get("click"):
        record["click"] = segment["click"]
    return record


def _keep(segment: dict[str, Any]) -> bool:
    text = (segment.get("text") or "").strip()
    if not text or _FILLER.match(text):
        return False
    start = int(segment["t_start_ms"])
    end = int(segment["t_end_ms"])
    return end > start
