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
- AP-11 FastAPI-Zugriffsschicht: API-Vertrag, FastAPI-App, Read-Repositories, Spieler/Teams/Historie/Transfermarkt und API-Tests
- AP-12 Delta-Berechnungen in API: SQL-Projektion, additive Schemas und Randfalltests
- AP-13 Integrations-, Contract-, Fehlerpfad- und Performance-Nachweise

Ergebnis:

- Taegliche Updates stabil
- Saubere API-Endpunkte fuer Frontend und Integrationen

### Phase 4: Frontend MVP und Ausbau (Woche 11 bis 17)

Ziele:

- Minimal-Frontend und danach Komfort-Ausbau

Stand 2026-09-20: Das Frontend-v1 ist unter `frontend/` implementiert und in CI mit `npm ci`, `npm audit --audit-level=moderate`, Tests, ESLint und Production-Build abgesichert. Vercel-Konfiguration und serverseitiger Next.js-Proxy sind vorbereitet; AP-13.a (Secret-Validierung in der FastAPI) bleibt vor dem Produktions-Livegang erforderlich.

Arbeitspakete:

- AP-14 Basis-Dashboard (Uebersicht, Team, Spieler) mit serverseitigem API-Proxy/BFF
- AP-15 Marktwert-Historie und Ranking-Ansichten
- AP-16 Transfermarkt-Uebersicht
- AP-17 UX-Verbesserungen, Filter, Sortierung
- AP-18 Frontend-Tests und Monitoring-Einbindung

Zugriffsmodell fuer das Frontend:

- Browser rufen nur die Frontend-Routen auf; der serverseitige Proxy ruft die FastAPI auf.
- Der Proxy authentifiziert sich gegen die API mit einem Secret aus den Hosting-Umgebungsvariablen.
- Das Secret darf niemals in Client-JavaScript, HTML oder oeffentlichen Repositories auftauchen.
- Direkte API-Aufrufe ohne Proxy-Authentifizierung werden mit `401` abgewiesen.
- Der Proxy uebernimmt Timeout, Fehlerweitergabe, Rate-Limit-Budget und spaeter optionales Caching.
- In der Uebergangsphase bleibt der API-ALB oeffentlich; als Folge-Haertung werden interne API-Subnets oder ein privater ALB vorgesehen.

Ergebnis:

- Nutzbare Web-App mit Kernfunktionalitaet
- Gute Nutzbarkeit fuer taegliche Anwendung
- Kein API-Secret im Browser und kein ungeschuetzter direkter Frontend-Zugriff auf die API

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

1. Risiko: Performanceprobleme bei wachsender Datenmenge
   Massnahme: Indexstrategie, Query-Tuning, Caching, Lasttests vor Go-Live.

1. Risiko: Sicherheitsluecken durch schnelle Iteration
   Massnahme: Security-Checks in CI, Dependency-Scanning, Threat-Model-Review pro Release.

1. Risiko: Zeitplanabweichungen
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

Der aktuelle Stand liegt innerhalb von Phase 3:

- AP-5 bis AP-10 sind auf Code-, Test- und Dokumentationsebene umgesetzt.
- AP-9 laeuft als EventBridge-Scheduler; fuenf aufeinanderfolgende erfolgreiche Tagesfenster sind nachgewiesen.
- AP-10 ist mit `v0.4.4` veroeffentlicht; AP-11-DEV ist fuer `v0.5.0` umgesetzt, Backend-Tests sowie Terraform-Formatierung und -Validierung sind gruen.
- AP-11-PROD ist als kostenorientierter HTTP-MVP ausgerollt: ECS-Service hinter oeffentlichem ALB, `assign_public_ip=true`, Vercel-CORS und separater Read-only-DB-User/Secret. HTTPS/ACM, WAF und private API-Subnets bleiben spaetere Haertung.
- Das oeffentliche API-ALB ist bis zur Frontend-Integration ein bewusst befristeter MVP-Zustand. Das Zielmodell ist ein serverseitiger Frontend-Proxy mit API-Authentifizierung; CORS allein gilt nicht als Zugriffsschutz.

Naechste Schritte in verbindlicher Reihenfolge:

1. AP-12 ist umgesetzt; die PostgreSQL- und Vertragsintegration wird in AP-13 als Regression abgesichert.
1. AP-13 ist implementiert: PostgreSQL-16-Integrationstests, OpenAPI-Contract-Test, Fehlerpfadtests, reproduzierbares Benchmark-Skript und kostenguenstige native ALB-CloudWatch-Alarme sind vorhanden. Eine AWS-Staging-Baseline bleibt optional.
1. Optionales Hardening nach dem MVP: AP-10a.5 mit NAT-/ECR-Endpoint-Pfad, privatem ECS-Task ohne Public IP und DB-Reconnect-Nachweis.
1. AP-13.a als Zwischenpaket fuer serverseitigen Frontend-Proxy und API-Authentifizierung umsetzen; danach mit AP-14 in das Frontend integrieren und optional AP-11-PROD weiter haerten: HTTPS/ACM, WAF und private API-Subnets.

