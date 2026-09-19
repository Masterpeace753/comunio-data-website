CREATE TABLE IF NOT EXISTS market_values (
    id BIGSERIAL PRIMARY KEY,
    player_id BIGINT NOT NULL REFERENCES players(id),
    snapshot_date DATE NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL,
    value_eur BIGINT NOT NULL CHECK (value_eur >= 0),
    source TEXT NOT NULL DEFAULT 'comuniopy',
    ingest_run_id BIGINT REFERENCES ingest_runs(id),
    UNIQUE (player_id, snapshot_date)
);

CREATE TABLE IF NOT EXISTS player_points (
    id BIGSERIAL PRIMARY KEY,
    player_id BIGINT NOT NULL REFERENCES players(id),
    season TEXT NOT NULL,
    matchday INTEGER NOT NULL CHECK (matchday > 0),
    points INTEGER NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source TEXT NOT NULL DEFAULT 'comuniopy',
    UNIQUE (player_id, season, matchday)
);

CREATE TABLE IF NOT EXISTS transfermarket_snapshots (
    id BIGSERIAL PRIMARY KEY,
    player_id BIGINT NOT NULL REFERENCES players(id),
    snapshot_date DATE NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL,
    listed BOOLEAN NOT NULL,
    price_eur BIGINT CHECK (price_eur >= 0),
    owner_name TEXT,
    ingest_run_id BIGINT REFERENCES ingest_runs(id),
    UNIQUE (player_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_market_values_player_date ON market_values(player_id, snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_market_values_date ON market_values(snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_player_points_player_matchday ON player_points(player_id, season, matchday);
CREATE INDEX IF NOT EXISTS idx_transfermarket_player_date ON transfermarket_snapshots(player_id, snapshot_date DESC);
