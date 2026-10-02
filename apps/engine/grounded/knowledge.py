"""Local retrieval helpers: product help over docs/skills, hash embeddings.

The hashing embedder runs on the box. Briefing chat does not use the product
docs; it answers only from the briefing's own sources (see :mod:`chat`).
"""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Any

from .catalog import content_root

_TOKEN = re.compile(r"[a-z0-9']+")
_STOP = frozenset(
    {
        "the", "a", "an", "of", "to", "and", "or", "how", "what", "is", "was",
        "are", "do", "does", "i", "we", "you", "this", "that", "with", "for",
        "in", "on", "it", "use", "using", "can", "about",
    }
)
DIMS = 768


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in _TOKEN.findall(text.lower())
        if token not in _STOP and len(token) > 2
    ]


def embed(text: str, dims: int = DIMS) -> list[float]:
    """Local hashing embedder. Same text always yields the same vector."""
    vec = [0.0] * dims
    tokens = tokenize(text)
    if not tokens:
        tokens = ["empty"]
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dims
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vec)) or 1.0
    return [value / norm for value in vec]


def vector_literal(text: str) -> str:
    return "[" + ",".join(f"{value:.6f}" for value in embed(text)) + "]"


def iter_chunks(root: Path | None = None) -> list[dict[str, str]]:
    base = root or content_root()
    chunks: list[dict[str, str]] = []
    docs = base / "docs"
    skills = base / "skills"
    if docs.is_dir():
        for path in sorted(docs.glob("*.md")):
            chunks.extend(_split(path, base))
    if skills.is_dir():
        for path in sorted(skills.glob("**/SKILL.md")):
            chunks.extend(_split(path, base))
    readme = base / "README.md"
    if readme.is_file():
        chunks.extend(_split(readme, base))
    return chunks


def search_knowledge(question: str, root: Path | None = None, limit: int = 3) -> list[dict[str, str]]:
    words = tokenize(question)
    if not words:
        return []
    scored: list[tuple[int, dict[str, str]]] = []
    for chunk in iter_chunks(root):
        haystack = tokenize(chunk["text"])
        if not haystack:
            continue
        score = sum(1 for word in words if word in haystack)
        if score:
            scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _score, chunk in scored[:limit]]


def search_vectors(db: Any, briefing_id: str, question: str, limit: int = 3) -> list[dict[str, str]]:
    """Cosine search over chunks stored for one briefing. Empty on any DB error."""
    if db is None or not briefing_id or not tokenize(question):
        return []
    try:
        from sqlalchemy import text

        rows = db.execute(
            text(
                """
                SELECT text, span::text
                FROM embedding_chunks
                WHERE briefing_id = :id
                ORDER BY embedding <=> CAST(:q AS vector)
                LIMIT :limit
                """
            ),
            {"id": briefing_id, "q": vector_literal(question), "limit": limit},
        ).mappings().all()
    except Exception:
        return []
    hits = []
    for row in rows:
        hits.append({"path": "pgvector", "text": str(row["text"]), "span": str(row["span"] or "")})
    return hits


def _split(path: Path, root: Path) -> list[dict[str, str]]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return []
    rel = str(path.relative_to(root)) if path.is_relative_to(root) else path.name
    blocks = re.split(r"\n(?=#{1,3} )", raw)
    chunks: list[dict[str, str]] = []
    for block in blocks:
        text = " ".join(block.split())
        if len(text) < 40:
            continue
        for start in range(0, len(text), 900):
            piece = text[start : start + 900].strip()
            if len(piece) >= 40:
                chunks.append({"path": rel, "text": piece})
    return chunks