### AP-12 Implementierungsumfang und Definition of Done

AP-12 wird als read-only-Projektion in der bestehenden API umgesetzt:

- `get_player_history()` berechnet Referenzwerte mit PostgreSQL-Fensterfunktionen aus `market_values`; Deltas werden nicht gespeichert.
- `snapshot_date` ist die fachliche Zeitachse. `previous_*` bezieht sich auf den exakten Kalendertag davor, nicht auf `captured_at` oder den naechsten vorhandenen Snapshot.
- Der Erstwert wird ueber die gesamte Spielerhistorie bestimmt, bevor `from_date`, `to_date` und `limit` angewendet werden.
- Die History-Response erhaelt additive Felder fuer vorheriges Datum/Wert, Erstwertdatum/-wert, absolute Deltas und Prozentdeltas.
- Fehlende Kalendertage liefern `NULL` fuer die Vortagsreferenz und deren Deltas. Beim ersten vorhandenen Snapshot ist `delta_first_eur=0`; bei Referenzwert `0` bleibt der Prozentwert `NULL`.
- Negative absolute und prozentuale Deltas werden als gueltige Fachwerte ausgeliefert.
- AP-10a.5 bleibt davon unabhaengig und ist weiterhin optionale Netzwerk-Haertung nach dem MVP.

Definition of Done:

- API-Schema und OpenAPI enthalten alle AP-12-Felder mit korrekten nullable Typen.
- Tests decken positiven Wertanstieg, Wertverlust, ersten Snapshot, fehlenden Kalendervortag, Erstwert ueber Zeitraumfilter und Referenzwert `0` ab.
- Bestehendes 404/400/422/503-Verhalten, Sortierung und Limitierung bleiben unveraendert.
- Keine neue Tabelle, Migration, Schreibberechtigung oder AWS-Ressource ist fuer AP-12 erforderlich.
- AP-13 misst anschliessend P95, DB-Laufzeit und Query-Plan; Caching oder materialisierte Projektionen werden erst nach Messung entschieden.

### AP-13 Implementierungsumfang und Definition of Done

AP-13 ist in vier Nachweise gegliedert:

- **AP-13.1 PostgreSQL-Integration:** PostgreSQL 16 als CI-Service, sequenzielle Migrationen, idempotente Wiederholung, deterministische Fixtures und echte Repository-/API-Aufrufe.
- **AP-13.2 OpenAPI-Contract:** Laufzeitpruefung von `/api/v1`, ausschliesslichen GET-Methoden, Pagination-Grenzen, AP-12-Nullable-Feldern und dokumentierten History-Fehlerantworten.
- **AP-13.3 Fehlerpfade:** 400 bei ungueltigem Datumsbereich, 404 bei unbekannten Ressourcen, 422 bei ungueltigen Parametern, 503 bei Datenbankproblemen und keine sensiblen Fehlerdetails.
- **AP-13.4 Performance:** `backend/scripts/benchmark_api.py` misst Repository-/DB-P50, P95, P99 und Maximalzeit fuer History, Spieler, Teams und Transfermarkt. Eine AWS-Staging-Baseline mit ECS/ALB/RDS bleibt ein separater releasebezogener Nachweis.

Definition of Done:

- Migrationen laufen gegen eine leere PostgreSQL-16-Datenbank und sind wiederholbar.
- AP-12-Faelle fuer positive, negative, erste, fehlende und Null-Referenzwerte laufen gegen echte SQL-Daten.
- OpenAPI enthaelt den versionierten Read-only-Vertrag und alle AP-12-Felder mit korrekten nullable Typen.
- 400-, 404-, 422- und 503-Verhalten ist automatisiert geprueft; SQL-, DSN-, Secret- und Stacktrace-Details werden nicht ausgegeben.
- Benchmark-Artefakte enthalten Datenbankziel, Iterationszahl und P50/P95/P99-Werte; Produktions-P95 wird nicht aus lokalen CI-Zeiten abgeleitet.
- Caching, Redis, Read Replica, Partitionierung und materialisierte Projektionen werden erst nach Query-Plan- und P95-Nachweis entschieden.
- AP-10a.5 bleibt optionale Netzwerk-Haertung und ist kein AP-13-Abnahmekriterium.
- Die API-Observability verwendet native ALB-Metriken statt Custom Metrics: P95-Alarm mit 0,5 Sekunden, 5xx-Rate mit 5 Prozent und 4xx-Rate mit 25 Prozent als konfigurierbare Terraform-Defaults. Alarme werden nur mit `api_enabled=true` angelegt.
- CloudWatch-Alarme nutzen 5-Minuten-Perioden und keine zusaetzliche Staging-Infrastruktur. Ein SNS-Topic bleibt optional; dadurch bleibt der MVP-Kostenpfad niedrig.
- Die AWS-Staging-Baseline wird erst vor einem groesseren Release oder bei Skalierungsbedarf aktiviert, weil sie zusaetzliche ECS-, ALB- und RDS-Kosten erzeugt.

