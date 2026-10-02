"""Offline quality gate and the cheapest local fix for each finding."""

from __future__ import annotations

from typing import Any

from .continuity import verify_carry
from .qa import validate_script

def gate_script(script: dict[str, Any], cells: dict | None = None) -> dict[str, Any]:
    errors = validate_script(
        script,
        duration_ms=script.get("source_duration_ms"),
        cells=cells,
    )
    warnings: list[str] = []
    skill_id = script.get("skill_id") or ""
    continuity = (script.get("edit") or {}).get("continuity") or {}
    checks_carry = skill_id in {"continuous-take-demo", "carry-boundary-verify"} or continuity.get("mode") == "carry-boundary"
    if checks_carry:
        errors.extend(verify_carry(script))
        warnings.extend(_cadence_warnings(script))
    status = "fail" if errors else "warn" if warnings else "pass"
    return {"status": status, "errors": errors, "warnings": warnings}


def refine_actions(report: dict[str, Any]) -> list[dict[str, str]]:
    """Cheapest on-box fix. Never a cloud render."""
    actions: list[dict[str, str]] = []
    for error in report.get("errors") or []:
        text = str(error)
        lowered = text.lower()
        if "survivor" in lowered or "replaces the picture" in lowered or "carry" in lowered:
            fix = "carry-hold"
        elif "citation" in lowered or "caption" in lowered:
            fix = "recaption"
        elif "empty" in lowered:
            fix = "fail-closed"
        else:
            fix = "fail-closed"
        actions.append({"fix": fix, "why": text, "where": "local"})
    for warning in report.get("warnings") or []:
        text = str(warning)
        lowered = text.lower()
        if "cadence" in lowered or "stillness" in lowered:
            fix = "trim"
        elif "clip" in lowered or "loud" in lowered:
            fix = "duck"
        else:
            fix = "trim"
        actions.append({"fix": fix, "why": text, "where": "local"})
    return actions


def clipping_warning(max_volume_db: float | None) -> str | None:
    if max_volume_db is None:
        return None
    if max_volume_db > -1.0:
        return f"clipped audio (max_volume {max_volume_db:.1f} dB)"
    return None


def _cadence_warnings(script: dict[str, Any]) -> list[str]:
    cuts = list((script.get("edit") or {}).get("cuts") or [])
    if len(cuts) < 3:
        return []
    spans = [int(cut["src_out_ms"]) - int(cut["src_in_ms"]) for cut in cuts]
    warnings: list[str] = []
    if max(spans) - min(spans) <= 40:
        warnings.append("uniform cadence: every cut is the same length")
    if script.get("skill_id") == "continuous-take-demo" and max(spans) < 1500:
        warnings.append("no stillness: no beat rests")
    return warnings
