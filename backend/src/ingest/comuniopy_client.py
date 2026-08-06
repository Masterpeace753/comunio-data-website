from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import boto3
import requests

from src.config import Settings

_API_BASE = "https://api.comunio.de"
_LOGIN_ENDPOINT = _API_BASE + "/login"
_PAGE_SIZE = 100


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
    """Client for the Comunio REST API (api.comunio.de)."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._session: requests.Session | None = None
        self._user_id: str = ""
        self._community_id: str = ""
        self._community_name: str = ""

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
    def _get_any(d: dict[str, Any], keys: tuple[str, ...], default: Any = None):
        for k in keys:
            if k in d and d[k] is not None:
                return d[k]
        return default

    @staticmethod
    def _normalize_position(raw_position: Any) -> str:
        mapping = {
            # Comunio REST API values
            "KEEPER": "TW",
            "DEFENDER": "ABW",
            "MIDFIELDER": "MITT",
            "STRIKER": "ST",
            # Legacy / German abbreviations
            "TW": "TW", "GK": "TW", "TOR": "TW",
            "ABW": "ABW", "DEF": "ABW", "VERTEIDIGER": "ABW",
            "MITT": "MITT", "MF": "MITT", "MID": "MITT",
            "ST": "ST", "FW": "ST", "STR": "ST",
        }
        value = str(raw_position or "").upper().strip()
        if value in mapping:
            return mapping[value]
        raise ComunioSnapshotError(f"Unsupported position value: {raw_position}")

    def login(self) -> None:
        """Authenticate against the Comunio REST API and store session state."""
        if self.settings.comunio_snapshot_file:
            # Fixture mode: no network login needed.
            self._session = requests.Session()
            return

        creds = self.load_credentials()

        s = requests.Session()
        s.headers["User-Agent"] = "Mozilla/5.0"

        r = s.post(
            _LOGIN_ENDPOINT,
            data={"username": creds.email, "password": creds.password, "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        if r.status_code != 200:
            raise ComunioLoginError(f"Login failed ({r.status_code}): {r.text[:200]}")

        token = r.json().get("access_token")
        if not token:
            raise ComunioLoginError("No access_token in login response")

        s.headers["Authorization"] = f"Bearer {token}"

        root = s.get(_API_BASE + "/", timeout=30)
        if root.status_code != 200:
            raise ComunioLoginError(f"Failed to fetch user info ({root.status_code})")

        user = root.json().get("user", {})
        uid = str(user["id"])
        self._session = s
        self._user_id = uid

        # Community ID is in the full user profile, not the root summary.
        user_r = s.get(f"{_API_BASE}/users/{uid}", timeout=30)
        if user_r.status_code != 200:
            raise ComunioLoginError(f"Failed to fetch user profile ({user_r.status_code})")
        user_profile = user_r.json()
        community = user_profile.get("community") or {}
        self._community_id = str(community.get("id", ""))
        self._community_name = str(community.get("name", ""))

    def fetch_snapshot(self) -> dict[str, list[dict[str, Any]]]:
        """Fetch teams, players and market values.

        Supports two modes:
        1) Live: paginate the Comunio REST API (requires prior login())
        2) Fixture: load from COMUNIO_SNAPSHOT_FILE (deterministic tests)
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

        if self._session is None or not self._community_id:
            raise ComunioSnapshotError("Not logged in; call login() first")

        all_players: list[dict[str, Any]] = []
        offset = 0
        while True:
            r = self._session.get(
                f"{_API_BASE}/communities/{self._community_id}/players",
                params={"limit": _PAGE_SIZE, "offset": offset},
                timeout=30,
            )
            if r.status_code != 200:
                raise ComunioSnapshotError(f"Failed to fetch players ({r.status_code}): {r.text[:200]}")
            data = r.json()
            batch: list[dict[str, Any]] = data.get("tradables", [])
            all_players.extend(batch)
            if len(all_players) >= data.get("totalHits", 0) or not batch:
                break
            offset += _PAGE_SIZE

        # Derive teams (community members) from player owner field.
        teams_seen: dict[int, dict[str, Any]] = {}
        for p in all_players:
            owner = p.get("owner")
            if owner and owner.get("id") not in teams_seen:
                teams_seen[int(owner["id"])] = {
                    "comunio_team_id": int(owner["id"]),
                    "name": str(owner.get("name", "")).strip(),
                    "league": self._community_name or None,
                    "season": None,
                }

        players_out: list[dict[str, Any]] = []
        market_values_out: list[dict[str, Any]] = []
        for p in all_players:
            pid = p.get("id")
            name = p.get("name")
            position = p.get("position")
            if pid is None or not name or position is None:
                continue
            try:
                normalized_pos = self._normalize_position(position)
            except ComunioSnapshotError:
                continue

            club = p.get("club") or {}
            players_out.append({
                "comunio_player_id": int(pid),
                "name": str(name),
                "position": normalized_pos,
                "team_comunio_id": int(club["id"]) if club.get("id") else None,
            })
            market_values_out.append({
                "comunio_player_id": int(pid),
                "value_eur": int(p.get("quotedprice") or 0),
            })

        return {
            "teams": list(teams_seen.values()),
            "players": players_out,
            "market_values": market_values_out,
        }

    def normalize_snapshot(self, snapshot: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
        teams_out: list[dict[str, Any]] = []
        players_out: list[dict[str, Any]] = []
        values_out: list[dict[str, Any]] = []

        for t in snapshot.get("teams", []):
            team_id = self._get_any(t, ("comunio_team_id", "id", "team_id", "comunioId"))
            name = self._get_any(t, ("name", "team_name"))
            if team_id is None or not name:
                continue
            teams_out.append(
                {
                    "comunio_team_id": int(team_id),
                    "name": str(name),
                    "league": self._get_any(t, ("league", "community")),
                    "season": self._get_any(t, ("season",)),
                }
            )

        for p in snapshot.get("players", []):
            player_id = self._get_any(p, ("comunio_player_id", "id", "player_id", "comunioId"))
            name = self._get_any(p, ("name", "player_name"))
            position = self._get_any(p, ("position", "pos"))
            team_comunio_id = self._get_any(p, ("team_comunio_id", "team_id"))
            if player_id is None or not name or position is None:
                continue
            players_out.append(
                {
                    "comunio_player_id": int(player_id),
                    "name": str(name),
                    "position": self._normalize_position(position),
                    "team_comunio_id": int(team_comunio_id) if team_comunio_id is not None else None,
                }
            )

        for m in snapshot.get("market_values", []):
            player_id = self._get_any(m, ("comunio_player_id", "player_id", "id", "comunioId"))
            value = self._get_any(m, ("value_eur", "value", "market_value", "marketValue"))
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

