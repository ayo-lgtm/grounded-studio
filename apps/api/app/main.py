"""Phase 1 API. Dev auth is a header bypass. Wire SSO before any real data lands."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import get_db, ping
from .queue import enqueue, new_id
from .ranges import content_type, slice_body
from .settings import settings
from .storage import put_fileobj, read_bytes, signed_url
from .validation import UploadTooLarge, hash_limited, is_allowed_kind, sanitize_filename
from grounded.network_policy import assert_private_runtime

_ROOM = (Path(__file__).resolve().parent / "room.html").read_text(encoding="utf-8")

assert_private_runtime(
    ("DATABASE_URL", settings.database_url),
    ("REDIS_URL", settings.redis_url),
    ("MINIO_ENDPOINT", settings.minio_endpoint),
    ("MODEL_BASE_URL", settings.model_base_url),
)


def _require_dev_auth() -> None:
    if not settings.dev_bypass_auth:
        raise HTTPException(501, "SSO auth is not wired yet")

app = FastAPI(
    title="Grounded Studio",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

_LOCAL_DOCS = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Grounded API</title>
<style>
body { margin: 2rem; font-family: Georgia, serif; background: #f3f0e8; color: #1a1814; }
code { font-family: ui-monospace, monospace; }
</style></head>
<body>
<h1>Grounded API</h1>
<p>Offline reference. This page does not load a hosted API console.</p>
<ul>
<li><code>GET /health</code> egress mode</li>
<li><code>GET /api/v1/skills</code> on-disk skill catalog</li>
<li><code>POST /api/v1/briefings</code> create a briefing</li>
<li><code>POST /api/v1/briefings/{id}/assets</code> upload</li>
<li><code>POST /api/v1/briefings/{id}/jobs</code> transcribe, compile, render, index</li>
<li><code>GET /api/v1/briefings/{id}/script</code></li>
<li><code>POST /api/v1/briefings/{id}/chat</code> local retrieval</li>
<li><code>POST /api/v1/help/chat</code> how to use the tool</li>
<li><code>GET /api/v1/artifacts/{id}/file</code> watchable file</li>
</ul>
</body></html>
"""
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class BriefingIn(BaseModel):
    title: str
    skill_id: str = "product-walkthrough"
    project_id: Optional[str] = None


class JobIn(BaseModel):
    type: str


class ChatIn(BaseModel):
    question: str


@app.get("/health")
def health():
    from grounded.egress import health_report

    return health_report(ping(), settings.minio_endpoint)


@app.get("/docs", include_in_schema=False)
def local_docs():
    return HTMLResponse(_LOCAL_DOCS, headers={"Cache-Control": "no-store"})


@app.get("/")
def room():
    return HTMLResponse(_ROOM, headers={"Cache-Control": "no-store"})


@app.post("/api/v1/briefings")
def create_briefing(body: BriefingIn, db: Session = Depends(get_db)):
    _require_dev_auth()
    from grounded.skill_registry import SkillRegistryError, resolve_skill
    try:
        contract, _crafts = resolve_skill(body.skill_id)
    except SkillRegistryError as exc:
        raise HTTPException(400, str(exc)) from exc
    briefing_id = new_id()
    project_id = body.project_id or _ensure_dev_project(db)
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
            "user_id": _dev_user(db),
        },
    )
    db.commit()
    return {"id": briefing_id, "state": "draft", "skill_id": body.skill_id, "skill_version": contract.version}


@app.get("/api/v1/briefings")
def list_briefings(db: Session = Depends(get_db)):
    _require_dev_auth()
    rows = db.execute(
        text(
            """
            SELECT id, title, state, skill_id, created_at
            FROM briefings
            ORDER BY created_at DESC
            LIMIT 20
            """
        )
    ).mappings().all()
    return {"briefings": [_public_row(row) for row in rows]}


@app.get("/api/v1/briefings/{briefing_id}")
def get_briefing(briefing_id: str, db: Session = Depends(get_db)):
    _require_dev_auth()
    row = db.execute(
        text("SELECT id, title, state, skill_id, language FROM briefings WHERE id = :id"),
        {"id": briefing_id},
    ).mappings().first()
    if not row:
        raise HTTPException(404, "briefing not found")
    assets = db.execute(
        text(
            "SELECT id, kind, filename, mime, bytes FROM source_assets WHERE briefing_id = :id"
        ),
        {"id": briefing_id},
    ).mappings().all()
    return {**dict(row), "assets": [dict(a) for a in assets]}


