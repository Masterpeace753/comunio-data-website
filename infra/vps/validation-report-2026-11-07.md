# VPS Compose validation report — 2026-11-07

## Result

**Cutover in progress; detail-page fix and acceptance outstanding.** A separate, isolated test was performed over SSH
after the repository-only checks. It used a unique temporary Compose project,
synthetic certificates and an empty volume, without production data or a live
Ingest. The test resources were removed; the downloaded PostgreSQL 16.14 image
remains in the VPS image cache. Subsequent production cutover steps are
recorded separately below.

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
- On the local Windows workspace, the three backend PostgreSQL integration
  tests passed against an isolated, temporary PostgreSQL 16.15 container
  using synthetic data; the container was removed. This is not a VPS runtime
  test or a restore of the production database.
- A subsequent isolated VPS Compose test with PostgreSQL 16.14 and synthetic
  certificates verified `sslmode=verify-full` and an Ingest-role write.
  Connections with a wrong CA, wrong hostname, missing client certificate, or
  disabled TLS failed. A test row persisted after DB container recreation.
  The unique test project, volume, network, and temporary directory were
  removed. This does not test production certificates or a production restore.
- On the local Windows workspace, a separate PostgreSQL 16.15 synthetic test
  streamed a custom-format dump directly into OpenPGP encryption. The dump was
  decrypted and restored to a new isolated test database, where its test row
  matched. The test container and encrypted test file were removed. The
  private key had to be unlocked interactively in the operator's terminal;
  this test does not constitute a production-data backup or restore.
- A preliminary RDS custom-format dump was streamed through a temporary SSM
  port-forward directly into an OpenPGP-encrypted local file. Decryption and
  a complete `pg_restore` archive read succeeded. The temporary instance,
  database ingress rule, security group, IAM role and instance profile were
  removed. The production-data dump was restored successfully to an isolated
  local PostgreSQL container with its data directory on tmpfs; nine public
  base tables were present. Host swapping was not ruled out. The container
  was removed; source/target reconciliation remains outstanding. This is not
  the final dump required after the AWS writer is stopped.
  The encrypted file `comunio-migration-a5a21ff42aa8.dump.gpg` has SHA-256
  `0aad8766308499764e3f742290290083b47152d1618f6977cc378be9c87abd90`.
- A second preliminary dump used a PostgreSQL exported snapshot shared by
  `pg_dump` and source row-count queries. Its isolated tmpfs restore contained
  the same public table set and row counts for all nine tables. It is not a
  substitute for schema/constraint checks, a VPS restore, or the final dump
  taken after the writer is stopped. Temporary AWS resources and the test
  container were removed. The encrypted file
  `comunio-migration-ec25d8e8ccd1.dump.gpg` has SHA-256
  `c46970f2d3c1b5964cce82541d0fe498c54f01b58f68637d81512b4f308759b6`.
- A clean Linux-line-ending deployment copy of commit
  `fa8a945858ea12fad201b45f8848fdc3fd881a2a` was staged under
  `serveradmin`'s home directory, without enabling the timer or starting the
  application. Both application images built on the VPS; the Ingest and API
  images run as UID 100/GID 101. The cached PostgreSQL 16.14 image reports
  UID/GID 999 and digest
  `sha256:95206741a5b214807675e14165369d05b93a9cf692223b616d07cca227e74b0b`.
  This is preparation, not approval of the images or a production deployment.
- The staged API was subsequently rebuilt with the VPS-only global,
  single-worker login limiter and passed a secret-free, network-isolated
  import/configuration smoke test. An optional Caddy HTTPS overlay was tested
  locally with a synthetic internal CA: HTTPS proxying, the HTTP redirect and
  rejection/removal of spoofed forwarding headers passed with a non-root
  read-only Caddy container. The overlay and API changes were staged on the
  VPS but not started. Public certificates, the production proxy path,
  Vercel, API auth and firewall behavior still need end-to-end verification.
- The HTTPS overlay rendered successfully on the VPS with non-secret dummy
  paths; the timer remains uninstalled. Image group IDs 101 and 999 map to
  existing host groups, so they must not be used for group-readable secrets.
  PostgreSQL 16.14 `initdb` succeeded in a disposable tmpfs with UID 999 and
  an unused numeric GID 11002; TLS key permissions and all actual production
  UID/GID mappings still require separate validation.
