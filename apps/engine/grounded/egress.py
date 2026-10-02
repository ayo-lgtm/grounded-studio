"""Egress policy.

Default mode is offline. Public generative APIs are never called.
A public object-store host is refused unless an operator explicitly
sets EGRESS_MODE=aws-in-region, and even then chat, TTS, and ASR stay local.
"""

from __future__ import annotations

import ipaddress
import os
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

# Hosts the offline profile may call. Everything else is public.
PRIVATE_SUFFIXES = (
    "railway.internal",
    "internal",
    "local",
)


class EgressError(Exception):
    pass


def mode() -> str:
    raw = (os.environ.get("EGRESS_MODE") or "offline").strip().lower()
    if raw in {"aws", "aws-in-region", "bedrock"}:
        return "aws-in-region"
    return "offline"


def offline() -> bool:
    return mode() == "offline"


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
        # Docker/Railway service names on the private network.
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
    """Refuse a public object store while the process is in offline mode."""
    if not offline():
        return
    host = host_of(endpoint)
    if is_public_host(host):
        raise EgressError(
            f"object store host {host or '(missing)'} is public; "
            "offline mode refuses it. Point MINIO_ENDPOINT at in-network MinIO."
        )


def assert_private_model(base_url: str) -> str:
    """Return a private model base URL, or raise. Empty is not configured."""
    url = (base_url or "").strip()
    if not url:
        raise EgressError("no private model endpoint configured")
    host = host_of(url)
    if not is_private_host(host) or is_public_host(host):
        raise EgressError(f"model host {host or '(missing)'} is not a private endpoint")
    return url.rstrip("/")


def object_store_label(endpoint: str) -> str:
    if is_public_host(host_of(endpoint)):
        return "public"
    return "private"


def health_report(db_ok: bool, object_endpoint: str) -> dict[str, object]:
    """Honest status. ok is false when the database is down or offline mode is blocked."""
    store = object_store_label(object_endpoint)
    if offline() and store == "public":
        egress = "blocked"
        ok = False
        store_label = "public-refused"
    elif offline():
        egress = "offline"
        ok = bool(db_ok)
        store_label = "private"
    else:
        egress = "aws-in-region"
        ok = bool(db_ok)
        store_label = store
    return {
        "ok": ok,
        "egress": egress,
        "chat": "retrieval",
        "narration": "local",
        "transcription": "local",
        "object_store": store_label,
    }
