"""Redis job consumer: ingest, transcribe, compile, qa, render, index.

Startup is fail-closed: the deployment policy, the provider selection and
every infrastructure endpoint are validated, then the process-wide socket
guard is installed before the first job is read. Logs carry ids and counts
only (see :mod:`grounded.logsafe`).
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from .bootstrap import ensure_engine
from .qa import validate_script
from .settings import settings

ensure_engine()

from grounded import guard, logsafe  # noqa: E402
from grounded.policy import assert_runtime  # noqa: E402
from grounded.providers import registry  # noqa: E402

POLICY = assert_runtime(
    ("DATABASE_URL", settings.database_url),
    ("REDIS_URL", settings.redis_url),
    ("MODEL_BASE_URL", settings.model_base_url),
)
SELECTION = registry.selection()

engine = create_engine(settings.database_url, pool_pre_ping=True)
Session = sessionmaker(bind=engine)
QUEUE = "grounded.jobs"

MAX_PARSE_BYTES = 512 * 1024**2
AUDITABLE_KINDS = ("workbook", "document", "presentation", "image", "recording")


class JobError(RuntimeError):
    pass


def main() -> None:
    import redis

    logsafe.configure()
    guard.install(POLICY)
    from grounded.objectstore import check

    check(_store_config())
    r = redis.from_url(settings.redis_url)
    logsafe.log_event("worker.start", mode=POLICY.mode, provider=SELECTION.inference)
    while True:
        item = r.brpop(QUEUE, timeout=5)
        if not item:
            continue
        payload = json.loads(item[1])
        handle(payload)


def _store_config():
    from grounded.objectstore import StoreConfig

    return StoreConfig(
        settings.minio_endpoint,
        settings.minio_bucket,
        settings.minio_access_key,
        settings.minio_secret_key,
        settings.minio_region,
    )


HANDLERS: dict[str, Any] = {}


def handle(payload: dict, session_factory: Any = None) -> None:
    db = (session_factory or Session)()
    job_id = payload["job_id"]
    job_type = payload["type"]
    briefing_id = payload["briefing_id"]
    started = time.monotonic()
    db.execute(
        text("UPDATE jobs SET state = 'running', started_at = now() WHERE id = :id"),
        {"id": job_id},
    )
    db.commit()
    logsafe.log_event("job.start", job_id=job_id, job_type=job_type, briefing_id=briefing_id)
    try:
        runner = HANDLERS.get(job_type)
        if runner is None:
            raise JobError(f"unsupported job {job_type}")
        models = runner(db, briefing_id) or {}
        db.execute(
            text(
                "UPDATE jobs SET state = 'succeeded', finished_at = now(), "
                "model_ids = CAST(:models AS jsonb) WHERE id = :id"
            ),
            {"id": job_id, "models": json.dumps(models)},
        )
        db.commit()
        logsafe.log_event(
            "job.succeeded", job_id=job_id, job_type=job_type,
            elapsed_ms=int((time.monotonic() - started) * 1000),
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        db.execute(
            text(
                "UPDATE jobs SET state = 'failed', error = :err, finished_at = now() WHERE id = :id"
            ),
            {"id": job_id, "err": str(exc)[:2000]},
        )
        db.commit()
        logsafe.log_failure("job.failed", exc, job_id=job_id, job_type=job_type)
    finally:
        db.close()


# ---------------------------------------------------------------- storage

def _download(key: str, dest: Path) -> Path:
    from .store import download_file

    return download_file(
        settings.minio_endpoint,
        settings.minio_bucket,
        key,
        settings.minio_access_key,
        settings.minio_secret_key,
        dest,
        region=settings.minio_region,
    )


def _upload(key: str, src: Path, content_type: str) -> int:
    from .store import upload_file

    return upload_file(
        settings.minio_endpoint,
        settings.minio_bucket,
        key,
        settings.minio_access_key,
        settings.minio_secret_key,
        src,
        content_type,
        region=settings.minio_region,
    )


def _asset_bytes(key: str, filename: str | None) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / ("asset" + Path(filename or "").suffix)
        _download(key, dest)
        if dest.stat().st_size > MAX_PARSE_BYTES:
            raise JobError("source is too large to parse")
        return dest.read_bytes()


# ---------------------------------------------------------------- ingest

def ingest_sources(db, briefing_id: str) -> dict:
    """Normalize every not-yet-normalized asset: cells, rows, blocks, packages."""
    from grounded.sources import detect_bytes, normalize, unpack

    pending = list(
        db.execute(
            text(
                """
                SELECT id, kind::text, filename, minio_key, mime
                FROM source_assets
                WHERE briefing_id = :id AND normalized_at IS NULL
                ORDER BY created_at
                """
            ),
            {"id": briefing_id},
        ).all()
    )
    image_text = None
    counts = {"members": 0, "cells": 0, "rows": 0, "blocks": 0}
    while pending:
        asset_id, kind, filename, key, mime = pending.pop(0)
        asset_id = str(asset_id)
        if kind == "recording":
            _mark_recording(db, asset_id, key, filename)
            continue
        data = _asset_bytes(key, filename)
        detected = detect_bytes(filename, data)
        if detected.kind == "package":
            for member in unpack(data):
                child, child_key = _store_member(db, briefing_id, asset_id, member)
                pending.append((child, member.detected.kind, _safe_name(member.name), child_key, None))
                counts["members"] += 1
            _mark(db, asset_id, "package", "zip")
            continue
        if detected.kind == "recording":
            _mark_recording(db, asset_id, key, filename, kind="recording")
            continue
        if detected.kind == "image" and image_text is None:
            image_text = registry.image_text_provider()
        normalized = normalize(filename, data, image_text=image_text)
        if normalized.kind == "workbook":
            _persist_workbook(db, asset_id, normalized)
            counts["cells"] += len(normalized.cells)
            counts["rows"] += len(normalized.rows)
        else:
            _persist_blocks(db, asset_id, normalized.blocks)
            counts["blocks"] += len(normalized.blocks)
        _mark(db, asset_id, normalized.kind, normalized.format)
    db.commit()
    logsafe.log_event("ingest.done", briefing_id=briefing_id, **counts)
    return {}


def _safe_name(name: str) -> str:
    base = Path(name.replace("\\", "/")).name.replace("\x00", "").strip() or "member.bin"
    return base[:128]


def _store_member(db, briefing_id: str, parent_id: str, member) -> tuple[str, str]:
    child_id = str(uuid.uuid4())
    safe = _safe_name(member.name)
    key = f"briefings/{briefing_id}/{child_id}/{safe}"
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "member"
        path.write_bytes(member.data)
        _upload(key, path, "application/octet-stream")
    db.execute(
        text(
            """
            INSERT INTO source_assets
              (id, briefing_id, kind, filename, mime, bytes, sha256, minio_key, parent_asset_id, detected_format)
            VALUES
              (:id, :briefing_id, CAST(:kind AS asset_kind), :filename, 'application/octet-stream',
               :bytes, :sha, :key, :parent, :fmt)
            """
        ),
        {
            "id": child_id,
            "briefing_id": briefing_id,
            "kind": member.detected.kind,
            "filename": safe,
            "bytes": len(member.data),
            "sha": hashlib.sha256(member.data).hexdigest(),
            "key": key,
            "parent": parent_id,
            "fmt": member.detected.format,
        },
    )
    return child_id, key


def _mark(db, asset_id: str, kind: str, fmt: str) -> None:
    db.execute(
        text(
            "UPDATE source_assets SET kind = CAST(:kind AS asset_kind), detected_format = :fmt, "
            "normalized_at = now() WHERE id = :id"
        ),
        {"id": asset_id, "kind": kind, "fmt": fmt},
    )


def _mark_recording(db, asset_id: str, key: str | None, filename: str | None, kind: str = "recording") -> None:
    duration = None
    if key and shutil.which("ffprobe"):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / ("rec" + (Path(filename or "").suffix or ".mp4"))
            _download(key, dest)
            duration = probe_duration_ms(dest)
    db.execute(
        text(
            "UPDATE source_assets SET kind = CAST(:kind AS asset_kind), duration_ms = COALESCE(:d, duration_ms), "
            "detected_format = COALESCE(detected_format, :fmt), normalized_at = now() WHERE id = :id"
        ),
        {"id": asset_id, "kind": kind, "d": duration, "fmt": Path(filename or "").suffix.lstrip(".") or None},
    )


def probe_duration_ms(path: Path) -> int | None:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True,
        timeout=60,
        check=False,
    )
    try:
        return int(float(proc.stdout.decode().strip()) * 1000)
    except ValueError:
        return None


def _persist_workbook(db, asset_id: str, normalized) -> None:
    db.execute(text("DELETE FROM workbook_cells WHERE asset_id = :id"), {"id": asset_id})
    db.execute(text("DELETE FROM workbook_rows WHERE asset_id = :id"), {"id": asset_id})
    for cell in normalized.cells:
        db.execute(
            text(
                """
                INSERT INTO workbook_cells (id, asset_id, sheet, addr, value_num, value_text, fmt, formula)
                VALUES (:id, :asset_id, :sheet, :addr, :value_num, :value_text, :fmt, :formula)
                """
            ),
            {"id": str(uuid.uuid4()), "asset_id": asset_id, "formula": cell.get("formula"), **{k: cell.get(k) for k in ("sheet", "addr", "value_num", "value_text", "fmt")}},
        )
    for row in normalized.rows:
        db.execute(
            text(
                """
                INSERT INTO workbook_rows (id, asset_id, sheet, row_num, range_ref, text)
                VALUES (:id, :asset_id, :sheet, :row_num, :range_ref, :text)
                """
            ),
            {"id": str(uuid.uuid4()), "asset_id": asset_id, **row},
        )


def _persist_blocks(db, asset_id: str, blocks: list[dict]) -> None:
    db.execute(text("DELETE FROM document_blocks WHERE asset_id = :id"), {"id": asset_id})
    for index, block in enumerate(blocks):
        db.execute(
            text(
                """
                INSERT INTO document_blocks (id, asset_id, block_id, heading_path, page, text, extractor, ord)
                VALUES (:id, :asset_id, :block_id, :heading_path, :page, :text, :extractor, :ord)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "asset_id": asset_id,
                "block_id": block["block_id"],
                "heading_path": block.get("heading_path"),
                "page": block.get("page"),
                "text": block["text"],
                "extractor": block.get("extractor"),
                "ord": index,
            },
        )


