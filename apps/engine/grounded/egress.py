"""Fail-closed egress policy for Grounded Studio.

There is no cloud/provider escape hatch. Runtime data may reach only loopback,
private RFC1918/link-local addresses, Docker/Kubernetes service names, or
explicit internal suffixes. Public object stores and managed AI services are
always refused.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

PUBLIC_SUFFIXES = (
    "storageapi.dev",
    "amazonaws.com",
    "tigris.dev",
    "r2.cloudflarestorage.com",
    "storage.googleapis.com",
    "blob.core.windows.net",
    "railway.app",
    "openai.com",
    "anthropic.com",
    "elevenlabs.io",
    "jsdelivr.net",
    "huggingface.co",
    "scenario.com",
    "runwayml.com",
    "heygen.com",
    "slides.com",
    "googleapis.com",
)

PRIVATE_SUFFIXES = ("internal", "local", "corp")


class EgressError(Exception):
    pass


def mode() -> str:
    return "offline"


def offline() -> bool:
    return True


def host_of(endpoint: str) -> str:
    text = (endpoint or "").strip()
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"http://{text}")
    return (parsed.hostname or "").lower().rstrip(".")


def is_private_host(host: str) -> bool:
    name = (host or "").lower().rstrip(".")
    if not name:
        return False
    if name in {"localhost", "minio", "postgres", "redis", "pgvector", "ollama", "vllm"}:
        return True
    if "." not in name:
        return True
    if any(name == suffix or name.endswith("." + suffix) for suffix in PRIVATE_SUFFIXES):
        return True
    try:
        ip = ipaddress.ip_address(name)
    except ValueError:
        return False
    return bool(ip.is_private or ip.is_loopback or ip.is_link_local)


def is_public_host(host: str) -> bool:
    name = (host or "").lower().rstrip(".")
    if not name:
        return True
    if any(name == suffix or name.endswith("." + suffix) for suffix in PUBLIC_SUFFIXES):
        return True
    return not is_private_host(name)


def assert_object_store(endpoint: str) -> None:
    host = host_of(endpoint)
    if is_public_host(host):
        raise EgressError(
            f"object store host {host or '(missing)'} is external; "
            "Grounded Studio requires in-network MinIO/object storage"
        )


def assert_private_model(base_url: str) -> str:
    url = (base_url or "").strip()
    if not url:
        raise EgressError("no private model endpoint configured")
    host = host_of(url)
    if not is_private_host(host) or is_public_host(host):
        raise EgressError(f"model host {host or '(missing)'} is external")
    return url.rstrip("/")


def object_store_label(endpoint: str) -> str:
    return "private" if is_private_host(host_of(endpoint)) else "public-refused"


def health_report(db_ok: bool, object_endpoint: str) -> dict[str, object]:
    store = object_store_label(object_endpoint)
    ok = bool(db_ok) and store == "private"
    return {
        "ok": ok,
        "egress": "offline",
        "chat": "retrieval",
        "narration": "local",
        "transcription": "local",
        "object_store": store,
    }
