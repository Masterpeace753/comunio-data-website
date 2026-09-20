# Frontend-Konzept fuer das Comunio-Projekt

Dieses Dokument ist die verbindliche Spezifikation und Bauanleitung fuer das Frontend. Es beschreibt Framework-Wahl, Design-System, Informationsarchitektur, Komponenten, Datenanbindung und den empfohlenen Umsetzungsablauf. Der v1-Stand ist unter `frontend/` umgesetzt; dieses Dokument bleibt die fachliche Referenz fuer Erweiterungen.

Bezug zu den bestehenden Projektdokumenten:

- `architecture.md` Abschnitt 3.3: Frontend Service (React auf Vercel), Dashboard/Team-/Spieleransichten, historische Visualisierung, Filter/Suche/Sortierung/Vergleich.
- `data_model.md`: liefert die Datenfelder, die im Frontend dargestellt werden (Spieler, Teams, Marktwert-Historie mit Deltas, Transfermarkt).
- `backend/src/api/app.py` und `backend/src/api/schemas.py`: der aktuelle, verbindliche REST-Vertrag `/api/v1/...`, gegen den das Frontend implementiert wird.

## 1. Ziele und Leitplanken

- Read-only-Dashboard fuer Comunio-Daten: Spieler, Teams, Marktwert-Historie mit Deltas, Transfermarkt.
- Performance-Ziel gemaess `architecture.md`: Seitenladezeit unter 2 Sekunden, API P95 unter 500 ms wird vom Backend eingehalten.
- Deployment-Ziel: Vercel (statische/Edge-Auslieferung, CDN, Preview-Deployments je PR).
- Kein eigener Fachdaten-Backend-Code im Frontend: alle Daten kommen ausschliesslich ueber die bestehende FastAPI unter `/api/v1`.
- Der Browser spricht ausschliesslich den serverseitigen Next.js-Proxy unter `/api/proxy/...` an. `API_PROXY_SECRET` bleibt eine serverseitige Vercel-Umgebungsvariable und wird nie an Client-JavaScript weitergegeben.
- Es gibt in Phase 1 keinen Benutzerlogin. Der Proxy unterstuetzt die technische Proxy-Authentifizierung; die verpflichtende Validierung dieses Secrets in der FastAPI ist AP-13.a und muss vor dem Produktions-Livegang aktiviert werden. Direkte Browser-Aufrufe auf die FastAPI sind kein unterstuetzter Frontend-Pfad.

## 2. Framework-Entscheidung

**Gewaehlt: Next.js 16.3.5 (App Router) mit TypeScript, Tailwind CSS, Recharts und einer serverseitigen Proxy-Route.**

Begruendung:

- `architecture.md` legt bereits **React auf Vercel** fest. Next.js ist das von Vercel selbst entwickelte React-Framework mit nativer Vercel-Integration (Zero-Config-Deployment, Preview-URLs, Edge-Caching) und erfuellt damit die bestehende Architekturentscheidung direkt, ohne sie zu aendern.
- App Router + statische Seiten und Client Components fuer interaktive Teile (Charts, Filter, Suche) unterstuetzen das <2s-Ladeziel. Die Datenzugriffe laufen ueber den serverseitigen Proxy; relative Browser-Requests werden nicht direkt an die FastAPI gerichtet.
- TypeScript sichert die Vertragstreue zum Backend: die Pydantic-Schemas aus `backend/src/api/schemas.py` werden 1:1 als TypeScript-Typen gespiegelt (siehe Abschnitt 6).
- Tailwind CSS passt zum gewuenschten Dark-Mode-Design (utility-first, einfache Theming-Variablen fuer Farben/Spacing, gute Performance durch Purging ungenutzter Klassen).
- Die UI nutzt schlanke, lokal definierte Komponenten im shadcn-inspirierten Stil (Table, Badge, Card, Skeleton, Empty/Error-State), damit das Dark-Navy-Neon-Theme ohne ungenutzte Abhaengigkeiten kontrollierbar bleibt.
- Recharts fuer die Marktwert-Historie (Line-/Area-Charts): React-nativ, gut mit Server/Client-Split kombinierbar, ausreichend fuer Zeitreihen mit Tooltip/Zoom.
- TanStack Query ist als spaeterer Ausbau vorgesehen; v1 verwendet gezielte Client-Fetches, URL-/Form-Zustand und serverseitiges Proxy-Caching.

