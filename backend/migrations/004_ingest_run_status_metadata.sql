ALTER TABLE ingest_runs
    ADD COLUMN IF NOT EXISTS stage TEXT,
    ADD COLUMN IF NOT EXISTS error_code TEXT;

CREATE INDEX IF NOT EXISTS idx_ingest_runs_started_id
    ON ingest_runs(started_at DESC, id DESC);
