"""Grounded Studio API. Every data endpoint is authenticated and authorized.

Startup validates the deployment policy, the provider selection, the auth
configuration and every infrastructure endpoint, then installs the socket
egress guard. Nothing is served if any of those is wrong.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import User, audit, auth_mode, authorize_briefing, current_user, role_in_workspace, ROLE_RANK
from .db import get_db, ping
from .queue import enqueue, new_id
from .ranges import content_type, parse_range
from .settings import settings
from .storage import HashingReader, delete_object, object_size, open_range, put_fileobj
from .validation import MAX_UPLOAD_BYTES, UploadTooLarge, is_allowed_kind, sanitize_filename

from grounded import guard, logsafe
from grounded.policy import assert_runtime
from grounded.providers import registry

POLICY = assert_runtime(
    ("DATABASE_URL", settings.database_url),
    ("REDIS_URL", settings.redis_url),
    ("MODEL_BASE_URL", settings.model_base_url),
)
SELECTION = registry.selection()
AUTH_MODE = auth_mode()
guard.install(POLICY)
logsafe.configure()

_ROOM = (Path(__file__).resolve().parent / "room.html").read_text(encoding="utf-8")

app = FastAPI(title="Grounded Studio", version="0.2.0", docs_url=None, redoc_url=None, openapi_url=None)

_LOCAL_DOCS = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Grounded API</title>
<style>
body { margin: 2rem; font-family: Georgia, serif; background: #f3f0e8; color: #1a1814; }
code { font-family: ui-monospace, monospace; }
</style></head>
<body>
<h1>Grounded API</h1>
<p>Offline reference. This page does not load a hosted API console. Every
<code>/api/v1</code> route requires company SSO.</p>
<ul>
<li><code>GET /health</code> deployment mode and posture</li>
<li><code>GET /api/v1/skills</code> on-disk skill catalog</li>
<li><code>POST /api/v1/briefings</code> create a briefing</li>
<li><code>POST /api/v1/briefings/{id}/assets</code> upload (xlsx, csv, docx, pdf, pptx, txt, md, png/jpg, mp4/mov/webm/mp3/wav, zip)</li>
<li><code>POST /api/v1/briefings/{id}/jobs</code> ingest, transcribe, compile, qa, render, index</li>
<li><code>GET /api/v1/briefings/{id}/script</code> latest script with persisted citations</li>
<li><code>GET /api/v1/briefings/{id}/sources</code> normalized cells, blocks, segments</li>
<li><code>POST /api/v1/briefings/{id}/chat</code> grounded chat (refuses what the sources do not say)</li>
<li><code>GET /api/v1/artifacts/{id}/file</code> watchable file</li>
</ul>
</body></html>
"""

_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["authorization", "content-type"],
        allow_credentials=False,
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; "
        "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; "
        "frame-ancestors 'self'",
    )
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


class BriefingIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    skill_id: str = "product-walkthrough"
    project_id: Optional[str] = None


class JobIn(BaseModel):
    type: str


class ChatIn(BaseModel):
    question: str = Field(max_length=2000)


class ShareIn(BaseModel):
    emails: list[str] = Field(default_factory=list, max_length=200)
    company: Optional[bool] = None


class MemberIn(BaseModel):
    email: str
    role: str = "viewer"


JOB_TYPES = {"ingest", "parse", "transcribe", "compile", "qa", "render", "index"}


@app.get("/health")
def health():
    from grounded.egress import health_report

    try:
        db_ok = ping()
    except Exception:  # noqa: BLE001
        db_ok = False
    report = health_report(db_ok, settings.minio_endpoint, settings.minio_bucket)
    report["auth"] = AUTH_MODE or "unconfigured"
    if not AUTH_MODE:
        report["ok"] = False
    return report


@app.get("/docs", include_in_schema=False)
def local_docs():
    return HTMLResponse(_LOCAL_DOCS, headers={"Cache-Control": "no-store"})


@app.get("/")
def room():
    return HTMLResponse(_ROOM, headers={"Cache-Control": "no-store"})