Alternativen wurden bewusst verworfen:

- Vite + reines React: kein natives SSR/ISR, mehr manuelle Vercel-Konfiguration, kein Vorteil gegenueber Next.js bei diesem Anwendungsfall.
- Nuxt/Vue oder SvelteKit: kein Bezug zu "React auf Vercel" aus `architecture.md`, zusaetzlicher Technologie-Bruch ohne Mehrwert.

## 3. Design-System: "Dark Mode Professional" (Navy + Neon-Akzente)

Merkmale (siehe angehaengtes Referenzbild und verlinktes Dashboard-Beispiel):

- Dunkler, navy-getoenter Hintergrund (kein reines Schwarz) fuer ein technisches, seriöses "Enterprise"-Wirken.
- Karten/Panels in einem etwas helleren Navy-Ton mit dezenten Bordern statt Schatten, um Tiefe zu erzeugen.
- Neon-Akzente in Blau und Violett fuer interaktive Elemente, aktive Zustaende, Chart-Linien, Fokus-Ringe und Badges.
- Klare, hohe Kontraste zwischen Text und Hintergrund (WCAG AA mindestens fuer Fliesstext).
- Datenvisualisierung als zentrales gestalterisches Element (Sparklines, Flow-/Area-Charts, Donut-Charts, Trendindikatoren).

### 3.1 Farbpalette (CSS-Variablen / Tailwind-Theme-Tokens)

Basis-Tokens, die als Tailwind-`theme.extend.colors` bzw. CSS-Variablen (`:root[data-theme="dark"]`) definiert werden:

| Token | Hex | Verwendung |
| --- | --- | --- |
| `--bg-canvas` | `#0B0E1A` | Seitenhintergrund (dunkelstes Navy) |
| `--bg-surface` | `#12162B` | Card-/Panel-Hintergrund |
| `--bg-surface-elevated` | `#171B33` | Hover-/aktive Panels, Dropdowns, Modals |
| `--border-subtle` | `#232848` | Kartenrahmen, Trennlinien |
| `--text-primary` | `#F5F6FA` | Ueberschriften, Primaertext |
| `--text-secondary` | `#9AA1C4` | Sekundaertext, Labels, Meta-Infos |
| `--text-muted` | `#5D6491` | Deaktivierte/inaktive Texte |
| `--accent-blue` | `#4C7DFF` | Primaerakzent: Links, Primary-Buttons, aktive Nav-Items |
| `--accent-blue-glow` | `#6E9BFF` | Hover-/Glow-Variante von Blau |
| `--accent-violet` | `#8B5CF6` | Sekundaerakzent: sekundaere CTAs, Highlights, Chart-Linie 2 |
| `--accent-violet-glow` | `#A78BFA` | Hover-/Glow-Variante von Violett |
| `--success` | `#34D399` | Positive Marktwert-Deltas |
| `--danger` | `#F87171` | Negative Marktwert-Deltas |
| `--warning` | `#FBBF24` | Warnungen (z. B. fehlende Referenzdaten) |
| `--focus-ring` | `#8B5CF6` | `outline`/`ring` bei Tastaturfokus |

Verwendungsregeln:

- Neon-Farben (`accent-blue`, `accent-violet`) werden **sparsam** fuer Fokuspunkte eingesetzt: aktive Navigation, Primary-Buttons, Chart-Serien, Badges, Fokus-Ringe. Sie werden nicht flaechig als Hintergrund verwendet.
- Positive/negative Marktwert-Deltas verwenden ausschliesslich `success`/`danger`, niemals die Akzentfarben, um Verwechslung mit UI-Interaktion zu vermeiden.
- Glow-Effekte (leichter `box-shadow`/`filter: drop-shadow` in Akzentfarbe) sind auf Hover-Zustaende und aktive Chart-Punkte begrenzt, nicht dauerhaft animiert (Performance, Zugaenglichkeit).

