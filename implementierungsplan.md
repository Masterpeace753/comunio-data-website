# Implementierungsplan fuer das Comunio-Projekt

## 1. Zielbild
Dieser Plan setzt das Lastenheft in umsetzbare Arbeitspakete um und orientiert sich an den vorgegebenen Ausbaustufen, dem Zeitplan und den nicht-funktionalen Anforderungen.

Rahmen:
- Gesamtzeit: 22 Wochen
- Team: Architektur, Backend, Frontend, DevOps, Security
- Zielkosten: Infrastruktur so niedrig wie moeglich

## 2. Liefergegenstaende
- Laufender Ingest-Prozess auf Basis ComunioPy
- PostgreSQL-Datenmodell mit Historisierung
- FastAPI-Backend mit stabilen Endpunkten
- Frontend-Dashboard auf Vercel
- Monitoring, Alerting, Security Hardening
- CI/CD-Pipeline fuer Build, Test und Deployment

## 3. Roadmap nach Wochen

### Phase 1: Analyse und Setup (Woche 1 bis 2)
Ziele:
- Anforderungen finalisieren
- Architektur und Datenmodell verabschieden
- Repositories, Konventionen und Grundgeruest aufsetzen

Arbeitspakete:
- AP-1 Lastenheft-Review und Scope-Fixierung
- AP-2 Architekturentscheidungen dokumentieren
- AP-3 Datenmodell finalisieren
- AP-4 Dev-Umgebung, Docker-Basis, Branching-Strategie

Ergebnis:
- Freigegebene Zielarchitektur
- Freigegebenes Datenmodell
- Projekt-Basis lauffaehig

### Phase 2: Architekturdesign und Ingest-MVP (Woche 3 bis 5)
Ziele:
- Stabiler manueller Abruf als erste Ausbaustufe

Arbeitspakete:
- AP-5 ComunioPy-Integration und Login-Flows
- AP-6 Tabellen und Migrationen umsetzen
- AP-7 Manueller Snapshot-Job fuer Spieler, Teams, Marktwerte
- AP-8 Grundlegendes Logging und Fehlerbehandlung

Hinweis zur aktuellen Umsetzung:
- AP-5 bis AP-8 sind als Phase-2 Ergebnisstand umgesetzt.

Ergebnis:
- Login-Flow ueber ComunioPy ist technisch vorbereitet und testbar.
- Migrationsgrundlage fuer PostgreSQL ist umgesetzt.
- Manueller Snapshot-Lauf schreibt Teams, Spieler und Marktwerte idempotent.
- Basis-Fehlerbehandlung mit Retry/Backoff und ingest_runs Status-Tracking ist aktiv.

### AP-5 Deliverables (umgesetzt)
- Backend-Konfiguration fuer Credentials aus AWS Secrets Manager oder ENV.
- ComunioPy-Client-Bootstrap mit expliziter Login-Validierung.
- Manueller Runner fuer Login-Flow (ohne Snapshot-Verarbeitung).

### AP-6 Deliverables (umgesetzt)
- SQL-Migrationen fuer Core-, Timeseries- und Audit/Event-Tabellen.
- Migration-Runner mit schema_migrations zur Versionsnachverfolgung.
- Kern-Indizes und Idempotenz-Constraints im Schema.

### AP-7 Deliverables (umgesetzt)
- Manueller Snapshot-Lauf im Runner (`--mode snapshot`).
- Snapshot-Normalisierung fuer Teams, Spieler und Marktwerte.
- Idempotente Upserts auf Tabellenebene.
- ingest_runs Tracking fuer success/failed und records_written.

### AP-8 Deliverables (umgesetzt)
- Basis-Error-Handling mit klaren Fehlermeldungen je Pipeline-Schritt.
- Retry/Backoff fuer Snapshot-Abruf (2s, 4s, 8s, insgesamt 4 Versuche).
- Operatives Smoke-Runbook fuer AP-5/AP-6 vorhanden und weiterverwendbar.

### AP-5/AP-6 Definition of Done
- AP-5:
	- Login-Bootstrap liefert success oder failed mit klarer Ursache.
	- Keine Secrets im Quellcode oder im Repository.
- AP-6:
	- Migrationen lassen sich sequenziell anwenden.
	- Wiederholte Ausfuehrung erzeugt keine doppelten Tabellen.
	- Schema umfasst alle fuer AP-7 benoetigten Kernstrukturen.

### AP-7/AP-8 Definition of Done
- AP-7:
	- Manuelle Ausfuehrung verarbeitet Snapshotdaten fuer Teams, Spieler, Marktwerte.
	- Wiederholte Ausfuehrung am gleichen Tag erzeugt keine Duplikate in market_values.
- AP-8:
	- Snapshot-Abruf hat Retry/Backoff und bricht nach Maximalversuchen kontrolliert ab.
	- Fehlerfaelle werden als failed-Lauf in ingest_runs nachvollziehbar.

### AP-5/AP-6 Smoke-Check-Runbook
- Operativer Prüfpfad ist dokumentiert in `backend/OPERABILITY-AP5-AP6.md`.
- Verbindliche Gates vor AP-7:
	- G1 Login-Bootstrap PASS
	- G2 Migrations-Idempotenz PASS
	- G3 Schema-Integritaet PASS

### Phase 3: Automatisierung und Backend-API (Woche 6 bis 10)
Ziele:
- Taeglicher Abruf und API als Zugriffsschicht