# ---------------------------------------------------------------- transcribe

def transcribe(db, briefing_id: str) -> dict:
    from grounded.providers.base import ProviderError

    asset = db.execute(
        text(
            """
            SELECT id, minio_key, filename FROM source_assets
            WHERE briefing_id = :id AND kind = 'recording'
            ORDER BY created_at DESC LIMIT 1
            """
        ),
        {"id": briefing_id},
    ).first()
    if not asset:
        raise JobError("no recording asset")
    provider = registry.transcription_provider()
    asset_id, key, filename = str(asset[0]), asset[1], asset[2]
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / ("upload" + (Path(filename or "").suffix or ".mp4"))
        _download(key, dest)
        duration = probe_duration_ms(dest) if shutil.which("ffprobe") else None
        try:
            segments = provider.transcribe(dest, (settings.trans_language or "en")[:2])
        except ProviderError as exc:
            raise JobError(str(exc)) from exc
    if not segments:
        raise JobError("transcription returned no speech")
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
    db.execute(
        text(
            "UPDATE source_assets SET duration_ms = COALESCE(:d, duration_ms), normalized_at = now() WHERE id = :id"
        ),
        {"id": asset_id, "d": duration},
    )
    db.commit()
    logsafe.log_event("transcribe.done", briefing_id=briefing_id, segments=len(segments), provider=provider.name)
    return {"transcription": f"{provider.name}:{provider.model_id}"}


