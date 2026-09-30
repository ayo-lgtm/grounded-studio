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
    """Parse a .docx file into a document pack for compile_document."""
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
    blocks: list[dict[str, Any]] = []
    for paragraph in body.iter(f"{_W}p"):
        text = _paragraph_text(paragraph).strip()
        if not text:
            continue
        blocks.append({"id": f"p{len(blocks) + 1}", "text": text, "role": "evidence"})
    if not blocks:
        raise IngestError("document has no readable text")
    return {"title": blocks[0]["text"], "title_block": blocks[0]["id"], "blocks": blocks}


def _paragraph_text(paragraph: ET.Element) -> str:
    parts: list[str] = []
    for node in paragraph.iter():
        if node.tag == f"{_W}t":
            parts.append(node.text or "")
        elif node.tag in {_W + "tab", _W + "br"}:
            parts.append(" ")
    return "".join(parts)
