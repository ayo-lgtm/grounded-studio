"""Deterministic citation QA. No model. Fail closed."""

from typing import Any


def validate_script(script: dict[str, Any], duration_ms: int | None = None) -> list[str]:
    errors: list[str] = []
    beats = script.get("beats") or []
    if not beats:
        errors.append("script has no beats")
        return errors
    for beat in beats:
        cites = beat.get("citations") or []
        if not cites:
            errors.append(f"beat {beat.get('ord')} has no citations")
            continue
        for cite in cites:
            kind = cite.get("kind")
            if kind not in {"recording", "workbook", "document"}:
                errors.append(f"beat {beat.get('ord')} bad citation kind {kind}")
            if kind == "recording":
                start = cite.get("t_start_ms")
                end = cite.get("t_end_ms")
                if start is None or end is None or end <= start:
                    errors.append(f"beat {beat.get('ord')} invalid recording span")
                if duration_ms is not None and end is not None and end > duration_ms:
                    errors.append(f"beat {beat.get('ord')} citation past duration")
            if kind == "workbook" and not (cite.get("sheet") and cite.get("addr")):
                errors.append(f"beat {beat.get('ord')} workbook citation missing sheet/addr")
            if kind == "document" and not cite.get("block_id"):
                errors.append(f"beat {beat.get('ord')} document citation missing block_id")
    return errors
