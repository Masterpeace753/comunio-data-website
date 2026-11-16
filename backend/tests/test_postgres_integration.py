from __future__ import annotations

import secrets
from datetime import UTC, date, datetime
from pathlib import Path

import bcrypt
import psycopg2
import pytest
from fastapi.testclient import TestClient

import src.api.app as api_app
from src.api import auth
from src.api.dependencies import get_db_connection
from src.api import repositories
from src.ingest import snapshot_job
from src.ingest.snapshot_job import _upsert_player_points, _upsert_players, _upsert_teams, run_manual_snapshot
from migrations import runner as migration_runner


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


def test_players_can_be_ordered_by_first_database_insert(seeded_postgres, postgres_connection, monkeypatch) -> None:
    player_id = seeded_postgres["player_id"]
    with postgres_connection.cursor() as cursor:
        cursor.execute(
            "UPDATE players SET first_seen_at = CASE WHEN id = %s THEN %s ELSE %s END",
            (player_id, datetime(2026, 1, 2, tzinfo=UTC), datetime(2026, 1, 1, tzinfo=UTC)),
        )
    postgres_connection.commit()
    test_client = _client(postgres_connection, monkeypatch)
    try:
        newest = test_client.get("/api/v1/players?limit=2&sort=newest")
        default = test_client.get("/api/v1/players?limit=2")
    finally:
        api_app.app.dependency_overrides.clear()

    assert newest.status_code == 200
    assert [player["name"] for player in newest.json()["items"]] == ["Test Player", "No History"]
    assert default.status_code == 200
    assert [player["name"] for player in default.json()["items"]] == ["No History", "Test Player"]


def test_player_club_and_owner_persist_and_update(postgres_connection, monkeypatch) -> None:
    teams = _upsert_teams(postgres_connection, [
        {"comunio_team_id": 99, "name": "Mein Team"},
    ])
    players = [{"comunio_player_id": 1, "name": "Spieler", "position": "ST",
                "team_comunio_id": 99, "club_name": "FC Bayern", "total_points": 18}]
    player_id = _upsert_players(postgres_connection, players, teams)[1]
    test_client = _client(postgres_connection, monkeypatch)
    try:
        player = test_client.get(f"/api/v1/players/{player_id}").json()
        roster = test_client.get(f"/api/v1/players?team_id={teams[99]}").json()
        assert player["club_name"] == "FC Bayern"
        assert player["total_points"] == 18
        assert player["team_name"] == "Mein Team"
        assert roster["items"][0]["club_name"] == "FC Bayern"
        assert roster["items"][0]["total_points"] == 18
        assert test_client.get(f"/api/v1/teams/{teams[99]}").json()["player_count"] == 1

        players[0].update(team_comunio_id=None, club_name=None)
        _upsert_players(postgres_connection, players, teams)
        player = test_client.get(f"/api/v1/players/{player_id}").json()
        assert player["team_name"] is None
        assert player["club_name"] is None
        assert test_client.get(f"/api/v1/teams/{teams[99]}").json()["player_count"] == 0
    finally:
        api_app.app.dependency_overrides.clear()


def test_matchday_points_upsert_and_repository(seeded_postgres, postgres_connection) -> None:
    player_id = seeded_postgres["player_id"]
    players = [{"comunio_player_id": 1001, "last_points": 0}]
    mapping = {1001: player_id}
    def capture(at: datetime) -> None:
        _upsert_player_points(postgres_connection, players, mapping, at, at, "scheduled")

    capture(datetime(2026, 8, 31, 6, tzinfo=UTC))
    assert repositories.get_player_points(postgres_connection, player_id, "2026/27") == [(1, 0)]
    players[0]["last_points"] = -2
    capture(datetime(2026, 9, 1, 6, tzinfo=UTC))
    players[0]["last_points"] = None
    capture(datetime(2026, 9, 2, 6, tzinfo=UTC))
    players[0]["last_points"] = 99
    capture(datetime(2026, 8, 31, 6, tzinfo=UTC))
    capture(datetime(2026, 9, 4, 6, tzinfo=UTC))
    assert repositories.get_player_points(postgres_connection, player_id, "2026/27") == [(1, -2)]
    players[0]["last_points"] = 5
    capture(datetime(2027, 1, 15, 6, tzinfo=UTC))
    capture(datetime(2027, 3, 5, 6, tzinfo=UTC))
    capture(datetime(2027, 1, 15, 7, tzinfo=UTC))
    assert sorted(repositories.get_player_points(postgres_connection, player_id, "2026/27")) == [(1, -2), (16, 5), (24, 5)]


def test_snapshot_persists_points_when_capture_window_is_safe(postgres_connection, monkeypatch) -> None:
    captured_at = datetime(2026, 8, 31, 6, tzinfo=UTC)
    monkeypatch.setattr(snapshot_job, "matchday_for_capture", lambda start, end, run_type: 1)
    snapshot = {
        "players": [{"comunio_player_id": 1001, "name": "Spieler", "position": "ST", "total_points": 5, "last_points": 5}],
        "teams": [],
        "market_values": [{"comunio_player_id": 1001, "value_eur": 1000}],
    }
    _, written = run_manual_snapshot(postgres_connection, snapshot, captured_at=captured_at)
    with postgres_connection.cursor() as cursor:
        cursor.execute("SELECT id, total_points FROM players WHERE comunio_player_id = 1001")
        player_id, total_points = cursor.fetchone()
    assert written == 1
    assert total_points == 5
    assert repositories.get_player_points(postgres_connection, player_id, "2026/27") == [(1, 5)]


def test_total_points_migration_upgrades_existing_database(
    seeded_postgres, postgres_connection, postgres_database_url, monkeypatch
) -> None:
    with postgres_connection.cursor() as cursor:
        cursor.execute("ALTER TABLE players DROP COLUMN total_points")
        cursor.execute("DELETE FROM schema_migrations WHERE name = '006_player_total_points.sql'")
    monkeypatch.setattr(migration_runner, "connect", lambda _url: psycopg2.connect(postgres_database_url))

    migration_runner.run()
    migration_runner.run()

    with postgres_connection.cursor() as cursor:
        cursor.execute("SELECT name, total_points FROM players WHERE id = %s", (seeded_postgres["player_id"],))
        assert cursor.fetchone() == ("Test Player", None)
        cursor.execute("SELECT COUNT(*) FROM schema_migrations WHERE name = '006_player_total_points.sql'")
        assert cursor.fetchone() == (1,)


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
