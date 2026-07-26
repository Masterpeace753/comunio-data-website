# Backend AP-5/AP-6

This backend skeleton implements only:
- AP-5: ComunioPy login flow bootstrap
- AP-6: PostgreSQL schema migrations
- AP-7: Manual snapshot pipeline (teams, players, market values)

## Quick start

1. Copy `.env.example` to `.env` and fill values.
2. Create database locally.
3. Run migrations:

```powershell
python -m migrations.runner
```

4. Test login flow bootstrap only:

```powershell
python -m src.ingest.runner --run-type manual --mode login
```

5. Execute AP-7 manual snapshot run:

```powershell
python -m src.ingest.runner --run-type manual --mode snapshot
```

## Notes

- For deterministic local tests you can set `COMUNIO_SNAPSHOT_FILE` to a JSON file
	containing `teams`, `players`, and `market_values` arrays.
- Scheduler/automation is intentionally out of scope for AP-7 and remains Phase 3.
