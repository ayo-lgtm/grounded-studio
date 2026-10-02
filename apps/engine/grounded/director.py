"""The director's cut: pro structure and pacing that can never break the skill.

The director writes and re-cuts like a veteran broadcast director — story
arc, emphasis, pacing, broadcast-ready copy — but every decision routes
through the skill contract: locked layouts, QA gates, authored number
surfaces, and the completeness rule (no required datum is ever skipped,
rounded away, or removed). A treatment or user revision that fails any
gate is refused with a reason, and the previous script stands.
"""

from __future__ import annotations

import copy
from typing import Any

from .numbers import close, parse_numbers
from .qa import DISPLAY_KEYS, validate_script

_REFUSAL_USAGE = (
    'I can "focus <topic>" to lead with a beat, or "polish" the copy. '
    "I never drop, skip, or shorten data."
)


def surface_locks(pack: dict[str, Any]) -> dict[tuple[str, str], str]:
    """Authored number surfaces, shown exactly as written in the source."""
    locks: dict[tuple[str, str], str] = {}
    for kpi in pack.get("kpis") or []:
        if kpi.get("display"):
            locks[(kpi["sheet"], kpi["addr"])] = kpi["display"]
        if kpi.get("target_addr") and kpi.get("target_display"):
            locks[(kpi.get("target_sheet") or kpi["sheet"], kpi["target_addr"])] = kpi[
                "target_display"
            ]
    for row in pack.get("movers") or []:
        if row.get("display"):
            locks[(row["sheet"], row["addr"])] = row["display"]
        if row.get("prior_display"):
            locks[(row["sheet"], row["prior_addr"])] = row["prior_display"]
    return locks


def check_surfaces(
    script: dict[str, Any], locks: dict[tuple[str, str], str]
) -> list[str]:
    """Every authored surface must appear verbatim in a beat citing its cell."""
    errors: list[str] = []
    for (sheet, addr), surface in sorted(locks.items()):
        shown = any(
            surface in shown_text
            for beat in script.get("beats") or []
            if _cites_cell(beat, sheet, addr)
            for shown_text in _shown_texts(beat)
        )
        if not shown:
            errors.append(f"surface {surface!r} from {sheet}!{addr} is not shown verbatim")
    return errors


def check_coverage(pack: dict[str, Any], script: dict[str, Any]) -> list[str]:
    """Every required datum must reach the script. Nothing skipped, nothing cut."""
    errors: list[str] = []
    beats = script.get("beats") or []
    for kpi in pack.get("kpis") or []:
        if not any(_cites_cell(beat, kpi["sheet"], kpi["addr"]) for beat in beats):
            errors.append(
                f"coverage: KPI {kpi.get('label')} ({kpi['sheet']}!{kpi['addr']}) has no beat"
            )
    tables = [
        row.get("line")
        for beat in beats
        for row in ((beat.get("slots") or {}).get("rows") or [])
    ]
    for row in pack.get("movers") or []:
        if row.get("label") not in tables:
            errors.append(f"coverage: mover row {row.get('label')} is missing from the table")
    texts = [str(beat.get("text") or "") for beat in beats]
    for note in list(pack.get("risks") or []) + list(pack.get("asks") or []):
        if (note.get("text") or "").strip() and note["text"].strip() not in texts:
            errors.append(f"coverage: note {note['text'].strip()[:40]!r} is missing")
    return errors


def check_claims_shown(script: dict[str, Any]) -> list[str]:
    """Every cited numeric claim must be visible in its own beat."""
    errors: list[str] = []
    for beat in script.get("beats") or []:
        shown = parse_numbers("\n".join(_shown_texts(beat)))
        for claim in beat.get("claims") or []:
            value = claim.get("value")
            if not claim.get("sheet") or not claim.get("addr"):
                continue
            if not isinstance(value, (int, float)):
                continue
            if not any(close(number, float(value)) for number in shown):
                errors.append(
                    f"beat {beat.get('ord')} hides cited claim "
                    f"{claim['sheet']}!{claim['addr']} ({value})"
                )
    return errors


