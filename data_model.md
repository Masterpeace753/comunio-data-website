# Datenmodell für das Comunio-Dashboard

## Übersicht
Das Datenmodell ist darauf ausgelegt, tägliche Marktwert‑Snapshots, Spieler‑Punkte,
Transfermarkt‑Daten und Team‑Strukturen effizient zu speichern und auszuwerten.

---

## Tabellen

### 1. players
Stammdaten der Spieler.

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | SERIAL / PK | interne ID |
| comunio_id | INT | eindeutige Comunio-ID |
| name | TEXT | Spielername |
| position | TEXT | Position (TW, AW, MF, ST) |
| team_id | INT (FK) | Verweis auf teams |
| transfermarkt_id | TEXT | optionale TM-ID |
| created_at | TIMESTAMP | Erstellungszeitpunkt |

---

### 2. teams
Stammdaten der Teams.

| Feld | Typ |
|------|-----|
| id | SERIAL / PK |
| name | TEXT |
| league | TEXT |
| season | TEXT |

---

### 3. market_values
Historische Marktwerte (Snapshots).

| Feld | Typ |
|------|-----|
| id | SERIAL / PK |
| player_id | INT (FK) |
| value_eur | INT |
| timestamp | TIMESTAMP |
| source | TEXT |

---

### 4. points
Punkte pro Spieltag.

| Feld | Typ |
|------|-----|
| id | SERIAL / PK |
| player_id | INT (FK) |
| matchday | INT |
| points | INT |
| timestamp | TIMESTAMP |

---

### 5. transfermarket_snapshots
Spieler auf dem Transfermarkt.

| Feld | Typ |
|------|-----|
| id | SERIAL / PK |
| player_id | INT (FK) |
| listed | BOOLEAN |
| price_eur | INT |
| owner | TEXT |
| timestamp | TIMESTAMP |

---

## Beziehungen
- Ein Team hat viele Spieler  
- Ein Spieler hat viele Marktwert‑Snapshots  
- Ein Spieler hat viele Punkte‑Einträge  
- Ein Spieler hat viele Transfermarkt‑Snapshots  

---

## Hinweise
- TimescaleDB kann optional genutzt werden, um `market_values` und `transfermarket_snapshots` als Hypertables zu speichern.
- Alle Tabellen sollten Indizes auf `player_id` und `timestamp` haben.

