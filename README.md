# Comunio Data Website

Release-Version: v0.5.0 (AP-11 Read-only FastAPI API, Vercel CORS and CI)

## Repository-Beschreibung

Dieses Repository enthält die vollständige Comunio-Datenplattform: einen Python-Ingest für tägliche Snapshots, PostgreSQL-Migrationen und Historisierung, eine read-only FastAPI für das Vercel-Frontend, AWS-ECS/Fargate- und Terraform-Infrastruktur sowie Tests, CI/CD-, Security- und Betriebsdokumentation.

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

Die AWS-Baseline ist deployed. Migrationen sowie ein produktiver Live-Snapshot mit Secrets Manager Credentials wurden End-to-End erfolgreich ausgefuehrt; der letzte Lauf schrieb 600 Datensaetze. Der AP-9-Scheduler laeuft taeglich um 06:00 UTC ueber EventBridge und ECS Fargate. AP-9.2 ergaenzt einen automatischen Login-Retry (3 Versuche im 5-Minuten-Abstand) mit CloudWatch-Alarm bei erschoepften Versuchen. Die Backend-Tests bestehen.

Der Drei-Lauf-Stabilitaetsnachweis fuer AP-9 ist erbracht (fuenf aufeinanderfolgende erfolgreiche Tagesfenster 2026-08-27 bis 2026-08-31, siehe `implementierungsplan.md` Abschnitt 19). Noch offen sind die verbindlichen State-/Security-Gates und die Phase-3-Arbeiten fuer die API.

Der vollstaendige Security-Review vom 2026-08-25 steht unter [docs/code-review/2026-08-25-full-project-security-review.md](docs/code-review/2026-08-25-full-project-security-review.md). Der aktuelle Production-Readiness-Status ist **No-Go**, bis insbesondere die Logging-Sanitization, die unveraenderliche Image-Referenz und die nicht umgehbare Produktions-Secret-Policy umgesetzt sind.

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
1. Abhaengigkeiten installieren.
1. Umgebungswerte aus [backend/.env.example](backend/.env.example) setzen.
1. Migrationen ausfuehren.
1. Login-Check oder Snapshot-Run starten.

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
- AP-9/AP-9.2 Scheduler-Runbook (inkl. Login-Retry und Alarm): [backend/OPERABILITY-AP9.md](backend/OPERABILITY-AP9.md)
- AWS Deployment-Baseline: [infra/aws/README.md](infra/aws/README.md)
- Security-Review: [docs/code-review/2026-08-25-full-project-security-review.md](docs/code-review/2026-08-25-full-project-security-review.md)

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
- requests: wird vom eigenen Comunio-REST-Adapter verwendet

Hinweis zum Comunio-Adapter:

- Das externe Legacy-Paket `comuniopy` ist keine Projektabhaengigkeit und wird nicht importiert.
- `backend/src/ingest/comuniopy_client.py` enthaelt stattdessen den eigenen `ComunioPyClient` fuer Login, Snapshot-Abruf und Normalisierung.
- Der produktive AWS-Live-Snapshot wurde mit diesem Adapter erfolgreich ausgefuehrt.

## Naechste Schritte

1. Blockierendes Security-Finding H1 schliessen: rohe Exception-Details aus Logs entfernen und Sanitization-Tests ergaenzen.
1. Terraform-State sicher verwalten und sensible Werte rotieren, falls sie ausserhalb des geschuetzten AWS-/CI-Kontexts exponiert waren.
1. Produktions-Secret-Policy strukturell erzwingen und auf immutable Container-Image-Referenzen umstellen.
1. Nach dem Drei-Lauf-Nachweis AP-10 Idempotenz-/Retry-Nachweise vervollstaendigen und AP-11 FastAPI-Endpunkte umsetzen.

Die verbindliche Reihenfolge und das priorisierte Rest-Backlog stehen im [Implementierungsplan](implementierungsplan.md).
