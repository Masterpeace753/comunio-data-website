import { describe, expect, it } from "vitest";
import { loginUrlFor, safeRedirectPath } from "./redirects";

describe("safeRedirectPath", () => {
  it("preserves a local path, query, and fragment", () => {
    expect(safeRedirectPath("/spieler/12?tab=history#chart")).toBe("/spieler/12?tab=history#chart");
  });

  it.each([
    "https://example.com",
    "//example.com",
    "/\\example.com",
    "/login\r\nLocation: https://example.com",
    null,
    12,
  ])("rejects unsafe or invalid destinations: %s", (value) => {
    expect(safeRedirectPath(value)).toBe("/");
  });

  it("uses a supplied safe fallback when the destination is invalid", () => {
    expect(safeRedirectPath("https://example.com", "/teams?page=2")).toBe("/teams?page=2");
  });

  it("rejects an unsafe fallback too", () => {
    expect(safeRedirectPath(null, "//example.com")).toBe("/");
  });

  it("creates a login URL with an encoded and safe return destination", () => {
    expect(loginUrlFor("//example.com")).toBe("/login?next=%2F");
    expect(loginUrlFor("/spieler/7?tab=history")).toBe(
      "/login?next=%2Fspieler%2F7%3Ftab%3Dhistory",
    );
  });
});
