"""Briefing chat: quote a cited beat or a cited source passage, else refuse.

Retrieval decides what is said. Answers come only from the briefing's own
beats and its normalized sources (workbook cells, document blocks,
transcript segments) - never from product docs, the skill library, or a
model's general knowledge. When an inference provider is enabled for the
``chat`` feature it may rephrase the retrieved passage; the rephrase must
pass :func:`grounding.check_rewrite` or the verbatim passage ships. A
question the sources do not cover gets ``REFUSAL``.
"""

from __future__ import annotations

import math
import re
from typing import Any

REFUSAL = "That is not in this briefing."

_STOP = frozenset(
    {
        "the", "a", "an", "of", "to", "and", "or", "did", "where", "what", "is",
        "was", "our", "how", "many", "in", "on", "for", "this", "that", "against",
        "from", "with", "are", "were", "does", "do", "we", "it", "its", "be",
        "at", "by", "about", "into", "than", "then", "their", "there", "tell",
        "show", "give", "please", "which", "when", "much", "week", "briefing",
        "slide", "deck", "say", "says", "said", "explain", "have", "has", "had",
    }
)


def _words(text: str) -> list[str]:
    return [
        word.rstrip("s") if len(word) > 4 else word
        for word in re.findall(r"[a-z0-9']+", (text or "").lower())
        if word not in _STOP and len(word) > 2
    ]


def _score(words: list[str], haystack: str) -> int:
    hay = set(_words(haystack))
    return sum(1 for word in words if word in hay)


def _needed(words: list[str]) -> int:
    return max(1, math.ceil(len(set(words)) / 2))


def answer(script: dict[str, Any], question: str) -> dict[str, Any]:
    """Best cited beat for ``question`` or a refusal. Deterministic."""
    words = _words(question)
    if not words:
        return _refuse()
    best = None
    best_score = 0
    for beat in script.get("beats") or []:
        if not beat.get("citations"):
            continue
        eyebrow = str((beat.get("slots") or {}).get("eyebrow") or "")
        score = _score(words, f"{beat.get('text') or ''} {eyebrow}")
        if score > best_score:
            best, best_score = beat, score
    if best is None or best_score < _needed(words):
        return _refuse()
    return {
        "refused": False,
        "text": best["text"],
        "citations": best.get("citations") or [],
        "ord": best.get("ord"),
    }


def answer_from_sources(passages: list[dict[str, Any]], question: str) -> dict[str, Any]:
    """Best normalized source passage (each must carry a citation)."""
    words = _words(question)
    if not words:
        return _refuse()
    best = None
    best_score = 0
    for passage in passages:
        cite = passage.get("citation")
        if not cite:
            continue
        score = _score(words, str(passage.get("text") or ""))
        if score > best_score:
            best, best_score = passage, score
    if best is None or best_score < _needed(words):
        return _refuse()
    return {"refused": False, "text": str(best["text"]), "citations": [best["citation"]], "ord": None}


def _refuse() -> dict[str, Any]:
    return {"refused": True, "text": REFUSAL, "citations": [], "ord": None}


_PHRASE_SYSTEM = (
    "Rephrase the quoted passage so it directly answers the question. Use only facts, "
    "names and numbers in the passage, written exactly as they appear. Do not add causes, "
    "risks, recommendations or forecasts. Reply with JSON: {\"text\": <answer>}. If the "
    "passage does not answer the question reply {\"text\": \"That is not in this briefing.\"}."
)


def _phrase(base: dict[str, Any], question: str, provider: Any) -> tuple[str, dict[str, str] | None]:
    import json

    from .grounding import check_rewrite
    from .providers.base import ProviderError

    passage = str(base["text"])
    try:
        result = provider.complete(_PHRASE_SYSTEM, f'Passage: "{passage}"\nQuestion: {question}', max_tokens=300)
        raw = result.text if hasattr(result, "text") else str(result)
        text = str(json.loads(raw).get("text") or "").strip()
    except (ProviderError, ValueError, AttributeError, TypeError):
        return passage, None
    if not text or text == REFUSAL:
        return passage, None
    if not check_rewrite(passage, text).ok:
        return passage, None
    return text, {"provider": getattr(provider, "name", "model"), "model_id": getattr(provider, "model_id", "")}