def direct(
    script: dict[str, Any],
    pack: dict[str, Any] | None = None,
    cells: dict[tuple[str, str], Any] | None = None,
) -> dict[str, Any]:
    """Approve the cut and annotate it with the director's notes.

    Read-only: the script comes back unchanged. Notes record the story
    arc, the emphasis beat, the pacing read, and the locks enforced.
    """
    notes: list[str] = []
    errors = validate_script(
        script, duration_ms=script.get("source_duration_ms"), cells=cells
    )
    locks: dict[tuple[str, str], str] = {}
    if pack is not None:
        locks = surface_locks(pack)
        errors += check_coverage(pack, script)
        errors += check_surfaces(script, locks)
    errors += check_claims_shown(script)
    if errors:
        return {"script": script, "notes": notes, "errors": errors}
    notes.append(_arc_note(script))
    notes.append(_emphasis_note(script))
    if (script.get("renderer") or "") == "recording":
        notes.append(_pacing_note(script))
    if locks:
        notes.append(f"Locked {len(locks)} authored number surfaces.")
    if pack is not None:
        notes.append(_coverage_note(pack))
    return {"script": script, "notes": notes, "errors": []}


def revise(
    script: dict[str, Any],
    instruction: str,
    pack: dict[str, Any] | None = None,
    cells: dict[tuple[str, str], Any] | None = None,
    client: Any = None,
) -> dict[str, Any]:
    """Re-cut the script on instruction. The gates re-run; failures refuse.

    Returns {"script", "notes", "applied"}. On refusal the ORIGINAL script
    object comes back untouched.
    """
    text = (instruction or "").strip()
    lowered = text.lower()
    if _is_drop_request(lowered):
        return _refuse(
            script,
            f'Refused "{text}": the director never drops, skips, or shortens data.',
        )
    if lowered.startswith(("focus ", "lead with ", "start with ")):
        term = _term_of(text)
        if not term:
            return _refuse(script, 'Refused: "focus" needs a topic, e.g. "focus revenue".')
        return _revise_focus(script, term, pack, cells)
    if lowered == "polish" or lowered.startswith("polish "):
        return _revise_polish(script, text, pack, cells, client)
    return _refuse(script, f'Refused "{text}": unknown direction. {_REFUSAL_USAGE}')


def _revise_focus(
    script: dict[str, Any],
    term: str,
    pack: dict[str, Any] | None,
    cells: dict[tuple[str, str], Any] | None,
) -> dict[str, Any]:
    if (script.get("renderer") or "") == "recording":
        return _refuse(
            script,
            f'Refused "focus {term}": the picture is cut to the words — '
            "reordering beats would unsync the film.",
        )
    beats = list(script.get("beats") or [])
    head = beats[:1] if beats and beats[0].get("layout") == "cover" else []
    rest = beats[len(head):]
    matched = [beat for beat in rest if term in _searchable(beat)]
    if not matched:
        return _refuse(script, f'Refused "focus {term}": no beat mentions it.')
    others = [beat for beat in rest if beat not in matched]
    candidate = copy.deepcopy(script)
    candidate["beats"] = copy.deepcopy(head + matched + others)
    for index, beat in enumerate(candidate["beats"], start=1):
        beat["ord"] = index
    errors = _gates(candidate, pack, cells)
    if errors:
        return _refuse(
            script, f'Refused "focus {term}": the re-cut breaks the skill ({errors[0]}).'
        )
    return {
        "script": candidate,
        "notes": [f"Leading with {len(matched)} beat(s) on {term!r}; all gates still pass."],
        "applied": True,
    }


