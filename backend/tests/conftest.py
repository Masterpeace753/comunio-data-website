from __future__ import annotations

import os
from pathlib import Path

import psycopg2
import pytest


@pytest.fixture(scope="session")
def postgres_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    return database_url


@pytest.fixture(scope="session")
def migrated_postgres(postgres_database_url: str):
    connection = psycopg2.connect(postgres_database_url)
    connection.autocommit = True
    migrations_dir = Path(__file__).resolve().parents[1] / "migrations"
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        for migration_path in sorted(migrations_dir.glob("*.sql")):
            if not migration_path.name[0].isdigit():
                continue
            cursor.execute(migration_path.read_text(encoding="utf-8"))
            cursor.execute(
                "INSERT INTO schema_migrations(name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                (migration_path.name,),
            )
    yield connection
    connection.close()


@pytest.fixture
def postgres_connection(migrated_postgres):
    with migrated_postgres.cursor() as cursor:
        cursor.execute(
            """
            TRUNCATE TABLE
                audit_log,
                availability_events,
                transfermarket_snapshots,
                player_points,
                market_values,
                players,
                teams,
                ingest_runs
            RESTART IDENTITY CASCADE
            """
        )
    return migrated_postgres


@pytest.fixture
def seeded_postgres(postgres_connection):
    with postgres_connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO teams (comunio_team_id, name, league, season)
            VALUES (2001, 'Test Team', 'Test League', '2026')
            RETURNING id
            """
        )
        team_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO players (comunio_player_id, name, position, team_id)
            VALUES (1001, 'Test Player', 'MITT', %s), (1002, 'No History', 'ST', NULL)
            RETURNING id
            """,
            (team_id,),
        )
        player_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO market_values (player_id, snapshot_date, captured_at, value_eur)
            VALUES
                (%s, '2026-01-01', '2026-01-01T06:00:00Z', 0),
                (%s, '2026-01-02', '2026-01-02T06:00:00Z', 1000),
                (%s, '2026-01-04', '2026-01-04T06:00:00Z', 900)
            """,
            (player_id, player_id, player_id),
        )
        cursor.execute(
            """
            INSERT INTO transfermarket_snapshots
                (player_id, snapshot_date, captured_at, listed, price_eur, owner_name)
            VALUES (%s, '2026-01-04', '2026-01-04T06:00:00Z', TRUE, 900, NULL)
            """,
            (player_id,),
        )
    postgres_connection.commit()
    return {"team_id": team_id, "player_id": player_id}
