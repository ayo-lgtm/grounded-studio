"""Numeric formatting/parsing used by deterministic cite-or-cut QA."""

from __future__ import annotations

import re

# A quantity is not glued to letters: "7Q", "Q3", "FY24", "SKU-12A" are
# identifiers, not displayed numbers. Model rewrites lock identifiers
# separately (grounding.identifiers), so they cannot drift either.
_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_.])(?:"
    r"\(?[+\u2212-]?\s*[$€£¥]?\s*\d{1,3}(?:,\d{3})+(?:\.\d+)?\s*[MmKk]?%?\)?"
    r"|\(?[+\u2212-]?\s*[$€£¥]?\s*\d+(?:\.\d+)?\s*[MmKk]?%?\)?"
    r")(?![A-Za-z0-9_])"
)


def format_usd_full(value: float) -> str:
    sign = "-" if value < 0 else ""
    n = abs(float(value))
    if n == int(n):
        return "{}${:,.0f}".format(sign, n)
    return "{}${:,.2f}".format(sign, n)


def format_usd(value: float) -> str:
    sign = "-" if value < 0 else ""
    n = abs(float(value))
    if n >= 1_000_000:
        return "{}${:.2f}M".format(sign, n / 1_000_000)
    if n == int(n):
        return "{}${:,.0f}".format(sign, n)
    return "{}${:,.2f}".format(sign, n)


def format_number(value: float) -> str:
    n = float(value)
    if n == int(n):
        return "{:,.0f}".format(n)
    return "{:,.2f}".format(n).rstrip("0").rstrip(".")


def format_pct(ratio: float) -> str:
    return "{:.1f}%".format(ratio * 100)


def format_points(points: float) -> str:
    return "{:.1f}".format(points)


def format_value(value: float, unit: str, *, full: bool = False) -> str:
    if unit == "pct":
        return format_pct(value)
    if unit in {"currency", "usd"}:
        return format_usd_full(value) if full else format_usd(value)
    return format_number(value)


def parse_numbers(text: str) -> list[float]:
    return [_normalize(match.group()) for match in _TOKEN.finditer(text or "")]


def _normalize(token: str) -> float:
    raw = token.strip()
    accounting_negative = raw.startswith("(") and raw.endswith(")")
    text = (
        raw.strip("()")
        .replace(" ", "")
        .replace(",", "")
        .replace("$", "")
        .replace("€", "")
        .replace("£", "")
        .replace("¥", "")
        .replace("\u2212", "-")
    )
    sign = -1.0 if accounting_negative else 1.0
    if text and text[0] in "+-":
        if text[0] == "-":
            sign *= -1.0
        text = text[1:]
    mult = 1.0
    if text.endswith("%"):
        text = text[:-1]
    if text and text[-1] in "Mm":
        mult = 1_000_000.0
        text = text[:-1]
    elif text and text[-1] in "Kk":
        mult = 1_000.0
        text = text[:-1]
    return sign * float(text) * mult


def close(left: float, right: float) -> bool:
    return abs(left - right) <= max(0.05, abs(right) * 0.002)
