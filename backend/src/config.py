from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    aws_region: str | None
    comunio_secret_name: str | None
    comunio_email: str | None
    comunio_password: str | None
    comunio_snapshot_file: str | None


def load_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", ""),
        aws_region=os.getenv("AWS_REGION"),
        comunio_secret_name=os.getenv("COMUNIO_SECRET_NAME"),
        comunio_email=os.getenv("COMUNIO_EMAIL"),
        comunio_password=os.getenv("COMUNIO_PASSWORD"),
        comunio_snapshot_file=os.getenv("COMUNIO_SNAPSHOT_FILE"),
    )