### 3.2 Typografie

- Schriftart: `Inter` (oder `Geist Sans`, da nativ mit Next.js/Vercel ausgeliefert) als Systemfont-Fallback-Stack.
- Monospace fuer Zahlen/EUR-Betraege optional: `Geist Mono` oder `JetBrains Mono` fuer tabellarische Zahlenausrichtung in Tabellen/Charts.
- Groessen-Skala (Tailwind-Default-Skala nutzen, keine Neuerfindung): `text-xs` (Meta/Labels), `text-sm` (Tabelleninhalt), `text-base` (Fliesstext), `text-lg`/`text-xl` (Card-Titel), `text-2xl`/`text-3xl` (Seitentitel/KPI-Zahlen).
- Zahlen/KPIs (z. B. Marktwert-Summen) werden `font-semibold` bis `font-bold` gesetzt, um im dunklen UI visuell zu dominieren.

### 3.3 Spacing, Radius, Elevation

- Grid-/Spacing-Basis: 4px-Raster ueber Tailwind-Defaults (`p-2`, `p-4`, `p-6`, `gap-4`, `gap-6`).
- Card-Radius: `rounded-2xl` (grosszuegig, wirkt modern/"enterprise" wie im Referenzbild).
- Elevation ausschliesslich ueber Farbabstufung (`bg-surface` vs. `bg-canvas`) und `border-subtle`, keine harten Drop-Shadows in Schwarz (wirkt im Dark Mode "schmutzig"); optional sehr dezente farbige Schatten (`shadow-[0_0_40px_-10px_rgba(76,125,255,0.25)]`) fuer Hero-/KPI-Karten.
- Icon-Set: `lucide-react` (passt zu shadcn/ui, konsistente Strichstaerke).

### 3.4 Kernkomponenten (shadcn/ui-Basis, im Theme angepasst)

- `Card` fuer KPI-Kacheln, Chart-Container, Ranking-Listen.
- `Table` (mit `Tanstack Table` optional fuer Sortierung/Pagination) fuer Spieler-/Team-/Transfermarktlisten.
- `Tabs` fuer Detailseiten (z. B. Spieler: "Historie" / "Uebersicht").
- `Badge` fuer Position (`TW`/`ABW`/`MITT`/`ST`), Liga, "auf Transfermarkt"-Status.
- `Command`/`Popover`-basierte Suche fuer globale Spieler-/Team-Suche (Cmd/Ctrl+K), passend zum "Enterprise"-Anspruch.
- `Skeleton` fuer Ladezustaende (dunkles Shimmer statt weisser Standard-Skeleton).
- `Tooltip` fuer Chart-Datenpunkte und abgeschnittene Tabellenwerte.
- `Sheet`/`Dialog` fuer mobile Filter-Panels bzw. Detail-Overlays.
- Custom: `TrendBadge` (Pfeil hoch/runter + Prozentwert in `success`/`danger`), `Sparkline` (kompakte Recharts-Line ohne Achsen fuer Tabellenzeilen), `EmptyState`, `ErrorState` (fuer 404/503 gemaess API-Vertrag).

## 4. Informationsarchitektur / Seiten

```text
/                          Dashboard (Uebersicht)
/spieler                   Spielerliste (Suche, Filter, Sortierung)
/spieler/[id]              Spielerdetail (Stammdaten + Marktwert-Historie)
/teams                     Teamliste (Suche, Filter nach Liga/Saison)
/teams/[id]                Teamdetail (Stammdaten + Kaderliste)
/transfermarkt             Transfermarkt-Uebersicht (aktueller Snapshot-Tag)
```

