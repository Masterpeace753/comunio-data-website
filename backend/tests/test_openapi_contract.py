from __future__ import annotations

import src.api.app as api_app


def _schema_definitions(openapi: dict) -> dict:
    return openapi.get("components", {}).get("schemas", {})


def test_openapi_exposes_only_versioned_read_routes() -> None:
    paths = api_app.app.openapi()["paths"]
    expected_paths = {
        "/health/live",
        "/health/ready",
        "/api/v1/players",
        "/api/v1/players/{player_id}",
        "/api/v1/players/{player_id}/history",
        "/api/v1/teams",
        "/api/v1/teams/{team_id}",
        "/api/v1/transfermarket",
    }

    assert set(paths) == expected_paths
    assert all(set(operation) <= {"get"} for path in paths.values() for operation in [path])
    assert all(set(operation.keys()) == {"get"} for operation in paths.values())


def test_openapi_contains_ap12_nullable_fields() -> None:
    schemas = _schema_definitions(api_app.app.openapi())
    market_value_point = schemas["MarketValuePoint"]["properties"]

    for field in (
        "previous_snapshot_date",
        "previous_value_eur",
        "delta_previous_day_eur",
        "first_snapshot_date",
        "first_value_eur",
        "delta_first_eur",
        "percent_delta_previous_day",
        "percent_delta_first",
    ):
        schema = market_value_point[field]
        serialized = str(schema)
        assert "null" in serialized or schema.get("nullable") is True


def test_openapi_history_declares_validation_responses() -> None:
    history = api_app.app.openapi()["paths"]["/api/v1/players/{player_id}/history"]["get"]
    assert {"200", "400", "404", "422", "503"} <= set(history["responses"])
