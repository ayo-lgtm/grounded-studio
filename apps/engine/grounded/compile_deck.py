"""Fill locked deck masters from a workbook pack or a document. No freeform layout."""

from __future__ import annotations

from typing import Any

from .layouts import SKILL_RENDERER
from .numbers import format_pct, format_points, format_value


class CompileError(Exception):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def cell_index(pack: dict[str, Any]) -> dict[tuple[str, str], Any]:
    cells: dict[tuple[str, str], Any] = {}
    title = pack.get("title") or {}
    period = pack.get("period") or {}
    if title.get("sheet"):
        cells[(title["sheet"], title["addr"])] = title.get("text")
    if period.get("sheet"):
        cells[(period["sheet"], period["addr"])] = period.get("text")
    for kpi in pack.get("kpis") or []:
        cells[(kpi["sheet"], kpi["addr"])] = kpi.get("value")
        if kpi.get("target_addr"):
            cells[(kpi.get("target_sheet") or kpi["sheet"], kpi["target_addr"])] = kpi.get("target")
    for row in pack.get("movers") or []:
        cells[(row["sheet"], row["addr"])] = row.get("value")
        cells[(row["sheet"], row["prior_addr"])] = row.get("prior")
    for source in pack.get("source_ranges") or []:
        for row in source.get("rows") or []:
            for cell in row:
                if cell.get("addr"):
                    cells[(source["sheet"], cell["addr"])] = cell.get("value") if cell.get("value") is not None else cell.get("display")
    for note in list(pack.get("risks") or []) + list(pack.get("asks") or []):
        cells[(note["sheet"], note["addr"])] = note.get("text")
    return cells


def compile_workbook(pack: dict[str, Any], skill_id: str = "weekly-ops-review") -> dict[str, Any]:
    errors: list[str] = []
    for kpi in pack.get("kpis") or []:
        if kpi.get("required") and kpi.get("value") is None:
            errors.append(f"required KPI {kpi.get('label')} at {kpi.get('sheet')}!{kpi.get('addr')} is empty")
    if errors:
        raise CompileError(errors)

    beats: list[dict[str, Any]] = []
    title = pack["title"]
    period = pack.get("period") or {}
    cover_slots: dict[str, Any] = {}
    cover_claims: list[dict[str, Any]] = []
    cover_cites = [_workbook(title["sheet"], title["addr"])]
    if period.get("text"):
        cover_slots["period"] = period["text"]
        cover_cites.append(_workbook(period["sheet"], period["addr"]))
        for number in _integers_in(period["text"]):
            cover_claims.append(
                {"value": number, "sheet": period["sheet"], "addr": period["addr"], "in_text": True}
            )
    _add(
        beats,
        kind="cover",
        layout="cover",
        text=title["text"],
        slots=cover_slots,
        claims=cover_claims,
        citations=cover_cites,
    )

    for kpi in pack.get("kpis") or []:
        beats.append(_kpi_beat(kpi))

    movers = list(pack.get("movers") or [])
    if movers:
        beats.append(_movers_beat(movers))

    for source in pack.get("source_ranges") or []:
        beats.append(_source_range_beat(source))

    for note in pack.get("risks") or []:
        if note.get("text"):
            _add(
                beats,
                kind="risk",
                layout="risk",
                text=note["text"],
                slots={"eyebrow": "Risk"},
                claims=[],
                citations=[_workbook(note["sheet"], note["addr"])],
            )
    for note in pack.get("asks") or []:
        if note.get("text"):
            _add(
                beats,
                kind="ask",
                layout="ask",
                text=note["text"],
                slots={"eyebrow": "Ask"},
                claims=[],
                citations=[_workbook(note["sheet"], note["addr"])],
            )

    return _script(skill_id, title["text"], beats)


def compile_document(doc: dict[str, Any], skill_id: str) -> dict[str, Any]:
    blocks = [block for block in doc.get("blocks") or [] if (block.get("text") or "").strip()]
    if not blocks and not doc.get("title"):
        raise CompileError(["document has no blocks"])
    beats: list[dict[str, Any]] = []
    title = doc.get("title") or "Briefing"
    title_block = doc.get("title_block") or (blocks[0]["id"] if blocks else "p1")
    _add(
        beats,
        kind="cover",
        layout="cover",
        text=title,
        slots={},
        claims=_text_claims(title, title_block),
        citations=[_document(title_block)],
    )
    for block in blocks:
        role = block.get("role") or "evidence"
        layout = {"ask": "ask", "risk": "risk"}.get(role, "statement")
        if skill_id == "launch-announcement" and layout == "risk":
            layout = "statement"
        eyebrow = {"ask": "Ask", "risk": "Risk", "situation": "Situation", "evidence": "Evidence"}.get(
            role, "Note"
        )
        text = block["text"].strip()
        if block.get("id") == title_block and text == title.strip():
            continue
        _add(
            beats,
            kind=role,
            layout=layout,
            text=text,
            slots={"eyebrow": eyebrow},
            claims=_text_claims(text, block["id"]),
            citations=[_document(block["id"])],
        )
    return _script(skill_id, title, beats)


