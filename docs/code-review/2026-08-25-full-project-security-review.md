# Code Review: Full Project Security Review

**Review date:** 2026-08-25\
**Scope:** Full repository, including backend, migrations, Dockerfile, Terraform/IaC, AWS scripts, configuration, tests, and documentation\
**Ready for Production:** No\
**Critical Issues:** 0 confirmed\
**High Issues:** 1 confirmed\
**Medium Issues:** 3 confirmed\
**Low Issues:** 2 observations

## Executive Summary

The project has a narrow current attack surface because it is an ingest worker without a public API or frontend in the repository. Parameterized SQL is used, external HTTP requests do not disable certificate verification, and Terraform state and `terraform.tfvars` are ignored and are not tracked by Git.

Production readiness is nevertheless **No** until raw exception details are removed from logs and the remaining deployment controls are made explicit and reproducible. The AWS live task has already used Secrets Manager credentials successfully, but the application still contains a development ENV fallback and the deployed Fargate task currently uses public IP assignment and the mutable `latest` image tag.

## Priority 1: Must Fix

### H1. Raw exception details are written to application logs

- **Severity:** High
- **Category:** OWASP A09 Logging and Monitoring Failures; Information Disclosure
- **Evidence:** `backend/src/ingest/runner.py`, login, snapshot, and persistence exception handlers pass `detail=str(exc)` to `_log()`.
- **Impact:** API response bodies, database hostnames, filesystem paths, or other sensitive operational data can reach CloudWatch Logs. This expands the blast radius of a log-reader compromise and can expose personal or infrastructure data.
- **Minimal fix:** Replace raw exception details with a fixed error taxonomy and a bounded, explicitly sanitized diagnostic. Do not log credentials, tokens, connection strings, response bodies, local paths, or raw tracebacks. Add unit tests for the login, snapshot, and persistence paths.
- **Validation:** Assert that representative exceptions containing a password, token, PostgreSQL URL, ARN, email address, and path produce no sensitive values in captured log output. Review CloudWatch logs after deployment.
- **Production decision:** Blocking.

## Priority 2: Must Fix Before Broader Production Use

### M1. Public IP is enabled for scheduled Fargate tasks

- **Severity:** Medium
- **Category:** Zero Trust; Network Exposure; AWS Well-Architected Security
- **Evidence:** `infra/aws/terraform/terraform.tfvars` sets `assign_public_ip = true`; the active EventBridge target uses `AssignPublicIp=ENABLED`.
- **Impact:** The task receives direct internet addressing. This increases exposure and makes egress control, incident investigation, and network policy enforcement harder.
- **Minimal fix:** Move ECS tasks to private subnets, set `assign_public_ip = false`, and provide the required controlled egress path through NAT or appropriate VPC endpoints. Validate Secrets Manager, ECR, and Comunio API reachability before switching production.
- **Validation:** Terraform plan must show `AssignPublicIp=DISABLED`; verify the task ENI has no public address and run a scheduled smoke test.
- **Trade-off:** NAT gateways add fixed and per-GB cost. For the current low-volume worker, this is a security improvement with a measurable monthly cost, so the MVP may explicitly accept public egress only as a documented temporary exception.

### M2. Mutable container image tag `latest`

- **Severity:** Medium
- **Category:** Supply-chain security; Change control; Reproducibility
- **Evidence:** `infra/aws/terraform/terraform.tfvars` sets `image_tag = "latest"`; `infra/aws/terraform/main.tf` uses that tag in the ECS task definition.
- **Impact:** A task can run different code without a task-definition source change. Rollback and forensic attribution become unreliable, and an accidental or compromised push can change production behavior.
- **Minimal fix:** Publish immutable version or commit-SHA image tags and deploy the exact tag. Optionally enforce ECR tag immutability after the migration.
- **Validation:** ECS task definition references a non-mutable tag or image digest; redeploying the same Terraform configuration produces no unexpected image change.
- **Trade-off:** Releases require an explicit build/push/deploy step, but this materially improves rollback and auditability.

### M3. Production policy and development fallback are not structurally separated

- **Severity:** Medium
- **Category:** Secret management; Configuration safety
- **Evidence:** `backend/src/config.py` reads `COMUNIO_EMAIL` and `COMUNIO_PASSWORD`, and `backend/src/ingest/comuniopy_client.py` supports ENV credentials when secret mode is not required. Production defaults secret mode on, and the deployed task explicitly sets `COMUNIO_REQUIRE_SECRET_MODE=true`; therefore this is a defense-in-depth/configuration risk, not a confirmed production bypass.
- **Impact:** A future deployment with an incorrect `APP_ENV` or explicit `COMUNIO_REQUIRE_SECRET_MODE=false` could silently use environment credentials. Environment values are easier to expose through task definitions and operational tooling than Secrets Manager references.
- **Minimal fix:** Make production mode reject ENV credentials unconditionally. Keep ENV credentials available only behind an explicit local-development configuration, and add a startup/deploy gate that rejects production settings without `COMUNIO_SECRET_NAME`.
- **Validation:** Test production settings with both ENV credentials and a missing secret name; startup must fail before login. Inspect the ECS task definition for absence of `COMUNIO_EMAIL` and `COMUNIO_PASSWORD`.
- **Trade-off:** Local convenience is reduced; production behavior becomes deterministic and auditable.

