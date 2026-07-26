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

Ergebnis:
- Manueller Abruf funktioniert reproduzierbar
- Erste valide Datensaetze in DB

### Phase 3: Automatisierung und Backend-API (Woche 6 bis 10)
Ziele:
- Taeglicher Abruf und API als Zugriffsschicht

Arbeitspakete:
- AP-9 Scheduler fuer taegliche Runs
- AP-10 Idempotenz-Regeln und Retry-Strategien
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
1. Architektur und Datenmodell intern freigeben.
2. AP-5 bis AP-8 als erstes Sprint-Backlog schneiden.
3. Technisches Kickoff mit Backend, Frontend, DevOps und Security durchfuehren.
4. Erfolgskriterien fuer M1 schriftlich abnehmen.

## 10. Technische Entscheidungen vor Start Phase 2

Diese Entscheidungen sind als Blocker zuerst verbindlich zu treffen:

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

### M3 (Woche 17)
- Frontend-Hauptseiten erreichen Ladezeit unter 2 Sekunden.
- Kern-User-Flows funktionieren auf Desktop und Mobile.
- E2E-Tests fuer zentrale Flows sind vorhanden.

### M4 (Woche 22)
- Security-Scan ohne offene High/Critical Findings.
- Backup/Restore-Test erfolgreich.
- CI/CD fuehrt Build, Tests und Deployments reproduzierbar aus.

## 12. Sprint-Backlog fuer die naechsten 2 Sprints

### Sprint 1 (Woche 1 bis 2)
Ziel: Architektur- und Delivery-Basis ohne Blocker herstellen.

- Story 1: Technische Entscheidungen finalisieren und als ADRs dokumentieren.
- Story 2: Lokale Dev-Umgebung mit Docker Compose fuer DB, Backend und Frontend bereitstellen.
- Story 3: Migration-Framework und Initialschema inkl. Constraints und Indizes aufsetzen.
- Story 4: CI-Baseline mit Linting, Dependency-Check und Branch-Schutz aktivieren.
- Story 5: ComunioPy-Research-Spike mit dokumentiertem Datenmapping abschliessen.

## 13. Phase-1 Umsetzungscheckliste (konsolidiert aus 5 Agent-Beitraegen)

### 13.1 AP-1 Lastenheft-Review und Scope-Fixierung
- MUST/SHOULD/NICE-TO-HAVE schriftlich festlegen.
- Nicht-Ziele fuer Phase 1 explizit dokumentieren.
- Messbare NFR-Definitionen fuer Phase 1 festhalten.
- Stakeholder-Signoff fuer Scope bis Ende Woche 1.

### 13.2 AP-2 Architekturentscheidungen dokumentieren
- ADR-Set fuer Kernentscheidungen anlegen (Runtime, DB-Hosting, Secrets, CI/CD, Branching).
- Sicherheits-Baseline fuer Secrets, IAM, Netzwerk und Verschluesselung festlegen.
- Service-Mapping fuer AWS in der Architekturdoku konkretisieren.
- Offene Architekturentscheidungen mit Verantwortlichen und Due Date markieren.

### 13.3 AP-3 Datenmodell finalisieren
- Kern-Tabellen und Beziehungen fuer Phase 1 final freigeben.
- Idempotenz-Constraint und Index-Mindestset verbindlich machen.
- Migrations-Strategie festlegen (Tool + Benennung + Rollback-Prinzip).
- Data Dictionary fuer Kernfelder abschliessen.

### 13.4 AP-4 Dev-Umgebung und Delivery-Basis
- Repo-Struktur fuer backend, ingest, frontend, infrastructure und docs festlegen.
- Docker- und lokale Startkonventionen dokumentieren.
- CI-Baseline mit Lint, Tests und Dependency-Checks aktivieren.
- Branch-Schutz und PR-Regeln verbindlich konfigurieren.

## 14. Phase-1 Abnahme (Ende Woche 2)

### 14.1 Muss-Kriterien
- Lastenheft-Scope ist schriftlich freigegeben.
- Architekturentscheidungen sind als ADRs dokumentiert.
- Datenmodell fuer Phase 1 ist final und widerspruchsfrei.
- Dev-Setup ist reproduzierbar und vom Team erfolgreich durchlaufen.

### 14.2 KPI-Kriterien
- Setup-Zeit fuer neue Entwickler ist dokumentiert.
- Kritische Blocker aus Woche 1 sind geschlossen.
- CI-Baseline laeuft fuer Pull Requests stabil.

## 15. Phase-1 Trade-offs und offene Entscheidungen

### 15.1 Trade-offs
- Dokumentations- und Entscheidungsqualitaet wird vor Feature-Tempo priorisiert.
- Kern-Setup wird abgeschlossen, spaetere Funktionsumsetzung wird bewusst nicht vorgezogen.

### 15.2 Offene Entscheidungen
- Finale Produktions-Runtime fuer Ingest.
- Exakte Budgetgrenzen fuer Dev/Staging in der Fruehphase.
- Mindestumfang der Security-Controls vor Start von Phase 2.