def _kpi_beat(kpi: dict[str, Any]) -> dict[str, Any]:
    label = kpi["label"]
    sheet = kpi["sheet"]
    addr = kpi["addr"]
    unit = kpi.get("unit") or "number"
    target = kpi.get("target")
    target_sheet = kpi.get("target_sheet") or sheet
    target_addr = kpi.get("target_addr")
    cites = [_workbook(sheet, addr)]

    actual_txt = kpi.get("display") or format_value(kpi["value"], unit)
    actual_claim = {
        "value": round(kpi["value"] * 100, 1) if unit == "pct" else kpi["value"],
        "cell": kpi["value"],
        "unit": unit,
        "sheet": sheet,
        "addr": addr,
        "formula": kpi.get("formula"),
    }
    claims = [actual_claim]

    if target is None or not target_addr:
        return {
            "kind": "kpi",
            "layout": "big-number",
            "text": f"{label} is {actual_txt}.",
            "slots": {"eyebrow": label, "actual": actual_txt},
            "claims": claims,
            "citations": cites,
        }

    cites.append(_workbook(target_sheet, target_addr))
    target_txt = kpi.get("target_display") or format_value(target, unit)
    target_claim = {
        "value": round(target * 100, 1) if unit == "pct" else target,
        "cell": target,
        "unit": unit,
        "sheet": target_sheet,
        "addr": target_addr,
        "formula": kpi.get("target_formula"),
    }
    relation = _relation(kpi["value"], target)
    extra_claims: list[dict[str, Any]] = []

    if unit == "pct":
        delta = (kpi["value"] - target) * 100
        if relation == "at":
            text = f"{label} is {actual_txt}, at the {target_txt} target."
            delta_line = f"At the {target_txt} target"
        else:
            word = "above" if relation == "above" else "below"
            delta_txt = format_points(abs(delta))
            text = f"{label} is {actual_txt}, {delta_txt} percentage points {word} the {target_txt} target."
            delta_line = f"{delta_txt} percentage points {word}"
            extra_claims.append({
                "value": abs(round(delta, 1)),
                "sheet": sheet,
                "addr": addr,
                "derived": True,
                "formula": "(actual - target) * 100",
                "operands": [
                    {"sheet": sheet, "addr": addr},
                    {"sheet": target_sheet, "addr": target_addr},
                ],
            })
    else:
        delta = kpi["value"] - target
        if relation == "at":
            text = f"{label} is {actual_txt}, at the {target_txt} target."
            delta_line = f"At the {target_txt} target"
        else:
            word = "above" if relation == "above" else "below"
            delta_txt = format_value(abs(delta), unit)
            text = f"{label} is {actual_txt}, {delta_txt} {word} the {target_txt} target."
            delta_line = f"{delta_txt} {word}"
            extra_claims.append({
                "value": abs(delta),
                "sheet": sheet,
                "addr": addr,
                "derived": True,
                "formula": "actual - target",
                "operands": [
                    {"sheet": sheet, "addr": addr},
                    {"sheet": target_sheet, "addr": target_addr},
                ],
            })

    claims.extend([target_claim, *extra_claims])
    return {
        "kind": "kpi",
        "layout": "versus-target",
        "text": text,
        "slots": {
            "eyebrow": label,
            "actual": actual_txt,
            "target": target_txt,
            "delta": delta_line,
            "direction": relation,
        },
        "claims": claims,
        "citations": cites,
    }

