import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Dashboard from "./page";

const mocks = vi.hoisted(() => ({
  getPlayers: vi.fn(),
  getTeams: vi.fn(),
  getTransfermarket: vi.fn(),
}));

vi.mock("@/lib/api/players", () => ({ getPlayers: mocks.getPlayers }));
vi.mock("@/lib/api/teams", () => ({ getTeams: mocks.getTeams }));
vi.mock("@/lib/api/transfermarket", () => ({ getTransfermarket: mocks.getTransfermarket }));

beforeEach(() => {
  vi.resetAllMocks();
  mocks.getPlayers.mockResolvedValue({
    items: [{
      id: 1,
      comunio_player_id: 1001,
      name: "Neuer Spieler",
      position: "MITT",
      club_name: null,
      team_id: null,
      team_name: null,
      current_value_eur: null,
      total_points: null,
    }],
    limit: 5,
    offset: 0,
    total: 1,
  });
  mocks.getTeams.mockResolvedValue({ items: [], limit: 5, offset: 0, total: 0 });
  mocks.getTransfermarket.mockResolvedValue({ items: [], limit: 5, offset: 0, total: 0 });
});

afterEach(cleanup);

describe("dashboard", () => {
  it("requests and displays players ordered by first database insert", async () => {
    render(<Dashboard />);

    expect(await screen.findByText("Neuer Spieler")).toBeInTheDocument();
    await waitFor(() => expect(mocks.getPlayers).toHaveBeenCalledWith({ limit: 5, sort: "newest" }));
    expect(screen.getByText("Erstmalig in der Datenbank erfasst")).toBeInTheDocument();
  });
});