Globale Navigation (Sidebar, wie im Referenzbild links): Dashboard, Spieler, Teams, Transfermarkt. Kopfzeile (Header) mit globaler Suche, Zeitraum-/Snapshot-Auswahl (sofern relevant) und einer **Platzhalter-Anzeige "Zuletzt aktualisiert am"**: rechts im Header reserviert (kleines `text-secondary`-Label mit Uhr-Icon aus `lucide-react`), zeigt in v1 statisch "--" statt eines Datums und keinen API-Call. Sobald der Status-Endpunkt aus Abschnitt 8 existiert, wird nur die Datenquelle angebunden, ohne das Header-Layout zu aendern.

### 4.1 Dashboard (`/`)

Ziel: schneller Ueberblick, angelehnt an das Referenzdesign (KPI-Kacheln oben, zwei grosse Chart-Karten darunter).

- KPI-Kacheln (oben, 4er-Reihe wie im Referenzbild):
  - Anzahl Spieler gesamt (`GET /api/v1/players` `total`).
  - Anzahl Teams gesamt (`GET /api/v1/teams` `total`).
  - Anzahl Spieler aktuell auf dem Transfermarkt (`GET /api/v1/transfermarket?listed=true` `total`).
  - **Platzhalter-Kachel "Gesamtmarktwert"**: die vierte KPI-Kachel ist von Anfang an im Layout reserviert (gleiche `Card`-Komponente, gleiche Groesse wie die anderen drei), zeigt aber bis zur Umsetzung des Aggregat-Endpunkts (siehe Abschnitt 8) einen deaktivierten Zustand statt einer echten Zahl: Titel "Gesamtmarktwert", Wert `--` in `text-muted`, kein `TrendBadge`, kleiner Hinweistext "Bald verfuegbar". Kein API-Call fuer diese Kachel in v1; sie wird rein clientseitig als statischer Platzhalter gerendert, damit spaeter nur die Datenquelle angebunden werden muss, ohne das Layout zu aendern.
- Card "Markt-Trend" (grosse Flow-/Area-Chart-Karte): Recharts-Area-/Line-Chart mit den Top-N Spielern nach `abs(delta_previous_day_eur)` aus zuletzt geladenen Historien; alternativ (einfacher fuer v1) Platzhalter-Karte "Marktwert-Entwicklung ausgewaehlter Spieler" mit manueller Spielerauswahl (max. 3-5 Spieler zum Vergleich, siehe Abschnitt 4.2).
- Card "Transfermarkt-Aktivitaet" (Donut-/Ring-Chart wie im Referenzbild "Traffic sources"): Anteil `listed=true` vs. `listed=false` am aktuellen Snapshot-Tag.
- Card "Neu auf dem Transfermarkt" / "Top Marktwert-Gewinner/-Verlierer": kompakte Liste (Name, Team-Badge, `TrendBadge`) basierend auf den geladenen Listendaten.
- Alle Dashboard-Karten sind bewusst auf **bereits vorhandene** API-Endpunkte begrenzt; es werden keine neuen Backend-Endpunkte in diesem Dokument vorausgesetzt. Wo ein Aggregat fehlt, wird das in Abschnitt 8 als offener Punkt vermerkt statt es zu erfinden.

### 4.2 Spielerliste (`/spieler`)

- Datenquelle: `GET /api/v1/players` (`limit`, `offset`, `team_id`, `position`, `search`).
- UI: Tabelle mit Spalten Name, Position (`Badge`), Team, aktueller Marktwert (`current_value_eur`, formatiert als EUR), `Sparkline` (optional v2, benoetigt zusaetzliche History-Calls und wird daher erst nach v1 aktiviert), Aktion "Details".
- Filterleiste oberhalb der Tabelle: Textsuche (`search`), Team-Dropdown (`team_id`, gespeist aus `GET /api/v1/teams`), Position-Dropdown (`position` enum `TW/ABW/MITT/ST`).
- Pagination: Standard `limit=25`, Seitensteuerung ueber `offset`; Gesamtzahl aus `total` anzeigen ("Zeige 1-25 von 412").
- Mehrfachauswahl (Checkbox je Zeile, max. 5) fuer "Zum Vergleich hinzufuegen" -> fuehrt zu einer Vergleichsansicht (Modal oder eigene Route `/spieler/vergleich?ids=...`), die mehrere `GET /api/v1/players/{id}/history`-Aufrufe parallel in einem gemeinsamen Line-Chart darstellt (mehrere Farben aus der Akzentpalette + abgeleiteten Tonwerten).

