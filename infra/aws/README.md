# AWS deployment baseline

Infrastructure-Version: v0.5.4
Dokumentationsstand: 2026-09-19

## AP-14.1: HTTPS CloudFront ingress

When `api_enabled = true`, the API is exposed through a CloudFront distribution.
Use its `api_cloudfront_domain_name` output as the API base URL in the Vercel
server-side proxy. CloudFront redirects viewer HTTP requests to HTTPS, disables
caching for all paths (including `/auth/*` and `/api/*`), and forwards cookies,
`Authorization`, `Content-Type`, `Origin`, and query strings to the API. The
CloudFront-generated `CloudFront-Viewer-Address` is also forwarded for per-viewer
login throttling. Authorization is
included in a zero-TTL cache policy because CloudFront requires this to forward
that header; it is never cached. The ALB security group allows inbound TCP/443
only from AWS's CloudFront origin-facing managed prefix list; its HTTP listener
is not reachable through that security group.

These are Terraform configuration changes only; they do not alter an existing
AWS deployment until reviewed and applied. Do not send session cookies,
authorization headers, or other credentials to the legacy HTTP ALB endpoint.

Before enabling the API, provision these inputs:

1. A public DNS hostname for the ALB origin (for example, `api-origin.example.com`)
   with DNS resolving to the API ALB.
1. An issued, publicly trusted ACM certificate in `aws_region` whose SAN covers
   that exact hostname. Complete ACM DNS validation before applying Terraform.
1. Set `api_origin_domain_name` and `api_origin_certificate_arn` in the
   environment's Terraform input file (not this repository).
1. Set `api_allowed_origins` to the exact production Vercel origin; the Terraform
   default permits only localhost and is not suitable for production login.

The custom origin hostname and certificate are mandatory because the ALB's
AWS-generated `*.elb.amazonaws.com` hostname cannot be covered by a customer
certificate. CloudFront uses `https-only` to the ALB and validates the origin
certificate; do not substitute HTTP or a self-signed certificate. The viewer
uses CloudFront's default `*.cloudfront.net` certificate, so a separate
CloudFront viewer-domain certificate in `us-east-1` is not required unless a
custom viewer hostname is added later. The origin hostname must continue to
resolve to this ALB after deployment.

The SG prefix-list restriction allows connections originating from CloudFront's
origin-facing network, not only this one distribution. This is the AP-14.1
network-boundary option; do not expose additional ALB listeners or add a
`0.0.0.0/0` ingress rule. Existing ALB CloudWatch alarms continue to cover API
latency and 4xx/5xx rates. CloudFront distributions have standard
request/error/latency metrics in CloudWatch; enable additional detailed metrics
only if operational needs justify their cost. The distribution uses
`PriceClass_100` (lower-cost edge coverage); CloudFront request and data-transfer
charges can apply outside any eligible Free Tier quotas, and the ALB remains a
separately billed resource.

## API deployment status

The API remains disabled. The last verified deployment used an internet-facing
HTTP ALB before AP-14; the current Terraform changes add an HTTPS-only CloudFront
path but have not been applied. The ingest scheduler, database, and snapshot
pipeline remain active.

Re-enable the API only when the frontend integration starts:

```hcl
api_enabled = true
```

The API requires both the AP-13.a proxy bearer token and the AP-14 login session.
Configure the proxy token as
`API_PROXY_SECRET` in Vercel and as the AWS Secrets Manager secret referenced by
`api_proxy_secret_arn`.

The legacy HTTP API endpoint from the earlier deployment is:

```text
http://comunio-prod-api-1413412868.eu-central-1.elb.amazonaws.com
```

Previously verified endpoints (before AP-14; not a live status check):

- `/health/live` -> HTTP 200
- `/health/ready` -> HTTP 200 with database connectivity
- `/api/v1/players?limit=1` -> HTTP 200

The endpoint above is not an HTTPS endpoint and must not be used for
authentication credentials. The AP-14.1 CloudFront deployment and its TLS
origin prerequisites must be completed before re-enabling the API for auth.

The earlier MVP used `assign_public_ip=true`, an HTTP listener, Vercel CORS for
`https://comunio-data-website.vercel.app`, a mandatory proxy bearer token, and a
separate PostgreSQL read-only user/secret. AP-14.1 replaces direct access to that
HTTP endpoint with the CloudFront HTTPS origin described above. The Vercel
server-side proxy must call the CloudFront hostname, never the ALB hostname.
CloudFront is the low-operations ingress choice instead of a separate
ECS/Fargate proxy or API Gateway. AWS WAF, private API subnets, and NAT remain
future hardening options; they are not substitutes for the AP-14.1 TLS and
origin-network restrictions.