Arbeitspakete:
- AP-9 Scheduler fuer taegliche Runs mit AWS Tools (implementiert, aktiviert und Stabilitaetsnachweis ueber drei Zeitfenster erbracht, siehe Abschnitt 19)
- AP-9.2 Login-Retry und automatischer Erfolgs-/Fehler-Check (umgesetzt): 3 Login-Versuche im 5-Minuten-Abstand, CloudWatch-Alarm bei erschoepften Retries
- AP-10 Idempotenz-Regeln und Retry-Strategien
- AP-10a Security baseline enforcement (Secrets-Policy, DB-TLS-Policy, Logging-Sanitization, Snapshot-Input-Haertung, immutable Images und Netzwerk-Exposure)
- AP-10b Production Gate Enforcement in CI (Deploy-Block bei Gate-Verletzung, Secret-Scan, Dependency-Scan und Terraform-Pruefungen)
- AP-11 FastAPI-Endpunkte fuer Spieler, Teams, Historie, Transfermarkt
- AP-12 Delta-Berechnungen in API
- AP-13 API-Tests und Performance-Baselines

Ergebnis:
- Taegliche Updates stabil
- Saubere API-Endpunkte fuer Frontend und Integrationen

### Phase 4: Frontend MVP und Ausbau (Woche 11 bis 17)
Ziele:
- Minimal-Frontend und danach Komfort-Ausbau

Arbeitspakete:
- AP-14 Basis-Dashboard (Uebersicht, Team, Spieler)
- AP-15 Marktwert-Historie und Ranking-Ansichten
- AP-16 Transfermarkt-Uebersicht
- AP-17 UX-Verbesserungen, Filter, Sortierung
- AP-18 Frontend-Tests und Monitoring-Einbindung

Ergebnis:
- Nutzbare Web-App mit Kernfunktionalitaet
- Gute Nutzbarkeit fuer taegliche Anwendung

### Phase 5: Skalierung, Security, CI/CD und Release (Woche 18 bis 22)
Ziele:
- Produktionsreife gemaess Lastenheft

Arbeitspakete:
- AP-19 Lasttests und Caching-Strategie
- AP-20 Security-Hardening nach OWASP Top 10
- AP-20a FinOps-Controls (Tag-Compliance, Budget-Alarme, monatlicher Rightsizing-Review)
- AP-21 DSGVO-Readiness (Datenfluss, Protokollierung, Prozesse)
- AP-22 CI/CD-Pipeline mit automatisierten Tests
- AP-23 Go-Live-Checkliste und Deployment

Ergebnis:
- Produktionsfaehige Plattform
- Uptime-, Security- und Wartbarkeitsziele adressiert

## 4. Zuordnung zu den Ausbaustufen
- Stufe Manueller Abruf: Phase 2
- Stufe Taeglicher Abruf: Phase 3
- Stufe Backend-API: Phase 3
- Stufe Minimal-Frontend: Phase 4 (frueh)
- Stufe Frontend-Ausbau: Phase 4 (spaet)
- Stufe Features: Phase 4 bis 5
- Stufe Skalierung: Phase 5
- Stufe Security: Phase 5
- Stufe CI/CD: Phase 5

## 5. Definition of Done je Meilenstein

### M1 Ende Woche 5
- Manueller Ingest-End-to-End laeuft
- Daten korrekt in Kern-Tabellen gespeichert
- Fehlerfaelle dokumentiert

### M2 Ende Woche 10
- Taeglicher Ingest stabil ueber mindestens 7 Tage
- API-Endpunkte liefern valide Antworten
- Automatisierte Tests fuer Kernlogik vorhanden

### M3 Ende Woche 17
- Frontend-MVP und Ausbaufeatures verfuegbar
- Kern-User-Flows ohne Blocker nutzbar
- Ladezeitziele fuer Hauptseiten messbar verbessert

### M4 Ende Woche 22
- Security- und Betriebsanforderungen umgesetzt
- CI/CD mit Quality Gates aktiv
- Release- und Rollback-Prozess getestet

## 6. Risiken und Gegenmassnahmen

1. Risiko: Instabile externe Datenquelle
Massnahme: Retry, Backoff, Alerting, robustes Mapping, Fallback auf letzten gueltigen Snapshot.

2. Risiko: Performanceprobleme bei wachsender Datenmenge
Massnahme: Indexstrategie, Query-Tuning, Caching, Lasttests vor Go-Live.

3. Risiko: Sicherheitsluecken durch schnelle Iteration
Massnahme: Security-Checks in CI, Dependency-Scanning, Threat-Model-Review pro Release.

4. Risiko: Zeitplanabweichungen
Massnahme: Strikte Meilensteine, Scope-Management, priorisierte Must-have-Liste.

## 7. Test- und Qualitaetsstrategie
- Unit-Tests fuer Ingest-Mapping, Delta-Berechnung, API-Services
- Integrationstests fuer DB und API-Endpunkte
- End-to-End-Tests fuer zentrale Frontend-Flows
- Nicht-funktionale Tests: Performance, Stabilitaet, Security-Checks

## 8. Betriebs- und Monitoring-Konzept
- Dashboards fuer Ingest-Status, API-Latenz, Fehlerquote
- Alerts bei Job-Ausfall, leerem Snapshot, hoher Fehlerquote
- Runbook fuer Stoerungsbehebung mit klaren Eskalationswegen

