"""Provider interfaces. Implementations live in :mod:`.local` and :mod:`.bedrock`."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


class ProviderError(RuntimeError):
    """A provider is misconfigured, refused by policy, or failed a call."""


@dataclass(frozen=True)
class Attachment:
    """Source bytes handed to a multimodal model (image or document)."""

    kind: str  # "image" | "document"
    format: str  # png, jpeg, gif, webp | pdf, docx, xlsx, csv, txt, md, html
    data: bytes
    name: str = "source"


@dataclass(frozen=True)
class InferenceResult:
    text: str
    provider: str
    model_id: str
    usage: dict[str, int] = field(default_factory=dict)


@runtime_checkable
class InferenceProvider(Protocol):
    name: str
    model_id: str

    def complete(
        self,
        system: str,
        prompt: str,
        *,
        max_tokens: int = 1024,
        attachments: tuple[Attachment, ...] = (),
    ) -> InferenceResult: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    name: str
    model_id: str
    dims: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


@runtime_checkable
class TranscriptionProvider(Protocol):
    name: str
    model_id: str

    def transcribe(self, path: Path, language: str = "en") -> list[dict[str, Any]]: ...


@runtime_checkable
class SpeechProvider(Protocol):
    name: str
    model_id: str

    def narrate(self, script: dict[str, Any], out_path: Path) -> Path: ...


@runtime_checkable
class ImageTextProvider(Protocol):
    name: str
    model_id: str

    def extract_text(self, data: bytes, fmt: str) -> list[str]: ...
