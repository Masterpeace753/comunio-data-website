import { NextRequest, NextResponse } from "next/server";
import { safeRedirectPath } from "./lib/auth/redirects";

export function proxy(request: NextRequest) {
  if (request.nextUrl.pathname === "/login" || request.nextUrl.pathname.startsWith("/api/")) {
    return NextResponse.next();
  }

  if (request.cookies.has("token")) return NextResponse.next();

  const requestedPath = `${request.nextUrl.pathname}${request.nextUrl.search}`;
  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", safeRedirectPath(requestedPath));
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.[^/]+$).*)"],
};