## 9. Naechste konkrete Schritte
Der aktuelle Stand liegt am Uebergang von Phase 2 zu Phase 3:
- AP-5 bis AP-8 sind auf Code- und Dokumentationsebene umgesetzt.
- AWS-Infrastruktur, Migrationen und ein manueller Snapshot im Fixture-Modus sind End-to-End validiert.
- Backend-Tests bestehen; ein produktiver Live-Snapshot mit Secrets Manager Credentials ist End-to-End validiert.

Naechste Schritte in verbindlicher Reihenfolge:
1. AP-10a Security-Baseline abschliessen: Secrets-Manager-Pflicht, DB-TLS-Gate, Logging-Sanitization und Snapshot-Input-Haertung.
2. Terraform-State aus dem Repository entfernen beziehungsweise sicher verwalten und sensible Werte rotieren, falls sie exponiert waren.
3. AP-7 mit echter Comunio-Anmeldung und produktiver DATABASE_URL ist nachgewiesen; der Lauf endete mit `run_success` und 600 geschriebenen Datensaetzen.
4. AP-9 ist als EventBridge-Scheduler aktiv; drei aufeinanderfolgende Zeitfenster mit erfolgreichem `run_type=scheduled` und ohne Duplikate nachgewiesen (erledigt, siehe Abschnitt 19: fuenf aufeinanderfolgende erfolgreiche Tagesfenster 2026-08-27 bis 2026-08-31).
5. Danach AP-10 Idempotenz-/Retry-Nachweise vervollstaendigen und AP-11 als FastAPI-Zugriffsschicht mit API-Tests beginnen.

## 10. Technische Entscheidungen fuer Phase 3

Diese Entscheidungen sind vor dem produktiven Phase-3-Ausbau verbindlich zu treffen oder zu bestaetigen:

- Authentifizierung: JWT/OAuth2-Variante fuer API festlegen.
- Scheduler: EventBridge in Produktion, lokale Variante fuer Entwicklung.
- Secrets: AWS Secrets Manager in Produktion, keine Secrets im Repository.
- Skalierung: API Pod Min/Max, Connection-Pool und Autoscaling-Grenzen definieren.
- Deployment: Rolling Deployments und Rollback-Prozess verbindlich dokumentieren.

## 11. Messbare Akzeptanzkriterien je Meilenstein

### M1 (Woche 5)
- Zwei aufeinanderfolgende Ingest-Runs erzeugen keine Duplikate.
- Kern-Tabellen sind nach Testlauf valide befuellt.
- Parser- und Mapping-Tests erreichen mindestens 80 Prozent Coverage.

### M2 (Woche 10)
- Taeglicher Lauf ist ueber 7 Tage stabil.
- API P95 fuer Standardendpunkte liegt unter 500 ms.
- API-Testabdeckung liegt bei mindestens 75 Prozent.
- Security-Gates S1-S4 sind ohne Verletzung aktiv.
- In Produktion: 0 Runs mit ENV-Credentials.

### M3 (Woche 17)
- Frontend-Hauptseiten erreichen Ladezeit unter 2 Sekunden.
- Kern-User-Flows funktionieren auf Desktop und Mobile.
- E2E-Tests fuer zentrale Flows sind vorhanden.

### M4 (Woche 22)
- Security-Scan ohne offene High/Critical Findings.
- Backup/Restore-Test erfolgreich.
- CI/CD fuehrt Build, Tests und Deployments reproduzierbar aus.
- Release nur mit gruenem Gate-Report (kein Override fuer Critical/High).

## 12. Aktuelles Rest-Backlog und Reihenfolge

Das folgende Backlog ersetzt die urspruengliche Sprint-3-/Sprint-4-Einteilung und beschreibt den Stand nach dem Security-Review vom 2026-08-25.

### 12.1 P1: Production-Blocker
- AP-10a.1 (erledigt, 2026-08-31): Rohe Exception-Details aus `backend/src/ingest/runner.py` entfernt; feste Fehlertaxonomie (`_safe_detail`) mit Sanitization-Tests in `backend/tests/test_scheduled_runner.py` eingefuehrt. Siehe Abschnitt 20.2.
- AP-10a.2 (erledigt, 2026-08-31): Terraform-State-Exposition geprueft (kein Git-/GitHub-Vektor, siehe Abschnitt 20.3) und Remote-Backend (S3 + DynamoDB-Lock) als Code vorbereitet (`infra/aws/terraform/state_backend.tf`, `backend.tf`). Rotation der RDS-Credentials bewusst auf P2 verschoben (dokumentierte Ausnahme, kein Expositionsvektor).
- Abnahme: Keine sensiblen Werte oder rohen Exception-Texte in Standardlogs (erfuellt); State-Bootstrap-Code ist vorbereitet, der eigentliche Backend-Umzug (`terraform init -migrate-state`) steht als bewusst manuell freizugebender Schritt aus, da er den produktiven State-Speicherort aendert.

### 12.2 P2: Produktionshygiene
- AP-10a.3: Produktions-Secret-Modus strukturell erzwingen; ENV-Credentials duerfen nur in explizitem Development-Modus verwendet werden.
- AP-10a.4: Container-Images mit Commit-SHA oder Release-Tag statt `latest` deployen und Rollback ueber die immutable Referenz pruefen.
- AP-9.1 (erledigt, 2026-08-31): Drei aufeinanderfolgende Scheduler-Fenster mit `run_type=scheduled`, Exit-Code `0` und ohne Snapshot-Duplikate nachgewiesen; siehe Abschnitt 19 fuer die vollstaendige Evidenz.

