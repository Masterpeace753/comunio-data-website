from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import src.api.app as api_app
from src.api.dependencies import get_db_connection
from src.api import repositories


pytestmark = pytest.mark.integration


def _client(connection) -> TestClient:
    api_app.app.dependency_overrides[get_db_connection] = lambda: connection
    return TestClient(api_app.app)


def test_migrations_and_ap12_history_run_against_postgres(seeded_postgres, postgres_connection) -> None:
    test_client = _client(postgres_connection)
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
