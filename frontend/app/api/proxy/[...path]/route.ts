import { NextRequest, NextResponse } from "next/server";
export async function GET(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const base = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!base) return NextResponse.json({ code: "api_not_configured", message: "API is not configured." }, { status: 503 });
  const target = `${base.replace(/\/$/, "")}/${path.join("/")}${request.nextUrl.search}`;
  const headers: HeadersInit = { Accept: "application/json" };
  if (process.env.API_PROXY_SECRET) headers.Authorization = `Bearer ${process.env.API_PROXY_SECRET}`;
  try { const response = await fetch(target, { headers, signal: AbortSignal.timeout(8000), next: { revalidate: 30 } }); return new NextResponse(response.body, { status: response.status, headers: { "content-type": response.headers.get("content-type") ?? "application/json", "cache-control": "public, s-maxage=30, stale-while-revalidate=60" } }); }
  catch { return NextResponse.json({ code: "api_timeout", message: "Upstream API unavailable." }, { status: 503 }); }
}