@app.get("/watch/{briefing_id}")
def watch(briefing_id: str):
    """The viewer page: same app, watch mode. Data still needs SSO + a grant."""
    return HTMLResponse(_ROOM, headers={"Cache-Control": "no-store"})


# ------------------------------------------------------------ workspaces

def _bootstrap_membership(db: Session, user: User) -> None:
    """First-run: listed admins (or the dev user) get the default workspace."""
    admins = {email.strip().lower() for email in settings.bootstrap_admins.split(",") if email.strip()}
    if AUTH_MODE != "dev" and user.email.lower() not in admins:
        return
    ws = db.execute(text("SELECT id FROM workspaces WHERE slug = 'internal'")).first()
    if ws is None:
        ws_id = str(uuid.uuid4())
        db.execute(text("INSERT INTO workspaces (id, name, slug) VALUES (:id, 'Internal', 'internal')"), {"id": ws_id})
        db.execute(
            text("INSERT INTO projects (id, workspace_id, name, created_by) VALUES (:id, :ws, 'Default', :u)"),
            {"id": str(uuid.uuid4()), "ws": ws_id, "u": user.id},
        )
    else:
        ws_id = str(ws[0])
    db.execute(
        text(
            "INSERT INTO workspace_members (workspace_id, user_id, role) VALUES (:ws, :u, 'admin') "
            "ON CONFLICT (workspace_id, user_id) DO NOTHING"
        ),
        {"ws": ws_id, "u": user.id},
    )
    db.commit()


def _member(db: Session = Depends(get_db), user: User = Depends(current_user)) -> User:
    _bootstrap_membership(db, user)
    return user


@app.get("/api/v1/me")
def me(db: Session = Depends(get_db), user: User = Depends(_member)):
    roles = db.execute(
        text("SELECT role::text FROM workspace_members WHERE user_id = :u"), {"u": user.id}
    ).scalars().all()
    rank = max((ROLE_RANK.get(role, -1) for role in roles), default=-1)
    best = next((name for name, value in ROLE_RANK.items() if value == rank), None)
    return {"email": user.email, "role": best, "auth": AUTH_MODE}


@app.get("/api/v1/projects")
def list_projects(db: Session = Depends(get_db), user: User = Depends(_member)):
    rows = db.execute(
        text(
            """
            SELECT p.id, p.name, p.workspace_id, wm.role::text AS role
            FROM projects p JOIN workspace_members wm ON wm.workspace_id = p.workspace_id
            WHERE wm.user_id = :u ORDER BY p.created_at
            """
        ),
        {"u": user.id},
    ).mappings().all()
    return {"projects": [_public_row(row) for row in rows]}


@app.post("/api/v1/workspaces/{workspace_id}/members")
def add_member(workspace_id: str, body: MemberIn, db: Session = Depends(get_db), user: User = Depends(_member)):
    if role_in_workspace(db, user, workspace_id) not in {"admin", "owner"}:
        raise HTTPException(403, "admin role required")
    if body.role not in ROLE_RANK:
        raise HTTPException(400, "unknown role")
    target = db.execute(text("SELECT id FROM users WHERE lower(email) = lower(:e)"), {"e": body.email}).first()
    if target is None:
        raise HTTPException(404, "user has not signed in yet")
    db.execute(
        text(
            "INSERT INTO workspace_members (workspace_id, user_id, role) VALUES (:ws, :u, CAST(:r AS workspace_role)) "
            "ON CONFLICT (workspace_id, user_id) DO UPDATE SET role = EXCLUDED.role"
        ),
        {"ws": workspace_id, "u": str(target[0]), "r": body.role},
    )
    audit(db, user, "member.set", "workspace", workspace_id, role=body.role)
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------ briefings