### 4.3 Spielerdetail (`/spieler/[id]`)

- Datenquelle: `GET /api/v1/players/{id}` (Stammdaten) und `GET /api/v1/players/{id}/history` (`from_date`, `to_date`, `limit`).
- Kopfbereich: Name, Position-Badge, Team-Link, `current_value_eur` gross dargestellt, `TrendBadge` fuer `delta_previous_day_eur`/`percent_delta_previous_day` aus dem juengsten History-Eintrag.
- Zeitraum-Umschalter (z. B. 30 Tage / 90 Tage / Saison / gesamt) steuert `from_date`/`to_date` fuer den History-Request neu.
- Haupt-Chart: Recharts Line-/Area-Chart ueber `snapshot_date` vs. `value_eur`; Tooltip zeigt zusaetzlich `previous_value_eur`, `delta_previous_day_eur`, `percent_delta_previous_day` aus dem jeweiligen Datenpunkt.
- Sekundaerblock "Seit Erstsichtung": zeigt `first_snapshot_date`, `first_value_eur`, `delta_first_eur`, `percent_delta_first` des neuesten Punkts als eigene KPI-Kachel.
- Nullable-Felder werden explizit als "keine Vergleichsdaten" (z. B. `-` oder ausgegrauter Text) dargestellt, nie als `0`, gemaess der Backend-Regel in `data_model.md` Abschnitt 4.
- Fehlerzustand: 404 vom Backend -> eigener `ErrorState` mit Link zurueck zur Spielerliste.

### 4.4 Teamliste (`/teams`)

- Datenquelle: `GET /api/v1/teams` (`search`, `league`, `season`, Pagination wie bei Spielern).
- Tabelle: Name, Liga, Saison, `player_count` (Badge/Zahl), Aktion "Details".

### 4.5 Teamdetail (`/teams/[id]`)

- Datenquelle: `GET /api/v1/teams/{id}` und `GET /api/v1/players?team_id={id}` fuer die Kaderliste (gleiche Tabellenkomponente wie `/spieler`, aber vorgefiltert und ohne Team-Filter-Steuerelement).

### 4.6 Transfermarkt (`/transfermarkt`)

- Datenquelle: `GET /api/v1/transfermarket` (`limit`, `offset`, `snapshot_date`, `listed`).
- Anzeige des aktuellen `snapshot_date` (aus Response) prominent im Seitenkopf ("Stand: TT.MM.JJJJ").
- Tabelle: Spieler (Link zu Detail), Team, Position, Preis (`price_eur`, EUR-formatiert oder "-" falls `null`), `owner_name` (falls vorhanden), `listed`-Badge.
- Hinweis-Banner (`EmptyState`), falls `items` leer ist bzw. `owner_name` grundsaetzlich `null` ist (siehe `data_model.md` 5: aktuell noch keine Befuellung durch die Ingest-Pipeline) -> Text: "Transfermarktdaten werden aktuell noch nicht befuellt." statt eines irrefuehrenden leeren Tabellenzustands.
- Datenschutz-Hinweis: `owner_name` ist ein Comunio-Benutzername und damit personenbezogen (siehe `data_model.md` 5). Die fachliche Freigabe zur Anzeige liegt vor; die Spalte wird trotzdem hinter einem Feature-Flag (`NEXT_PUBLIC_SHOW_OWNER_NAME`, Standardwert `true`) gefuehrt, damit sie bei Bedarf jederzeit ohne Codeaenderung deaktiviert werden kann.

## 5. Responsives Verhalten

