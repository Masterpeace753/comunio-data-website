from __future__ import annotations

import datetime as dt

from psycopg2.extensions import connection as PgConnection


def start_ingest_run(conn: PgConnection, run_type: str, stage: str = "login") -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ingest_runs(run_type, status, started_at, stage)
            VALUES (%s, 'started', %s, %s)
            RETURNING id
            """,
            (run_type, dt.datetime.now(dt.UTC), stage),
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("Could not create ingest_run")
        run_id = int(row[0])
    conn.commit()
    return run_id


def set_ingest_run_stage(conn: PgConnection, run_id: int, stage: str) -> None:
    with conn.cursor() as cur:
        cur.execute("UPDATE ingest_runs SET stage = %s WHERE id = %s", (stage, run_id))
    conn.commit()


def mark_ingest_run_failed(conn: PgConnection, run_id: int, stage: str, error_code: str) -> None:
    _mark_ingest_run(
        conn,
        run_id,
        status="failed",
        records_written=0,
        stage=stage,
        error_code=error_code,
    )


def _mark_ingest_run(
    conn: PgConnection,
    run_id: int,
    status: str,
    records_written: int,
    stage: str,
    error_code: str | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE ingest_runs
            SET status = %s,
                finished_at = %s,
                records_written = %s,
                stage = %s,
                error_code = %s
            WHERE id = %s
            """,
            (status, dt.datetime.now(dt.UTC), records_written, stage, error_code, run_id),
        )
    conn.commit()


def _upsert_teams(conn: PgConnection, teams: list[dict]) -> dict[int, int]:
    mapping: dict[int, int] = {}
    with conn.cursor() as cur:
        for team in teams:
            cur.execute(
                """
                INSERT INTO teams(comunio_team_id, name, league, season)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (comunio_team_id)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    league = EXCLUDED.league,
                    season = EXCLUDED.season,
                    updated_at = now()
                RETURNING id, comunio_team_id
                """,
                (
                    team["comunio_team_id"],
                    team["name"],
                    team.get("league"),
                    team.get("season"),
                ),
            )
            row = cur.fetchone()
            if row is None:
                continue
            mapping[int(row[1])] = int(row[0])
    return mapping


def _upsert_players(conn: PgConnection, players: list[dict], team_map: dict[int, int]) -> dict[int, int]:
    mapping: dict[int, int] = {}
    with conn.cursor() as cur:
        for player in players:
            team_fk = None
            team_comunio_id = player.get("team_comunio_id")
            if team_comunio_id is not None:
                team_fk = team_map.get(int(team_comunio_id))

            cur.execute(
                """
                INSERT INTO players(comunio_player_id, name, position, team_id)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (comunio_player_id)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    position = EXCLUDED.position,
                    team_id = EXCLUDED.team_id,
                    last_seen_at = now(),
                    updated_at = now()
                RETURNING id, comunio_player_id
                """,
                (
                    player["comunio_player_id"],
                    player["name"],
                    player["position"],
                    team_fk,
                ),
            )
            row = cur.fetchone()
            if row is None:
                continue
            mapping[int(row[1])] = int(row[0])
    return mapping


def _upsert_market_values(conn: PgConnection, market_values: list[dict], player_map: dict[int, int], run_id: int) -> int:
    written = 0
    snapshot_date = dt.datetime.now(dt.UTC).date()

    with conn.cursor() as cur:
        for value in market_values:
            player_fk = player_map.get(int(value["comunio_player_id"]))
            if player_fk is None:
                continue

            cur.execute(
                """
                INSERT INTO market_values(player_id, snapshot_date, captured_at, value_eur, source, ingest_run_id)
                VALUES (%s, %s, %s, %s, 'comuniopy', %s)
                ON CONFLICT (player_id, snapshot_date)
                DO UPDATE SET
                    captured_at = EXCLUDED.captured_at,
                    value_eur = EXCLUDED.value_eur,
                    ingest_run_id = EXCLUDED.ingest_run_id
                """,
                (
                    player_fk,
                    snapshot_date,
                    dt.datetime.now(dt.UTC),
                    value["value_eur"],
                    run_id,
                ),
            )
            written += 1

    return written


def run_manual_snapshot(
    conn: PgConnection,
    normalized_snapshot: dict[str, list[dict]],
    run_type: str = "manual",
    run_id: int | None = None,
) -> tuple[int, int]:
    """Execute the AP-7/AP-9 snapshot transaction flow.

    Returns:
        (run_id, records_written)
    """
    if run_type not in {"manual", "scheduled"}:
        raise ValueError(f"Unsupported ingest run type: {run_type}")

    if run_id is None:
        run_id = start_ingest_run(conn, run_type=run_type, stage="persistence")

    try:
        set_ingest_run_stage(conn, run_id, "persistence")
        team_map = _upsert_teams(conn, normalized_snapshot.get("teams", []))
        player_map = _upsert_players(conn, normalized_snapshot.get("players", []), team_map)
        written = _upsert_market_values(conn, normalized_snapshot.get("market_values", []), player_map, run_id)
        _mark_ingest_run(conn, run_id, status="success", records_written=written, stage="snapshot")
        return run_id, written
    except Exception:
        conn.rollback()
        mark_ingest_run_failed(conn, run_id, stage="persistence", error_code="database_persistence_failed")
        raise
