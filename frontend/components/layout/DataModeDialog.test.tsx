import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DataModeDialog } from "./DataModeDialog";
import { getIngestRuns } from "@/lib/api/ingest";
import type { IngestRunsResponse } from "@/lib/api/types";

vi.mock("@/lib/api/ingest", () => ({ getIngestRuns: vi.fn() }));
const getRunsMock = vi.mocked(getIngestRuns);

const makeResponse = (overrides: Partial<IngestRunsResponse> = {}): IngestRunsResponse => ({
  current_data_date: "2026-11-07",
  items: [{
    id: 1,
    run_type: "scheduled",
    status: "success" as const,
    started_at: "2026-11-08T01:15:00Z",
    finished_at: "2026-11-08T01:16:00Z",
    records_written: 42,
    stage: "snapshot",
    error_code: null,
  }],
  limit: 25,
  offset: 0,
  total: 1,
  ...overrides,
});

beforeEach(() => {
  vi.resetAllMocks();
});
afterEach(cleanup);

describe("Datenmodus dialog", () => {
  it("opens accessibly, focuses the dialog, closes with Escape, and restores trigger focus", async () => {
    getRunsMock.mockResolvedValue(makeResponse());
    render(<DataModeDialog />);
    const trigger = screen.getByRole("button", { name: /datenmodus.*ladeverlauf anzeigen/i });
    trigger.focus();
    fireEvent.click(trigger);

    const dialog = await screen.findByRole("dialog", { name: "Datenladeverlauf" });
    await waitFor(() => expect(screen.getByRole("button", { name: "Datenladeverlauf schließen" })).toHaveFocus());
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(trigger).toHaveAttribute("aria-expanded", "true");

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });

  it("renders the UTC data date and attempt details, and requests the exact initial page", async () => {
    getRunsMock.mockResolvedValue(makeResponse());
    render(<DataModeDialog />);
    fireEvent.click(screen.getByRole("button", { name: /datenmodus/i }));

    expect(await screen.findByText(/Erfolgreich/)).toBeInTheDocument();
    expect(screen.getByTestId("current-data-date")).toHaveTextContent("07.11.2026");
    expect(screen.getByText("Datenstand 2026-11-07 UTC")).toBeInTheDocument();
    expect(screen.getByText("Geplanter Lauf")).toBeInTheDocument();
    expect(screen.getByText(/Gestartet:.*UTC/)).toBeInTheDocument();
    expect(screen.getByText("Datensätze geschrieben: 42")).toBeInTheDocument();
    expect(screen.getByText(/Angezeigt werden registrierte Läufe/)).toBeInTheDocument();
    expect(getRunsMock).toHaveBeenCalledWith({ limit: 25, offset: 0 });
  });

  it("paginates using the response offset and page size", async () => {
    getRunsMock
      .mockResolvedValueOnce(makeResponse({
        items: Array.from({ length: 25 }, (_, index) => ({
          id: index + 1,
          run_type: "scheduled",
          status: "started" as const,
          started_at: "2026-11-08T01:15:00Z",
          finished_at: null,
          records_written: 0,
          stage: "snapshot",
          error_code: null,
        })),
        total: 26,
      }))
      .mockResolvedValueOnce(makeResponse({
        items: [{
          id: 26,
          run_type: "manual",
          status: "failed",
          started_at: "2026-11-08T02:15:00Z",
          finished_at: null,
          records_written: 3,
          stage: "snapshot",
          error_code: "snapshot_fetch_failed",
        }],
        offset: 25,
        total: 26,
      }));
    render(<DataModeDialog />);
    fireEvent.click(screen.getByRole("button", { name: /datenmodus/i }));
    await waitFor(() => expect(screen.getAllByText(/Läuft/)).toHaveLength(25));
    expect(screen.getAllByText(/Noch nicht beendet/)).toHaveLength(25);

    fireEvent.click(screen.getByRole("button", { name: "Weiter" }));
    expect(await screen.findByText(/Fehlgeschlagen/)).toBeInTheDocument();
    expect(screen.getByText("Daten konnten nicht abgerufen werden")).toBeInTheDocument();
    expect(getRunsMock).toHaveBeenNthCalledWith(2, { limit: 25, offset: 25 });
    expect(screen.getByText("26–26 von 26")).toBeInTheDocument();
  });

  it("shows loading, unavailable-date, and empty-history states", async () => {
    let resolveRuns!: (value: Awaited<ReturnType<typeof getIngestRuns>>) => void;
    getRunsMock.mockReturnValue(new Promise((resolve) => { resolveRuns = resolve; }));
    render(<DataModeDialog />);
    fireEvent.click(screen.getByRole("button", { name: /datenmodus/i }));
    expect(screen.getByRole("status")).toHaveTextContent("Lade Status und Ladeversuche");

    resolveRuns(makeResponse({ current_data_date: null, items: [], total: 0 }));
    expect(await screen.findByText("Nicht verfügbar")).toBeInTheDocument();
    expect(screen.getByText("Es liegen noch keine Datenladeversuche vor.")).toBeInTheDocument();
    expect(screen.getByText("Für die aktuelle Datenbasis liegt kein Datum vor.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Weiter" })).not.toBeInTheDocument();
  });

  it("shows a recoverable error and retries the current page", async () => {
    getRunsMock.mockRejectedValueOnce(new Error("network detail")).mockResolvedValueOnce(makeResponse());
    render(<DataModeDialog />);
    fireEvent.click(screen.getByRole("button", { name: /datenmodus/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Ladeverlauf nicht verfügbar");
    expect(screen.queryByText("network detail")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Erneut versuchen" }));
    expect(await screen.findByText(/Erfolgreich/)).toBeInTheDocument();
    expect(getRunsMock).toHaveBeenNthCalledWith(2, { limit: 25, offset: 0 });
  });

  it("closes with the close button", async () => {
    getRunsMock.mockResolvedValue(makeResponse());
    render(<DataModeDialog />);
    fireEvent.click(screen.getByRole("button", { name: /datenmodus/i }));
    await screen.findByRole("dialog");
    fireEvent.click(screen.getByRole("button", { name: "Datenladeverlauf schließen" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
