# VPS deployment slice (not approved for production)

This directory contains a deployment definition for a single Ubuntu VPS:
PostgreSQL, a one-shot Ingest container, and an optional API container with a
systemd **user** timer. The API is in an opt-in Compose profile, has no
published backend port, and has no HTTPS ingress or reverse proxy in this
slice. AWS files and deployment definitions are not changed.

CI builds the Ingest and API images, checks the rendered Compose profiles and
security boundaries with `python infra/vps/tests/test_compose.py`, checks the
scheduler contract with `python infra/vps/tests/test_systemd.py`, verifies the
systemd unit syntax and UTC calendar, and tests `flock` contention. The
repository security scan remains in place. Trivy's config scanner did not
recognize the Compose file in a local check; the explicit Compose assertions
are therefore the VPS configuration gate. These checks do not start the VPS
stack or prove TLS, volume persistence, scheduler execution, or restore.

**No cutover is approved. Do not enable the timer or run a live Ingest.**
The operator reports that the AWS API is live; older repository documentation
describes it as disabled, so verify the actual state before any plan or change.
Do not disable the AWS API or its dependencies before a separately approved
cutover. The source RDS version is not established by this repository. The
current operator also lacks sudo, user lingering is disabled, and monitoring
and a tested restore are outstanding. Those are deployment blockers, not
configuration steps this directory can bypass. No server access or production
action is performed by these files.

## What this deployment does and does not do

- `db` is a persistent PostgreSQL service on a private, internal Compose
  network. It has no published host port and accepts only TLS client
  certificates for `comunio_ingest` and, only when separately approved, the
  read-only `comunio_api_readonly` role.
- `db-volume-init` is an explicitly invoked, one-shot bootstrap helper for a
  **new empty** named volume. It is not `privileged`; it runs only `install`
  with `CHOWN` and `FOWNER`, has no network or secrets, and changes only the
  volume root directory's owner/mode. PostgreSQL initialization and runtime
  then run under the selected non-root UID/GID.
- `db-initdb` is a separate, one-shot, non-root initialization service. It
  has only the data volume, no network, no host HBA/TLS mounts, no secrets,
  and no added capabilities. It initializes with local peer auth and rejects
  all TCP authentication until the normal DB service starts with its mounted
  TLS files and HBA policy.
- `ingest` is a short-lived, non-root job. It is not started by `compose up`;
  the systemd user service runs it once and returns its exit status. Both the
  timer and supported manual starts use the same host lock.
- `api` is behind the opt-in `api` Compose profile, uses separate API secrets,
  a separate database URL and client certificate, and has no `ports:` entry.
  It is not externally reachable in this design.
- Secret file contents are never Compose environment values or command-line
  arguments. Only file paths are passed. The application reads
  `COMUNIO_SECRET_FILE` and `DATABASE_URL_FILE`.
- `pg_hba.conf` permits local peer administration and TLS certificate
  authentication for the Ingest and gated API roles. It rejects non-TLS TCP
  connections.
- There is no HTTPS ingress or reverse proxy. Do not publish the API port or
  add a proxy as a shortcut. Public API activation requires a separate design
  and approval after the trusted-proxy/header and authentication gates below.
- The database image has no default major version. Select and pin the image
  only after checking the actual RDS engine version, extensions, collation,
  encoding, schema, and supported upgrade/dump-restore path. Never use `latest`.

The Compose file uses an explicit numeric `user:` for both services. The
container process IDs are therefore the configured `APP_UID:APP_GID` and
`POSTGRES_UID:POSTGRES_GID`; secret ownership must match those identities.
This avoids guessing the user created by a particular image. The image
references, numeric IDs, `PGDATA`, and host paths below are non-secret
deployment inputs.

## Files and host-only inputs

Repository files:

- `compose.yaml`: DB and one-shot Ingest services, networks, volume, and
  read-only file mounts, plus the opt-in empty-volume permission helper.
- `postgres/pg_hba.conf`: database access policy.
- `systemd/comunio-ingest@.service` and `.timer`: shared-lock one-shot and
  daily UTC schedule.
- `comunio-vps.env.example`: non-secret Compose interpolation template.
- `.gitignore`: excludes local deployment inputs and data.

