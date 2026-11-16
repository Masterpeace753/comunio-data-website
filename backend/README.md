# Backend Ingest and API

> **Platform default:** Develop new backend and Ingest features for Ubuntu/Linux
> VPS using Docker Compose, FastAPI, PostgreSQL, Caddy, and systemd. The VPS
> deployment guide at [infra/vps/README.md](../infra/vps/README.md) is the
> operational source of truth. AWS providers remain for the historical,
> optional alternative and should be changed only when explicitly requested.

This backend implements:

- AP-5: ComunioPy login flow bootstrap
- AP-6: PostgreSQL schema migrations
- AP-7: Manual snapshot pipeline (teams, players, market values)
- AP-11: read-only FastAPI endpoints for players, teams, history and transfer market
- AP-12: read-only market-value delta projection for player history
- AP-13: PostgreSQL integration tests, OpenAPI contract checks, error-path tests and benchmark harness

## Quick start

CI and both Linux images install `requirements.lock` with hash verification.
`requirements.txt` contains the direct dependency constraints. The lock is
resolved on Linux with Python 3.11; other platforms or Python versions may
need additional platform-specific dependencies. The final images remove
`pip` after installation; rebuild the image instead of installing packages
inside a running container.

To update the lock, use Python 3.11 on Linux and `pip-tools` 7.6.2:

```sh
pip-compile --allow-unsafe --generate-hashes --strip-extras --output-file requirements.lock requirements.txt
python -m pip install --require-hashes -r requirements.lock
```

Review the resulting dependency changes, run the tests and audit, and rebuild
and scan both images. Base-image and OS package updates still depend on the
upstream image and Debian repositories; the Python lock does not pin them.

1. Copy `.env.example` to `.env` and fill values, using local or test-only
   credentials and database settings.
1. Create a local development database.
1. Run migrations:

```sh
python -m migrations.runner
```

1. Test login flow bootstrap only:

```sh
python -m src.ingest.runner --run-type manual --mode login
```

1. Execute AP-7 manual snapshot run:

```sh
python -m src.ingest.runner --run-type manual --mode snapshot
```

1. Start the AP-11 API locally:

```sh
uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

Run the AP-13 test layers:

```sh
python -m pytest tests -q
export TEST_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/comunio_test?sslmode=disable"
python -m pytest tests -m integration -q
python scripts/benchmark_api.py
```

The API contract is available at `http://127.0.0.1:8000/docs` and uses the versioned
read-only routes under `/api/v1`. `/health/live` does not require a database connection;
`/health/ready` verifies database connectivity. API pagination is bounded to a maximum
`limit` of 100. The transfer-market route returns an empty page until the ingest pipeline
populates `transfermarket_snapshots`. Set `API_ALLOWED_ORIGINS` to a comma-separated
allowlist containing the Vercel production origin, for example
`https://comunio-data.vercel.app`. To allow Vercel branch-preview logins without
adding every PR URL individually, set both `API_VERCEL_PREVIEW_PROJECT_SLUG`
and `API_VERCEL_PREVIEW_TEAM_SLUG` to the project and team slug shown in the
generated preview hostname. The API accepts only HTTPS hosts matching
`<project>-git-<branch>-<team>.vercel.app`; other Vercel projects remain
blocked. Leave both unset to disable preview-origin matching.

`GET /api/v1/ingest/runs` returns a bounded, authenticated history of runs
registered in `ingest_runs` and the latest available market-value
`snapshot_date`. It never returns raw `error_message` values. It is not a
complete invocation audit: failures before database registration (including
database unavailability and scheduler lock conflicts) cannot appear there.
The date describes the latest available market-value data, not the most recent
attempt, and is reported in UTC. The endpoint requires migration
`004_ingest_run_status_metadata.sql`; apply it with `python -m migrations.runner`
before deploying the API code that serves this route. On 2026-11-08, migration
004 and the updated API and Ingest images were deployed to the VPS. The public
health and readiness endpoints returned 200; an unauthenticated request to the
history route was rejected as expected.

## Notes

- `sort=newest` on `GET /api/v1/players` orders by first database insertion
  for the dashboard; the default remains alphabetical.
- Player responses include nullable Comunio season `total_points`. The
  authenticated `GET /api/v1/players/{id}/points` returns completed matchdays
  for 2026/27, including `null` for unrecorded points. The calendar-based
  capture windows, including the restricted windows for matchdays 16 and 24,
  and their limitations are documented in [data_model.md](../data_model.md#35-player_points).
  Apply `006_player_total_points.sql` with the migration runner before
  deploying the updated API and Ingest. Deploy the API before the frontend.
  These changes describe the code, not a confirmed production deployment.
- Player responses include `club_name` (football club) separately from
  `team_id`/`team_name` (Comunio owner). Apply migration
  `005_player_club.sql` before deploying the updated API and ingest. Club names
  and corrected owner assignments become available after the next successful
  live snapshot; previously stored team assignments may be incorrect until then.
- Live player ingestion paginates Comunio's player endpoint with `start` and
  `limit`. Repeated pages without new player IDs fail the snapshot instead of
  reporting a successful but incomplete import.
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
- The AP-9 EventBridge task and ECS API service describe the former AWS
  deployment. Current production runs on the VPS: a systemd user timer starts
  the one-shot Ingest Compose job, and the API is served through the Caddy
  HTTPS proxy. See the [VPS runbook](../infra/vps/README.md) for current
  operating status and deployment instructions. Do not infer the live AWS
  service state from these historical AP-9/AWS descriptions.
