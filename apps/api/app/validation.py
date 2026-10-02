"""Pure input-validation helpers for the Phase 1 API.

Kept free of third-party imports so the rules are unit-testable without
a database, Redis, or MinIO.
"""

from __future__ import annotations

import os

#: Kinds accepted by the upload endpoint. Mirrors the ``asset_kind`` enum in
#: ``schema/schema.sql``.
ALLOWED_ASSET_KINDS = frozenset(
    {"recording", "workbook", "document", "attachment", "presentation", "image", "package"}
)

#: Upper bound for a single uploaded asset. Uploads stream to private storage
#: in bounded parts, so the API never holds a whole body in memory.
MAX_UPLOAD_BYTES = int(os.environ.get("GROUNDED_MAX_UPLOAD_BYTES") or 4 * 1024**3)

_CHUNK_SIZE = 8 * 1024 * 1024


def sanitize_filename(name: str | None) -> str:
    """Return a safe basename for ``name``.

    Strips directories, path separators, and NUL bytes; falls back to
    ``"upload.bin"`` for empty input; truncates to 128 characters.
    """
    if not name:
        return "upload.bin"
    base = os.path.basename(name.replace("\\", "/"))
    base = base.replace("\x00", "").strip()
    if base in ("", ".", ".."):
        return "upload.bin"
    if len(base) > 128:
        stem, dot, ext = base.rpartition(".")
        if dot and len(ext) <= 16:
            base = stem[: 128 - len(ext) - 1] + dot + ext
        else:
            base = base[:128]
    return base


def is_allowed_kind(kind: str) -> bool:
    return kind in ALLOWED_ASSET_KINDS


class UploadTooLarge(Exception):
    pass


async def read_limited(read_chunk) -> bytes:
    """Read ``(size) -> bytes`` async chunks until ``b""``, enforcing the cap."""
    parts: list[bytes] = []
    total = 0
    while True:
        chunk = await read_chunk(_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise UploadTooLarge(f"asset exceeds {MAX_UPLOAD_BYTES} bytes")
        parts.append(chunk)
    return b"".join(parts)


async def hash_limited(read_chunk) -> tuple[int, str]:
    """Stream an upload through SHA-256 without retaining the body in memory."""
    import hashlib

    digest = hashlib.sha256()
    total = 0
    while True:
        chunk = await read_chunk(_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise UploadTooLarge(f"asset exceeds {MAX_UPLOAD_BYTES} bytes")
        digest.update(chunk)
    return total, digest.hexdigest()
