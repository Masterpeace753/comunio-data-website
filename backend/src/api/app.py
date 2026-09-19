from __future__ import annotations

from datetime import date
import os
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg2.extensions import connection as PgConnection

from . import repositories
from .dependencies import get_db_connection
from .errors import RepositoryUnavailableError, ResourceNotFoundError
from .schemas import (
    MarketValuePoint,
    Page,
    PlayerDetail,
    PlayerHistoryResponse,
    PlayerSummary,
    Position,
    TeamDetail,
    TeamSummary,
    TransferMarketItem,
    TransferMarketResponse,
)

app = FastAPI(title="Comunio Data API", version="1.0.0")
Db = Annotated[PgConnection, Depends(get_db_connection)]

allowed_origins = [
    origin.strip()
    for origin in os.getenv("API_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)


@app.exception_handler(RepositoryUnavailableError)
async def database_error_handler(_request: Request, _exc: RepositoryUnavailableError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"code": "api_database_unavailable", "message": "Database is not ready."})


@app.exception_handler(ResourceNotFoundError)
async def not_found_handler(_request: Request, exc: ResourceNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"code": str(exc), "message": "Resource not found."})


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready(connection: Db) -> dict[str, str]:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:
        raise RepositoryUnavailableError("database_not_ready") from exc
    return {"status": "ready"}


@app.get("/api/v1/players", response_model=Page[PlayerSummary])
def players(
    connection: Db,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
    team_id: Annotated[int | None, Query(gt=0)] = None,
    position: Position | None = None,
    search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
) -> Page[PlayerSummary]:
    rows, total = repositories.list_players(connection, limit, offset, team_id, position.value if position else None, search)
    items = [PlayerSummary(id=row[0], comunio_player_id=row[1], name=row[2], position=row[3], team_id=row[4], team_name=row[5], current_value_eur=row[6]) for row in rows]
    return Page(items=items, limit=limit, offset=offset, total=total)


@app.get("/api/v1/players/{player_id}", response_model=PlayerDetail)
def player(player_id: int, connection: Db) -> PlayerDetail:
    row = repositories.get_player(connection, player_id)
    return PlayerDetail(id=row[0], comunio_player_id=row[1], name=row[2], position=row[3], team_id=row[4], team_name=row[5], current_value_eur=row[6], source=row[7], first_seen_at=row[8], last_seen_at=row[9], updated_at=row[10])


@app.get(
    "/api/v1/players/{player_id}/history",
    response_model=PlayerHistoryResponse,
    responses={
        400: {"description": "Invalid date range"},
        404: {"description": "Player not found"},
        503: {"description": "Database unavailable"},
    },
)
def player_history(
    player_id: int,
    connection: Db,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: Annotated[int, Query(ge=1, le=366)] = 90,
) -> PlayerHistoryResponse:
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=400, detail={"code": "invalid_date_range", "message": "from_date must not be after to_date."})
    rows = repositories.get_player_history(connection, player_id, from_date, to_date, limit)
    return PlayerHistoryResponse(
        player_id=player_id,
        from_date=from_date,
        to_date=to_date,
        items=[
            MarketValuePoint(
                snapshot_date=row[0],
                captured_at=row[1],
                value_eur=row[2],
                previous_snapshot_date=row[3],
                previous_value_eur=row[4],
                delta_previous_day_eur=row[5],
                first_snapshot_date=row[6],
                first_value_eur=row[7],
                delta_first_eur=row[8],
                percent_delta_previous_day=row[9],
                percent_delta_first=row[10],
            )
            for row in rows
        ],
    )


@app.get("/api/v1/teams", response_model=Page[TeamSummary])
def teams(
    connection: Db,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    league: Annotated[str | None, Query(max_length=100)] = None,
    season: Annotated[str | None, Query(max_length=30)] = None,
) -> Page[TeamSummary]:
    rows, total = repositories.list_teams(connection, limit, offset, search, league, season)
    items = [TeamSummary(id=row[0], comunio_team_id=row[1], name=row[2], league=row[3], season=row[4], player_count=row[5]) for row in rows]
    return Page(items=items, limit=limit, offset=offset, total=total)


@app.get("/api/v1/teams/{team_id}", response_model=TeamDetail)
def team(team_id: int, connection: Db) -> TeamDetail:
    row = repositories.get_team(connection, team_id)
    return TeamDetail(id=row[0], comunio_team_id=row[1], name=row[2], league=row[3], season=row[4], player_count=row[5], updated_at=row[6])


@app.get("/api/v1/transfermarket", response_model=TransferMarketResponse)
def transfermarket(
    connection: Db,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
    snapshot_date: date | None = None,
    listed: bool | None = None,
) -> TransferMarketResponse:
    rows, total, latest = repositories.list_transfermarket(connection, limit, offset, snapshot_date, listed)
    items = [TransferMarketItem(player_id=row[0], player_name=row[1], position=row[2], team_id=row[3], team_name=row[4], snapshot_date=row[5], listed=row[6], price_eur=row[7], owner_name=row[8]) for row in rows]
    return TransferMarketResponse(items=items, snapshot_date=latest, limit=limit, offset=offset, total=total)