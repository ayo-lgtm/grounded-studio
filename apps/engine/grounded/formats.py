"""Placement masters. Local scale and pad only. Safe zones stay inside the frame."""

from __future__ import annotations

from typing import Any

# Pad color is house theater, not a generated plate.
PAD = "0x241f1a"

RATIOS: dict[str, tuple[int, int]] = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
}


def scale_filter(ratio: str, safe: float = 0.9) -> str:
    if ratio not in RATIOS:
        raise ValueError(f"unknown placement {ratio}")
    width, height = RATIOS[ratio]
    inner_w = int(width * safe) // 2 * 2
    inner_h = int(height * safe) // 2 * 2
    return (
        f"scale={inner_w}:{inner_h}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color={PAD}"
    )


def placement_plan(safe: float = 0.9) -> dict[str, Any]:
    return {
        "master": "16:9",
        "safe": safe,
        "engine": "ffmpeg",
        "variants": [
            {"ratio": ratio, "width": size[0], "height": size[1], "vf": scale_filter(ratio, safe)}
            for ratio, size in RATIOS.items()
        ],
    }