def answer_grounded(
    script: dict[str, Any],
    question: str,
    *,
    briefing_id: str | None = None,
    db: Any = None,
    passages: list[dict[str, Any]] | None = None,
    provider: Any = None,
    use_provider: bool = True,
) -> dict[str, Any]:
    """Cite a beat, else a normalized source passage of this briefing, else refuse."""
    base = answer(script, question)
    if base["refused"]:
        sources = passages if passages is not None else load_passages(db, briefing_id)
        base = answer_from_sources(sources, question)
    if base["refused"]:
        return {**base, "provider": "retrieval", "phrased": False}
    model = provider
    if model is None and use_provider:
        from .providers.base import ProviderError
        from .providers.registry import inference_provider

        try:
            model = inference_provider("chat")
        except ProviderError:
            model = None  # fail closed to verbatim retrieval; never another provider
    if model is None:
        return {**base, "provider": "retrieval", "phrased": False}
    text, used = _phrase(base, question, model)
    if used is None:
        return {**base, "provider": "retrieval", "phrased": False}
    return {**base, "text": text, "provider": used["provider"], "model_id": used["model_id"], "phrased": True}


def load_passages(db: Any, briefing_id: str | None, limit: int = 400) -> list[dict[str, Any]]:
    """Normalized source rows for one briefing, each with its citation."""
    if db is None or not briefing_id:
        return []
    try:
        from sqlalchemy import text
    except ImportError:  # pragma: no cover
        return []
    passages: list[dict[str, Any]] = []
    try:
        blocks = db.execute(
            text(
                """
                SELECT db.block_id, db.page, db.text, sa.id AS asset_id
                FROM document_blocks db JOIN source_assets sa ON sa.id = db.asset_id
                WHERE sa.briefing_id = :id ORDER BY sa.created_at, db.page NULLS FIRST
                LIMIT :limit
                """
            ),
            {"id": briefing_id, "limit": limit},
        ).mappings().all()
        for row in blocks:
            cite = {"kind": "document", "block_id": row["block_id"], "asset_id": str(row["asset_id"])}
            if row["page"] is not None:
                cite["page"] = row["page"]
            passages.append({"text": row["text"], "citation": cite})
        segments = db.execute(
            text(
                """
                SELECT ts.t_start_ms, ts.t_end_ms, ts.text, sa.id AS asset_id
                FROM transcript_segments ts JOIN source_assets sa ON sa.id = ts.asset_id
                WHERE sa.briefing_id = :id ORDER BY ts.t_start_ms LIMIT :limit
                """
            ),
            {"id": briefing_id, "limit": limit},
        ).mappings().all()
        for row in segments:
            passages.append(
                {
                    "text": row["text"],
                    "citation": {
                        "kind": "recording",
                        "t_start_ms": row["t_start_ms"],
                        "t_end_ms": row["t_end_ms"],
                        "asset_id": str(row["asset_id"]),
                    },
                }
            )
        rows = db.execute(
            text(
                """
                SELECT wr.sheet, wr.row_num, wr.range_ref, wr.text, sa.id AS asset_id
                FROM workbook_rows wr JOIN source_assets sa ON sa.id = wr.asset_id
                WHERE sa.briefing_id = :id ORDER BY wr.sheet, wr.row_num LIMIT :limit
                """
            ),
            {"id": briefing_id, "limit": limit},
        ).mappings().all()
        for row in rows:
            first = str(row["range_ref"]).split(":")[0]
            passages.append(
                {
                    "text": row["text"],
                    "citation": {
                        "kind": "workbook",
                        "sheet": row["sheet"],
                        "addr": first,
                        "range": row["range_ref"],
                        "asset_id": str(row["asset_id"]),
                    },
                }
            )
    except Exception:  # noqa: BLE001 - a DB problem means "no sources", i.e. refuse
        return []
    return passages


def answer_help(question: str) -> dict[str, Any]:
    """Product help from the on-disk docs and skill library (not business data)."""
    from .knowledge import search_knowledge

    hits = search_knowledge(question)
    if not hits:
        return {**_refuse(), "text": "That is not in the Grounded Studio docs.", "provider": "retrieval"}
    return {
        "refused": False,
        "text": hits[0]["text"],
        "citations": [{"kind": "document", "block_id": hits[0]["path"]}],
        "ord": None,
        "provider": "retrieval",
    }
