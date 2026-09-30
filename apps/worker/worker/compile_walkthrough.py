"""product-walkthrough compiler.

Without a local model, the recording compiler drops filler and writes an edit
list. It does not restyle the recording.
"""

from typing import Any

from .bootstrap import ensure_engine

ensure_engine()

from grounded.compile_recording import compile_recording  # noqa: E402


def stub_from_transcript(segments: list[dict[str, Any]]) -> dict[str, Any]:
    return compile_recording(segments, skill_id="product-walkthrough", title="Walkthrough")