The AWS PowerShell scripts set `AWS_CLI_CONNECT_TIMEOUT=10` and
`AWS_CLI_READ_TIMEOUT=30` and verify `aws sts get-caller-identity` before running.
Expired credentials therefore fail fast instead of leaving an AWS CLI process
waiting indefinitely.

## AP-14.2: authentication secret lifecycle

The API login secret is separate from the Comunio credentials, database URL, and
AP-13.a proxy-token secrets. Create it from an authenticated operator session;
the helper prompts for the username and password without putting credentials in
shell history or command-line arguments:

```powershell
python scripts/aws/manage-auth-secret.py create
```

The helper stores only `username`, a bcrypt Cost-12 `passwordHash`, and a
cryptographically random `jwtSecret` in `comunio/auth`. It prints the secret ARN,
not secret contents. Pass that ARN as `auth_secret_arn` in the protected
Terraform input file; Terraform does not create or read the secret value.

Rotate the login password (existing JWT sessions remain valid):

```powershell
python scripts/aws/manage-auth-secret.py rotate-password
```

Rotate the JWT signing key to revoke all existing sessions:

```powershell
python scripts/aws/manage-auth-secret.py rotate-jwt
```

After either operation, deploy a new API task revision or force a new ECS
deployment so every process discards its cached secret and reads the new
Secrets Manager version. Verify the service is healthy and that login works
before ending the operator session. Do not print, copy into Terraform variables,
or commit the secret JSON or generated values. The task role is granted
`secretsmanager:GetSecretValue` only for the configured auth-secret ARN.

### Emergency private switch

The API remains disabled as the immediate no-frontend measure. Re-enabling it
creates the HTTPS CloudFront path only when the required origin hostname and
regional ACM certificate inputs are supplied. This Terraform configuration does
not make the ALB internal; its security group instead restricts inbound traffic
to CloudFront's origin-facing managed prefix list.

## API database access

The public API service uses a separate PostgreSQL role with `SELECT`-only
permissions and a separate Secrets Manager secret. It must not reuse the ingest
`DATABASE_URL` secret or the Comunio credentials.

Provision the role and raw DSN secret manually from an authenticated operator session:

```powershell
$env:MASTER_DATABASE_URL_SECRET_ARN = "arn:aws:secretsmanager:<region>:<account>:secret:<ingest-database-secret>"
$env:API_DATABASE_URL_SECRET_NAME = "comunio-prod/api-database-url"
$env:API_DATABASE_ROLE = "comunio_api_readonly"
python scripts/aws/provision-api-readonly-user.py
```

The script never prints the password or DSN. The resulting secret contains the raw
`DATABASE_URL` value expected by ECS secret injection. Set the future API task's
`api_database_url_secret_arn` to that secret; the ingest task continues using
`database_url_secret_arn` with its write-capable role.

This repository now includes a lean AWS baseline for the backend ingest job:

- Docker image build from `backend/Dockerfile`
- ECR repository for image storage
- ECS Fargate scheduled task for the manual snapshot runner
- CloudWatch log group for task output
- EventBridge schedule trigger
- Login-retry safeguard (AP-9.2): the container retries a failed Comunio login up to `login_retry_attempts` times (default 3), 5 minutes apart (`login_retry_wait_seconds`, default 300s), before ending the run
- CloudWatch Logs metric filter and alarm (`login-retries-exhausted`) that fires when all login retries are exhausted; optionally notifies `alert_sns_topic_arn`
- Optional managed VPC with public and private subnets
- Optional managed PostgreSQL on RDS with generated `DATABASE_URL` secret
- Low-cost API observability through native ALB CloudWatch alarms for P95, 4xx and 5xx rates

The Terraform now supports two operating modes:

1. Existing infrastructure mode
   Provide existing VPC, subnets, security groups, and Secrets Manager ARNs via variables.

1. Managed MVP mode
   Set `create_network=true` and `create_database=true` to let Terraform create the VPC, subnets, ECS security group, PostgreSQL instance, and a `DATABASE_URL` secret for you.

For a first AWS validation without live Comunio credentials, set `comunio_snapshot_file=/app/tests/sample_snapshot.json`. In that mode the ECS task uses the bundled fixture snapshot instead of live login.

## Expected secrets

Create these secrets before applying Terraform:

1. `database_url_secret_arn`
   Plain string secret containing the full PostgreSQL connection string, for example:

```text
postgresql://user:password@db-host:5432/comunio?sslmode=require
```