Create these directories **outside the repository** on the VPS:

- a private secret directory containing `comunio.json` and `database-url`;
- separate API files `api-auth.json`, `api-proxy-secret`, and
  `api-database-url` (only when preparing the separately gated API profile);
- a TLS directory containing `ca.crt`, `server.crt`, `server.key`,
  `ingest.crt`, `ingest.key`, and optionally `api.crt`/`api.key`;
- `%h/.config/comunio-vps.env`, containing non-secret Compose settings only.

Never put private keys, DB URLs, Comunio credentials, backups, or dumps in Git,
the image build context, CI artifacts, shell arguments, service environment
values, or logs. `compose config` and `docker inspect` should expose paths and
image references only, never file contents.

## Safe prerequisites — operator with host administration

An authorized host administrator must perform and record the following before
deployment:

1. Verify Ubuntu, Docker Engine/Compose versions, disk capacity, NTP/time
   synchronization, host firewall, existing listeners, and the approved
   operator access/recovery path. No firewall rule should expose PostgreSQL
   (`5432`) or Uvicorn (`8000`).
2. Confirm who is allowed to use the Docker socket. Membership in the
   `docker` group is effectively root-equivalent; grant it only with explicit
   approval. A user without sudo cannot install the units system-wide, change
   host ownership, grant Docker access, or enable lingering.
3. Determine the actual RDS PostgreSQL major/minor version and extensions.
   Choose a destination major only after a compatibility review and a
   successful isolated restore. Set `POSTGRES_IMAGE` to an immutable
   version-and-digest reference for that choice. Set `PGDATA` and the volume
   target to the data path supported by that exact image. The current source
   version is not established by this repository, so this plan deliberately
   selects no PostgreSQL major version.
4. Build and approve the Ingest image, then set `INGEST_IMAGE` to its immutable
   digest reference. The runtime Compose definition does not build images on
   the VPS.
5. Select stable non-root numeric IDs. Set `APP_UID`/`APP_GID` to the process
   identity used by the Ingest and API containers and `POSTGRES_UID`/`POSTGRES_GID` to
   the `postgres` identity in the exact pinned database image. Verify these
   IDs against each image before creating host files or the data volume.
6. Prepare TLS materials through an approved CA process:
   - a private CA certificate (`ca.crt`) trusted by both PostgreSQL and the
     Ingest client;
   - a PostgreSQL server certificate with `serverAuth` and SAN `DNS:db`;
   - an Ingest client certificate with `clientAuth` and subject CN
     `comunio_ingest`, matching the DB role;
   - only for the separately gated API, an API client certificate with
     `clientAuth` and subject CN `comunio_api_readonly`.
   Keep CA private keys offline. Private service keys must be unencrypted for
   unattended PostgreSQL/libpq startup unless a separately tested credential
   unlock mechanism is approved; protect them with restricted host access and
   encrypted host storage. Do not copy CA private keys to the VPS.
7. Prepare `comunio.json` as UTF-8 JSON with the existing
   `{"username": "...", "password": "..."}` shape. Prepare `database-url` as
   a PostgreSQL DSN with **no password**, for example the following non-secret
   connection parameters:

   `host=db`, the selected database and role, `sslmode=verify-full`,
   `sslrootcert=/run/certs/ca.crt`, `sslcert=/run/certs/ingest.crt`, and
   `sslkey=/run/certs/ingest.key`.

   The URL is read from `DATABASE_URL_FILE`; credentials to PostgreSQL are
   client-certificate based, not password-based. The hostname must remain
   `db`, and the server certificate must include `DNS:db`.
8. Provision PostgreSQL roles and grants through the controlled local
   administration path. Keep superuser access local to the container's
   `postgres` OS identity. Do not mount an administrative credential into
   Ingest or API. The Ingest role gets only the DDL/DML rights needed by the
   currently supported migrations and job. The API role, if provisioned,
   gets `SELECT` only on the approved tables/views; prove writes are denied.
