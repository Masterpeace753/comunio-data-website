from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import psycopg2


_ALLOWED_SSLMODES = {"require", "verify-ca", "verify-full"}


def _validate_sslmode(database_url: str) -> None:
    parsed = urlparse(database_url)
    sslmode = (parse_qs(parsed.query).get("sslmode") or [""])[0].strip().lower()
    if sslmode not in _ALLOWED_SSLMODES:
        raise ValueError("DATABASE_URL must enforce TLS with sslmode=require or stronger")


def connect(database_url: str):
    if not database_url:
        raise ValueError("DATABASE_URL is required")
    _validate_sslmode(database_url)
    return psycopg2.connect(database_url)


def database_name(database_url: str) -> str:
    parsed = urlparse(database_url)
    return parsed.path.lstrip("/")