1. `comunio_credentials_secret_arn`
   JSON secret consumed by the current backend code:

```json
{
  "username": "user@example.com",
  "password": "super-secret"
}
```

## Deployment flow

1. Build and push the immutable image tag.
1. Confirm the SNS subscription if email alerting is required.
1. Apply Terraform.
1. Run migrations once with an ECS command override.
1. Enable the schedule for recurring snapshots.

When `create_database=true`, Terraform creates the database URL secret automatically and you do not need to provide `database_url_secret_arn`.
When `comunio_snapshot_file` is set, you do not need `comunio_credentials_secret_arn` for the first infrastructure validation.

## Remote Terraform state (AP-10a)

Local state (`terraform.tfstate`) is git-ignored but has no locking, durability, or shared access. The active backend uses a versioned/encrypted S3 bucket with Terraform's native S3 lockfile (`use_lockfile = true`). The existing DynamoDB table is retained as a legacy managed resource and is not used by the active backend. Backend activation changes where live production state lives, so it must be run deliberately, not as part of routine `terraform apply`:

```powershell
aws configure export-credentials --format powershell | Invoke-Expression
terraform init
terraform apply `
  -target=aws_s3_bucket.tfstate `
  -target=aws_s3_bucket_versioning.tfstate `
  -target=aws_s3_bucket_server_side_encryption_configuration.tfstate `
  -target=aws_s3_bucket_public_access_block.tfstate `
  -target=aws_s3_bucket_lifecycle_configuration.tfstate `

# then enable/reconfigure the backend "s3" block in backend.tf
terraform init -migrate-state   # only if the state is still local
terraform init -reconfigure     # use when the state is already in S3
terraform plan                  # verify no unexpected diff
```

Rotation note: `git ls-files`/`git log` confirm `terraform.tfstate*` and `terraform.tfvars` were never committed, so there is no Git/GitHub exposure vector for the RDS master password stored in state. Rotation is therefore treated as a scheduled P2 hardening step (documented in `architecture.md` §5.2), not an immediate P1 gate.

## Build and push

```powershell
Set-Location backend
docker build -t comunio-backend-aws:<immutable-tag> .
aws ecr get-login-password --region <region> |
  docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker tag comunio-backend-aws:<immutable-tag> <account>.dkr.ecr.<region>.amazonaws.com/comunio-backend-ingest:<immutable-tag>
docker push <account>.dkr.ecr.<region>.amazonaws.com/comunio-backend-ingest:<immutable-tag>
```

Windows helper:

```powershell
./scripts/aws/push-image.ps1 -Region eu-central-1
```

## Terraform apply

```powershell
Set-Location infra/aws/terraform
terraform init
Copy-Item terraform.tfvars.example terraform.tfvars
terraform apply
```

Windows helper:

```powershell
./scripts/aws/apply-infra.ps1
```

For an MVP with fully managed networking and database, the example file is already set up for:

- a dedicated VPC
- public ECS subnets with public IP assignment for outbound access
- private RDS subnets
- generated `DATABASE_URL` secret from the created PostgreSQL instance

For the example file, the first deploy path is fixture-based and does not require live Comunio credentials.
For restricted or free-tier AWS accounts, the example also pins `db_backup_retention_days = 1` to satisfy RDS account limits.

## One-time migration run

Use the generated cluster, task definition, and subnets from Terraform outputs.
Override the default snapshot command with the migration runner:

```powershell
aws ecs run-task \
  --cluster <cluster-name> \
  --launch-type FARGATE \
  --task-definition <task-definition-arn> \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-1,subnet-2],securityGroups=[sg-1],assignPublicIp=DISABLED}" \
  --overrides '{"containerOverrides":[{"name":"ingest-runner","command":["python","-m","migrations.runner"]}]}'
```

Windows helper:

```powershell
./scripts/aws/run-migrations.ps1 -AssignPublicIp
```

## Manual snapshot run

To trigger the snapshot task once before enabling the scheduler:

```powershell
./scripts/aws/run-snapshot.ps1 -AssignPublicIp
```

## Runtime model

- Default container command runs `python -m src.ingest.runner --run-type manual --mode snapshot`.
- `DATABASE_URL` is injected directly from Secrets Manager by ECS.
- `COMUNIO_SECRET_NAME` is set to the Comunio credentials secret ARN.
- The task role is allowed to call `secretsmanager:GetSecretValue` only for the Comunio credentials secret.
- If Terraform creates the database, the RDS security group only accepts PostgreSQL traffic from the ECS task security group.
- If `comunio_snapshot_file` is set, the task bypasses live Comunio login and can validate the AWS path end to end.
