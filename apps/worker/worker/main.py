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

from grounded.network_policy import assert_private_runtime  # noqa: E402
from grounded.render_deck import render_deck  # noqa: E402
from grounded.render_recording import render_edit  # noqa: E402

assert_private_runtime(
    ("DATABASE_URL", settings.database_url),
    ("REDIS_URL", settings.redis_url),
    ("MINIO_ENDPOINT", settings.minio_endpoint),
    ("MODEL_BASE_URL", settings.model_base_url),
)
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
        elif job_type in {"ingest", "parse"}:
            ingest_sources(db, briefing_id)
        elif job_type == "index":
            index_knowledge(db, briefing_id)
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


def ingest_sources(db, briefing_id: str) -> None:
    """Normalize private workbook/document assets for audit and retrieval."""
    from grounded.ingest import IngestError, parse_docx, parse_pdf
    from grounded.ingest_workbook import extract_workbook_cells

    assets = db.execute(
        text(
            """
            SELECT id, kind, minio_key, filename
            FROM source_assets
            WHERE briefing_id = :id AND kind IN ('workbook', 'document')
            ORDER BY created_at
            """
        ),
        {"id": briefing_id},
    ).all()

    for asset_id, kind, key, filename in assets:
        data = _bytes_for_asset(key, filename)
        if str(kind) == "workbook":
            cells = extract_workbook_cells(data)
            db.execute(text("DELETE FROM workbook_cells WHERE asset_id = :id"), {"id": asset_id})
            for cell in cells:
                db.execute(
                    text(
                        """
                        INSERT INTO workbook_cells
                          (id, asset_id, sheet, addr, value_num, value_text, fmt)
                        VALUES
                          (:id, :asset_id, :sheet, :addr, :value_num, :value_text, :fmt)
                        """
                    ),
                    {"id": str(uuid.uuid4()), "asset_id": asset_id, **cell},
                )
            continue

        try:
            if data.startswith(b"%PDF"):
                doc = parse_pdf(data)
            elif data[:2] == b"PK":
                doc = parse_docx(data)
            elif data.lstrip()[:1] in {b"{", b"["}:
                doc = json.loads(data)
                if not isinstance(doc, dict):
                    raise RuntimeError("document JSON must be an object")
            else:
                raise RuntimeError("document must be PDF, DOCX, or JSON")
        except (IngestError, json.JSONDecodeError) as exc:
            raise RuntimeError(str(exc)) from exc

        db.execute(text("DELETE FROM document_blocks WHERE asset_id = :id"), {"id": asset_id})
        seen: set[str] = set()
        title = str(doc.get("title") or "").strip()
        title_block = str(doc.get("title_block") or "p1")
        if title:
            db.execute(
                text(
                    """
                    INSERT INTO document_blocks (id, asset_id, block_id, page, text)
                    VALUES (:id, :asset_id, :block_id, 1, :text)
                    """
                ),
                {"id": str(uuid.uuid4()), "asset_id": asset_id, "block_id": title_block, "text": title},
            )
            seen.add(title_block)
        for block in doc.get("blocks") or []:
            block_id = str(block.get("id") or "")
            block_text = str(block.get("text") or "").strip()
            if not block_id or not block_text or block_id in seen:
                continue
            db.execute(
                text(
                    """
                    INSERT INTO document_blocks
                      (id, asset_id, block_id, heading_path, page, text)
                    VALUES
                      (:id, :asset_id, :block_id, :heading_path, :page, :text)
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "asset_id": asset_id,
                    "block_id": block_id,
                    "heading_path": block.get("heading_path"),
                    "page": block.get("page"),
                    "text": block_text,
                },
            )
            seen.add(block_id)
    db.commit()


def transcribe(db, briefing_id: str) -> None:
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
    provider = (settings.trans_provider or "local").strip().lower()
    if provider in {"transcribe", "aws", "polly", "stub"}:
        raise RuntimeError("public transcription providers are disabled; set TRANS_PROVIDER=local")
    _transcribe_local(db, briefing_id, asset)


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
    asset_ids = _citation_asset_ids(db, briefing_id)
    for beat in script["beats"]:
        beat_id = str(uuid.uuid4())
        db.execute(
            text(
                """
                INSERT INTO script_beats (id, script_id, ord, kind, text, visual)
                VALUES (:id, :script_id, :ord, :kind, :text, CAST(:visual AS jsonb))
                """
            ),
            {
                "id": beat_id,
                "script_id": script_id,
                "ord": beat["ord"],
                "kind": beat["kind"],
                "text": beat["text"],
                "visual": json.dumps({"layout": beat.get("layout"), "visual": beat.get("visual")}),
            },
        )
        for cite in beat.get("citations") or []:
            asset_id = asset_ids.get(str(cite.get("kind")))
            if not asset_id:
                raise RuntimeError(f"no source asset for {cite.get('kind')} citation")
            db.execute(
                text(
                    """
                    INSERT INTO citations
                      (id, beat_id, asset_id, kind, t_start_ms, t_end_ms, sheet, addr, block_id)
                    VALUES
                      (:id, :beat_id, :asset_id, CAST(:kind AS citation_kind),
                       :t_start_ms, :t_end_ms, :sheet, :addr, :block_id)
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "beat_id": beat_id,
                    "asset_id": asset_id,
                    "kind": cite.get("kind"),
                    "t_start_ms": cite.get("t_start_ms"),
                    "t_end_ms": cite.get("t_end_ms"),
                    "sheet": cite.get("sheet"),
                    "addr": cite.get("addr"),
                    "block_id": cite.get("block_id"),
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
    video = None
    if script.get("renderer") == "recording":
        source_video = _fetch_source_video(db, briefing_id, out)
        rendered = render_edit(script, out, source_video=source_video)
        if rendered.get("video_error"):
            raise RuntimeError(rendered["video_error"])
        video = rendered.get("video")
    else:
        render_deck(script, out / "deck.html")
    _write_sidecars(script, out)
    _narrate_local(script, out, video)
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

def _citation_asset_ids(db, briefing_id: str) -> dict[str, str]:
    rows = db.execute(
        text(
            """
            SELECT DISTINCT ON (kind) kind, id
            FROM source_assets
            WHERE briefing_id = :id AND kind IN ('recording', 'workbook', 'document')
            ORDER BY kind, created_at DESC
            """
        ),
        {"id": briefing_id},
    ).all()
    return {str(kind): str(asset_id) for kind, asset_id in rows}


def _bytes_for_asset(key: str, filename: str | None) -> bytes:
    import tempfile
    suffix = Path(filename or "").suffix
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    handle.close()
    dest = Path(handle.name)
    try:
        _download_asset(key, dest)
        return dest.read_bytes()
    finally:
        dest.unlink(missing_ok=True)


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


def _transcribe_local(db, briefing_id: str, asset) -> None:
    from .transcribe_local import LocalTranscribeError, transcribe_file

    asset_id, minio_key = asset[0], asset[1]
    suffix = Path(asset[3] if len(asset) > 3 else "").suffix or ".mp4"
    dest = Path(settings.artifact_dir) / briefing_id / f"upload{suffix}"
    try:
        _download_asset(minio_key, dest)
        try:
            segments = transcribe_file(dest, settings.whisper_model, settings.whisper_cache)
        except LocalTranscribeError as exc:
            raise RuntimeError(str(exc)) from exc
    finally:
        dest.unlink(missing_ok=True)
    if not segments:
        raise RuntimeError("local transcription returned no speech")
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


def _narrate_local(script: dict, out: Path, video: Path | None) -> None:
    provider = (settings.narration_provider or "local").strip().lower()
    if provider in {"", "off", "none"}:
        return
    if provider in {"polly", "elevenlabs", "aws"}:
        raise RuntimeError("public narration providers are disabled; set NARRATION_PROVIDER=local")
    from grounded.local_voice import LocalVoiceError, max_volume_db, mix_bed, narrate_local
    from grounded.quality import clipping_warning

    if settings.piper_bin:
        import os

        os.environ["PIPER_BIN"] = settings.piper_bin
    if settings.piper_model:
        import os

        os.environ["PIPER_MODEL"] = settings.piper_model
    try:
        voice = narrate_local(script, out / "voiceover.mp3")
    except LocalVoiceError as exc:
        raise RuntimeError(str(exc)) from exc
    if video is not None and Path(video).is_file():
        mixed = out / "_mixed.mp4"
        try:
            mix_bed(Path(video), voice, mixed)
            mixed.replace(video)
        except LocalVoiceError as exc:
            raise RuntimeError(str(exc)) from exc
        finally:
            mixed.unlink(missing_ok=True)
    warning = clipping_warning(max_volume_db(out / "voiceover.mp3"))
    if warning:
        raise RuntimeError(warning)


def _write_sidecars(script: dict, out: Path) -> None:
    from grounded.formats import placement_plan
    from grounded.quality import gate_script

    report = gate_script(script)
    (out / "quality.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out / "placement.json").write_text(json.dumps(placement_plan(), indent=2), encoding="utf-8")
    if report["status"] == "fail":
        raise RuntimeError("quality gate: " + "; ".join(report["errors"]))


def index_knowledge(db, briefing_id: str) -> None:
    """Store local hash embeddings for docs and skills. No hosted embedder."""
    from grounded.knowledge import iter_chunks, vector_literal

    db.execute(text("DELETE FROM embedding_chunks WHERE briefing_id = :id"), {"id": briefing_id})
    chunks = iter_chunks()[:80]
    if not chunks:
        db.commit()
        return
    for chunk in chunks:
        db.execute(
            text(
                """
                INSERT INTO embedding_chunks (id, briefing_id, kind, text, span, embedding)
                VALUES (:id, :briefing_id, 'doc', :text, CAST(:span AS jsonb), CAST(:embedding AS vector))
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "briefing_id": briefing_id,
                "text": chunk["text"],
                "span": json.dumps({"path": chunk["path"]}),
                "embedding": vector_literal(chunk["text"]),
            },
        )
    db.commit()


if __name__ == "__main__":
    time.sleep(2)
    main()
