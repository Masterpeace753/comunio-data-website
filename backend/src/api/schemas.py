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