- Breakpoints: Tailwind-Defaults (`sm`, `md`, `lg`, `xl`).
- `< md`: Sidebar wird zu einem einklappbaren Off-Canvas-Menu (Hamburger-Icon im Header, `Sheet`-Komponente); KPI-Kacheln stapeln sich einspaltig; Tabellen werden horizontal scrollbar statt umzubrechen (kein Card-Stacking von Tabellenzeilen in v1, um Komplexitaet gering zu halten).
- `md` - `lg`: Sidebar sichtbar, KPI-Kacheln 2-spaltig, Chart-Karten stapeln sich.
- `>= lg`: volles Layout wie im Referenzbild (Sidebar + 4 KPI-Kacheln + 2x2 Chart-/Listen-Grid).

## 6. Datenanbindung / API-Integration

### 6.1 Environment-Konfiguration

- `NEXT_PUBLIC_API_BASE_URL`: Zielbasis der FastAPI fuer die serverseitige Next.js-Proxy-Route. Die Variable wird in Vercel fuer Production/Preview/Development getrennt gepflegt und niemals im Code hartkodiert.
- `API_PROXY_SECRET`: serverseitiges Vercel-Secret fuer den Proxy-Request an die FastAPI; niemals als `NEXT_PUBLIC_*`-Variable konfigurieren. Die API muss das Secret serverseitig validieren, bevor der Proxy als Produktionsschutz gilt.
- `NEXT_PUBLIC_SHOW_OWNER_NAME`: oeffentliche Feature-Flag fuer die Transfermarkt-Spalte, Standardwert `true`.
- CORS bleibt als Backend-Schutz fuer erlaubte Origins konfiguriert, ist aber nicht der primaere Frontend-Zugriffspfad, weil Browser nur `/api/proxy/...` aufrufen.

### 6.2 Typisierte API-Schicht

Ein schlanker, generierter oder manuell gepflegter API-Client-Layer (`lib/api/`) mit 1:1-TypeScript-Typen zu den Pydantic-Schemas:

```text
lib/api/types.ts        // Position, PlayerSummary, PlayerDetail, TeamSummary, TeamDetail,
                         // MarketValuePoint, PlayerHistoryResponse, TransferMarketItem,
                         // TransferMarketResponse, Page<T>
lib/api/client.ts        // fetch-Wrapper mit Basis-URL, Error-Mapping (404/422/503), Timeout
lib/api/players.ts       // getPlayers(), getPlayer(id), getPlayerHistory(id, params)
lib/api/teams.ts         // getTeams(), getTeam(id)
lib/api/transfermarket.ts// getTransfermarket(params)
```

Regeln:

- Enum `Position` wird 1:1 als TS-Union `"TW" | "ABW" | "MITT" | "ST"` gefuehrt; Anzeige-Labels ("Torwart", "Abwehr", "Mittelfeld", "Sturm") werden nur in der UI-Schicht gemappt, nicht im Datenmodell.
- Nullable Backend-Felder (`team_id`, `team_name`, `current_value_eur`, alle Delta-/Referenzfelder) bleiben `T | null` in TypeScript, kein stilles Ersetzen durch `0`/`""` beim Parsen.
- Datumsfelder (`snapshot_date`, `captured_at`, etc.) werden als `string` (ISO/`YYYY-MM-DD`) belassen und erst in der UI-Schicht formatiert/geparst (`date-fns`), nicht global in `Date`-Objekte umgewandelt, um Zeitzonenfehler bei reinen Datumswerten zu vermeiden.
- Fehlerbehandlung folgt dem Backend-Vertrag: 404 -> `ErrorState` "Nicht gefunden"; 422 -> Formular-/Filterfehler inline anzeigen; 503 -> globaler `ErrorState` "Daten aktuell nicht verfuegbar" mit Retry-Button; keine Rohdetails aus Fehlerantworten anzeigen (Backend liefert ohnehin sanitizte `code`/`message`-Felder).

### 6.3 Daten-Fetching-Strategie

- Server Components (App Router) fuer den initialen Render von Listenseiten (`/spieler`, `/teams`, `/transfermarkt`) mit den in der URL enthaltenen Filter-/Pagination-Query-Params -> schnelles First Paint, SEO-faehig, kein Client-Loading-Spinner beim ersten Laden.
- Client Components + TanStack Query fuer:
  - interaktive Nachfilterungen ohne vollen Seiten-Reload,
  - Spielerdetail-Charts mit Zeitraum-Umschalter (mehrere `history`-Requests je nach gewaehltem Zeitraum),
  - Vergleichsansicht mit parallelen Requests.
