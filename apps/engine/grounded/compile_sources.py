"""Compile whatever was uploaded: a transcript, a workbook pack, or a document."""

from __future__ import annotations

import json
from typing import Any

from .compile_deck import CompileError, cell_index
from .director import direct
from .ingest import IngestError, parse_docx

_RECORDING_SKILLS = frozenset({"product-walkthrough", "sop-training", "feature-delta"})
_DOCUMENT_SKILLS = frozenset({"leadership-brief", "launch-announcement"})
DOCUMENT_SKILLS = _DOCUMENT_SKILLS


def load_json(data: bytes, label: str) -> dict[str, Any]:
    return _json_object(data, label)


def load_document(data: bytes) -> dict[str, Any]:
    return _load_document(data)


def compile_uploaded(
    *,
    skill_id: str,
    title: str,
    segments: list[dict[str, Any]] | None = None,
    document: bytes | None = None,
    workbook: bytes | None = None,
) -> dict[str, Any]:
    """Build a cited script from the assets on a briefing.

    A recording skill with a transcript stays a recording. A workbook JSON
    pack becomes the weekly deck. A .docx or a JSON block pack becomes a
    leadership or launch deck. A document uploaded onto the default
    walkthrough skill is compiled as a leadership brief instead of waiting
    for a transcript that will never arrive.
    """
    from . import compile_sources as sources
    from .dispatch import compile_for_skill

    return compile_for_skill(
        skill_id=skill_id,
        title=title,
        segments=segments,
        document=document,
        workbook=workbook,
        sources=sources,
    )


def _approve(
    script: dict[str, Any],
    pack: dict[str, Any] | None = None,
    cells: dict[tuple[str, str], Any] | None = None,
) -> None:
    result = direct(script, pack, cells)
    if result["errors"]:
        raise CompileError(result["errors"])


def _load_document(data: bytes) -> dict[str, Any]:
    if data[:2] == b"PK":
        try:
            return parse_docx(data)
        except IngestError as exc:
            raise CompileError([str(exc)]) from exc
    if data.lstrip()[:1] in {b"{", b"["}:
        return _json_object(data, "document")
    raise CompileError(["document must be a .docx or a JSON block pack"])


def _json_object(data: bytes, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as exc:
        raise CompileError([f"{label} is not JSON ({exc.msg})"]) from exc
    if not isinstance(parsed, dict):
        raise CompileError([f"{label} must be a JSON object"])
    return parsed