### AP-13.a Zugriffsschutz und serverseitiger Frontend-Proxy

AP-13.a wird nach dem abgeschlossenen API-MVP und vor der Frontend-Produktivnutzung umgesetzt:

- Serverseitiger Frontend-Proxy/BFF als einziger geplanter Zugriffspfad des Browsers.
- Separates Proxy-Secret in den Server-Umgebungsvariablen; kein Secret in Client-JavaScript, HTML oder Repositorys.
- FastAPI weist direkte Requests ohne gueltige Proxy-Authentifizierung mit `401` ab.
- `/docs` und vergleichbare Diagnose-Endpunkte werden in Production deaktiviert oder geschuetzt.
- Das aktuelle oeffentliche ALB bleibt bis zur Umsetzung von AP-13.a ein bewusst befristeter MVP-Zustand.
- Als Folgeausbau werden interner ALB, private API-Subnets, kontrollierter Egress und optional WAF bewertet.

Definition of Done:

- Browserzugriff auf die AWS-API ohne gueltige Authentifizierung ist nicht moeglich.
- Der Proxy-Token ist in keiner Browserantwort und keinem gebauten Client-Bundle enthalten.
- Proxy-, API- und Fehlerpfadtests decken `401`, Timeout, Weitergabe von `4xx`/`5xx` und CORS-Verhalten ab.
- Eine Kostenentscheidung fuer Vercel-Proxy, ECS-Proxy oder privaten AWS-Pfad ist dokumentiert.

### AP-11 Umsetzungsumfang und Definition of Done

AP-11 wird in folgende Teilaufgaben zerlegt:

- AP-11.1 API-Vertrag: `/api/v1`, Endpunkte, Fehlerformat, Pagination und OpenAPI-Schema.
- AP-11.2 FastAPI-App: App Factory, Dependency-Lifecycle sowie `/health/live` und `/health/ready`.
- AP-11.3 Read-Schicht: getrennte Repository-/Service-Funktionen fuer parametrisierte PostgreSQL-Abfragen.
- AP-11.4 Kernressourcen: Spieler, Teams und Marktwerthistorie mit typisierten Pydantic-Responses.
- AP-11.5 Transfermarkt: read-only Route; bis zur Ingest-Erweiterung ist eine leere, valide Antwort zulaessig.
- AP-11.6 Qualität: HTTP-, Mapping-, Fehler- und Pagination-Tests in CI.
- AP-11.7 Production: eigener API-Container beziehungsweise ECS-Service, ALB, Vercel-CORS-Allowlist, separater Read-only-DB-User/Secret, Health-Checks und Rollback. Fuer das MVP verifiziert; WAF, HTTPS/ACM und private Tasks sind spaetere Haertung.

AP-11 gilt technisch als erledigt, wenn alle vereinbarten read-only-Endpunkte versioniert und typisiert sind, keine ungebundenen SQL-Werte oder unlimitierten Listenabfragen existieren, unbekannte Ressourcen mit 404 beantwortet werden, ungültige Parameter mit 400/422 scheitern, Datenbankfehler als 503 erscheinen und API-Fehler keine sensiblen Details enthalten. Das kostenorientierte MVP ist bewusst oeffentlich lesbar, erlaubt nur `GET`, begrenzt CORS auf die Vercel-Origin und verwendet einen separaten Read-only-DB-User/Secret. Die Production-Abnahme erfordert zusaetzlich ECS-Health-Checks und einen DB-Reconnect-Nachweis; private Subnets und WAF bleiben spaetere Haertung.

## 10. Technische Entscheidungen fuer Phase 3

Diese Entscheidungen sind vor dem produktiven Phase-3-Ausbau verbindlich zu treffen oder zu bestaetigen:

- Authentifizierung: Der aktuelle MVP ist bewusst oeffentlich lesbar und read-only. Vor der Frontend-Produktivnutzung wird mindestens ein serverseitig verwaltetes Proxy-Secret eingefuehrt; JWT/OAuth2 bleibt die Option fuer benutzerbezogene oder personalisierte Daten.
- Frontend-Origin: Vercel-Produktions-Origin ueber `API_ALLOWED_ORIGINS` konfigurieren; keine Wildcard-Origin in Production.
- Frontend-Zugriff: Das Browser-Frontend spricht den API-Proxy an, nicht die AWS-API direkt. Der Proxy darf keine geheimen Header an den Browser weiterreichen.
- Datenbankzugriff: API verwendet einen separaten PostgreSQL-Read-only-User und ein separates Secrets-Manager-Secret; Ingest bleibt schreibberechtigt.
- Scheduler: EventBridge in Produktion, lokale Variante fuer Entwicklung.
- Secrets: AWS Secrets Manager in Produktion, keine Secrets im Repository.
- Skalierung: Ein API-Task fuer das kostenorientierte MVP; API Pod Min/Max, Connection-Pool und Autoscaling-Grenzen sind spaetere Production-Entscheidungen.
- Deployment: Rolling Deployments und Rollback-Prozess verbindlich dokumentieren.

### 10.1 Serverseitiger Frontend-Proxy und Kosten

Zielarchitektur:

```text
Browser -> Frontend-Proxy/BFF -> API mit Proxy-Authentifizierung -> PostgreSQL
```

- Bevorzugte MVP-Variante: Proxy als serverseitige Route des kuenftigen Frontends, zum Beispiel Next.js auf Vercel. Der API-Proxy-Token wird als Server-Environment-Secret hinterlegt.
- Strengeres Zielbild: Frontend-Proxy und API innerhalb AWS; API-ALB intern, Security Group nur vom Proxy, kein direkter Internetzugriff auf die API.
- Ein Token im Browser oder eine reine Origin-/Referer-Pruefung ist kein ausreichender Zugriffsschutz, weil beides nachgebaut werden kann.
- `/docs` und vergleichbare Diagnose-Endpunkte werden in Production deaktiviert oder ebenfalls authentifiziert.

Kostenannahme fuer die Planung:

- Vercel-Proxy auf einem bestehenden Frontend: meist keine oder geringe Zusatzkosten, abhaengig von Function-Aufrufen und Transfer.
- Separater kleiner ECS-Fargate-Proxy: grob 10-20 EUR/Monat plus moegliche Transferkosten.
- Privater API-Pfad mit API Gateway, WAF oder zusaetzlichem Load Balancer: grob 5-30 EUR/Monat bei geringem Traffic, je nach Nutzung und WAF-Regeln.
- Vor einer privaten Netzwerk-Haertung ist ein Kosten- und Verbindungsnachweis erforderlich; das oeffentliche ALB-MVP bleibt bis dahin der dokumentierte Zwischenstand.

**Architekturentscheidung (2026-09-20):** Fuer den MVP wird der serverseitige Next.js-Proxy auf Vercel vor dem AWS-API-ALB verwendet. Ein AWS-interner API-Proxy beziehungsweise interner ALB ist kein offener Auswahlpunkt mehr, sondern ein spaeteres Haertungsziel. Offen bleiben nur die Umsetzung von AP-13.a (Proxy-Secret-Validierung in der FastAPI), HTTPS/ACM fuer den API-Endpunkt und die produktive Verifikation des Proxy-Pfads.

**Kostenentscheidung (2026-09-20):** Der MVP verwendet keinen separaten ECS-/Fargate-Proxy, kein zusaetzliches API Gateway und keine verpflichtende WAF. Der serverseitige Proxy laeuft als Vercel Function im Frontend. Im Vercel-Hobbyplan ist das innerhalb der Kontingente enthalten: aktuell 1 Mio. Function-Aufrufe/Monat, 4 Stunden aktive CPU und 360 GB-Stunden reservierter Speicher pro Monat; zusaetzlich gelten Transferlimits. Das Hobby-Angebot ist laut Vercel fuer persoenliche, nicht-kommerzielle Projekte vorgesehen. Bei kommerziellem Betrieb oder Ueberschreitung der Kontingente ist der Vercel-Pro-Plan beziehungsweise eine alternative Hosting-Entscheidung erforderlich. Der bestehende AWS-API-ALB bleibt der kostenorientierte Zwischenstand. SNS-Benachrichtigungen fuer CloudWatch-Alarme bleiben optional, bis ein verbindlicher Alarmempfaenger feststeht.

