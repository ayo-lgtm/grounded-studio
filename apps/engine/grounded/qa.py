"""Deterministic checks. No model. Fail closed."""

from __future__ import annotations

from typing import Any

from .layouts import ALL_LAYOUTS, FORBIDDEN_KEYS, SKILL_LAYOUTS, SKILL_RENDERER
from .numbers import close, parse_numbers

DISPLAY_KEYS = ("actual", "target", "delta", "period", "body")


def validate_script(
    script: dict[str, Any],
    duration_ms: int | None = None,
    cells: dict[tuple[str, str], Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    beats = script.get("beats") or []
    if not beats:
        return ["script has no beats"]

    skill_id = script.get("skill_id") or ""
    allowed = SKILL_LAYOUTS.get(skill_id, ALL_LAYOUTS)
    renderer = SKILL_RENDERER.get(skill_id)
    if renderer and script.get("renderer") not in {None, renderer}:
        if skill_id != "localize":
            errors.append(f"{skill_id} must render as {renderer}")

    _reject_style_keys(script, errors)

    previous_end = -1
    check_order = skill_id in {"product-walkthrough", "sop-training"}
    for beat in beats:
        ord_ = beat.get("ord")
        layout = beat.get("layout")
        if layout not in allowed:
            errors.append(f"beat {ord_} layout {layout} is not allowed for {skill_id or 'script'}")
        cites = beat.get("citations") or []
        if not cites:
            errors.append(f"beat {ord_} has no citations")
        for cite in cites:
            errors.extend(_cite_errors(ord_, cite, duration_ms))
            if cite.get("kind") == "recording":
                end = cite.get("t_end_ms")
                start = cite.get("t_start_ms")
                if check_order and start is not None and start < previous_end:
                    errors.append(f"beat {ord_} recording spans go backwards")
                if end is not None:
                    previous_end = end
        errors.extend(_number_errors(beat, cells))
    return errors


def _cite_errors(ord_: Any, cite: dict[str, Any], duration_ms: int | None) -> list[str]:
    errors: list[str] = []
    kind = cite.get("kind")
    if kind not in {"recording", "workbook", "document"}:
        errors.append(f"beat {ord_} bad citation kind {kind}")
        return errors
    if kind == "recording":
        start = cite.get("t_start_ms")
        end = cite.get("t_end_ms")
        if start is None or end is None or end <= start:
            errors.append(f"beat {ord_} invalid recording span")
        elif duration_ms is not None and end > duration_ms:
            errors.append(f"beat {ord_} citation past duration")
    if kind == "workbook" and not (cite.get("sheet") and cite.get("addr")):
        errors.append(f"beat {ord_} workbook citation missing sheet/addr")
    if kind == "document" and not cite.get("block_id"):
        errors.append(f"beat {ord_} document citation missing block_id")
    return errors


def _number_errors(beat: dict[str, Any], cells: dict[tuple[str, str], Any] | None) -> list[str]:
    errors: list[str] = []
    claims = list(beat.get("claims") or [])
    shown = parse_numbers("\n".join(_displayed(beat)))
    for number in shown:
        if not any(close(number, float(claim["value"])) for claim in claims):
            errors.append(f"beat {beat.get('ord')} shows {number} without a cited claim")
    cited = {
        (cite.get("sheet"), cite.get("addr"))
        for cite in beat.get("citations") or []
        if cite.get("kind") == "workbook"
    }
    for claim in claims:
        sheet = claim.get("sheet")
        addr = claim.get("addr")
        if sheet and addr and (sheet, addr) not in cited:
            errors.append(f"beat {beat.get('ord')} claim {sheet}!{addr} is not cited")
        if cells is None or not sheet or not addr:
            continue
        cell = cells.get((sheet, addr))
        if cell is None:
            errors.append(f"beat {beat.get('ord')} cited empty cell {sheet}!{addr}")
            continue
        if claim.get("in_text"):
            if str(int(claim["value"])) not in str(cell):
                errors.append(f"beat {beat.get('ord')} number {claim['value']} is not in {sheet}!{addr}")
        elif claim.get("derived"):
            continue
        else:
            expected = claim.get("cell", claim["value"])
            if not close(float(expected), float(cell)):
                errors.append(
                    f"beat {beat.get('ord')} claim {claim['value']} does not match {sheet}!{addr}"
                )
    return errors


def _displayed(beat: dict[str, Any]) -> list[str]:
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
    return strings


def _reject_style_keys(node: Any, errors: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key.lower() in FORBIDDEN_KEYS:
                errors.append(f"script carries design key {key}")
            _reject_style_keys(value, errors)
    elif isinstance(node, list):
        for item in node:
            _reject_style_keys(item, errors)
