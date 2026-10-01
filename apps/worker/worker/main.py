"""Redis job consumer. Phase 1 handles transcribe, compile, qa."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

import redis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from .bootstrap import ensure_engine
from .qa import validate_script
from .settings import settings

ensure_engine()

from grounded.render_deck import render_deck  # noqa: E402
from grounded.render_recording import render_edit  # noqa: E402

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
        elif job_type == "render":
            render(db, briefing_id)
        elif job_type in {"ingest", "index"}:
            # Phase 1 no-op: assets are stored inline by the API; embeddings ship later.
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
            SELECT id, minio_key, mime FROM source_assets
            WHERE briefing_id = :id AND kind = 'recording'
            ORDER BY created_at DESC LIMIT 1
            """
        ),
        {"id": briefing_id},
    ).first()
    if not asset:
        raise RuntimeError("no recording asset")
    if settings.trans_provider == "transcribe":
        _transcribe_via_aws(db, briefing_id, asset)
        return
    # Stub provider: deterministic placeholder until GPU transcription lands.
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
    from grounded.compile_deck import CompileError
    from grounded.compile_sources import compile_uploaded

    briefing = db.execute(
        text("SELECT skill_id, title FROM briefings WHERE id = :id"),
        {"id": briefing_id},
    ).first()
    if not briefing:
        raise RuntimeError("briefing not found")
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
    try:
        script = compile_uploaded(
            skill_id=briefing[0],
            title=briefing[1],
            segments=[dict(row) for row in rows],
            document=_latest_bytes(db, briefing_id, "document"),
            workbook=_latest_bytes(db, briefing_id, "workbook"),
        )
    except CompileError as exc:
        raise RuntimeError("; ".join(exc.errors)) from exc
    errors = validate_script(script, duration_ms=script.get("source_duration_ms"))
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
                VALUES (:id, :script_id, :ord, :kind, :text, CAST(:visual AS jsonb))
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "script_id": script_id,
                "ord": beat["ord"],
                "kind": beat["kind"],
                "text": beat["text"],
                "visual": json.dumps({"layout": beat.get("layout")}),
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


def render(db, briefing_id: str) -> None:
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
    script = row[0] if isinstance(row[0], dict) else json.loads(row[0])
    errors = validate_script(script)
    if errors:
        raise RuntimeError("; ".join(errors))
    out = Path(settings.artifact_dir) / briefing_id
    out.mkdir(parents=True, exist_ok=True)
    if script.get("renderer") == "recording":
        source_video = _fetch_source_video(db, briefing_id, out)
        rendered = render_edit(script, out, source_video=source_video)
        if rendered.get("video_error"):
            raise RuntimeError(rendered["video_error"])
    else:
        render_deck(script, out / "deck.html")
    if settings.narration_provider == "polly":
        from grounded.narrate import narrate_script

        narrate_script(script, out / "voiceover.mp3", region=settings.aws_region)
    _persist_artifacts(db, briefing_id, out)

    db.execute(
        text("UPDATE briefings SET state = 'review' WHERE id = :id"),
        {"id": briefing_id},
    )
    db.commit()


def _persist_artifacts(db, briefing_id: str, out: Path) -> None:
    import hashlib

    from .store import artifact_kind, content_type_for, upload_file

    rows = []
    for path in sorted(out.iterdir()):
        if not path.is_file():
            continue
        kind = artifact_kind(path.name)
        if kind is None:
            continue
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        key = f"briefings/{briefing_id}/artifacts/{path.name}"
        size = upload_file(
            settings.minio_endpoint,
            settings.minio_bucket,
            key,
            settings.minio_access_key,
            settings.minio_secret_key,
            path,
            content_type_for(path.suffix),
            region=settings.minio_region,
        )
        rows.append((str(uuid.uuid4()), kind, key, digest.hexdigest(), size))
    db.execute(
        text("DELETE FROM artifacts WHERE briefing_id = :id"),
        {"id": briefing_id},
    )
    for artifact_id, kind, key, sha, size in rows:
        db.execute(
            text(
                "INSERT INTO artifacts (id, briefing_id, kind, minio_key, sha256, bytes) "
                "VALUES (:id, :briefing_id, :kind, :key, :sha, :bytes)"
            ),
            {
                "id": artifact_id,
                "briefing_id": briefing_id,
                "kind": kind,
                "key": key,
                "sha": sha,
                "bytes": size,
            },
        )