def _revise_polish(
    script: dict[str, Any],
    instruction: str,
    pack: dict[str, Any] | None,
    cells: dict[tuple[str, str], Any] | None,
    client: Any,
) -> dict[str, Any]:
    from .local_model import LocalModel, LocalModelError

    target: int | None = None
    words = instruction.lower().split()
    if "beat" in words:
        try:
            target = int(words[words.index("beat") + 1])
        except (ValueError, IndexError):
            return _refuse(script, f'Refused "{instruction}": "polish beat N" needs a number.')
        if not any(beat.get("ord") == target for beat in script.get("beats") or []):
            return _refuse(script, f'Refused "{instruction}": there is no beat {target}.')
    candidate = copy.deepcopy(script)
    notes: list[str] = []
    chat = client if client is not None else LocalModel()
    locks = surface_locks(pack) if pack is not None else {}
    for beat in candidate.get("beats") or []:
        if target is not None and beat.get("ord") != target:
            continue
        if beat.get("layout") == "cover":
            continue
        old_text = str(beat.get("text") or "")
        wanted = sorted(_beat_locks(beat, locks))
        try:
            import json as _json

            raw = chat.complete(_POLISH_SYSTEM, _polish_prompt(beat, old_text, wanted))
            new_text = str(_json.loads(raw).get("text") or "").strip()
        except (LocalModelError, ValueError, AttributeError):
            notes.append(f"beat {beat.get('ord')} kept verbatim (Claude unavailable).")
            continue
        problem = _polish_problem(beat, old_text, new_text, wanted)
        if problem:
            notes.append(f"beat {beat.get('ord')} kept verbatim ({problem}).")
            continue
        beat["text"] = new_text
        notes.append(f"beat {beat.get('ord')} polished.")
    errors = _gates(candidate, pack, cells)
    if errors:
        original = copy.deepcopy(script)
        return {
            "script": original,
            "notes": [f"Polish reverted: the re-cut breaks the skill ({errors[0]})."],
            "applied": False,
        }
    if not notes:
        notes.append("Nothing to polish.")
    changed = any(
        str(new.get("text") or "") != str(old.get("text") or "")
        for new, old in zip(candidate.get("beats") or [], script.get("beats") or [])
    )
    return {"script": candidate, "notes": notes, "applied": changed}


def _polish_problem(
    beat: dict[str, Any], old_text: str, new_text: str, wanted: list[str]
) -> str | None:
    if not new_text:
        return "empty reply"
    old_numbers = sorted(parse_numbers(old_text))
    new_numbers = sorted(parse_numbers(new_text))
    if len(new_numbers) != len(old_numbers) or any(
        not close(new, old) for new, old in zip(new_numbers, old_numbers)
    ):
        return "numbers drifted"
    for surface in wanted:
        if surface not in new_text:
            return f"dropped surface {surface!r}"
    return None


def _gates(
    script: dict[str, Any],
    pack: dict[str, Any] | None,
    cells: dict[tuple[str, str], Any] | None,
) -> list[str]:
    errors = validate_script(
        script, duration_ms=script.get("source_duration_ms"), cells=cells
    )
    if pack is not None:
        errors += check_coverage(pack, script)
        errors += check_surfaces(script, surface_locks(pack))
    errors += check_claims_shown(script)
    return errors


def _refuse(script: dict[str, Any], note: str) -> dict[str, Any]:
    return {"script": script, "notes": [note], "applied": False}


def _is_drop_request(lowered: str) -> bool:
    return lowered.startswith(
        ("drop ", "remove ", "delete ", "cut ", "shorten", "skip ", "lose ", "without ")
    )


def _term_of(instruction: str) -> str:
    lowered = instruction.lower()
    for prefix in ("focus ", "lead with ", "start with "):
        if lowered.startswith(prefix):
            term = instruction[len(prefix):].strip().strip("\"'")
            return term.lower()
    return ""


def _searchable(beat: dict[str, Any]) -> str:
    slots = beat.get("slots") or {}
    return f"{beat.get('text') or ''} {slots.get('eyebrow') or ''}".lower()


def _cites_cell(beat: dict[str, Any], sheet: str, addr: str) -> bool:
    return any(
        cite.get("kind") == "workbook"
        and cite.get("sheet") == sheet
        and cite.get("addr") == addr
        for cite in beat.get("citations") or []
    )


