from __future__ import annotations

from datetime import date

import psycopg2
from psycopg2.extensions import connection as PgConnection

from .errors import RepositoryUnavailableError, ResourceNotFoundError


def _execute(connection: PgConnection, query: str, parameters: tuple = ()) -> list[tuple]:
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, parameters)
            return cursor.fetchall()
    except psycopg2.Error as exc:
        raise RepositoryUnavailableError("database_query_failed") from exc


def _execute_one(connection: PgConnection, query: str, parameters: tuple = ()) -> tuple | None:
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, parameters)
            return cursor.fetchone()
    except psycopg2.Error as exc:
        raise RepositoryUnavailableError("database_query_failed") from exc


def _count(connection: PgConnection, query: str, parameters: tuple) -> int:
    row = _execute_one(connection, query, parameters)
    return int(row[0]) if row else 0


def list_players(connection: PgConnection, limit: int, offset: int, team_id: int | None, position: str | None, search: str | None) -> tuple[list[tuple], int]:
    filters = "WHERE (%s IS NULL OR p.team_id = %s) AND (%s IS NULL OR p.position = %s) AND (%s IS NULL OR p.name ILIKE %s)"
    filter_parameters = (team_id, team_id, position, position, f"%{search}%" if search else None, f"%{search}%" if search else None)
    query = f"""
        SELECT p.id, p.comunio_player_id, p.name, p.position, p.team_id, t.name,
               mv.value_eur
        FROM players AS p
        LEFT JOIN teams AS t ON t.id = p.team_id
        LEFT JOIN LATERAL (
            SELECT value_eur FROM market_values
            WHERE player_id = p.id ORDER BY snapshot_date DESC LIMIT 1
        ) AS mv ON TRUE
        {filters}
        ORDER BY p.name ASC, p.id ASC
        LIMIT %s OFFSET %s
    """
    count_query = f"SELECT COUNT(*) FROM players AS p {filters}"
    return _execute(connection, query, filter_parameters + (limit, offset)), _count(connection, count_query, filter_parameters)


def get_player(connection: PgConnection, player_id: int) -> tuple:
    row = _execute_one(
        connection,
        """
        SELECT p.id, p.comunio_player_id, p.name, p.position, p.team_id, t.name,
               mv.value_eur, p.source, p.first_seen_at, p.last_seen_at, p.updated_at
        FROM players AS p
        LEFT JOIN teams AS t ON t.id = p.team_id
        LEFT JOIN LATERAL (
            SELECT value_eur FROM market_values
            WHERE player_id = p.id ORDER BY snapshot_date DESC LIMIT 1
        ) AS mv ON TRUE
        WHERE p.id = %s
        """,
        (player_id,),
    )
    if row is None:
        raise ResourceNotFoundError("player_not_found")
    return row


def list_teams(connection: PgConnection, limit: int, offset: int, search: str | None, league: str | None, season: str | None) -> tuple[list[tuple], int]:
    filters = "WHERE (%s IS NULL OR t.name ILIKE %s) AND (%s IS NULL OR t.league = %s) AND (%s IS NULL OR t.season = %s)"
    parameters = (f"%{search}%" if search else None, f"%{search}%" if search else None, league, league, season, season)
    query = f"""
        SELECT t.id, t.comunio_team_id, t.name, t.league, t.season,
               COUNT(p.id)::integer
        FROM teams AS t
        LEFT JOIN players AS p ON p.team_id = t.id
        {filters}
        GROUP BY t.id
        ORDER BY t.name ASC, t.id ASC
        LIMIT %s OFFSET %s
    """
    count_query = f"SELECT COUNT(*) FROM teams AS t {filters}"
    return _execute(connection, query, parameters + (limit, offset)), _count(connection, count_query, parameters)


def get_team(connection: PgConnection, team_id: int) -> tuple:
    row = _execute_one(
        connection,
        """
        SELECT t.id, t.comunio_team_id, t.name, t.league, t.season,
               COUNT(p.id)::integer, t.updated_at
        FROM teams AS t
        LEFT JOIN players AS p ON p.team_id = t.id
        WHERE t.id = %s
        GROUP BY t.id
        """,
        (team_id,),
    )
    if row is None:
        raise ResourceNotFoundError("team_not_found")
    return row


def get_player_history(connection: PgConnection, player_id: int, from_date: date | None, to_date: date | None, limit: int) -> list[tuple]:
    if _execute_one(connection, "SELECT 1 FROM players WHERE id = %s", (player_id,)) is None:
        raise ResourceNotFoundError("player_not_found")
    return _execute(
        connection,
        """
        SELECT snapshot_date, captured_at, value_eur
        FROM market_values
        WHERE player_id = %s
          AND (%s IS NULL OR snapshot_date >= %s)
          AND (%s IS NULL OR snapshot_date <= %s)
        ORDER BY snapshot_date DESC
        LIMIT %s
        """,
        (player_id, from_date, from_date, to_date, to_date, limit),
    )


def list_transfermarket(connection: PgConnection, limit: int, offset: int, snapshot_date: date | None, listed: bool | None) -> tuple[list[tuple], int, date | None]:
    date_parameter = snapshot_date
    query = """
        SELECT p.id, p.name, p.position, p.team_id, t.name, tm.snapshot_date,
               tm.listed, tm.price_eur, tm.owner_name
        FROM transfermarket_snapshots AS tm
        JOIN players AS p ON p.id = tm.player_id
        LEFT JOIN teams AS t ON t.id = p.team_id
        WHERE tm.snapshot_date = COALESCE(%s, (SELECT MAX(snapshot_date) FROM transfermarket_snapshots))
          AND (%s IS NULL OR tm.listed = %s)
        ORDER BY tm.price_eur ASC NULLS LAST, p.name ASC, p.id ASC
        LIMIT %s OFFSET %s
    """
    parameters = (date_parameter, listed, listed)
    rows = _execute(connection, query, parameters + (limit, offset))
    total = _count(
        connection,
        """
        SELECT COUNT(*) FROM transfermarket_snapshots AS tm
        WHERE tm.snapshot_date = COALESCE(%s, (SELECT MAX(snapshot_date) FROM transfermarket_snapshots))
          AND (%s IS NULL OR tm.listed = %s)
        """,
        parameters,
    )
    latest = _execute_one(connection, "SELECT MAX(snapshot_date) FROM transfermarket_snapshots", ())
    return rows, total, latest[0] if latest else None