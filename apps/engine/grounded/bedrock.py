"""Compatibility guard for the retired Bedrock path.

Cloud LLM egress is prohibited in Grounded Studio private mode. Importers that
still reference this module fail closed before any network client is created.
"""

from __future__ import annotations


class BedrockError(RuntimeError):
    pass


class BedrockChat:
    def __init__(self, *args, **kwargs) -> None:
        raise BedrockError(
            "Amazon Bedrock is disabled. Use grounded.local_model with an internal-only endpoint."
        )


def from_env(*args, **kwargs):
    raise BedrockError(
        "Amazon Bedrock is disabled. Use grounded.local_model with an internal-only endpoint."
    )
