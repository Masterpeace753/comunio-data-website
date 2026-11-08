"use client";

import { useEffect, useRef, useState } from "react";
import { Activity, X } from "lucide-react";
import { getIngestRuns } from "@/lib/api/ingest";
import type { IngestRun, IngestRunsResponse } from "@/lib/api/types";
import { dateLabel } from "@/lib/format";

const PAGE_SIZE = 25;

type ViewState =
  | { kind: "loading" }
  | { kind: "error" }
  | { kind: "loaded"; data: IngestRunsResponse };

const statusLabels: Record<IngestRun["status"], string> = {
  started: "Läuft",
  success: "Erfolgreich",
  failed: "Fehlgeschlagen",
  unknown: "Unbekannt",
};

const runTypeLabels: Record<IngestRun["run_type"], string> = {
  manual: "Manueller Lauf",
  scheduled: "Geplanter Lauf",
  unknown: "Unbekannter Lauf",
};

const errorLabels: Record<NonNullable<IngestRun["error_code"]>, string> = {
  authentication_failed: "Anmeldung fehlgeschlagen",
  snapshot_fetch_failed: "Daten konnten nicht abgerufen werden",
  database_persistence_failed: "Daten konnten nicht gespeichert werden",
  unexpected_error: "Unerwarteter Fehler",
};

const stageLabels: Record<NonNullable<IngestRun["stage"]>, string> = {
  login: "Anmeldung",
  snapshot: "Datenabruf",
  persistence: "Speicherung",
};

function timestampLabel(value: string | null) {
  if (!value) return "Noch nicht beendet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${new Intl.DateTimeFormat("de-DE", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(date)} UTC`;
}

function AttemptRow({ run }: { run: IngestRun }) {
  return (
    <li className="border-t border-line py-4 first:border-0">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-semibold">{runTypeLabels[run.run_type]}</p>
          <p className="mt-1 text-xs text-secondary">
            {statusLabels[run.status] ?? run.status}
            {run.stage ? ` · ${stageLabels[run.stage]}` : ""}
          </p>
        </div>
        <p className="text-right text-xs text-secondary">
          Gestartet: {timestampLabel(run.started_at)}
          <br />
          {run.finished_at ? `Beendet: ${timestampLabel(run.finished_at)}` : "Noch nicht beendet"}
        </p>
      </div>
      <p className="mt-2 text-xs text-secondary">Datensätze geschrieben: {run.records_written}</p>
      {run.error_code && (
        <p className="mt-2 text-sm text-danger" role="note">
          {errorLabels[run.error_code]}
        </p>
      )}
    </li>
  );
}

