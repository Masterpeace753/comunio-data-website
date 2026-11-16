import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { PlayerTable } from "./DataTables";

afterEach(cleanup);

describe("PlayerTable", () => {
  it("shows club and Comunio team separately and links the player name", () => {
    render(<PlayerTable items={[
      { id: 7, comunio_player_id: 100, name: "Testspieler", position: "ST",
        club_name: "FC Bayern München", team_id: 2, team_name: "Mein Team", current_value_eur: 1250000 },
      { id: 8, comunio_player_id: 101, name: "Freier Spieler", position: "TW",
        club_name: null, team_id: null, team_name: null, current_value_eur: null },
    ]}/>);

    expect(screen.getAllByRole("columnheader").map((header) => header.textContent))
      .toEqual(["Name", "Position", "Club", "Team", "Marktwert"]);
    expect(screen.getByRole("link", { name: "Testspieler" })).toHaveAttribute("href", "/spieler/7");
    const rows = screen.getAllByRole("row");
    expect(within(rows[1]).getByText("FC Bayern München")).toBeInTheDocument();
    expect(within(rows[1]).getByText("Mein Team")).toBeInTheDocument();
    expect(within(rows[2]).getAllByText("-")).toHaveLength(3);
  });
});
