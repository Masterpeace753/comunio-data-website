# Comunio Data Website

Release-Version: 0.2.1 (Security Patch)

Ziel dieses Projekts ist eine moderne, skalierbare Plattform zur Erfassung, Speicherung und Auswertung von Comunio-Daten.

## Projektziel

Das Projekt liefert:
- stabilen Datenabruf mit ComunioPy
- historisierte Speicherung in PostgreSQL
- Backend-API fuer Auswertung und Bereitstellung
- Frontend-Dashboard auf Vercel
- Betrieb mit Security-, Monitoring- und CI/CD-Baseline

## Aktueller Stand

Phase 1 ist umgesetzt (Analyse und Setup).

Phase 2 ist auf Code- und Dokumentationsseite umgesetzt:
- AP-5: ComunioPy Login-Integration
- AP-6: Datenbankschema und Migrationen
- AP-7: Manueller Snapshot-Job (Teams, Spieler, Marktwerte)
- AP-8: Basis-Fehlerbehandlung und Retry/Backoff

Die laufenden Nachweise werden ueber Runbooks und Smoke Checks gefuehrt.

## Architektur und Planung

- Zielarchitektur: [architecture.md](architecture.md)
- Datenmodell: [data_model.md](data_model.md)
- Umsetzungsplan: [implementierungsplan.md](implementierungsplan.md)
- Lastenheft: [Lastenheft_Comunio_Projekt.md](Lastenheft_Comunio_Projekt.md)
- ComunioPy Entscheidung: [Projektdokumentation_ComunioPy.md](Projektdokumentation_ComunioPy.md)

## Projektstruktur

- [backend](backend): Ingest, Migrationen, Operability-Runbooks
- [agents](agents): hinterlegte Agent-Profile
- [architecture.md](architecture.md): technische Zielarchitektur
- [data_model.md](data_model.md): fachliches und technisches Datenmodell
- [implementierungsplan.md](implementierungsplan.md): Roadmap und Abnahmekriterien

## Backend Quick Start

Voraussetzungen:
- Python 3.11+
- PostgreSQL erreichbar

Schritte:
1. In den Backend-Ordner wechseln.
2. Abhaengigkeiten installieren.
3. Umgebungswerte aus [backend/.env.example](backend/.env.example) setzen.
4. Migrationen ausfuehren.
5. Login-Check oder Snapshot-Run starten.

Beispielbefehle (PowerShell):

```powershell
Set-Location backend
python -m pip install -r requirements.txt
python -m migrations.runner
python -m src.ingest.runner --run-type manual --mode login
python -m src.ingest.runner --run-type manual --mode snapshot
```

Hinweis fuer lokale, deterministische Tests:
- Mit COMUNIO_SNAPSHOT_FILE kann statt Live-API eine Fixture-Datei genutzt werden.
- Beispiel: [backend/tests/sample_snapshot.json](backend/tests/sample_snapshot.json)

## Operability und Smoke Checks

- AP-5/AP-6 Runbook: [backend/OPERABILITY-AP5-AP6.md](backend/OPERABILITY-AP5-AP6.md)
- AP-7 Runbook: [backend/OPERABILITY-AP7.md](backend/OPERABILITY-AP7.md)

Verbindliche Gates vor dem naechsten Ausbau:
- G1 Login-Bootstrap
- G2 Migrations-Idempotenz
- G3 Schema-Integritaet

## Requirements-Status

Aktuelle Datei: [backend/requirements.txt](backend/requirements.txt)

Einschaetzung Stand heute:
- boto3: technisch aktuell einsetzbar
- psycopg2-binary: technisch aktuell einsetzbar
- python-dotenv: technisch aktuell einsetzbar
- comuniopy: funktional kritisch pruefen

Wichtiger Hinweis zu ComunioPy:
- In der aktuellen Umgebung wurde ein Legacy-Modul (ComunioPy) erkannt, das auf Python 3 Import-Probleme verursachen kann.
- Der AP-7 Snapshot-Run funktioniert lokal trotzdem im Fixture-Modus.
- Fuer produktiven Live-Login ist als naechster Schritt die Bibliotheks-/Adapter-Kompatibilitaet verbindlich zu stabilisieren.

## Naechste Schritte

1. Live-Kompatibilitaet des ComunioPy-Clients final absichern.
2. AP-7 End-to-End mit realer DATABASE_URL und echten Credentials erfolgreich nachweisen.
3. Danach in Phase 3 mit Scheduler und API-Ausbau fortfahren.
