"""Authentication and workspace authorization. Fail closed.

``AUTH_MODE`` selects exactly one mechanism:

``oidc``            Bearer JWT from the company IdP. Signature (RS256/ES256),
                    issuer, audience and expiry are verified against a JWKS
                    loaded from ``OIDC_JWKS_FILE`` or fetched once from an
                    *internal* ``OIDC_JWKS_URL`` (egress policy applies).
``trusted-header``  The company SSO reverse proxy authenticates and forwards
                    the identity in ``AUTH_USER_HEADER``; the proxy proves
                    itself with ``AUTH_PROXY_SECRET`` in ``X-Proxy-Secret``.
``dev``             Header-free single developer. Refused unless
                    ``GROUNDED_ENV=development`` *and* ``DEV_BYPASS_AUTH=true``.

Unset or unknown ``AUTH_MODE`` means every data endpoint answers 503. There
is no default identity in production.
"""

from __future__ import annotations

import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import get_db

MODES = ("oidc", "trusted-header", "dev")
ROLE_RANK = {"viewer": 0, "editor": 1, "owner": 2, "admin": 3}


class AuthConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Identity:
    sub: str
    email: str
    name: str


@dataclass(frozen=True)
class User:
    id: str
    sub: str
    email: str


def auth_mode(env: dict[str, str] | None = None) -> str:
    source = os.environ if env is None else env
    mode = (source.get("AUTH_MODE") or "").strip().lower()
    dev_bypass = (source.get("DEV_BYPASS_AUTH") or "").strip().lower() in {"1", "true", "yes"}
    development = (source.get("GROUNDED_ENV") or "").strip().lower() == "development"
    if dev_bypass and not development:
        raise AuthConfigError("DEV_BYPASS_AUTH=true is refused outside GROUNDED_ENV=development")
    if not mode and dev_bypass and development:
        mode = "dev"
    if mode == "dev" and not (dev_bypass and development):
        raise AuthConfigError("AUTH_MODE=dev requires GROUNDED_ENV=development and DEV_BYPASS_AUTH=true")
    if mode and mode not in MODES:
        raise AuthConfigError(f"unknown AUTH_MODE {mode!r}")
    return mode


_JWKS_CACHE: dict[str, Any] = {}


def _jwks() -> dict[str, Any]:
    if "keys" in _JWKS_CACHE:
        return _JWKS_CACHE
    path = (os.environ.get("OIDC_JWKS_FILE") or "").strip()
    if path:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    else:
        url = (os.environ.get("OIDC_JWKS_URL") or "").strip()
        if not url:
            raise AuthConfigError("AUTH_MODE=oidc needs OIDC_JWKS_FILE or an internal OIDC_JWKS_URL")
        from grounded.net import get_json

        data = get_json(url, label="OIDC_JWKS_URL")
    if not isinstance(data, dict) or not data.get("keys"):
        raise AuthConfigError("JWKS has no keys")
    _JWKS_CACHE.clear()
    _JWKS_CACHE.update(data)
    return _JWKS_CACHE


def verify_bearer(token: str) -> Identity:
    from jose import JWTError, jwt

    issuer = (os.environ.get("OIDC_ISSUER") or "").strip()
    audience = (os.environ.get("OIDC_AUDIENCE") or "").strip()
    if not issuer or not audience:
        raise AuthConfigError("AUTH_MODE=oidc needs OIDC_ISSUER and OIDC_AUDIENCE")
    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(401, "invalid token") from None
    if header.get("alg") not in {"RS256", "RS384", "RS512", "ES256", "ES384"}:
        raise HTTPException(401, "token algorithm is not allowed")
    keys = [key for key in _jwks()["keys"] if not header.get("kid") or key.get("kid") == header.get("kid")]
    if not keys:
        raise HTTPException(401, "unknown signing key")
    try:
        claims = jwt.decode(
            token,
            keys[0],
            algorithms=[header["alg"]],
            audience=audience,
            issuer=issuer,
            options={"require_exp": True, "require_sub": True, "verify_at_hash": False},
        )
    except JWTError:
        raise HTTPException(401, "invalid token") from None
    if int(claims.get("exp", 0)) < int(time.time()):
        raise HTTPException(401, "token expired")
    return Identity(
        sub=str(claims["sub"]),
        email=str(claims.get("email") or claims.get("upn") or claims["sub"]),
        name=str(claims.get("name") or claims.get("email") or claims["sub"]),
    )


