"""Internal-only text generation client.

The endpoint must resolve to loopback/private/internal networking. Public hosts
are rejected by network_policy before any prompt is serialized.
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from .network_policy import EgressPolicyError, assert_internal_url


class LocalModelError(RuntimeError):
    pass


class LocalModel:
    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or os.environ.get("MODEL_BASE_URL") or "").rstrip("/")
        self.model = model or os.environ.get("MODEL_NAME") or "local-instruct"
        if not self.base_url:
            raise LocalModelError("MODEL_BASE_URL is not configured")
        try:
            assert_internal_url(self.base_url, "MODEL_BASE_URL")
        except EgressPolicyError as exc:
            raise LocalModelError(str(exc)) from exc

    def complete(self, system: str, prompt: str, max_tokens: int = 1024) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
                "max_tokens": max_tokens,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + "/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))
            return str(body["choices"][0]["message"]["content"]).strip()
        except Exception as exc:
            raise LocalModelError(f"internal model request failed: {exc}") from exc


def from_env() -> LocalModel:
    return LocalModel()
