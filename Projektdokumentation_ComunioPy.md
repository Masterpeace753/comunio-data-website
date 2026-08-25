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
- **players**  
  Spieler-Stammdaten (ID, Name, Position, Team, Transfermarkt-ID)
- **teams**  
  Team-Stammdaten
- **market_values**  
  Historische Marktwerte (Snapshot-Tabelle)
- **points**  
  Punkte pro Spieltag
- **transfermarket_snapshots**  
  Spieler auf dem Transfermarkt inkl. Preis & Besitzer

## Delta-Berechnung
- Delta Vortag = `value_today - value_yesterday`
- Delta Erstwert = `value_today - value_first_snapshot`
- Fehlende Werte → `NULL`

## Architektur (Kurzüberblick)
- **Ingest:** Python + eigener ComunioPyClient
- **DB:** PostgreSQL (optional TimescaleDB)  
- **Backend:** FastAPI  
- **Frontend:** React oder Dash  
- **Automatisierung:** Cron‑Jobs  
- **Monitoring:** Logging + Alerts  

## Update-Frequenz
- Marktwerte: täglich (optional mehrfach)
- Punkte: nach Spieltag

## To‑Do (erste 2 Wochen)
1. Repo + README erstellen  
2. DB‑Schema implementieren  
3. Comunio-REST-Login + Team-Abruf testen
4. Snapshot‑Job implementieren  
5. Delta‑Berechnung implementieren  
6. Transfermarkt‑Abruf testen  
7. Dashboard‑MVP erstellen  
8. Legal Check  

## Persistenz der Entscheidung
- Entscheidung im README verankert  
- CI-Check prueft den eigenen ComunioPyClient und seine REST-Adapter-Tests
- Dokumentation im `/docs`‑Ordner  

