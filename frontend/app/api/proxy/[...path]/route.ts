import { NextRequest, NextResponse } from "next/server";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  const base = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!base) {
    return NextResponse.json(
      { code: "api_not_configured", message: "API is not configured." },
      { status: 503 },
    );
  }

  const target = `${base.replace(/\/+$/, "")}/${path.join("/")}${request.nextUrl.search}`;
  const headers = new Headers({ Accept: "application/json" });
  const proxySecret = process.env.API_PROXY_SECRET;
  if (proxySecret) headers.set("Authorization", "Bearer " + proxySecret);

  // The session is verified by the backend; keep it server-side in this proxy hop.
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("Cookie", cookie);

  try {
    const response = await fetch(target, {
      headers,
      signal: AbortSignal.timeout(8000),
      cache: "no-store",
    });
    return new NextResponse(response.body, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") ?? "application/json",
        "cache-control": "private, no-store, max-age=0",
      },
    });
  } catch {
    return NextResponse.json(
      { code: "api_timeout", message: "Upstream API unavailable." },
      { status: 503 },
    );
  }
}
