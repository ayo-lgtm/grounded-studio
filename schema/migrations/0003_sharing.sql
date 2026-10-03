-- Viewer sharing: per-briefing grants and company-wide watch links.
-- Idempotent; applied on every API start.

ALTER TABLE briefings ADD COLUMN IF NOT EXISTS visibility TEXT NOT NULL DEFAULT 'workspace';

CREATE TABLE IF NOT EXISTS briefing_grants (
  briefing_id   UUID NOT NULL REFERENCES briefings(id) ON DELETE CASCADE,
  email         TEXT NOT NULL,
  role          TEXT NOT NULL DEFAULT 'viewer',
  granted_by    UUID REFERENCES users(id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (briefing_id, email)
);
CREATE INDEX IF NOT EXISTS briefing_grants_email ON briefing_grants (email);