- Kein globales State-Management (Redux etc.) noetig; URL-Suchparameter sind die "Single Source of Truth" fuer Filter-/Pagination-Zustand (teilbare/bookmarkbare Links), TanStack Query cached die zugehoerigen Responses.

## 7. Projektstruktur (Next.js App Router)

```text
frontend/
  app/
    layout.tsx                 // Root-Layout, Theme-Provider (dark als einziges Theme), Fonts
    globals.css                 // Tailwind-Direktiven + CSS-Variablen aus Abschnitt 3.1
    page.tsx                    // Dashboard "/"
    spieler/
      page.tsx                  // Spielerliste
      [id]/page.tsx              // Spielerdetail
      vergleich/page.tsx         // Vergleichsansicht (v2, optional)
    teams/
      page.tsx
      [id]/page.tsx
    transfermarkt/
      page.tsx
  components/
    layout/                     // Sidebar, Header, GlobalSearch
    charts/                     // MarketValueChart, TrendDonutChart, Sparkline
    tables/                     // PlayerTable, TeamTable, TransferMarketTable, DataTablePagination
    ui/                          // shadcn/ui-generierte Basiskomponenten (Card, Badge, Tabs, ...)
    shared/                     // TrendBadge, EmptyState, ErrorState, LoadingSkeletons
  lib/
    api/                         // siehe Abschnitt 6.2
    format.ts                    // EUR-/Datums-/Prozent-Formatierung (Intl.NumberFormat de-DE)
    query-client.ts              // TanStack Query Client Setup
  styles/
    theme.ts                     // Tailwind-Theme-Tokens (siehe 3.1), falls nicht direkt in globals.css
  public/
  tailwind.config.ts
  next.config.ts
  package.json
  tsconfig.json
  .env.example                  // NEXT_PUBLIC_API_BASE_URL, NEXT_PUBLIC_SHOW_OWNER_NAME (Default: true)
```

`frontend/` liegt als eigenstaendiges Verzeichnis auf oberster Ebene neben `backend/`, analog zur bestehenden Monorepo-Struktur.

## 8. Offene Punkte / spaetere Entscheidungen

Diese Punkte sind bewusst **nicht** Teil der ersten Umsetzung und werden hier nur vermerkt:

- Aggregat-Endpunkt fuer "Gesamtmarktwert"/"Durchschnittsmarktwert" existiert im Backend noch nicht; falls gewuenscht, muss dies zuerst als neuer `/api/v1/...`-Endpunkt spezifiziert werden. Das Frontend-Layout haelt dafuer bereits eine deaktivierte Platzhalter-Kachel vor (Abschnitt 4.1); sobald der Endpunkt steht, wird nur `lib/api/` um eine Funktion ergaenzt und die Kachel von Platzhalter- auf Live-Zustand umgeschaltet, ohne Layout-Aenderung.
- Freigabe zur Anzeige von `owner_name` (Comunio-Benutzername) im Transfermarkt liegt vor; `NEXT_PUBLIC_SHOW_OWNER_NAME` startet daher mit `true` und dient nur noch als Notfall-Schalter, falls die Freigabe spaeter widerrufen wird.
- Benutzer-Authentifizierung und Rollen (Admin/User) sind laut `architecture.md` Abschnitt 5 noch nicht spezifiziert; v1 ist daher ohne Benutzerlogin read-only. Der technische serverseitige Proxy-Secret-Schutz ist bereits vorgesehen.
- AP-13.a bleibt vor dem Livegang offen: Die FastAPI muss direkte Requests ohne gueltiges Proxy-Secret mit `401` ablehnen; danach sind Proxy-, 401-, Timeout- und Fehlerweitergabe-Tests gegen die produktive API auszufuehren.
- "Zuletzt aktualisiert am"-Anzeige (aus `ingest_runs`) benoetigt einen eigenen kleinen Status-Endpunkt (z. B. `GET /api/v1/status`); die Daten dafuer existieren bereits in `ingest_runs`, es fehlt nur die API-Exposition. Der Header haelt dafuer bereits eine deaktivierte Platzhalter-Anzeige vor (siehe oben); sobald der Endpunkt steht, wird nur `lib/api/` ergaenzt und die Anzeige von Platzhalter- auf Live-Zustand umgeschaltet.

