"""Byte ranges for the film. Players seek with Range; decks are small enough to slice in memory."""

from __future__ import annotations


def parse_range(header: str | None, size: int) -> tuple[int, int] | None:
    """Inclusive byte span, or None when the request has no Range.

    Raises ValueError when the header is present and cannot be satisfied.
    Only the first range is honored.
    """
    if header is None or not header.strip():
        return None
    spec = header.strip()
    if not spec.lower().startswith("bytes="):
        raise ValueError("unsupported range")
    part = spec[6:].split(",", 1)[0].strip()
    if "-" not in part:
        raise ValueError("bad range")
    start_s, end_s = part.split("-", 1)
    if start_s == "" and end_s == "":
        raise ValueError("bad range")
    if size <= 0:
        raise ValueError("unsatisfiable")
    if start_s == "":
        length = _int(end_s)
        if length <= 0:
            raise ValueError("bad range")
        if length > size:
            length = size
        return size - length, size - 1
    start = _int(start_s)
    if start < 0 or start >= size:
        raise ValueError("unsatisfiable")
    if end_s == "":
        end = size - 1
    else:
        end = _int(end_s)
        if end < start:
            raise ValueError("unsatisfiable")
        if end >= size:
            end = size - 1
    return start, end


def slice_body(data: bytes, header: str | None) -> tuple[int, bytes, dict[str, str]]:
    """Return status, body, and range headers for one object."""
    size = len(data)
    span = parse_range(header, size)
    if span is None:
        return 200, data, {"Accept-Ranges": "bytes", "Content-Length": str(size)}
    start, end = span
    body = data[start : end + 1]
    return 206, body, {
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {start}-{end}/{size}",
        "Content-Length": str(len(body)),
    }


def content_type(key: str) -> str:
    suffix = key.rsplit(".", 1)[-1].lower() if "." in key else ""
    return {
        "mp4": "video/mp4",
        "html": "text/html; charset=utf-8",
        "htm": "text/html; charset=utf-8",
        "vtt": "text/vtt; charset=utf-8",
        "json": "application/json",
        "mp3": "audio/mpeg",
        "md": "text/markdown; charset=utf-8",
    }.get(suffix, "application/octet-stream")


def _int(value: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError("bad range") from exc
