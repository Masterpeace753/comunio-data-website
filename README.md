# Comunio Data Website

Release-Version: v0.6.1 (Authenticated API Go-live and Vercel Proxy Integration)
Dokumentationsstand: 2026-11-08

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

**Betriebsstand 08.11.2026:** Das Vercel-Frontend nutzt die VPS-API. Der
VPS-Timer ist aktiv; der erste reguläre Lauf heute um 06:00 UTC war
erfolgreich (Lauf-ID 81, 600 Datensätze). Die API und der HTTPS-Proxy liefen
bei der letzten VPS-Prüfung. Der Ingest-Service wurde am 08.11. so angepasst,
dass er auch das HTTPS-Compose-Overlay lädt; die Änderung ist auf dem VPS
installiert und validiert. Der nächste Lauf soll bestätigen, dass dadurch die
Compose-Warnung zu einem vermeintlich verwaisten Proxy entfällt.

Der AWS-Ingest bleibt deaktiviert; AWS-Ressourcen bleiben für den
kontrollierten Rückfall vorerst erhalten. Der AWS-API-Status wurde bei der
Prüfung am 08.11. nicht live verifiziert. Monitoring, regelmäßige Backups und
VPS-Speicherverschlüsselung sind weiterhin offene Betriebsaufgaben. Details:
[Migrationsplan](docs/migration/00-gesamtplan.md) und
[VPS-Validierungsbericht](infra/vps/validation-report-2026-11-07.md).

**Datenladeverlauf (08.11.2026):** Commit `4c863bf` ist auf dem VPS
ausgerollt; Migration 004 ist angewendet. Die neue API ist über HTTPS
erreichbar und bereit für Datenbankzugriffe. Der Verlauf-Endpunkt weist
unauthentifizierte Anfragen zurück. Das Frontend wurde laut Betreiber
automatisch auf Vercel deployed. Der aktualisierte Ingest ist konfiguriert;
ein neuer Produktionslauf wurde nicht manuell gestartet und steht beim
nächsten Timer-Termin zur Laufzeitprüfung an.

### Historischer Projektstand

Phase 1 ist umgesetzt (Analyse und Setup).

Phase 2 ist auf Code- und Dokumentationsseite umgesetzt:

- AP-5: ComunioPy Login-Integration
- AP-6: Datenbankschema und Migrationen
- AP-7: Manueller Snapshot-Job (Teams, Spieler, Marktwerte)
- AP-8: Basis-Fehlerbehandlung und Retry/Backoff

Die folgenden Angaben beschreiben frühere Projekt- und AWS-Meilensteine, nicht
den aktuellen Produktionsbetrieb: Die AWS-Baseline, Migrationen und
Live-Snapshots wurden umgesetzt; AP-9 verwendete zuvor EventBridge und ECS
Fargate. Der aktuelle tägliche Produktions-Ingest läuft auf dem VPS über
systemd und Docker Compose (siehe oben und das VPS-Runbook). Das
Frontend-v1 ist unter `frontend/` als Next.js-App mit serverseitigem
Vercel-Proxy, typisierter API-Schicht, Dashboard, Spieler-, Team- und
Transfermarktseiten umgesetzt. Ältere Aussagen weiter unten, die AWS-API sei
abgeschaltet oder vor einer Reaktivierung stünden, beschreiben einen
überholten Zustand.

Der Drei-Lauf-Stabilitaetsnachweis fuer AP-9 ist erbracht (fuenf aufeinanderfolgende erfolgreiche Tagesfenster 2026-08-27 bis 2026-08-31, siehe `implementierungsplan.md` Abschnitt 19). AP-11 ist als kostenorientiertes HTTP-MVP verifiziert. AP-12 ist als read-only-Delta-Projektion umgesetzt. AP-13 ist mit PostgreSQL-16-Integrationstests, OpenAPI-Contract-Test, Fehlerpfadtests, Benchmark-Skript und nativen ALB-CloudWatch-Alarmen umgesetzt.

Der vollständige Security-Review vom 2026-08-25 steht unter
[docs/code-review/2026-08-25-full-project-security-review.md](docs/code-review/2026-08-25-full-project-security-review.md).
Die dortigen sowie die nachfolgenden historischen AWS-Notfallhinweise sind
keine aktuelle Betriebsanweisung. Für den aktuellen VPS- und API-Status gilt
ausschließlich das [VPS-Runbook](infra/vps/README.md).

## Architektur und Planung

- Zielarchitektur: [architecture.md](architecture.md)
- Datenmodell: [data_model.md](data_model.md)
- Umsetzungsplan: [implementierungsplan.md](implementierungsplan.md)
- Lastenheft: [Lastenheft_Comunio_Projekt.md](Lastenheft_Comunio_Projekt.md)
- ComunioPy Entscheidung: [Projektdokumentation_ComunioPy.md](Projektdokumentation_ComunioPy.md)

## Projektstruktur

- [backend](backend): Ingest, Migrationen, Operability-Runbooks
- [frontend](frontend): Next.js-Dashboard und serverseitiger API-Proxy
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

## Operability, Tests und Smoke Checks

- AP-5/AP-6 Runbook: [backend/OPERABILITY-AP5-AP6.md](backend/OPERABILITY-AP5-AP6.md)
- AP-7 Runbook: [backend/OPERABILITY-AP7.md](backend/OPERABILITY-AP7.md)
- AP-9/AP-9.2 Scheduler-Runbook (inkl. Login-Retry und Alarm): [backend/OPERABILITY-AP9.md](backend/OPERABILITY-AP9.md)
- AWS Deployment-Baseline: [infra/aws/README.md](infra/aws/README.md)
- Security-Review (historischer Stichtag): [docs/code-review/2026-08-25-full-project-security-review.md](docs/code-review/2026-08-25-full-project-security-review.md)

