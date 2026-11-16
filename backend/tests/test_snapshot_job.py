from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock

import pytest

from src.config import load_settings
from src.ingest.comuniopy_client import ComunioPyClient, ComunioSnapshotError
import src.ingest.snapshot_job as snapshot_job
from src.ingest.snapshot_job import _upsert_market_values
from src.matchdays import MATCHDAYS, matchday_for_capture, safe_capture_date


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
             "owner": {"id": 99, "name": "Mein Team"}, "quotedprice": 1000, "points": "18", "lastPoints": "0"},
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
    assert snapshot["players"][0]["total_points"] == 18
    assert snapshot["players"][0]["last_points"] == 0
    assert snapshot["players"][1]["last_points"] is None
    assert snapshot["players"][1]["club_name"] == "Anderer Club"
    assert snapshot["players"][1]["team_comunio_id"] is None


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2026, 8, 30), None),
        (date(2026, 8, 31), 1),
        (date(2026, 9, 3), 1),
        (date(2026, 9, 4), None),
        (date(2027, 1, 14), None),
        (date(2027, 1, 15), 16),
        (date(2027, 1, 16), None),
        (date(2027, 3, 4), None),
        (date(2027, 3, 5), 24),
        (date(2027, 3, 6), None),
        (date(2027, 5, 23), 34),
        (date(2027, 5, 30), None),
    ],
)
def test_matchday_capture_windows(day: date, expected: int | None) -> None:
    capture = datetime(day.year, day.month, day.day, 6, tzinfo=UTC)
    assert matchday_for_capture(capture, capture, "scheduled") == expected


def test_complete_2026_27_calendar_and_next_day_capture() -> None:
    expected = [
        ("2026-08-28", "2026-08-30"), ("2026-09-04", "2026-09-06"),
        ("2026-09-11", "2026-09-13"), ("2026-09-18", "2026-09-20"),
        ("2026-10-09", "2026-10-11"), ("2026-10-16", "2026-10-18"),
        ("2026-10-23", "2026-10-25"), ("2026-10-30", "2026-11-01"),
        ("2026-11-06", "2026-11-08"), ("2026-11-20", "2026-11-22"),
        ("2026-11-27", "2026-11-29"), ("2026-12-04", "2026-12-06"),
        ("2026-12-11", "2026-12-13"), ("2026-12-18", "2026-12-20"),
        ("2027-01-08", "2027-01-10"), ("2027-01-12", "2027-01-14"),
        ("2027-01-15", "2027-01-17"), ("2027-01-22", "2027-01-24"),
        ("2027-01-29", "2027-01-31"), ("2027-02-05", "2027-02-07"),
        ("2027-02-12", "2027-02-14"), ("2027-02-19", "2027-02-21"),
        ("2027-02-26", "2027-02-28"), ("2027-03-02", "2027-03-04"),
        ("2027-03-05", "2027-03-07"), ("2027-03-12", "2027-03-14"),
        ("2027-03-19", "2027-03-21"), ("2027-04-02", "2027-04-04"),
        ("2027-04-09", "2027-04-11"), ("2027-04-16", "2027-04-18"),
        ("2027-04-23", "2027-04-25"), ("2027-05-07", "2027-05-09"),
        ("2027-05-14", "2027-05-16"), ("2027-05-22", "2027-05-22"),
    ]
    assert MATCHDAYS == tuple((date.fromisoformat(start), date.fromisoformat(end)) for start, end in expected)
    for matchday, (_, end) in enumerate(expected, 1):
        capture = datetime.fromisoformat(end).replace(hour=6, tzinfo=UTC) + timedelta(days=1)
        assert matchday_for_capture(capture, capture + timedelta(minutes=10), "scheduled") == matchday


@pytest.mark.parametrize("day", [date(2027, 1, 15), date(2027, 3, 5)])
def test_adjacent_matchdays_only_accept_scheduled_morning_capture(day: date) -> None:
    capture = datetime(day.year, day.month, day.day, 6, 15, tzinfo=UTC)
    assert matchday_for_capture(capture, capture, "manual") is None
    assert matchday_for_capture(capture, capture.replace(hour=7), "scheduled") is None
    assert matchday_for_capture(capture.replace(hour=5), capture, "scheduled") is None
    assert matchday_for_capture(capture.replace(hour=7), capture.replace(hour=7), "scheduled") is None


def test_capture_window_excludes_crossing_dates_and_german_midnight() -> None:
    start = datetime(2026, 8, 31, 6, tzinfo=UTC)
    assert safe_capture_date(start, datetime(2026, 8, 31, 21, 59, tzinfo=UTC)) == date(2026, 8, 31)
    assert safe_capture_date(start, datetime(2026, 8, 31, 22, tzinfo=UTC)) is None
    assert safe_capture_date(start, datetime(2026, 9, 1, 6, tzinfo=UTC)) is None
    assert safe_capture_date(start, datetime(2026, 8, 31, 5, tzinfo=UTC)) is None


@pytest.mark.parametrize("value", [True, 1.5, "1.5", "invalid"])
def test_invalid_points_are_rejected(value) -> None:
    with pytest.raises(ComunioSnapshotError, match="Invalid player points"):
        ComunioPyClient._normalize_points(value)


def test_live_snapshot_uses_start_pagination_to_fetch_all_players(monkeypatch) -> None:
    monkeypatch.delenv("COMUNIO_SNAPSHOT_FILE", raising=False)
    client = ComunioPyClient(load_settings())
    players = [
        {
            "id": player_id,
            "name": f"Spieler {player_id}",
            "position": "STRIKER",
            "owner": {"id": 99, "name": "Philipp"},
            "quotedprice": 1000,
        }
        for player_id in range(1, 540)
    ]
    responses = []
    for start in range(0, len(players), 100):
        response = Mock(status_code=200)
        response.json.return_value = {
            "totalHits": len(players),
            "tradables": players[start : start + 100],
        }
        responses.append(response)

    client._session = Mock()
    client._session.get.side_effect = responses
    client._community_id = "1"

    snapshot = client.fetch_snapshot()

    assert len(snapshot["players"]) == 539
    assert len(snapshot["market_values"]) == 539
    assert len(snapshot["teams"]) == 1
    assert all(player["team_comunio_id"] == 99 for player in snapshot["players"])
    assert [call.kwargs["params"]["start"] for call in client._session.get.call_args_list] == [
        0, 100, 200, 300, 400, 500
    ]
    assert all("offset" not in call.kwargs["params"] for call in client._session.get.call_args_list)


def test_live_snapshot_fails_when_pagination_repeats_a_full_page(monkeypatch) -> None:
    monkeypatch.delenv("COMUNIO_SNAPSHOT_FILE", raising=False)
    client = ComunioPyClient(load_settings())
    response = Mock(status_code=200)
    response.json.return_value = {
        "totalHits": 200,
        "tradables": [
            {"id": player_id, "name": f"Spieler {player_id}", "position": "STRIKER"}
            for player_id in range(1, 101)
        ],
    }

    client._session = Mock()
    client._session.get.side_effect = [response, response]
    client._community_id = "1"

    with pytest.raises(ComunioSnapshotError, match="page without new players"):
        client.fetch_snapshot()

    assert [call.kwargs["params"]["start"] for call in client._session.get.call_args_list] == [0, 100]
