"""Deterministic QA. The rules live in the engine."""

from __future__ import annotations

from .bootstrap import ensure_engine

ensure_engine()

from grounded.qa import validate_script as validate_script  # noqa: E402,F401
