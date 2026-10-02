"""Deterministic evaluation of simple spreadsheet formulas, on the box.

openpyxl reads the cached result Excel stored with each formula. Files
written by scripts or exported by some tools carry no cache, so the value
would be missing. This evaluator covers the arithmetic that business-review
packs actually use - cell references (same or other sheet), ranges inside
SUM/AVERAGE/MIN/MAX/COUNT, + - * /, unary minus, parentheses, percentages -
and nothing else. Anything outside that grammar returns ``None``; the cell
is then reported as a data-quality warning and never cited.
"""

from __future__ import annotations

import re
from typing import Any, Callable

_TOKEN = re.compile(
    r"\s*(?:"
    r"(?P<num>\d+(?:\.\d+)?%?)"
    r"|(?P<ref>(?:(?:'[^']+'|[A-Za-z_][A-Za-z0-9_ ]*)!)?\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?)"
    r"|(?P<func>SUM|AVERAGE|MIN|MAX|COUNT|ABS|ROUND)(?=\()"
    r"|(?P<op>[-+*/(),])"
    r")",
    re.I,
)


class Unsupported(ValueError):
    pass


def _col(letters: str) -> int:
    total = 0
    for char in letters.upper():
        total = total * 26 + (ord(char) - 64)
    return total


def _letters(col: int) -> str:
    out = ""
    while col:
        col, rem = divmod(col - 1, 26)
        out = chr(65 + rem) + out
    return out


def _expand(ref: str, sheet: str) -> list[tuple[str, str]]:
    if "!" in ref:
        sheet_part, ref = ref.rsplit("!", 1)
        sheet = sheet_part.strip("'")
    ref = ref.replace("$", "").upper()
    if ":" not in ref:
        return [(sheet, ref)]
    start, end = ref.split(":")
    m1 = re.fullmatch(r"([A-Z]+)(\d+)", start)
    m2 = re.fullmatch(r"([A-Z]+)(\d+)", end)
    if not m1 or not m2:
        raise Unsupported(ref)
    c1, c2 = sorted((_col(m1.group(1)), _col(m2.group(1))))
    r1, r2 = sorted((int(m1.group(2)), int(m2.group(2))))
    if (c2 - c1 + 1) * (r2 - r1 + 1) > 10000:
        raise Unsupported("range too large")
    return [(sheet, f"{_letters(c)}{r}") for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)]


def evaluate(formula: str, sheet: str, lookup: Callable[[str, str], Any], depth: int = 0) -> float | None:
    """Evaluate ``formula`` (with or without leading '='). ``None`` if unsupported."""
    if depth > 20:
        return None
    text = (formula or "").strip()
    if text.startswith("="):
        text = text[1:]
    tokens: list[tuple[str, str]] = []
    pos = 0
    while pos < len(text):
        match = _TOKEN.match(text, pos)
        if not match or match.end() == pos:
            return None
        pos = match.end()
        kind = match.lastgroup or ""
        tokens.append((kind, match.group(kind).strip()))
    parser = _Parser(tokens, sheet, lookup, depth)
    try:
        value = parser.expr()
        if parser.i != len(tokens):
            return None
    except (Unsupported, ZeroDivisionError, TypeError, ValueError):
        return None
    return value


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]], sheet: str, lookup: Callable[[str, str], Any], depth: int = 0) -> None:
        self.depth = depth
        self.tokens = tokens
        self.i = 0
        self.sheet = sheet
        self.lookup = lookup

    def peek(self) -> tuple[str, str] | None:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def take(self, value: str | None = None) -> tuple[str, str]:
        token = self.peek()
        if token is None or (value is not None and token[1] != value):
            raise Unsupported("unexpected end")
        self.i += 1
        return token

    def expr(self) -> float:
        value = self.term()
        while self.peek() and self.peek()[1] in "+-" and self.peek()[0] == "op":
            op = self.take()[1]
            right = self.term()
            value = value + right if op == "+" else value - right
        return value

    def term(self) -> float:
        value = self.unary()
        while self.peek() and self.peek()[1] in "*/" and self.peek()[0] == "op":
            op = self.take()[1]
            right = self.unary()
            value = value * right if op == "*" else value / right
        return value

    def unary(self) -> float:
        token = self.peek()
        if token and token == ("op", "-"):
            self.take()
            return -self.unary()
        if token and token == ("op", "+"):
            self.take()
            return self.unary()
        return self.atom()

    def atom(self) -> float:
        kind, value = self.take()
        if kind == "num":
            return float(value[:-1]) / 100 if value.endswith("%") else float(value)
        if kind == "ref":
            cells = _expand(value, self.sheet)
            if len(cells) != 1:
                raise Unsupported("range outside a function")
            return self._number(*cells[0])
        if kind == "func":
            return self.call(value.upper())
        if (kind, value) == ("op", "("):
            inner = self.expr()
            self.take(")")
            return inner
        raise Unsupported(value)

    def call(self, name: str) -> float:
        self.take("(")
        values: list[float] = []
        while True:
            token = self.peek()
            if token and token[0] == "ref" and ":" in token[1]:
                self.take()
                for sheet, addr in _expand(token[1], self.sheet):
                    raw = self.lookup(sheet, addr)
                    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
                        values.append(float(raw))
                    elif isinstance(raw, str) and raw.startswith("="):
                        nested = evaluate(raw, sheet, self.lookup, self.depth + 1)
                        if nested is None:
                            raise Unsupported("nested formula")
                        values.append(nested)
            else:
                values.append(self.expr())
            token = self.take()
            if token[1] == ")":
                break
            if token[1] != ",":
                raise Unsupported("bad argument list")
        if name == "SUM":
            return sum(values)
        if name == "AVERAGE":
            if not values:
                raise ZeroDivisionError
            return sum(values) / len(values)
        if name == "MIN":
            return min(values)
        if name == "MAX":
            return max(values)
        if name == "COUNT":
            return float(len(values))
        if name == "ABS":
            return abs(values[0])
        if name == "ROUND":
            digits = int(values[1]) if len(values) > 1 else 0
            return round(values[0], digits)
        raise Unsupported(name)

    def _number(self, sheet: str, addr: str) -> float:
        raw = self.lookup(sheet, addr)
        if isinstance(raw, bool):
            raise Unsupported("boolean")
        if isinstance(raw, (int, float)):
            return float(raw)
        if raw is None:
            return 0.0
        if isinstance(raw, str) and raw.startswith("="):
            nested = evaluate(raw, sheet, self.lookup, self.depth + 1)
            if nested is None:
                raise Unsupported("nested formula")
            return nested
        raise Unsupported("text operand")
