"""Startup network gate. Delegates to :mod:`grounded.policy`.

The retired public-egress switch is not honoured: setting it stops the
process (see :func:`grounded.policy.from_env`).
"""

from __future__ import annotations

from .policy import EgressError, assert_runtime, from_env

EgressPolicyError = EgressError


def assert_internal_url(url: str, label: str = "endpoint") -> str:
    if not url:
        return url
    return from_env().check_url(url, label)


def assert_private_runtime(*urls: tuple[str, str] | str) -> None:
    pairs = [item if isinstance(item, tuple) else ("endpoint", item) for item in urls]
    assert_runtime(*pairs)


def public_egress_disabled() -> bool:
    from_env()  # raises if the retired escape hatch is set
    return True