@app.post("/api/v1/briefings")
def create_briefing(body: BriefingIn, db: Session = Depends(get_db), user: User = Depends(_member)):
    from grounded.skill_registry import SkillRegistryError, resolve_skill

    try:
        contract, _crafts = resolve_skill(body.skill_id)
    except SkillRegistryError as exc:
        raise HTTPException(400, str(exc)) from exc
    project_id = body.project_id or _default_project(db, user)
    project = db.execute(text("SELECT workspace_id FROM projects WHERE id = :id"), {"id": project_id}).first()
    if project is None or ROLE_RANK.get(role_in_workspace(db, user, str(project[0])) or "", -1) < ROLE_RANK["editor"]:
        raise HTTPException(404, "project not found")
    briefing_id = new_id()
    db.execute(
        text(
            """
            INSERT INTO briefings
              (id, project_id, title, state, skill_id, skill_version, language, created_by)
            VALUES
              (:id, :project_id, :title, 'draft', :skill_id, :skill_version, 'en', :user_id)
            """
        ),
        {
            "id": briefing_id,
            "project_id": project_id,
            "title": body.title,
            "skill_id": body.skill_id,
            "skill_version": contract.version,
            "user_id": user.id,
        },
    )
    audit(db, user, "briefing.create", "briefing", briefing_id, skill_id=body.skill_id)
    db.commit()
    return {"id": briefing_id, "state": "draft", "skill_id": body.skill_id, "skill_version": contract.version}


def _default_project(db: Session, user: User) -> str:
    row = db.execute(
        text(
            """
            SELECT p.id FROM projects p JOIN workspace_members wm ON wm.workspace_id = p.workspace_id
            WHERE wm.user_id = :u AND wm.role IN ('admin', 'owner', 'editor')
            ORDER BY p.created_at LIMIT 1
            """
        ),
        {"u": user.id},
    ).first()
    if row is None:
        raise HTTPException(403, "no project you can edit; ask a workspace admin")
    return str(row[0])


@app.get("/api/v1/briefings")
def list_briefings(db: Session = Depends(get_db), user: User = Depends(_member)):
    rows = db.execute(
        text(
            """
            SELECT b.id, b.title, b.state, b.skill_id, b.skill_version, b.created_at, false AS shared
            FROM briefings b
            JOIN projects p ON p.id = b.project_id
            JOIN workspace_members wm ON wm.workspace_id = p.workspace_id AND wm.user_id = :u
            UNION
            SELECT b.id, b.title, b.state, b.skill_id, b.skill_version, b.created_at, true AS shared
            FROM briefings b JOIN briefing_grants g ON g.briefing_id = b.id
            WHERE g.email = lower(:email)
              AND NOT EXISTS (
                SELECT 1 FROM projects p JOIN workspace_members wm ON wm.workspace_id = p.workspace_id
                WHERE p.id = b.project_id AND wm.user_id = :u)
            ORDER BY created_at DESC
            LIMIT 80
            """
        ),
        {"u": user.id, "email": user.email},
    ).mappings().all()
    return {"briefings": [_public_row(row) for row in rows]}


@app.get("/api/v1/briefings/{briefing_id}")
def get_briefing(briefing_id: str, db: Session = Depends(get_db), user: User = Depends(_member)):
    role = authorize_briefing(db, user, briefing_id)
    row = db.execute(
        text("SELECT id, title, state, skill_id, skill_version, language, visibility FROM briefings WHERE id = :id"),
        {"id": briefing_id},
    ).mappings().first()
    assets = db.execute(
        text(
            "SELECT id, kind::text AS kind, filename, mime, bytes, sha256, detected_format, parent_asset_id, "
            "duration_ms, normalized_at FROM source_assets WHERE briefing_id = :id ORDER BY created_at"
        ),
        {"id": briefing_id},
    ).mappings().all()
    member = role_in_workspace_of(db, user, briefing_id) is not None
    return {**_public_row(row), "role": role, "member": member, "assets": [_public_row(a) for a in assets]}