# ---------------------------------------------------------------- compile

def build_bundle(db, briefing_id: str):
    """Assemble compiler inputs from normalized, persisted sources only."""
    from grounded.dispatch import SourceBundle, SourceDoc

    assets = db.execute(
        text(
            """
            SELECT id, kind::text, filename, minio_key, duration_ms, detected_format
            FROM source_assets
            WHERE briefing_id = :id AND normalized_at IS NOT NULL AND kind::text <> 'package'
            ORDER BY created_at
            """
        ),
        {"id": briefing_id},
    ).all()
    bundle = SourceBundle()
    for asset_id, kind, filename, key, duration, fmt in assets:
        asset_id = str(asset_id)
        if kind == "workbook":
            if fmt == "json":
                raise JobError(
                    "JSON workbook packs are not auditable source cells; upload the .xlsx or .csv workbook"
                )
            bundle.workbook = _asset_bytes(key, filename)
            bundle.workbook_asset = asset_id
        elif kind in {"document", "presentation", "image"}:
            doc = _doc_from_blocks(db, asset_id)
            if doc is not None:
                bundle.documents.append(SourceDoc(asset_id, kind, doc))
        elif kind == "recording":
            rows = db.execute(
                text(
                    "SELECT t_start_ms, t_end_ms, text FROM transcript_segments "
                    "WHERE asset_id = :id ORDER BY t_start_ms"
                ),
                {"id": asset_id},
            ).mappings().all()
            if rows:
                bundle.segments = [dict(row) for row in rows]
                bundle.recording_asset = asset_id
                bundle.duration_ms = duration
    return bundle