def _beat_locks(
    beat: dict[str, Any], locks: dict[tuple[str, str], str]
) -> list[str]:
    wanted = []
    for cite in beat.get("citations") or []:
        if cite.get("kind") != "workbook":
            continue
        surface = locks.get((cite.get("sheet"), cite.get("addr")))
        if surface:
            wanted.append(surface)
    return wanted


def _shown_texts(beat: dict[str, Any]) -> list[str]:
    strings = [str(beat.get("text") or "")]
    slots = beat.get("slots") or {}
    for key in DISPLAY_KEYS:
        value = slots.get(key)
        if isinstance(value, str):
            strings.append(value)
    for row in slots.get("rows") or []:
        for value in row.values():
            if isinstance(value, str):
                strings.append(value)
    visual = beat.get("visual") or {}
    for row in visual.get("rows") or []:
        for cell in row:
            value = cell.get("display") if isinstance(cell, dict) else None
            if isinstance(value, str):
                strings.append(value)
    return strings


def _arc_note(script: dict[str, Any]) -> str:
    beats = [beat for beat in script.get("beats") or [] if beat.get("layout") != "cover"]
    kinds = [beat.get("kind") for beat in beats]
    closers = sum(1 for kind in kinds if kind in {"ask", "risk"})
    evidence = len(kinds) - closers
    return f"Arc: cover -> {evidence} evidence beats -> {closers} closing beats."


def _emphasis_note(script: dict[str, Any]) -> str:
    best_ord: Any = None
    best_value = -1.0
    for beat in script.get("beats") or []:
        for claim in beat.get("claims") or []:
            value = claim.get("value")
            if claim.get("derived") and isinstance(value, (int, float)) and abs(value) > best_value:
                best_value = abs(value)
                best_ord = beat.get("ord")
    if best_ord is None:
        first = next(
            (beat.get("ord") for beat in script.get("beats") or [] if beat.get("layout") != "cover"),
            None,
        )
        return f"Emphasis: beat {first} opens the evidence."
    return f"Emphasis: beat {best_ord} carries the largest swing."


def _pacing_note(script: dict[str, Any]) -> str:
    cuts = list((script.get("edit") or {}).get("cuts") or [])
    if not cuts:
        return "Pacing: no cuts."
    spans = [int(cut["src_out_ms"]) - int(cut["src_in_ms"]) for cut in cuts]
    screens = sorted({str(cut.get("screen") or "") for cut in cuts if cut.get("screen")})
    flags = []
    for index, span in enumerate(spans):
        if span < 600:
            flags.append(f"cut {index} is tight ({span}ms)")
        elif span > 15000:
            flags.append(f"cut {index} holds long ({span}ms)")
    base = (
        f"Pacing: {len(cuts)} cuts, {min(spans) / 1000:.1f}s–{max(spans) / 1000:.1f}s. "
        f"Screens: {', '.join(screens) or 'untagged'}."
    )
    if flags:
        return base + " " + "; ".join(flags) + "."
    return base


def _coverage_note(pack: dict[str, Any]) -> str:
    count = (
        len(pack.get("kpis") or [])
        + len(pack.get("movers") or [])
        + len([note for note in list(pack.get("risks") or []) + list(pack.get("asks") or []) if (note.get("text") or "").strip()])
    )
    return f"Coverage: all {count} required points present."


_POLISH_SYSTEM = (
    "You are a veteran broadcast writer polishing one briefing beat. "
    "Reply with a single JSON object: {\"text\": <polished beat>}. "
    "Keep every number EXACTLY as written in the locked list — same digits, "
    "same units, same order of magnitude. Never add, round, drop, or reorder "
    "numbers or facts. Same meaning, broadcast polish, one or two sentences."
)


def _polish_prompt(beat: dict[str, Any], text: str, wanted: list[str]) -> str:
    locked = ", ".join(wanted) if wanted else "none"
    return f"Beat {beat.get('ord')} says: \"{text}\"\nLocked numbers: {locked}"