## Priority 3: Recommended Hardening

### L1. No repository CI security gate is present

- **Severity:** Low
- **Category:** Supply-chain security; Secure delivery
- **Evidence:** No GitHub Actions workflow or equivalent CI configuration is present in the repository file set reviewed.
- **Impact:** Tests, dependency scanning, Terraform validation, secret scanning, and image checks are not automatically enforced before changes reach the deployment path.
- **Recommendation:** Add CI checks for `pytest`, Terraform format/validate/plan, dependency vulnerability scanning, secret scanning, and container image scanning. Block deployment on high/critical findings.

### L2. Terraform local state remains a sensitive local artifact

- **Severity:** Low for the current Git state, potentially Critical if mishandled
- **Category:** Secret management; Infrastructure governance
- **Evidence:** `.gitignore` correctly ignores `*.tfstate*` and `*.tfvars`; verification found no tracked state or tfvars files and no Git history entries for them. The local Terraform state nevertheless contains infrastructure and secret-related values and no remote backend is configured.
- **Impact:** Loss, workstation compromise, accidental sharing, or future force-add can expose state and create concurrent-apply or recovery problems.
- **Recommendation:** Migrate production to a versioned, encrypted remote backend with locking and least-privilege access. Rotate any credentials that were ever exposed outside the protected workstation. Keep state out of commits and incident attachments.
- **Validation:** `git ls-files` returns no state/tfvars files; backend configuration uses encrypted remote state and locking; access is limited to the deployment principal.

## Confirmed Safe or Not Confirmed as Vulnerable

- **SQL injection:** No confirmed finding. Database statements reviewed use static SQL with bound parameters; no dynamic table/column interpolation was found.
- **TLS verification for the Comunio API:** No confirmed finding. `requests` does not use `verify=False`, and its default certificate verification remains enabled. Certificate pinning is not required for this finding.
- **Database TLS:** Existing `connection.py` rejects missing or weak `sslmode`; the generated production database URL uses `sslmode=require`.
- **Snapshot path and size controls:** Existing tests cover the configured base-directory and maximum-size checks. Nested payload validation should continue to be expanded as the fixture/API contract grows.
- **IAM scope:** The reviewed Terraform grants the task role access to the specific Comunio secret and grants the execution role the permissions required by the ECS managed execution policy plus the specific database URL secret. A periodic IAM simulation is still recommended.

## OWASP and Zero-Trust Coverage

- **A01 Broken Access Control:** No public API is currently implemented. ECS task and EventBridge roles are scoped to the known task, roles, and secrets; verify with IAM policy simulation before production expansion.
- **A02 Cryptographic Failures:** Database TLS and encrypted RDS storage are configured. Remote Terraform state encryption remains outstanding.
- **A03 Injection:** No confirmed SQL injection; parameterized database writes are used. Continue schema/type validation for imported snapshots.
- **A05 Security Misconfiguration:** Public task IP, mutable image tag, and missing CI gates remain.
- **A07 Identification and Authentication Failures:** Comunio login uses Secrets Manager in the deployed production task; make that policy structurally non-overridable.
- **A09 Logging and Monitoring Failures:** Raw exception logging is the main confirmed application finding.
- **A10 SSRF:** No user-controlled URL input or public API endpoint was found in the reviewed project.
- **Zero Trust:** Least-privilege roles and private RDS are positive controls; public task addressing and local-only state are remaining gaps.

## Risk Summary

- **Critical:** 0 confirmed; state exposure would become critical if ignored or committed.
- **High:** 1 confirmed, raw exception details in logs.
- **Medium:** 3 confirmed, public task IP, mutable image tag, and structurally overridable credential fallback.
- **Low:** 2 recommendations, missing CI security gates and local-only Terraform state.

## Decision

- **Production Ready:** No.
- **Blocking issue:** Remove raw exception details from logs and add regression tests.
- **Required before routine production operation:** Make production secret mode non-overridable, replace `latest` with immutable image references, and decide whether public Fargate egress is an explicitly accepted MVP exception or must be replaced by private networking.
- **Residual testing gaps:** No CI pipeline, no automated dependency/secret scan, no IAM policy simulation in CI, and the three-consecutive-scheduled-run acceptance criterion is not yet evidenced in this review.
