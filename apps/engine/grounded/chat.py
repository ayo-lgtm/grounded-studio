"""Briefing chat: answer from this briefing's sources, show the moment, or refuse.

The answer pool is the briefing's own material: its script beats, what was
said in the recording, what was on screen, its knowledge-base documents and
its workbook rows (see :mod:`grounded.retrieval`). Never product docs, never
a model's general knowledge.

* The best grounded candidate is the answer, quoted with its citation.
* Related recording moments come back as ``moments`` so the player can
  "show me" the exact clip.
* With an inference provider enabled for ``chat`` (internal model or Nova),
  the model may *choose* which retrieved passage answers and may phrase it;
  the phrasing must pass :func:`grounding.check_rewrite` or the verbatim
  passage ships. The model never supplies facts.
* Nothing relevant: ``REFUSAL``.
"""

from __future__ import annotations

import json
from typing import Any

from .retrieval import Candidate, Hit, prepare, rank

REFUSAL = "That is not in this briefing."


def _beat_candidates(script: dict[str, Any]) -> list[Candidate]:
    out = []
    for beat in script.get("beats") or []:
        cites = beat.get("citations") or []
        if not cites:
            continue
        slots = beat.get("slots") or {}
        label = " ".join(str(slots.get(key) or "") for key in ("eyebrow", "screen"))
        cand = Candidate(
            id=f"beat-{beat.get('ord')}",
            text=f"{beat.get('text') or ''} {label}".strip(),
            citation=cites[0],
            source="beat",
            ord=beat.get("ord"),
        )
        cand.citations = cites  # type: ignore[attr-defined]
        cand.answer = str(beat.get("text") or "")  # type: ignore[attr-defined]
        out.append(cand)
    return out


def _passage_candidates(passages: list[dict[str, Any]]) -> list[Candidate]:
    out = []
    for index, passage in enumerate(passages):
        cite = passage.get("citation")
        if not cite:
            continue
        source = passage.get("source") or {"recording": "speech", "document": "document", "workbook": "workbook"}.get(
            str(cite.get("kind")), "document"
        )
        cand = Candidate(id=f"p-{index}", text=str(passage.get("text") or ""), citation=cite, source=source)
        cand.citations = [cite]  # type: ignore[attr-defined]
        cand.answer = str(passage.get("answer") or passage.get("text") or "")  # type: ignore[attr-defined]
        out.append(cand)
    return out


def _result(hit: Hit) -> dict[str, Any]:
    cand = hit.candidate
    return {
        "refused": False,
        "text": getattr(cand, "answer", cand.text),
        "citations": list(getattr(cand, "citations", [cand.citation])),
        "ord": cand.ord,
        "source": cand.source,
    }


def _refuse() -> dict[str, Any]:
    return {"refused": True, "text": REFUSAL, "citations": [], "ord": None, "source": None, "moments": []}


def answer(script: dict[str, Any], question: str) -> dict[str, Any]:
    """Best cited beat for ``question`` or a refusal. Deterministic."""
    hits = rank(question, prepare(_beat_candidates(script)))
    if not hits or not hits[0].accepted:
        return _refuse()
    return {**_result(hits[0]), "moments": []}


def answer_from_sources(passages: list[dict[str, Any]], question: str) -> dict[str, Any]:
    hits = rank(question, prepare(_passage_candidates(passages)))
    if not hits or not hits[0].accepted:
        return _refuse()
    return {**_result(hits[0]), "moments": []}


def _moments(hits: list[Hit], primary: Hit | None) -> list[dict[str, Any]]:
    seen: set[tuple[Any, Any]] = set()
    if primary is not None:
        cite = primary.candidate.citation
        if cite.get("kind") == "recording":
            seen.add((cite.get("t_start_ms"), cite.get("t_end_ms")))
    best = primary.score if primary else (hits[0].score if hits else 0)
    out = []
    for hit in hits:
        cite = hit.candidate.citation
        if cite.get("kind") != "recording" or hit is primary:
            continue
        if not (hit.accepted or hit.score >= 0.6 * best):
            continue
        key = (cite.get("t_start_ms"), cite.get("t_end_ms"))
        if key in seen:
            continue
        seen.add(key)
        out.append({"citation": cite, "text": getattr(hit.candidate, "answer", hit.candidate.text), "source": hit.candidate.source})
        if len(out) == 3:
            break
    return out


_SELECT_SYSTEM = (
    "You help people find the answer inside a briefing. You are given a question and numbered "
    "passages quoted from the briefing's own sources. Pick the ONE passage that directly answers the "
    "question, and optionally rephrase it as a direct answer using only that passage's words, names "
    "and numbers. Never add facts, causes, advice or numbers. Reply with JSON only: "
    "{\"id\": \"<passage id>\", \"text\": \"<answer>\"}, or {\"id\": null} if no passage answers it."
)


