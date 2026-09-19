CREATE TABLE IF NOT EXISTS availability_events (
    id BIGSERIAL PRIMARY KEY,
    player_id BIGINT NOT NULL REFERENCES players(id),
    event_type TEXT NOT NULL,
    event_at TIMESTAMPTZ NOT NULL,
    payload JSONB
);

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    record_id BIGINT NOT NULL,
    old_value JSONB,
    new_value JSONB,
    changed_by TEXT NOT NULL DEFAULT 'system',
    changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_availability_events_player_event_at ON availability_events(player_id, event_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_table_changed_at ON audit_log(table_name, changed_at DESC);