def _latest_bytes(db, briefing_id: str, kind: str) -> bytes | None:
    row = db.execute(
        text(
            """
            SELECT minio_key, filename FROM source_assets
            WHERE briefing_id = :id AND kind = CAST(:kind AS asset_kind)
            ORDER BY created_at DESC LIMIT 1
            """
        ),
        {"id": briefing_id, "kind": kind},
    ).first()
    if not row:
        return None
    import tempfile

    suffix = Path(row[1] or "").suffix
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    handle.close()
    dest = Path(handle.name)
    try:
        _download_asset(row[0], dest)
        return dest.read_bytes()
    finally:
        dest.unlink(missing_ok=True)


def _download_asset(key: str, dest: Path) -> None:
    from .store import download_file

    download_file(
        settings.minio_endpoint,
        settings.minio_bucket,
        key,
        settings.minio_access_key,
        settings.minio_secret_key,
        dest,
    )


def _latest_recording(db, briefing_id: str):
    asset = db.execute(
        text(
            """
            SELECT id, minio_key, mime, filename FROM source_assets
            WHERE briefing_id = :id AND kind = 'recording'
            ORDER BY created_at DESC LIMIT 1
            """
        ),
        {"id": briefing_id},
    ).first()
    if not asset:
        raise RuntimeError("no recording asset")
    return asset


def _fetch_source_video(db, briefing_id: str, out: Path):
    """Download the real capture so render cuts source pixels, not synthesis."""
    from .store import download_file

    asset = _latest_recording(db, briefing_id)
    suffix = Path(asset[3] or "").suffix or ".mp4"
    return download_file(
        settings.minio_endpoint,
        settings.minio_bucket,
        asset[1],
        settings.minio_access_key,
        settings.minio_secret_key,
        out / f"upload{suffix}",
        region=settings.minio_region,
    )


def _transcribe_via_aws(db, briefing_id: str, asset) -> None:
    from .transcribe_aws import parse_transcribe_json, stage_from_store, transcribe_media

    if not settings.trans_s3_bucket:
        raise RuntimeError("TRANS_S3_BUCKET is not set")
    asset_id, minio_key = asset[0], asset[1]
    dest_key = f"transcribe/{briefing_id}/{asset_id}"
    media_uri = stage_from_store(
        settings.minio_endpoint,
        settings.minio_bucket,
        minio_key,
        settings.minio_access_key,
        settings.minio_secret_key,
        settings.trans_s3_bucket,
        dest_key,
        settings.aws_region,
        settings.minio_region,
    )
    job_name = f"grounded-{str(asset_id).replace('-', '')[:24]}-{int(time.time())}"
    payload = transcribe_media(
        media_uri,
        job_name,
        settings.trans_language,
        settings.aws_region,
        settings.trans_timeout_s,
    )
    segments = parse_transcribe_json(payload)
    if not segments:
        raise RuntimeError("transcribe returned no segments")
    db.execute(text("DELETE FROM transcript_segments WHERE asset_id = :aid"), {"aid": asset_id})
    for segment in segments:
        db.execute(
            text(
                """
                INSERT INTO transcript_segments (id, asset_id, t_start_ms, t_end_ms, text)
                VALUES (:id, :aid, :start_ms, :end_ms, :text)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "aid": asset_id,
                "start_ms": segment["t_start_ms"],
                "end_ms": segment["t_end_ms"],
                "text": segment["text"],
            },
        )
    db.commit()


if __name__ == "__main__":
    time.sleep(2)
    main()
