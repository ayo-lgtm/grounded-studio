"""Compile uploaded sources through an executable skill contract."""

from __future__ import annotations

import json
from typing import Any

from .compile_deck import CompileError, cell_index, compile_document, compile_workbook
from .compile_recording import compile_recording
from .director import direct
from .ingest import IngestError, parse_docx, parse_pdf
from .ingest_workbook import parse_workbook
from .skill_registry import SkillRegistryError, execution_provenance

_RECORDING_SKILLS = frozenset({"product-walkthrough", "sop-training", "feature-delta"})
_DOCUMENT_SKILLS = frozenset({"leadership-brief", "launch-announcement"})
_WORKBOOK_SKILLS = frozenset(
    {"weekly-ops-review", "finance-wbr", "half-year-business-review"}
)
_MIXED_SKILLS = frozenset({"executive-business-review"})


def compile_uploaded(
    *,
    skill_id: str,
    title: str,
    segments: list[dict[str, Any]] | None = None,
    document: bytes | None = None,
    workbook: bytes | None = None,
) -> dict[str, Any]:
    """Build a cited script and persist skill/craft provenance in it."""
    try:
        provenance = execution_provenance(skill_id)
    except SkillRegistryError as exc:
        raise CompileError([str(exc)]) from exc

    spoken = [dict(segment) for segment in (segments or []) if (segment.get("text") or "").strip()]

    if skill_id in _RECORDING_SKILLS and spoken:
        script = compile_recording(spoken, skill_id=skill_id, title=title or "Walkthrough")
        _attach_provenance(script, provenance)
        _approve(script)
        return script

    if skill_id in _WORKBOOK_SKILLS or (
        workbook and not document and skill_id not in _DOCUMENT_SKILLS and not spoken
    ):
        if not workbook:
            raise CompileError([f"{skill_id} needs a workbook upload"])
        pack = parse_workbook(workbook)
        script = compile_workbook(pack, skill_id)
        _attach_provenance(script, provenance)
        _approve(script, pack, cell_index(pack))
        return script

    if skill_id in _MIXED_SKILLS:
        if workbook:
            pack = parse_workbook(workbook)
            script = compile_workbook(pack, skill_id)
            _attach_provenance(script, provenance)
            if document:
                script["supporting_document_present"] = True
            _approve(script, pack, cell_index(pack))
            return script
        if document:
            script = compile_document(_load_document(document), skill_id)
            _attach_provenance(script, provenance)
            _approve(script)
            return script
        raise CompileError([f"{skill_id} needs a workbook or document upload"])

    if document and (skill_id in _DOCUMENT_SKILLS or not spoken):
        doc_skill = skill_id if skill_id in _DOCUMENT_SKILLS else "leadership-brief"
        script = compile_document(_load_document(document), doc_skill)
        if doc_skill != skill_id:
            # The user selected a recording-oriented default but uploaded only
            # a document. Record the actual execution contract, not the UI default.
            try:
                provenance = execution_provenance(doc_skill)
            except SkillRegistryError as exc:
                raise CompileError([str(exc)]) from exc
        _attach_provenance(script, provenance)
        _approve(script)
        return script

    if skill_id in _RECORDING_SKILLS:
        raise CompileError(["transcribe first"])
    raise CompileError(["upload a supported workbook, PDF/DOCX, or recording before compile"])


def _attach_provenance(script: dict[str, Any], provenance: dict[str, object]) -> None:
    script["provenance"] = provenance
    script["skill_version"] = str(provenance["skill_version"])
    script["skill_contract"] = provenance.get("contract_text") or ""
    script["craft_contracts"] = provenance.get("craft_contracts") or {}


def _approve(
    script: dict[str, Any],
    pack: dict[str, Any] | None = None,
    cells: dict[tuple[str, str], Any] | None = None,
) -> None:
    result = direct(script, pack, cells)
    if result["errors"]:
        raise CompileError(result["errors"])


def _load_document(data: bytes) -> dict[str, Any]:
    if data.startswith(b"%PDF"):
        try:
            return parse_pdf(data)
        except IngestError as exc:
            raise CompileError([str(exc)]) from exc
    if data[:2] == b"PK":
        try:
            return parse_docx(data)
        except IngestError as exc:
            raise CompileError([str(exc)]) from exc
    if data.lstrip()[:1] in {b"{", b"["}:
        return _json_object(data, "document")
    raise CompileError(["document must be a PDF, DOCX, or JSON block pack"])


def _json_object(data: bytes, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as exc:
        raise CompileError([f"{label} is not JSON ({exc.msg})"]) from exc
    if not isinstance(parsed, dict):
        raise CompileError([f"{label} must be a JSON object"])
    return parsed
