"""Ingest real documents into compiler inputs.

Stdlib only: a .docx file is a zip of XML, so no new dependency is needed
to read one. Every non-empty paragraph becomes a block, in document order
— the director's completeness rule starts here, with nothing skipped.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class IngestError(Exception):
    pass


def parse_docx(source: str | Path | bytes) -> dict[str, Any]:
    """Parse a .docx file into a document pack for compile_document.

    The first paragraph is the title and is not repeated as a slide.
    A table row is one block, cells joined, so a header is not its own slide.
    """
    try:
        if isinstance(source, bytes):
            archive = zipfile.ZipFile(io.BytesIO(source))
        else:
            archive = zipfile.ZipFile(str(source))
    except zipfile.BadZipFile as exc:
        raise IngestError(f"not a readable .docx file: {exc}") from exc
    try:
        try:
            raw = archive.read("word/document.xml")
        except KeyError as exc:
            raise IngestError("docx has no word/document.xml") from exc
    finally:
        archive.close()
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise IngestError(f"docx document.xml does not parse: {exc}") from exc
    body = root.find(f"{_W}body")
    if body is None:
        raise IngestError("docx has no document body")
    pieces = _body_pieces(body)
    if not pieces:
        raise IngestError("document has no readable text")
    blocks = [
        {"id": f"p{index}", "text": text, "role": _role(text)}
        for index, text in enumerate(pieces[1:], start=2)
    ]
    return {"title": pieces[0], "title_block": "p1", "blocks": blocks}


def _body_pieces(body: ET.Element) -> list[str]:
    pieces: list[str] = []
    for child in list(body):
        if child.tag == f"{_W}p":
            text = _paragraph_text(child).strip()
            if text:
                pieces.append(text)
        elif child.tag == f"{_W}tbl":
            pieces.extend(_table_rows(child))
    return pieces


def _table_rows(table: ET.Element) -> list[str]:
    rows: list[str] = []
    for row in table.findall(f"{_W}tr"):
        cells: list[str] = []
        for cell in row.findall(f"{_W}tc"):
            bits = [
                _paragraph_text(paragraph).strip()
                for paragraph in cell.findall(f"{_W}p")
            ]
            text = " ".join(bit for bit in bits if bit).strip()
            if text:
                cells.append(text)
        if cells:
            rows.append(" ".join(cells))
    return rows


def _role(text: str) -> str:
    lowered = text.strip().lower()
    if lowered.startswith(("approve ", "ask ", "please approve", "request ")):
        return "ask"
    if lowered.startswith("risk"):
        return "risk"
    return "evidence"


def _paragraph_text(paragraph: ET.Element) -> str:
    parts: list[str] = []
    for node in paragraph.iter():
        if node.tag == f"{_W}t":
            parts.append(node.text or "")
        elif node.tag in {_W + "tab", _W + "br"}:
            parts.append(" ")
    return "".join(parts)