def _movers_beat(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [(row, row["value"] - row["prior"]) for row in rows]
    units = {row.get("unit") or "number" for row, _delta in scored}
    claims: list[dict[str, Any]] = []
    if len(units) > 1:
        text = "Selected movements are shown by source unit; cross-unit movements are not ranked."
    else:
        lead, lead_delta = max(scored, key=lambda item: abs(item[1]))
        unit = lead.get("unit") or "number"
        if lead_delta == 0:
            text = "No selected line moved versus the prior period."
        else:
            word = "up" if lead_delta > 0 else "down"
            if unit == "pct":
                delta_text = f"{abs(lead_delta) * 100:.1f} percentage points"
                claim_value = abs(round(lead_delta * 100, 1))
            else:
                delta_text = format_value(abs(lead_delta), unit)
                claim_value = abs(lead_delta)
            text = f"Largest selected move is {lead['label']}, {word} {delta_text} from the prior period."
            claims.append({"value": claim_value, "sheet": lead["sheet"], "addr": lead["addr"], "derived": True})

    table = []
    cites = []
    for row, delta in scored:
        row_unit = row.get("unit") or "number"
        cites.append(_workbook(row["sheet"], row["addr"]))
        cites.append(_workbook(row["sheet"], row["prior_addr"]))
        current_claim = round(row["value"] * 100, 1) if row_unit == "pct" else row["value"]
        prior_claim = round(row["prior"] * 100, 1) if row_unit == "pct" else row["prior"]
        claims.append({"value": current_claim, "cell": row["value"], "unit": row_unit, "sheet": row["sheet"], "addr": row["addr"], "formula": row.get("formula")})
        claims.append({"value": prior_claim, "cell": row["prior"], "unit": row_unit, "sheet": row["sheet"], "addr": row["prior_addr"], "formula": row.get("prior_formula")})
        if delta == 0:
            delta_txt = "Flat"
        elif row_unit == "pct":
            delta_txt = f"{delta * 100:+.1f} pp"
            claims.append({
                "value": round(delta * 100, 1),
                "sheet": row["sheet"],
                "addr": row["addr"],
                "derived": True,
                "formula": "(actual - prior) * 100",
                "operands": [
                    {"sheet": row["sheet"], "addr": row["addr"]},
                    {"sheet": row["sheet"], "addr": row["prior_addr"]},
                ],
            })
        else:
            sign = "+" if delta > 0 else "-"
            delta_txt = sign + format_value(abs(delta), row_unit, full=True)
            claims.append({
                "value": delta,
                "sheet": row["sheet"],
                "addr": row["addr"],
                "derived": True,
                "formula": "actual - prior",
                "operands": [
                    {"sheet": row["sheet"], "addr": row["addr"]},
                    {"sheet": row["sheet"], "addr": row["prior_addr"]},
                ],
            })
        table.append(
            {
                "line": row["label"],
                "this_week": row.get("display") or format_value(row["value"], row_unit, full=True),
                "last_week": row.get("prior_display") or format_value(row["prior"], row_unit, full=True),
                "delta": delta_txt,
            }
        )
    return {
        "kind": "movers",
        "layout": "movers",
        "text": text,
        "slots": {"eyebrow": "Movers", "rows": table},
        "claims": claims,
        "citations": cites,
    }


def _source_range_beat(source: dict[str, Any]) -> dict[str, Any]:
    claims: list[dict[str, Any]] = []
    cites: list[dict[str, str]] = []
    rows = source.get("rows") or []
    for row in rows:
        for cell in row:
            addr = cell.get("addr")
            display = str(cell.get("display") or "")
            if not addr or not display:
                continue
            cites.append(_workbook(source["sheet"], addr))
            value = cell.get("value")
            if isinstance(value, (int, float)):
                unit = cell.get("unit") or "number"
                claims.append(
                    {
                        "value": round(value * 100, 1) if unit == "pct" else value,
                        "cell": value,
                        "unit": unit,
                        "sheet": source["sheet"],
                        "addr": addr,
                    }
                )
            else:
                from .numbers import parse_numbers

                for token in parse_numbers(display):
                    claims.append(
                        {
                            "value": token,
                            "sheet": source["sheet"],
                            "addr": addr,
                            "in_text": True,
                        }
                    )
    if not cites:
        raise CompileError([f"source range {source.get('sheet')} has no displayable cells"])
    return {
        "kind": "source",
        "layout": "source-range",
        "text": f"Source data from {source['sheet']}.",
        "slots": {"eyebrow": "Source data"},
        "visual": {"range": source.get("range"), "rows": rows},
        "claims": claims,
        "citations": cites,
    }


def _text_claims(text: str, block_id: str) -> list[dict[str, Any]]:
    from .numbers import parse_numbers

    return [{"value": number, "block_id": block_id, "in_text": True, "source": text} for number in parse_numbers(text)]


def _integers_in(text: str) -> list[int]:
    from .numbers import parse_numbers

    return [int(number) for number in parse_numbers(text) if float(number).is_integer()]


def _relation(actual: float, target: float) -> str:
    if actual == target:
        return "at"
    return "above" if actual > target else "below"


def _workbook(sheet: str, addr: str) -> dict[str, str]:
    return {"kind": "workbook", "sheet": sheet, "addr": addr}


def _document(block_id: str) -> dict[str, str]:
    return {"kind": "document", "block_id": block_id}


def _add(beats: list[dict[str, Any]], **beat: Any) -> None:
    beats.append(beat)


def _script(skill_id: str, title: str, beats: list[dict[str, Any]]) -> dict[str, Any]:
    for index, beat in enumerate(beats, start=1):
        beat["ord"] = index
    return {
        "skill_id": skill_id,
        "skill_version": "1.0.0",
        "language": "en",
        "title": title,
        "renderer": SKILL_RENDERER[skill_id],
        "beats": beats,
    }