### 12.3 P3: Härtung und Ausbau
- AP-10a.5: Fargate-Tasks in private Subnets mit kontrolliertem Egress betreiben und `assign_public_ip=false` nach Netzwerk-Smoke-Test aktivieren.
- AP-10b: CI-Gates fuer Tests, Terraform-Format/Validate/Plan, Secret-Scanning, Dependency-Scanning und Container-Scanning einrichten.
- AP-10/AP-11: Idempotenz-/Retry-Nachweise vervollstaendigen und danach die FastAPI-Endpunkte fuer Spieler, Teams, Historie und Transfermarkt umsetzen.

## 13. Security-Remediation-Sequenz (konsolidiert)

Diese Reihenfolge ist verbindlich vor dem regulaeren Produktionsbetrieb und dem weiteren Ausbau ab AP-10:
1. Credentials-Policy: Produktion nur Secrets Manager, kein ENV-Fallback.
2. DB-Transport-Policy: TLS `sslmode=require` oder staerker als Laufzeit-Gate.
3. Logging-Sanitization: keine rohen Exceptions, strukturierte `error_code`-Logs.
4. Snapshot-Input-Haertung: Allowlist-Verzeichnis, Groessenlimit, Schema-Pruefung.
5. Erst danach: Scheduler-Automatisierung und weitere Skalierungsfeatures.

### 13.1 Review-Status (2026-08-25, aktualisiert 2026-08-31)
- P1 erledigt (2026-08-31): `git ls-files`/`git log` bestaetigen, dass `terraform.tfstate`, `terraform.tfstate.backup` und `terraform.tfvars` nie in der Git-Historie waren (`.gitignore` schliesst sie seit Projektstart aus); ein Bereinigen der Historie ist damit nicht erforderlich. Remote-State-Bootstrap-Code ist vorbereitet (siehe Abschnitt 20.3); die Migration selbst (`terraform init -migrate-state`) steht als manuell freizugebender Schritt aus.
- P1 teilweise: DB-TLS, Snapshot-Input-Haertung und produktive Secrets-Manager-Nutzung sind im Live-Lauf nachgewiesen; die Secrets-Manager-Pflicht muss noch als dauerhaftes Deploy-Gate abgesichert werden.
- P2 erledigt (2026-08-31): Fehlerlogs sind vor der Ausgabe sanitiziert (`_safe_detail` in `runner.py`); Tests decken Connection Strings, Tokens, ARNs, Pfade und personenbezogene Daten ab (siehe Abschnitt 20.2).
- P3 geplant: RDS-Multi-AZ, laengere Backup-Retention, private Fargate-Netzwerkpfade und erweiterte State-Integritaetsalarme folgen nach den P1-Gates. RDS-Multi-AZ ist gemaess Abschnitt 20.4 bewusst auf spaeter verschoben (Kosten-Mandat).
- AP-9 umgesetzt: ECS-Task-Revision 3, EventBridge `ENABLED`, Cron `cron(0 6 * * ? *)` (06:00 UTC), zwei Retries, eine SQS-DLQ und Fargate `1.4.0` sind aktiv; der erste scheduled Smoke-Test schrieb 600 Datensaetze ohne Fehler.
- AP-9.1 Stabilitaetsnachweis (2026-08-31): Fuenf aufeinanderfolgende taegliche Scheduler-Fenster (2026-08-27 bis 2026-08-31, jeweils `run_type=scheduled`, `run_success`, Exit-Code `0`) belegen die geforderten drei aufeinanderfolgenden Zeitfenster. `market_values_count` waechst je Tag um genau 100 (702 -> 802 -> 902 -> 1002 -> 1102) ohne Duplikat- oder Constraint-Fehler in CloudWatch. Details in Abschnitt 19.
- Datenmodell-Entscheidung: Secret- und Terraform-State-Metadaten werden nicht in den fachlichen Tabellen persistiert; technische Audits verbleiben in AWS-Diensten.

### 13.2 Security-Review-Massnahmen (2026-08-25)
Grundlage ist der vollstaendige Review in `docs/code-review/2026-08-25-full-project-security-review.md`.

#### P1: Vor Production-Freigabe
- Logging-Sanitization in `backend/src/ingest/runner.py`: `detail=str(exc)` entfernen, feste Fehlertaxonomie verwenden und Tests fuer Tokens, Connection Strings, ARNs, Pfade und personenbezogene Daten ergaenzen. **Erledigt 2026-08-31**, siehe Abschnitt 20.2.
- Abnahmekriterium: Standardlogs enthalten keine rohen Exception-Texte oder sensiblen Werte; Security-Review H1 ist geschlossen. **Erfuellt.**

#### P2: Vor dem regulaeren Produktionsbetrieb
- Produktionskonfiguration strukturell gegen ENV-Credentials absichern; `COMUNIO_SECRET_NAME` und `COMUNIO_REQUIRE_SECRET_MODE=true` muessen als nicht umgehbares Gate gelten.
- Container-Images mit Commit-SHA oder Release-Tag statt `latest` deployen und die ECR-Tag-Strategie auf unveraenderliche Referenzen umstellen.
- Abnahmekriterium: ECS-Task-Definition enthaelt keine Credential-ENV-Werte und referenziert eine nachvollziehbare immutable Image-Version.