def identity_from_request(request: Request) -> Identity:
    try:
        mode = auth_mode()
    except AuthConfigError:
        raise HTTPException(503, "authentication is misconfigured") from None
    if not mode:
        raise HTTPException(503, "authentication is not configured; set AUTH_MODE")
    if mode == "dev":
        email = os.environ.get("DEV_USER_EMAIL") or "dev@internal"
        return Identity(sub="dev", email=email, name="Dev User")
    if mode == "trusted-header":
        secret = os.environ.get("AUTH_PROXY_SECRET") or ""
        header = os.environ.get("AUTH_USER_HEADER") or "X-Authenticated-User"
        if len(secret) < 32:
            raise HTTPException(503, "AUTH_PROXY_SECRET must be at least 32 characters")
        offered = request.headers.get("x-proxy-secret") or ""
        if not hmac.compare_digest(offered.encode(), secret.encode()):
            raise HTTPException(401, "request did not come through the SSO proxy")
        user = (request.headers.get(header) or "").strip()
        if not user:
            raise HTTPException(401, "no authenticated user")
        return Identity(sub=f"proxy:{user}", email=user, name=user)
    authorization = request.headers.get("authorization") or ""
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "bearer token required")
    try:
        return verify_bearer(authorization.split(" ", 1)[1].strip())
    except AuthConfigError:
        raise HTTPException(503, "authentication is misconfigured") from None


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    identity = identity_from_request(request)
    row = db.execute(text("SELECT id FROM users WHERE idp_sub = :sub"), {"sub": identity.sub}).first()
    if row:
        return User(id=str(row[0]), sub=identity.sub, email=identity.email)
    user_id = str(uuid.uuid4())
    db.execute(
        text("INSERT INTO users (id, idp_sub, email, display_name) VALUES (:id, :sub, :email, :name)"),
        {"id": user_id, "sub": identity.sub, "email": identity.email, "name": identity.name},
    )
    db.commit()
    return User(id=user_id, sub=identity.sub, email=identity.email)


def role_in_workspace(db: Session, user: User, workspace_id: str) -> str | None:
    row = db.execute(
        text("SELECT role::text FROM workspace_members WHERE workspace_id = :ws AND user_id = :u"),
        {"ws": workspace_id, "u": user.id},
    ).first()
    return str(row[0]) if row else None


def authorize_briefing(db: Session, user: User, briefing_id: str, need: str = "viewer") -> None:
    """404 for briefings the user cannot see (no existence leak), 403 for low role."""
    try:
        uuid.UUID(str(briefing_id))
    except ValueError:
        raise HTTPException(404, "briefing not found") from None
    row = db.execute(
        text(
            """
            SELECT wm.role::text
            FROM briefings b
            JOIN projects p ON p.id = b.project_id
            LEFT JOIN workspace_members wm ON wm.workspace_id = p.workspace_id AND wm.user_id = :u
            WHERE b.id = :id
            """
        ),
        {"id": briefing_id, "u": user.id},
    ).first()
    if row is None or row[0] is None:
        raise HTTPException(404, "briefing not found")
    if ROLE_RANK.get(str(row[0]), -1) < ROLE_RANK[need]:
        raise HTTPException(403, f"{need} role required")


def audit(db: Session, user: User | None, action: str, entity_type: str, entity_id: str | None, **meta: Any) -> None:
    """Who did what, without content. Never store text, values or filenames."""
    safe = {k: v for k, v in meta.items() if isinstance(v, (int, float, bool)) or (isinstance(v, str) and len(v) <= 64)}
    db.execute(
        text(
            "INSERT INTO audit_events (id, actor_id, action, entity_type, entity_id, meta) "
            "VALUES (:id, :actor, :action, :etype, :eid, CAST(:meta AS jsonb))"
        ),
        {
            "id": str(uuid.uuid4()),
            "actor": user.id if user else None,
            "action": action,
            "etype": entity_type,
            "eid": entity_id,
            "meta": json.dumps(safe),
        },
    )
