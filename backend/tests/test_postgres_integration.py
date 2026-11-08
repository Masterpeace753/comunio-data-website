from __future__ import annotations

import secrets
from datetime import date
from pathlib import Path

import bcrypt
import pytest
from fastapi.testclient import TestClient

import src.api.app as api_app
from src.api import auth
from src.api.dependencies import get_db_connection
from src.api import repositories


pytestmark = pytest.mark.integration


AUTH_CONFIG = auth.AuthConfig(
    username="test-user",
    password_hash=bcrypt.hashpw(b"unused", bcrypt.gensalt(rounds=4)),
    jwt_secret=secrets.token_urlsafe(48),
)


def _client(connection, monkeypatch) -> TestClient:
    api_app.app.dependency_overrides[get_db_connection] = lambda: connection
    monkeypatch.setattr(auth, "get_auth_config", lambda: AUTH_CONFIG)
    test_client = TestClient(api_app.app, base_url="https://testserver")
    test_client.cookies.set(
        auth.TOKEN_COOKIE_NAME,
        auth.create_access_token(AUTH_CONFIG.username, AUTH_CONFIG.jwt_secret),
        path="/",
    )
    return test_client


def test_migrations_and_ap12_history_run_against_postgres(seeded_postgres, postgres_connection, monkeypatch) -> None:
    test_client = _client(postgres_connection, monkeypatch)
    try:
        response = test_client.get("/api/v1/players/1/history")
    finally:
        api_app.app.dependency_overrides.clear()

    assert response.status_code == 200
    items = {item["snapshot_date"]: item for item in response.json()["items"]}
    assert items["2026-01-04"]["previous_snapshot_date"] is None
    assert items["2026-01-01"]["delta_first_eur"] == 0
    assert items["2026-01-02"]["delta_first_eur"] == 1000
    assert items["2026-01-04"]["delta_first_eur"] == 900
    assert items["2026-01-04"]["percent_delta_first"] is None


def test_ingest_runs_pagination_order_and_current_data_date(
    seeded_postgres, postgres_connection, monkeypatch
) -> None:
    with postgres_connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO ingest_runs
                (run_type, status, started_at, finished_at, records_written, stage, error_code, error_message)
            VALUES
                ('manual', 'success', '2026-01-05T06:00:00Z', '2026-01-05T06:01:00Z', 2, 'snapshot', NULL, NULL),
                ('scheduled', 'failed', '2026-01-05T06:00:00Z', '2026-01-05T06:01:00Z', 0, 'snapshot', 'snapshot_fetch_failed', 'private upstream error'),
                ('scheduled', 'started', '2026-01-04T06:00:00Z', NULL, 0, 'login', NULL, NULL)
            """
        )
    postgres_connection.commit()
    test_client = _client(postgres_connection, monkeypatch)
    try:
        response = test_client.get("/api/v1/ingest/runs?limit=2&offset=0")
        stale = test_client.get("/api/v1/ingest/runs?limit=1&offset=2")
    finally:
        api_app.app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["current_data_date"] == "2026-01-04"
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert [item["status"] for item in body["items"]] == ["failed", "success"]
    assert [item["id"] for item in body["items"]] == sorted(
        [item["id"] for item in body["items"]], reverse=True
    )
    assert body["items"][0]["error_code"] == "snapshot_fetch_failed"
    assert "private upstream error" not in response.text
    assert "error_message" not in response.text
    assert stale.status_code == 200
    assert stale.json()["items"][0]["status"] == "started"


def test_postgres_repositories_cover_lists_and_empty_history(seeded_postgres, postgres_connection) -> None:
    player_id = seeded_postgres["player_id"]
    players, total = repositories.list_players(postgres_connection, 25, 0, None, None, None)
    teams, team_total = repositories.list_teams(postgres_connection, 25, 0, None, None, None)
    transfermarket, transfer_total, latest = repositories.list_transfermarket(postgres_connection, 25, 0, None, None)
    empty_history = repositories.get_player_history(postgres_connection, seeded_postgres["player_id"] + 1, None, None, 90)

    assert players and total == 2
    assert teams and team_total == 1
    assert transfermarket and transfer_total == 1
    assert latest == date(2026, 1, 4)
    assert empty_history == []
    assert player_id > 0


def test_migrations_are_idempotent(migrated_postgres) -> None:
    migrations_dir = Path(__file__).resolve().parents[1] / "migrations"
    with migrated_postgres.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM schema_migrations")
        migration_count_before = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
        table_count_before = cursor.fetchone()[0]

        for migration_path in sorted(migrations_dir.glob("*.sql")):
            cursor.execute(migration_path.read_text(encoding="utf-8"))

        cursor.execute("SELECT COUNT(*) FROM schema_migrations")
        assert cursor.fetchone()[0] == migration_count_before
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
        assert cursor.fetchone()[0] == table_count_before
