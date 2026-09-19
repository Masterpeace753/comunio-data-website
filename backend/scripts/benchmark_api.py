from __future__ import annotations

import json
import os
import statistics
import time
from datetime import date

import psycopg2

from src.api import repositories


def percentile(values: list[float], percentile_rank: int) -> float:
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=100, method="inclusive")[percentile_rank - 1]


def measure(label: str, operation, warmup: int, iterations: int) -> dict[str, float | int | str]:
    for _ in range(warmup):
        operation()
    samples = []
    for _ in range(iterations):
        started = time.perf_counter()
        operation()
        samples.append((time.perf_counter() - started) * 1000)
    return {
        "operation": label,
        "iterations": iterations,
        "p50_ms": round(percentile(samples, 50), 2),
        "p95_ms": round(percentile(samples, 95), 2),
        "p99_ms": round(percentile(samples, 99), 2),
        "max_ms": round(max(samples), 2),
    }


def main() -> None:
    database_url = os.environ.get("TEST_DATABASE_URL")
    player_id = int(os.environ.get("BENCHMARK_PLAYER_ID", "1"))
    warmup = int(os.environ.get("BENCHMARK_WARMUP", "20"))
    iterations = int(os.environ.get("BENCHMARK_ITERATIONS", "200"))
    if not database_url:
        raise SystemExit("TEST_DATABASE_URL is required")

    connection = psycopg2.connect(database_url)
    try:
        results = [
            measure(
                "get_player_history",
                lambda: repositories.get_player_history(connection, player_id, date(2025, 1, 1), None, 366),
                warmup,
                iterations,
            ),
            measure(
                "list_players",
                lambda: repositories.list_players(connection, 100, 0, None, None, None),
                warmup,
                iterations,
            ),
            measure(
                "list_teams",
                lambda: repositories.list_teams(connection, 100, 0, None, None, None),
                warmup,
                iterations,
            ),
            measure(
                "list_transfermarket",
                lambda: repositories.list_transfermarket(connection, 100, 0, None, None),
                warmup,
                iterations,
            ),
        ]
        print(json.dumps({"database": "postgresql", "results": results}, indent=2))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