9. Create host directories and files with an approved owner/mode plan:
   - each Ingest-readable file is owned by `root` and the numeric
     `APP_GID`, mode `0440`; the Ingest process runs with that primary GID;
   - API auth, proxy, database URL, and client-key files are mounted only into
     `api` and are owned by `root` and the numeric `APP_GID`, mode `0440`;
   - the DB server key is owned by `root` and `POSTGRES_GID`, mode `0440`,
     which is PostgreSQL's supported root-owned/group-readable key mode;
     verify startup accepts it for the pinned image;
   - certificate/CA files are read-only and not writable by the service;
   - directories are not listable by unauthorized users. The deployment
     operator must have only the traversal rights Compose needs.

   Do not rely on Compose `uid`, `gid`, or `mode` metadata to secure
   file-backed mounts; host ownership and the explicit container `user:` are
   the control. Check actual ownership from inside a disposable test container
   before mounting production values.
10. Copy `comunio-vps.env.example` to `%h/.config/comunio-vps.env` and fill
    the required PostgreSQL/Ingest image references, numeric IDs, `PGDATA`,
    and absolute host directory paths. Do not place secret values in it.
    Before the separately approved API profile, also set its immutable
    `API_IMAGE` reference and reviewed `API_ALLOWED_ORIGINS`.
    `INGEST_RUN_TYPE` is set by the systemd template instance (`manual` or
    `scheduled`), not by this file.
11. Monitoring/alerting and a protected migration backup with a successful
    restore test are not yet established. Define and test them before any
    production timer or cutover.

## Initial database and Compose procedure

Perform this only in an isolated staging environment after the prerequisites
above. It is an operator procedure, not authorization for a production run:

1. Validate interpolation using non-secret dummy values and inspect the
   rendered Compose model. Confirm no published ports, no secret contents,
   and that the database image is the approved immutable digest.
2. Confirm the named volume is genuinely new and empty before initialization.
   Never remove or recreate a volume to make this procedure pass. The Compose
   project name is `comunio-vps`; inspect the corresponding
   `comunio-vps_postgres-data` volume using the approved operator path. If it
   already contains a database or its state is uncertain, stop and use the
   reviewed restore/migration procedure instead.
3. On a new volume only, run the opt-in `db-volume-init` service once. It
   executes `install -d` on the mounted `PGDATA` directory, setting owner to
   the selected PostgreSQL UID/GID and mode `0700`. A fresh named volume may
   otherwise be root-owned and unwritable by the non-root PostgreSQL process.
   The helper is an ephemeral UID 0 container, but it is **not privileged**:
   it has only `CHOWN` and `FOWNER`, no network, no secrets, a read-only root
   filesystem, and access to that one named volume. It does not recursively
   chown data. Run it only against a confirmed empty volume.

   From the deployment checkout, the command shape is:

   ```sh
   docker compose --env-file "$HOME/.config/comunio-vps.env" \
     --project-directory "$HOME/comunio/infra/vps" \
     -f "$HOME/comunio/infra/vps/compose.yaml" \
     --profile bootstrap run --rm db-volume-init
   ```

4. Initialize the directory as the configured non-root PostgreSQL UID/GID
   using the separate `db-initdb` service. It invokes the selected image's
   `initdb` directly, bypassing the official image entrypoint. Set
   `--auth-local=peer` and `--auth-host=reject`; do not set `POSTGRES_PASSWORD`,
   `POSTGRES_PASSWORD_FILE`, or `POSTGRES_HOST_AUTH_METHOD`, and never use
   `trust`. This creates no TCP authentication path and requires no password
   in an environment variable or argument. `initdb` uses the non-secret
   `PGDATA` setting from Compose. It has no network and does not mount the
   eventual `pg_hba.conf` or TLS certificates; no server is started at this
   step.

   ```sh
   docker compose --env-file "$HOME/.config/comunio-vps.env" \
     --project-directory "$HOME/comunio/infra/vps" \
     -f "$HOME/comunio/infra/vps/compose.yaml" \
     --profile bootstrap run --rm db-initdb
   ```

