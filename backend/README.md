# Backend Ingest and API

This backend implements:

- AP-5: ComunioPy login flow bootstrap
- AP-6: PostgreSQL schema migrations
- AP-7: Manual snapshot pipeline (teams, players, market values)
- AP-11: read-only FastAPI endpoints for players, teams, history and transfer market

## Quick start

1. Copy `.env.example` to `.env` and fill values.
1. Create database locally.
1. Run migrations:

```powershell
python -m migrations.runner
```

1. Test login flow bootstrap only:

```powershell
python -m src.ingest.runner --run-type manual --mode login
```

1. Execute AP-7 manual snapshot run:

```powershell
python -m src.ingest.runner --run-type manual --mode snapshot
```

1. Start the AP-11 API locally:

```powershell
uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

The API contract is available at `http://127.0.0.1:8000/docs` and uses the versioned
read-only routes under `/api/v1`. `/health/live` does not require a database connection;
`/health/ready` verifies database connectivity. API pagination is bounded to a maximum
`limit` of 100. The transfer-market route returns an empty page until the ingest pipeline
populates `transfermarket_snapshots`. Set `API_ALLOWED_ORIGINS` to a comma-separated
allowlist containing the Vercel production origin, for example
`https://comunio-data.vercel.app`.

## Notes

- For deterministic local tests you can set `COMUNIO_SNAPSHOT_FILE` to a JSON file
  containing `teams`, `players`, and `market_values` arrays.
- Scheduler/automation remains the separate AP-9 EventBridge task. The production API
  deployment is a separate ECS service and remains gated on private networking, health
  checks and a database reconnect proof. It must use a separate PostgreSQL read-only
  user and a separate Secrets Manager secret from the ingest `DATABASE_URL`.