def _doc_from_blocks(db, asset_id: str) -> dict | None:
    import re

    from grounded.ingest import _role

    rows = db.execute(
        text(
            "SELECT block_id, text, page, heading_path, extractor FROM document_blocks "
            "WHERE asset_id = :id ORDER BY ord"
        ),
        {"id": asset_id},
    ).mappings().all()
    if not rows:
        return None
    first, rest = rows[0], rows[1:]
    blocks = []
    for row in rest:
        if re.fullmatch(r"s\d+-n\d+", row["block_id"]):
            continue  # speaker notes stay searchable but are not slides
        block = {"id": row["block_id"], "text": row["text"], "role": _role(row["text"])}
        if row["page"] is not None:
            block["page"] = row["page"]
        if row["heading_path"]:
            block["heading_path"] = row["heading_path"]
        blocks.append(block)
    return {"title": first["text"], "title_block": first["block_id"], "blocks": blocks}


def compile_script(db, briefing_id: str) -> dict:
    from grounded.compile_deck import CompileError
    from grounded.dispatch import compile_bundle

    ingest_sources(db, briefing_id)
    briefing = db.execute(
        text("SELECT skill_id, title FROM briefings WHERE id = :id"),
        {"id": briefing_id},
    ).first()
    if not briefing:
        raise JobError("briefing not found")
    bundle = build_bundle(db, briefing_id)
    try:
        script = compile_bundle(skill_id=briefing[0], title=briefing[1], bundle=bundle)
    except CompileError as exc:
        raise JobError("; ".join(exc.errors)) from exc
    script = _assist(script, bundle)
    errors = validate_script(script, duration_ms=script.get("source_duration_ms"))
    errors += verify_against_sources(db, briefing_id, script)
    if errors:
        raise JobError("grounding QA failed: " + "; ".join(errors[:20]))
    script_id, version = persist_script(db, briefing_id, script)
    db.execute(text("UPDATE briefings SET state = 'review' WHERE id = :id"), {"id": briefing_id})
    db.commit()
    logsafe.log_event(
        "compile.done", briefing_id=briefing_id, script_id=script_id, version=version,
        beats=len(script["beats"]), skill_id=script.get("skill_id"), skill_version=script.get("skill_version"),
    )
    return script.get("providers") or {}


