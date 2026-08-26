# AP-9 Scheduled Ingest Operability Runbook

## Scope

AP-9 runs the existing ECS Fargate snapshot task once per day through an EventBridge rule.

- Schedule: configured by `schedule_expression` (default `cron(0 6 * * ? *)`, 06:00 UTC)
- Target: ECS Fargate task `ingest-runner`
- Run type: `scheduled`
- Logs: `/ecs/comunio-prod-ingest`
- Failure handling: EventBridge retries twice, then sends the event to the SQS scheduler DLQ

## Activation and verification

1. Run `terraform validate` and `terraform plan` in `infra/aws/terraform`.
2. Confirm `enable_schedule=true` only after the live snapshot and security gates are green.
3. Apply Terraform and record the EventBridge rule name and scheduler DLQ URL from Terraform outputs.
4. Verify the rule:

```powershell
aws events describe-rule --name comunio-prod-snapshot-schedule --region eu-central-1
```

5. After the first scheduled window, verify the task and logs:

```powershell
aws ecs list-tasks --cluster comunio-prod-cluster --desired-status STOPPED --region eu-central-1
aws logs tail /ecs/comunio-prod-ingest --since 24h --region eu-central-1
```

Expected application events include `run_started`, `db_verify`, and `run_success` with a non-zero `records_written` value.

## Login retry and automated success/failure check (AP-9.2)

- On each run the container attempts login up to `COMUNIO_LOGIN_RETRY_ATTEMPTS` times (default 3), waiting `COMUNIO_LOGIN_RETRY_WAIT_SECONDS` seconds (default 300, i.e. 5 minutes) between attempts.
- Log events to look for:
  - `login_attempt_failed attempt=<n> max_attempts=<n>` on each failed attempt.
  - `login_retry_scheduled attempt=<n+1> wait_seconds=300` before each retry.
  - `login_recovered attempt=<n>` if a later attempt succeeds.
  - `run_failed stage=login attempts=<n>` if all attempts fail; the task still exits normally afterwards.
- Because the ingest task is a one-off ECS Fargate task (not an ECS service), ECS stops the container the same way after a successful run (exit code 0) and after exhausted login retries (exit code 1). No extra shutdown step is required or configured.
- A CloudWatch Logs metric filter (`comunio-prod-login-retries-exhausted`) turns `run_failed stage=login` log lines into a metric, backing the CloudWatch alarm `comunio-prod-login-retries-exhausted`. Configure `alert_sns_topic_arn` in Terraform to route this alarm to an SNS topic; without it, the alarm stays visible in CloudWatch only.

```powershell
aws cloudwatch describe-alarms --alarm-names comunio-prod-login-retries-exhausted --region eu-central-1
```

## Retry and DLQ behavior

- EventBridge retries a failed target invocation up to two times.
- Events older than one hour are not retried.
- After retries are exhausted, the event is available in the SQS scheduler DLQ for investigation.
- A successful ECS task with application exit code `0` is not retried by EventBridge.

Inspect the DLQ without exposing payloads in tickets or logs:

```powershell
$dlqUrl = terraform -chdir=infra/aws/terraform output -raw scheduler_dlq_url
aws sqs get-queue-attributes --queue-url $dlqUrl --attribute-names ApproximateNumberOfMessagesVisible --region eu-central-1
```

## Failure response

1. Check the ECS task exit code and the sanitized `error_code` in CloudWatch.
2. If the failure is `stage=login`, confirm whether the login retries (3 attempts, 5 minutes apart) already ran; the CloudWatch alarm `comunio-prod-login-retries-exhausted` fires only after all attempts are exhausted.
3. Check database availability, Secrets Manager access, image availability, and network reachability.
4. Do not paste SecretString values, credentials, connection strings, or raw exception text into incident records.
5. Re-run the task manually only after the root cause is understood:

```powershell
./scripts/aws/run-snapshot.ps1 -AssignPublicIp
```

6. Keep the schedule disabled while a systemic failure is being repaired. Re-enable it through Terraform after validation.

## Rollback

Disable the rule without destroying the task definition:

```powershell
terraform -chdir=infra/aws/terraform apply -var-file=terraform.tfvars -var="enable_schedule=false"
```

The existing manual snapshot command remains available for controlled recovery runs.

## AP-9 acceptance criteria

- EventBridge rule is `ENABLED` with the approved schedule.
- ECS target uses the pinned Fargate platform version and least-privilege EventBridge role.
- A scheduled task completes with exit code `0` and `run_type=scheduled`.
- Three consecutive scheduled runs complete successfully without duplicate market-value rows.
- Failed target invocations are retried and visible in the scheduler DLQ.
- Runbook and CloudWatch evidence are available for the first production window.