@app.post("/api/v1/briefings/{briefing_id}/assets")
async def upload_asset(
    briefing_id: str,
    request: Request,
    kind: str = Form("attachment"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(_member),
):
    authorize_briefing(db, user, briefing_id, need="editor")
    if not is_allowed_kind(kind):
        raise HTTPException(400, f"unknown asset kind {kind}")
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_UPLOAD_BYTES + 1024 * 1024:
        raise HTTPException(413, f"asset exceeds {MAX_UPLOAD_BYTES} bytes")
    asset_id = new_id()
    safe_name = sanitize_filename(file.filename)
    key = f"briefings/{briefing_id}/{asset_id}/{safe_name}"
    mime = file.content_type or "application/octet-stream"
    reader = HashingReader(file.file)
    try:
        put_fileobj(key, reader, mime)
    except UploadTooLarge as exc:
        delete_object(key)
        raise HTTPException(413, str(exc)) from None
    try:
        from grounded.sources import SourceError, detect

        detected = detect(safe_name, reader.head)
    except SourceError as exc:
        delete_object(key)
        raise HTTPException(415, "; ".join(exc.errors)) from None
    # The declared kind is a hint; the stored kind is what the bytes are.
    stored_kind = detected.kind
    db.execute(
        text(
            """
            INSERT INTO source_assets
              (id, briefing_id, kind, filename, mime, bytes, sha256, minio_key, detected_format)
            VALUES
              (:id, :briefing_id, CAST(:kind AS asset_kind), :filename, :mime, :bytes, :sha256, :key, :fmt)
            """
        ),
        {
            "id": asset_id,
            "briefing_id": briefing_id,
            "kind": stored_kind,
            "filename": safe_name,
            "mime": mime,
            "bytes": reader.size,
            "sha256": reader.sha256,
            "key": key,
            "fmt": detected.format,
        },
    )
    audit(db, user, "asset.upload", "source_asset", asset_id, bytes=reader.size, kind=stored_kind)
    db.commit()
    logsafe.log_event("asset.upload", briefing_id=briefing_id, asset_id=asset_id, bytes=reader.size, asset_kind=stored_kind)
    return {"id": asset_id, "sha256": reader.sha256, "bytes": reader.size, "kind": stored_kind, "format": detected.format}


@app.post("/api/v1/briefings/{briefing_id}/jobs")
def start_job(briefing_id: str, body: JobIn, db: Session = Depends(get_db), user: User = Depends(_member)):
    authorize_briefing(db, user, briefing_id, need="editor")
    if body.type not in JOB_TYPES:
        raise HTTPException(400, f"unknown job type {body.type}")
    job_id = new_id()
    db.execute(
        text(
            """
            INSERT INTO jobs (id, briefing_id, type, state, model_ids)
            VALUES (:id, :briefing_id, CAST(:type AS job_type), 'queued', '{}'::jsonb)
            """
        ),
        {"id": job_id, "briefing_id": briefing_id, "type": body.type},
    )
    audit(db, user, "job.start", "job", job_id, type=body.type)
    db.commit()
    enqueue(job_id, body.type, briefing_id)
    return {"id": job_id, "type": body.type, "state": "queued"}


@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db), user: User = Depends(_member)):
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(404, "job not found") from None
    row = db.execute(
        text("SELECT id, briefing_id, type::text AS type, state::text AS state, error, model_ids FROM jobs WHERE id = :id"),
        {"id": job_id},
    ).mappings().first()
    if not row:
        raise HTTPException(404, "job not found")
    authorize_briefing(db, user, str(row["briefing_id"]))
    return _public_row(row)


@app.get("/api/v1/briefings/{briefing_id}/script")
def get_script(briefing_id: str, db: Session = Depends(get_db), user: User = Depends(_member)):
    authorize_briefing(db, user, briefing_id)
    row = db.execute(
        text(
            """
            SELECT id, version, accepted, raw_json, skill_id, skill_version, provenance, providers
            FROM script_versions
            WHERE briefing_id = :id
            ORDER BY version DESC
            LIMIT 1
            """
        ),
        {"id": briefing_id},
    ).mappings().first()
    if not row:
        raise HTTPException(404, "no script yet")
    citations = db.execute(
        text(
            """
            SELECT sb.ord, c.id, c.kind::text AS kind, c.asset_id, c.sheet, c.addr, c.block_id, c.page,
                   c.t_start_ms, c.t_end_ms
            FROM script_beats sb JOIN citations c ON c.beat_id = sb.id
            WHERE sb.script_id = :sid ORDER BY sb.ord
            """
        ),
        {"sid": row["id"]},
    ).mappings().all()
    return {**_public_row(row), "citations": [_public_row(c) for c in citations]}