5. Only after successful `initdb`, start the normal `db` service. Its
   Compose entrypoint directly starts the `postgres` binary as the same
   non-root UID/GID; it deliberately bypasses the upstream
   `docker-entrypoint.sh`. This avoids the official empty-volume password
   check, implicit ownership changes, and entrypoint initialization behavior.
   The volume must already contain the successful `initdb` result. The
   service command loads the repository HBA policy and the mounted TLS
   CA/server certificate/key before PostgreSQL accepts network connections.
   Its HBA rejects non-TLS TCP and requires a client certificate for the
   allowed database roles.

   ```sh
   docker compose --env-file "$HOME/.config/comunio-vps.env" \
     --project-directory "$HOME/comunio/infra/vps" \
     -f "$HOME/comunio/infra/vps/compose.yaml" up -d db
   ```
6. The DB healthcheck uses the local Unix socket
   (`/var/run/postgresql`) and the `local ... postgres peer` HBA rule. This is
   a process/readiness check; it does **not** prove TCP TLS or client
   certificate authentication. Prove those separately from an Ingest test
   container with `sslmode=verify-full`, correct `DNS:db`, CA validation, and
   the role-matching client certificate. Unknown CA, wrong hostname,
   missing/wrong client certificate, and non-TLS TCP must fail.
7. Through local peer administration, create the `comunio` database and
   `comunio_ingest` role, then apply only the required grants. Provision the
   API role only during its separately approved activation work.
8. Run migration and fixture/idempotency checks only against an isolated
   database copy. A live Comunio snapshot is not a staging smoke test.

If the selected PostgreSQL image cannot initialize and run under the explicit
non-root UID/GID with the read-only root filesystem and mounted TLS key, stop.
Do not “fix” it by making the container privileged, adding host networking, or
making secrets world-readable.

The permission helper is not a general repair tool. If an existing volume has
root-owned database files or an unexpected mode, do not run recursive `chown`
or `initdb`; stop and follow a separately reviewed restore/ownership-repair
procedure. Never use `docker compose down -v` on a volume containing data.

## systemd user timer and shared lock

The templated service uses `flock` on `%t/comunio-ingest.lock`. The timer
starts `comunio-ingest@scheduled.service`; a supported manual run starts
`comunio-ingest@manual.service`. Both instances pass through the same lock.
A lock conflict exits nonzero and is visible in the user journal.

