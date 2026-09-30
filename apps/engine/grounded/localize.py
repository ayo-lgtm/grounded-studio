"""Swap supplied lines. Numbers on each beat must stay the same multiset."""

from __future__ import annotations

import copy
from typing import Any

from .compile_deck import CompileError
from .numbers import parse_numbers


def localize(script: dict[str, Any], lines: dict[int, str], language: str) -> dict[str, Any]:
    if not lines:
        raise CompileError(["localize needs replacement lines"])
    out = copy.deepcopy(script)
    out["skill_id"] = "localize"
    out["language"] = language
    errors: list[str] = []
    by_ord = {int(key): value for key, value in lines.items()}
    seen = set()
    for beat in out["beats"]:
        replacement = by_ord.get(beat["ord"])
        if replacement is None:
            continue
        seen.add(beat["ord"])
        before = parse_numbers(beat["text"])
        after = parse_numbers(replacement)
        if sorted(before) != sorted(after):
            errors.append(
                f"beat {beat['ord']} changed numbers {before} -> {after}"
            )
        beat["text"] = replacement
    missing = sorted(set(by_ord) - seen)
    if missing:
        errors.append(f"no beats for ords {missing}")
    if errors:
        raise CompileError(errors)
    return out
