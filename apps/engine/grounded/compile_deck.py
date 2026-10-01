"""Fill locked deck masters from a workbook pack or a document. No freeform layout."""

from __future__ import annotations

from typing import Any

from .layouts import SKILL_RENDERER
from .numbers import format_pct, format_points, format_usd, format_usd_full


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
    target = kpi.get("target")
    target_sheet = kpi.get("target_sheet") or sheet
    target_addr = kpi.get("target_addr")
    cites = [_workbook(sheet, addr)]
    if kpi["unit"] == "pct":
        actual_txt = kpi.get("display") or format_pct(kpi["value"])
        actual_claim = {"value": round(kpi["value"] * 100, 1), "cell": kpi["value"], "unit": "pct", "sheet": sheet, "addr": addr}
    else:
        actual_txt = kpi.get("display") or format_usd(kpi["value"])
        actual_claim = {"value": kpi["value"], "sheet": sheet, "addr": addr}

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
    if kpi["unit"] == "pct":
        target_txt = kpi.get("target_display") or format_pct(target)
        target_claim = {
            "value": round(target * 100, 1),
            "cell": target,
            "unit": "pct",
            "sheet": target_sheet,
            "addr": target_addr,
        }
        delta_points = (kpi["value"] - target) * 100
        delta_value = round(delta_points, 1)
        delta_txt = format_points(abs(delta_points))
        relation = _relation(kpi["value"], target)
        if relation == "at":
            text = f"{label} is {actual_txt}, at the {target_txt} target."
            delta_line = f"At the {target_txt} target"
            extra_claims = []
        else:
            word = "above" if relation == "above" else "below"
            text = f"{label} is {actual_txt}, {delta_txt} points {word} the {target_txt} target."
            delta_line = f"{delta_txt} points {word}"
            extra_claims = [{"value": abs(delta_value), "sheet": sheet, "addr": addr, "derived": True}]
    else:
        target_txt = kpi.get("target_display") or format_usd(target)
        target_claim = {"value": target, "sheet": target_sheet, "addr": target_addr}
        delta = kpi["value"] - target
        relation = _relation(kpi["value"], target)
        if relation == "at":
            text = f"{label} is {actual_txt}, at the {target_txt} target."
            delta_line = f"At the {target_txt} target"
            extra_claims = []
        else:
            word = "above" if relation == "above" else "below"
            delta_txt = format_usd(abs(delta))
            text = f"{label} is {actual_txt}, {delta_txt} {word} the {target_txt} target."
            delta_line = f"{delta_txt} {word}"
            extra_claims = [{"value": abs(delta), "sheet": sheet, "addr": addr, "derived": True}]
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
    lead, lead_delta = max(scored, key=lambda item: abs(item[1]))
    if lead_delta == 0:
        text = "No line moved versus last week."
        claims: list[dict[str, Any]] = []
    else:
        word = "up" if lead_delta > 0 else "down"
        text = f"Largest move is {lead['label']}, {word} {format_usd(abs(lead_delta))} from last week."
        claims = [{"value": abs(lead_delta), "sheet": lead["sheet"], "addr": lead["addr"], "derived": True}]

    table = []
    cites = []
    for row, delta in scored:
        cites.append(_workbook(row["sheet"], row["addr"]))
        cites.append(_workbook(row["sheet"], row["prior_addr"]))
        claims.append({"value": row["value"], "sheet": row["sheet"], "addr": row["addr"]})
        claims.append({"value": row["prior"], "sheet": row["sheet"], "addr": row["prior_addr"]})
        if delta == 0:
            delta_txt = "Flat"
        else:
            delta_txt = format_usd_full(delta)
            claims.append({"value": delta, "sheet": row["sheet"], "addr": row["addr"], "derived": True})
        table.append(
            {
                "line": row["label"],
                "this_week": row.get("display") or format_usd_full(row["value"]),
                "last_week": row.get("prior_display") or format_usd_full(row["prior"]),
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
