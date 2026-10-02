"""Deterministic grounding gate for model-written language.

A model (local or Amazon Nova) may rephrase, structure or summarize. It may
not add facts. :func:`check_rewrite` compares a candidate sentence with the
cited source text it claims to restate and rejects it when it:

* contains a number that the source does not contain (or drops one);
* changes an authored number surface (``$4,820,000`` -> ``$4.82M``);
* introduces causal language ("because", "driven by", "due to" ...);
* introduces a recommendation, risk, forecast or obligation that the source
  does not state;
* flips direction (above/below, up/down, increase/decrease) or negation;
* introduces proper nouns / entities absent from the source.

:func:`recompute` independently evaluates a derived numeric claim from the
cited operand cells, so a model-proposed calculation is never trusted.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Any, Iterable

from .numbers import close, parse_numbers

_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")

CAUSAL = (
    "because", "due to", "driven by", "caused", "causing", "as a result", "owing to",
    "thanks to", "led to", "leading to", "attributable", "on the back of", "result of",
    "fueled by", "fuelled by", "stemming from", "resulting from", "explained by",
)
RECOMMEND = (
    "should", "recommend", "we need", "need to", "must", "ought", "propose", "suggest",
    "advise", "consider ", "plan to", "will need",
)
RISK = ("risk", "concern", "threat", "exposure", "jeopard", "warning")
FORECAST = ("will ", "expect", "forecast", "projected", "likely", "on track to", "anticipate")
NEGATION = ("not", "no", "never", "none", "neither", "nor", "without")
POSITIVE = ("above", "up", "increase", "increased", "rose", "grew", "growth", "higher", "gain", "ahead", "beat", "exceed")
NEGATIVE = ("below", "down", "decrease", "decreased", "fell", "declined", "decline", "lower", "drop", "behind", "missed", "short")


@dataclass(frozen=True)
class Verdict:
    ok: bool
    reason: str = ""


def _has(phrases: Iterable[str], text: str) -> set[str]:
    lowered = f" {text.lower()} "
    found = set()
    for phrase in phrases:
        if phrase.endswith(" "):
            if f" {phrase}" in lowered:
                found.add(phrase.strip())
        elif re.search(rf"(?<![a-z]){re.escape(phrase)}", lowered):
            found.add(phrase)
    return found


def _words(text: str) -> set[str]:
    return {word.lower() for word in _WORD.findall(text)}


def _entities(text: str) -> set[str]:
    """Capitalised tokens that are not sentence-initial: crude proper nouns."""
    found: set[str] = set()
    for sentence in re.split(r"(?<=[.!?:;])\s+|\n", text):
        tokens = _WORD.findall(sentence)
        for token in tokens[1:]:
            if token[:1].isupper() and token.lower() not in {"i"}:
                found.add(token.lower())
    return found


_IDENT = re.compile(r"(?<![\w.,$€£¥])(?=[A-Za-z0-9_\-]*\d)(?=[A-Za-z0-9_\-]*[A-Za-z])[A-Za-z0-9_\-]+\b")
_QUANTITY = re.compile(r"\d+(?:[.,]\d+)*[MmKkBb]|\d+(?:st|nd|rd|th|pp|bp|bps|x)", re.I)


def identifiers(text: str) -> set[str]:
    """Letter+digit tokens such as Q3, FY24, H1, SKU-12A, P95 (not 4.8M or 3pp)."""
    return {
        token.strip("-")
        for token in _IDENT.findall(text or "")
        if not _QUANTITY.fullmatch(token.strip("-"))
    }


def check_rewrite(source: str, candidate: str, locked_surfaces: Iterable[str] = ()) -> Verdict:
    """Is ``candidate`` a faithful restatement of ``source``?"""
    text = (candidate or "").strip()
    if not text:
        return Verdict(False, "empty reply")
    if identifiers(text) != identifiers(source):
        return Verdict(False, "identifier changed")
    src_numbers = sorted(parse_numbers(source))
    new_numbers = sorted(parse_numbers(text))
    if len(src_numbers) != len(new_numbers) or any(not close(a, b) for a, b in zip(new_numbers, src_numbers)):
        return Verdict(False, "numbers drifted")
    for surface in locked_surfaces:
        if surface and surface not in text:
            return Verdict(False, f"dropped surface {surface!r}")
    for label, phrases in (("causal claim", CAUSAL), ("recommendation", RECOMMEND), ("risk", RISK), ("forecast", FORECAST)):
        added = _has(phrases, text) - _has(phrases, source)
        if added:
            return Verdict(False, f"unsupported {label} ({sorted(added)[0]})")
    src_words = _words(source)
    new_words = _words(text)
    if (new_words & set(NEGATION)) - src_words or (src_words & set(NEGATION)) - new_words:
        return Verdict(False, "negation changed")
    src_pos, src_neg = src_words & set(POSITIVE), src_words & set(NEGATIVE)
    new_pos, new_neg = new_words & set(POSITIVE), new_words & set(NEGATIVE)
    if (new_pos and not src_pos) or (new_neg and not src_neg):
        return Verdict(False, "direction changed")
    novel_entities = _entities(text) - src_words - _entities(source)
    if novel_entities:
        return Verdict(False, f"unsupported entity ({sorted(novel_entities)[0]})")
    return Verdict(True)


# ---- independent recomputation -------------------------------------------

_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Add, ast.Sub, ast.Mult, ast.Div,
    ast.USub, ast.UAdd, ast.Constant, ast.Name, ast.Load, ast.Call,
)
_NAMES = ("actual", "comparator", "target", "prior", "a", "b")


class FormulaError(ValueError):
    pass


def evaluate(formula: str, values: list[float]) -> float:
    """Evaluate a claim formula over operand values. Tiny, safe grammar."""
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError as exc:
        raise FormulaError(f"formula {formula!r} does not parse") from exc
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise FormulaError(f"formula {formula!r} uses an unsupported construct")
        if isinstance(node, ast.Call) and not (isinstance(node.func, ast.Name) and node.func.id == "abs"):
            raise FormulaError(f"formula {formula!r} calls an unsupported function")
    if len(values) < 2:
        raise FormulaError("derived claims need two operands")
    env = {"actual": values[0], "a": values[0], "comparator": values[1], "target": values[1], "prior": values[1], "b": values[1]}

    def run(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return run(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id not in env:
                raise FormulaError(f"unknown name {node.id}")
            return float(env[node.id])
        if isinstance(node, ast.UnaryOp):
            value = run(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.Call):
            return abs(run(node.args[0]))
        if isinstance(node, ast.BinOp):
            left, right = run(node.left), run(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if right == 0:
                raise FormulaError("division by zero")
            return left / right
        raise FormulaError("unsupported formula node")

    return run(tree)


def recompute(claim: dict[str, Any], cells: dict[tuple[str, str], Any]) -> str | None:
    """Return an error if a derived claim does not match its cited operands."""
    formula = claim.get("formula")
    operands = claim.get("operands") or []
    values: list[float] = []
    for operand in operands:
        raw = cells.get((operand.get("sheet"), operand.get("addr")))
        try:
            values.append(float(raw))
        except (TypeError, ValueError):
            return f"operand {operand.get('sheet')}!{operand.get('addr')} is not numeric"
    try:
        expected = evaluate(str(formula), values)
    except FormulaError as exc:
        return str(exc)
    if not close(float(claim["value"]), round(expected, 6)) and not close(float(claim["value"]), round(expected, 1)):
        return f"derived value {claim['value']} does not recompute ({formula} = {expected:g})"
    return None


def numbers_supported(text: str, claims: list[dict[str, Any]]) -> list[float]:
    """Numbers in ``text`` that no claim backs."""
    return [number for number in parse_numbers(text) if not any(close(number, float(c["value"])) for c in claims)]
