from __future__ import annotations

import os
from pathlib import Path


_MAX_SECRET_FILE_BYTES = 1_048_576


def _configured_value(name: str) -> str | None:
    value = os.getenv(name)
    return value if value else None


def _remove_one_line_ending(value: str) -> str:
    if value.endswith("\n"):
        value = value[:-1]
        if value.endswith("\r"):
            value = value[:-1]
    return value


def read_secret_file(path: str, option_name: str) -> str:
    """Read a small UTF-8 secret file without exposing its path or contents in errors."""
    try:
        with Path(path).open("rb") as secret_file:
            data = secret_file.read(_MAX_SECRET_FILE_BYTES + 1)
        if len(data) > _MAX_SECRET_FILE_BYTES:
            raise ValueError
        value = data.decode("utf-8")
    except (OSError, UnicodeError, ValueError):
        raise ValueError(f"{option_name} could not be read as a UTF-8 secret file") from None

    value = _remove_one_line_ending(value)
    if not value:
        raise ValueError(f"{option_name} must not be empty")
    return value


def resolve_environment_secret(value_name: str, file_name: str) -> str | None:
    """Resolve one direct-env or file source; configuring both is always an error."""
    value = _configured_value(value_name)
    file_path = _configured_value(file_name)
    if value is not None and file_path is not None:
        raise ValueError(f"Configure only one of {value_name} and {file_name}")
    if value is not None:
        return value
    if file_path is not None:
        return read_secret_file(file_path, file_name)
    return None