@app.post("/api/v1/briefings/{briefing_id}/script/accept")
def accept_script(briefing_id: str, db: Session = Depends(get_db), user: User = Depends(_member)):
    authorize_briefing(db, user, briefing_id, need="editor")
    result = db.execute(
        text(
            """
            UPDATE script_versions
            SET accepted = true, accepted_by = :u
            WHERE briefing_id = :id
              AND version = (
                SELECT MAX(version) FROM script_versions WHERE briefing_id = :id
              )
            """
        ),
        {"id": briefing_id, "u": user.id},
    )
    if result.rowcount == 0:
        raise HTTPException(404, "no script to accept")
    db.execute(text("UPDATE briefings SET state = 'review' WHERE id = :id"), {"id": briefing_id})
    audit(db, user, "script.accept", "briefing", briefing_id)
    db.commit()
    return {"accepted": True}


@app.get("/api/v1/briefings/{briefing_id}/share")
def get_share(briefing_id: str, db: Session = Depends(get_db), user: User = Depends(_member)):
    authorize_briefing(db, user, briefing_id, need="editor")
    vis = db.execute(text("SELECT visibility FROM briefings WHERE id = :id"), {"id": briefing_id}).scalar_one()
    rows = db.execute(
        text("SELECT email, role, created_at FROM briefing_grants WHERE briefing_id = :id ORDER BY created_at"),
        {"id": briefing_id},
    ).mappings().all()
    return {"company": vis == "company", "people": [_public_row(r) for r in rows], "watch_path": f"/watch/{briefing_id}"}


_EMAIL = re.compile(r"[^@\s<>\"']+@[^@\s<>\"']+\.[^@\s<>\"']+")


@app.post("/api/v1/briefings/{briefing_id}/share")
def set_share(briefing_id: str, body: ShareIn, db: Session = Depends(get_db), user: User = Depends(_member)):
    """Let people watch and ask, without editing. Always behind company SSO."""
    authorize_briefing(db, user, briefing_id, need="editor")
    if len(body.emails) > 500:
        raise HTTPException(400, "share with at most 500 people at a time")
    added = 0
    for raw in body.emails:
        email = raw.strip().lower()
        if len(email) > 254 or not _EMAIL.fullmatch(email):
            raise HTTPException(400, "each share must be an email address")
        db.execute(
            text(
                "INSERT INTO briefing_grants (briefing_id, email, role, granted_by) VALUES (:b, :e, 'viewer', :u) "
                "ON CONFLICT (briefing_id, email) DO NOTHING"
            ),
            {"b": briefing_id, "e": email, "u": user.id},
        )
        added += 1
    if body.company is not None:
        db.execute(
            text("UPDATE briefings SET visibility = :v WHERE id = :id"),
            {"v": "company" if body.company else "workspace", "id": briefing_id},
        )
    audit(db, user, "briefing.share", "briefing", briefing_id, people=added, company=bool(body.company))
    db.commit()
    return get_share(briefing_id, db, user)


@app.delete("/api/v1/briefings/{briefing_id}/share/{email}")
def remove_share(briefing_id: str, email: str, db: Session = Depends(get_db), user: User = Depends(_member)):
    authorize_briefing(db, user, briefing_id, need="editor")
    db.execute(text("DELETE FROM briefing_grants WHERE briefing_id = :b AND email = lower(:e)"), {"b": briefing_id, "e": email})
    audit(db, user, "briefing.unshare", "briefing", briefing_id)
    db.commit()
    return {"ok": True}