def _assist(script: dict, _bundle) -> dict:
    """Optional model assist (polish/summary). Grounding gates decide; never fallback."""
    from grounded.assist import assist_script

    return assist_script(script)


def verify_against_sources(db, briefing_id: str, script: dict) -> list[str]:
    """Every citation and claim must resolve to persisted, normalized source rows."""
    from grounded.numbers import close, parse_numbers

    errors: list[str] = []
    assets = {
        str(row[0]): (row[1], row[2])
        for row in db.execute(
            text("SELECT id, kind::text, duration_ms FROM source_assets WHERE briefing_id = :id"),
            {"id": briefing_id},
        ).all()
    }
    cell_cache: dict[tuple[str, str, str], Any] = {}
    block_cache: dict[tuple[str, str], str | None] = {}

    def cell(asset_id: str, sheet: str, addr: str):
        key = (asset_id, sheet, addr)
        if key not in cell_cache:
            cell_cache[key] = db.execute(
                text(
                    "SELECT value_num, value_text FROM workbook_cells "
                    "WHERE asset_id = :a AND sheet = :s AND addr = :c"
                ),
                {"a": asset_id, "s": sheet, "c": addr},
            ).first()
        return cell_cache[key]

    def block(asset_id: str, block_id: str):
        key = (asset_id, block_id)
        if key not in block_cache:
            row = db.execute(
                text("SELECT text FROM document_blocks WHERE asset_id = :a AND block_id = :b"),
                {"a": asset_id, "b": block_id},
            ).first()
            block_cache[key] = row[0] if row else None
        return block_cache[key]

    for beat in script.get("beats") or []:
        ord_ = beat.get("ord")
        workbook_asset = None
        doc_assets: dict[str, str] = {}
        for cite in beat.get("citations") or []:
            asset_id = str(cite.get("asset_id") or "")
            if asset_id not in assets:
                errors.append(f"beat {ord_} citation does not name a source asset of this briefing")
                continue
            kind = cite.get("kind")
            if kind == "workbook":
                workbook_asset = asset_id
                if cell(asset_id, cite.get("sheet"), cite.get("addr")) is None:
                    errors.append(f"beat {ord_} cites {cite.get('sheet')}!{cite.get('addr')}, absent from the normalized workbook")
            elif kind == "document":
                doc_assets[str(cite.get("block_id"))] = asset_id
                if block(asset_id, str(cite.get("block_id"))) is None:
                    errors.append(f"beat {ord_} cites block {cite.get('block_id')}, absent from the normalized document")
            elif kind == "recording":
                duration = assets[asset_id][1]
                start, end = int(cite.get("t_start_ms") or 0), int(cite.get("t_end_ms") or 0)
                if duration is not None and end > duration + 250:
                    errors.append(f"beat {ord_} recording citation runs past the source duration")
                hit = db.execute(
                    text(
                        "SELECT 1 FROM transcript_segments WHERE asset_id = :a "
                        "AND t_start_ms < :e AND t_end_ms > :s LIMIT 1"
                    ),
                    {"a": asset_id, "s": start, "e": end},
                ).first()
                if hit is None:
                    errors.append(f"beat {ord_} recording citation has no transcript at that time")
        for claim in beat.get("claims") or []:
            if claim.get("derived"):
                continue  # recomputed from cited operands by QA
            if claim.get("sheet") and claim.get("addr") and workbook_asset:
                row = cell(workbook_asset, claim["sheet"], claim["addr"])
                if row is None:
                    errors.append(f"beat {ord_} claim {claim['sheet']}!{claim['addr']} is not a source cell")
                    continue
                value_num, value_text = row
                if claim.get("in_text"):
                    if not any(close(float(claim["value"]), n) for n in parse_numbers(str(value_text or ""))):
                        errors.append(f"beat {ord_} number {claim['value']} is not in {claim['sheet']}!{claim['addr']}")
                else:
                    expected = claim.get("cell", claim["value"])
                    if value_num is None or not close(float(expected), float(value_num)):
                        errors.append(f"beat {ord_} claim does not match source cell {claim['sheet']}!{claim['addr']}")
            elif claim.get("block_id"):
                asset_id = doc_assets.get(str(claim["block_id"]))
                source = block(asset_id, str(claim["block_id"])) if asset_id else None
                if source is None or not any(close(float(claim["value"]), n) for n in parse_numbers(source)):
                    errors.append(f"beat {ord_} number {claim['value']} is not in block {claim['block_id']}")
    return errors


