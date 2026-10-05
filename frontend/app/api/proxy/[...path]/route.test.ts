import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET } from "./route";

const fetchMock = vi.fn();

describe("data API proxy", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.test");
    vi.stubEnv("API_PROXY_SECRET", "server-only-secret");
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  it("preserves API paths and query strings while forwarding the session and server secret", async () => {
    fetchMock.mockResolvedValue(new Response('{"items":[]}', { status: 200 }));
    const request = new NextRequest("http://localhost/api/proxy/api/v1/players?limit=10", {
      headers: { cookie: "token=session-value" },
    });

    const response = await GET(request, {
      params: Promise.resolve({ path: ["api", "v1", "players"] }),
    });
    const [url, options] = fetchMock.mock.calls[0];

    expect(url).toBe("https://api.example.test/api/v1/players?limit=10");
    expect(options.headers.get("cookie")).toBe("token=session-value");
    expect(options.headers.get("authorization")).toBe("Bearer server-only-secret");
    expect(options.cache).toBe("no-store");
    expect(response.headers.get("cache-control")).toContain("private");
    expect(await response.text()).toBe('{"items":[]}');
  });
});
