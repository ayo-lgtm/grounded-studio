"""Ingest real documents into compiler inputs.

Stdlib only: a .docx file is a zip of XML, so no new dependency is needed
to read one. Every non-empty paragraph becomes a block, in document order
— the director's completeness rule starts here, with nothing skipped.
"""

from __future__ import annotations

import io
import re
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
    items = _body_items(body)
    if not items:
        raise IngestError("document has no readable text")
    blocks = []
    for index, (text, heading) in enumerate(items[1:], start=2):
        block = {"id": f"p{index}", "text": text, "role": _role(text)}
        if heading:
            block["heading_path"] = heading
        blocks.append(block)
    return {"title": items[0][0], "title_block": "p1", "blocks": blocks}


def _body_pieces(body: ET.Element) -> list[str]:
    return [text for text, _heading in _body_items(body)]


def _body_items(body: ET.Element) -> list[tuple[str, str | None]]:
    """(text, heading_path) in document order. Headings set the path."""
    items: list[tuple[str, str | None]] = []
    stack: list[tuple[int, str]] = []
    for child in list(body):
        if child.tag == f"{_W}p":
            text = _paragraph_text(child).strip()
            if not text:
                continue
            level = _heading_level(child)
            if level is not None:
                stack = [entry for entry in stack if entry[0] < level] + [(level, text)]
            items.append((text, " > ".join(name for _lvl, name in stack[:-1]) if level else _path(stack)))
        elif child.tag == f"{_W}tbl":
            for row in _table_rows(child):
                items.append((row, _path(stack)))
    return items


def _path(stack: list[tuple[int, str]]) -> str | None:
    return " > ".join(name for _lvl, name in stack) or None


def _heading_level(paragraph: ET.Element) -> int | None:
    style = paragraph.find(f"{_W}pPr/{_W}pStyle")
    value = (style.get(f"{_W}val") if style is not None else "") or ""
    match = re.fullmatch(r"(?i)heading\s*([1-6])|title", value)
    if not match:
        return None
    return int(match.group(1)) if match.group(1) else 0


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


def parse_pdf(source: str | Path | bytes) -> dict[str, Any]:
    """Parse a text-bearing PDF into page-grounded document blocks.

    OCR is intentionally not performed here. Scanned/garbled pages fail closed
    so a future page-image/OCR pipeline cannot be mistaken for extracted truth.
    """
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise IngestError("PDF support requires pypdf") from exc

    try:
        stream = io.BytesIO(source) if isinstance(source, bytes) else str(source)
        reader = PdfReader(stream)
    except Exception as exc:
        raise IngestError(f"not a readable PDF: {exc}") from exc

    blocks: list[dict[str, Any]] = []
    title = "PDF Briefing"
    title_block = "pdf-p1-b1"
    first_text = ""
    for page_index, page in enumerate(reader.pages, start=1):
        try:
            text = (page.extract_text() or "").strip()
        except Exception as exc:
            raise IngestError(f"PDF page {page_index} text extraction failed: {exc}") from exc
        if not text:
            continue
        if not first_text:
            first_text = text
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n|(?<=\.)\s*\n", text) if part.strip()]
        if not paragraphs:
            paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
        for block_index, paragraph in enumerate(paragraphs, start=1):
            block_id = f"pdf-p{page_index}-b{block_index}"
            blocks.append(
                {
                    "id": block_id,
                    "text": paragraph,
                    "role": _role(paragraph),
                    "page": page_index,
                }
            )
    if not blocks:
        raise IngestError(
            "PDF has no extractable text; scanned PDFs require the page-image/OCR ingestion path"
        )

    first_line = next((line.strip() for line in first_text.splitlines() if line.strip()), "")
    if first_line:
        title = first_line[:180]
        title_block = blocks[0]["id"]
        # Avoid repeating a title-only first block as a slide.
        if blocks[0]["text"].strip() == first_line:
            blocks = blocks[1:]
    return {"title": title, "title_block": title_block, "blocks": blocks}


_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def parse_pptx(source: str | Path | bytes) -> dict[str, Any]:
    """Parse a .pptx deck into slide-grounded blocks (``s{slide}-b{n}``).

    Each text frame paragraph is a block with ``page`` = slide number, so a
    citation names the slide. Speaker notes become blocks too, marked
    ``role: notes``. Images and charts are not interpreted.
    """
    try:
        archive = zipfile.ZipFile(io.BytesIO(source) if isinstance(source, bytes) else str(source))
    except zipfile.BadZipFile as exc:
        raise IngestError(f"not a readable .pptx file: {exc}") from exc
    try:
        names = archive.namelist()
        slides = sorted(
            (name for name in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)),
            key=lambda name: int(re.findall(r"\d+", name)[-1]),
        )
        if not slides:
            raise IngestError("pptx has no slides")
        blocks: list[dict[str, Any]] = []
        title = ""
        title_block = ""
        for slide_name in slides:
            number = int(re.findall(r"\d+", slide_name)[-1])
            paragraphs = _drawing_paragraphs(archive.read(slide_name))
            notes_name = f"ppt/notesSlides/notesSlide{number}.xml"
            notes = _drawing_paragraphs(archive.read(notes_name)) if notes_name in names else []
            for index, text in enumerate(paragraphs, start=1):
                block_id = f"s{number}-b{index}"
                if not title:
                    title, title_block = text, block_id
                    continue
                blocks.append({"id": block_id, "text": text, "role": _role(text), "page": number})
            for index, text in enumerate(notes, start=1):
                if re.fullmatch(r"\d+", text):
                    continue  # slide-number placeholder in the notes page
                blocks.append({"id": f"s{number}-n{index}", "text": text, "role": "notes", "page": number})
    finally:
        archive.close()
    if not title:
        raise IngestError("presentation has no readable text")
    return {"title": title, "title_block": title_block, "blocks": blocks}


def _drawing_paragraphs(raw: bytes) -> list[str]:
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise IngestError(f"slide XML does not parse: {exc}") from exc
    out: list[str] = []
    for paragraph in root.iter(f"{_A}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{_A}t")).strip()
        if text:
            out.append(text)
    return out


def parse_text(data: bytes, *, markdown: bool = False) -> dict[str, Any]:
    """Plain text or Markdown: blank-line separated paragraphs become blocks."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise IngestError("text documents must be UTF-8") from exc
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        raise IngestError("document has no readable text")
    blocks: list[dict[str, Any]] = []
    heading: str | None = None
    title = paragraphs[0].lstrip("# ").strip() if markdown else paragraphs[0]
    for index, paragraph in enumerate(paragraphs[1:], start=2):
        if markdown and paragraph.startswith("#"):
            heading = paragraph.lstrip("# ").strip()
        clean = paragraph.lstrip("# ").strip() if markdown else paragraph
        block = {"id": f"t{index}", "text": " ".join(clean.split()), "role": _role(clean)}
        if heading:
            block["heading_path"] = heading
        blocks.append(block)
    return {"title": " ".join(title.split()), "title_block": "t1", "blocks": blocks}