`snapshot_job.py` uses `date.today()` for `market_values.snapshot_date`. The
Ingest container explicitly sets `TZ=UTC`, and PostgreSQL session/log timezones
are also UTC. Thus the snapshot key does not depend on the VPS host timezone or
daylight-saving changes. The date is nevertheless the UTC date **when the
process actually runs**, not the intended date of a missed schedule. A delayed
or manual run on the same UTC day upserts that day's `(player_id,
snapshot_date)` rows; if it runs after 00:00 UTC, it writes under the new UTC
date, does not backfill the missed day, and may leave a gap or create an
additional daily snapshot. Check `run_type`, UTC start time, and snapshot date
after late/manual execution; do not rerun without considering this effect.

`OnCalendar=*-*-* 06:00:00 UTC` is explicitly UTC. `Persistent=true` causes a
missed calendar activation to run after the user manager becomes active; test
this behavior and document the expected catch-up window before enabling the
timer. It does not provide monitoring or prove a successful database write.
Direct `docker` or `docker compose` starts bypass the shared lock and are
unsupported and forbidden for operators. A direct invocation can overlap a
timer or another manual job.

The timer is not enabled by these files. Once every operational gate passes,
an authorized administrator must enable user lingering for the deployment
account (for example via `loginctl enable-linger <user>`); this requires host
administrative authority. Verify `Linger=yes`. Without lingering, the user
manager/timer will not reliably survive logout or run after boot. The current
account has no sudo and lingering is disabled, so installation/activation is
currently blocked.

Install the user units under
`~/.config/systemd/user/`, then reload the user manager. Keep the timer
disabled until backup/restore, TLS/secret checks, monitoring, and the explicit
production approval are complete. Manual tests should use
`comunio-ingest@manual.service` so they use the same lock as the timer.

## Optional API profile — separate release only

The `api` service is defined but is not part of the default Compose profile.
It has no host-published port and the Compose file contains no reverse proxy.
Its required files are distinct from Ingest:

- `api-auth.json` for `AUTH_SECRET_FILE` (the validated
  `username`/`passwordHash`/`jwtSecret` format);
- `api-proxy-secret` for `API_PROXY_SECRET_FILE`;
- `api-database-url` for `DATABASE_URL_FILE`, using role
  `comunio_api_readonly`, `sslmode=verify-full`, the trusted CA, and the
  separate API client certificate/key.

The profile is **not authorized for production activation**. The `pg_hba`
entry alone does not grant data access; the role must have explicit `SELECT`
grants only, and negative write tests must pass. API secret files are mounted
only into the API container, not the Ingest service.

No HTTPS ingress is included because a safe public path cannot be established
from this repository-only change: domain/DNS/certificate ownership, external
firewall, trusted proxy peer, and forwarded-header policy have not been
verified. The current backend auth logic recognizes
`CloudFront-Viewer-Address`; that is not a trusted Contabo proxy contract.
Before any API activation, separately prove that client-supplied forwarding
headers are stripped, the backend trusts only the designated proxy peer, the
proxy is the only network path to Uvicorn, HTTPS is enforced, and the Vercel
proxy/auth/CORS/session flows pass end-to-end tests. Until then, do not start
the `api` profile, expose port 8000, or change the Vercel origin.

The operator reports that the AWS API is live. Keep it and its database/API
dependencies running until a separately approved, verified cutover. This
Compose definition does not authorize or perform AWS shutdown.

## Required validation and go/no-go

Run all checks in an isolated environment with synthetic test credentials:

- `docker compose --env-file <non-secret-test-env> -f infra/vps/compose.yaml config`
  succeeds. Review output for image digests, host paths, no secret values, and
  no DB/API `ports:` entries. Supply non-secret `API_IMAGE` and
  `API_ALLOWED_ORIGINS` test values to validate the optional profile.
- Inspect the rendered service definitions and images: `db` and `ingest` have
  non-root numeric users, `read_only`, dropped capabilities, no-new-privileges,
  resource limits, and only the required read-only file mounts. No privileged
  mode, host PID/network, Docker socket, or restart loop for Ingest.
- Confirm actual mounted file owner/group/mode matches the configured
  container UID/GID. Negative test with an unreadable secret must fail closed
  without printing the secret, path, DSN, or Comunio response.
- DB healthcheck becomes healthy; the persistent volume survives DB container
  recreation. The healthcheck is explicitly local-socket readiness, not a TLS
  test. There is no host-published `5432`.
- On a disposable new volume, the bootstrap helper is non-privileged, has only
  `CHOWN`/`FOWNER`, and changes only the volume root; `initdb` runs as the
  configured non-root PostgreSQL identity, with no network/TLS mounts and no
  password or `POSTGRES_HOST_AUTH_METHOD` environment setting. Confirm no
  `POSTGRES_PASSWORD`/`POSTGRES_PASSWORD_FILE` is present in Compose.
- TLS positive and negative tests above pass. `pg_hba.conf` rejects cleartext
  TCP, and a certificate for another role is not accepted.
- Run backend unit/integration tests, a fixture Ingest, repeated fixture
  idempotency test, and migration/restore checks against isolated data.
- For the API profile, prove its DB role cannot INSERT/UPDATE/DELETE, its
  credentials are isolated from Ingest, and route/auth behavior is correct.
  Compose validation is not API activation approval.
- On Ubuntu, verify both unit files with `systemd-analyze --user verify`,
  inspect the calendar with `systemd-analyze calendar`, test missed-run
  behavior and lock contention, and confirm the systemd service returns the
  Compose job's nonzero exit status.
- Test external monitoring/heartbeat and alert delivery before activating the
  timer. Monitoring is currently outstanding.

**Production NO-GO:** no cutover, no live VPS writer, no timer enablement, and
no AWS changes until the source RDS version and live AWS services (including
the reported-live API) are verified, migration backup/restore is proven, all
tests and monitoring pass, the VPS administrator enables lingering and
required host access, and the operator explicitly approves the cutover. API
activation additionally requires separate TLS, trusted-proxy/header, auth,
read-only-role, and Vercel end-to-end approval. Keep the AWS API active until
that cutover is separately approved and verified.