#### P3: Geplante Härtung
- Fargate-Tasks in private Subnets mit kontrolliertem Egress betreiben; `assign_public_ip=false` erst nach validiertem NAT-/VPC-Endpoint-Pfad aktivieren.
- CI-Security-Gates fuer Tests, Terraform-Format/Validate/Plan, Secret-Scanning, Dependency-Scanning und Container-Scanning einrichten.
- Abnahmekriterium: Keine offenen Critical/High Findings und reproduzierbarer Deploy-Block bei Gate-Verletzung.

## 14. Konsolidierte Trade-offs und offene Entscheidungen

### 14.1 Trade-offs
- Strikte Security-Gates verlangsamen kurzfristig Deployments, reduzieren aber Produktionsrisiko.
- Erweiterte Logging- und Audit-Anforderungen erhoehen Betriebsaufwand, verbessern Incident-Reaktion.
- Fruehe FinOps-Gates begrenzen Experimentierfreiheit, stabilisieren jedoch Kostenpfad.

### 14.2 Offene Entscheidungen
- Zielniveau fuer DB-TLS in Produktion (`require` Mindestniveau, `verify-full` Zielniveau) inkl. CA-Handling.
- Exakter Umfang der geschuetzten Debug-Logs fuer tiefe Störungsanalyse.

### 14.3 Kosten- und Betriebs-Trade-offs
- Remote S3-State mit Locking verursacht geringe laufende Kosten, reduziert aber State-Konflikte und Credential-Exposure deutlich.
- Automatische Secret-Rotation verbessert den Sicherheitsstatus, erfordert jedoch einen getesteten Rotationshandler und einen Reconnect-Nachweis.
- Multi-AZ, laengere Backups und private Fargate-Netzwerkpfade werden erst nach dem MVP-Reliability-Gate aktiviert, um die fruehe Betriebsphase budgetschonend zu halten.

## 15. Phase-1 Umsetzungscheckliste (konsolidiert aus 5 Agent-Beitraegen)

### 15.1 AP-1 Lastenheft-Review und Scope-Fixierung
- MUST/SHOULD/NICE-TO-HAVE schriftlich festlegen.
- Nicht-Ziele fuer Phase 1 explizit dokumentieren.
- Messbare NFR-Definitionen fuer Phase 1 festhalten.
- Stakeholder-Signoff fuer Scope bis Ende Woche 1.

### 15.2 AP-2 Architekturentscheidungen dokumentieren
- ADR-Set fuer Kernentscheidungen anlegen (Runtime, DB-Hosting, Secrets, CI/CD, Branching).
- Sicherheits-Baseline fuer Secrets, IAM, Netzwerk und Verschluesselung festlegen.
- Service-Mapping fuer AWS in der Architekturdoku konkretisieren.
- Offene Architekturentscheidungen mit Verantwortlichen und Due Date markieren.

### 15.3 AP-3 Datenmodell finalisieren
- Kern-Tabellen und Beziehungen fuer Phase 1 final freigeben.
- Idempotenz-Constraint und Index-Mindestset verbindlich machen.
- Migrations-Strategie festlegen (Tool + Benennung + Rollback-Prinzip).
- Data Dictionary fuer Kernfelder abschliessen.

### 15.4 AP-4 Dev-Umgebung und Delivery-Basis
- Repo-Struktur fuer backend, ingest, frontend, infrastructure und docs festlegen.
- Docker- und lokale Startkonventionen dokumentieren.
- CI-Baseline mit Lint, Tests und Dependency-Checks aktivieren.
- Branch-Schutz und PR-Regeln verbindlich konfigurieren.

## 16. Phase-1 Abnahme (Ende Woche 2)

### 16.1 Muss-Kriterien
- Lastenheft-Scope ist schriftlich freigegeben.
- Architekturentscheidungen sind als ADRs dokumentiert.
- Datenmodell fuer Phase 1 ist final und widerspruchsfrei.
- Dev-Setup ist reproduzierbar und vom Team erfolgreich durchlaufen.

### 16.2 KPI-Kriterien
- Setup-Zeit fuer neue Entwickler ist dokumentiert.
- Kritische Blocker aus Woche 1 sind geschlossen.
- CI-Baseline laeuft fuer Pull Requests stabil.

## 17. Phase-1 Trade-offs und offene Entscheidungen

### 17.1 Trade-offs
- Dokumentations- und Entscheidungsqualitaet wird vor Feature-Tempo priorisiert.
- Kern-Setup wird abgeschlossen, spaetere Funktionsumsetzung wird bewusst nicht vorgezogen.

### 17.2 Offene Entscheidungen
- Finale Produktions-Runtime fuer Ingest.
- Exakte Budgetgrenzen fuer Dev/Staging in der Fruehphase.

## 18. AP-9.2 Login-Retry und automatischer Erfolgs-/Fehler-Check (umgesetzt)

### 18.1 Ziel
Der Scheduler-Lauf soll selbststaendig erkennen, ob er erfolgreich war oder an einem Login-Problem gescheitert ist. Bei Login-Fehlern wird der Lauf automatisch erneut versucht, statt sofort als fehlgeschlagen zu enden.

