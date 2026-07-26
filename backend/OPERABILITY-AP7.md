# AP-7 Operability Runbook

## Scope
Manual snapshot pipeline only:
- Login
- Snapshot fetch
- Normalization
- Idempotent DB writes

## Command

```powershell
python -m src.ingest.runner --run-type manual --mode snapshot
```

## Required Environment
- DATABASE_URL
- Either:
  - COMUNIO_EMAIL + COMUNIO_PASSWORD
  - or AWS_REGION + COMUNIO_SECRET_NAME
- Optional deterministic local mode:
  - COMUNIO_SNAPSHOT_FILE=tests/sample_snapshot.json

## Expected Success Output
- `[INGEST] status=success ... run_id=<id> records_written=<n>`
- Exit code `0`

## Failure Modes
- Missing credentials: status failed, exit code 1
- Missing DB URL: status failed, exit code 1
- Snapshot fetch failures: retries with backoff then failed
- DB write failures: ingest_run marked failed

## Go/No-Go for Phase 2 closure
- G1 Login successful
- G2 Migration runner idempotent
- G3 Snapshot mode stores records without duplicate market_values
