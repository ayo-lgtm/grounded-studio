"""Carry-boundary continuity for a real recording edit.

At every beat boundary something already on screen survives into the next
beat: the same screen label, or the outgoing source frame held briefly
under the next title. A full-frame card that replaces the picture is a
slideshow cut and does not pass.
"""

from __future__ import annotations

from typing import Any

HOLD_MS = 480
TAIL_MS = 80


def apply_carry(script: dict[str, Any], hold_ms: int = HOLD_MS) -> dict[str, Any]:
    """Annotate edit.continuity. Source in/out points stay put."""
    edit = script.setdefault("edit", {})
    cuts = list(edit.get("cuts") or [])
    boundaries: list[dict[str, Any]] = []
    for index in range(len(cuts) - 1):
        left = cuts[index]
        right = cuts[index + 1]
        left_screen = str(left.get("screen") or "").strip()
        right_screen = str(right.get("screen") or "").strip()
        if left_screen and left_screen == right_screen:
            kind = "screen-label"
            survivor = left_screen
        else:
            kind = "outgoing-frame"
            survivor = left_screen or "outgoing-frame"
        src_out = int(left["src_out_ms"])
        boundary = {
            "from_ord": index + 1,
            "to_ord": index + 2,
            "survivor": survivor,
            "kind": kind,
            "hold_ms": int(hold_ms),
            "src_ms": max(int(left["src_in_ms"]), src_out - TAIL_MS),
        }
        boundaries.append(boundary)
        carried = dict(right)
        carried["carry"] = {
            "survivor": survivor,
            "kind": kind,
            "hold_ms": int(hold_ms),
        }
        cuts[index + 1] = carried
    edit["cuts"] = cuts
    edit["continuity"] = {"mode": "carry-boundary", "boundaries": boundaries}
    return script


def verify_carry(script: dict[str, Any]) -> list[str]:
    """Fail closed when a boundary drops the picture or names no survivor."""
    errors: list[str] = []
    edit = script.get("edit") or {}
    continuity = edit.get("continuity") or {}
    cuts = list(edit.get("cuts") or [])
    if continuity.get("mode") != "carry-boundary":
        errors.append("continuity mode is not carry-boundary")
        return errors
    boundaries = list(continuity.get("boundaries") or [])
    if len(cuts) >= 2 and len(boundaries) != len(cuts) - 1:
        errors.append("a beat boundary has no carry record")
    for boundary in boundaries:
        if not str(boundary.get("survivor") or "").strip():
            errors.append(
                f"boundary {boundary.get('from_ord')}→{boundary.get('to_ord')} has no survivor"
            )
        if boundary.get("kind") == "replace":
            errors.append(
                f"boundary {boundary.get('from_ord')}→{boundary.get('to_ord')} replaces the picture"
            )
    return errors