### 18.2 Umsetzung
- `backend/src/ingest/runner.py`: neue Funktion `_login_with_retry` fuehrt bis zu `COMUNIO_LOGIN_RETRY_ATTEMPTS` (Default 3) Login-Versuche im Abstand von `COMUNIO_LOGIN_RETRY_WAIT_SECONDS` (Default 300 Sekunden, 5 Minuten) durch.
- `backend/src/config.py`: neue Settings-Felder `login_retry_attempts` und `login_retry_wait_seconds` mit Validierung (positive Ganzzahlen).
- Nach erschoepften Versuchen wird der Lauf mit `run_failed`, `stage=login` beendet; der Prozess terminiert mit Exit-Code 1, genau wie ein erfolgreicher Lauf mit Exit-Code 0 den Prozess regulaer beendet. Da der Ingest-Task ein einmaliger ECS-Fargate-Task ist (kein Dauerservice), stoppt ECS den Container in beiden Faellen identisch; es ist kein zusaetzlicher Shutdown-Mechanismus noetig.
- `infra/aws/terraform/main.tf`: neue Terraform-Variablen `login_retry_attempts` und `login_retry_wait_seconds` werden als Container-ENV durchgereicht. Ein neuer CloudWatch Logs Metric Filter (`login-retries-exhausted`) auf das Muster `event=run_failed stage=login` speist einen CloudWatch Alarm; optionale Benachrichtigung ueber `alert_sns_topic_arn`.

### 18.3 Tests
- `backend/tests/test_scheduled_runner.py` deckt ab:
  - Erfolgreicher Login nach transienten Fehlern (`login_recovered`).
  - Alle Versuche fehlgeschlagen (`login_attempt_failed` dreimal, korrekte Wartezeiten).
  - End-to-End: `runner.main()` liefert Exit-Code 1 und loggt `run_failed stage=login` nach erschoepften Retries.
- `terraform validate` und `terraform fmt -check` sind fuer die Infrastrukturaenderung gruen.

### 18.4 Priorisierung
- P1: Login-Retry-Logik im Runner (dieser Abschnitt, umgesetzt).
- P2: CloudWatch-Alarm auf erschoepfte Login-Retries (umgesetzt, Benachrichtigung optional).
- P3: Verbindliche SNS-Anbindung fuer den Alarm, sobald das Betriebsteam einen Ziel-Topic bestaetigt.

### 18.5 Trade-offs
- Ein Lauf mit drei fehlgeschlagenen Login-Versuchen kann bis zu 10 Minuten laenger laufen (zwei Wartezeiten je 5 Minuten). Dies wird akzeptiert, da Login-Probleme typischerweise transient sind und die Snapshot-Verarbeitung ohnehin erst nach erfolgreichem Login beginnt.
- Bewusst keine Step-Functions-Orchestrierung: Die intra-Prozess-Loesung vermeidet zusaetzliche AWS-Ressourcen und laufende Kosten und passt sich in den bestehenden Retry-Stil (Snapshot-Backoff) ein.

## 19. AP-9.1 Stabilitaetsnachweis: drei aufeinanderfolgende Scheduler-Fenster (erledigt, 2026-08-31)

### 19.1 Pruefergebnis
Die Verifikation ueber `aws events describe-rule`, `aws ecs list-tasks`/`describe-tasks` und `aws logs tail /ecs/comunio-prod-ingest` (Region `eu-central-1`) am 2026-08-31 bestaetigt das Akzeptanzkriterium aus Abschnitt 3, Punkt 4 sowie AP-9.1 (Abschnitt 12.2) und die AP-9-Acceptance-Kriterien in `backend/OPERABILITY-AP9.md`. Die EventBridge-Rule `comunio-prod-snapshot-schedule` ist `ENABLED` mit `cron(0 6 * * ? *)` (06:00 UTC).

### 19.2 Chronologische Scheduler-Runs (CloudWatch, `/ecs/comunio-prod-ingest`)
| Datum (UTC) | Ereignis | run_id | Ergebnis | market_values_count |
|---|---|---|---|---|
| 2026-08-25 19:39 | `run_type=scheduled` | 10 | `run_success` | 501 |
| 2026-08-26 06:00 | `run_type=scheduled` | - | `run_failed stage=login` (Comunio "Plus/Pro"-Sperre, vor Deployment der Login-Retry-Logik) | - |
| 2026-08-26 13:05 | `run_type=scheduled` | 11 | `run_success` | 601 |
| 2026-08-27 06:00 | `run_type=scheduled` | 13 | `run_success` (nach `login_attempt_failed` + `login_recovered` bei Versuch 2) | 702 |
| 2026-08-28 06:00 | `run_type=scheduled` | 14 | `run_success` (nach `login_recovered` bei Versuch 2) | 802 |
| 2026-08-29 06:00 | `run_type=scheduled` | 15 | `run_success` (Login sofort erfolgreich) | 902 |
| 2026-08-30 06:00 | `run_type=scheduled` | 16 | `run_success` (nach `login_recovered` bei Versuch 2) | 1002 |
| 2026-08-31 06:00 | `run_type=scheduled` | 17 | `run_success` (nach `login_recovered` bei Versuch 2) | 1102 |

