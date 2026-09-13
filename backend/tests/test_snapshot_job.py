from __future__ import annotations

from dataclasses import dataclass, field

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