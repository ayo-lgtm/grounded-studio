"""Project an accepted script onto locked slide masters."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from .house import css

_EYEBROW = {
    "weekly-ops-review": "Weekly operating review",
    "finance-wbr": "Finance weekly business review",
    "half-year-business-review": "Half-year business review",
    "executive-business-review": "Executive business review",
    "leadership-brief": "Leadership brief",
    "launch-announcement": "Launch",
    "sop-training": "Procedure",
    "product-walkthrough": "Walkthrough",
    "feature-delta": "What changed",
    "localize": "Briefing",
}


def render_deck(script: dict[str, Any], path: Path) -> Path:
    slides = [_slide(script, beat, index, len(script["beats"])) for index, beat in enumerate(script["beats"], start=1)]
    page = f"""<!DOCTYPE html>
<html lang="{html.escape(script.get("language") or "en")}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(script.get("title") or "Briefing")}</title>
<style>{css()}</style>
</head>
<body>
<main class="deck">
{''.join(slides)}
</main>
<script>
const slides = [...document.querySelectorAll(".slide")];
let index = 0;
function go(next) {{
  index = Math.max(0, Math.min(slides.length - 1, next));
  slides[index].scrollIntoView({{behavior: "instant" in window ? "instant" : "auto"}});
  history.replaceState(null, "", "#" + (index + 1));
}}
document.addEventListener("keydown", (event) => {{
  if (["ArrowRight", "ArrowDown", " "].includes(event.key)) {{ event.preventDefault(); go(index + 1); }}
  if (["ArrowLeft", "ArrowUp"].includes(event.key)) {{ event.preventDefault(); go(index - 1); }}
}});
window.addEventListener("hashchange", () => {{
  const next = parseInt((location.hash || "#1").slice(1), 10);
  if (!Number.isNaN(next)) go(next - 1);
}});
const start = parseInt((location.hash || "#1").slice(1), 10);
if (!Number.isNaN(start)) go(start - 1);
</script>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")
    return path


def guide_md(script: dict[str, Any]) -> str:
    lines = [f"# {script.get('title') or 'Briefing'}", ""]
    for beat in script["beats"]:
        if beat.get("layout") == "step":
            lines.append(f"{beat['ord']}. {beat['text']}")
    return "\n".join(lines) + "\n"


def _slide(script: dict[str, Any], beat: dict[str, Any], index: int, total: int) -> str:
    layout = beat["layout"]
    body = {
        "cover": _cover,
        "big-number": _big_number,
        "versus-target": _versus,
        "movers": _movers,
        "source-range": _source_range,
        "risk": _sentence,
        "ask": _sentence,
        "statement": _sentence,
        "step": _step,
    }[layout](script, beat)
    return f"""<section class="slide" id="s{index}">
  <article class="frame {html.escape(layout)}">
    {body}
    <footer class="footer"><span>{html.escape(_cites(beat))}</span><span>{index} / {total}</span></footer>
  </article>
</section>
"""


def _cover(script: dict[str, Any], beat: dict[str, Any]) -> str:
    eyebrow = _EYEBROW.get(script.get("skill_id") or "", "Briefing")
    period = (beat.get("slots") or {}).get("period") or ""
    period_html = f'<p class="lead">{html.escape(period)}</p>' if period else ""
    return (
        f'<p class="eyebrow">{html.escape(eyebrow)}</p>'
        f"<h1>{html.escape(beat['text'])}</h1>"
        f"{period_html}"
    )


def _big_number(script: dict[str, Any], beat: dict[str, Any]) -> str:
    slots = beat.get("slots") or {}
    return (
        f'<p class="eyebrow">{html.escape(slots.get("eyebrow") or "")}</p>'
        f"<h1>{html.escape(beat['text'])}</h1>"
        f'<p class="num xl">{html.escape(slots.get("actual") or "")}</p>'
    )


