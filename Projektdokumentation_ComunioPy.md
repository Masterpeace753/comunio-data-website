# Projektdokumentation: Eigener Comunio-REST-Adapter

## Entscheidung

Dieses Projekt verwendet einen eigenen `ComunioPyClient` als API-Adapter und
Comunio als Datenquelle für alle Comunio-bezogenen Funktionen. Das externe
Legacy-Paket `comuniopy` ist keine Abhängigkeit des Projekts.

## Begründung

- **Stabilität:** Der Adapter kontrolliert Login, Timeouts, Pagination und Fehlerbehandlung selbst.
- **Funktionsumfang:** Breitere Abdeckung (Teams, Spieler, Marktwerte, Transfermarkt).
- **Wartbarkeit:** Die Schnittstelle ist im Projektcode sichtbar und testbar.
- **Datenqualität:** Normalisierung und Positionsmapping werden zentral im Adapter umgesetzt.

## Abgedeckte Use Cases

- Spieler pro Team inkl. Marktwert, Marktwert‑Deltas, Punkten.
- Tägliche Marktwert‑Snapshots.
- Transfermarkt‑Daten (Spieler auf dem Markt, Preise, Besitzer).
- Historisierung aller Werte.
- Delta‑Berechnung (Vortag / Erstwert).

## Datenmodell (Kurzfassung)

- **players**\
  Spieler-Stammdaten (ID, Name, Position, Team, Transfermarkt-ID)
- **teams**\
  Team-Stammdaten
- **market_values**\
  Historische Marktwerte (Snapshot-Tabelle)
- **points**\
  Punkte pro Spieltag
- **transfermarket_snapshots**\
  Spieler auf dem Transfermarkt inkl. Preis & Besitzer

## Delta-Berechnung

- `snapshot_date` ist die fachliche Zeitachse; `captured_at` ist nur der technische Erfassungszeitpunkt.
- Das Vortagsdelta verwendet ausschliesslich den exakten Kalendertag davor. Fehlt dieser Snapshot, bleiben Referenz und Vortagsdelta `NULL`.
- Das Erstwertdelta verwendet den chronologisch ersten Snapshot der gesamten Spielerhistorie; beim ersten Snapshot ist es `0`.
- Prozentwerte sind bei fehlender Referenz oder Referenzwert `0` `NULL`.
- Deltas werden in der read-only-API-Projektion berechnet und nicht redundant gespeichert. Details stehen in `data_model.md` und `implementierungsplan.md`.

## Architektur (Kurzüberblick)

- **Ingest:** Python + eigener ComunioPyClient
- **DB:** PostgreSQL (optional TimescaleDB)
- **Backend:** FastAPI
- **Frontend:** React auf Vercel
- **Automatisierung:** EventBridge → ECS Fargate
- **Monitoring:** CloudWatch Logs sowie native ALB-Metriken fuer API-P95 und Fehlerquoten

## Update-Frequenz

- Marktwerte: täglich (optional mehrfach)
- Punkte: nach Spieltag

## Urspruengliche To-do-Liste (historischer Plan)

1. Repo + README erstellen
1. DB‑Schema implementieren
1. Comunio-REST-Login + Team-Abruf testen
1. Snapshot‑Job implementieren
1. Delta‑Berechnung implementieren
1. Transfermarkt‑Abruf testen
1. Dashboard‑MVP erstellen
1. Legal Check

Die aktuelle verbindliche Roadmap steht in `implementierungsplan.md`. AP-11, AP-12
und AP-13 sind umgesetzt; private Netzwerke, HTTPS/ACM, WAF, Remote-State-Migration
und eine AWS-Staging-Baseline bleiben nachgelagerte Entscheidungen.

## Persistenz der Entscheidung

- Entscheidung im README verankert
- CI-Check prueft den eigenen ComunioPyClient und seine REST-Adapter-Tests
- Dokumentation im `/docs`‑Ordner
