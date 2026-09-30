"""Import the engine whether it sits beside the worker or inside the image."""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_engine() -> None:
    try:
        import grounded  # noqa: F401
    except ImportError:
        root = Path(__file__).resolve().parents[2] / "engine"
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
