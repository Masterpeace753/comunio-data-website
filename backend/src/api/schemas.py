from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class Position(StrEnum):
    GOALKEEPER = "TW"
    DEFENDER = "ABW"
    MIDFIELDER = "MITT"
    FORWARD = "ST"


class IngestStage(StrEnum):
    LOGIN = "login"
    SNAPSHOT = "snapshot"
    PERSISTENCE = "persistence"


class IngestErrorCode(StrEnum):
    AUTHENTICATION_FAILED = "authentication_failed"
    SNAPSHOT_FETCH_FAILED = "snapshot_fetch_failed"
    DATABASE_PERSISTENCE_FAILED = "database_persistence_failed"
    UNEXPECTED_ERROR = "unexpected_error"


class IngestRunType(StrEnum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    UNKNOWN = "unknown"


class IngestRunStatus(StrEnum):
    STARTED = "started"
    SUCCESS = "success"
    FAILED = "failed"
    UNKNOWN = "unknown"


Item = TypeVar("Item")


class Page(BaseModel, Generic[Item]):
    items: list[Item]
    limit: int
    offset: int
    total: int


class PlayerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    comunio_player_id: int
    name: str
    position: Position
    team_id: int | None
    team_name: str | None
    current_value_eur: int | None


class PlayerDetail(PlayerSummary):
    source: str
    first_seen_at: datetime
    last_seen_at: datetime
    updated_at: datetime


class TeamSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    comunio_team_id: int
    name: str
    league: str | None
    season: str | None
    player_count: int


class TeamDetail(TeamSummary):
    updated_at: datetime


class MarketValuePoint(BaseModel):
    snapshot_date: date
    captured_at: datetime
    value_eur: int
    previous_snapshot_date: date | None = None
    previous_value_eur: int | None = None
    delta_previous_day_eur: int | None = None
    first_snapshot_date: date | None = None
    first_value_eur: int | None = None
    delta_first_eur: int | None = None
    percent_delta_previous_day: float | None = None
    percent_delta_first: float | None = None


class PlayerHistoryResponse(BaseModel):
    player_id: int
    from_date: date | None
    to_date: date | None
    items: list[MarketValuePoint]


class TransferMarketItem(BaseModel):
    player_id: int
    player_name: str
    position: Position
    team_id: int | None
    team_name: str | None
    snapshot_date: date
    listed: bool
    price_eur: int | None
    owner_name: str | None


class TransferMarketResponse(BaseModel):
    items: list[TransferMarketItem]
    snapshot_date: date | None
    limit: int
    offset: int
    total: int


class IngestRunItem(BaseModel):
    id: int
    run_type: IngestRunType
    status: IngestRunStatus
    started_at: datetime
    finished_at: datetime | None
    records_written: int
    stage: IngestStage | None
    error_code: IngestErrorCode | None


class IngestRunsResponse(BaseModel):
    current_data_date: date | None
    items: list[IngestRunItem]
    limit: int
    offset: int
    total: int