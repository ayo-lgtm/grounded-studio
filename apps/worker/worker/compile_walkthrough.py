"""product-walkthrough compiler.

If MODEL_BASE_URL is unset, builds a conservative script from transcript
segments so the loop can be tested without a GPU.
"""

from typing import Any


def stub_from_transcript(segments: list[dict[str, Any]]) -> dict[str, Any]:
    beats = []
    for i, seg in enumerate(segments, start=1):
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        beats.append(
            {
                "ord": len(beats) + 1,
                "kind": "hook" if i == 1 else "step",
                "text": text,
                "citations": [
                    {
                        "kind": "recording",
                        "t_start_ms": int(seg["t_start_ms"]),
                        "t_end_ms": int(seg["t_end_ms"]),
                    }
                ],
            }
        )
    return {
        "skill_id": "product-walkthrough",
        "skill_version": "1.0.0",
        "language": "en",
        "title": "Walkthrough",
        "beats": beats,
    }
