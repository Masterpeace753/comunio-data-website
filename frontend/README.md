# Comunio Data Frontend

Next.js App Router frontend for the read-only Comunio API.

## Local development

```powershell
npm install
Copy-Item .env.example .env.local
npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL` to the FastAPI base URL. The browser only calls the Next.js `/api/proxy` route; `API_PROXY_SECRET` is server-side only and must be configured as a Vercel Environment Variable when the API requires proxy authentication.

The current stack uses Next.js 16.3.5, React 18, Tailwind CSS, Recharts 3, Vitest 5 and ESLint 9. ESLint 9 is retained because `eslint-config-next@16.3.5` does not yet support ESLint 10; revisit this pin when the Next.js ESLint integration adds support. The API proxy runs as a Vercel Function. Vercel Hobby currently includes 1 million function invocations per month, 4 active CPU hours and 360 GB-hours of provisioned memory, but is intended for personal, non-commercial use. The API proxy applies an 8-second upstream timeout and forwards only `GET` requests. Before production, the FastAPI must enforce `API_PROXY_SECRET` as specified by AP-13.a; forwarding a secret alone is not an access-control boundary.

## Checks

```powershell
npm run test
npm run lint
npm run build
npm audit --audit-level=moderate
```

The CI gate runs all four commands after `npm ci`. A deployment is blocked when the audit reports a moderate or higher vulnerability.

Create a Vercel project with `frontend` as the root directory. Configure `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_SHOW_OWNER_NAME` for Development, Preview, and Production independently. Configure `API_PROXY_SECRET` only on the server environments.
