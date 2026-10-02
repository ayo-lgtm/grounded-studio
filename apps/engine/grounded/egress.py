"""Compatibility surface over :mod:`grounded.policy`.

Older modules import these helpers. Every decision is made by the active
deployment policy; nothing here can widen it.
"""

from __future__ import annotations

from .policy import EgressError, from_env, host_of

__all__ = [
    "EgressError",
    "assert_object_store",
    "assert_private_model",
    "health_report",
    "host_of",
    "is_private_host",
    "is_public_host",
    "mode",
    "object_store_label",
    "offline",
]


def mode() -> str:
    return from_env().mode


def offline() -> bool:
    return from_env().offline


def is_private_host(host: str) -> bool:
    return from_env().is_private_host(host)


def is_public_host(host: str) -> bool:
    return not from_env().is_private_host(host)


def assert_object_store(endpoint: str, bucket: str | None = None) -> None:
    from_env().check_object_store(endpoint, bucket)


def assert_private_model(base_url: str) -> str:
    """An OpenAI-compatible model server must be on private infrastructure."""
    url = (base_url or "").strip()
    if not url:
        raise EgressError("no private model endpoint configured")
    policy = from_env()
    host = host_of(url)
    if not policy.is_private_host(host):
        raise EgressError(f"model host {host or '(missing)'} is not private infrastructure")
    return url.rstrip("/")


def object_store_label(endpoint: str, bucket: str | None = None) -> str:
    return from_env().object_store_label(endpoint, bucket)


def health_report(db_ok: bool, object_endpoint: str, bucket: str | None = None) -> dict[str, object]:
    """Non-sensitive runtime posture. No hostnames, keys or content."""
    from .providers import registry

    try:
        policy = from_env()
    except EgressError:
        return {"ok": False, "egress": "misconfigured", "object_store": "unknown"}
    store = policy.object_store_label(object_endpoint, bucket)
    try:
        selection = registry.selection()
        providers = selection.describe()
        provider_ok = True
    except Exception:  # noqa: BLE001 - surfaced as not-ok, never as detail
        providers = {"inference": "misconfigured"}
        provider_ok = False
    ok = bool(db_ok) and store != "public-refused" and provider_ok
    return {
        "ok": ok,
        "egress": policy.mode if store != "public-refused" else "blocked",
        "deployment_mode": policy.mode,
        "chat": "retrieval" if providers.get("chat_phrasing") in {None, "none"} else "retrieval+validated-phrasing",
        "narration": providers.get("tts", "local"),
        "transcription": providers.get("transcription", "local"),
        "providers": providers,
        "object_store": store,
    }
