"""Route a skill id onto the deck or recording compiler. Empty KPIs still fail closed."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .brand import brand_lock
from .compile_deck import (
    CompileError,
    _movers_beat,
    _text_claims,
    cell_index,
    compile_document,
    compile_workbook,
)
from .contracts import runtime_for
from .compile_recording import compile_recording
from .continuity import verify_carry
from .formats import placement_plan
from .layouts import SKILL_LAYOUTS, SKILL_RENDERER, SLIDESHOW_SKILLS
from .quality import gate_script, refine_actions
from .ingest_workbook import parse_workbook
from .skill_registry import SkillRegistryError, execution_provenance, resolve_skill

WORKBOOK_SKILLS = frozenset(
    {
        "weekly-ops-review",
        "finance-wbr",
        "half-year-business-review",
        "executive-business-review",
        "wbr-kpi-spine",
        "wbr-executive",
        "wbr-ops-deep-dive",
        "wbr-ask-pack",
        "wbr-exception-only",
        "kpi-spotlight-deck",
        "comparison-versus-deck",
        "risk-and-ask-deck",
        "one-pager-summary-deck",
    }
)

RECORDING_SKILLS = frozenset(
    {
        "product-walkthrough",
        "sop-training",
        "feature-delta",
        "chaptered-demo-cut",
        "continuous-take-demo",
        "carry-boundary-verify",
        "caption-studio-local",
        "local-video-assembly",
        "storyboard-from-chapters",
        "text-overlay-cards",
        "narration-room-mix",
        "identity-consistency-lock",
    }
) | SLIDESHOW_SKILLS

FLEX = frozenset(
    {
        "offline-quality-gate",
        "offline-refine-loop",
        "placement-formats-export",
        "brand-kit-lock",
    }
)

CARRY_CHECK = frozenset({"carry-boundary-verify", "continuous-take-demo"})


@dataclass
class SourceDoc:
    asset_id: str | None
    kind: str  # document | presentation | image
    doc: dict[str, Any]


@dataclass
class SourceBundle:
    """Everything a briefing may cite, each piece tagged with its asset id."""

    workbook: bytes | None = None
    workbook_asset: str | None = None
    documents: list[SourceDoc] = field(default_factory=list)
    segments: list[dict[str, Any]] = field(default_factory=list)
    recording_asset: str | None = None
    duration_ms: int | None = None

    def kinds(self) -> set[str]:
        present = {doc.kind for doc in self.documents}
        if self.workbook:
            present.add("workbook")
        if self.spoken():
            present.add("recording")
        return present

    def spoken(self) -> list[dict[str, Any]]:
        return [dict(seg) for seg in self.segments if (seg.get("text") or "").strip()]


def compile_for_skill(
    *,
    skill_id: str,
    title: str,
    segments: list[dict[str, Any]] | None,
    document: bytes | None,
    workbook: bytes | None,
    sources: Any,
) -> dict[str, Any]:
    """Legacy single-asset entry point."""
    bundle = SourceBundle(workbook=workbook, segments=list(segments or []))
    if document:
        bundle.documents.append(SourceDoc(None, "document", sources.load_document(document)))
    return compile_bundle(skill_id=skill_id, title=title, bundle=bundle, sources=sources)


def compile_bundle(*, skill_id: str, title: str, bundle: SourceBundle, sources: Any = None) -> dict[str, Any]:
    if sources is None:
        from . import compile_sources as sources
    try:
        skill, crafts = resolve_skill(skill_id)
        runtime = runtime_for(skill, crafts)
    except SkillRegistryError as exc:
        raise CompileError([str(exc)]) from exc
    input_errors = runtime.check_inputs(bundle.kinds())
    if input_errors:
        raise CompileError(input_errors)

    spoken = bundle.spoken()
    documents = list(bundle.documents)
    workbook = bundle.workbook
    if skill_id in FLEX:
        if spoken:
            chosen = "product-walkthrough"
        elif workbook and not documents:
            chosen = "weekly-ops-review"
        elif documents:
            chosen = "leadership-brief"
        else:
            chosen = "product-walkthrough"
    else:
        chosen = skill_id

    if workbook and (
        chosen in WORKBOOK_SKILLS
        or (not documents and chosen not in sources.DOCUMENT_SKILLS and not spoken)
    ):
        pack = parse_workbook(workbook)
        target = chosen if chosen in WORKBOOK_SKILLS else "weekly-ops-review"
        extra = _document_notes(documents, target) if documents and _accepts_documents(runtime) else []
        script = specialize_workbook(pack, target, extra_beats=extra)
        _tag(script, "workbook", bundle.workbook_asset)
        if pack.get("data_quality"):
            script["data_quality"] = list(pack["data_quality"])
        _finish(script, skill_id if skill_id in FLEX else target, pack)
        _contract_gate(script, skill_id if skill_id in FLEX else target, cell_index(pack))
        _approve(script, cells=cell_index(pack))
        return script

    if chosen in WORKBOOK_SKILLS and chosen != "executive-business-review" and not workbook:
        raise CompileError([f"{skill_id} needs a workbook upload"])

    if documents and not spoken and chosen in TRAINING_SKILLS:
        course = "onboarding-guide" if chosen == "onboarding-guide" else "training-course"
        script = _compile_course(documents, course)
        _finish(script, course, None)
        _contract_gate(script, course, None)
        _approve(script)
        return script

    if documents and (chosen in sources.DOCUMENT_SKILLS or not spoken):
        doc_skill = chosen if chosen in sources.DOCUMENT_SKILLS else "leadership-brief"
        script = _compile_documents(documents, doc_skill)
        _finish(script, skill_id if skill_id in FLEX else doc_skill, None)
        _contract_gate(script, skill_id if skill_id in FLEX else doc_skill, None)
        _approve(script)
        return script

    if chosen in RECORDING_SKILLS or skill_id in RECORDING_SKILLS:
        if not spoken:
            raise CompileError(["transcribe first"])
        record_as = chosen if chosen in RECORDING_SKILLS else skill_id
        script = compile_recording(
            spoken,
            skill_id=record_as,
            title=title or "Walkthrough",
            carry=record_as not in SLIDESHOW_SKILLS,
        )
        _tag(script, "recording", bundle.recording_asset)
        if bundle.duration_ms:
            script["source_duration_ms"] = max(int(bundle.duration_ms), int(script.get("source_duration_ms") or 0))
        _finish(script, skill_id if skill_id in FLEX else record_as, None)
        if record_as in CARRY_CHECK or skill_id in CARRY_CHECK:
            errors = verify_carry(script)
            if errors:
                raise CompileError(errors)
        _contract_gate(script, skill_id if skill_id in FLEX else record_as, None)
        _approve(script)
        return script

    if skill_id in RECORDING_SKILLS:
        raise CompileError(["transcribe first"])
    raise CompileError(["upload a workbook, PDF/DOCX/PPTX, screenshot, or recording before compile"])


TRAINING_SKILLS = frozenset({"onboarding-guide", "training-course", "training-quiz-deck", "sop-training"})


def _compile_course(documents: list[SourceDoc], skill_id: str) -> dict[str, Any]:
    from .compile_deck import compile_training

    primary = documents[0]
    script = compile_training(primary.doc, skill_id)
    _tag(script, "document", primary.asset_id, pages=_pages(primary.doc))
    for extra in documents[1:]:
        more = compile_training(extra.doc, skill_id)
        _tag(more, "document", extra.asset_id, pages=_pages(extra.doc))
        script["beats"].extend(beat for beat in more["beats"] if beat.get("layout") != "cover")
    step = 0
    for index, beat in enumerate(script["beats"], start=1):
        beat["ord"] = index
        if beat.get("kind") == "step":
            step += 1
            beat["slots"]["step"] = step
            beat["slots"]["eyebrow"] = f"Step {step}"
    script["course"] = {
        "steps": step,
        "checkpoints": sum(1 for beat in script["beats"] if beat.get("kind") == "checkpoint"),
    }
    return script


def _accepts_documents(runtime) -> bool:
    return bool(runtime.accepts & {"document", "presentation", "image"})


def _document_notes(documents: list[SourceDoc], skill_id: str) -> list[dict[str, Any]]:
    """Risk/ask beats quoted verbatim from accompanying documents."""
    allowed = SKILL_LAYOUTS.get(skill_id, frozenset())
    beats: list[dict[str, Any]] = []
    for source in documents:
        for block in source.doc.get("blocks") or []:
            role = block.get("role")
            text = str(block.get("text") or "").strip()
            if role not in {"risk", "ask"} or role not in allowed or not text:
                continue
            cite = {"kind": "document", "block_id": block["id"]}
            if source.asset_id:
                cite["asset_id"] = source.asset_id
            if block.get("page") is not None:
                cite["page"] = block["page"]
            beats.append(
                {
                    "kind": role,
                    "layout": role,
                    "text": text,
                    "slots": {"eyebrow": role.capitalize()},
                    "claims": _text_claims(text, block["id"]),
                    "citations": [cite],
                }
            )
    return beats


def _compile_documents(documents: list[SourceDoc], skill_id: str) -> dict[str, Any]:
    primary = documents[0]
    script = compile_document(primary.doc, skill_id)
    _tag(script, "document", primary.asset_id, pages=_pages(primary.doc))
    for extra in documents[1:]:
        more = compile_document(extra.doc, skill_id)
        _tag(more, "document", extra.asset_id, pages=_pages(extra.doc))
        # The extra document's own cover becomes an evidence statement only
        # when the skill allows statements; otherwise it is skipped.
        body = [beat for beat in more["beats"] if beat.get("layout") != "cover"]
        script["beats"].extend(body)
    for index, beat in enumerate(script["beats"], start=1):
        beat["ord"] = index
    return script


def _pages(doc: dict[str, Any]) -> dict[str, int]:
    return {str(block.get("id")): int(block["page"]) for block in doc.get("blocks") or [] if block.get("page") is not None}


def _tag(script: dict[str, Any], kind: str, asset_id: str | None, pages: dict[str, int] | None = None) -> None:
    for beat in script.get("beats") or []:
        for cite in beat.get("citations") or []:
            if cite.get("kind") != kind:
                continue
            if asset_id and not cite.get("asset_id"):
                cite["asset_id"] = asset_id
            if pages and cite.get("block_id") in pages and "page" not in cite:
                cite["page"] = pages[cite["block_id"]]


def _contract_gate(script: dict[str, Any], skill_id: str, cells: dict | None) -> None:
    from .contracts import run_checks

    try:
        skill, crafts = resolve_skill(skill_id)
        runtime = runtime_for(skill, crafts)
    except SkillRegistryError as exc:
        raise CompileError([str(exc)]) from exc
    errors = run_checks(script, runtime, cells)
    if errors:
        raise CompileError(errors)
    script.setdefault("provenance", {})["checks_run"] = ["layout-allowed", "max-slides", *runtime.checks]


def specialize_workbook(
    pack: dict[str, Any], skill_id: str, extra_beats: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Build the full cited deck, then narrow. Empty required KPIs fail first."""
    full = compile_workbook(pack, "weekly-ops-review")
    if extra_beats:
        asks = [beat for beat in full["beats"] if beat.get("layout") == "ask"]
        head = [beat for beat in full["beats"] if beat.get("layout") != "ask"]
        doc_risks = [beat for beat in extra_beats if beat.get("layout") == "risk"]
        doc_asks = [beat for beat in extra_beats if beat.get("layout") == "ask"]
        full = {**full, "beats": head + doc_risks + asks + doc_asks}
    if skill_id in {"weekly-ops-review", "finance-wbr", "half-year-business-review", "wbr-kpi-spine", "wbr-ops-deep-dive", "brand-kit-lock"}:
        beats = list(full["beats"])
    elif skill_id in {"wbr-executive", "executive-business-review"}:
        beats = _executive(full, pack)
    elif skill_id == "wbr-ask-pack":
        beats = _keep(full, {"cover", "ask"})
    elif skill_id == "risk-and-ask-deck":
        beats = _keep(full, {"cover", "risk", "ask"})
        if not any(beat["layout"] in {"risk", "ask"} for beat in beats):
            raise CompileError(["risk-and-ask-deck needs a risk or an ask in the workbook"])
    elif skill_id == "kpi-spotlight-deck":
        beats = _keep(full, {"cover", "big-number", "versus-target"})
    elif skill_id == "comparison-versus-deck":
        beats = _keep(full, {"cover", "versus-target"})
        if not any(beat["layout"] == "versus-target" for beat in beats):
            raise CompileError(["comparison-versus-deck needs a filled target cell"])
    elif skill_id == "one-pager-summary-deck":
        beats = list(full["beats"])[:6]
    elif skill_id == "wbr-exception-only":
        beats = _exceptions(full, pack)
    elif skill_id == "placement-formats-export":
        beats = list(full["beats"])
    else:
        beats = list(full["beats"])
    if skill_id == "kpi-spotlight-deck" and len(beats) > 16:
        raise CompileError(["kpi-spotlight-deck stops at 16 slides"])
    if skill_id in {"wbr-executive", "executive-business-review"} and len(beats) > 6:
        raise CompileError(["wbr-executive keeps at most 6 slides"])
    script = dict(full)
    script["beats"] = []
    for index, beat in enumerate(beats, start=1):
        copied = dict(beat)
        copied["ord"] = index
        script["beats"].append(copied)
    script["skill_id"] = skill_id
    script["renderer"] = SKILL_RENDERER.get(skill_id, "deck")
    return script


