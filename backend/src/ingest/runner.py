from __future__ import annotations

import argparse
import time
import sys

from src.config import load_settings
from src.database.connection import connect
from src.ingest.comuniopy_client import ComunioLoginError, ComunioPyClient, ComunioSnapshotError
from src.ingest.snapshot_job import run_manual_snapshot


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
            print(f"[INGEST] retry={idx + 1} wait_seconds={delay} reason={exc}")
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
    print("[INGEST] run_type=manual")

    settings = load_settings()
    client = ComunioPyClient(settings)

    try:
        client.login()
    except ComunioLoginError as exc:
        print(f"[INGEST] status=failed reason={exc}")
        return 1

    if args.mode == "login":
        print("[INGEST] status=success message=Login flow validated")
        return 0

    if not settings.database_url:
        print("[INGEST] status=failed reason=DATABASE_URL is required for snapshot mode")
        return 1

    try:
        raw_snapshot = _fetch_with_backoff(client)
        normalized_snapshot = client.normalize_snapshot(raw_snapshot)
    except ComunioSnapshotError as exc:
        print(f"[INGEST] status=failed reason={exc}")
        return 1

    try:
        conn = connect(settings.database_url)
        try:
            run_id, records_written = run_manual_snapshot(conn, normalized_snapshot)
        finally:
            conn.close()
    except Exception as exc:
        print(f"[INGEST] status=failed reason={exc}")
        return 1

    print(
        f"[INGEST] status=success message=Snapshot stored run_id={run_id} records_written={records_written}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