- **MVP-Budgetannahme:** kein eigener Proxy-Service, keine zusaetzliche Gateway-/WAF-Grundgebuehr; fuer ein persoenliches Projekt bleibt der Vercel-Hobbyplan innerhalb seiner Limits kostenfrei. Variable Vercel-, ALB-, Transfer- und Alarmkosten werden ueber die bestehenden AWS-/Vercel-Budgets beobachtet.
- **Bewusst nicht im MVP enthalten:** separater ECS-Proxy (geschaetzt 10-20 EUR/Monat), privater API-Pfad mit API Gateway/WAF (geschaetzt 5-30 EUR/Monat plus Nutzung), NAT Gateway und Multi-AZ-Haertung.
- **Neubewertung ausloesen bei:** API-P95-/Fehler-Alarmen, steigender Traffic- oder Vercel-Function-Nutzung, Sicherheitsanforderung fuer private API-Erreichbarkeit oder verbindlicher WAF-/Compliance-Vorgabe.
- **Voraussetzung:** Die Entscheidung gilt nur fuer den MVP mit AP-13.a-Proxy-Authentifizierung, HTTPS/ACM und aktivierter Kosten-/Alarmueberwachung.

**WAF-Entscheidung (2026-09-20):** AWS WAF wird nicht als Go-live-Gate des kostenorientierten MVP eingefuehrt, sondern als priorisierte P2-Haertung nach dem Livegang. Der MVP ist eine read-only API mit AP-13.a-Proxy-Secret, HTTPS/ACM, begrenzten GET-Requests, FastAPI-Validierung, CloudWatch-Alarmen und separater Read-only-Datenbankrolle. Ein WAF wird bei erhoehtem Traffic, wiederholten Angriffsmustern, Compliance-Vorgabe oder wiederholten 4xx-/5xx-Anomalien nachgeruestet.

- **Kosten:** Fuer AWS WAF an einem ALB sind typischerweise eine monatliche Web-ACL-Gebuehr, Gebuehren je Regel und nutzungsabhaengige Request-Kosten einzuplanen; die exakten Preise sind region- und preisstandsabhaengig. Fuer den MVP wird deshalb keine feste WAF-Grundgebuehr akzeptiert.
- **Umsetzungsaufwand:** Terraform-Ressourcen fuer Web ACL, Managed/Core-Regeln, Rate-Limit-Regel, ALB-Assoziation, Logging und Tests; grob ein halber bis ein Arbeitstag fuer eine einfache Baseline, zusaetzlich Tuning nach echten Requests.
- **Go-live-Voraussetzung:** Vor Aktivierung des Vercel-Proxys muss der API-Endpunkt fuer Vercel erreichbar sein. Der aktuelle Terraform-Stand setzt den API-ALB auf `internal = true`; das ist mit einem direkten Vercel-Hobby-Proxy nicht kompatibel und muss vor dem Go-live entweder auf einen oeffentlichen HTTPS-ALB mit restriktivem Zugang oder auf einen privaten, netzwerkseitig angebundenen Proxy-Pfad geaendert und verifiziert werden.

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
- AP-11-API-Vertrag, Pagination und Fehlerformat sind versioniert dokumentiert.
- AP-12-Delta-Semantik ist fuer positive, negative, erste, fehlende und Null-Referenzwerte getestet; die History-Projektion bleibt unter dem AP-13-P95-Ziel.

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
- AP-10a.3 (erledigt, 2026-09-12): `backend/src/config.py` erzwingt in `APP_ENV=prod|production` den Pflichtmodus `COMUNIO_REQUIRE_SECRET_MODE=true`; ein ENV-Fallback wirft jetzt sofort einen Fehler und verhindert damit das unkontrollierte Blue/Green-Deployment mit Secret-Exposition.
- AP-10a.4 (erledigt, 2026-09-12): ECR-Repository ist auf `image_tag_mutability = "IMMUTABLE"` gesetzt, und das Terraform-Input `image_tag` akzeptiert keine `latest`-Referenzen mehr. Damit sind Rollbacks nur noch via signifikanter, nicht wechselnder Image-Referenzen moeglich.
- Abnahme: Keine sensiblen Werte oder rohen Exception-Texte in Standardlogs (erfuellt); State-Bootstrap-Code ist vorbereitet, der eigentliche Backend-Umzug (`terraform init -migrate-state`) steht als bewusst manuell freizugebender Schritt aus, da er den produktiven State-Speicherort aendert.

### 12.2 P2: Produktionshygiene

- AP-10b (erledigt, 2026-09-12): CI-Gates fuer Tests, Terraform-Format/Validate/Plan, Secret-Scanning und Dependency-Scanning sind in `.github/workflows/ci.yml` dokumentiert; die Pipeline blockiert Deployments bei Quality-Gate-Verletzung.
- AP-9.1 (erledigt, 2026-08-31): Drei aufeinanderfolgende Scheduler-Fenster mit `run_type=scheduled`, Exit-Code `0` und ohne Snapshot-Duplikate nachgewiesen; siehe Abschnitt 19 fuer die vollstaendige Evidenz.

