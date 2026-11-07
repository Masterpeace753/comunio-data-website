import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import TeamDetailPage from "./teams/[id]/page";
import PlayerDetailPage from "./spieler/[id]/page";

const mocks = vi.hoisted(() => ({
  useParams: vi.fn(),
  getTeam: vi.fn(),
  getPlayers: vi.fn(),
  getPlayer: vi.fn(),
  getPlayerHistory: vi.fn(),
}));

vi.mock("next/navigation", () => ({ useParams: mocks.useParams }));
vi.mock("@/lib/api/teams", () => ({ getTeam: mocks.getTeam }));
vi.mock("@/lib/api/players", () => ({
  getPlayers: mocks.getPlayers,
  getPlayer: mocks.getPlayer,
  getPlayerHistory: mocks.getPlayerHistory,
}));
vi.mock("@/components/tables/DataTables", () => ({ PlayerTable: () => null }));
vi.mock("@/components/charts/MarketChart", () => ({ MarketChart: () => null }));

beforeEach(() => {
  vi.resetAllMocks();
  mocks.useParams.mockReturnValue({ id: "42" });
});
afterEach(cleanup);

describe("dynamic detail routes", () => {
  it("uses the current team ID for the team and player requests", async () => {
    mocks.getTeam.mockResolvedValue({ name: "Testteam", league: null, season: null, player_count: 0 });
    mocks.getPlayers.mockResolvedValue({ items: [] });
    const page = render(<TeamDetailPage />);
    expect(await screen.findByText("Testteam")).toBeInTheDocument();
    expect(mocks.getTeam).toHaveBeenCalledWith("42");
    expect(mocks.getPlayers).toHaveBeenCalledWith({ team_id: "42", limit: 100 });

    mocks.useParams.mockReturnValue({ id: "43" });
    page.rerender(<TeamDetailPage />);
    await waitFor(() => expect(mocks.getTeam).toHaveBeenCalledWith("43"));
    expect(mocks.getPlayers).toHaveBeenCalledWith({ team_id: "43", limit: 100 });
  });

  it("uses the current player ID for the player and history requests", async () => {
    mocks.getPlayer.mockResolvedValue({ name: "Testspieler", position: "MITT", team_name: null, current_value_eur: null, source: "test", last_seen_at: "2026-11-07" });
    mocks.getPlayerHistory.mockResolvedValue({ items: [] });
    const page = render(<PlayerDetailPage />);
    expect(await screen.findByText("Testspieler")).toBeInTheDocument();
    expect(mocks.getPlayer).toHaveBeenCalledWith("42");
    expect(mocks.getPlayerHistory).toHaveBeenCalledWith("42", { limit: 90 });

    mocks.useParams.mockReturnValue({ id: "43" });
    page.rerender(<PlayerDetailPage />);
    await waitFor(() => expect(mocks.getPlayer).toHaveBeenCalledWith("43"));
    expect(mocks.getPlayerHistory).toHaveBeenCalledWith("43", { limit: 90 });
  });
});