def _versus(script: dict[str, Any], beat: dict[str, Any]) -> str:
    slots = beat.get("slots") or {}
    direction = slots.get("direction") or ""
    delta_class = "delta down" if direction == "below" else "delta"
    return (
        f'<p class="eyebrow">{html.escape(slots.get("eyebrow") or "")}</p>'
        f"<h1>{html.escape(beat['text'])}</h1>"
        f'<div class="figures">'
        f'<div><span class="label">Actual</span><div class="num lg">{html.escape(slots.get("actual") or "")}</div></div>'
        f'<div><span class="label">Target</span><div class="num lg">{html.escape(slots.get("target") or "")}</div></div>'
        f"</div>"
        f'<p class="{delta_class}">{html.escape(slots.get("delta") or "")}</p>'
    )


def _movers(script: dict[str, Any], beat: dict[str, Any]) -> str:
    rows = []
    for row in (beat.get("slots") or {}).get("rows") or []:
        delta = str(row.get("delta") or "")
        klass = "num down" if delta.startswith("-") else "num"
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('line') or ''))}</td>"
            f"<td class=\"num\">{html.escape(str(row.get('this_week') or ''))}</td>"
            f"<td class=\"num\">{html.escape(str(row.get('last_week') or ''))}</td>"
            f"<td class=\"{klass}\">{html.escape(delta)}</td>"
            "</tr>"
        )
    return (
        f'<p class="eyebrow">Movers</p>'
        f"<h1>{html.escape(beat['text'])}</h1>"
        "<table><thead><tr>"
        "<th>Line</th><th class=\"num\">This week</th><th class=\"num\">Last week</th><th class=\"num\">Delta</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )



def _source_range(script: dict[str, Any], beat: dict[str, Any]) -> str:
    visual = beat.get("visual") or {}
    grid = visual.get("rows") or []
    rendered_rows = []
    for row_index, row in enumerate(grid):
        cells = []
        tag = "th" if row_index == 0 else "td"
        for cell in row:
            display = html.escape(str(cell.get("display") or ""))
            addr = html.escape(str(cell.get("addr") or ""))
            cells.append(f'<{tag} class="source-cell" title="{addr}">{display}</{tag}>')
        rendered_rows.append("<tr>" + "".join(cells) + "</tr>")
    range_label = html.escape(str(visual.get("range") or ""))
    source = html.escape(str((beat.get("citations") or [{}])[0].get("sheet") or "Workbook"))
    return (
        '<p class="eyebrow">Source data</p>'
        f"<h1>{html.escape(beat['text'])}</h1>"
        f'<p class="lead">{source} {range_label}</p>'
        '<div class="source-table"><table><tbody>'
        + "".join(rendered_rows)
        + "</tbody></table></div>"
    )


def _sentence(script: dict[str, Any], beat: dict[str, Any]) -> str:
    eyebrow = (beat.get("slots") or {}).get("eyebrow") or ""
    klass = "eyebrow risk" if beat.get("layout") == "risk" else "eyebrow"
    return f'<p class="{klass}">{html.escape(eyebrow)}</p><h1>{html.escape(beat["text"])}</h1>'


def _step(script: dict[str, Any], beat: dict[str, Any]) -> str:
    screen = (beat.get("slots") or {}).get("screen") or ""
    screen_html = f'<p class="lead">{html.escape(screen)}</p>' if screen else ""
    return (
        f'<p class="eyebrow">Step {beat["ord"]}</p>'
        f"<h1>{html.escape(beat['text'])}</h1>"
        f"{screen_html}"
    )


def _cites(beat: dict[str, Any]) -> str:
    if beat.get("layout") == "source-range":
        cites = beat.get("citations") or []
        sheet = cites[0].get("sheet") if cites else ""
        source_range = (beat.get("visual") or {}).get("range") or ""
        return f"{sheet}!{source_range}" if sheet and source_range else str(sheet or source_range)
    labels = []
    for cite in beat.get("citations") or []:
        kind = cite.get("kind")
        if kind == "workbook":
            labels.append(f"{cite.get('sheet')}!{cite.get('addr')}")
        elif kind == "document":
            labels.append(f"block {cite.get('block_id')}")
        elif kind == "recording":
            labels.append(f"{_clock(cite.get('t_start_ms') or 0)}–{_clock(cite.get('t_end_ms') or 0)}")
    return " · ".join(labels)


def _clock(ms: int) -> str:
    total = max(0, int(ms)) / 1000
    minutes, seconds = divmod(total, 60)
    return f"{int(minutes)}:{seconds:04.1f}"
