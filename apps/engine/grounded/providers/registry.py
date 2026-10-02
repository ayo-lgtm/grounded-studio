"""Explicit provider selection per workload. No silent fallback.

Environment (all optional; defaults are the offline-safe choices):

``GROUNDED_INFERENCE_PROVIDER``      none | local | bedrock        (default none)
``GROUNDED_ASSIST_FEATURES``         comma list of polish, chat, summary (default empty)
``GROUNDED_EMBEDDING_PROVIDER``      local-hash | bedrock          (default local-hash)
``GROUNDED_TRANSCRIPTION_PROVIDER``  local | none                  (default local)
``GROUNDED_TTS_PROVIDER``            local | none                  (default local)
``GROUNDED_IMAGE_TEXT_PROVIDER``     none | local-ocr | bedrock    (default none)

``TRANS_PROVIDER`` / ``NARRATION_PROVIDER`` are honoured as legacy aliases.
Retired cloud values (``transcribe``, ``aws``, ``polly``, ``elevenlabs``,
``openai``, ``stub`` ...) are rejected with an error, never mapped.

Selecting ``bedrock`` for anything in offline mode is a configuration error.
When a selected provider fails at call time the caller keeps its
deterministic result or fails the job; it never retries on another provider.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping

from ..policy import EgressError, from_env
from .base import ProviderError

INFERENCE = ("none", "local", "bedrock")
EMBEDDING = ("local-hash", "bedrock")
TRANSCRIPTION = ("local", "none")
TTS = ("local", "none")
IMAGE_TEXT = ("none", "local-ocr", "bedrock")
FEATURES = frozenset({"polish", "chat", "summary"})

RETIRED = frozenset(
    {"transcribe", "aws", "aws-transcribe", "polly", "elevenlabs", "openai", "anthropic", "stub", "cloud", "public"}
)


@dataclass(frozen=True)
class Selection:
    mode: str
    inference: str
    features: frozenset[str]
    embedding: str
    transcription: str
    tts: str
    image_text: str
    models: dict[str, str]

    def uses_cloud(self) -> bool:
        return "bedrock" in {self.inference, self.embedding, self.image_text}

    def describe(self) -> dict[str, Any]:
        return {
            "inference": self.inference,
            "features": sorted(self.features),
            "embedding": self.embedding,
            "transcription": self.transcription,
            "tts": self.tts,
            "image_text": self.image_text,
            "chat_phrasing": self.inference if "chat" in self.features else "none",
            "models": dict(self.models),
        }


def _pick(env: Mapping[str, str], keys: tuple[str, ...], allowed: tuple[str, ...], default: str, label: str) -> str:
    raw = ""
    for key in keys:
        if (env.get(key) or "").strip():
            raw = env[key].strip().lower()
            break
    value = raw or default
    if value in RETIRED:
        raise ProviderError(f"{label} provider {value!r} is retired; choose one of {', '.join(allowed)}")
    if value not in allowed:
        raise ProviderError(f"unknown {label} provider {value!r}; choose one of {', '.join(allowed)}")
    return value


def selection(env: Mapping[str, str] | None = None) -> Selection:
    source = os.environ if env is None else env
    policy = from_env(source)
    inference = _pick(source, ("GROUNDED_INFERENCE_PROVIDER",), INFERENCE, "none", "inference")
    embedding = _pick(source, ("GROUNDED_EMBEDDING_PROVIDER",), EMBEDDING, "local-hash", "embedding")
    transcription = _pick(
        source, ("GROUNDED_TRANSCRIPTION_PROVIDER", "TRANS_PROVIDER"), TRANSCRIPTION, "local", "transcription"
    )
    tts = _pick(source, ("GROUNDED_TTS_PROVIDER", "NARRATION_PROVIDER"), TTS, "local", "tts")
    image_text = _pick(source, ("GROUNDED_IMAGE_TEXT_PROVIDER",), IMAGE_TEXT, "none", "image-text")
    features = frozenset(
        part.strip().lower() for part in (source.get("GROUNDED_ASSIST_FEATURES") or "").split(",") if part.strip()
    )
    unknown = sorted(features - FEATURES)
    if unknown:
        raise ProviderError(f"unknown assist features {', '.join(unknown)}")
    if features and inference == "none":
        raise ProviderError("GROUNDED_ASSIST_FEATURES needs GROUNDED_INFERENCE_PROVIDER=local or bedrock")

    models: dict[str, str] = {}
    cloud = [name for name, value in (("inference", inference), ("embedding", embedding), ("image-text", image_text)) if value == "bedrock"]
    if cloud and policy.offline:
        raise ProviderError(
            "offline mode refuses Bedrock for " + ", ".join(cloud) + "; set GROUNDED_DEPLOYMENT_MODE=aws-private"
        )
    region = (source.get("GROUNDED_BEDROCK_REGION") or source.get("AWS_REGION") or "").strip().lower()
    try:
        if inference == "bedrock":
            models["text"] = (source.get("GROUNDED_BEDROCK_TEXT_MODEL") or "").strip()
            policy.check_bedrock(models["text"], region)
        if image_text == "bedrock":
            models["multimodal"] = (
                source.get("GROUNDED_BEDROCK_MULTIMODAL_MODEL") or source.get("GROUNDED_BEDROCK_TEXT_MODEL") or ""
            ).strip()
            policy.check_bedrock(models["multimodal"], region)
        if embedding == "bedrock":
            models["embedding"] = (source.get("GROUNDED_BEDROCK_EMBEDDING_MODEL") or "").strip()
            policy.check_bedrock(models["embedding"], region)
        endpoint = (source.get("GROUNDED_BEDROCK_ENDPOINT") or "").strip()
        if cloud and endpoint:
            policy.check_url(endpoint, "GROUNDED_BEDROCK_ENDPOINT")
    except EgressError as exc:
        raise ProviderError(str(exc)) from exc
    if cloud:
        from .bedrock import assert_role_credentials

        assert_role_credentials(dict(source))
    if inference == "local":
        from ..policy import host_of

        models["text"] = (source.get("MODEL_NAME") or "local-instruct").strip()
        base_url = (source.get("MODEL_BASE_URL") or "").strip()
        if not base_url:
            raise ProviderError("GROUNDED_INFERENCE_PROVIDER=local needs MODEL_BASE_URL")
        if not policy.is_private_host(host_of(base_url)):
            raise ProviderError("MODEL_BASE_URL must be private infrastructure")
    return Selection(
        mode=policy.mode,
        inference=inference,
        features=features,
        embedding=embedding,
        transcription=transcription,
        tts=tts,
        image_text=image_text,
        models=models,
    )


def inference_provider(feature: str, *, client: Any = None):
    """The selected inference provider for ``feature``, or ``None`` if not enabled.

    ``None`` means "use the deterministic result". Errors constructing the
    selected provider propagate; there is no fallback to another provider.
    """
    chosen = selection()
    if feature not in chosen.features or chosen.inference == "none":
        return None
    if chosen.inference == "local":
        from .local import LocalInference

        return LocalInference()
    from .bedrock import BedrockInference

    return BedrockInference(client=client)


def embedding_provider(*, client: Any = None):
    chosen = selection()
    if chosen.embedding == "bedrock":
        from .bedrock import BedrockEmbeddings

        return BedrockEmbeddings(client=client)
    from .local import LocalHashEmbeddings

    return LocalHashEmbeddings()


def transcription_provider():
    chosen = selection()
    if chosen.transcription == "none":
        raise ProviderError("transcription is disabled for this deployment")
    from .local import LocalWhisper

    return LocalWhisper()


def speech_provider():
    chosen = selection()
    if chosen.tts == "none":
        return None
    from .local import LocalPiper

    return LocalPiper()


def image_text_provider(*, client: Any = None):
    chosen = selection()
    if chosen.image_text == "none":
        return None
    if chosen.image_text == "local-ocr":
        from .local import LocalOCR

        return LocalOCR()
    from .bedrock import BedrockImageText

    return BedrockImageText(client=client)