@app.get("/api/v1/briefings/{briefing_id}/sources")
def list_sources(briefing_id: str, db: Session = Depends(get_db), user: User = Depends(_member)):
    """Normalized source rows so every citation can be audited."""
    authorize_briefing(db, user, briefing_id)
    cells = db.execute(
        text(
            "SELECT wc.asset_id, wc.sheet, wc.addr, wc.value_num, wc.value_text, wc.formula "
            "FROM workbook_cells wc JOIN source_assets sa ON sa.id = wc.asset_id "
            "WHERE sa.briefing_id = :id ORDER BY wc.sheet, wc.addr LIMIT 5000"
        ),
        {"id": briefing_id},
    ).mappings().all()
    blocks = db.execute(
        text(
            "SELECT db.asset_id, db.block_id, db.page, db.heading_path, db.text, db.extractor "
            "FROM document_blocks db JOIN source_assets sa ON sa.id = db.asset_id "
            "WHERE sa.briefing_id = :id ORDER BY db.asset_id, db.ord LIMIT 5000"
        ),
        {"id": briefing_id},
    ).mappings().all()
    segments = db.execute(
        text(
            "SELECT ts.asset_id, ts.t_start_ms, ts.t_end_ms, ts.text "
            "FROM transcript_segments ts JOIN source_assets sa ON sa.id = ts.asset_id "
            "WHERE sa.briefing_id = :id ORDER BY ts.t_start_ms LIMIT 5000"
        ),
        {"id": briefing_id},
    ).mappings().all()
    return {
        "cells": [_public_row(r) for r in cells],
        "blocks": [_public_row(r) for r in blocks],
        "segments": [_public_row(r) for r in segments],
    }


def _asset_key(db: Session, user: User, table: str, object_id: str) -> str:
    try:
        uuid.UUID(object_id)
    except ValueError:
        raise HTTPException(404, "not found") from None
    row = db.execute(
        text(f"SELECT minio_key, briefing_id FROM {table} WHERE id = :id"),  # table is a literal below
        {"id": object_id},
    ).first()
    if not row:
        raise HTTPException(404, "not found")
    authorize_briefing(db, user, str(row[1]))
    return str(row[0])


@app.get("/api/v1/assets/{asset_id}/content")
def asset_content(asset_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(_member)):
    key = _asset_key(db, user, "source_assets", asset_id)
    owner = db.execute(text("SELECT briefing_id FROM source_assets WHERE id = :id"), {"id": asset_id}).scalar_one()
    if role_in_workspace_of(db, user, str(owner)) is None:
        raise HTTPException(403, "shared viewers can watch and ask, not download raw sources")
    audit(db, user, "asset.read", "source_asset", asset_id)
    db.commit()
    return _stream(key, request, disposition="attachment")


@app.get("/api/v1/briefings/{briefing_id}/artifacts")
def list_artifacts(briefing_id: str, db: Session = Depends(get_db), user: User = Depends(_member)):
    authorize_briefing(db, user, briefing_id)
    rows = db.execute(
        text(
            "SELECT id, kind, bytes, sha256, created_at FROM artifacts "
            "WHERE briefing_id = :id ORDER BY created_at"
        ),
        {"id": briefing_id},
    ).mappings().all()
    return {"artifacts": [_public_row(row) for row in rows]}


@app.get("/api/v1/artifacts/{artifact_id}/content")
def artifact_content(artifact_id: str, db: Session = Depends(get_db), user: User = Depends(_member)):
    _asset_key(db, user, "artifacts", artifact_id)
    return {"url": f"/api/v1/artifacts/{artifact_id}/file"}


@app.get("/api/v1/artifacts/{artifact_id}/file")
def artifact_file(artifact_id: str, request: Request, db: Session = Depends(get_db), user: User = Depends(_member)):
    """Stream an artifact from this origin so the film can seek and the deck can be framed."""
    key = _asset_key(db, user, "artifacts", artifact_id)
    return _stream(key, request, disposition="inline")


def _stream(key: str, request: Request, disposition: str) -> Response:
    try:
        size = object_size(key)
    except FileNotFoundError:
        raise HTTPException(404, "object missing") from None
    try:
        span = parse_range(request.headers.get("range"), size)
    except ValueError:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{size}", "Accept-Ranges": "bytes"})
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": content_type(key),
        "Content-Disposition": disposition,
        "Cache-Control": "private, no-store",
    }
    if span is None:
        body = open_range(key)
        headers["Content-Length"] = str(size)
        status = 200
    else:
        start, end = span
        body = open_range(key, start, end)
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        headers["Content-Length"] = str(end - start + 1)
        status = 206

    def chunks():
        try:
            for chunk in iter(lambda: body.read(1024 * 1024), b""):
                yield chunk
        finally:
            close = getattr(body, "close", None)
            if close:
                close()

    return StreamingResponse(chunks(), status_code=status, headers=headers)


