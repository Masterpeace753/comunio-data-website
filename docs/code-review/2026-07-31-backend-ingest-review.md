# Code Review: Backend Ingest Pipeline (AP-5/AP-7)
**Ready for Production**: Conditional Yes
**Critical Issues**: 0

## Scope
Reviewed files:
- backend/src/database/connection.py
- backend/src/ingest/runner.py
- backend/src/ingest/comuniopy_client.py

## Priority 1 (Must Fix) ⛔
No open P1 findings after remediation.

## Priority 2 (Should Fix)

### 1) Medium - Raw exception details in operational logs
- Severity: Medium
- Category: OWASP A09 - Security Logging and Monitoring Failures / Information Disclosure
- Status: Mitigated
- Evidence:
  - backend/src/ingest/runner.py now logs sanitized `error_code` fields instead of raw exception payloads.
- Impact:
  - Third-party/library exception payloads may leak operational details (endpoints, stack traces, account identifiers, secret metadata) into logs consumed by broader audiences.
- Fix:
  - Replace direct exception interpolation with sanitized error codes/messages.
  - Log detailed stack traces only in protected debug channels.
  - Keep user-facing/ops-facing logs minimal and non-sensitive.
- Validation:
  - Add tests asserting that failed login/snapshot paths do not emit raw provider exception text.

### 2) Medium - Snapshot file input trusts arbitrary local path without hardening
- Severity: Medium
- Category: Zero Trust - Input Validation / Local File Access
- Status: Mitigated
- Evidence:
  - backend/src/ingest/comuniopy_client.py validates base directory, file size limit, and JSON structure.
- Impact:
  - If runtime environment variables are manipulated, process may read unintended local files or very large payloads causing data exposure/DoS.
- Fix:
  - Restrict snapshot file loading to an allowlisted base directory.
  - Enforce max file size before parsing JSON.
  - Validate schema strictly before normalization.
- Validation:
  - Add tests for path traversal attempts and oversized file rejection.

## Recommended Changes

### Example: enforce SSL mode for DB connections
```python
from urllib.parse import parse_qs, urlparse


def connect(database_url: str):
    if not database_url:
        raise ValueError("DATABASE_URL is required")

    query = parse_qs(urlparse(database_url).query)
    sslmode = (query.get("sslmode") or [""])[0].lower()
    if sslmode not in {"require", "verify-ca", "verify-full"}:
        raise ValueError("DATABASE_URL must enforce TLS (sslmode=require or stronger)")

    return psycopg2.connect(database_url)
```

### Example: sanitize logging output
```python
# Instead of printing full exception text:
# print(f"[INGEST] status=failed reason={exc}")

print("[INGEST] status=failed reason=login_failed")
```

## Remediation Status
- DB TLS policy enforced in runtime (`sslmode=require` or stronger required).
- Secrets policy enforcement added (`COMUNIO_REQUIRE_SECRET_MODE` with prod default).
- Snapshot file hardening added (allowlist directory + max size + schema check).
- Automated policy tests added in backend/tests/test_security_policies.py.

## Risk Summary
- Critical: 0
- High: 1
- Medium: 2
- Low: 0

## Decision
- Production Ready: Conditional Yes
- Blocking Issues:
  - None on code level; production rollout still requires environment-level TLS/CA and Secrets Manager configuration.

## Residual Risks / Testing Gaps
- No dedicated automated security tests were found for transport security policy, log sanitization, or file-path hardening.
- Dependency-level security posture (boto3/comuniopy/psycopg2 CVEs) was not assessed in this review.
