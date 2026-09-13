# AWS deployment baseline

Infrastructure-Version: v0.5.0

## API database access

The future public API service must use a separate PostgreSQL role with `SELECT`-only
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

The Terraform now supports two operating modes:

1. Existing infrastructure mode
Provide existing VPC, subnets, security groups, and Secrets Manager ARNs via variables.

2. Managed MVP mode
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

1. Build and push the image.
2. Apply Terraform.
3. Run migrations once with an ECS command override.
4. Enable the schedule for recurring snapshots.

When `create_database=true`, Terraform creates the database URL secret automatically and you do not need to provide `database_url_secret_arn`.
When `comunio_snapshot_file` is set, you do not need `comunio_credentials_secret_arn` for the first infrastructure validation.

## Remote Terraform state (AP-10a)

Local state (`terraform.tfstate`) is git-ignored but has no locking, durability, or shared access. `state_backend.tf` defines bootstrap resources (versioned/encrypted S3 bucket + DynamoDB lock table); `backend.tf` holds the commented-out `backend "s3"` block. This migration changes where the live production state lives, so it must be run deliberately, not as part of routine `terraform apply`:

```powershell
aws configure export-credentials --format powershell | Invoke-Expression
terraform init
terraform apply `
  -target=aws_s3_bucket.tfstate `
  -target=aws_s3_bucket_versioning.tfstate `
  -target=aws_s3_bucket_server_side_encryption_configuration.tfstate `
  -target=aws_s3_bucket_public_access_block.tfstate `
  -target=aws_s3_bucket_lifecycle_configuration.tfstate `
  -target=aws_dynamodb_table.tfstate_lock

# then uncomment the backend "s3" block in backend.tf
terraform init -migrate-state   # confirm "yes" to copy existing local state
terraform plan                  # verify no unexpected diff
```

Rotation note: `git ls-files`/`git log` confirm `terraform.tfstate*` and `terraform.tfvars` were never committed, so there is no Git/GitHub exposure vector for the RDS master password stored in state. Rotation is therefore treated as a scheduled P2 hardening step (documented in `architecture.md` §5.2), not an immediate P1 gate.

## Build and push

```powershell
Set-Location backend
docker build -t comunio-backend-aws .
aws ecr get-login-password --region <region> |
  docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker tag comunio-backend-aws:latest <account>.dkr.ecr.<region>.amazonaws.com/comunio-backend-ingest:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/comunio-backend-ingest:latest
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
terraform apply -var-file=terraform.tfvars
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