def _executive(full: dict[str, Any], pack: dict[str, Any]) -> list[dict[str, Any]]:
    risks = [note for note in pack.get("risks") or [] if (note.get("text") or "").strip()]
    asks = [note for note in pack.get("asks") or [] if (note.get("text") or "").strip()]
    if len(risks) > 1 and not any(note.get("primary") for note in risks):
        raise CompileError(["wbr-executive has multiple risks and none is marked primary"])
    if len(asks) > 1 and not any(note.get("primary") for note in asks):
        raise CompileError(["wbr-executive has multiple asks and none is marked primary"])
    cover = _keep(full, {"cover"})
    kpis = [beat for beat in full["beats"] if beat["layout"] in {"big-number", "versus-target"}][:1]
    rows = [
        row
        for row in pack.get("movers") or []
        if row.get("value") is not None and row.get("prior") is not None
    ]
    rows.sort(key=lambda row: abs(row["value"] - row["prior"]), reverse=True)
    movers = [_movers_beat(rows[:3])] if rows else []
    risk_beats = [beat for beat in full["beats"] if beat["layout"] == "risk"][:1]
    ask_beats = [beat for beat in full["beats"] if beat["layout"] == "ask"][:1]
    return cover + kpis + movers + risk_beats + ask_beats


def _exceptions(full: dict[str, Any], pack: dict[str, Any]) -> list[dict[str, Any]]:
    flagged = list(pack.get("exceptions") or [])
    if flagged:
        return _keep(full, {"cover", "risk", "ask"})
    title = pack.get("title") or {}
    cover = _keep(full, {"cover"})
    note = {
        "kind": "statement",
        "layout": "statement",
        "text": "No exceptions are flagged this week.",
        "slots": {"eyebrow": "Exceptions"},
        "claims": [],
        "citations": [{"kind": "workbook", "sheet": title.get("sheet") or "Notes", "addr": title.get("addr") or "A1"}],
    }
    return cover + [note]


