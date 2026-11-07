# Comunio Data Frontend

Next.js App Router frontend for the read-only Comunio API.

## Local development

```powershell
npm install
Copy-Item .env.example .env.local
npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL` to the FastAPI base URL. The browser only calls the Next.js `/api/proxy` route; `API_PROXY_SECRET` is server-side only and must be configured as a Vercel Environment Variable when the API requires proxy authentication.

The current stack uses Next.js 16.4.5, React 19, Tailwind CSS, Recharts 3, Vitest 5 and ESLint 9. ESLint 9.39.5 is no longer supported; the operator accepted a temporary, version-specific CI exception because the Next.js lint plugins do not yet support ESLint 10. Replace the exception once a compatible lint stack is available. The API proxy runs as a Vercel Function. Vercel Hobby currently includes 1 million function invocations per month, 4 active CPU hours and 360 GB-hours of provisioned memory, but is intended for personal, non-commercial use. The API proxy applies an 8-second upstream timeout and forwards only `GET` requests. The FastAPI must enforce `API_PROXY_SECRET`; forwarding a secret alone is not an access-control boundary.

## Checks

```powershell
npm run test
npm run lint
npm run build
npm audit --audit-level=moderate
```

CI also checks every locked npm version against current npm deprecation metadata,
including development and transitive dependencies. It checks Node.js, Next.js
and React lifecycle status and rejects the deprecated Next.js 16/React 18
combination. Registry or lifecycle lookup failures fail the check. The explicit
ESLint exception above is reported on every run; it does not cover other
versions or packages. CI's npm audit includes development dependencies.
The scoped `minimatch` override addresses a development dependency advisory;
remove it after the upstream TypeScript ESLint dependency accepts a fixed
version and the complete audit remains clean.

Create a Vercel project with `frontend` as the root directory. Configure `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_SHOW_OWNER_NAME` for Development, Preview, and Production independently. Configure `API_PROXY_SECRET` only on the server environments.
