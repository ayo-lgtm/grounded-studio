"""Executable skill contracts.

A SKILL.md ``## Runtime`` section is machine-read:

``runtime_compiler``      workbook-deck | document-deck | recording | mixed
``runtime_accepts``       source kinds the skill may use
``runtime_requires_any``  at least one of these source kinds must be present
``runtime_layouts``       layouts the skill may emit (subset of renderer layouts)
``runtime_max_slides``    hard slide cap
``runtime_checks``        deterministic check ids (crafts declare theirs too)

Every declared check id must exist in :data:`CHECKS`; an unknown id is a
contract error and the compile fails closed. The checks that ran are
recorded in the briefing provenance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .grounding import CAUSAL, RECOMMEND, _has, recompute
from .layouts import ALL_LAYOUTS, SKILL_LAYOUTS
from .numbers import close, parse_numbers
from .skill_registry import SkillContract, SkillRegistryError

SOURCE_KINDS = frozenset({"workbook", "document", "presentation", "image", "recording"})
COMPILERS = frozenset({"workbook-deck", "document-deck", "recording", "mixed"})

CheckFn = Callable[[dict[str, Any], "SkillRuntime", dict | None], list[str]]


@dataclass(frozen=True)
class SkillRuntime:
    skill_id: str
    compiler: str | None
    accepts: frozenset[str]
    requires_any: frozenset[str]
    layouts: frozenset[str]
    max_slides: int | None
    checks: tuple[str, ...]
    declared: bool

    def describe(self) -> dict[str, Any]:
        return {
            "compiler": self.compiler,
            "accepts": sorted(self.accepts),
            "requires_any": sorted(self.requires_any),
            "layouts": sorted(self.layouts),
            "max_slides": self.max_slides,
            "checks": list(self.checks),
            "declared": self.declared,
        }

    def check_inputs(self, present: set[str]) -> list[str]:
        if not self.declared:
            return []
        errors = []
        unexpected = sorted((present & SOURCE_KINDS) - self.accepts)
        if self.requires_any and not (present & self.requires_any):
            errors.append(
                f"{self.skill_id} needs one of: {', '.join(sorted(self.requires_any))}"
            )
        if unexpected and not (present & self.accepts):
            errors.append(f"{self.skill_id} does not accept {', '.join(unexpected)} sources")
        return errors


def runtime_for(skill: SkillContract, crafts: tuple[SkillContract, ...] = ()) -> SkillRuntime:
    compiler = skill.field("runtime_compiler") or None
    if compiler and compiler not in COMPILERS:
        raise SkillRegistryError(f"{skill.id} declares unknown runtime_compiler {compiler!r}")
    accepts = frozenset(item.lower() for item in skill.items("runtime_accepts"))
    requires = frozenset(item.lower() for item in skill.items("runtime_requires_any"))
    for kind in accepts | requires:
        if kind not in SOURCE_KINDS:
            raise SkillRegistryError(f"{skill.id} declares unknown source kind {kind!r}")
    layouts = frozenset(skill.items("runtime_layouts")) or SKILL_LAYOUTS.get(skill.id, ALL_LAYOUTS)
    unknown_layouts = sorted(layouts - ALL_LAYOUTS)
    if unknown_layouts:
        raise SkillRegistryError(f"{skill.id} declares layouts the renderers lack: {', '.join(unknown_layouts)}")
    cap = skill.field("runtime_max_slides")
    try:
        max_slides = int(cap) if cap else None
    except ValueError as exc:
        raise SkillRegistryError(f"{skill.id} runtime_max_slides must be an integer") from exc
    checks: list[str] = list(skill.items("runtime_checks"))
    for craft in crafts:
        checks.extend(craft.items("runtime_checks"))
    checks = list(dict.fromkeys(checks))
    unknown = [check for check in checks if check not in CHECKS]
    if unknown:
        raise SkillRegistryError(f"contract check ids are not implemented: {', '.join(unknown)}")
    declared = bool(compiler or accepts or skill.items("runtime_checks"))
    return SkillRuntime(
        skill_id=skill.id,
        compiler=compiler,
        accepts=accepts or SOURCE_KINDS,
        requires_any=requires,
        layouts=layouts,
        max_slides=max_slides,
        checks=tuple(checks),
        declared=declared,
    )


def run_checks(script: dict[str, Any], runtime: SkillRuntime, cells: dict | None) -> list[str]:
    errors: list[str] = []
    for check in ("layout-allowed", "max-slides", *runtime.checks):
        errors.extend(CHECKS[check](script, runtime, cells))
    return list(dict.fromkeys(errors))


# ---- check implementations ------------------------------------------------

def _beats(script: dict[str, Any]) -> list[dict[str, Any]]:
    return list(script.get("beats") or [])


def _layout_allowed(script, runtime, _cells):
    return [
        f"beat {beat.get('ord')} layout {beat.get('layout')} is not in the {runtime.skill_id} contract"
        for beat in _beats(script)
        if beat.get("layout") not in runtime.layouts
    ]


def _max_slides(script, runtime, _cells):
    if runtime.max_slides and len(_beats(script)) > runtime.max_slides:
        return [f"{runtime.skill_id} contract allows at most {runtime.max_slides} slides"]
    return []


def _citations_present(script, _runtime, _cells):
    return [f"beat {beat.get('ord')} has no citations" for beat in _beats(script) if not beat.get("citations")]


def _cell_exists(script, _runtime, cells):
    if cells is None:
        return []
    errors = []
    for beat in _beats(script):
        for cite in beat.get("citations") or []:
            if cite.get("kind") == "workbook" and (cite.get("sheet"), cite.get("addr")) not in cells:
                errors.append(f"beat {beat.get('ord')} cites {cite.get('sheet')}!{cite.get('addr')}, which is not in the workbook")
    return errors


def _derived_lineage(script, _runtime, _cells):
    errors = []
    for beat in _beats(script):
        for claim in beat.get("claims") or []:
            if claim.get("derived") and (not claim.get("formula") or len(claim.get("operands") or []) < 2):
                errors.append(f"beat {beat.get('ord')} derived claim lacks formula/operands")
    return errors


def _recompute_derived(script, _runtime, cells):
    if cells is None:
        return []
    errors = []
    for beat in _beats(script):
        for claim in beat.get("claims") or []:
            if claim.get("derived") and claim.get("formula"):
                problem = recompute(claim, cells)
                if problem:
                    errors.append(f"beat {beat.get('ord')} {problem}")
    return errors


def _numbers_cited(script, _runtime, _cells):
    from .qa import _displayed

    errors = []
    for beat in _beats(script):
        claims = beat.get("claims") or []
        for number in parse_numbers("\n".join(_displayed(beat))):
            if not any(close(number, float(claim["value"])) for claim in claims):
                errors.append(f"beat {beat.get('ord')} shows {number} without a cited claim")
    return errors


def _source_range_cited(script, _runtime, _cells):
    errors = []
    for beat in _beats(script):
        if beat.get("layout") != "source-range":
            continue
        cited = {(c.get("sheet"), c.get("addr")) for c in beat.get("citations") or []}
        visual = beat.get("visual") or {}
        sheet = next((c.get("sheet") for c in beat.get("citations") or []), None)
        for row in visual.get("rows") or []:
            for cell in row:
                if str(cell.get("display") or "") and (sheet, cell.get("addr")) not in cited:
                    errors.append(f"beat {beat.get('ord')} shows {cell.get('addr')} without citing it")
    return errors


_NUMERIC_KINDS = {"kpi", "movers", "source", "cover"}


def _no_unsourced_causal(script, _runtime, _cells):
    """Arithmetic beats state movement only. Causes/recommendations must be quoted sources."""
    errors = []
    for beat in _beats(script):
        text = str(beat.get("text") or "")
        if beat.get("kind") in _NUMERIC_KINDS:
            found = _has(CAUSAL, text) | _has(RECOMMEND, text)
            if found:
                errors.append(f"beat {beat.get('ord')} adds unsourced explanation ({sorted(found)[0]})")
        for assist in beat.get("assist") or []:
            source = str(assist.get("source_text") or "")
            added = (_has(CAUSAL, text) - _has(CAUSAL, source)) | (_has(RECOMMEND, text) - _has(RECOMMEND, source))
            if added:
                errors.append(f"beat {beat.get('ord')} model text adds unsupported language ({sorted(added)[0]})")
    return errors


def _period_cited(script, _runtime, _cells):
    beats = _beats(script)
    if not beats or beats[0].get("layout") != "cover":
        return []
    cover = beats[0]
    if (cover.get("slots") or {}).get("period") and len(cover.get("citations") or []) < 2:
        return ["cover shows a reporting period without citing it"]
    return []


def _single_unit_ranking(script, _runtime, _cells):
    errors = []
    for beat in _beats(script):
        if beat.get("layout") != "movers":
            continue
        units = {claim.get("unit") for claim in beat.get("claims") or [] if claim.get("unit")}
        if len(units) > 1 and "largest" in str(beat.get("text") or "").lower():
            errors.append(f"beat {beat.get('ord')} ranks movers across units")
    return errors


def _model_text_reviewed(script, _runtime, _cells):
    """Any model-assisted beat must keep the source text it was checked against."""
    errors = []
    for beat in _beats(script):
        for assist in beat.get("assist") or []:
            if not assist.get("source_text") or not assist.get("provider"):
                errors.append(f"beat {beat.get('ord')} model text lacks its grounding record")
    return errors


CHECKS: dict[str, CheckFn] = {
    "layout-allowed": _layout_allowed,
    "max-slides": _max_slides,
    "citations-present": _citations_present,
    "cell-exists": _cell_exists,
    "derived-lineage": _derived_lineage,
    "recompute-derived": _recompute_derived,
    "numbers-cited": _numbers_cited,
    "source-range-cited": _source_range_cited,
    "no-unsourced-causal": _no_unsourced_causal,
    "period-cited": _period_cited,
    "single-unit-ranking": _single_unit_ranking,
    "model-text-reviewed": _model_text_reviewed,
}