### 12.3 P3: Härtung und Ausbau

- AP-10a.5/10a.6 (optional nach MVP): VPC-/Egress-Haertung mit NAT Gateway oder NAT Instance sowie ECR-/Secrets-Manager-VPC-Endpoints umsetzen; danach privaten Fargate-Task ohne Public IP und DB-Reconnect aus dem Task nachweisen.
- AP-10 (Anwendungsnachweise umgesetzt, 2026-09-13): Snapshot-Backoff (2/4/8 Sekunden, begrenzt auf vier Versuche), Login-Retry und idempotente Marktwert-Upserts sind durch fokussierte Tests nachgewiesen. Der private Netzwerkpfad ist vorbereitet, aber fuer den kostenorientierten MVP nicht erforderlich.
- AP-11 (umgesetzt): FastAPI-Endpunkte fuer Spieler, Teams, Historie und Transfermarkt sind als kostenorientiertes HTTP-MVP ausgerollt und verifiziert.

### 12.4 Verifizierter Stand der Release-Gate-Sequenz (2026-09-12)

- Schritt 1: Option D (MVP Standard mit `assign_public_ip=true` und Egress-Only SG) ist in AWS ausgerollt, via `terraform apply` synchronisiert (`Apply complete! Resources: 0 added, 0 changed, 0 destroyed`) und mit `Exit-Code 0` verifiziert.
- Schritt 2: NAT-Optionen A (`enable_nat_gateway`) und B (`enable_nat_instance`) wurden als schaltbare Terraform-Variablen in `infra/aws/terraform/network.tf` implementiert, validiert und im AWS-State synchronisiert.
- Schritt 3: Der Switch auf `assign_public_ip=false` (AP-10a.6 / Enterprise Private Egress) bleibt als optionale spaetere Haertung vorbereitet; der fehlende private Egress-Nachweis blockiert den kostenorientierten MVP nicht.

## 13. Security-Remediation-Sequenz (konsolidiert)

Diese Reihenfolge ist verbindlich vor dem regulaeren Produktionsbetrieb und dem weiteren Ausbau ab AP-10:

1. Credentials-Policy: Produktion nur Secrets Manager, kein ENV-Fallback.
1. DB-Transport-Policy: TLS `sslmode=require` oder staerker als Laufzeit-Gate.
1. Logging-Sanitization: keine rohen Exceptions, strukturierte `error_code`-Logs.
1. Snapshot-Input-Haertung: Allowlist-Verzeichnis, Groessenlimit, Schema-Pruefung.
1. Erst danach: Scheduler-Automatisierung und weitere Skalierungsfeatures.

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
- AP-13.a: Vor der Frontend-Produktivnutzung API-Authentifizierung fuer den serverseitigen Frontend-Proxy einfuehren; direkte unauthentifizierte API-Aufrufe muessen mit `401` abgewiesen werden.
- Nachweis erbringen, dass der Proxy-Token nicht im Browser ausgeliefert wird; `/docs` in Production deaktivieren oder schuetzen.
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

| Datum (UTC)      | Ereignis             | run_id | Ergebnis                                                                                   | market_values_count |
| ---------------- | -------------------- | ------ | ------------------------------------------------------------------------------------------ | ------------------- |
| 2026-08-25 19:39 | `run_type=scheduled` | 10     | `run_success`                                                                              | 501                 |
| 2026-08-26 06:00 | `run_type=scheduled` | -      | `run_failed stage=login` (Comunio "Plus/Pro"-Sperre, vor Deployment der Login-Retry-Logik) | -                   |
| 2026-08-26 13:05 | `run_type=scheduled` | 11     | `run_success`                                                                              | 601                 |
| 2026-08-27 06:00 | `run_type=scheduled` | 13     | `run_success` (nach `login_attempt_failed` + `login_recovered` bei Versuch 2)              | 702                 |
| 2026-08-28 06:00 | `run_type=scheduled` | 14     | `run_success` (nach `login_recovered` bei Versuch 2)                                       | 802                 |
| 2026-08-29 06:00 | `run_type=scheduled` | 15     | `run_success` (Login sofort erfolgreich)                                                   | 902                 |
| 2026-08-30 06:00 | `run_type=scheduled` | 16     | `run_success` (nach `login_recovered` bei Versuch 2)                                       | 1002                |
| 2026-08-31 06:00 | `run_type=scheduled` | 17     | `run_success` (nach `login_recovered` bei Versuch 2)                                       | 1102                |

