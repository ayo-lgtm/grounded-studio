"""Format money and percents so the same parser can check them."""

from __future__ import annotations

import re

_TOKEN = re.compile(
    r"[+\u2212-]?\s*\$?\d{1,3}(?:,\d{3})+(?:\.\d+)?%?"
    r"|[+\u2212-]?\s*\$?\d+(?:\.\d+)?\s*[MmKk]\b"
    r"|[+\u2212-]?\s*\$?\d+(?:\.\d+)?%"
    r"|[+\u2212-]?\s*\d+(?:\.\d+)?%"
    r"|[+\u2212-]?\s*\$?\d+\.\d+"
    r"|[+\u2212-]?\s*\d+\.\d+"
    r"|[+\u2212-]?\s*\d+"
)


def format_usd_full(value: float) -> str:
    sign = "-" if value < 0 else ""
    n = abs(float(value))
    if n == int(n):
        return f"{sign}${n:,.0f}"
    return f"{sign}${n:,.2f}"


def format_usd(value: float) -> str:
    sign = "-" if value < 0 else ""
    n = abs(float(value))
    if n >= 1_000_000:
        return f"{sign}${n / 1_000_000:.2f}M"
    if n == int(n):
        return f"{sign}${n:,.0f}"
    return f"{sign}${n:,.2f}"


def format_pct(ratio: float) -> str:
    return f"{ratio * 100:.1f}%"


def format_points(points: float) -> str:
    return f"{points:.1f}"


def parse_numbers(text: str) -> list[float]:
    return [_normalize(match.group()) for match in _TOKEN.finditer(text or "")]


def _normalize(token: str) -> float:
    text = token.strip().replace(" ", "").replace(",", "").replace("$", "").replace("\u2212", "-")
    sign = 1.0
    if text[0] in "+-":
        if text[0] == "-":
            sign = -1.0
        text = text[1:]
    mult = 1.0
    if text.endswith("%"):
        text = text[:-1]
    elif text[-1] in "Mm":
        mult = 1_000_000.0
        text = text[:-1]
    elif text[-1] in "Kk":
        mult = 1_000.0
        text = text[:-1]
    return sign * float(text) * mult


def close(left: float, right: float) -> bool:
    return abs(left - right) <= max(0.05, abs(right) * 0.002)