export function DataModeDialog() {
  const [isOpen, setIsOpen] = useState(false);
  const [offset, setOffset] = useState(0);
  const [retry, setRetry] = useState(0);
  const [view, setView] = useState<ViewState>({ kind: "loading" });
  const triggerRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    let active = true;
    getIngestRuns({ limit: PAGE_SIZE, offset })
      .then((data) => {
        if (active) setView({ kind: "loaded", data });
      })
      .catch(() => {
        if (active) setView({ kind: "error" });
      });

    return () => {
      active = false;
    };
  }, [isOpen, offset, retry]);

  useEffect(() => {
    if (!isOpen) return;
    closeRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setIsOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  const close = () => {
    setIsOpen(false);
    triggerRef.current?.focus();
  };

  const handleDialogKeyDown = (event: React.KeyboardEvent<HTMLElement>) => {
    if (event.key !== "Tab" || !dialogRef.current) return;
    const focusable = Array.from(
      dialogRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
      ),
    );
    if (!focusable.length) {
      event.preventDefault();
      dialogRef.current.focus();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className="w-full rounded-xl border border-line bg-canvas p-4 text-left transition hover:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        aria-controls="data-mode-dialog"
        onClick={() => {
          setOffset(0);
          setView({ kind: "loading" });
          setIsOpen(true);
        }}
      >
        <span className="eyebrow block">Datenmodus</span>
        <span className="mt-2 flex items-center gap-2 text-sm text-secondary">
          <span className="h-2 w-2 rounded-full bg-success" aria-hidden="true" />
          Read-only API
          <span className="ml-auto text-accent">Ladeverlauf anzeigen</span>
        </span>
      </button>

      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) close();
          }}
        >
          <section
            ref={dialogRef}
            id="data-mode-dialog"
            className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-line bg-surface p-5 shadow-2xl md:p-7"
            role="dialog"
            aria-modal="true"
            aria-labelledby="data-mode-title"
            tabIndex={-1}
            onKeyDown={handleDialogKeyDown}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="eyebrow">Datenmodus</p>
                <h2 id="data-mode-title" className="mt-2 text-2xl font-bold">
                  Datenladeverlauf
                </h2>
              </div>
              <button
                ref={closeRef}
                type="button"
                className="button"
                aria-label="Datenladeverlauf schließen"
                onClick={close}
              >
                <X size={18} aria-hidden="true" />
              </button>
            </div>

            {view.kind === "loading" && (
              <div className="mt-6" role="status" aria-live="polite">
                <p className="font-semibold">Aktuelle Datenbasis (UTC)</p>
                <p className="mt-2 text-secondary">Lade Status und Ladeversuche …</p>
              </div>
            )}

            {view.kind === "error" && (
              <div className="mt-6 rounded-xl border border-danger/40 p-4" role="alert">
                <p className="font-semibold">Ladeverlauf nicht verfügbar</p>
                <p className="mt-1 text-sm text-secondary">Die Daten konnten nicht geladen werden.</p>
                <button
                  className="button mt-4"
                  type="button"
                  onClick={() => {
                    setView({ kind: "loading" });
                    setRetry((value) => value + 1);
                  }}
                >
                  Erneut versuchen
                </button>
              </div>
            )}

            {view.kind === "loaded" && (
              <>
                <div className="mt-6 rounded-xl border border-line bg-canvas p-4">
                  <p className="eyebrow">Aktuelle Datenbasis (UTC)</p>
                  <p className="mt-2 text-2xl font-bold" data-testid="current-data-date">
                    {view.data.current_data_date
                      ? dateLabel(view.data.current_data_date)
                      : "Nicht verfügbar"}
                  </p>
                  <p className="mt-1 text-xs text-secondary">
                    {view.data.current_data_date
                      ? `Datenstand ${view.data.current_data_date} UTC`
                      : "Für die aktuelle Datenbasis liegt kein Datum vor."}
                  </p>
                </div>

                <div className="mt-6 flex items-center gap-2">
                  <Activity size={18} className="text-accent" aria-hidden="true" />
                  <h3 className="text-lg font-semibold">Ladeversuche</h3>
                  <span className="ml-auto text-sm text-secondary">{view.data.total} insgesamt</span>
                </div>
                <p className="mt-2 text-xs text-secondary">
                  Angezeigt werden registrierte Läufe. Abbrüche vor der Registrierung,
                  etwa durch einen Datenbankausfall oder eine belegte Start-Sperre,
                  sind hier nicht enthalten.
                </p>

                {view.data.items.length === 0 ? (
                  <p className="mt-4 rounded-xl border border-line p-5 text-sm text-secondary">
                    Es liegen noch keine Datenladeversuche vor.
                  </p>
                ) : (
                  <ul className="mt-3" aria-label="Datenladeversuche">
                    {view.data.items.map((run) => <AttemptRow key={run.id} run={run} />)}
                  </ul>
                )}

                {view.data.total > 0 && (
                  <div className="mt-4 flex items-center justify-between border-t border-line pt-4">
                    <p className="text-sm text-secondary">
                      {view.data.offset + 1}–{Math.min(view.data.offset + view.data.items.length, view.data.total)} von {view.data.total}
                    </p>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        className="button"
                        disabled={view.data.offset <= 0}
                        onClick={() => {
                          setView({ kind: "loading" });
                          setOffset(Math.max(0, view.data.offset - PAGE_SIZE));
                        }}
                      >
                        Zurück
                      </button>
                      <button
                        type="button"
                        className="button"
                        disabled={view.data.offset + view.data.items.length >= view.data.total}
                        onClick={() => {
                          setView({ kind: "loading" });
                          setOffset(view.data.offset + PAGE_SIZE);
                        }}
                      >
                        Weiter
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </section>
        </div>
      )}
    </>
  );
}
