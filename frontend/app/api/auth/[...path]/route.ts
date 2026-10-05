import { NextRequest, NextResponse } from "next/server";

const AUTH_PATHS = new Set(["login", "logout", "me"]);

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxyAuthRequest(request: NextRequest, { params }: RouteContext) {
  const { path } = await params;
  if (path.length !== 1 || !AUTH_PATHS.has(path[0])) {
    return NextResponse.json({ code: "not_found", message: "Not found." }, { status: 404 });
  }

  const base = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!base) {
    return NextResponse.json(
      { code: "api_not_configured", message: "API is not configured." },
      { status: 503 },
    );
  }

  const headers = new Headers({ Accept: "application/json" });
  const proxySecret = process.env.API_PROXY_SECRET;
  if (proxySecret) headers.set("Authorization", "Bearer " + proxySecret);

  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("Cookie", cookie);
  const origin = request.headers.get("origin");
  if (origin) headers.set("Origin", origin);
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType);

  const target = `${base.replace(/\/+$/, "")}/auth/${path[0]}`;
  try {
    const response = await fetch(target, {
      method: request.method,
      headers,
      body: request.method === "POST" ? await request.text() : undefined,
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.timeout(8000),
    });

    const responseHeaders = new Headers({
      "Cache-Control": "private, no-store, max-age=0",
    });
    const responseType = response.headers.get("content-type");
    if (responseType) responseHeaders.set("Content-Type", responseType);

    // Headers.get() may fold Set-Cookie values; preserve each cookie separately where supported.
    const upstreamHeaders = response.headers as Headers & { getSetCookie?: () => string[] };
    const cookies = upstreamHeaders.getSetCookie?.() ?? [];
    if (cookies.length) {
      for (const setCookie of cookies) responseHeaders.append("Set-Cookie", setCookie);
    } else {
      const setCookie = response.headers.get("set-cookie");
      if (setCookie) responseHeaders.append("Set-Cookie", setCookie);
    }

    return new NextResponse(response.body, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch {
    return NextResponse.json(
      { code: "auth_upstream_unavailable", message: "Authentication service unavailable." },
      { status: 503, headers: { "Cache-Control": "private, no-store, max-age=0" } },
    );
  }
}

export const GET = proxyAuthRequest;
export const POST = proxyAuthRequest;
