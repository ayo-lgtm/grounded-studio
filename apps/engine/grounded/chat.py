"""Answer only by quoting a beat. Otherwise refuse."""

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
    }


def _refuse() -> dict[str, Any]:
    return {
        "refused": True,
        "text": "That is not in this briefing.",
        "citations": [],
        "ord": None,
    }


_SYSTEM = (
    "You answer questions about a briefing using ONLY the quoted beat below. "
    "Reply with a single JSON object: {\"text\": <plain-language answer>, \"ord\": <beat number>}. "
    "Use the beat's words and numbers exactly; never add facts, numbers, or screens "
    "from anywhere else. If the beat does not answer the question, reply "
    "{\"text\": \"That is not in this briefing.\", \"ord\": null}."
)


def answer_grounded(
    script: dict[str, Any],
    question: str,
    *,
    briefing_id: str | None = None,
    db: Any = None,
) -> dict[str, Any]:
    """Cite a briefing beat, else a local doc or skill chunk. No public model."""
    from .knowledge import rephrase_private, search_knowledge, search_vectors

    base = answer(script, question)
    if not base["refused"]:
        text = rephrase_private(str(base["text"]), question) or base["text"]
        return {**base, "text": text, "provider": "retrieval", "claude": False}
    hits = search_vectors(db, briefing_id or "", question)
    if not hits:
        hits = search_knowledge(question)
    if not hits:
        return {**base, "provider": "retrieval", "claude": False}
    passage = hits[0]["text"]
    text = rephrase_private(passage, question) or passage
    return {
        "refused": False,
        "text": text,
        "citations": [{"kind": "document", "block_id": hits[0]["path"]}],
        "ord": None,
        "provider": "retrieval",
        "claude": False,
    }


def answer_with_claude(
    script: dict[str, Any], question: str, client: Any = None
) -> dict[str, Any]:
    """Phrase the retrieved beat with Claude, enforcing cite-or-cut.

    Retrieval decides WHAT is cited; Claude only rephrases. Any model
    output that does not point back at the retrieved beat is discarded
    and the verbatim beat ships instead. Bedrock failures also fall
    back to verbatim — chat never invents.
    """
    from .bedrock import BedrockError, from_env

    base = answer(script, question)
    if base["refused"]:
        return {**base, "claude": False}
    beat_text = base["text"]
    prompt = (
        f"Beat {base['ord']} says: \"{beat_text}\"\n"
        f"Citations: {base['citations']}\n"
        f"Question: {question}"
    )
    try:
        import json as _json

        raw = from_env(client).complete(_SYSTEM, prompt)
        parsed = _json.loads(raw)
        text = str(parsed.get("text") or "").strip()
        if parsed.get("ord") == base["ord"] and text:
            return {
                "refused": False,
                "text": text,
                "citations": base["citations"],
                "ord": base["ord"],
                "claude": True,
            }
    except (BedrockError, ValueError, AttributeError):
        pass
    return {**base, "claude": False}
