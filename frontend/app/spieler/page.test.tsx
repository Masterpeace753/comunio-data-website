import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PlayersPage from "./page";
import type { Page, PlayerSummary } from "@/lib/api/types";

const mocks = vi.hoisted(() => ({
  getPlayers: vi.fn(),
  push: vi.fn(),
  params: new URLSearchParams(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mocks.push }),
  useSearchParams: () => mocks.params,
}));
vi.mock("@/lib/api/players", () => ({ getPlayers: mocks.getPlayers }));
vi.mock("@/components/tables/DataTables", () => ({
  PlayerTable: ({ items }: { items: PlayerSummary[] }) => <div>{items.map((item) => <p key={item.id}>{item.name}</p>)}</div>,
}));

function page(offset: number, total: number, name?: string): Page<PlayerSummary> {
  return {
    offset, total, limit: 25,
    items: name ? [{ id: offset + 1, comunio_player_id: offset + 1, name, position: "ST", club_name: null, team_id: null, team_name: null, current_value_eur: null, total_points: null }] : [],
  };
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.params = new URLSearchParams();
});
afterEach(cleanup);

describe("player navigation", () => {
  it("loads both directions and keeps the search in pagination and browser history", async () => {
    mocks.getPlayers.mockImplementation(({ offset }: { offset: number }) =>
      Promise.resolve(page(offset, 51, `Spieler ${offset + 1}`)));
    const view = render(<PlayersPage />);
    expect(await screen.findByText("Spieler 1")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Zurück" })).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("link", { name: "Weiter" })).toHaveAttribute("href", "/spieler?offset=25");

    mocks.params = new URLSearchParams("offset=25");
    view.rerender(<PlayersPage />);
    expect(await screen.findByText("Spieler 26")).toBeInTheDocument();
    expect(mocks.getPlayers).toHaveBeenLastCalledWith({ limit: 25, offset: 25, search: undefined });
    expect(screen.getByRole("link", { name: "Zurück" })).toHaveAttribute("href", "/spieler?offset=0");

    fireEvent.change(screen.getByPlaceholderText("Spieler suchen..."), { target: { value: " Müller & Co " } });
    fireEvent.click(screen.getByRole("button", { name: "Suchen" }));
    expect(mocks.push).toHaveBeenCalledWith("/spieler?search=M%C3%BCller+%26+Co");
    mocks.params = new URLSearchParams("search=M%C3%BCller+%26+Co");
    view.rerender(<PlayersPage />);
    await waitFor(() => expect(mocks.getPlayers).toHaveBeenLastCalledWith({ limit: 25, offset: 0, search: "Müller & Co" }));
    expect(await screen.findByRole("link", { name: "Weiter" })).toHaveAttribute("href", "/spieler?search=M%C3%BCller+%26+Co&offset=25");

    mocks.params = new URLSearchParams("search=M%C3%BCller+%26+Co&offset=25");
    view.rerender(<PlayersPage />);
    expect(await screen.findByText("Spieler 26")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Zurück" })).toHaveAttribute("href", "/spieler?search=M%C3%BCller+%26+Co&offset=0");
    mocks.params = new URLSearchParams("search=M%C3%BCller+%26+Co&offset=50");
    view.rerender(<PlayersPage />);
    expect(await screen.findByText("Spieler 51")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Weiter" })).toHaveAttribute("aria-disabled", "true");

    mocks.params = new URLSearchParams("offset=25");
    view.rerender(<PlayersPage />);
    expect(await screen.findByText("Spieler 26")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Spieler suchen...")).toHaveValue("");
    expect(screen.getByRole("link", { name: "Filter zurücksetzen" })).toHaveAttribute("href", "/spieler");
  });

  it("ignores an outdated response and permits returning from an empty page", async () => {
    let resolveFirst!: (value: Page<PlayerSummary>) => void;
    mocks.getPlayers.mockImplementation(({ offset }: { offset: number }) =>
      offset === 0 ? new Promise<Page<PlayerSummary>>((resolve) => { resolveFirst = resolve; }) : Promise.resolve(page(offset, 12)));
    const view = render(<PlayersPage />);
    mocks.params = new URLSearchParams("offset=25");
    view.rerender(<PlayersPage />);
    expect(await screen.findByText("Keine Spieler gefunden")).toBeInTheDocument();
    expect(screen.getByText("Zeige 0-0 von 12")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Zurück" })).toHaveAttribute("href", "/spieler?offset=0");
    await act(async () => resolveFirst(page(0, 12, "Alte Antwort")));
    expect(screen.queryByText("Alte Antwort")).not.toBeInTheDocument();
  });

  it("rejects invalid offsets and searches the full dataset", async () => {
    mocks.params = new URLSearchParams("search=Sp%C3%A4ter&offset=-25");
    mocks.getPlayers.mockResolvedValue(page(0, 1, "Später Spieler"));
    render(<PlayersPage />);
    expect(await screen.findByText("Später Spieler")).toBeInTheDocument();
    expect(mocks.getPlayers).toHaveBeenCalledWith({ limit: 25, offset: 0, search: "Später" });
  });
});
