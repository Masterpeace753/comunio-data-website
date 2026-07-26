# AP-5/AP-6 Operability and Smoke Checks

## Scope
This runbook validates only:
- AP-5: ComunioPy login bootstrap
- AP-6: PostgreSQL migration baseline

Out of scope:
- AP-7+ snapshot processing
- Scheduler automation
- API endpoint delivery

## Go/No-Go Gates

### Gate G1: Login Bootstrap
PASS criteria:
- `python -m src.ingest.runner --run-type manual` exits with code 0
- Output contains `status=success`

NO-GO if:
- Exit code is non-zero
- Output contains `status=failed`

### Gate G2: Migration Idempotency
PASS criteria:
- First migration run applies SQL files successfully
- Second migration run exits successfully without duplicate migration records

NO-GO if:
- Migration runner fails
- Re-run causes duplicate artifacts or SQL errors

### Gate G3: Schema Integrity
PASS criteria:
- Core tables exist: teams, players, ingest_runs
- Timeseries tables exist: market_values, player_points, transfermarket_snapshots
- Event/Audit tables exist: availability_events, audit_log
- Required unique constraints are present

NO-GO if:
- Any required table is missing
- Unique constraints are missing or broken

## Layered Smoke Check Sequence

### Layer 1: Prerequisites
1. Confirm Python version:

```powershell
python --version
```

2. Install dependencies:

```powershell
Set-Location backend
pip install -r requirements.txt
```

3. Ensure DB URL is set:

```powershell
$env:DATABASE_URL
```

Expected: non-empty output.

### Layer 2: AP-5 Login Flow
1. Local env mode test (if no AWS secret is used):

```powershell
$env:COMUNIO_EMAIL="your-email"
$env:COMUNIO_PASSWORD="your-password"
python -m src.ingest.runner --run-type manual
```

2. AWS secret mode test (preferred for cloud-like validation):

```powershell
$env:AWS_REGION="eu-central-1"
$env:COMUNIO_SECRET_NAME="/comunio/phase2/comuniopy-credentials"
python -m src.ingest.runner --run-type manual
```

Expected:
- success path prints `status=success`
- failure path prints `status=failed reason=...`

### Layer 3: AP-6 Migrations
1. Run migrations (first pass):

```powershell
python -m migrations.runner
```

2. Run migrations again (idempotency pass):

```powershell
python -m migrations.runner
```

Expected:
- First pass applies pending migrations
- Second pass applies none and exits successfully

### Layer 4: Schema Verification
Run SQL checks against the target database:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'teams','players','ingest_runs',
    'market_values','player_points','transfermarket_snapshots',
    'availability_events','audit_log'
  )
ORDER BY table_name;
```

```sql
SELECT conname, conrelid::regclass AS table_name
FROM pg_constraint
WHERE contype = 'u'
  AND conrelid::regclass::text IN ('market_values','player_points','transfermarket_snapshots')
ORDER BY table_name, conname;
```

Expected:
- All required tables returned
- Unique constraints present for idempotency keys

### Layer 5: Security Quick Checks
1. Ensure no secrets are committed:

```powershell
git grep -i "password\|secret\|token\|apikey" backend/src
```

Expected:
- No hardcoded credentials in source files.

2. If using AWS secret mode, confirm secret exists:

```powershell
aws secretsmanager get-secret-value --secret-id "/comunio/phase2/comuniopy-credentials" --region "eu-central-1"
```

Expected:
- Command returns SecretString (do not paste value into logs or tickets).

## Common Failure Cases and Recovery

### F1 Login fails with missing credentials
Symptoms:
- `status=failed reason=Missing COMUNIO_EMAIL/COMUNIO_PASSWORD`

Recovery:
1. Set COMUNIO_EMAIL and COMUNIO_PASSWORD, or
2. Set AWS_REGION and COMUNIO_SECRET_NAME for secret mode.

### F2 Login fails due to incompatible comuniopy API
Symptoms:
- `Unable to validate ComunioPy login with current library API`

Recovery:
1. Check installed comuniopy version.
2. Align wrapper logic in src/ingest/comuniopy_client.py with active constructor in library.

### F3 Migration runner fails on DB connection
Symptoms:
- psycopg2 connection error

Recovery:
1. Validate DATABASE_URL.
2. Verify PostgreSQL is reachable.
3. Retry migration runner.

### F4 Re-run migration fails
Symptoms:
- SQL errors on second run

Recovery:
1. Inspect schema_migrations table.
2. Fix migration ordering/content.
3. Re-run after correction.

## Acceptance Snapshot (AP-5/AP-6)
- G1 PASS
- G2 PASS
- G3 PASS

Only when all three are PASS, AP-5/AP-6 is operationally ready for AP-7 handoff.

## Handoff
For AP-7 manual snapshot operations, use `OPERABILITY-AP7.md`.
