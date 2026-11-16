# Repository instructions

## Platform default

- Unless a task explicitly asks for AWS, treat the Ubuntu/Linux VPS deployment as the only target for new backend, data-pipeline, and operations features.
- Use the existing Linux stack: Docker Compose, FastAPI, PostgreSQL, Caddy, and the systemd user timer where scheduled work is needed. Vercel remains the frontend host and its Next.js server routes remain the backend-for-frontend.
- Use `infra/vps/README.md` as the operational source of truth. Develop and validate in a local Linux-compatible environment or CI; do not develop directly on the production VPS.
- Use `architecture.md` for the current system design. Treat `docs/architecture/aws-legacy-notes.md` as an archive, not as instructions for new work.
- Do not add AWS dependencies, AWS runtime paths, Terraform resources, or AWS deployment steps by default. Preserve `infra/aws/` as a historical/optional alternative and modify or deploy it only when the user explicitly requests AWS.
- Use the VPS runbook for current VPS operations. Do not infer live AWS state from legacy documentation; verify it only through an explicitly authorized AWS check.

## Change and validation expectations

- New runtime features must work in the existing Linux container environment and must not require Windows-only behavior.
- Keep secrets in the existing host-mounted files or server-side Vercel environment variables; never commit them or expose them through `NEXT_PUBLIC_*`.
- Run the focused tests and VPS Compose/configuration checks relevant to the change. Production deployment is a separate action and requires an explicit user request.
