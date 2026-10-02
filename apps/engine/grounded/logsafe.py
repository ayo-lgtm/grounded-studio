"""Content-free operational logging.

Application logs carry identifiers, counts, durations, provider names and
error *classes* only - never document text, cell values, transcript text,
prompts, model output, filenames or exception messages (which can quote
source content). :func:`log_event` enforces an allowlist of field names;
anything else is dropped. :func:`configure` also pins chatty SDK loggers
(botocore wire logging can print request bodies at DEBUG) to WARNING and
installs a filter that blocks records from those loggers below WARNING.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

LOGGER = logging.getLogger("grounded")

SAFE_FIELDS = frozenset(
    {
        "briefing_id", "job_id", "job_type", "asset_id", "asset_kind", "detected_format",
        "script_id", "version", "beats", "citations", "claims", "cells", "rows", "blocks",
        "segments", "members", "bytes", "duration_ms", "elapsed_ms", "provider", "model_id",
        "mode", "state", "error_class", "count", "user_id", "status", "skill_id",
        "skill_version", "feature", "dims",
    }
)

_QUIET = ("botocore", "boto3", "urllib3", "s3transfer", "httpx", "httpcore", "faster_whisper", "huggingface_hub")


class _SdkFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.name.split(".")[0] in _QUIET:
            return record.levelno >= logging.WARNING
        return True


def configure(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if not any(getattr(handler, "_grounded", False) for handler in root.handlers):
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler.addFilter(_SdkFilter())
        handler._grounded = True  # type: ignore[attr-defined]
        root.addHandler(handler)
    root.setLevel(level)
    for name in _QUIET:
        logging.getLogger(name).setLevel(logging.WARNING)


def _safe(value: Any) -> Any:
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    text = str(value)
    # Identifiers and enum-like values only; long free text is never logged.
    if len(text) > 80 or any(ch in text for ch in "\n\r"):
        return "[redacted]"
    return text


def log_event(event: str, **fields: Any) -> dict[str, Any]:
    record = {"event": str(event)[:64]}
    for key, value in fields.items():
        if key in SAFE_FIELDS:
            record[key] = _safe(value)
    LOGGER.info(json.dumps(record, sort_keys=True))
    return record


def log_failure(event: str, exc: BaseException, **fields: Any) -> dict[str, Any]:
    """Record that something failed without the exception message."""
    return log_event(event, error_class=type(exc).__name__, **fields)
