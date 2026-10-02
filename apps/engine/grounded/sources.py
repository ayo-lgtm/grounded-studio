"""Detect, unpack and normalize uploaded sources. All parsing is local.

Supported inputs:

=================  ==============================================  =============
asset kind         formats                                         citation unit
=================  ==============================================  =============
workbook           .xlsx .xlsm .csv (.json pack)                   sheet!cell / range
document           .docx .pdf (text layer) .txt .md (.json pack)   block / page
presentation       .pptx                                           slide block
image              .png .jpg .jpeg .gif .webp (screenshots)        image text block
recording          .mp4 .mov .webm .mkv .m4a .mp3 .wav             timestamps
package            .zip of any of the above (one level)            per member
=================  ==============================================  =============

Legacy binary .xls/.doc/.ppt and scanned PDFs without a text layer fail
closed with an explicit message rather than producing unverifiable text.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from .compile_deck import CompileError

IMAGE_EXT = {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".gif": "gif", ".webp": "webp"}
RECORDING_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".m4a", ".mp3", ".wav", ".aac", ".ogg"}

MAX_PACKAGE_MEMBERS = 200
MAX_PACKAGE_BYTES = 2 * 1024**3
MAX_COMPRESSION_RATIO = 200


class SourceError(CompileError):
    pass


@dataclass
class Detected:
    kind: str  # workbook | document | presentation | image | recording | package
    format: str  # xlsx, csv, json, docx, pdf, txt, md, pptx, png..., mp4..., zip


def detect(filename: str | None, head: bytes) -> Detected:
    """Classify by magic bytes first, extension second."""
    name = (filename or "").lower()
    suffix = PurePosixPath(name).suffix
    if head[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        raise SourceError([f"{suffix or 'legacy Office'} binary files are not supported; save as .xlsx/.docx/.pptx"])
    if head.startswith(b"%PDF"):
        return Detected("document", "pdf")
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return Detected("image", "png")
    if head[:3] == b"\xff\xd8\xff":
        return Detected("image", "jpeg")
    if head[:6] in {b"GIF87a", b"GIF89a"}:
        return Detected("image", "gif")
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return Detected("image", "webp")
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return Detected("recording", "wav")
    if head[4:8] == b"ftyp" or head[:4] == b"\x1aE\xdf\xa3" or head[:3] == b"ID3" or head[:4] == b"OggS":
        return Detected("recording", suffix.lstrip(".") or "mp4")
    if head[:2] == b"PK":
        return _detect_zip(name, head)
    if suffix in RECORDING_EXT:
        return Detected("recording", suffix.lstrip("."))
    stripped = head.lstrip()
    if stripped[:1] in {b"{", b"["}:
        return Detected("workbook" if "workbook" in name or "kpi" in name else "document", "json")
    if suffix == ".csv":
        return Detected("workbook", "csv")
    if suffix in {".md", ".markdown"}:
        return Detected("document", "md")
    if suffix in {".txt", ""}:
        return Detected("document", "txt")
    raise SourceError([f"unsupported file type {suffix or '(none)'}"])


def _detect_zip(name: str, head: bytes) -> Detected:
    # Office files are zips; their first entry is usually [Content_Types].xml.
    suffix = PurePosixPath(name).suffix
    office = {".xlsx": ("workbook", "xlsx"), ".xlsm": ("workbook", "xlsx"), ".docx": ("document", "docx"), ".pptx": ("presentation", "pptx")}
    if suffix in office:
        return Detected(*office[suffix])
    return Detected("package", "zip")


def sniff_office(data: bytes) -> Detected | None:
    """Look inside a zip to tell xlsx/docx/pptx/package apart."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = set(archive.namelist())
    except zipfile.BadZipFile:
        return None
    if "xl/workbook.xml" in names:
        return Detected("workbook", "xlsx")
    if "word/document.xml" in names:
        return Detected("document", "docx")
    if "ppt/presentation.xml" in names:
        return Detected("presentation", "pptx")
    return Detected("package", "zip")


def detect_bytes(filename: str | None, data: bytes) -> Detected:
    found = detect(filename, data[:64])
    if data[:2] == b"PK":
        inside = sniff_office(data)
        if inside is not None:
            return inside
    return found


@dataclass
class Member:
    name: str
    data: bytes
    detected: Detected