@app.post("/api/v1/briefings/{briefing_id}/assets")
async def upload_asset(
    briefing_id: str,
    kind: str = Form("recording"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    exists = db.execute(
        text("SELECT 1 FROM briefings WHERE id = :id"), {"id": briefing_id}
    ).first()
    if not exists:
        raise HTTPException(404, "briefing not found")
    _require_dev_auth()
    if not is_allowed_kind(kind):
        raise HTTPException(400, f"unknown asset kind {kind}")
    try:
        size, digest = await hash_limited(file.read)
    except UploadTooLarge as exc:
        raise HTTPException(413, str(exc))
    await file.seek(0)
    asset_id = new_id()
    safe_name = sanitize_filename(file.filename)
    key = f"briefings/{briefing_id}/{asset_id}/{safe_name}"
    put_fileobj(key, file.file, file.content_type or "application/octet-stream")
    db.execute(
        text(
            """
            INSERT INTO source_assets
              (id, briefing_id, kind, filename, mime, bytes, sha256, minio_key)
            VALUES
              (:id, :briefing_id, CAST(:kind AS asset_kind), :filename, :mime, :bytes, :sha256, :key)
            """
        ),
        {
            "id": asset_id,
            "briefing_id": briefing_id,
            "kind": kind,
            "filename": safe_name,
            "mime": file.content_type or "application/octet-stream",
            "bytes": size,
            "sha256": digest,
            "key": key,
        },
    )
    db.commit()
    return {"id": asset_id, "sha256": digest, "bytes": size}


@app.post("/api/v1/briefings/{briefing_id}/jobs")
def start_job(briefing_id: str, body: JobIn, db: Session = Depends(get_db)):
    _require_dev_auth()
    allowed = {"ingest", "transcribe", "compile", "qa", "render", "index"}
    if body.type not in allowed:
        raise HTTPException(400, f"unknown job type {body.type}")
    exists = db.execute(text("SELECT 1 FROM briefings WHERE id = :id"), {"id": briefing_id}).first()
    if not exists:
        raise HTTPException(404, "briefing not found")
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
    db.commit()
    enqueue(job_id, body.type, briefing_id)
    return {"id": job_id, "type": body.type, "state": "queued"}


@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    _require_dev_auth()
    row = db.execute(
        text("SELECT id, briefing_id, type, state, error FROM jobs WHERE id = :id"),
        {"id": job_id},
    ).mappings().first()
    if not row:
        raise HTTPException(404, "job not found")
    return dict(row)


@app.get("/api/v1/briefings/{briefing_id}/script")
def get_script(briefing_id: str, db: Session = Depends(get_db)):
    _require_dev_auth()
    row = db.execute(
        text(
            """
            SELECT id, version, accepted, raw_json
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
    return dict(row)


@app.post("/api/v1/briefings/{briefing_id}/script/accept")
def accept_script(briefing_id: str, db: Session = Depends(get_db)):
    _require_dev_auth()
    result = db.execute(
        text(
            """
            UPDATE script_versions
            SET accepted = true
            WHERE briefing_id = :id
              AND version = (
                SELECT MAX(version) FROM script_versions WHERE briefing_id = :id
              )
            """
        ),
        {"id": briefing_id},
    )
    if result.rowcount == 0:
        raise HTTPException(404, "no script to accept")
    db.execute(
        text("UPDATE briefings SET state = 'review' WHERE id = :id"),
        {"id": briefing_id},
    )
    db.commit()
    return {"accepted": True}


@app.get("/api/v1/assets/{asset_id}/content")
def asset_content(asset_id: str, db: Session = Depends(get_db)):
    _require_dev_auth()
    row = db.execute(
        text("SELECT minio_key FROM source_assets WHERE id = :id"),
        {"id": asset_id},
    ).first()
    if not row:
        raise HTTPException(404, "asset not found")
    return {"url": signed_url(row[0])}


@app.get("/api/v1/briefings/{briefing_id}/artifacts")
def list_artifacts(briefing_id: str, db: Session = Depends(get_db)):
    _require_dev_auth()
    rows = db.execute(
        text(
            "SELECT id, kind, bytes, sha256, created_at FROM artifacts "
            "WHERE briefing_id = :id ORDER BY created_at"
        ),
        {"id": briefing_id},
    ).mappings().all()
    return {"artifacts": [dict(row) for row in rows]}


@app.get("/api/v1/artifacts/{artifact_id}/content")
def artifact_content(artifact_id: str, db: Session = Depends(get_db)):
    _require_dev_auth()
    row = db.execute(
        text("SELECT minio_key FROM artifacts WHERE id = :id"),
        {"id": artifact_id},
    ).first()
    if not row:
        raise HTTPException(404, "artifact not found")
    return {"url": signed_url(row[0])}


@app.get("/api/v1/artifacts/{artifact_id}/file")
def artifact_file(artifact_id: str, request: Request, db: Session = Depends(get_db)):
    _require_dev_auth()
    """Stream an artifact from this origin so the film can seek and the deck can be framed."""
    row = db.execute(
        text("SELECT minio_key FROM artifacts WHERE id = :id"),
        {"id": artifact_id},
    ).first()
    if not row:
        raise HTTPException(404, "artifact not found")
    try:
        data = read_bytes(row[0])
    except FileNotFoundError:
        raise HTTPException(404, "artifact missing")
    try:
        status, body, headers = slice_body(data, request.headers.get("range"))
    except ValueError:
        return Response(
            status_code=416,
            headers={"Content-Range": f"bytes */{len(data)}", "Accept-Ranges": "bytes"},
        )
    headers["Content-Type"] = content_type(row[0])
    headers["Content-Disposition"] = "inline"
    headers["Cache-Control"] = "private, max-age=300"
    return Response(content=body, status_code=status, headers=headers)


@app.get("/api/v1/skills")
def list_skills():
    from grounded.catalog import CatalogError, load_catalog, load_crafts

    try:
        skills = load_catalog()
        crafts = load_crafts()
    except CatalogError as exc:
        raise HTTPException(500, str(exc)) from exc
    return {"offline": True, "skills": skills, "crafts": crafts}


@app.post("/api/v1/help/chat")
def help_chat(body: ChatIn):
    from grounded.chat import answer_grounded

    question = (body.question or "").strip()
    if not question:
        raise HTTPException(400, "question is required")
    return answer_grounded({"beats": []}, question[:2000])


@app.post("/api/v1/briefings/{briefing_id}/chat")
def briefing_chat(briefing_id: str, body: ChatIn, db: Session = Depends(get_db)):
    _require_dev_auth()
    from grounded.chat import answer_grounded

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
    if not row:
        raise HTTPException(404, "no script yet")
    raw = row[0] if isinstance(row[0], dict) else json.loads(row[0])
    return answer_grounded(raw, question[:2000], briefing_id=briefing_id, db=db)


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


def _dev_user(db: Session) -> str:
    row = db.execute(text("SELECT id FROM users LIMIT 1")).first()
    if row:
        return str(row[0])
    user_id = str(uuid.uuid4())
    db.execute(
        text(
            """
            INSERT INTO users (id, idp_sub, email, display_name)
            VALUES (:id, 'dev', 'dev@internal', 'Dev User')
            """
        ),
        {"id": user_id},
    )
    db.commit()
    return user_id


def _ensure_dev_project(db: Session) -> str:
    row = db.execute(text("SELECT id FROM projects LIMIT 1")).first()
    if row:
        return str(row[0])
    ws_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    user_id = _dev_user(db)
    db.execute(
        text("INSERT INTO workspaces (id, name, slug) VALUES (:id, 'Internal', 'internal')"),
        {"id": ws_id},
    )
    db.execute(
        text(
            """
            INSERT INTO projects (id, workspace_id, name, created_by)
            VALUES (:id, :ws, 'Pilot', :user_id)
            """
        ),
        {"id": project_id, "ws": ws_id, "user_id": user_id},
    )
    db.commit()
    return project_id
