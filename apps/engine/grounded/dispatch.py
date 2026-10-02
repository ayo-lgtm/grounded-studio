"""Route a skill id onto the deck or recording compiler. Empty KPIs still fail closed."""

from __future__ import annotations

from typing import Any

from .brand import brand_lock
from .compile_deck import CompileError, _movers_beat, cell_index, compile_document, compile_workbook
from .compile_recording import compile_recording
from .continuity import verify_carry
from .formats import placement_plan
from .layouts import SKILL_RENDERER, SLIDESHOW_SKILLS
from .quality import gate_script, refine_actions
from .ingest_workbook import parse_workbook
from .skill_registry import SkillRegistryError, execution_provenance

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


def compile_for_skill(
    *,
    skill_id: str,
    title: str,
    segments: list[dict[str, Any]] | None,
    document: bytes | None,
    workbook: bytes | None,
    sources: Any,
) -> dict[str, Any]:
    spoken = [dict(segment) for segment in (segments or []) if (segment.get("text") or "").strip()]
    if skill_id in FLEX:
        if spoken:
            chosen = "product-walkthrough"
        elif workbook and not document:
            chosen = "weekly-ops-review"
        elif document:
            chosen = "leadership-brief"
        else:
            chosen = "product-walkthrough"
    else:
        chosen = skill_id

    if workbook and (
        chosen in WORKBOOK_SKILLS
        or (not document and chosen not in sources.DOCUMENT_SKILLS and not spoken)
    ):
        pack = parse_workbook(workbook)
        target = chosen if chosen in WORKBOOK_SKILLS else "weekly-ops-review"
        script = specialize_workbook(pack, target)
        _finish(script, skill_id if skill_id in FLEX else target, pack)
        _approve(script, cells=cell_index(pack))
        return script

    if chosen in WORKBOOK_SKILLS and chosen != "executive-business-review" and not workbook:
        raise CompileError([f"{skill_id} needs a workbook upload"])

    if document and (chosen in sources.DOCUMENT_SKILLS or not spoken):
        doc_skill = chosen if chosen in sources.DOCUMENT_SKILLS else "leadership-brief"
        script = compile_document(sources.load_document(document), doc_skill)
        _finish(script, skill_id if skill_id in FLEX else doc_skill, None)
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
        _finish(script, skill_id if skill_id in FLEX else record_as, None)
        if record_as in CARRY_CHECK or skill_id in CARRY_CHECK:
            errors = verify_carry(script)
            if errors:
                raise CompileError(errors)
        _approve(script)
        return script

    if skill_id in RECORDING_SKILLS:
        raise CompileError(["transcribe first"])
    raise CompileError(["upload a workbook, PDF/DOCX, or recording before compile"])


def specialize_workbook(pack: dict[str, Any], skill_id: str) -> dict[str, Any]:
    """Build the full cited deck, then narrow. Empty required KPIs fail first."""
    full = compile_workbook(pack, "weekly-ops-review")
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
