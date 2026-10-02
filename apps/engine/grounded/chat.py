"""Grounded briefing chat with no model or network egress."""

from __future__ import annotations

import re
from typing import Any

_STOP = frozenset(
    {
        "the", "a", "an", "of", "to", "and", "or", "did", "where", "what", "is",
        "was", "our", "how", "many", "in", "on", "for", "this", "that", "against",
        "from", "with", "are", "were", "does", "do", "we", "it", "its", "be",
        "at", "by", "about", "into", "than", "then", "their", "there",
    }
)


def answer(script: dict[str, Any], question: str) -> dict[str, Any]:
    words = [
        word
        for word in re.findall(r"[a-z0-9']+", question.lower())
        if word not in _STOP and len(word) > 3
    ]
    if not words:
        return _refuse()
    best = None
    best_score = 0
    for beat in script.get("beats") or []:
        eyebrow = str((beat.get("slots") or {}).get("eyebrow") or "")
        haystack = f"{beat.get('text') or ''} {eyebrow}".lower()
        score = sum(1 for word in words if word in haystack)
        if score > best_score:
            best = beat
            best_score = score
    if best is None or best_score == 0:
        return _refuse()
    return {
        "refused": False,
        "text": best["text"],
        "citations": best.get("citations") or [],
        "ord": best.get("ord"),
        "model_used": False,
    }


def answer_with_claude(script: dict[str, Any], question: str, client: Any = None) -> dict[str, Any]:
    """Deprecated compatibility wrapper. It never calls Claude or any network."""
    result = answer(script, question)
    return {**result, "claude": False}


def _refuse() -> dict[str, Any]:
    return {
        "refused": True,
        "text": "That is not in this briefing.",
        "citations": [],
        "ord": None,
        "model_used": False,
    }
