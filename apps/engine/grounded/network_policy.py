"""Fail-closed network policy for Grounded Studio private mode.

Grounded Studio may talk only to loopback, RFC1918/link-local hosts, Docker/
cluster service names, and explicit internal suffixes. Public internet hosts are
rejected before any document, workbook, transcript, or prompt can be sent.
"""

from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse


class EgressPolicyError(RuntimeError):
    pass


_ALLOWED_SUFFIXES = tuple(
    part.strip().lower()
    for part in os.environ.get("GROUND_INTERNAL_SUFFIXES", ".internal,.local,.corp").split(",")
    if part.strip()
)


def assert_internal_url(url: str, label: str = "endpoint") -> str:
    if not url:
        return url
    parsed = urlparse(url if "://" in url else f"//{url}")
    host = (parsed.hostname or "").strip().lower()
    if not host:
        raise EgressPolicyError(f"{label} has no hostname")
    if _host_is_internal(host):
        return url
    raise EgressPolicyError(f"{label} points to public/external host {host!r}; private mode blocks egress")


def assert_private_runtime(*urls: tuple[str, str] | str) -> None:
    if public_egress_disabled():
        external_hosts = [
            name
            for name in ("RAILWAY_ENVIRONMENT", "RAILWAY_PROJECT_ID", "VERCEL", "RENDER", "FLY_APP_NAME")
            if os.environ.get(name)
        ]
        if external_hosts:
            raise EgressPolicyError(
                "private mode refuses third-party hosted runtime: " + ", ".join(external_hosts)
            )
    for item in urls:
        if isinstance(item, tuple):
            label, url = item
        else:
            label, url = "endpoint", item
        if url:
            assert_internal_url(url, label)


def public_egress_disabled() -> bool:
    value = os.environ.get("GROUND_ALLOW_PUBLIC_EGRESS", "").strip().lower()
    return value not in {"1", "true", "yes"}


def _host_is_internal(host: str) -> bool:
    if host in {"localhost", "host.docker.internal"}:
        return True
    if "." not in host:
        # Docker/Kubernetes service name, e.g. postgres, redis, minio, ollama.
        return True
    if any(host.endswith(suffix) for suffix in _ALLOWED_SUFFIXES):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return bool(ip.is_private or ip.is_loopback or ip.is_link_local)
    except ValueError:
        pass

    # DNS names can resolve to internal IPs. Resolution failure is fail-closed.
    try:
        answers = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except OSError:
        return False
    if not answers:
        return False
    try:
        return all(
            ipaddress.ip_address(addr).is_private
            or ipaddress.ip_address(addr).is_loopback
            or ipaddress.ip_address(addr).is_link_local
            for addr in answers
        )
    except ValueError:
        return False
