"""The single guarded HTTP client for internal services.

Runtime code that needs to POST to an internal service (an OpenAI-compatible
model server on the company network, an internal IdP JWKS endpoint) goes
through :func:`post_json` / :func:`get_json`. The URL is checked against the
active policy before a socket is opened, redirects are refused (a private
server cannot bounce a prompt to a public host), and environment proxies are
ignored (a proxy would be an unvetted hop).

The privacy regression scan allows raw HTTP primitives only in this file.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .policy import EgressError, from_env


class NetError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any):  # noqa: D401
        raise NetError("redirects are refused for internal service calls")


def _opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


def _private_only(url: str, label: str) -> str:
    policy = from_env()
    checked = policy.check_url(url, label)
    from .policy import host_of

    if not policy.is_private_host(host_of(checked)):
        # Generic HTTP is for private infrastructure only. AWS services are
        # reached through their SDK provider, never through this client.
        raise EgressError(f"{label} must be private infrastructure for generic HTTP")
    return checked


def post_json(url: str, payload: dict[str, Any], *, headers: dict[str, str] | None = None,
              timeout: float = 60.0, label: str = "endpoint") -> dict[str, Any]:
    target = _private_only(url, label)
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        target,
        data=body,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with _opener().open(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError, OSError) as exc:
        raise NetError(f"{label} request failed ({type(exc).__name__})") from None


def get_json(url: str, *, timeout: float = 15.0, label: str = "endpoint") -> dict[str, Any]:
    target = _private_only(url, label)
    request = urllib.request.Request(target, method="GET")
    try:
        with _opener().open(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError, OSError) as exc:
        raise NetError(f"{label} request failed ({type(exc).__name__})") from None
