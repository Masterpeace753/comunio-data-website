from __future__ import annotations

import argparse
import time
import sys

from src.config import load_settings
from src.database.connection import connect
from src.ingest.comuniopy_client import ComunioLoginError, ComunioPyClient, ComunioSnapshotError
from src.ingest.snapshot_job import run_manual_snapshot


def _log(event: str, **fields: object) -> None:
    payload = " ".join(f"{k}={v}" for k, v in fields.items())
    if payload:
        print(f"[INGEST] event={event} {payload}")
        return
    print(f"[INGEST] event={event}")


def _error_code(exc: Exception) -> str:
    return exc.__class__.__name__.lower()


def _fetch_with_backoff(client: ComunioPyClient, attempts: int = 4) -> dict:
    delays = [2, 4, 8]
    last_error: Exception | None = None

    for idx in range(attempts):
        try:
            return client.fetch_snapshot()
        except ComunioSnapshotError as exc:
            last_error = exc
            if idx >= attempts - 1:
                break
            delay = delays[min(idx, len(delays) - 1)]
            _log("snapshot_retry", retry=idx + 1, wait_seconds=delay, error_code=_error_code(exc))
            time.sleep(delay)

    raise ComunioSnapshotError(f"Snapshot fetch failed after {attempts} attempts: {last_error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AP-5/AP-7 manual ingest runner")
    parser.add_argument("--run-type", default="manual", choices=["manual"], help="Only manual is in scope")
    parser.add_argument(
        "--mode",
        default="snapshot",
        choices=["login", "snapshot"],
        help="login validates credentials only, snapshot executes AP-7 manual snapshot pipeline",
    )
    args = parser.parse_args(argv)

    _ = args.run_type
    _log("run_started", run_type="manual", mode=args.mode)

    settings = load_settings()
    client = ComunioPyClient(settings)

    try:
        client.login()
    except ComunioLoginError as exc:
        _log("run_failed", stage="login", error_code=_error_code(exc), detail=str(exc))
        return 1

    if args.mode == "login":
        _log("run_success", stage="login", message="login_validated")
        return 0

    if not settings.database_url:
        _log("run_failed", stage="config", error_code="missing_database_url")
        return 1

    try:
        raw_snapshot = _fetch_with_backoff(client)
        normalized_snapshot = client.normalize_snapshot(raw_snapshot)
    except ComunioSnapshotError as exc:
        _log("run_failed", stage="snapshot", error_code=_error_code(exc), detail=str(exc))
        return 1

    try:
        conn = connect(settings.database_url)
        try:
            run_id, records_written = run_manual_snapshot(conn, normalized_snapshot)
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM ingest_runs")
                ingest_runs_count = int(cur.fetchone()[0])
                cur.execute("SELECT COUNT(*) FROM market_values")
                market_values_count = int(cur.fetchone()[0])
            _log(
                "db_verify",
                run_id=run_id,
                records_written=records_written,
                ingest_runs_count=ingest_runs_count,
                market_values_count=market_values_count,
            )
        finally:
            conn.close()
    except Exception as exc:
        _log("run_failed", stage="persistence", error_code=_error_code(exc), detail=str(exc))
        return 1

    _log("run_success", stage="snapshot", run_id=run_id, records_written=records_written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