### 19.3 Bewertung
- Fuenf aufeinanderfolgende taegliche Zeitfenster (2026-08-27 bis 2026-08-31) erfuellen `run_type=scheduled` mit `run_success` und uebertreffen damit die geforderten drei aufeinanderfolgenden Fenster.
- `market_values_count` steigt exakt um 100 pro Tag (702 -> 802 -> 902 -> 1002 -> 1102), was zur erwarteten Snapshot-Groesse passt; es liegen keine Duplikat-, Unique-Constraint- oder IntegrityError-Meldungen in den CloudWatch-Logs vor.
- Der einzelne fehlgeschlagene Lauf am 2026-08-26 06:00 lag vor der Aktivierung von AP-9.2 (Login-Retry, deployed am 2026-08-26) und ist damit kein Verstoss gegen den nachtraeglich gehaerteten Betrieb; alle Laeufe ab 2026-08-27 nutzen die Retry-Logik und enden erfolgreich.
- Damit gelten Abschnitt 3 Punkt 4, AP-9.1 (Abschnitt 12.2) sowie das entsprechende Akzeptanzkriterium in `backend/OPERABILITY-AP9.md` als erfuellt.

### 19.4 Naechster Schritt
- AP-10/AP-11 gemaess Abschnitt 9 und 12.3 fortsetzen: Idempotenz-/Retry-Nachweise vervollstaendigen und danach die FastAPI-Endpunkte umsetzen.

## 20. AP-10a: Konsolidierte Agent-Beiträge und Hardening-Roadmap (2026-08-31)

Folgende Abschnitte dokumentieren die Ergebnisse einer konzertierten Multi-Agent-Analyse (AWS Cloud Expert, AWS Principal Architect, Principal Software Engineer, Project Architecture Planner, Software Engineer Agent v1) zur Komplettierung der AP-10a Security-Baseline.

### 20.1 AWS Cloud Expert (Secrets Mgmt + Terraform State)

**P1 — Remote State-Backend (S3 + DynamoDB) sofort implementieren.**
Lokales `terraform.tfstate` ohne Locking und Durability stellt ein Reliability-Risiko dar (concurrent-apply-Korruption möglich). `infra/aws/terraform/state_backend.tf` und `infra/aws/terraform/backend.tf` wurden codiert (noch nicht aktiviert — erfordert manuelle `terraform init -migrate-state`, um den produktiven State-Speicherort zu ändern).

**P2 — Secrets-Manager-Durchsatz als hartes Deployment-Gate.**
`COMUNIO_REQUIRE_SECRET_MODE` muss in `prod`-Umgebungen auf `true` erzwungen werden; ENV-Fallback darf nicht zulässig sein. Terraform-Validierung soll dies `precondition` auf der ECS-Task-Definition durchsetzen.

**P3 — Automatische RDS-Credential-Rotation (später).**
Ein Lambda-Rotation-Handler für Secrets Manager wird nach der State-Migration als P3 implementiert.

**Trade-offs:** S3+DynamoDB kostet cents/mo, bringt aber State-Locking und Versioning. Terraform Cloud wäre vendor-agnostic, führt aber eine zweite Plattform-Abhängigkeit ein — für dieses AWS-only-Projekt nicht optimal.

### 20.2 Principal Software Engineer (Log-Sanitization)

**P1 — Exception-Text aus Logs entfernen (ERLEDIGT).**
`backend/src/ingest/runner.py`: neue Funktion `_safe_detail(stage)` ersetzt alle `detail=str(exc)` durch eine feste Taxonomie (`authentication_failed`, `snapshot_fetch_failed`, `database_persistence_failed`, `unexpected_error`). Roh-Exception-Text (Comunio HTTP-Responses, psycopg DSN-Details, etc.) wird nie ausgegeben.

**Tests hinzugefügt:** `backend/tests/test_scheduled_runner.py` enthält nun `test_run_failed_login_sanitizes_sensitive_exception_text()` und `test_safe_detail_falls_back_for_unmapped_stage()`. Sie prüfen explizit, dass Postgres-DSN, Bearer-Tokens, AWS-ARNs, Dateipfade und E-Mails **nicht** in stdout-Logs erscheinen — nur der sichere Replacements-Text.

**All 13 backend tests pass.**

**Trade-off:** Verlust von granularem Debug-Text für CloudWatch-Incident-Debugging; Mitigation ist eine optionale, intern-only zugängliche Debug-Trace-API später.

### 20.3 AWS Principal Architect (Well-Architected / Governance)

**P1 — State-Locking als Reliability-Gate.**
Lokale State ohne DynamoDB-Lock erlaubt concurrent-apply-Korruption → Datenbank-Duplikate, orphaned Ressourcen. S3-Backend + Lock-Tabelle ist mandatory vor Team-Onboarding oder CI/CD-Automatisierung.

**Terraform-State Exposure-Analyse:** `git ls-files` und `git log` bestätigen, dass `terraform.tfstate*` und `terraform.tfvars` **nie** in Git-Historie waren (`.gitignore` schließt sie seit Projektstart aus). **Kein GitHub-Expositions-Vektor.**

**Rotationsentscheidung:** RDS-Master-Password-Rotation wird auf P2 verschoben (dokumentierte Ausnahme). Begründung: kein Git/GitHub-Vektor, State lag nur auf Einzelarbeitsplatz. Runbook wird vorbereitet; Rotation folgt opportunistisch nach State-Backend-Aktivierung oder bei Team-Onboarding.

