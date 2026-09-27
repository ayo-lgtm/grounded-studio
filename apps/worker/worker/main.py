"""Redis job consumer. Phase 1 handles transcribe, compile, qa."""

from __future__ import annotations

import json
import time
import uuid

import redis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from .compile_walkthrough import stub_from_transcript
from .qa import validate_script
from .settings import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
Session = sessionmaker(bind=engine)
QUEUE = "grounded.jobs"


def main() -> None:
    r = redis.from_url(settings.redis_url)
    print("worker listening on", QUEUE)
    while True:
        item = r.brpop(QUEUE, timeout=5)
        if not item:
            continue
        payload = json.loads(item[1])
        handle(payload)


def handle(payload: dict) -> None:
    db = Session()
    job_id = payload["job_id"]
    job_type = payload["type"]
    briefing_id = payload["briefing_id"]
    db.execute(
        text("UPDATE jobs SET state = 'running', started_at = now() WHERE id = :id"),
        {"id": job_id},
    )
    db.commit()
    try:
        if job_type == "transcribe":
            transcribe(db, briefing_id)
        elif job_type == "compile":
            compile_script(db, briefing_id)
        elif job_type == "qa":
            run_qa(db, briefing_id)
        elif job_type in {"ingest", "render", "index"}:
            pass
        else:
            raise ValueError(f"unsupported job {job_type}")
        db.execute(
            text("UPDATE jobs SET state = 'succeeded', finished_at = now() WHERE id = :id"),
            {"id": job_id},
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        db.execute(
            text(
                "UPDATE jobs SET state = 'failed', error = :err, finished_at = now() WHERE id = :id"
            ),
            {"id": job_id, "err": str(exc)[:2000]},
        )
        db.commit()
    finally:
        db.close()


def transcribe(db, briefing_id: str) -> None:
    asset = db.execute(
        text(
            """
            SELECT id FROM source_assets
            WHERE briefing_id = :id AND kind = 'recording'
            ORDER BY created_at DESC LIMIT 1
            """
        ),
        {"id": briefing_id},
    ).first()
    if not asset:
        raise RuntimeError("no recording asset")
    db.execute(text("DELETE FROM transcript_segments WHERE asset_id = :aid"), {"aid": asset[0]})
    db.execute(
        text(
            """
            INSERT INTO transcript_segments (id, asset_id, t_start_ms, t_end_ms, text)
            VALUES (:id, :aid, 0, 5000, :text)
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "aid": asset[0],
            "text": "Placeholder transcript. Replace with faster-whisper on the GPU box.",
        },
    )
    db.commit()


def compile_script(db, briefing_id: str) -> None:
    rows = db.execute(
        text(
            """
            SELECT ts.t_start_ms, ts.t_end_ms, ts.text
            FROM transcript_segments ts
            JOIN source_assets sa ON sa.id = ts.asset_id
            WHERE sa.briefing_id = :id
            ORDER BY ts.t_start_ms
            """
        ),
        {"id": briefing_id},
    ).mappings().all()
    if not rows:
        raise RuntimeError("transcribe first")
    script = stub_from_transcript([dict(r) for r in rows])
    errors = validate_script(script)
    if errors:
        raise RuntimeError("compile QA failed: " + "; ".join(errors))
    version = db.execute(
        text("SELECT COALESCE(MAX(version), 0) + 1 FROM script_versions WHERE briefing_id = :id"),
        {"id": briefing_id},
    ).scalar_one()
    script_id = str(uuid.uuid4())
    db.execute(
        text(
            """
            INSERT INTO script_versions (id, briefing_id, version, accepted, raw_json)
            VALUES (:id, :briefing_id, :version, false, CAST(:raw AS jsonb))
            """
        ),
        {
            "id": script_id,
            "briefing_id": briefing_id,
            "version": version,
            "raw": json.dumps(script),
        },
    )
    for beat in script["beats"]:
        db.execute(
            text(
                """
                INSERT INTO script_beats (id, script_id, ord, kind, text, visual)
                VALUES (:id, :script_id, :ord, :kind, :text, '{}'::jsonb)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "script_id": script_id,
                "ord": beat["ord"],
                "kind": beat["kind"],
                "text": beat["text"],
            },
        )
    db.execute(
        text("UPDATE briefings SET state = 'review' WHERE id = :id"),
        {"id": briefing_id},
    )
    db.commit()


def run_qa(db, briefing_id: str) -> None:
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
        raise RuntimeError("no script")
    raw = row[0] if isinstance(row[0], dict) else json.loads(row[0])
    errors = validate_script(raw)
    if errors:
        raise RuntimeError("; ".join(errors))


if __name__ == "__main__":
    time.sleep(2)
    main()
