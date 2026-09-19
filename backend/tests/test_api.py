from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

import src.api.app as api_app
from src.api.dependencies import get_db_connection
from src.api.errors import ResourceNotFoundError


class ReadyConnection:
    def cursor(self):
        return ReadyCursor()


class ReadyCursor:
    def __enter__(self) -> "ReadyCursor":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def execute(self, query: str, parameters: tuple = ()) -> None:
        assert query == "SELECT 1"

    def fetchone(self) -> tuple[int]:
        return (1,)


def client(monkeypatch) -> TestClient:
    api_app.app.dependency_overrides[get_db_connection] = lambda: ReadyConnection()
    monkeypatch.setattr(api_app, "get_db_connection", lambda: ReadyConnection())
    return TestClient(api_app.app)


def test_live_health_does_not_require_database(monkeypatch) -> None:
    test_client = client(monkeypatch)

    try:
        response = test_client.get("/health/live")
    finally:
        api_app.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_health_checks_database(monkeypatch) -> None:
    test_client = client(monkeypatch)

    try:
        response = test_client.get("/health/ready")
    finally:
        api_app.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_players_returns_typed_page(monkeypatch) -> None:
    test_client = client(monkeypatch)
    monkeypatch.setattr(
        api_app.repositories,
        "list_players",
        lambda *args: ([(1, 1001, "Max", "MITT", None, None, 1250000)], 1),
    )

    try:
        response = test_client.get("/api/v1/players?limit=10&search=Max")
    finally:
        api_app.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": 1,
                "comunio_player_id": 1001,
                "name": "Max",
                "position": "MITT",
                "team_id": None,
                "team_name": None,
                "current_value_eur": 1250000,
            }
        ],
        "limit": 10,
        "offset": 0,
        "total": 1,
    }


def test_player_history_rejects_reversed_date_range(monkeypatch) -> None:
    test_client = client(monkeypatch)

    try:
        response = test_client.get("/api/v1/players/1/history?from_date=2026-02-01&to_date=2026-01-01")
    finally:
        api_app.app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_date_range"


def test_unknown_player_returns_sanitized_404(monkeypatch) -> None:
    test_client = client(monkeypatch)
    monkeypatch.setattr(api_app.repositories, "get_player", lambda *args: (_ for _ in ()).throw(ResourceNotFoundError("player_not_found")))

    try:
        response = test_client.get("/api/v1/players/999")
    finally:
        api_app.app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"code": "player_not_found", "message": "Resource not found."}


def test_invalid_pagination_is_rejected(monkeypatch) -> None:
    test_client = client(monkeypatch)

    try:
        response = test_client.get("/api/v1/players?limit=101")
    finally:
        api_app.app.dependency_overrides.clear()

    assert response.status_code == 422


def test_player_history_maps_dates(monkeypatch) -> None:
    test_client = client(monkeypatch)
    captured_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(
        api_app.repositories,
        "get_player_history",
        lambda *args: [(
            date(2026, 1, 1),
            captured_at,
            1250000,
            None,
            None,
            None,
            date(2026, 1, 1),
            1250000,
            0,
            None,
            0.0,
        )],
    )

    try:
        response = test_client.get("/api/v1/players/1/history")
    finally:
        api_app.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"][0]["value_eur"] == 1250000
    assert response.json()["items"][0]["delta_first_eur"] == 0
    assert response.json()["items"][0]["delta_previous_day_eur"] is None


def test_player_history_returns_delta_projection(monkeypatch) -> None:
    test_client = client(monkeypatch)
    captured_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    monkeypatch.setattr(
        api_app.repositories,
        "get_player_history",
        lambda *args: [(
            date(2026, 1, 2),
            captured_at,
            1100,
            date(2026, 1, 1),
            1000,
            100,
            date(2026, 1, 1),
            1000,
            100,
            10.0,
            10.0,
        )],
    )

    try:
        response = test_client.get("/api/v1/players/1/history")
    finally:
        api_app.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"][0] == {
        "snapshot_date": "2026-01-02",
        "captured_at": "2026-01-02T00:00:00Z",
        "value_eur": 1100,
        "previous_snapshot_date": "2026-01-01",
        "previous_value_eur": 1000,
        "delta_previous_day_eur": 100,
        "first_snapshot_date": "2026-01-01",
        "first_value_eur": 1000,
        "delta_first_eur": 100,
        "percent_delta_previous_day": 10.0,
        "percent_delta_first": 10.0,
    }


def test_player_history_preserves_null_reference_deltas(monkeypatch) -> None:
    test_client = client(monkeypatch)
    captured_at = datetime(2026, 1, 3, tzinfo=timezone.utc)
    monkeypatch.setattr(
        api_app.repositories,
        "get_player_history",
        lambda *args: [(
            date(2026, 1, 3),
            captured_at,
            900,
            None,
            None,
            None,
            date(2026, 1, 1),
            1000,
            -100,
            None,
            -10.0,
        )],
    )

    try:
        response = test_client.get("/api/v1/players/1/history")
    finally:
        api_app.app.dependency_overrides.clear()

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["delta_previous_day_eur"] is None
    assert item["percent_delta_previous_day"] is None
    assert item["delta_first_eur"] == -100
    assert item["percent_delta_first"] == -10.0


def test_teams_returns_player_count(monkeypatch) -> None:
    test_client = client(monkeypatch)
    monkeypatch.setattr(
        api_app.repositories,
        "list_teams",
        lambda *args: ([(2, 2002, "Team", "Community", "2026", 3)], 1),
    )

    try:
        response = test_client.get("/api/v1/teams")
    finally:
        api_app.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"][0]["player_count"] == 3


def test_transfermarket_returns_valid_empty_page_when_not_ingested(monkeypatch) -> None:
    test_client = client(monkeypatch)
    monkeypatch.setattr(api_app.repositories, "list_transfermarket", lambda *args: ([], 0, None))

    try:
        response = test_client.get("/api/v1/transfermarket")
    finally:
        api_app.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"items": [], "snapshot_date": None, "limit": 25, "offset": 0, "total": 0}