@app.get("/api/v1/skills")
def list_skills(user: User = Depends(_member)):
    from grounded.catalog import CatalogError, load_catalog, load_crafts

    try:
        skills = load_catalog()
        crafts = load_crafts()
    except CatalogError as exc:
        raise HTTPException(500, str(exc)) from exc
    return {"offline": POLICY.offline, "deployment_mode": POLICY.mode, "skills": skills, "crafts": crafts}


@app.post("/api/v1/help/chat")
def help_chat(body: ChatIn, user: User = Depends(_member)):
    from grounded.chat import answer_help

    question = (body.question or "").strip()
    if not question:
        raise HTTPException(400, "question is required")
    return answer_help(question)


@app.post("/api/v1/briefings/{briefing_id}/chat")
def briefing_chat(briefing_id: str, body: ChatIn, db: Session = Depends(get_db), user: User = Depends(_member)):
    from grounded.chat import answer_grounded

    authorize_briefing(db, user, briefing_id)
    question = (body.question or "").strip()
    if not question:
        raise HTTPException(400, "question is required")
    row = db.execute(
        text(
            """
            SELECT raw_json FROM script_versions
            WHERE briefing_id = :id
            ORDER BY version DESC LIMIT 1
            """
        ),
        {"id": briefing_id},
    ).first()
    raw = {"beats": []}
    if row:
        raw = row[0] if isinstance(row[0], dict) else json.loads(row[0])
    result = answer_grounded(raw, question, briefing_id=briefing_id, db=db)
    _record_chat(db, user, briefing_id, question, result)
    return result


def _record_chat(db: Session, user: User, briefing_id: str, question: str, result: dict) -> None:
    session = db.execute(
        text("SELECT id FROM chat_sessions WHERE briefing_id = :b AND user_id = :u ORDER BY created_at DESC LIMIT 1"),
        {"b": briefing_id, "u": user.id},
    ).first()
    session_id = str(session[0]) if session else str(uuid.uuid4())
    if not session:
        db.execute(
            text("INSERT INTO chat_sessions (id, briefing_id, user_id) VALUES (:id, :b, :u)"),
            {"id": session_id, "b": briefing_id, "u": user.id},
        )
    for role, message, cites, provider in (
        ("user", question, [], None),
        ("assistant", result["text"], result.get("citations") or [], result.get("provider")),
    ):
        db.execute(
            text(
                "INSERT INTO chat_messages (id, session_id, role, text, citations, provider) "
                "VALUES (:id, :s, :role, :text, CAST(:cites AS jsonb), :provider)"
            ),
            {"id": str(uuid.uuid4()), "s": session_id, "role": role, "text": message, "cites": json.dumps(cites), "provider": provider},
        )
    db.commit()


def role_in_workspace_of(db: Session, user: User, briefing_id: str) -> str | None:
    row = db.execute(
        text(
            "SELECT wm.role::text FROM briefings b JOIN projects p ON p.id = b.project_id "
            "JOIN workspace_members wm ON wm.workspace_id = p.workspace_id AND wm.user_id = :u WHERE b.id = :id"
        ),
        {"u": user.id, "id": briefing_id},
    ).first()
    return str(row[0]) if row else None


def _public_row(row) -> dict:
    item = {}
    for key, value in dict(row).items():
        if isinstance(value, uuid.UUID):
            item[key] = str(value)
        elif hasattr(value, "isoformat"):
            item[key] = value.isoformat()
        else:
            item[key] = value
    return item


if os.environ.get("GROUNDED_PRINT_POSTURE") == "1":  # pragma: no cover - operator aid
    print(json.dumps({"mode": POLICY.mode, "auth": AUTH_MODE, "providers": SELECTION.describe()}))