**P2 — RDS Multi-AZ: explizit auf später verschieben (Budget-Constraint).**
Multi-AZ verdoppelt RDS-Compute-Kosten für ein Hobby-Projekt mit no-SLA → Konflikt mit „Infrastruktur-Kosten so niedrig wie möglich". Single-AZ + Snapshots ist ausreichend; Upgrade bei SLA-Anforderung.

**P2 — Dedicated terraform-deploy IAM-Role vorbereiten (nicht sofort aktivieren).**
Separierung von „wer kann Infra deployen" (terraform role) von „wer liest Secrets zur Laufzeit" ist Principle-of-Least-Privilege-Best-Practice. Heute noch optional (single engineer), wird bei Team-Wachstum Pflicht.

### 20.4 Project Architecture Planner (Cost / Scalability)

**Cost-Analyse AP-10a:**
- S3+DynamoDB remote state: ~$0.01–0.05/Monat (praktisch $0).
- Logging-Sanitization: $0 (Code-only).
- RDS Multi-AZ heute: +~$50–150/Monat (abgelehnt, deferred).
- Terraform Cloud Free Tier: $0, aber zusätzliche Vendor-Abhängigkeit (nicht empfohlen für AWS-only-Projekt).

**Recommendation:** S3+DynamoDB ist kosteffizient, bleibt in AWS-Ökosystem und vermeidet Vendor Lock-in zu Terraform Cloud. Single-AZ RDS bleibt auf P3 (keine Kosten-Bedrohung heute).

**Skalierungs-Roadmap nach AP-10a:**
- **Phase A (jetzt):** Single-AZ Ingest, single Fargate task daily, Local/S3 state, no API yet.
- **Phase B (Q4):** API Layer (FastAPI) mit read-only Endpoints, Query Caching, rate-limiting.
- **Phase C (Q1 2027):** Multi-AZ Ingest, RDS replicas, CDN für Frontend, Event-driven backpressure (SQS DLQ → Lambda retry).

### 20.5 Software Engineer Agent v1 (Execution Summary)

**Codierung abgeschlossen:**
1. ✅ `backend/src/ingest/runner.py`: `_safe_detail()` Funktion + 3 Call-site Patches.
2. ✅ `backend/tests/test_scheduled_runner.py`: Sanitization-Tests (sensible Substrings abgedeckt).
3. ✅ `infra/aws/terraform/state_backend.tf`: S3-Bucket (versioned, AES256, public-access-blocked, 90d lifecycle) + DynamoDB lock table.
4. ✅ `infra/aws/terraform/backend.tf`: Auskommentierter `backend "s3"` Block (Runbook-triggert Aktivierung).
5. ✅ `architecture.md` §5.1/§5.2: Logging-Gate dokumentiert, State-Exposure-Analyse eingefügt.
6. ✅ `infra/aws/README.md`: Remote-State-Migrationsprozess dokumentiert.
7. ✅ `terraform validate`: Erfolgreich, keine Fehler.

**Validation:**
- `pytest backend/tests/ -q` → 13 passed.
- `terraform validate` → Success.

**Nächste Schritte (manuelle Freigabe erforderlich):**
- `terraform init -migrate-state` (production state-Speicherort ändert sich → erfordert bewusste Freigabe vor Ausführung, nicht automatisiert).

### 20.6 Offene Entscheidungen und Blocker

| Entscheidung | Status | Aktion | Deadline |
|---|---|---|---|
| Remote Terraform-State aktivieren (`terraform init -migrate-state`) | **Cooked, awaiting approval** | Manuelle Freigabe vor Execution; siehe Runbook in `infra/aws/README.md` + `state_backend.tf` | Nach nächster Team-Review |
| RDS-Master-Password rotieren | **Deferred, documented** | Runbook vorbereitet; Rotation opportunistisch oder beim Team-Onboarding | Nach State-Backend-Aktivierung |
| RDS Multi-AZ aktivieren | **Deferred (cost mandate)** | Explizit auf Q1 2027 verschoben (Infrastruktur-Budget-Constraint) | Q1 2027 |
| Secrets-Manager-Pflicht in Prod durchsetzen | **P1 pending** | Terraform `precondition` hinzufügen auf ECS-Task-Definition, das `require_secret_mode=true` erzwingt | Vor nächstem Prod-Deploy |
| Dedicated terraform-deploy IAM-Role | **P2 pending** | Design vorbereitet, Aktivierung bei Team-Onboarding | Q4 2026 |

### 20.7 Zusammenfassung: AP-10a abgeschlossen, nächste Phase vorbereitet

**Erledigt:**
- ✅ Log-Sanitization (P1): Rohe Exception-Details entfernt, Tests bestanden.
- ✅ State-Exposure-Analyse (P1): Kein Git-Vektor, Bootstrap-Code ready, Aktivierung deferred.
- ✅ Security-Gates S1–S4 dokumentiert und teilweise durchgesetzt (S2/S4 live, S1/S3 in Terraform pending).

**Noch zu tun (P1-Gated vor Production):**
- Remote State aktivieren (manuelle Freigabe).
- Secrets-Manager-Pflicht in Terraform durchsetzen.

**P2–P3 (nach AP-10a, vor API-Launch):**
- AP-10b: CI-Gates (Tests, Terraform fmt/validate, Secret-Scanning).
- AP-10c: Container-Image-Tagging (immutable ref statt `latest`).
- AP-11: API-Grundlage (FastAPI, Endpoints für Spieler/Teams/Historie).