Lokale Backend-Tests ohne AWS:

```powershell
Set-Location backend
$env:PYTHONPATH = "."
python -m pytest tests -q
```

Integrationstests gegen PostgreSQL 16:

```powershell
$env:TEST_DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:5432/comunio_test?sslmode=disable"
python -m pytest tests -m integration -q
```

AP-13-Benchmark gegen eine synthetische Testdatenbank:

```powershell
python scripts/benchmark_api.py
```

Abgeschlossene Basis-Gates:

- G1 Login-Bootstrap
- G2 Migrations-Idempotenz
- G3 Schema-Integritaet

Die folgenden API-Angaben beschreiben den früheren AWS-Entwurf, nicht den
aktuellen Go-live: Die Vercel-Integration mit der VPS-API ist umgesetzt und
der VPS-HTTPS-Endpunkt ist aktiv. WAF, private API-Subnets, NAT/VPC-Endpoints
und Multi-AZ sind mögliche AWS-Härtungsmaßnahmen, falls AWS später wieder
als Produktionsplattform genutzt wird; SNS-E-Mail ist über
`alert_sns_topic_arn` optional.

Das Frontend nutzt Next.js 16.4.5 auf Vercel. Die lokalen Frontend-Gates sind `npm ci`, `npm audit --audit-level=moderate`, `npm test`, `npm run lint` und `npm run build`. Die CI führt diese Checks gemeinsam mit Backend-, Terraform- und Security-Scans aus; der npm-Audit umfasst auch Entwicklungsabhängigkeiten.

Die CI prüft zusätzlich veröffentlichte Support-Signale: npm-Deprecations
aller gelockten Pakete, PyPI-Klassifizierung „Inactive“ und vollständig
zurückgezogene Releases der installierten Backend-Pakete sowie die
End-of-Life-Daten von Python, Node.js, PostgreSQL, Terraform, Next.js und
React über [endoflife.date](https://endoflife.date/). Bei fehlenden Metadaten
oder Netzwerkfehlern schlägt die Prüfung fehl. Hersteller melden nicht jedes
Support-Ende maschinenlesbar; ein grüner Check garantiert daher keine
vollständige Erkennung. Die einzige aktuell genehmigte, versionsgenaue
Ausnahme ist ESLint 9.39.5 (siehe [Frontend-README](frontend/README.md)).
Sie soll entfallen, sobald die Next.js-Lint-Plugins mit ESLint 10 kompatibel
sind.

Die CI auditiert die hashgesperrten Backend-Abhängigkeiten und prüft beide
gebauten Images mit Trivy: Alle HIGH/CRITICAL-Befunde werden ausgegeben,
solche mit verfügbarem Fix blockieren. Ohne verfügbaren Fix bleiben sie
sichtbar, blockieren aber nicht. CodeQL analysiert Python und JavaScript/
TypeScript und veröffentlicht die Ergebnisse in GitHub Code Scanning; ein
erfolgreicher Analyse-Job allein bedeutet nicht, dass keine Alerts existieren.
Die Repository-Maintainer prüfen offene Alerts und Scanner-Ausnahmen monatlich
und nach relevanten Sicherheitsmeldungen. Actions sind auf Commit-SHAs
festgelegt; Dependabot schlägt monatliche Updates vor.

## Requirements-Status

Aktuelle Datei: [backend/requirements.txt](backend/requirements.txt)
und das für Linux/Python 3.11 erzeugte
[Lockfile](backend/requirements.lock). CI und Images installieren das Lockfile
mit Hashprüfung; Aktualisierung und Plattformgrenzen stehen im
[Backend-README](backend/README.md).

Einschaetzung Stand heute:

- boto3: technisch aktuell einsetzbar
- psycopg2-binary: technisch aktuell einsetzbar
- python-dotenv: technisch aktuell einsetzbar
- requests: wird vom eigenen Comunio-REST-Adapter verwendet

Hinweis zum Comunio-Adapter:

- Das externe Legacy-Paket `comuniopy` ist keine Projektabhaengigkeit und wird nicht importiert.
- `backend/src/ingest/comuniopy_client.py` enthaelt stattdessen den eigenen `ComunioPyClient` fuer Login, Snapshot-Abruf und Normalisierung.
- Der produktive AWS-Live-Snapshot wurde mit diesem Adapter erfolgreich ausgefuehrt.

## Historisches AWS-Backlog

Die folgenden Punkte betreffen den früheren AWS-Betrieb und sind nicht das
aktuelle VPS-Rest-Backlog. Die offenen VPS-Betriebsaufgaben stehen im
[VPS-Runbook](infra/vps/README.md).

1. SNS-Subscription bestaetigen und `terraform apply` fuer das Alarmrouting ausfuehren, falls E-Mail-Benachrichtigungen gewuenscht sind.
1. AP-13-AWS-Staging-Baseline nur vor groesseren Releases oder bei Skalierungsbedarf starten; sie ist kostenpflichtig und kein MVP-Blocker.
1. Optionales AP-10a.5-Hardening planen: privater ECS-Egress, NAT/VPC-Endpoints, `assign_public_ip=false`, HTTPS/ACM und WAF.
1. Vor Team-Onboarding den Remote-Terraform-State mit `terraform init -migrate-state` nach manueller Freigabe aktivieren.

Der [Implementierungsplan](implementierungsplan.md) dokumentiert die
historische AWS-Roadmap.
