"""Process-wide socket egress guard.

Endpoint validation in the provider layer is the first line. This is the
second: once installed, every outbound TCP/UDP connect in the process is
checked against the active :class:`grounded.policy.Policy`, whichever
library opened the socket (boto3, httpx, urllib, a transitive dependency).

* Private, loopback and link-local addresses are allowed.
* A public address is allowed only if it was produced by resolving a
  hostname the policy approves (aws-private mode, approved AWS endpoint).
* Anything else raises :class:`EgressError` before the connection is made.

The guard is defence in depth. It does not replace the infrastructure-level
outbound deny (security groups, NetworkPolicy, internal Docker networks)
documented in ``docs/18-deployment-profiles.md``.
"""

from __future__ import annotations

import ipaddress
import socket
import threading
from typing import Any

from .policy import EgressError, Policy, from_env

_lock = threading.Lock()
_installed: dict[str, Any] = {}
_approved_ips: set[str] = set()
_policy: Policy | None = None


def installed() -> bool:
    return bool(_installed)


def install(policy: Policy | None = None) -> Policy:
    """Install (or refresh) the guard. Idempotent."""
    global _policy
    with _lock:
        _policy = policy or from_env()
        _approved_ips.clear()
        if _installed:
            return _policy
        _installed["connect"] = socket.socket.connect
        _installed["connect_ex"] = socket.socket.connect_ex
        _installed["getaddrinfo"] = socket.getaddrinfo
        _installed["sendto"] = socket.socket.sendto
        socket.socket.connect = _guarded_connect  # type: ignore[method-assign]
        socket.socket.connect_ex = _guarded_connect_ex  # type: ignore[method-assign]
        socket.socket.sendto = _guarded_sendto  # type: ignore[method-assign]
        socket.getaddrinfo = _guarded_getaddrinfo  # type: ignore[assignment]
        return _policy


def uninstall() -> None:
    with _lock:
        if not _installed:
            return
        socket.socket.connect = _installed.pop("connect")  # type: ignore[method-assign]
        socket.socket.connect_ex = _installed.pop("connect_ex")  # type: ignore[method-assign]
        socket.socket.sendto = _installed.pop("sendto")  # type: ignore[method-assign]
        socket.getaddrinfo = _installed.pop("getaddrinfo")  # type: ignore[assignment]
        _approved_ips.clear()


def _ip_allowed(address: Any) -> bool:
    if not isinstance(address, tuple) or not address:
        return True  # AF_UNIX path or unusual family: not network egress
    host = str(address[0])
    try:
        ip = ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        return False
    if ip.is_loopback or ip.is_link_local or (ip.is_private and not ip.is_multicast):
        return True
    return host in _approved_ips


def _check(sock: socket.socket, address: Any) -> None:
    if sock.family not in (socket.AF_INET, socket.AF_INET6):
        return
    if not _ip_allowed(address):
        raise EgressError(
            f"egress guard blocked a connection to {address[0]!s}; destination is outside the "
            f"{(_policy.mode if _policy else 'offline')} policy"
        )


def _guarded_connect(self: socket.socket, address: Any) -> None:
    _check(self, address)
    return _installed["connect"](self, address)


def _guarded_connect_ex(self: socket.socket, address: Any) -> int:
    _check(self, address)
    return _installed["connect_ex"](self, address)


def _guarded_sendto(self: socket.socket, data: Any, *args: Any) -> int:
    address = args[-1] if args else None
    _check(self, address)
    return _installed["sendto"](self, data, *args)


def _guarded_getaddrinfo(host: Any, *args: Any, **kwargs: Any):
    results = _installed["getaddrinfo"](host, *args, **kwargs)
    name = (host.decode() if isinstance(host, bytes) else str(host or "")).lower().rstrip(".")
    policy = _policy
    if policy is not None and name and policy.aws_destination(name) is not None:
        for *_rest, sockaddr in results:
            if sockaddr:
                _approved_ips.add(str(sockaddr[0]))
    return results
