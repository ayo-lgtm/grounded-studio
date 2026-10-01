"""Compile whatever was uploaded: a transcript, a workbook pack, or a document."""

from __future__ import annotations

import json
from typing import Any

from .compile_deck import CompileError, cell_index, compile_document, compile_workbook
from .compile_recording import compile_recording
from .director import direct
from .ingest import IngestError, parse_docx

_RECORDING_SKILLS = frozenset({"product-walkthrough", "sop-training", "feature-delta"})
_DOCUMENT_SKILLS = frozenset({"leadership-brief", "launch-announcement"})


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
    spoken = [dict(segment) for segment in (segments or []) if (segment.get("text") or "").strip()]
    if skill_id in _RECORDING_SKILLS and spoken:
        script = compile_recording(spoken, skill_id=skill_id, title=title or "Walkthrough")
        _approve(script)
        return script
    if skill_id == "weekly-ops-review" or (
        workbook and not document and skill_id not in _DOCUMENT_SKILLS and not spoken
    ):
        if not workbook:
            raise CompileError(["weekly-ops-review needs a workbook JSON upload"])
        pack = _json_object(workbook, "workbook")
        script = compile_workbook(pack, "weekly-ops-review")
        _approve(script, pack, cell_index(pack))
        return script
    if document and (skill_id in _DOCUMENT_SKILLS or not spoken):
        doc_skill = skill_id if skill_id in _DOCUMENT_SKILLS else "leadership-brief"
        script = compile_document(_load_document(document), doc_skill)
        _approve(script)
        return script
    if skill_id in _RECORDING_SKILLS:
        raise CompileError(["transcribe first"])
    raise CompileError(["upload a workbook JSON or a .docx before compile"])


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
