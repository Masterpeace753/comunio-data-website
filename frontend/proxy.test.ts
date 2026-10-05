import { describe, expect, it } from "vitest";
import { NextRequest } from "next/server";
import { proxy } from "./proxy";

describe("session middleware", () => {
  it("redirects an unauthenticated page request and retains its local destination", () => {
    const response = proxy(new NextRequest("https://app.example.test/spieler/7?tab=history"));
    const redirect = new URL(response.headers.get("location")!);

    expect(response.status).toBe(307);
    expect(redirect.pathname).toBe("/login");
    expect(redirect.searchParams.get("next")).toBe("/spieler/7?tab=history");
  });

  it("allows a request with a token cookie through without attempting JWT verification", () => {
    const request = new NextRequest("https://app.example.test/teams", {
      headers: { cookie: "token=opaque-session" },
    });

    expect(proxy(request).status).toBe(200);
  });

  it("does not redirect login or API paths", () => {
    expect(proxy(new NextRequest("https://app.example.test/login")).status).toBe(200);
    expect(proxy(new NextRequest("https://app.example.test/api/auth/login")).status).toBe(200);
  });
});
