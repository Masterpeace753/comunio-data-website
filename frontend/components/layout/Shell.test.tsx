import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Shell } from "./Shell";

vi.mock("next/navigation", () => ({ usePathname: () => "/" }));

afterEach(cleanup);

describe("Datenmodus navigation", () => {
  it("links to the page and closes the mobile menu on navigation", () => {
    render(<Shell><p>Dashboard</p></Shell>);
    fireEvent.click(screen.getByRole("button", { name: "Menü öffnen" }));
    const link = screen.getByRole("link", { name: /datenmodus.*ladeverlauf anzeigen/i });
    expect(link).toHaveAttribute("href", "/datenmodus");
    link.addEventListener("click", (event) => event.preventDefault());
    fireEvent.click(link);
    expect(link.closest("aside")).toHaveClass("hidden");
  });
});
