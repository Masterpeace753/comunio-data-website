CREATE TABLE IF NOT EXISTS teams (
    id BIGSERIAL PRIMARY KEY,
    comunio_team_id BIGINT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    league TEXT,
    season TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS players (
    id BIGSERIAL PRIMARY KEY,
    comunio_player_id BIGINT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    position TEXT NOT NULL CHECK (position IN ('TW','ABW','MITT','ST')),
    team_id BIGINT REFERENCES teams(id),
    source TEXT NOT NULL DEFAULT 'comuniopy',
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ingest_runs (
    id BIGSERIAL PRIMARY KEY,
    run_type TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    records_written INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_players_team_id ON players(team_id);
CREATE INDEX IF NOT EXISTS idx_players_comunio_player_id ON players(comunio_player_id);
CREATE INDEX IF NOT EXISTS idx_ingest_runs_started_at ON ingest_runs(started_at DESC);