def persist_script(db, briefing_id: str, script: dict) -> tuple[str, int]:
    version = db.execute(
        text("SELECT COALESCE(MAX(version), 0) + 1 FROM script_versions WHERE briefing_id = :id"),
        {"id": briefing_id},
    ).scalar_one()
    script_id = str(uuid.uuid4())
    provenance = {
        key: value
        for key, value in (script.get("provenance") or {}).items()
        if key not in {"contract_text", "craft_contracts"}
    }
    db.execute(
        text(
            """
            INSERT INTO script_versions
              (id, briefing_id, version, accepted, raw_json, skill_id, skill_version, provenance, providers)
            VALUES
              (:id, :briefing_id, :version, false, CAST(:raw AS jsonb), :skill_id, :skill_version,
               CAST(:provenance AS jsonb), CAST(:providers AS jsonb))
            """
        ),
        {
            "id": script_id,
            "briefing_id": briefing_id,
            "version": version,
            "raw": json.dumps(script),
            "skill_id": script.get("skill_id"),
            "skill_version": script.get("skill_version"),
            "provenance": json.dumps(provenance),
            "providers": json.dumps(script.get("providers") or {}),
        },
    )
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
        by_cell: dict[tuple[str, str], str] = {}
        by_block: dict[str, str] = {}
        first_cite: str | None = None
        for cite in beat.get("citations") or []:
            citation_id = str(uuid.uuid4())
            first_cite = first_cite or citation_id
            db.execute(
                text(
                    """
                    INSERT INTO citations
                      (id, beat_id, asset_id, kind, t_start_ms, t_end_ms, sheet, addr, block_id, page, range_ref)
                    VALUES
                      (:id, :beat_id, :asset_id, CAST(:kind AS citation_kind),
                       :t_start_ms, :t_end_ms, :sheet, :addr, :block_id, :page, :range_ref)
                    """
                ),
                {
                    "id": citation_id,
                    "beat_id": beat_id,
                    "asset_id": cite["asset_id"],
                    "kind": cite.get("kind"),
                    "t_start_ms": cite.get("t_start_ms"),
                    "t_end_ms": cite.get("t_end_ms"),
                    "sheet": cite.get("sheet"),
                    "addr": cite.get("addr"),
                    "block_id": cite.get("block_id"),
                    "page": cite.get("page"),
                    "range_ref": cite.get("range"),
                },
            )
            if cite.get("sheet"):
                by_cell[(cite["sheet"], cite["addr"])] = citation_id
            if cite.get("block_id"):
                by_block[str(cite["block_id"])] = citation_id
        for claim in beat.get("claims") or []:
            citation_id = (
                by_cell.get((claim.get("sheet"), claim.get("addr")))
                or by_block.get(str(claim.get("block_id")))
                or first_cite
            )
            db.execute(
                text(
                    """
                    INSERT INTO claims
                      (id, beat_id, citation_id, value, unit, sheet, addr, block_id, derived, in_text, formula, operands)
                    VALUES
                      (:id, :beat_id, :citation_id, :value, :unit, :sheet, :addr, :block_id, :derived, :in_text,
                       :formula, CAST(:operands AS jsonb))
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "beat_id": beat_id,
                    "citation_id": citation_id,
                    "value": float(claim["value"]),
                    "unit": claim.get("unit"),
                    "sheet": claim.get("sheet"),
                    "addr": claim.get("addr"),
                    "block_id": claim.get("block_id"),
                    "derived": bool(claim.get("derived")),
                    "in_text": bool(claim.get("in_text")),
                    "formula": claim.get("formula"),
                    "operands": json.dumps(claim.get("operands") or []),
                },
            )
    return script_id, int(version)


# ---------------------------------------------------------------- qa / render

def _latest_script(db, briefing_id: str) -> dict:
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
        raise JobError("no script")
    return row[0] if isinstance(row[0], dict) else json.loads(row[0])


def run_qa(db, briefing_id: str) -> dict:
    script = _latest_script(db, briefing_id)
    errors = validate_script(script, duration_ms=script.get("source_duration_ms"))
    errors += verify_against_sources(db, briefing_id, script)
    if errors:
        raise JobError("; ".join(errors[:20]))
    return {}


def render(db, briefing_id: str) -> dict:
    from grounded.render_deck import render_deck
    from grounded.render_recording import render_edit

    script = _latest_script(db, briefing_id)
    errors = validate_script(script, duration_ms=script.get("source_duration_ms"))
    errors += verify_against_sources(db, briefing_id, script)
    if errors:
        raise JobError("; ".join(errors[:20]))
    out = Path(settings.artifact_dir) / briefing_id
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    models: dict[str, str] = {}
    try:
        video = None
        if script.get("renderer") == "recording":
            source_video = _fetch_source_video(db, briefing_id, out)
            rendered = render_edit(script, out, source_video=source_video)
            if rendered.get("video_error"):
                raise JobError(rendered["video_error"])
            video = rendered.get("video")
        else:
            render_deck(script, out / "deck.html")
        _write_sidecars(script, out)
        write_audits(script, out)
        models.update(_narrate(script, out, video))
        _persist_artifacts(db, briefing_id, out)
    finally:
        shutil.rmtree(out, ignore_errors=True)
    db.execute(text("UPDATE briefings SET state = 'review' WHERE id = :id"), {"id": briefing_id})
    db.commit()
    return models


def write_audits(script: dict, out: Path) -> None:
    """cell_audit.csv, calculation_audit.csv, data_quality.json, provenance.json."""
    cells = io.StringIO()
    writer = csv.writer(cells)
    writer.writerow(["beat", "kind", "asset_id", "sheet", "addr", "block_id", "page", "t_start_ms", "t_end_ms"])
    for beat in script.get("beats") or []:
        for cite in beat.get("citations") or []:
            writer.writerow([
                beat.get("ord"), cite.get("kind"), cite.get("asset_id"), cite.get("sheet"), cite.get("addr"),
                cite.get("block_id"), cite.get("page"), cite.get("t_start_ms"), cite.get("t_end_ms"),
            ])
    (out / "cell_audit.csv").write_text(cells.getvalue(), encoding="utf-8")
    calcs = io.StringIO()
    writer = csv.writer(calcs)
    writer.writerow(["beat", "value", "formula", "operands"])
    for beat in script.get("beats") or []:
        for claim in beat.get("claims") or []:
            if claim.get("derived"):
                operands = ";".join(f"{o.get('sheet')}!{o.get('addr')}" for o in claim.get("operands") or [])
                writer.writerow([beat.get("ord"), claim.get("value"), claim.get("formula"), operands])
    (out / "calculation_audit.csv").write_text(calcs.getvalue(), encoding="utf-8")
    (out / "data_quality.json").write_text(json.dumps(script.get("data_quality") or [], indent=2), encoding="utf-8")
    provenance = {k: v for k, v in (script.get("provenance") or {}).items() if k not in {"contract_text", "craft_contracts"}}
    provenance["providers"] = script.get("providers") or {}
    (out / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")


def _persist_artifacts(db, briefing_id: str, out: Path) -> None:
    from .store import artifact_kind, content_type_for

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
        size = _upload(key, path, content_type_for(path.suffix))
        rows.append((str(uuid.uuid4()), kind, key, digest.hexdigest(), size))
    db.execute(text("DELETE FROM artifacts WHERE briefing_id = :id"), {"id": briefing_id})
    for artifact_id, kind, key, sha, size in rows:
        db.execute(
            text(
                "INSERT INTO artifacts (id, briefing_id, kind, minio_key, sha256, bytes) "
                "VALUES (:id, :briefing_id, :kind, :key, :sha, :bytes)"
            ),
            {"id": artifact_id, "briefing_id": briefing_id, "kind": kind, "key": key, "sha": sha, "bytes": size},
        )


def _fetch_source_video(db, briefing_id: str, out: Path):
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
        raise JobError("no recording asset")
    suffix = Path(asset[3] or "").suffix or ".mp4"
    return _download(asset[1], out / f"upload{suffix}")


def _narrate(script: dict, out: Path, video: Path | None) -> dict:
    from grounded.local_voice import LocalVoiceError, max_volume_db, mix_bed
    from grounded.providers.base import ProviderError
    from grounded.quality import clipping_warning

    provider = registry.speech_provider()
    if provider is None:
        return {}
    try:
        voice = provider.narrate(script, out / "voiceover.mp3")
    except ProviderError as exc:
        raise JobError(str(exc)) from exc
    if video is not None and Path(video).is_file():
        mixed = out / "_mixed.mp4"
        try:
            mix_bed(Path(video), voice, mixed)
            mixed.replace(video)
        except LocalVoiceError as exc:
            raise JobError(str(exc)) from exc
        finally:
            mixed.unlink(missing_ok=True)
    warning = clipping_warning(max_volume_db(out / "voiceover.mp3"))
    if warning:
        raise JobError(warning)
    return {"tts": f"{provider.name}:{provider.model_id}"}


def _write_sidecars(script: dict, out: Path) -> None:
    from grounded.formats import placement_plan
    from grounded.quality import gate_script

    report = gate_script(script)
    (out / "quality.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out / "placement.json").write_text(json.dumps(placement_plan(), indent=2), encoding="utf-8")
    if report["status"] == "fail":
        raise JobError("quality gate: " + "; ".join(report["errors"]))


# ---------------------------------------------------------------- index

def index_sources(db, briefing_id: str) -> dict:
    """Embed this briefing's own normalized sources for retrieval."""
    from grounded.chat import load_passages

    provider = registry.embedding_provider()
    passages = load_passages(db, briefing_id)
    db.execute(text("DELETE FROM embedding_chunks WHERE briefing_id = :id"), {"id": briefing_id})
    texts = [p["text"] for p in passages]
    vectors = provider.embed(texts) if texts else []
    for passage, vector in zip(passages, vectors):
        cite = passage["citation"]
        db.execute(
            text(
                """
                INSERT INTO embedding_chunks (id, briefing_id, asset_id, kind, text, span, model, dims, embedding)
                VALUES (:id, :briefing_id, :asset_id, :kind, :text, CAST(:span AS jsonb), :model, :dims,
                        CAST(:embedding AS vector))
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "briefing_id": briefing_id,
                "asset_id": cite.get("asset_id"),
                "kind": cite.get("kind"),
                "text": passage["text"],
                "span": json.dumps(cite),
                "model": provider.model_id,
                "dims": provider.dims,
                "embedding": "[" + ",".join(f"{v:.6f}" for v in vector) + "]",
            },
        )
    db.commit()
    logsafe.log_event("index.done", briefing_id=briefing_id, count=len(vectors), provider=provider.name, dims=provider.dims)
    return {"embedding": f"{provider.name}:{provider.model_id}"}


HANDLERS.update(
    {
        "ingest": ingest_sources,
        "parse": ingest_sources,
        "transcribe": transcribe,
        "compile": compile_script,
        "qa": run_qa,
        "render": render,
        "index": index_sources,
    }
)


if __name__ == "__main__":
    time.sleep(2)
    main()