def _select(question: str, hits: list[Hit], model: Any) -> tuple[Hit | None, str | None, dict[str, str] | None]:
    from .grounding import check_rewrite
    from .providers.base import ProviderError

    pool = hits[:6]
    if not pool:
        return None, None, None
    listing = "\n".join(f"[{h.candidate.id}] {getattr(h.candidate, 'answer', h.candidate.text)}" for h in pool)
    try:
        result = model.complete(_SELECT_SYSTEM, f"Question: {question}\n\nPassages:\n{listing}", max_tokens=300)
        raw = result.text if hasattr(result, "text") else str(result)
        start, end = raw.find("{"), raw.rfind("}")
        parsed = json.loads(raw[start : end + 1]) if start >= 0 and end > start else {}
    except (ProviderError, ValueError, AttributeError, TypeError):
        return None, None, None
    used = {"provider": getattr(model, "name", "model"), "model_id": getattr(model, "model_id", "")}
    if "id" in parsed:
        chosen = next((h for h in pool if h.candidate.id == parsed.get("id")), None)
    else:
        # A bare {"text": ...} phrases the top retrieved passage, if it answers at all.
        chosen = pool[0] if pool[0].accepted else None
    if chosen is None:
        return None, None, used
    source = getattr(chosen.candidate, "answer", chosen.candidate.text)
    text = str(parsed.get("text") or "").strip()
    if text and text != REFUSAL and check_rewrite(source, text).ok:
        return chosen, text, used
    return chosen, None, used


def answer_grounded(
    script: dict[str, Any],
    question: str,
    *,
    briefing_id: str | None = None,
    db: Any = None,
    passages: list[dict[str, Any]] | None = None,
    provider: Any = None,
    use_provider: bool = True,
    embedder: Any = None,
) -> dict[str, Any]:
    """Answer from beats + recording + screen + knowledge base, or refuse."""
    sources = passages if passages is not None else load_passages(db, briefing_id)
    candidates = prepare(_beat_candidates(script) + _passage_candidates(sources))
    if embedder is None and use_provider:
        embedder = _semantic_embedder()
    hits = rank(question, candidates, embedder=embedder)
    model = provider
    if model is None and use_provider:
        from .providers.base import ProviderError
        from .providers.registry import inference_provider

        try:
            model = inference_provider("chat")
        except ProviderError:
            model = None  # fail closed to deterministic retrieval; never another provider
    primary: Hit | None = hits[0] if hits and hits[0].accepted else None
    phrased: str | None = None
    used: dict[str, str] | None = None
    if model is not None and hits:
        chosen, phrased, used = _select(question, hits, model)
        if chosen is not None:
            primary = chosen
        elif used is not None and primary is not None and primary.coverage < 1.0:
            # The model judged the partial lexical match irrelevant; trust the refusal.
            primary = None
    if primary is None:
        out = _refuse()
        out["moments"] = _moments(hits, None) if hits and any(h.accepted for h in hits) else []
        out["provider"] = used["provider"] if used else "retrieval"
        out["phrased"] = False
        return out
    result = _result(primary)
    result["moments"] = _moments(hits, primary)
    if phrased:
        result.update({"text": phrased, "provider": used["provider"], "model_id": used["model_id"], "phrased": True})
    else:
        result.update({"provider": used["provider"] if used else "retrieval", "phrased": False})
        if used:
            result["model_id"] = used["model_id"]
    return result


def _semantic_embedder():
    """A real semantic embedder if one is selected; the hash embedder is lexical, so skip it."""
    try:
        from .providers.registry import embedding_provider, selection

        if selection().embedding == "local-hash":
            return None
        provider = embedding_provider()
        return provider.embed
    except Exception:  # noqa: BLE001 - semantic boost is optional
        return None


def load_passages(db: Any, briefing_id: str | None, limit: int = 2000) -> list[dict[str, Any]]:
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
                SELECT db.block_id, db.page, db.text, db.heading_path, sa.id AS asset_id, sa.filename
                FROM document_blocks db JOIN source_assets sa ON sa.id = db.asset_id
                WHERE sa.briefing_id = :id ORDER BY sa.created_at, db.ord
                LIMIT :limit
                """
            ),
            {"id": briefing_id, "limit": limit},
        ).mappings().all()
        headings = {str(row["heading_path"] or "").split(" > ")[-1].strip() for row in blocks if row["heading_path"]}
        for row in blocks:
            if str(row["text"] or "").strip() in headings:
                continue  # a bare heading is context for the blocks under it, not an answer
            cite = {"kind": "document", "block_id": row["block_id"], "asset_id": str(row["asset_id"])}
            if row["page"] is not None:
                cite["page"] = row["page"]
            body = row["text"]
            heading = row["heading_path"]
            passages.append({"text": f"{body} {heading}" if heading else body, "answer": body, "citation": cite, "source": "document"})
        segments = db.execute(
            text(
                """
                SELECT ts.t_start_ms, ts.t_end_ms, ts.text, ts.speaker, sa.id AS asset_id
                FROM transcript_segments ts JOIN source_assets sa ON sa.id = ts.asset_id
                WHERE sa.briefing_id = :id ORDER BY ts.t_start_ms LIMIT :limit
                """
            ),
            {"id": briefing_id, "limit": limit},
        ).mappings().all()
        for row in segments:
            screen = row["speaker"] == "screen"
            passages.append(
                {
                    "text": row["text"],
                    "citation": {
                        "kind": "recording",
                        "t_start_ms": row["t_start_ms"],
                        "t_end_ms": row["t_end_ms"],
                        "asset_id": str(row["asset_id"]),
                        **({"on_screen": True} if screen else {}),
                    },
                    "source": "screen" if screen else "speech",
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
                    "source": "workbook",
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
