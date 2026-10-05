# Code Review: AP-14 integrated security changes

**Review date:** 2026-10-05  
**Ready for Production:** No  
**Critical Issues:** 0

## Targeted review plan

Risk is high because the change adds authentication, JWT sessions, login throttling, a server-side proxy, and public AWS ingress. Reviewed:

1. Authentication/session validation, cookie attributes, and origin checks.
2. Login rate limiting and reverse-proxy identity handling.
3. Frontend cookie forwarding, API proxy paths, and redirect validation.
4. CloudFront/ALB TLS and ingress boundaries, plus ECS IAM/secret access.
5. Security-relevant deployment documentation and tests.

## Findings (ordered by severity)

### Priority 2 — Medium: Login throttling used the ALB peer address (resolved in the working tree)

- **Category:** Zero Trust / Authentication availability
- **Confidence:** 8/10
- **Evidence at initial review:** `login()` used `request.client.host` as the rate-limit key. The API container is started by `backend/Dockerfile.api:17` with Uvicorn behind an ALB.
- **Impact:** Multiple browser requests could share the ALB peer bucket, allowing failed attempts to temporarily block legitimate logins.
- **Resolution in this working tree:** CloudFront forwards its generated `CloudFront-Viewer-Address` header; `backend/src/api/auth.py` parses that address for the login limiter and uses the direct peer only for local/non-CloudFront requests. The ALB security group allows origin traffic only from CloudFront's origin-facing prefix list. `backend/tests/test_auth.py` verifies that separate CloudFront viewer addresses get separate buckets and that different source ports for one address share a bucket.
- **Verification limitation:** The new behavior has unit/API test coverage but has not been exercised through a deployed CloudFront → ALB → ECS path. The limiter remains process-local, so its quota is not shared across API tasks or restarts; maintain the single-task deployment or add a shared/edge limiter before scaling horizontally.

## Deployment prerequisites (not code vulnerabilities)

- Do not enable the API until `api_origin_domain_name` resolves to the intended ALB and the issued regional ACM certificate covers that name. Terraform's inputs cannot independently prove those DNS/certificate facts.
- Set the production `api_allowed_origins` to the exact frontend origin; the Terraform default allows localhost origins and will not support the deployed frontend if left unchanged.
- Apply and verify the CloudFront/ALB security-group changes before using the API. The ALB prefix-list rule admits CloudFront origin-facing addresses generally, not only this distribution; protected data routes still depend on the JWT and proxy bearer checks.

## Remaining production gates (not unresolved code findings)

- The CloudFront/ALB path and AWS IAM/secret wiring were reviewed as configuration, not verified by a live AWS deployment or an end-to-end TLS request.
- Production must set `api_allowed_origins` to the exact Vercel origin; the checked-in default is localhost-only.
- The review did not identify a redirect escape, JWT validation bypass, proxy-secret bypass on `/api/v1`, or public direct ALB ingress rule in the reviewed implementation.

## Risk summary

- Critical: 0
- High: 0
- Medium: 1 finding, resolved in the current working tree; production path validation remains outstanding
- Low: 0

## Decision

- **Production Ready:** No
- **Production readiness:** Not verified. Apply only after reviewing the plan and supplying the required DNS, ACM, secret ARN, and production-origin inputs; then test the actual TLS/proxy path. The in-memory limiter remains unsuitable for horizontal scaling.