### 19.3 Bewertung

- Fuenf aufeinanderfolgende taegliche Zeitfenster (2026-08-27 bis 2026-08-31) erfuellen `run_type=scheduled` mit `run_success` und uebertreffen damit die geforderten drei aufeinanderfolgenden Fenster.
- `market_values_count` steigt exakt um 100 pro Tag (702 -> 802 -> 902 -> 1002 -> 1102), was zur erwarteten Snapshot-Groesse passt; es liegen keine Duplikat-, Unique-Constraint- oder IntegrityError-Meldungen in den CloudWatch-Logs vor.
- Der einzelne fehlgeschlagene Lauf am 2026-08-26 06:00 lag vor der Aktivierung von AP-9.2 (Login-Retry, deployed am 2026-08-26) und ist damit kein Verstoss gegen den nachtraeglich gehaerteten Betrieb; alle Laeufe ab 2026-08-27 nutzen die Retry-Logik und enden erfolgreich.
- Damit gelten Abschnitt 3 Punkt 4, AP-9.1 (Abschnitt 12.2) sowie das entsprechende Akzeptanzkriterium in `backend/OPERABILITY-AP9.md` als erfuellt.

### 19.4 Naechster Schritt

- AP-10-Anwendungsnachweise, AP-11, AP-12 und AP-13 sind inzwischen umgesetzt. Der naechste verbindliche Nachweis ist nicht die kostenpflichtige Staging-Umgebung, sondern die laufende CI-/Production-Beobachtung; HTTPS/ACM, WAF und private API-Subnets bleiben optionale Haertung.

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

- **Phase A (jetzt):** Single-AZ Ingest, single Fargate task daily, Local/S3 state und kostenorientierter oeffentlicher API-MVP.
- **Phase B (Q4):** Frontend-MVP mit serverseitigem API-Proxy, Proxy-Authentifizierung, Query Caching und Rate-Limiting; danach private API-Netzwerkpfade pruefen.
- **Phase C (Q1 2027):** Multi-AZ Ingest, RDS replicas, CDN für Frontend, Event-driven backpressure (SQS DLQ → Lambda retry).

### 20.5 Software Engineer Agent v1 (Execution Summary)

**Codierung abgeschlossen:**

1. ✅ `backend/src/ingest/runner.py`: `_safe_detail()` Funktion + 3 Call-site Patches.
1. ✅ `backend/tests/test_scheduled_runner.py`: Sanitization-Tests (sensible Substrings abgedeckt).
1. ✅ `infra/aws/terraform/state_backend.tf`: S3-Bucket (versioned, AES256, public-access-blocked, 90d lifecycle) + DynamoDB lock table.
1. ✅ `infra/aws/terraform/backend.tf`: Auskommentierter `backend "s3"` Block (Runbook-triggert Aktivierung).
1. ✅ `architecture.md` §5.1/§5.2: Logging-Gate dokumentiert, State-Exposure-Analyse eingefügt.
1. ✅ `infra/aws/README.md`: Remote-State-Migrationsprozess dokumentiert.
1. ✅ `terraform validate`: Erfolgreich, keine Fehler.

**Validation:**

- `pytest backend/tests/ -q` → 13 passed.
- `terraform validate` → Success.

**Nächste Schritte (manuelle Freigabe erforderlich):**

- `terraform init -migrate-state` (production state-Speicherort ändert sich → erfordert bewusste Freigabe vor Ausführung, nicht automatisiert).

### 20.6 Offene Entscheidungen und Blocker

|Entscheidung|Status|Aktion|Deadline|
|---|---|---|---|
|Remote Terraform-State aktivieren (`terraform init -migrate-state`)|**Cooked, awaiting approval**|Manuelle Freigabe vor Execution; siehe Runbook in `infra/aws/README.md` + `state_backend.tf`|Nach naechster Team-Review|
|RDS-Master-Passwort rotieren|**Deferred, documented**|Runbook vorbereitet; Rotation opportunistisch oder beim Team-Onboarding|Nach State-Backend-Aktivierung|
|RDS Multi-AZ aktivieren|**Deferred (cost mandate)**|Explizit auf Q1 2027 verschoben (Infrastruktur-Budget-Constraint)|Q1 2027|
|Secrets-Manager-Pflicht in Prod durchsetzen|**Erledigt**|Terraform-/Runtime-Gates erzwingen Secrets Manager in Produktion|2026-09-12|
|Dedicated terraform-deploy IAM-Role|**P2 optional**|Design vorbereitet, Aktivierung bei Team-Onboarding|Q4 2026|

