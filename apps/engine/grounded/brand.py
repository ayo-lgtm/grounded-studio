"""Brand lock reads house.py. Scripts do not carry color, type, or logos."""

from __future__ import annotations

from typing import Any

from . import house


def brand_lock() -> dict[str, Any]:
    return {
        "source": "house.py",
        "paper": house.PAPER,
        "ink": house.INK,
        "muted": house.MUTED,
        "rule": house.RULE,
        "accent": house.ACCENT,
        "negative": house.NEGATIVE,
        "theater": house.THEATER,
        "title": house.FONT_TITLE,
        "ui": house.FONT_UI,
        "logo": None,
    }
