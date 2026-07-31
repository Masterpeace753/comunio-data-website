from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str
    app_env: str
    require_secret_mode: bool
    aws_region: str | None
    comunio_secret_name: str | None
    comunio_email: str | None
    comunio_password: str | None
    comunio_snapshot_file: str | None
    comunio_snapshot_base_dir: str
    comunio_snapshot_max_bytes: int

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in {"prod", "production"}


def load_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "dev")
    require_secret_default = app_env.strip().lower() in {"prod", "production"}
    snapshot_base_dir = os.getenv(
        "COMUNIO_SNAPSHOT_BASE_DIR",
        str((Path(__file__).resolve().parents[1] / "tests").resolve()),
    )

    snapshot_max_bytes_raw = os.getenv("COMUNIO_SNAPSHOT_MAX_BYTES", "2000000")
    try:
        snapshot_max_bytes = int(snapshot_max_bytes_raw)
    except ValueError as exc:
        raise ValueError("COMUNIO_SNAPSHOT_MAX_BYTES must be an integer") from exc
    if snapshot_max_bytes <= 0:
        raise ValueError("COMUNIO_SNAPSHOT_MAX_BYTES must be > 0")

    return Settings(
        database_url=os.getenv("DATABASE_URL", ""),
        app_env=app_env,
        require_secret_mode=_parse_bool(
            os.getenv("COMUNIO_REQUIRE_SECRET_MODE"),
            default=require_secret_default,
        ),
        aws_region=os.getenv("AWS_REGION"),
        comunio_secret_name=os.getenv("COMUNIO_SECRET_NAME"),
        comunio_email=os.getenv("COMUNIO_EMAIL"),
        comunio_password=os.getenv("COMUNIO_PASSWORD"),
        comunio_snapshot_file=os.getenv("COMUNIO_SNAPSHOT_FILE"),
        comunio_snapshot_base_dir=snapshot_base_dir,
        comunio_snapshot_max_bytes=snapshot_max_bytes,
    )
