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
- AP-9 Scheduler fuer taegliche Runs mit AWS Tools (implementiert und aktiviert; Stabilitaetsnachweis ueber drei Zeitfenster ausstehend)
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
4. AP-9 ist als EventBridge-Scheduler aktiv; drei aufeinanderfolgende Zeitfenster mit erfolgreichem `run_type=scheduled` und ohne Duplikate nachweisen.
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
- AP-10a.1: Rohe Exception-Details aus `backend/src/ingest/runner.py` entfernen und eine feste Fehlertaxonomie mit Sanitization-Tests einfuehren.
- AP-10a.2: Terraform-State sicher verwalten, lokale State-/Variablendateien aus dem Deploymentprozess ausschliessen und betroffene Credentials rotieren, falls sie ausserhalb des geschuetzten Kontexts exponiert waren.
- Abnahme: Keine sensiblen Werte oder rohen Exception-Texte in Standardlogs; State und Credentials sind nicht Bestandteil von Git-Artefakten.

### 12.2 P2: Produktionshygiene
- AP-10a.3: Produktions-Secret-Modus strukturell erzwingen; ENV-Credentials duerfen nur in explizitem Development-Modus verwendet werden.
- AP-10a.4: Container-Images mit Commit-SHA oder Release-Tag statt `latest` deployen und Rollback ueber die immutable Referenz pruefen.
- AP-9.1: Drei aufeinanderfolgende Scheduler-Fenster mit `run_type=scheduled`, Exit-Code `0` und ohne Snapshot-Duplikate nachweisen.

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

### 13.1 Review-Status (2026-08-25)
- P1 offen: `terraform.tfstate`, `terraform.tfstate.backup` und produktive Variablendateien muessen aus Git entfernt beziehungsweise aus der Historie bereinigt werden; danach sind betroffene Credentials zu rotieren.
- P1 teilweise: DB-TLS, Snapshot-Input-Haertung und produktive Secrets-Manager-Nutzung sind im Live-Lauf nachgewiesen; die Secrets-Manager-Pflicht muss noch als dauerhaftes Deploy-Gate abgesichert werden.
- P2 offen: Fehlerlogs muessen vor der Ausgabe sanitiziert werden; Tests muessen Connection Strings, Tokens, ARNs, Pfade und personenbezogene Daten abdecken.
- P3 geplant: RDS-Multi-AZ, laengere Backup-Retention, private Fargate-Netzwerkpfade und erweiterte State-Integritaetsalarme folgen nach den P1-Gates.
- AP-9 umgesetzt: ECS-Task-Revision 3, EventBridge `ENABLED`, Cron `cron(0 6 * * ? *)` (06:00 UTC), zwei Retries, eine SQS-DLQ und Fargate `1.4.0` sind aktiv; der erste scheduled Smoke-Test schrieb 600 Datensaetze ohne Fehler.
- Datenmodell-Entscheidung: Secret- und Terraform-State-Metadaten werden nicht in den fachlichen Tabellen persistiert; technische Audits verbleiben in AWS-Diensten.

### 13.2 Security-Review-Massnahmen (2026-08-25)
Grundlage ist der vollstaendige Review in `docs/code-review/2026-08-25-full-project-security-review.md`.

#### P1: Vor Production-Freigabe
- Logging-Sanitization in `backend/src/ingest/runner.py`: `detail=str(exc)` entfernen, feste Fehlertaxonomie verwenden und Tests fuer Tokens, Connection Strings, ARNs, Pfade und personenbezogene Daten ergaenzen.
- Abnahmekriterium: Standardlogs enthalten keine rohen Exception-Texte oder sensiblen Werte; Security-Review H1 ist geschlossen.

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

