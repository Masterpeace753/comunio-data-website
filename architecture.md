# Architektur des Comunio-Datenprojekts

## Ziel
Automatisierte Erfassung, Speicherung und Visualisierung von Comunio‑Daten
(Marktwerte, Punkte, Transfermarkt, Teams, Spieler).

---

## Gesamtarchitektur

ComunioPy → Ingest → PostgreSQL → FastAPI → Frontend (React/Dash)


---

## Komponenten

### 1. Ingest (Python)
- Abruf aller Daten über ComunioPy  
- Tägliche Snapshot‑Jobs  
- Speicherung in PostgreSQL  
- Fehlerlogging + Alerts  

### 2. Datenbank (PostgreSQL)
- Relationales Modell  
- Optional TimescaleDB für Zeitreihen  
- Tabellen: players, teams, market_values, points, transfermarket_snapshots  

### 3. Backend (FastAPI)
- Endpunkte für:
  - Spielerübersicht
  - Teamübersicht
  - Marktwert‑Historie
  - Transfermarkt‑Status
- Authentifizierung optional

### 4. Frontend (React oder Dash)
- Dashboard mit:
  - Team‑Ansicht
  - Spieler‑Detailseite
  - Marktwert‑Graphen
  - Transfermarkt‑Übersicht

### 5. Automatisierung
- Cron‑Jobs (z. B. 02:00 Uhr)
- Optional Airflow für komplexere Pipelines

### 6. Monitoring
- Logging (Python + DB)
- Alerts bei:
  - fehlgeschlagenen Requests
  - leeren Snapshots
  - API‑Fehlern

---

## Datenfluss

1. ComunioPy authentifiziert sich  
2. Daten werden abgerufen  
3. Snapshots werden gespeichert  
4. Backend stellt Daten bereit  
5. Frontend visualisiert sie  

---

## Skalierung
- Docker‑Container für alle Services  
- Load Balancer für API  
- Caching (Redis) optional  
- CDN für Frontend  