def unpack(data: bytes) -> list[Member]:
    """Expand a mixed-source package. One level, bounded, no path tricks."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise SourceError([f"package is not a readable zip ({exc})"]) from exc
    members: list[Member] = []
    total = 0
    with archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        if len(infos) > MAX_PACKAGE_MEMBERS:
            raise SourceError([f"package has more than {MAX_PACKAGE_MEMBERS} files"])
        for info in infos:
            base = PurePosixPath(info.filename.replace("\\", "/")).name
            if not base or base.startswith(".") or "__MACOSX" in info.filename:
                continue
            if info.flag_bits & 0x1:
                raise SourceError(["encrypted package members are not supported"])
            total += info.file_size
            if total > MAX_PACKAGE_BYTES:
                raise SourceError(["package expands beyond the size limit"])
            if info.compress_size and info.file_size / max(info.compress_size, 1) > MAX_COMPRESSION_RATIO:
                raise SourceError([f"package member {base} has a suspicious compression ratio"])
            blob = archive.read(info)
            detected = detect_bytes(base, blob)
            if detected.kind == "package":
                raise SourceError([f"nested package {base} is not supported"])
            members.append(Member(name=base, data=blob, detected=detected))
    if not members:
        raise SourceError(["package has no supported files"])
    return members


@dataclass
class Normalized:
    kind: str
    format: str
    cells: list[dict[str, Any]] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    blocks: list[dict[str, Any]] = field(default_factory=list)
    document: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)


def normalize(filename: str | None, data: bytes, *, image_text: Any = None) -> Normalized:
    """Normalize one non-recording source into cells/rows or blocks."""
    from .ingest import IngestError, parse_docx, parse_pdf, parse_pptx, parse_text
    from .ingest_workbook import extract_workbook_cells, extract_workbook_rows

    found = detect_bytes(filename, data)
    if found.kind == "workbook" and found.format != "json":
        return Normalized(
            kind="workbook",
            format=found.format,
            cells=extract_workbook_cells(data),
            rows=extract_workbook_rows(data),
        )
    if found.kind == "workbook":
        return Normalized(kind="workbook", format="json")
    try:
        if found.format == "pdf":
            doc = parse_pdf(data)
        elif found.format == "docx":
            doc = parse_docx(data)
        elif found.format == "pptx":
            doc = parse_pptx(data)
        elif found.format in {"txt", "md"}:
            doc = parse_text(data, markdown=found.format == "md")
        elif found.format == "json":
            import json

            doc = json.loads(data)
            if not isinstance(doc, dict):
                raise IngestError("document JSON must be an object")
        elif found.kind == "image":
            doc = _image_document(data, found.format, image_text)
        else:
            raise SourceError([f"{found.kind} sources are normalized by their own job"])
    except IngestError as exc:
        raise SourceError([str(exc)]) from exc
    except ValueError as exc:
        raise SourceError([f"document does not parse ({type(exc).__name__})"]) from exc
    return Normalized(kind=found.kind, format=found.format, blocks=document_blocks(doc), document=doc)


def _image_document(data: bytes, fmt: str, provider: Any) -> dict[str, Any]:
    from .ingest import IngestError

    if provider is None:
        raise IngestError(
            "screenshot text needs GROUNDED_IMAGE_TEXT_PROVIDER (local-ocr, or bedrock in aws-private)"
        )
    paragraphs = provider.extract_text(data, fmt)
    if not paragraphs:
        raise IngestError("no readable text in the screenshot")
    extractor = f"{getattr(provider, 'name', 'ocr')}:{getattr(provider, 'model_id', '')}"
    blocks = [
        {"id": f"img-b{index}", "text": text, "role": "evidence", "page": 1, "extractor": extractor}
        for index, text in enumerate(paragraphs[1:], start=2)
    ]
    return {"title": paragraphs[0], "title_block": "img-b1", "blocks": blocks, "extractor": extractor}


def document_blocks(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Persistable blocks: title block first, then body blocks in order."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    title = str(doc.get("title") or "").strip()
    title_block = str(doc.get("title_block") or "p1")
    if title:
        out.append({"block_id": title_block, "text": title, "page": 1 if title_block.startswith(("pdf-p1", "s1", "img")) else None,
                    "heading_path": None, "extractor": doc.get("extractor")})
        seen.add(title_block)
    for block in doc.get("blocks") or []:
        block_id = str(block.get("id") or "")
        text = str(block.get("text") or "").strip()
        if not block_id or not text or block_id in seen:
            continue
        out.append(
            {
                "block_id": block_id,
                "text": text,
                "page": block.get("page"),
                "heading_path": block.get("heading_path"),
                "extractor": block.get("extractor"),
            }
        )
        seen.add(block_id)
    return out
