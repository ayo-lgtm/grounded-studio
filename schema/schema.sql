-- Grounded Studio v1 schema
-- Postgres 16 + pgvector >= 0.5 (HNSW)
-- Fresh databases apply this file; existing ones apply schema/migrations/*.sql.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE workspace_role AS ENUM ('admin', 'owner', 'editor', 'viewer');
CREATE TYPE asset_kind AS ENUM ('recording', 'workbook', 'document', 'attachment', 'presentation', 'image', 'package');
CREATE TYPE briefing_state AS ENUM ('draft', 'compiling', 'review', 'rendering', 'published', 'archived');
CREATE TYPE job_type AS ENUM (
  'ingest', 'transcribe', 'parse', 'compile', 'qa', 'render', 'index', 'localize', 'diff'
);
CREATE TYPE job_state AS ENUM ('queued', 'running', 'succeeded', 'failed', 'cancelled');
CREATE TYPE citation_kind AS ENUM ('recording', 'workbook', 'document');

CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  idp_sub       TEXT NOT NULL UNIQUE,
  email         TEXT NOT NULL,
  display_name  TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE workspaces (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name          TEXT NOT NULL,
  slug          TEXT NOT NULL UNIQUE,
  retention_days INT NOT NULL DEFAULT 365,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE workspace_members (
  workspace_id  UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role          workspace_role NOT NULL,
  PRIMARY KEY (workspace_id, user_id)
);

CREATE TABLE projects (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  workspace_id  UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  name          TEXT NOT NULL,
  created_by    UUID NOT NULL REFERENCES users(id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE briefings (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  parent_id       UUID REFERENCES briefings(id),
  template_id     UUID REFERENCES briefings(id),
  title           TEXT NOT NULL,
  state           briefing_state NOT NULL DEFAULT 'draft',
  skill_id        TEXT NOT NULL,
  skill_version   TEXT NOT NULL,
  language        TEXT NOT NULL DEFAULT 'en',
  is_template     BOOLEAN NOT NULL DEFAULT FALSE,
  visibility      TEXT NOT NULL DEFAULT 'workspace',
  published_at    TIMESTAMPTZ,
  created_by      UUID NOT NULL REFERENCES users(id),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE briefing_grants (
  briefing_id   UUID NOT NULL REFERENCES briefings(id) ON DELETE CASCADE,
  email         TEXT NOT NULL,
  role          TEXT NOT NULL DEFAULT 'viewer',
  granted_by    UUID REFERENCES users(id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (briefing_id, email)
);
CREATE INDEX briefing_grants_email ON briefing_grants (email);

CREATE TABLE source_assets (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  briefing_id   UUID NOT NULL REFERENCES briefings(id) ON DELETE CASCADE,
  kind          asset_kind NOT NULL,
  filename      TEXT NOT NULL,
  mime          TEXT NOT NULL,
  bytes         BIGINT NOT NULL,
  sha256        TEXT NOT NULL,
  minio_key     TEXT NOT NULL,
  parent_asset_id UUID REFERENCES source_assets(id) ON DELETE CASCADE,
  detected_format TEXT,
  duration_ms   INT,
  normalized_at TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX source_assets_sha ON source_assets (sha256);
CREATE INDEX source_assets_briefing ON source_assets (briefing_id);

CREATE TABLE transcript_segments (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  asset_id      UUID NOT NULL REFERENCES source_assets(id) ON DELETE CASCADE,
  t_start_ms    INT NOT NULL,
  t_end_ms      INT NOT NULL,
  text          TEXT NOT NULL,
  speaker       TEXT
);

CREATE TABLE workbook_cells (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  asset_id      UUID NOT NULL REFERENCES source_assets(id) ON DELETE CASCADE,
  sheet         TEXT NOT NULL,
  addr          TEXT NOT NULL,
  value_num     DOUBLE PRECISION,
  value_text    TEXT,
  fmt           TEXT,
  formula       TEXT,
  UNIQUE (asset_id, sheet, addr)
);

CREATE TABLE workbook_rows (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  asset_id      UUID NOT NULL REFERENCES source_assets(id) ON DELETE CASCADE,
  sheet         TEXT NOT NULL,
  row_num       INT NOT NULL,
  range_ref     TEXT NOT NULL,
  text          TEXT NOT NULL,
  UNIQUE (asset_id, sheet, row_num)
);

CREATE TABLE document_blocks (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  asset_id      UUID NOT NULL REFERENCES source_assets(id) ON DELETE CASCADE,
  block_id      TEXT NOT NULL,
  heading_path  TEXT,
  page          INT,
  text          TEXT NOT NULL,
  extractor     TEXT,
  ord           INT NOT NULL DEFAULT 0,
  UNIQUE (asset_id, block_id)
);

CREATE TABLE script_versions (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  briefing_id   UUID NOT NULL REFERENCES briefings(id) ON DELETE CASCADE,
  version       INT NOT NULL,
  accepted      BOOLEAN NOT NULL DEFAULT FALSE,
  accepted_by   UUID REFERENCES users(id),
  raw_json      JSONB NOT NULL,
  skill_id      TEXT,
  skill_version TEXT,
  provenance    JSONB NOT NULL DEFAULT '{}',
  providers     JSONB NOT NULL DEFAULT '{}',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (briefing_id, version)
);

CREATE TABLE script_beats (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  script_id     UUID NOT NULL REFERENCES script_versions(id) ON DELETE CASCADE,
  ord           INT NOT NULL,
  kind          TEXT NOT NULL,
  text          TEXT NOT NULL,
  visual        JSONB,
  UNIQUE (script_id, ord)
);

CREATE TABLE citations (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  beat_id         UUID NOT NULL REFERENCES script_beats(id) ON DELETE CASCADE,
  asset_id        UUID NOT NULL REFERENCES source_assets(id),
  kind            citation_kind NOT NULL,
  t_start_ms      INT,
  t_end_ms        INT,
  sheet           TEXT,
  addr            TEXT,
  block_id        TEXT,
  page            INT,
  range_ref       TEXT
);
CREATE INDEX citations_beat ON citations (beat_id);

CREATE TABLE claims (
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
CREATE INDEX claims_beat ON claims (beat_id);

CREATE TABLE artifacts (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  briefing_id   UUID NOT NULL REFERENCES briefings(id) ON DELETE CASCADE,
  kind          TEXT NOT NULL,
  minio_key     TEXT NOT NULL,
  sha256        TEXT NOT NULL,
  bytes         BIGINT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE chapters (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  briefing_id   UUID NOT NULL REFERENCES briefings(id) ON DELETE CASCADE,
  ord           INT NOT NULL,
  title         TEXT NOT NULL,
  t_start_ms    INT,
  t_end_ms      INT,
  beat_id       UUID REFERENCES script_beats(id)
);

CREATE TABLE embedding_chunks (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  briefing_id   UUID NOT NULL REFERENCES briefings(id) ON DELETE CASCADE,
  asset_id      UUID REFERENCES source_assets(id) ON DELETE CASCADE,
  kind          TEXT NOT NULL,
  text          TEXT NOT NULL,
  span          JSONB NOT NULL,
  model         TEXT NOT NULL DEFAULT 'sha256-bag-768',
  dims          INT NOT NULL DEFAULT 768,
  embedding     VECTOR NOT NULL
);
CREATE INDEX embedding_chunks_briefing ON embedding_chunks (briefing_id);
CREATE INDEX embedding_chunks_768 ON embedding_chunks
  USING hnsw ((embedding::vector(768)) vector_cosine_ops) WHERE dims = 768;
CREATE INDEX embedding_chunks_1024 ON embedding_chunks
  USING hnsw ((embedding::vector(1024)) vector_cosine_ops) WHERE dims = 1024;

CREATE TABLE chat_sessions (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  briefing_id   UUID NOT NULL REFERENCES briefings(id) ON DELETE CASCADE,
  user_id       UUID NOT NULL REFERENCES users(id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE chat_messages (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id    UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role          TEXT NOT NULL,
  text          TEXT NOT NULL,
  citation_ids  UUID[] NOT NULL DEFAULT '{}',
  citations     JSONB NOT NULL DEFAULT '[]',
  provider      TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE jobs (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  briefing_id   UUID REFERENCES briefings(id) ON DELETE CASCADE,
  type          job_type NOT NULL,
  state         job_state NOT NULL DEFAULT 'queued',
  model_ids     JSONB NOT NULL DEFAULT '{}',
  error         TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at    TIMESTAMPTZ,
  finished_at   TIMESTAMPTZ
);

CREATE TABLE audit_events (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  actor_id      UUID REFERENCES users(id),
  workspace_id  UUID REFERENCES workspaces(id),
  action        TEXT NOT NULL,
  entity_type   TEXT NOT NULL,
  entity_id     UUID,
  meta          JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX audit_events_at ON audit_events (at);
