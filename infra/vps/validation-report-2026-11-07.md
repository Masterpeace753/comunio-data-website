# VPS Compose validation report — 2026-11-07

## Result

**VPS runtime test: partial.** A separate, isolated test was performed over SSH
after the repository-only checks. It used a unique temporary Compose project,
synthetic certificates and an empty volume, without production data or a live
Ingest. The test resources were removed; the downloaded PostgreSQL 16.14 image
remains in the VPS image cache. No AWS resources were changed.

## Checks actually performed

- On the local Windows workspace, Docker Compose CLI version 5.6.0 validated
  the final `infra/vps/compose.yaml` with `docker compose config --quiet`.
- The default profile and the combined `bootstrap`, `jobs`, and `api` profiles
  both returned exit code 0. Validation used synthetic paths, image tags,
  numeric IDs, and a placeholder origin; no image was pulled and no container
  was started.
- Profile/security assertions previously confirmed the default profile
  includes only `db`; the full profile model has no published ports or
  `privileged` service, and includes the non-root `db-initdb` service and the
  isolated volume-permission helper.
- On the VPS, `systemd-analyze --user verify` accepted the service and timer;
  `systemd-analyze calendar` confirmed the next execution at 06:00 UTC.
- Using `postgres:16.14` on the VPS, the isolated volume helper and non-root
  `initdb` completed, the database started with a synthetic TLS server
  certificate, and its Unix-socket healthcheck reported healthy.
- Cleanup was verified: no probe containers, volumes, networks or temporary
  directories remained.

## Runtime checks still required on an authorized isolated VPS

Use a unique Compose project name (`-p`), a newly created temporary test
directory, synthetic test-only TLS CA/server/client certificates and
credentials, and an approved immutable PostgreSQL 16 image. Confirm the
project's named volume is new and empty before invoking the bootstrap helper.
Do not use the production Compose project name, production secret paths,
production certificates, or production database volume.

The following have **not** been run:

- database volume persistence after container recreation;
- `sslmode=verify-full` success and wrong-CA/wrong-host rejection;
- client-certificate/HBA success and negative cases;
- non-root read access to mounted test files;
- systemd lock contention or missed-run behavior.

No production run, live Ingest, AWS change, or cutover is authorized by this
report. Production remains NO-GO pending these tests, monitoring, a successful
restore, the required host-admin prerequisites, and separate operator Go.