## 9. Umsetzungsanleitung (Schritt fuer Schritt)

Diese Reihenfolge ist die empfohlene Bauanleitung fuer die spaetere Implementierung auf Basis dieses Dokuments:

1. **Projekt-Setup**: `frontend/` mit Next.js 16.3.5 (App Router, TypeScript) initialisieren, Tailwind CSS und lokale UI-Basiskomponenten einrichten, Inter/JetBrains Mono einbinden.
2. **Theme**: CSS-Variablen und Tailwind-Tokens aus Abschnitt 3.1-3.3 anlegen, globales Dark-Only-Layout (`layout.tsx`, `globals.css`) umsetzen, Sidebar- und Header-Grundgeruest ohne echte Daten bauen.
3. **API-Schicht**: `lib/api/types.ts` deckungsgleich zu `backend/src/api/schemas.py` erstellen, danach `lib/api/client.ts` und die endpunktspezifischen Funktionen (Abschnitt 6.2) inklusive Fehler-Mapping.
4. **Basiskomponenten**: `ui/`-Komponenten (Card, Badge, Table, Tabs, Skeleton, Tooltip) via shadcn/ui generieren und an das Theme anpassen; danach `shared/` (`TrendBadge`, `EmptyState`, `ErrorState`).
5. **Listenseiten**: `/spieler`, `/teams`, `/transfermarkt` inklusive Filter, Suche, Pagination gegen die echten Endpunkte umsetzen (Abschnitt 4.2, 4.4, 4.6).
6. **Detailseiten**: `/spieler/[id]` mit Chart und Delta-Kacheln, `/teams/[id]` mit Kaderliste (Abschnitt 4.3, 4.5).
7. **Dashboard**: `/` mit KPI-Kacheln und den beiden Chart-/Listen-Karten zuletzt umsetzen, da es Daten aus mehreren bereits gebauten Bereichen wiederverwendet (Abschnitt 4.1).
8. **Responsivitaet und Zugaenglichkeit**: Breakpoints aus Abschnitt 5 pruefen, Tastaturfokus/Kontraste (WCAG AA) gegen die Neon-Akzente verifizieren.
9. **Vergleichsansicht** (`/spieler/vergleich`) und Sparklines in der Spielerliste als optionaler v2-Ausbau, sobald v1 stabil ist.
10. **Deployment**: Vercel-Projekt mit `NEXT_PUBLIC_API_BASE_URL` (Production/Preview) verbinden, `API_ALLOWED_ORIGINS` im Backend um die finale Vercel-Domain ergaenzen, End-to-End gegen die produktive/Staging-API pruefen.

## 10. Nicht-funktionale Anforderungen fuer das Frontend

- Ladezeit: Time to Interactive unter 2 Sekunden auf einer Standard-Breitbandverbindung, gemaess `architecture.md` Abschnitt 7.
- Zugaenglichkeit: WCAG AA Kontrastverhaeltnisse fuer Text auf `bg-canvas`/`bg-surface`; alle interaktiven Elemente per Tastatur erreichbar; sichtbarer Fokus-Ring (`--focus-ring`).
- Keine Speicherung sensibler Daten im Browser (kein LocalStorage fuer Tokens); Filter-/Pagination-Zustand bleibt teilbar und wird nicht als Secret behandelt.
- Keine Inline-Secrets: `NEXT_PUBLIC_*`-Variablen sind nur fuer oeffentliche Konfiguration, `API_PROXY_SECRET` bleibt serverseitig und wird nicht ins Client-Bundle aufgenommen.
