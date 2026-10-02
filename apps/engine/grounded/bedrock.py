"""Claude via Amazon Bedrock.

The model drafts; the product enforces cite-or-cut. Callers must validate
any model output against retrieved sources before shipping it — a reply
that cannot cite does not ship.
"""

from __future__ import annotations

import os
from typing import Any, Protocol


class BedrockError(Exception):
    pass


class ConverseClient(Protocol):
    def converse(self, **kwargs: Any) -> dict[str, Any]: ...


DEFAULT_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"


class BedrockChat:
    """Thin wrapper over the Bedrock Converse API with an injectable client."""

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        region: str | None = None,
        client: ConverseClient | None = None,
    ) -> None:
        self.model_id = model_id
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self._client = client

    def _client_or_create(self) -> ConverseClient:
        if self._client is not None:
            return self._client
        raise BedrockError(
            "public Bedrock chat is disabled; answers stay on local retrieval"
        )

    def complete(self, system: str, prompt: str, max_tokens: int = 1024) -> str:
        try:
            response = self._client_or_create().converse(
                modelId=self.model_id,
                system=[{"text": system}],
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": max_tokens, "temperature": 0},
            )
        except BedrockError:
            raise
        except Exception as exc:
            raise BedrockError(f"bedrock converse failed: {exc}") from exc
        try:
            blocks = response["output"]["message"]["content"]
            return "".join(block.get("text", "") for block in blocks).strip()
        except (KeyError, TypeError, AttributeError) as exc:
            raise BedrockError(f"unexpected bedrock response shape: {exc}") from exc


def from_env(client: ConverseClient | None = None) -> BedrockChat:
    return BedrockChat(
        model_id=os.environ.get("CLAUDE_MODEL_ID", DEFAULT_MODEL_ID),
        region=os.environ.get("AWS_REGION"),
        client=client,
    )
