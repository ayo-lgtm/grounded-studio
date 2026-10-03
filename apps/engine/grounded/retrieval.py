"""Grounded retrieval across everything a briefing knows.

Candidates are the briefing's own material only: script beats, what was
said in the recording (timestamped), what was on screen (timestamped OCR),
knowledge-base documents (block/page) and workbook rows (sheet/range).

Ranking is local and deterministic:

* tokens are lower-cased, stop-worded and lightly stemmed;
* a curated synonym lexicon links everyday product/business words
  ("bills" ~ "invoices", "log in" ~ "sign in");
* BM25 scores each candidate; a candidate answers only when it covers enough
  of the question's concepts (so a single shared word is not an answer);
* optionally, an embedding provider (local ONNX model or Bedrock embeddings)
  reranks and can rescue a paraphrase whose words differ entirely.

Whatever ranks, the shipped answer is the candidate's own text (or a rewrite
that passes the grounding gate), with the candidate's own citation.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

_WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")

STOP = frozenset(
    """
    a an the of to and or but if then than so as at by for from in into on onto off out over under with without
    is are was were be been being am do does did doing done have has had having i me my mine we our ours you your
    yours he she it its they them their there here this that these those what which who whom whose when where why
    how can could should would will shall may might must not no yes please tell show give explain let lets let's
    about any some all each every just only also very really more most much many few lot lots get got go going
    one thing things way ways okay ok hi hello thanks thank need want like know see use using used s t
    briefing video demo slide deck section part
    """.split()
)

SYNONYMS: tuple[tuple[str, ...], ...] = (
    ("invoice", "bill", "billing", "receipt", "payment", "pay", "charge", "statement"),
    ("sign", "login", "log", "signin", "logon", "authenticate", "sso"),
    ("signup", "register", "registration", "enroll", "enrol"),
    ("account", "profile"),
    ("setting", "preference", "option", "configuration", "config", "configure", "setup"),
    ("delete", "remove", "erase", "discard", "trash"),
    ("create", "add", "new", "make", "start", "begin"),
    ("edit", "change", "modify", "update", "adjust", "rename"),
    ("download", "export", "save"),
    ("upload", "import", "attach", "drop"),
    ("search", "find", "lookup", "locate"),
    ("user", "member", "teammate", "colleague", "people", "person"),
    ("permission", "access", "role", "right", "privilege"),
    ("password", "credential", "passcode"),
    ("error", "issue", "problem", "bug", "fail", "failure", "broken", "wrong"),
    ("dashboard", "home", "overview", "landing"),
    ("report", "summary", "recap"),
    ("share", "invite", "send", "forward"),
    ("filter", "sort", "narrow"),
    ("revenue", "sale", "income", "turnover"),
    ("cost", "expense", "spend", "spending", "price", "pricing", "fee"),
    ("customer", "client", "buyer", "account"),
    ("employee", "staff", "hire", "newhire", "starter", "joiner"),
    ("onboard", "onboarding", "orientation", "induction"),
    ("laptop", "computer", "device", "machine", "hardware"),
    ("meeting", "call", "sync", "standup"),
    ("schedule", "calendar", "book", "booking", "appointment"),
    ("open", "launch", "go", "navigate", "visit"),
    ("close", "stop", "end", "cancel", "exit", "quit"),
    ("button", "control", "link", "icon"),
    ("page", "screen", "view", "tab", "panel", "window"),
    ("menu", "navigation", "nav", "sidebar"),
    ("notification", "alert", "notice", "reminder"),
    ("deadline", "due", "date"),
    ("team", "group", "squad"),
    ("manager", "lead", "supervisor", "boss"),
    ("approve", "approval", "signoff", "authorise", "authorize"),
    ("request", "ask", "apply"),
    ("target", "goal", "plan", "budget", "forecast"),
    ("risk", "concern", "threat", "blocker"),
    ("week", "weekly"),
    ("month", "monthly"),
    ("training", "course", "lesson", "tutorial", "learn", "learning"),
    ("step", "instruction", "procedure", "process", "workflow"),
    ("tool", "app", "application", "product", "platform", "system"),
    ("feature", "capability", "function", "functionality"),
    ("release", "launch", "ship", "rollout", "announce"),
    ("data", "record", "entry", "row"),
    ("file", "document", "doc", "attachment"),
    ("security", "secure", "safety", "compliance"),
    ("help", "support", "assist", "contact"),
    ("benefit", "perk", "insurance", "health"),
    ("holiday", "vacation", "leave", "pto", "time-off"),
    ("expense", "reimburse", "reimbursement", "claim"),
)

_GROUP: dict[str, int] = {}
for _index, _group in enumerate(SYNONYMS):
    for _word in _group:
        _GROUP.setdefault(_word, _index)

PHRASES = {
    "log in": "login", "sign in": "signin", "sign up": "signup", "set up": "setup", "time off": "time-off",
    "new hire": "newhire", "sign off": "signoff", "look up": "lookup", "log on": "logon",
}


def stem(word: str) -> str:
    w = word.lower()
    if len(w) <= 3 or w.isdigit():
        return w
    for suffix, repl in (("ies", "y"), ("sses", "ss"), ("ing", ""), ("ed", ""), ("es", ""), ("s", "")):
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            base = w[: -len(suffix)] + repl
            if suffix in {"ing", "ed"} and len(base) > 3 and base[-1] == base[-2] and base[-1] not in "lsz":
                base = base[:-1]
            return base
    return w


def tokens(text: str) -> list[str]:
    lowered = (text or "").lower()
    for phrase, joined in PHRASES.items():
        lowered = lowered.replace(phrase, joined)
    return [stem(word) for word in _WORD.findall(lowered) if word not in STOP and len(word) > 1]


def concept(token: str) -> str:
    group = _GROUP.get(token)
    if group is None:
        group = _GROUP.get(token + "e")  # "configur" -> "configure"
    return f"#{group}" if group is not None else token


@dataclass
class Candidate:
    id: str
    text: str
    citation: dict[str, Any]
    source: str  # beat | speech | screen | document | workbook
    ord: int | None = None
    terms: list[str] = field(default_factory=list)
    concepts: set[str] = field(default_factory=set)


@dataclass
class Hit:
    candidate: Candidate
    score: float
    coverage: float
    semantic: float | None
    accepted: bool


def prepare(candidates: Iterable[Candidate]) -> list[Candidate]:
    out = []
    for cand in candidates:
        if not cand.citation or not (cand.text or "").strip():
            continue
        cand.terms = tokens(cand.text)
        cand.concepts = {concept(term) for term in cand.terms}
        out.append(cand)
    return out


def _bm25(query: list[str], docs: list[Candidate], k1: float = 1.2, b: float = 0.75) -> list[float]:
    n = len(docs)
    if not n:
        return []
    avg = sum(len(d.terms) for d in docs) / n or 1.0
    df: dict[str, int] = {}
    for doc in docs:
        for c in set(concept(t) for t in doc.terms):
            df[c] = df.get(c, 0) + 1
    scores = []
    qconcepts = [concept(t) for t in query]
    for doc in docs:
        tf: dict[str, int] = {}
        for t in doc.terms:
            c = concept(t)
            tf[c] = tf.get(c, 0) + 1
        score = 0.0
        for qt, qc in zip(query, qconcepts):
            freq = tf.get(qc, 0)
            if not freq:
                continue
            idf = math.log(1 + (n - df.get(qc, 0) + 0.5) / (df.get(qc, 0) + 0.5))
            exact = 1.0 if qt in doc.terms else 0.8
            score += exact * idf * (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * len(doc.terms) / avg))
        scores.append(score)
    return scores


def needed(concepts: set[str]) -> float:
    n = len(concepts)
    if n <= 1:
        return 1.0
    if n == 2:
        return 0.5
    return 0.5 if n <= 4 else 0.4


Embedder = Callable[[list[str]], list[list[float]]]
_CACHE: dict[str, list[float]] = {}


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def _embed(embedder: Embedder, texts: list[str]) -> list[list[float]]:
    missing = [t for t in texts if hashlib.sha256(t.encode()).hexdigest() not in _CACHE]
    if missing:
        for text, vec in zip(missing, embedder(missing)):
            _CACHE[hashlib.sha256(text.encode()).hexdigest()] = vec
        if len(_CACHE) > 20000:
            _CACHE.clear()
    return [_CACHE[hashlib.sha256(t.encode()).hexdigest()] for t in texts]


def rank(
    question: str,
    candidates: list[Candidate],
    *,
    embedder: Embedder | None = None,
    semantic_threshold: float = 0.58,
    limit: int = 8,
) -> list[Hit]:
    query = tokens(question)
    if not query or not candidates:
        return []
    qconcepts = {concept(t) for t in query}
    bm = _bm25(query, candidates)
    top = max(bm) if bm else 0.0
    sem: list[float | None] = [None] * len(candidates)
    if embedder is not None:
        try:
            pool = sorted(range(len(candidates)), key=lambda i: bm[i], reverse=True)[:200]
            if len(candidates) <= 200:
                pool = list(range(len(candidates)))
            vectors = _embed(embedder, [question] + [candidates[i].text for i in pool])
            qv = vectors[0]
            for offset, i in enumerate(pool, start=1):
                sem[i] = _cos(qv, vectors[offset])
        except Exception:  # noqa: BLE001 - semantic is an optional boost, never a requirement
            sem = [None] * len(candidates)
    hits: list[Hit] = []
    need = needed(qconcepts)
    for i, cand in enumerate(candidates):
        coverage = len(qconcepts & cand.concepts) / len(qconcepts)
        lexical_ok = bm[i] > 0 and coverage >= need
        semantic_ok = sem[i] is not None and sem[i] >= semantic_threshold
        norm = bm[i] / top if top else 0.0
        score = norm * (0.6 + 0.4 * coverage) if sem[i] is None else 0.45 * norm + 0.35 * max(sem[i], 0) + 0.2 * coverage
        if score <= 0 and not semantic_ok:
            continue
        hits.append(Hit(cand, score, coverage, sem[i], lexical_ok or semantic_ok))
    hits.sort(key=lambda h: (h.accepted, h.score), reverse=True)
    return hits[:limit]
