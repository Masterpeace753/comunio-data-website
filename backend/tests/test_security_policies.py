from __future__ import annotations

from pathlib import Path

import pytest

from src.config import load_settings
from src.database.connection import connect
from src.ingest.comuniopy_client import ComunioLoginError, ComunioPyClient, ComunioSnapshotError


def test_load_settings_defaults_snapshot_base_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("COMUNIO_SNAPSHOT_BASE_DIR", raising=False)
    monkeypatch.delenv("COMUNIO_REQUIRE_SECRET_MODE", raising=False)
    monkeypatch.delenv("COMUNIO_SNAPSHOT_MAX_BYTES", raising=False)

    settings = load_settings()

    assert settings.comunio_snapshot_base_dir
    assert settings.comunio_snapshot_max_bytes > 0


def test_connect_rejects_missing_sslmode() -> None:
    with pytest.raises(ValueError, match="sslmode=require"):
        connect("postgresql://user:pass@localhost:5432/comunio")


def test_connect_rejects_weak_sslmode() -> None:
    with pytest.raises(ValueError, match="sslmode=require"):
        connect("postgresql://user:pass@localhost:5432/comunio?sslmode=disable")


def test_connect_accepts_secure_sslmode(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, str] = {}

    def fake_connect(dsn: str):
        called["dsn"] = dsn
        return object()

    monkeypatch.setattr("src.database.connection.psycopg2.connect", fake_connect)
    dsn = "postgresql://user:pass@db:5432/comunio?sslmode=require"
    conn = connect(dsn)

    assert conn is not None
    assert called["dsn"] == dsn


def test_secret_mode_requires_secret_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("COMUNIO_REQUIRE_SECRET_MODE", "true")
    monkeypatch.delenv("COMUNIO_SECRET_NAME", raising=False)
    monkeypatch.setenv("COMUNIO_EMAIL", "demo@example.com")
    monkeypatch.setenv("COMUNIO_PASSWORD", "pw")

    settings = load_settings()
    client = ComunioPyClient(settings)

    with pytest.raises(ComunioLoginError, match="COMUNIO_SECRET_NAME"):
        client.load_credentials()


def test_snapshot_file_must_be_within_base_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    base_dir = tmp_path / "allowed"
    outside_dir = tmp_path / "outside"
    base_dir.mkdir()
    outside_dir.mkdir()

    outside_file = outside_dir / "snapshot.json"
    outside_file.write_text('{"teams": [], "players": [], "market_values": []}', encoding="utf-8")

    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("COMUNIO_SNAPSHOT_BASE_DIR", str(base_dir))
    monkeypatch.setenv("COMUNIO_SNAPSHOT_FILE", str(outside_file))

    settings = load_settings()
    client = ComunioPyClient(settings)

    with pytest.raises(ComunioSnapshotError, match="inside configured base directory"):
        client.fetch_snapshot()


def test_snapshot_file_respects_max_size(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    base_dir = tmp_path / "allowed"
    base_dir.mkdir()
    snapshot_file = base_dir / "snapshot.json"
    snapshot_file.write_text('{"teams": [], "players": [], "market_values": []}', encoding="utf-8")

    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("COMUNIO_SNAPSHOT_BASE_DIR", str(base_dir))
    monkeypatch.setenv("COMUNIO_SNAPSHOT_FILE", str(snapshot_file))
    monkeypatch.setenv("COMUNIO_SNAPSHOT_MAX_BYTES", "10")

    settings = load_settings()
    client = ComunioPyClient(settings)

    with pytest.raises(ComunioSnapshotError, match="exceeds max allowed size"):
        client.fetch_snapshot()
