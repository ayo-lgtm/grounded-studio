"""Amazon Bedrock / Amazon Nova providers for the ``aws-private`` profile.

These are first-class providers, but they only exist inside the policy:

* offline mode refuses them before a client is built, even an injected one;
* in aws-private mode the region, the Bedrock model ID, and the resolved
  endpoint must all be on the deployment's allowlists;
* credentials come from the default chain (an IAM role on the task/instance);
  static long-lived access keys are refused;
* the client never follows an endpoint the policy has not approved, and the
  process-wide socket guard (:mod:`grounded.guard`) backs that up.

Model output is a draft. Callers pass every factual sentence through
:mod:`grounded.grounding` and the deterministic QA gates; Nova cannot ship
an uncited number, cause, risk or recommendation.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from ..policy import EgressError, from_env
from .base import Attachment, InferenceResult, ProviderError

IMAGE_FORMATS = {"png", "jpeg", "gif", "webp"}
DOCUMENT_FORMATS = {"pdf", "csv", "doc", "docx", "xls", "xlsx", "html", "txt", "md"}


def _region(explicit: str | None) -> str:
    return (explicit or os.environ.get("GROUNDED_BEDROCK_REGION") or os.environ.get("AWS_REGION") or "").strip().lower()


def assert_role_credentials(env: dict[str, str] | None = None) -> None:
    """Refuse static long-lived AWS keys. Roles yield session credentials."""
    source = os.environ if env is None else env
    if source.get("AWS_ACCESS_KEY_ID") and not source.get("AWS_SESSION_TOKEN"):
        raise ProviderError(
            "long-lived AWS access keys are refused; run with a scoped IAM role (task/instance/IRSA)"
        )


def _client(service: str, region: str, endpoint: str | None, client: Any) -> Any:
    policy = from_env()
    if endpoint:
        try:
            policy.check_url(endpoint, f"{service} endpoint")
        except EgressError as exc:
            raise ProviderError(str(exc)) from exc
    if client is not None:
        return client
    assert_role_credentials()
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise ProviderError("boto3 is required for the Bedrock provider") from exc
    config = Config(
        region_name=region,
        retries={"max_attempts": 2, "mode": "standard"},
        connect_timeout=5,
        read_timeout=120,
        user_agent_extra="grounded-studio",
    )
    try:
        built = boto3.session.Session().client(service, region_name=region, endpoint_url=endpoint or None, config=config)
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"cannot create {service} client ({type(exc).__name__})") from None
    resolved = getattr(getattr(built, "meta", None), "endpoint_url", "") or ""
    try:
        policy.check_url(resolved, f"{service} resolved endpoint")
    except EgressError as exc:
        raise ProviderError(str(exc)) from exc
    return built


class BedrockInference:
    """Converse API over an approved Nova (or other approved) model."""

    name = "bedrock"

    def __init__(
        self,
        model_id: str | None = None,
        region: str | None = None,
        endpoint: str | None = None,
        client: Any = None,
    ) -> None:
        self.model_id = (model_id or os.environ.get("GROUNDED_BEDROCK_TEXT_MODEL") or "").strip()
        self.region = _region(region)
        self.endpoint = (endpoint if endpoint is not None else os.environ.get("GROUNDED_BEDROCK_ENDPOINT", "")).strip()
        try:
            from_env().check_bedrock(self.model_id, self.region)
        except EgressError as exc:
            raise ProviderError(str(exc)) from exc
        self._client = _client("bedrock-runtime", self.region, self.endpoint, client)

    def complete(
        self,
        system: str,
        prompt: str,
        *,
        max_tokens: int = 1024,
        attachments: tuple[Attachment, ...] = (),
    ) -> InferenceResult:
        content: list[dict[str, Any]] = []
        for index, item in enumerate(attachments, start=1):
            content.append(_attachment_block(item, index))
        content.append({"text": prompt})
        try:
            response = self._client.converse(
                modelId=self.model_id,
                system=[{"text": system}],
                messages=[{"role": "user", "content": content}],
                inferenceConfig={"maxTokens": max_tokens, "temperature": 0},
            )
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"bedrock converse failed ({type(exc).__name__})") from None
        try:
            blocks = response["output"]["message"]["content"]
            text = "".join(block.get("text", "") for block in blocks).strip()
        except (KeyError, TypeError, AttributeError):
            raise ProviderError("unexpected bedrock response shape") from None
        usage = response.get("usage") or {}
        return InferenceResult(
            text=text,
            provider=self.name,
            model_id=self.model_id,
            usage={k: int(v) for k, v in usage.items() if isinstance(v, int)},
        )


def _attachment_block(item: Attachment, index: int) -> dict[str, Any]:
    fmt = item.format.lower()
    if item.kind == "image":
        if fmt == "jpg":
            fmt = "jpeg"
        if fmt not in IMAGE_FORMATS:
            raise ProviderError(f"image format {fmt} is not supported by Bedrock")
        return {"image": {"format": fmt, "source": {"bytes": item.data}}}
    if fmt not in DOCUMENT_FORMATS:
        raise ProviderError(f"document format {fmt} is not supported by Bedrock")
    # Document names are model-visible; never forward the user's filename.
    return {"document": {"format": fmt, "name": f"source {index}", "source": {"bytes": item.data}}}


class BedrockEmbeddings:
    """Nova Multimodal Embeddings or Titan Text Embeddings v2."""

    name = "bedrock"

    def __init__(
        self,
        model_id: str | None = None,
        region: str | None = None,
        endpoint: str | None = None,
        dims: int | None = None,
        client: Any = None,
    ) -> None:
        self.model_id = (model_id or os.environ.get("GROUNDED_BEDROCK_EMBEDDING_MODEL") or "").strip()
        self.region = _region(region)
        self.endpoint = (endpoint if endpoint is not None else os.environ.get("GROUNDED_BEDROCK_ENDPOINT", "")).strip()
        self.dims = int(dims or os.environ.get("GROUNDED_EMBEDDING_DIMS") or 1024)
        if self.dims not in {256, 384, 512, 1024}:
            raise ProviderError("Bedrock embedding dims must be 256, 384, 512 or 1024")
        try:
            from_env().check_bedrock(self.model_id, self.region)
        except EgressError as exc:
            raise ProviderError(str(exc)) from exc
        self._client = _client("bedrock-runtime", self.region, self.endpoint, client)

    def _body(self, text: str) -> dict[str, Any]:
        if "nova" in self.model_id:
            return {
                "taskType": "SINGLE_EMBEDDING",
                "singleEmbeddingParams": {
                    "embeddingPurpose": "GENERIC_INDEX",
                    "embeddingDimension": self.dims,
                    "text": {"truncationMode": "END", "value": text},
                },
            }
        return {"inputText": text, "dimensions": self.dims, "normalize": True}

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            try:
                response = self._client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(self._body(text)),
                    contentType="application/json",
                    accept="application/json",
                )
                raw = response["body"].read() if hasattr(response["body"], "read") else response["body"]
                parsed = json.loads(raw)
            except Exception as exc:  # noqa: BLE001
                raise ProviderError(f"bedrock embedding failed ({type(exc).__name__})") from None
            if "embeddings" in parsed:
                vector = parsed["embeddings"][0]["embedding"]
            else:
                vector = parsed.get("embedding")
            if not isinstance(vector, list) or len(vector) != self.dims:
                raise ProviderError("bedrock embedding has an unexpected shape")
            vectors.append([float(value) for value in vector])
        return vectors


class BedrockImageText:
    """Verbatim screenshot text via a multimodal Nova model. Draft provenance."""

    name = "bedrock"

    _SYSTEM = (
        "You transcribe the visible text in one screenshot. Output only the text that is "
        "visibly written, in reading order, one block per paragraph, separated by blank lines. "
        "Do not describe, summarize, infer, translate, or add anything that is not written."
    )

    def __init__(self, inference: BedrockInference | None = None, client: Any = None) -> None:
        model = os.environ.get("GROUNDED_BEDROCK_MULTIMODAL_MODEL") or os.environ.get("GROUNDED_BEDROCK_TEXT_MODEL")
        self._inference = inference or BedrockInference(model_id=model, client=client)
        self.model_id = self._inference.model_id

    def extract_text(self, data: bytes, fmt: str) -> list[str]:
        result = self._inference.complete(
            self._SYSTEM,
            "Transcribe the visible text.",
            max_tokens=2048,
            attachments=(Attachment(kind="image", format=fmt, data=data),),
        )
        return [part.strip() for part in re.split(r"\n\s*\n", result.text) if part.strip()]
