-- Idempotent upgrade for databases created before the grounding/provenance work.
-- Applied by `python -m app.bootstrap` on every start; safe to re-run.

ALTER TYPE asset_kind ADD VALUE IF NOT EXISTS 'presentation';
ALTER TYPE asset_kind ADD VALUE IF NOT EXISTS 'image';
ALTER TYPE asset_kind ADD VALUE IF NOT EXISTS 'package';

ALTER TABLE source_assets ADD COLUMN IF NOT EXISTS parent_asset_id UUID REFERENCES source_assets(id) ON DELETE CASCADE;
ALTER TABLE source_assets ADD COLUMN IF NOT EXISTS detected_format TEXT;
ALTER TABLE source_assets ADD COLUMN IF NOT EXISTS duration_ms INT;
ALTER TABLE source_assets ADD COLUMN IF NOT EXISTS normalized_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS source_assets_briefing ON source_assets (briefing_id);

ALTER TABLE workbook_cells ADD COLUMN IF NOT EXISTS formula TEXT;

CREATE TABLE IF NOT EXISTS workbook_rows (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  asset_id      UUID NOT NULL REFERENCES source_assets(id) ON DELETE CASCADE,
  sheet         TEXT NOT NULL,
  row_num       INT NOT NULL,
  range_ref     TEXT NOT NULL,
  text          TEXT NOT NULL,
  UNIQUE (asset_id, sheet, row_num)
);

ALTER TABLE document_blocks ADD COLUMN IF NOT EXISTS extractor TEXT;
ALTER TABLE document_blocks ADD COLUMN IF NOT EXISTS ord INT NOT NULL DEFAULT 0;

ALTER TABLE script_versions ADD COLUMN IF NOT EXISTS skill_id TEXT;
ALTER TABLE script_versions ADD COLUMN IF NOT EXISTS skill_version TEXT;
ALTER TABLE script_versions ADD COLUMN IF NOT EXISTS provenance JSONB NOT NULL DEFAULT '{}';
ALTER TABLE script_versions ADD COLUMN IF NOT EXISTS providers JSONB NOT NULL DEFAULT '{}';

ALTER TABLE citations ADD COLUMN IF NOT EXISTS page INT;
ALTER TABLE citations ADD COLUMN IF NOT EXISTS range_ref TEXT;
CREATE INDEX IF NOT EXISTS citations_beat ON citations (beat_id);

CREATE TABLE IF NOT EXISTS claims (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  beat_id         UUID NOT NULL REFERENCES script_beats(id) ON DELETE CASCADE,
  citation_id     UUID REFERENCES citations(id) ON DELETE CASCADE,
  value           DOUBLE PRECISION NOT NULL,
  unit            TEXT,
  sheet           TEXT,
  addr            TEXT,
  block_id        TEXT,
  derived         BOOLEAN NOT NULL DEFAULT FALSE,
  in_text         BOOLEAN NOT NULL DEFAULT FALSE,
  formula         TEXT,
  operands        JSONB NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS claims_beat ON claims (beat_id);

DROP INDEX IF EXISTS embedding_chunks_ivf;
ALTER TABLE embedding_chunks ALTER COLUMN embedding TYPE vector;
ALTER TABLE embedding_chunks ADD COLUMN IF NOT EXISTS model TEXT NOT NULL DEFAULT 'sha256-bag-768';
ALTER TABLE embedding_chunks ADD COLUMN IF NOT EXISTS dims INT NOT NULL DEFAULT 768;
CREATE INDEX IF NOT EXISTS embedding_chunks_768 ON embedding_chunks
  USING hnsw ((embedding::vector(768)) vector_cosine_ops) WHERE dims = 768;
CREATE INDEX IF NOT EXISTS embedding_chunks_1024 ON embedding_chunks
  USING hnsw ((embedding::vector(1024)) vector_cosine_ops) WHERE dims = 1024;

ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS citations JSONB NOT NULL DEFAULT '[]';
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS provider TEXT;
