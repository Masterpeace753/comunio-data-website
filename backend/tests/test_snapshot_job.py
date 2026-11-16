from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from unittest.mock import Mock

from src.config import load_settings
from src.ingest.comuniopy_client import ComunioPyClient
import src.ingest.snapshot_job as snapshot_job
from src.ingest.snapshot_job import _upsert_market_values


@dataclass
class FakeDatabase:
    market_values: dict[tuple[int, str], tuple[int, int]] = field(default_factory=dict)

    def cursor(self):
        return FakeCursor(self)


class FakeCursor:
    def __init__(self, database: FakeDatabase) -> None:
        self.database = database

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def execute(self, query: str, parameters: tuple) -> None:
        assert "ON CONFLICT (player_id, snapshot_date)" in query
        player_id, snapshot_date, _captured_at, value_eur, ingest_run_id = parameters
        self.database.market_values[(player_id, str(snapshot_date))] = (value_eur, ingest_run_id)


def test_repeated_snapshot_updates_same_market_value_key_without_duplicate() -> None:
    database = FakeDatabase()
    market_values = [{"comunio_player_id": 1001, "value_eur": 1_250_000}]
    player_map = {1001: 7}

    first_written = _upsert_market_values(database, market_values, player_map, run_id=11)
    second_written = _upsert_market_values(database, market_values, player_map, run_id=12)

    assert first_written == 1
    assert second_written == 1
    assert len(database.market_values) == 1
    assert next(iter(database.market_values.values())) == (1_250_000, 12)


def test_market_value_snapshot_date_uses_utc_calendar_date(monkeypatch) -> None:
    database = FakeDatabase()
    real_datetime = datetime

    class FixedDateTime:
        @staticmethod
        def now(tz):
            assert tz is UTC
            return real_datetime(2026, 1, 2, 0, 30, tzinfo=UTC)

    monkeypatch.setattr(snapshot_job.dt, "datetime", FixedDateTime)
    _upsert_market_values(database, [{"comunio_player_id": 1001, "value_eur": 500}], {1001: 7}, run_id=13)

    assert (7, "2026-01-02") in database.market_values


def test_live_snapshot_separates_club_from_comunio_owner(monkeypatch) -> None:
    monkeypatch.delenv("COMUNIO_SNAPSHOT_FILE", raising=False)
    client = ComunioPyClient(load_settings())
    response = Mock(status_code=200)
    response.json.return_value = {
        "totalHits": 2,
        "tradables": [
            {"id": 1, "name": "Spieler", "position": "STRIKER",
             "club": {"id": 42, "name": "FC Bayern"},
             "owner": {"id": 99, "name": "Mein Team"}, "quotedprice": 1000},
            {"id": 2, "name": "Frei", "position": "KEEPER",
             "club": {"id": 99, "name": "Anderer Club"}, "owner": None},
        ],
    }
    client._session = Mock()
    client._session.get.return_value = response
    client._community_id = "1"

    snapshot = client.normalize_snapshot(client.fetch_snapshot())

    assert snapshot["teams"][0]["comunio_team_id"] == 99
    assert snapshot["players"][0]["club_name"] == "FC Bayern"
    assert snapshot["players"][0]["team_comunio_id"] == 99
    assert snapshot["players"][1]["club_name"] == "Anderer Club"
    assert snapshot["players"][1]["team_comunio_id"] is None