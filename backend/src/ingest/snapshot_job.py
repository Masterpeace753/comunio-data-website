from __future__ import annotations

import datetime as dt

from psycopg2.extensions import connection as PgConnection


def _insert_ingest_run(conn: PgConnection, run_type: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ingest_runs(run_type, status, started_at)
            VALUES (%s, 'started', %s)
            RETURNING id
            """,
            (run_type, dt.datetime.now(dt.UTC)),
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("Could not create ingest_run")
        return int(row[0])


def _mark_ingest_run(conn: PgConnection, run_id: int, status: str, records_written: int, error_message: str | None = None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE ingest_runs
            SET status = %s,
                finished_at = %s,
                records_written = %s,
                error_message = %s
            WHERE id = %s
            """,
            (status, dt.datetime.now(dt.UTC), records_written, error_message, run_id),
        )


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
    snapshot_date = dt.date.today()

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


def run_manual_snapshot(conn: PgConnection, normalized_snapshot: dict[str, list[dict]]) -> tuple[int, int]:
    """Execute AP-7 manual snapshot transaction flow.

    Returns:
        (run_id, records_written)
    """
    run_id = _insert_ingest_run(conn, run_type="manual")
    conn.commit()

    try:
        team_map = _upsert_teams(conn, normalized_snapshot.get("teams", []))
        player_map = _upsert_players(conn, normalized_snapshot.get("players", []), team_map)
        written = _upsert_market_values(conn, normalized_snapshot.get("market_values", []), player_map, run_id)
        _mark_ingest_run(conn, run_id, status="success", records_written=written)
        conn.commit()
        return run_id, written
    except Exception as exc:
        conn.rollback()
        _mark_ingest_run(conn, run_id, status="failed", records_written=0, error_message=str(exc)[:1000])
        conn.commit()
        raise
