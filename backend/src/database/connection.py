from __future__ import annotations

from urllib.parse import urlparse

import psycopg2


def connect(database_url: str):
    if not database_url:
        raise ValueError("DATABASE_URL is required")
    return psycopg2.connect(database_url)


def database_name(database_url: str) -> str:
    parsed = urlparse(database_url)
    return parsed.path.lstrip("/")
