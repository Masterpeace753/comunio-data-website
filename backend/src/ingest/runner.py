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


# AP-10a: fixed, closed taxonomy so `detail=` never leaks raw exception text
# (HTTP response bodies, DSNs, tokens) into CloudWatch logs.
_SAFE_DETAIL_BY_STAGE: dict[str, str] = {
    "login": "authentication_failed",
    "snapshot": "snapshot_fetch_failed",
    "persistence": "database_persistence_failed",
}
_DEFAULT_SAFE_DETAIL = "unexpected_error"


def _safe_detail(stage: str) -> str:
    return _SAFE_DETAIL_BY_STAGE.get(stage, _DEFAULT_SAFE_DETAIL)


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


def _login_with_retry(
    client: ComunioPyClient,
    max_attempts: int,
    wait_seconds: int,
    sleep_fn=time.sleep,
) -> None:
    """AP-9.2: detect login failures and retry the whole run every `wait_seconds`.

    After `max_attempts` failed logins the caller ends the run the same way a
    successful run ends (process exit); ECS stops the one-off Fargate task
    identically in both cases, so no extra shutdown step is required here.
    """
    last_error: ComunioLoginError | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            client.login()
            if attempt > 1:
                _log("login_recovered", attempt=attempt, max_attempts=max_attempts)
            return
        except ComunioLoginError as exc:
            last_error = exc
            _log(
                "login_attempt_failed",
                attempt=attempt,
                max_attempts=max_attempts,
                error_code=_error_code(exc),
            )
            if attempt >= max_attempts:
                break
            _log("login_retry_scheduled", attempt=attempt + 1, max_attempts=max_attempts, wait_seconds=wait_seconds)
            sleep_fn(wait_seconds)

    raise ComunioLoginError(f"Login failed after {max_attempts} attempts: {last_error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AP-5/AP-7 manual ingest runner")
    parser.add_argument("--run-type", default="manual", choices=["manual", "scheduled"], help="manual or EventBridge scheduled run")
    parser.add_argument(
        "--mode",
        default="snapshot",
        choices=["login", "snapshot"],
        help="login validates credentials only, snapshot executes AP-7 manual snapshot pipeline",
    )
    args = parser.parse_args(argv)

    _log("run_started", run_type=args.run_type, mode=args.mode)

    settings = load_settings()
    client = ComunioPyClient(settings)

    try:
        _login_with_retry(client, settings.login_retry_attempts, settings.login_retry_wait_seconds)
    except ComunioLoginError as exc:
        _log(
            "run_failed",
            stage="login",
            error_code=_error_code(exc),
            attempts=settings.login_retry_attempts,
            detail=_safe_detail("login"),
        )
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
        _log("run_failed", stage="snapshot", error_code=_error_code(exc), detail=_safe_detail("snapshot"))
        return 1

    try:
        conn = connect(settings.database_url)
        try:
            run_id, records_written = run_manual_snapshot(conn, normalized_snapshot, run_type=args.run_type)
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
        _log("run_failed", stage="persistence", error_code=_error_code(exc), detail=_safe_detail("persistence"))
        return 1

    _log("run_success", stage="snapshot", run_id=run_id, records_written=records_written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
