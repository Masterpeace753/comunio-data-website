# Backend Ingest and API

This backend implements:

- AP-5: ComunioPy login flow bootstrap
- AP-6: PostgreSQL schema migrations
- AP-7: Manual snapshot pipeline (teams, players, market values)
- AP-11: read-only FastAPI endpoints for players, teams, history and transfer market
- AP-12: read-only market-value delta projection for player history
- AP-13: PostgreSQL integration tests, OpenAPI contract checks, error-path tests and benchmark harness

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

Run the AP-13 test layers:

```powershell
python -m pytest tests -q
$env:TEST_DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:5432/comunio_test?sslmode=disable"
python -m pytest tests -m integration -q
python scripts/benchmark_api.py
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
- Secret providers support the existing AWS settings and optional mounted files:
  - `COMUNIO_SECRET_NAME` remains the AWS Secrets Manager JSON secret
    (`username`, `password`). `COMUNIO_SECRET_FILE` points to a UTF-8 JSON file
    with the same keys. These two providers are mutually exclusive. A Comunio
    file cannot be combined with `COMUNIO_EMAIL` or `COMUNIO_PASSWORD`.
    For backwards compatibility, when the AWS secret name is configured it
    remains preferred over any legacy `COMUNIO_EMAIL`/`COMUNIO_PASSWORD`
    fallback values.
  - `AUTH_SECRET_ARN` remains the AWS Secrets Manager JSON secret with
    `username`, `passwordHash`, and `jwtSecret`. `AUTH_SECRET_FILE` points to a
    UTF-8 file with that same JSON shape. The ARN and file options conflict.
  - `DATABASE_URL_FILE` contains the raw database URL, and
    `API_PROXY_SECRET_FILE` contains the raw proxy secret. For each of these,
    its corresponding direct environment variable (`DATABASE_URL` or
    `API_PROXY_SECRET`) and `*_FILE` option are mutually exclusive.
    In production, `AUTH_SECRET_FILE` is read and fully validated during API
    startup; missing, unreadable, or invalid files prevent startup. The
    `AUTH_SECRET_ARN` Secrets Manager provider remains lazy-loaded.
  - Raw files may have one final LF or CRLF line ending, which is removed;
    other whitespace is retained. JSON files follow normal JSON parsing.
    Files must be non-empty, valid UTF-8, and at most 1 MiB. Read/configuration
    errors do not include file contents or paths. Production still requires
    `COMUNIO_REQUIRE_SECRET_MODE=true`, a Comunio AWS or file provider, and
    both API auth and proxy-secret providers. These checks fail closed.
  - On a VPS, mount only the required secret files read-only, restrict host
    permissions to the service/container identity, and keep secret files
    outside the repository and container image. Do not put secret contents in
    logs, command arguments, or deployment examples. AWS deployments should
    continue using their existing AWS settings without configuring `*_FILE`.
- Scheduler/automation remains the separate AP-9 EventBridge task. The production API
  deployment is a separate ECS service and the cost-optimized MVP uses a public HTTP ALB
  with health checks. Private networking, HTTPS/ACM, WAF and a database reconnect proof
  are later hardening steps. It must use a separate PostgreSQL read-only
  user and a separate Secrets Manager secret from the ingest `DATABASE_URL`.
