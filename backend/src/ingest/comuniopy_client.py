from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import boto3

from src.config import Settings


class ComunioLoginError(RuntimeError):
    pass


class ComunioSnapshotError(RuntimeError):
    pass


@dataclass(frozen=True)
class ComunioCredentials:
    email: str
    password: str
    source: str


class ComunioPyClient:
    """AP-7 client for ComunioPy login and manual snapshot extraction."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._provider: Any = None

    def _credentials_from_secret(self) -> ComunioCredentials:
        if not self.settings.aws_region or not self.settings.comunio_secret_name:
            raise ComunioLoginError("AWS_REGION and COMUNIO_SECRET_NAME are required for secret mode")

        sm = boto3.client("secretsmanager", region_name=self.settings.aws_region)
        response = sm.get_secret_value(SecretId=self.settings.comunio_secret_name)
        payload = json.loads(response["SecretString"])
        return ComunioCredentials(email=payload["username"], password=payload["password"], source="secrets_manager")

    def _credentials_from_env(self) -> ComunioCredentials:
        if not self.settings.comunio_email or not self.settings.comunio_password:
            raise ComunioLoginError("Missing COMUNIO_EMAIL/COMUNIO_PASSWORD")
        return ComunioCredentials(
            email=self.settings.comunio_email,
            password=self.settings.comunio_password,
            source="env",
        )

    def load_credentials(self) -> ComunioCredentials:
        if self.settings.require_secret_mode and not self.settings.comunio_secret_name:
            raise ComunioLoginError("COMUNIO_SECRET_NAME is required when COMUNIO_REQUIRE_SECRET_MODE is enabled")
        if self.settings.comunio_secret_name:
            return self._credentials_from_secret()
        return self._credentials_from_env()

    def _load_snapshot_payload(self, path: Path) -> dict[str, Any]:
        base_dir = Path(self.settings.comunio_snapshot_base_dir).resolve()
        resolved = path.resolve()
        if not resolved.is_relative_to(base_dir):
            raise ComunioSnapshotError(
                f"Snapshot file must be inside configured base directory: {base_dir}"
            )

        size = resolved.stat().st_size
        if size > self.settings.comunio_snapshot_max_bytes:
            raise ComunioSnapshotError(
                f"Snapshot file exceeds max allowed size ({self.settings.comunio_snapshot_max_bytes} bytes)"
            )

        payload = json.loads(resolved.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ComunioSnapshotError("Snapshot payload must be a JSON object")

        for key in ("teams", "players", "market_values"):
            value = payload.get(key, [])
            if not isinstance(value, list):
                raise ComunioSnapshotError(f"Snapshot field '{key}' must be a JSON array")
        return payload

    @staticmethod
    def _find_constructor(module: Any):
        for candidate in ("Client", "Comunio", "Session"):
            ctor = getattr(module, candidate, None)
            if ctor is not None:
                return ctor
        return None

    @staticmethod
    def _to_dict(item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            return item
        if hasattr(item, "__dict__"):
            return dict(item.__dict__)
        result: dict[str, Any] = {}
        for attr in dir(item):
            if attr.startswith("_"):
                continue
            try:
                value = getattr(item, attr)
            except Exception:
                continue
            if callable(value):
                continue
            result[attr] = value
        return result

    @staticmethod
    def _call_first(obj: Any, names: tuple[str, ...]):
        for name in names:
            fn = getattr(obj, name, None)
            if callable(fn):
                return fn()
        return None

    @staticmethod
    def _get_any(d: dict[str, Any], keys: tuple[str, ...], default: Any = None):
        for k in keys:
            if k in d and d[k] is not None:
                return d[k]
        return default

    def _extract_team_id(self, raw: dict[str, Any]) -> int | None:
        direct = self._get_any(raw, ("team_id", "comunio_team_id", "teamId"))
        if direct is not None:
            return int(direct)

        team = raw.get("team")
        if isinstance(team, dict):
            nested = self._get_any(team, ("id", "team_id", "comunio_team_id"))
            if nested is not None:
                return int(nested)
        return None

    @staticmethod
    def _normalize_position(raw_position: Any) -> str:
        mapping = {
            "TW": "TW",
            "GK": "TW",
            "TOR": "TW",
            "ABW": "ABW",
            "DEF": "ABW",
            "VERTEIDIGER": "ABW",
            "MITT": "MITT",
            "MF": "MITT",
            "MID": "MITT",
            "ST": "ST",
            "FW": "ST",
            "STR": "ST",
        }
        value = str(raw_position or "").upper().strip()
        if value in mapping:
            return mapping[value]
        raise ComunioSnapshotError(f"Unsupported position value: {raw_position}")

    def login(self) -> None:
        """Validate login and bind an API provider instance."""
        if self.settings.comunio_snapshot_file:
            # Local deterministic AP-7 mode: no external login required.
            self._provider = object()
            return

        creds = self.load_credentials()

        provider_instance: Any = None
        last_error: Exception | None = None

        try:
            import comuniopy as module  # type: ignore
            ctor = self._find_constructor(module)
            if ctor is None:
                raise ComunioLoginError("No compatible constructor in comuniopy module")
            provider_instance = ctor(creds.email, creds.password)
            if hasattr(provider_instance, "login"):
                provider_instance.login()
            self._provider = provider_instance
            return
        except Exception as exc:
            last_error = exc

        # Fallback for package exposing old module naming.
        try:
            import ComunioPy as module  # type: ignore
            ctor = self._find_constructor(module)
            if ctor is None:
                raise ComunioLoginError("No compatible constructor in ComunioPy module")
            provider_instance = ctor(creds.email, creds.password)
            if hasattr(provider_instance, "login"):
                provider_instance.login()
            self._provider = provider_instance
            return
        except Exception as exc:
            last_error = exc

        message = "Unable to validate ComunioPy login with current library API"
        if last_error:
            message = f"{message}: {last_error}"
        raise ComunioLoginError(message)

    def fetch_snapshot(self) -> dict[str, list[dict[str, Any]]]:
        """Fetch teams, players and market values for AP-7 manual snapshot run.

        Supports two data sources:
        1) Live provider (after successful login)
        2) Local JSON file via COMUNIO_SNAPSHOT_FILE for deterministic tests
        """
        if self.settings.comunio_snapshot_file:
            path = Path(self.settings.comunio_snapshot_file)
            if not path.exists():
                raise ComunioSnapshotError(f"Snapshot file not found: {path}")
            payload = self._load_snapshot_payload(path)
            return {
                "teams": payload.get("teams", []),
                "players": payload.get("players", []),
                "market_values": payload.get("market_values", []),
            }

        if self._provider is None:
            raise ComunioSnapshotError("Provider is not initialized; call login() first")

        teams_raw = self._call_first(self._provider, ("get_teams", "teams", "fetch_teams"))
        players_raw = self._call_first(self._provider, ("get_players", "players", "fetch_players"))
        market_raw = self._call_first(
            self._provider,
            ("get_market_values", "market_values", "fetch_market_values"),
        )

        teams_list = [self._to_dict(x) for x in (teams_raw or [])]
        players_list = [self._to_dict(x) for x in (players_raw or [])]
        market_list = [self._to_dict(x) for x in (market_raw or [])]

        # Fallback: derive market values from player payload if explicit endpoint is unavailable.
        if not market_list:
            for p in players_list:
                player_id = self._get_any(p, ("id", "player_id", "comunio_player_id", "comunioId"))
                value = self._get_any(p, ("market_value", "marketValue", "value_eur", "value"))
                if player_id is not None and value is not None:
                    market_list.append({"player_id": player_id, "value_eur": value})

        return {
            "teams": teams_list,
            "players": players_list,
            "market_values": market_list,
        }

    def normalize_snapshot(self, snapshot: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
        teams_out: list[dict[str, Any]] = []
        players_out: list[dict[str, Any]] = []
        values_out: list[dict[str, Any]] = []

        for t in snapshot.get("teams", []):
            raw = self._to_dict(t)
            team_id = self._get_any(raw, ("id", "team_id", "comunio_team_id", "comunioId"))
            name = self._get_any(raw, ("name", "team_name"))
            if team_id is None or not name:
                continue
            teams_out.append(
                {
                    "comunio_team_id": int(team_id),
                    "name": str(name),
                    "league": self._get_any(raw, ("league", "community")),
                    "season": self._get_any(raw, ("season",)),
                }
            )

        for p in snapshot.get("players", []):
            raw = self._to_dict(p)
            player_id = self._get_any(raw, ("id", "player_id", "comunio_player_id", "comunioId"))
            name = self._get_any(raw, ("name", "player_name"))
            position = self._get_any(raw, ("position", "pos"))
            team_id = self._extract_team_id(raw)
            if player_id is None or not name or position is None:
                continue
            players_out.append(
                {
                    "comunio_player_id": int(player_id),
                    "name": str(name),
                    "position": self._normalize_position(position),
                    "team_comunio_id": team_id,
                }
            )

        for m in snapshot.get("market_values", []):
            raw = self._to_dict(m)
            player_id = self._get_any(raw, ("player_id", "id", "comunio_player_id", "comunioId"))
            value = self._get_any(raw, ("value_eur", "value", "market_value", "marketValue"))
            if player_id is None or value is None:
                continue
            values_out.append(
                {
                    "comunio_player_id": int(player_id),
                    "value_eur": int(value),
                }
            )

        return {
            "teams": teams_out,
            "players": players_out,
            "market_values": values_out,
        }