- The operator created `/var/lib/comunio-caddy` with UID 10002, GID 11003 and
  mode 0700. A non-root, network-isolated Caddy container using digest
  `sha256:ce773ec7a742ce15ee6bf2bb5f65882b9e2a4487b10733e6f1484f86e6b5d8bc`
  verified access to that directory and validated the staged configuration.
  No proxy was started and no public certificate was requested.
- A non-secret Compose input file was staged with mode 0600, image digests or
  local image IDs, the selected API domain and Vercel origin. Both application
  images passed a network-isolated import test with UID 100/GID 11001, and
  the HTTPS overlay rendered successfully with these inputs.
- Actual service secrets and PostgreSQL TLS certificates were installed with
  root ownership and isolated numeric groups; restricted read-only container
  access and file ownership were checked. The CA private key was encrypted
  locally and its decryption verified; it was not copied to the VPS. The
  one-year service certificates expire on 2027-11-07 and require renewal.
- The second preliminary dump was restored into a separate VPS project and
  compared with an independent local tmpfs restore. All nine public table row
  counts, column metadata, constraints, indexes and sequence states matched.
  Production client certificates established TLS; a wrong-role certificate
  was rejected. API SELECT worked and writes, including temporary-table
  creation, were denied even with the read-only transaction mode overridden.
- The isolated API passed readiness, protected read, missing-secret, invalid
  login and Origin checks. A public Let's Encrypt certificate was issued for
  the selected domain. Public HTTPS readiness, authenticated read requests,
  HTTP-to-HTTPS redirect and rejection of missing proxy authentication passed;
  external probes reached ports 80/443 but not 5432/8000. This does not prove
  successful interactive login through Vercel. HTTP/3 was disabled because
  its UDP port is not published. The isolated test containers, volume and
  networks were subsequently removed; Caddy certificate storage remains.
- The AWS EventBridge ingest rule was disabled; the exporter checked for
  running or pending ingest tasks and source sessions with write privileges.
  The final encrypted backup `comunio-migration-3211c2f8fc77.dump.gpg` has
  SHA-256 `8e114718f56f5c7cc9bc39dc8b7e5f33b692d49c2e59bd9f09e4df981fb1295c`.
  An isolated local restore matched source snapshot row counts for all nine
  public tables. The temporary AWS access resources were cleaned up.
- The final dump was restored into the new VPS production volume. A separate
  local restore matched its nine table row counts, columns, constraints,
  indexes and sequence states. Production TLS client certificates, wrong-role
  rejection, API SELECT and denied API writes were verified. The VPS HTTPS
  API passed readiness and authenticated-read checks; direct unauthenticated
  access was rejected and external probes could not reach ports 5432/8000.
- One controlled manual VPS ingest succeeded (run 80, 600 records); its
  success record and absence of duplicate player/day snapshots were checked.
  The user timer was then enabled, with the next run at 06:00 UTC on
  2026-11-08. The AWS ingest rule remained disabled. Vercel was switched to
  the VPS: successful login and list requests reached the VPS API. Detail
  routes sent `undefined` IDs and failed; the frontend fix must be deployed
  and interactively accepted. AWS API and rollback resources remain available.
- A Windows GnuPG command intended to discard plaintext temporarily created
  `NUL.part` containing a decrypted preliminary dump. The file was removed;
  physical erasure from the underlying storage cannot be guaranteed.

## Runtime checks still required on an authorized isolated VPS

Use a unique Compose project name (`-p`), a newly created temporary test
directory, synthetic test-only TLS CA/server/client certificates and
credentials, and an approved immutable PostgreSQL 16 image. Confirm the
project's named volume is new and empty before invoking the bootstrap helper.
Do not use the production Compose project name, production secret paths,
production certificates, or production database volume.

The following have **not** been run:

- systemd lock contention or missed-run behavior.

The frontend detail-page fix and full interactive acceptance are not yet
deployed or demonstrated by this report. Keep AWS rollback resources until
acceptance and the agreed rollback period are complete. Automated
monitoring and alerting are deliberately deferred until after migration; manual
checks are also initially omitted at the operator's accepted risk. See the
[VPS runbook](README.md) for the outstanding monitoring TODO and current gates.
