from __future__ import annotations

from collections.abc import Iterator

from psycopg2.extensions import connection as PgConnection

from src.config import load_settings
from src.database.connection import connect

from .errors import RepositoryUnavailableError


def get_db_connection() -> Iterator[PgConnection]:
    settings = load_settings()
    if not settings.database_url:
        raise RepositoryUnavailableError("database_unavailable")

    try:
        connection = connect(settings.database_url)
    except Exception as exc:
        raise RepositoryUnavailableError("database_unavailable") from exc

    try:
        yield connection
    finally:
        connection.close()