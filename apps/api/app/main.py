"""Phase 1 API. Dev auth is a header bypass. Wire SSO before any real data lands."""

from __future__ import annotations

import hashlib
import uuid
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import get_db, ping
from .queue import enqueue, new_id
from .storage import put_bytes, signed_url

app = FastAPI(title="Grounded Studio", version="0.1.0")
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


@app.get("/health")
def health():
    ok = ping()
    return {"ok": ok, "egress": "denied-by-policy"}


@app.post("/api/v1/briefings")
def create_briefing(body: BriefingIn, db: Session = Depends(get_db)):
    briefing_id = new_id()
    project_id = body.project_id or _ensure_dev_project(db)
    db.execute(
        text(
            """
            INSERT INTO briefings
              (id, project_id, title, state, skill_id, skill_version, language, created_by)
            VALUES
              (:id, :project_id, :title, 'draft', :skill_id, '1.0.0', 'en', :user_id)
            """
        ),
        {
            "id": briefing_id,
            "project_id": project_id,
            "title": body.title,
            "skill_id": body.skill_id,
            "user_id": _dev_user(db),
        },
    )
    db.commit()
    return {"id": briefing_id, "state": "draft", "skill_id": body.skill_id}


@app.get("/api/v1/briefings/{briefing_id}")
def get_briefing(briefing_id: str, db: Session = Depends(get_db)):
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
    data = await file.read()
    digest = hashlib.sha256(data).hexdigest()
    asset_id = new_id()
    key = f"briefings/{briefing_id}/{asset_id}/{file.filename}"
    put_bytes(key, data, file.content_type or "application/octet-stream")
    db.execute(
        text(
            """
            INSERT INTO source_assets
              (id, briefing_id, kind, filename, mime, bytes, sha256, minio_key)
            VALUES
              (:id, :briefing_id, :kind, :filename, :mime, :bytes, :sha256, :key)
            """
        ),
        {
            "id": asset_id,
            "briefing_id": briefing_id,
            "kind": kind,
            "filename": file.filename,
            "mime": file.content_type or "application/octet-stream",
            "bytes": len(data),
            "sha256": digest,
            "key": key,
        },
    )
    db.commit()
    return {"id": asset_id, "sha256": digest, "bytes": len(data)}


@app.post("/api/v1/briefings/{briefing_id}/jobs")
def start_job(briefing_id: str, body: JobIn, db: Session = Depends(get_db)):
    allowed = {"ingest", "transcribe", "compile", "qa", "render", "index"}
    if body.type not in allowed:
        raise HTTPException(400, f"unknown job type {body.type}")
    job_id = new_id()
    db.execute(
        text(
            """
            INSERT INTO jobs (id, briefing_id, type, state, model_ids)
            VALUES (:id, :briefing_id, :type, 'queued', '{}'::jsonb)
            """
        ),
        {"id": job_id, "briefing_id": briefing_id, "type": body.type},
    )
    db.commit()
    enqueue(job_id, body.type, briefing_id)
    return {"id": job_id, "type": body.type, "state": "queued"}


@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    row = db.execute(
        text("SELECT id, briefing_id, type, state, error FROM jobs WHERE id = :id"),
        {"id": job_id},
    ).mappings().first()
    if not row:
        raise HTTPException(404, "job not found")
    return dict(row)


@app.get("/api/v1/briefings/{briefing_id}/script")
def get_script(briefing_id: str, db: Session = Depends(get_db)):
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
    row = db.execute(
        text("SELECT minio_key FROM source_assets WHERE id = :id"),
        {"id": asset_id},
    ).first()
    if not row:
        raise HTTPException(404, "asset not found")
    return {"url": signed_url(row[0])}


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