### 20.7 Zusammenfassung: AP-10a abgeschlossen, nächste Phase vorbereitet

**Erledigt:**

- ✅ Log-Sanitization (P1): Rohe Exception-Details entfernt, Tests bestanden.
- ✅ State-Exposure-Analyse (P1): Kein Git-Vektor, Bootstrap-Code ready, Aktivierung deferred.
- ✅ Security-Gates S1–S4 dokumentiert und teilweise durchgesetzt (S2/S4 live, S1/S3 in Terraform pending).

**Noch zu tun (manueller Betriebs-/Hardening-Schritt, kein MVP-Blocker):**

- Remote State aktivieren (manuelle Freigabe mit `terraform init -migrate-state`).

**P2–P3 (optionale Weiterentwicklung nach dem API-MVP):**

- AP-10b: CI-Gates sind umgesetzt.
- AP-10c: Immutable Image-Referenzen sind umgesetzt.
- AP-11/AP-12/AP-13: API, Delta-Projektion und Integrations-/Contract-Nachweise sind umgesetzt.
- Optional: private Netzwerk-Haertung, HTTPS/ACM, WAF und AWS-Staging-Baseline.

### 20.8 Migration-Status (2026-09-01)

**Erfolgreiche Ausführung aller Migrationsschritte (2026-09-01):**

1. **Bootstrap-Ressourcen erstellt** ✅

   - AWS S3-Bucket `comunio-prod-tfstate` mit Versioning, AES256-Encryption, Public-Access-Block und 90-Tage-Lifecycle für noncurrent versions
   - AWS DynamoDB-Tabelle `comunio-prod-tfstate-lock` mit PAY_PER_REQUEST-Billing
   - Plan: 6 to add, 0 to change, 0 to destroy
   - Termin: 2026-09-01 (Schritt 1)

1. **Backend-Konfiguration aktiviert** ✅

   - `infra/aws/terraform/backend.tf`: Terraform-Block aus Kommentaren entfernt
   - Datei ist konfiguriert mit:
     - `bucket = "comunio-prod-tfstate"`
     - `key = "comunio-prod/terraform.tfstate"`
     - `region = "eu-central-1"`
     - `dynamodb_table = "comunio-prod-tfstate-lock"`
     - `encrypt = true`
   - Termin: 2026-09-01 (Schritt 2)

1. **State Migration durchgeführt** ✅

   - `terraform init -migrate-state` bestätigt mit `yes`
   - Lokales `terraform.tfstate` wurde zu S3-Backend migriert
   - S3-State-Datei: `s3://comunio-prod-tfstate/comunio-prod/terraform.tfstate` (97,538 bytes)
   - DynamoDB Lock-Tabelle Status: `ACTIVE`
   - Termin: 2026-09-01 (Schritt 3)

1. **Plan-Verifikation** ✅

   - `terraform plan` bestätigt: No changes needed
   - Infrastruktur entspricht Konfiguration
   - Keine unerwarteten Diffs
   - Termin: 2026-09-01 (Schritt 4)

1. **Git-Sicherung** ✅

   - `.gitignore` erweitert um Terraform-Richtlinien:
     - `terraform.tfstate*` (alle State-Dateien ausgeschlossen)
     - `.terraform/` (lokale Provider-Cache ausgeschlossen)
     - `.terraform.lock.hcl` (NICHT ausgeschlossen, ist Dependency-Lock-File wie package-lock.json)
   - `.terraform.lock.hcl` ist in Git-Tracking bestätigt
   - Alle Änderungen staged für Commit
   - Termin: 2026-09-01 (Schritt 5)

**Verifikation abgeschlossen (2026-09-01):**

- ✅ Lokale `terraform.tfstate` existiert noch (Backup, nicht mehr verwendete)
- ✅ Remote S3-State ist abrufbar und vollständig
- ✅ DynamoDB Lock-Tabelle ist aktiv und bereit
- ✅ `terraform show -no-color` listet managed resources aus Remote-State auf
- ✅ Alle 13 Backend-Tests bestanden
- ✅ Terraform-Validierung erfolgreich

**Production-Readiness:**

- Terraform State ist nun durable (S3 mit Versioning), distributed (shareable Speicher), und gesichert mit Locking (DynamoDB) und Encryption
- Kein State-Speicherort-Risiko für Team-Onboarding oder CI/CD-Automation
- RDS-Credentials in lokalem State sind nicht mehr ein Hauptproblem (State ist aus Git und auf sicherem Cloud-Speicher)
- Rotation der RDS-Credentials bleibt auf P2 (kein Git-Expositionsvektor, opportunistische Durchführung nach State-Stabilisierung)