def _keep(full: dict[str, Any], layouts: set[str]) -> list[dict[str, Any]]:
    return [beat for beat in full["beats"] if beat.get("layout") in layouts]


def _finish(script: dict[str, Any], skill_id: str, pack: dict[str, Any] | None) -> None:
    script["skill_id"] = skill_id
    try:
        provenance = execution_provenance(skill_id)
    except SkillRegistryError as exc:
        raise CompileError([str(exc)]) from exc
    script["skill_version"] = str(provenance["skill_version"])
    script["provenance"] = provenance
    script["skill_contract"] = provenance.get("contract_text") or ""
    script["craft_contracts"] = provenance.get("craft_contracts") or {}
    if skill_id in SKILL_RENDERER:
        script["renderer"] = SKILL_RENDERER[skill_id]
    report = gate_script(script, cells=cell_index(pack) if pack else None)
    script["quality"] = {"status": report["status"], "warnings": report["warnings"]}
    if skill_id == "offline-refine-loop":
        script["refine"] = refine_actions(report)
    if skill_id in {"offline-quality-gate", "carry-boundary-verify", "offline-refine-loop"} and report["errors"]:
        raise CompileError(report["errors"])
    if skill_id in {"placement-formats-export", "continuous-take-demo"} or script.get("renderer") == "recording":
        script["placements"] = placement_plan()
    if skill_id == "brand-kit-lock" or script.get("renderer") == "deck":
        script["brand"] = brand_lock()
    screens = []
    for cut in (script.get("edit") or {}).get("cuts") or []:
        screen = str(cut.get("screen") or "").strip()
        if screen and screen not in screens:
            screens.append(screen)
    if screens:
        script["identity"] = {"screens": screens, "source": "capture-labels"}


def _approve(script: dict[str, Any], cells: dict | None = None) -> None:
    from .director import direct

    result = direct(script, None, cells)
    if result["errors"]:
        raise CompileError(result["errors"])
