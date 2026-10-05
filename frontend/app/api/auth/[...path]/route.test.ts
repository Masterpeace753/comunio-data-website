import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET, POST } from "./route";

const fetchMock = vi.fn();

function request(path: string, method = "GET", body?: string) {
  return new NextRequest(`http://localhost/api/auth/${path}`, {
    method,
    headers: {
      ...(method === "POST" ? { "content-type": "application/json", origin: "http://localhost" } : {}),
      cookie: "token=session-value",
    },
    body,
  });
}

describe("auth proxy", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.test/");
    vi.stubEnv("API_PROXY_SECRET", "server-only-secret");
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  it("forwards login data, cookie and the server-only proxy secret", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ authenticated: true }), {
        status: 200,
        headers: {
          "content-type": "application/json",
          "set-cookie": "token=jwt-value; HttpOnly; Secure; SameSite=Strict; Path=/",
        },
      }),
    );

    const response = await POST(
      request("login", "POST", JSON.stringify({ username: "owner", password: "password" })),
      { params: Promise.resolve({ path: ["login"] }) },
    );
    const [url, options] = fetchMock.mock.calls[0];

    expect(url).toBe("https://api.example.test/auth/login");
    expect(options.headers.get("cookie")).toBe("token=session-value");
    expect(options.headers.get("authorization")).toBe("Bearer server-only-secret");
    expect(options.headers.get("origin")).toBe("http://localhost");
    expect(options.body).toBe(JSON.stringify({ username: "owner", password: "password" }));
    expect(options.cache).toBe("no-store");
    expect(response.headers.get("set-cookie")).toBe(
      "token=jwt-value; HttpOnly; Secure; SameSite=Strict; Path=/",
    );
    expect(response.headers.get("authorization")).toBeNull();
    expect(await response.json()).toEqual({ authenticated: true });
  });

  it("forwards the session cookie to the current-user endpoint", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

    await GET(request("me"), { params: Promise.resolve({ path: ["me"] }) });

    expect(fetchMock.mock.calls[0][0]).toBe("https://api.example.test/auth/me");
    expect(fetchMock.mock.calls[0][1].headers.get("cookie")).toBe("token=session-value");
  });

  it("rejects paths outside the explicit auth endpoint allowlist", async () => {
    const response = await GET(request("admin/delete"), {
      params: Promise.resolve({ path: ["admin", "delete"] }),
    });

    expect(response.status).toBe(404);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("returns a safe service error when the upstream is unavailable", async () => {
    fetchMock.mockRejectedValue(new Error("network failure"));

    const response = await GET(request("me"), { params: Promise.resolve({ path: ["me"] }) });

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      code: "auth_upstream_unavailable",
      message: "Authentication service unavailable.",
    });
  });
});
