# Umsetzungsplan Software Engineering: AWS → Contabo VPS (Ubuntu)

**Status:** Planung, nicht ausgeführt

**Ziel:** Die bestehende Comunio-Datenplattform kontrolliert von AWS ECS/RDS/EventBridge auf einen Ubuntu-VPS bei Contabo überführen, ohne fachliche Funktionen, Sicherheitskontrollen oder Datenintegrität zu verlieren.

**Geltungsbereich:** Anwendungscode, Container, Scheduler, Secrets, PostgreSQL, CI/CD und überprüfbare Tests. Keine tatsächliche Serververbindung, Bereitstellung oder Quellcode-/Konfigurationsänderung ist Bestandteil dieses Dokuments.

## 1. Ergebnis in Kürze

Die aktuelle Anwendung ist kein bereits portables VPS-Paket: Ingest und API sind zwar als getrennte Docker-Images angelegt, aber es gibt keine Compose-Datei oder VPS-spezifische Laufzeitkonfiguration. Der Ingest-Client und der API-Login laden Secrets direkt aus AWS Secrets Manager; Datenbank-URL und API-Proxy-Secret werden in AWS über Secret-Injektion bereitgestellt. Zusätzlich erzwingt die Datenbankverbindung TLS. Die Migration benötigt daher vor dem VPS-Umzug einen expliziten, testbaren Secret-Provider für lokale Secret-Dateien (oder einen gleichwertigen dedizierten Secret-Dienst), PostgreSQL-TLS, Compose-Betriebsdefinitionen und einen idempotenten Scheduler.

Empfohlene erste Zielausbaustufe: Ubuntu-VPS mit Docker Compose, PostgreSQL 16 nur im internen Container-Netz, täglichem systemd-Timer in UTC für den einmaligen Ingest-Container, verschlüsselte externe Backups, HTTPS-Reverse-Proxy und unveränderte API-Abschaltung. API-Freigabe erfolgt separat, erst nach erfolgreichem Authentifizierungs-/Proxy-Sicherheits- und End-to-End-Test.

## 2. Belegte Ausgangslage

- Das Repository beschreibt eine aktive tägliche ECS-Fargate-/EventBridge-Pipeline mit 06:00 UTC, Login-Retry (drei Versuche, standardmäßig fünf Minuten Abstand), Snapshot-Retry und Idempotenz für tägliche Marktwerte. Der dokumentierte Stabilitätsnachweis stammt aus fünf erfolgreichen Tagesfenstern Ende August 2026. Siehe [README](../../README.md) und [AP-9-Runbook](../../backend/OPERABILITY-AP9.md).
- Der Ingest-Container wird mit `backend/Dockerfile` gebaut und startet standardmäßig einen manuellen Snapshot; der Scheduler muss den Container mit `--run-type scheduled --mode snapshot` starten. Ein separates API-Image existiert in `backend/Dockerfile.api`.
- `backend/src/ingest/comuniopy_client.py` liest Comunio-Zugangsdaten aus AWS Secrets Manager, wenn `COMUNIO_SECRET_NAME` gesetzt ist; ohne Secret-Modus bleibt ein Umgebungsvariablen-Fallback. `APP_ENV=production` verlangt standardmäßig `COMUNIO_REQUIRE_SECRET_MODE=true`.
- `backend/src/api/auth.py` lädt die Login-Konfiguration aus AWS Secrets Manager (`AUTH_SECRET_ARN`); `backend/src/api/app.py` verlangt in Produktion zusätzlich `API_PROXY_SECRET` und `AUTH_SECRET_ARN`. Die API ist laut README derzeit absichtlich abgeschaltet.
- `backend/src/database/connection.py` akzeptiert nur `sslmode=require`, `verify-ca` oder `verify-full`. Das muss für PostgreSQL auf demselben VPS beibehalten werden; ein unverschlüsselter DB-Verkehr im Docker-Bridge-Netz wäre keine unveränderte Sicherheitslage.
- SQL-Migrationen liegen in `backend/migrations/`; der Runner verfolgt angewandte Migrationen in `schema_migrations`. Tests umfassen Unit-, API- und PostgreSQL-Integrationstests. CI prüft bereits Backend, PostgreSQL 16, Docker-API-Image, Terraform, Dependencies, Secrets und Repository-Konfiguration, nicht jedoch ein vollständiges Compose-VPS-Release.
- Das Schema verwendet Eindeutigkeits-/Upsert-Strategien für wiederholte Snapshots; die produktive API ist read-only konzipiert und nutzt getrennte Datenbank-Zugangsdaten. Siehe [Datenmodell](../../data_model.md), [AP-7-Runbook](../../backend/OPERABILITY-AP7.md) und [AWS-Baseline](../../infra/aws/README.md).

## 3. Annahmen und offene technische Entscheidungen

| Kennung | Annahme für diesen Plan | Umsetzung/Entscheidung vor Freigabe |
|---|---|---|
| A1 | Es gibt zunächst genau einen Contabo-Ubuntu-VPS und keine Hochverfügbarkeits- oder automatische Failover-Umgebung. | Erreichbare Verfügbarkeit, Wartungsfenster und Wiederanlaufzeit ausdrücklich gegen die nicht-funktionalen Anforderungen abgleichen. Ein Einzel-VPS garantiert keine 99,9 % Ende-zu-Ende-Verfügbarkeit. |
| A2 | Ubuntu LTS, Docker Engine und Compose v2 werden auf dem Ziel installiert; Versionen sind in der Betriebsdokumentation festzuhalten. | Ziel-Ubuntu-LTS und unterstützte Docker-Version zum Umsetzungszeitpunkt festlegen. Kein Docker-Socket im Anwendungskontainer. |
| A3 | Die bestehende PostgreSQL-Datenbank enthält die zu übernehmenden Produktionsdaten; Umzug erfolgt mit konsistentem Export/Import und dokumentiertem Cutover. | Tatsächliche AWS-Datenbankversion, Größe, Extensions, Collation, Zeitzone, Rollen, Backup-/RPO-Anforderungen sowie Datenaufbewahrung vorab inventarisieren. |
| A4 | Für den ersten Cutover bleibt die API deaktiviert, wie im aktuellen Projektstand vorgesehen. | API separat freigeben, wenn Backend-Proxy-Authentifizierung, Login-Secret, HTTPS und Frontend-Integration abgenommen sind. |
| A5 | Eine dateibasierte Secret-Injektion auf dem Einzelserver ist zunächst akzeptabel. | Host-Root bleibt Vertrauensanker. Wenn Mehrpersonenbetrieb oder stärkere Audit-/Rotationsanforderung gilt, dedizierten Secret-Manager ergänzen. |
| A6 | Der Zeitplan bleibt täglich 06:00 UTC. | Schedule nur nach Prüfung von VPS-Zeitzone, Zeitabgleich (NTP), Comunio-Verfügbarkeit und gewünschtem Fachfenster ändern. |
| A7 | „Keine SSH-Verbindung“ beschränkt die Ausführung dieses Plans; Remote-Verbindung und Deployment erfolgen nicht durch diesen Auftrag. | Der spätere Betrieb muss einen freigegebenen, protokollierten Operatorzugang nutzen. |

## 4. Zielarchitektur und Betriebsgrenzen

```text
Internet ── HTTPS ── Caddy/Reverse Proxy ── API (optional, zunächst aus)
                                           │
systemd Timer (06:00 UTC) ── Compose One-shot Ingest
                                           │
                     privates Compose-Netz mit PostgreSQL 16
                                           │
                   verschlüsselter, externer Backup-Speicher
```

1. **Dienste:** `db` (PostgreSQL 16), optional dauerhafter `api`, One-shot `ingest`-Job und optional `proxy` (HTTPS). Scheduler ist ein systemd-Hosttimer, kein Cron-Prozess im App-Container und kein dauerhaft laufender Scheduler-Container.
2. **Netzwerk:** PostgreSQL erhält keinen öffentlich erreichbaren Port. API und Ingest greifen nur über das private Compose-Netz auf die Datenbank zu. Ein eventuell für administrative Wartung erforderlicher DB-Zugang ist kurzfristig und auf Loopback bzw. einen gesonderten Operatorpfad zu begrenzen. API- und Proxy-Ports werden nicht direkt aus dem Internet exponiert.
3. **TLS:** Externer Zugriff ausschließlich über HTTPS. PostgreSQL-TLS bleibt verpflichtend; `DATABASE_URL` verwendet für die VPS-Produktionsverbindung `sslmode=verify-full` mit vertrauenswürdigem CA-Zertifikat und passendem Servernamen. `sslmode=require` darf höchstens eine dokumentierte Übergangsstufe sein, weil es das Zertifikat nicht validiert.
4. **API:** API bleibt initial deaktiviert. Bei späterer Aktivierung bleiben API-Proxy-Bearer-Authentifizierung, Login-Session, Rate-Limits, CORS-Whitelist und separate PostgreSQL-Read-only-Rolle zwingend. Keine direkte öffentliche Erreichbarkeit des Uvicorn-Ports.
5. **Zustand:** PostgreSQL-Daten ausschließlich in benanntem persistentem Volume. Images, Containerdateisystem und Logs sind nicht der Datenbestand. Datenbank- und Secret-Backups liegen getrennt vom VPS, verschlüsselt, zugriffsbeschränkt und mit dokumentierter Aufbewahrung.
6. **Zeit:** Timer mit fester UTC-Angabe; Anwendungszeit-/Snapshot-Datumslogik wird anhand vorhandener Tests überprüft. Hostzeitzone darf nicht unbemerkt den Run-Zeitpunkt verschieben.

## 5. Geplante Änderungen nach Repository-Pfad

Die folgenden Punkte sind Change-Spezifikation, keine in diesem Auftrag ausgeführten Änderungen.

### 5.1 Konfiguration und Secret-Provider

**Betroffene Ist-Dateien:** `backend/src/config.py`, `backend/src/ingest/comuniopy_client.py`, `backend/src/api/auth.py`, `backend/src/database/connection.py`, `backend/.env.example`, Dockerfiles.

- Einen expliziten Secret-Provider-Vertrag einführen, z. B. `aws` und `file`. Providerwahl ist eindeutig; keine stillschweigende AWS→ENV-Ausweichlogik in Produktion.
- Für Contabo sensible Werte ausschließlich aus read-only gemounteten Dateien beziehen, z. B. `COMUNIO_CREDENTIALS_FILE`, `DATABASE_URL_FILE`, `AUTH_CONFIG_FILE` und `API_PROXY_SECRET_FILE`. Exakte Variablennamen als API definieren und in Beispieldateien ausschließlich Platzhalter verwenden.
- Datei-Inhalt für Comunio in einem validierten JSON-Format mit den erforderlichen Feldern lesen. Auth-Konfiguration muss weiter Username, bcrypt-Cost-12-Passworthash und kryptografisch ausreichend starken JWT-Schlüssel validieren. Proxy-Secret als einzelner Wert oder eng validiertes Format definieren. Fehlende/ungültige Dateien müssen vor Arbeitsbeginn fail-closed scheitern.
- AWS-Unterstützung nur behalten, wenn derselbe Providervertrag und dieselben Validierungen für beide Provider bestehen; unnötige AWS-Imports beim Contabo-Pfad vermeiden. Eine Dateioption darf AWS-Credentials oder Secrets nicht in Prozessargumente, Logs, Compose-Umgebungsblöcke oder CI-Ausgaben kopieren.
- `APP_ENV=production` darf Umgebungsvariablen-Zugangsdaten nicht als Fallback verwenden. `COMUNIO_SNAPSHOT_FILE` muss in Produktion standardmäßig gesperrt bleiben bzw. nur in nicht-produktiven Testprofilen nutzbar sein.
- Für jedes Secret `*_FILE`-Auflösung zentral und konsistent implementieren, Fehlertexte ohne Dateiinhalt, Secretwert oder vollständigen DSN. Relative Dateipfade vermeiden; erlaubte Secret-Verzeichnisse und Dateirechte dokumentieren.
- API-Secret-Laden von AWS entkoppeln, bevor die API auf dem VPS aktiviert wird. Fehlendes Secret muss Health-Readiness/Authentifizierung fail-closed machen, nicht zu deaktivierter Authentifizierung führen.
- `backend/.env.example` bleibt eine nicht geheime Entwickler-Vorlage. Produktionswerte nicht in `.env`, Git, Compose-Labels, Image-Layern oder `docker inspect`-sichtbaren Klartext-Umgebungsvariablen ablegen.

### 5.2 Container und Compose

**Betroffene Ist-Dateien:** `backend/Dockerfile`, `backend/Dockerfile.api`, `backend/.dockerignore`; neu: `compose.yaml` (oder versionskontrollierte Dateien unter `infra/contabo/`), PostgreSQL-TLS-Konfiguration und Container-Smoke-Tests.

- Bestehendes non-root-Ausführungsmodell beibehalten. Images als minimale, reproduzierbar gebaute Python-3.11-Images mit gepinnten/gelockten Dependencies, Health-/Exit-Verhalten und `init`- bzw. sauberem Signalhandling härten. Versions-/Digest-Pinning für Basisimage und PostgreSQL-Image als Release-Entscheidung dokumentieren.
- Compose `db`-Dienst: PostgreSQL 16, benanntes Datenvolume, keine öffentliche Portfreigabe, `restart: unless-stopped`, `pg_isready`-Healthcheck und Ressourcen-/Log-Rotation. TLS aktivieren und Zertifikats-/CA-Dateien read-only einbinden. Datenbankpasswort nicht in Compose-Definition oder Image speichern.
- Compose `ingest`-Dienst: kein dauerhafter Autostart; One-shot-Befehl entspricht dem existierenden Entry Point `python -m src.ingest.runner --run-type scheduled --mode snapshot`. `depends_on` mit DB-Healthcheck nur als Startreihenfolge verwenden, nicht als Ersatz für Anwendungsfehlerbehandlung. Bei Fehler Exitcode ungleich null an systemd weitergeben.
- Compose `migrate`-Profil oder separater one-shot-Aufruf: kein automatisches paralleles Migration-Ausführen bei jedem App-Start. Migration wird kontrolliert vor Anwendung/Cutover gestartet und anschließend auf Idempotenz geprüft.
- Compose `api`-Profil standardmäßig aus; bei expliziter Aktivierung non-root, nur privates Netz zum Proxy, DB-Read-only-Secret, Produktionskonfiguration, Restart-Policy und Healthchecks. Keine Portveröffentlichung an `0.0.0.0`.
- Compose `proxy` nur bei API-Freigabe oder für notwendige HTTPS-Endpunkte; HTTPS, automatische Zertifikatserneuerung und HTTP→HTTPS-Redirect. Forwarded-Header nur vom vertrauenswürdigen Proxy akzeptieren; keine direkt erreichbare API-Instanz.
- Alle Dienste mit `read_only`-Root-Dateisystem, `cap_drop: [ALL]`, `no-new-privileges`, CPU-/Memory-Limits und nur nötigen writable tmpfs/Volumes konfigurieren, sofern die getesteten Bibliotheken das zulassen. Keine privilegierten Container, Host-Netzwerk-, Host-PID- oder Docker-Socket-Mounts.
- Image-Build-Kontext so begrenzen, dass `.env`, lokale Secrets, `terraform.tfstate`, Dumps, private Schlüssel und Backupdateien durch `.dockerignore` ausgeschlossen sind. Compose-Interpolation mit Dummy-Variablen in CI validieren, ohne produktive Secrets zu verwenden.

### 5.3 PostgreSQL-Migration, Rollen und Datenschutz der Daten

- Zieldatenbankversion und Schema aus AWS inventarisieren; `backend/migrations/001_core_tables.sql` bis zur aktuellen Migration sowie `schema_migrations`-Status vergleichen. Extensions, Sequenzen, Constraints, Indizes, Zeitzone und Tabellenvolumen prüfen.
- Datenübertragung über konsistenten, verschlüsselten PostgreSQL-Export/Import und transportverschlüsselte Übertragung. Temporäre Dumps mit minimalen Dateirechten anlegen, nicht in Repository/CI-Artefakte/Supporttickets übertragen, nach verifiziertem Import sicher entfernen.
- Vor Import und direkt nach Import Datenbankversion, Encoding, Migrationstabelle, Zeilenzahlen wichtiger Tabellen, Min-/Max-Datum, Primär-/Unique-Constraints und Stichprobenabfragen vergleichen. Migrationen auf vorhandener produktiver Datenbank nicht rückwärts laufen lassen.
- `DATABASE_URL` für Ingest verwendet eine dedizierte Rolle mit nötigen Schreibrechten, nicht PostgreSQL-Superuser/Masterkonto. API (falls aktiviert) erhält separate Rolle mit ausschließlich `SELECT` auf benötigte Tabellen/Views. Rollen-Provisionierung und Grants versioniert dokumentieren; keine API-Schreibrechte.
- PostgreSQL-TLS-Zertifikat und CA ohne Secret-/Private-Key-Ausgabe erneuern können. Produktionsclient verwendet Zertifikatsprüfung (`verify-full`), gültige Hostnamen und CA-Vertrauen. Verbindungstest muss eine ungültige CA und Namensabweichung ablehnen.
- Backupstrategie mindestens: automatisierter regelmäßiger logischer oder physischer PostgreSQL-Backupjob, verschlüsselte Übertragung in einen anderen Fehler-/Standortbereich, Retention aus Aufbewahrungsanforderung ableiten, Integritätsprüfung und wiederkehrender Restore-Test. Ein lokales Backup auf derselben VPS-Platte gilt nicht als ausreichende Wiederherstellung.
- Cutover-Prozess: Ingest auf AWS vor dem finalen Delta-/Konsistenzexport kontrolliert pausieren; Snapshot-/Write-Zugriffe während Umschaltung verhindern; letzte Datenübernahme und Schema-/Counts verifizieren; VPS-Ingest erst nach Freigabe aktivieren. Doppeltes paralleles Schreiben aus AWS und VPS ist zu verhindern.
- Rollback: AWS-Datenbank/-Scheduler erst nach vereinbarter Stabilitätsbeobachtung abschalten. Wenn VPS bereits produktive Daten geschrieben hat, vor Rückschaltung festlegen, wie Delta-Daten verlustfrei zurückgeführt werden; nicht einfach auf AWS zurückschalten und VPS-Schreibvorgänge ignorieren.

### 5.4 Scheduler, Locks und Fehlerbehandlung

**Geplante Laufzeitkomponente:** systemd `.service` und `.timer` auf dem Ubuntu-Host; Ausführung im bestehenden Ingest-Container.

- Timer täglich 06:00 UTC mit `Persistent=true`; tatsächlicher Zeitplan und Zeitzone in Unit-Datei und Betriebsdokumentation explizit festhalten. NTP/Chrony-Synchronisierung prüfen.
- Service wartet auf einen gesunden DB-Dienst und führt dann gezielt den Compose-One-shot-Job mit `docker compose run --rm ingest` aus; Compose-Projektpfad/Arbeitsverzeichnis und Secret-Dateien sind explizit. Exitcode wird an systemd weitergereicht. Keine Compose-Environment-Datei mit Klartext-Secrets verwenden.
- Einen atomaren Host-Lock (z. B. `flock`) oder systemd-Einzelinstanzmechanismus nutzen, um manuelle und zeitgesteuerte Läufe nicht gleichzeitig auszuführen. Lock muss bei Prozessende freigegeben werden. Wiederholte Tages-Snapshots müssen durch bestehende DB-Constraints/Upserts idempotent bleiben.
- Ingest behält Login-Retry 3 × fünf Minuten sowie begrenzte Snapshot-Retries 2/4/8 Sekunden aus `runner.py`; diese Werte nicht zusätzlich unkontrolliert mit Scheduler-Retries multiplizieren. Gesamtdeadline des Services muss erwartete Laufzeit plus Retryfenster abdecken.
- Fehlgeschlagene Läufe müssen anhand Exitcode und strukturierten, redigierten Ereignissen erkannt werden (`run_started`, `db_verify`, `run_success`, `run_failed`). Für `run_success` werden nicht-null `records_written` und plausibler Datenbankfortschritt überwacht. Alarmierung bei fehlgeschlagenem oder ausgebliebenem Lauf definieren.
- `Persistent=true` holt einen verpassten Termin nach einem Hostausfall gegebenenfalls beim Neustart nach; muss mit Lock und Idempotenz funktionieren. Kein automatischer enger Restart-Loop. Manuelle Wiederholung erst nach Ursachenklärung gemäß [AP-9-Runbook](../../backend/OPERABILITY-AP9.md).
- Logs über journald/Container-Logging mit Rotation, begrenzter Retention und Zugriffsrechten. Keine Zugangsdaten, DSNs, Auth-Tokens, Comunio-Antwortkörper, Roh-Exceptions oder Secret-Werte loggen.

### 5.5 CI/CD und Release-Lieferkette

**Ist-Pipeline:** [.github/workflows/ci.yml](../../.github/workflows/ci.yml).

- CI um Build und Smoke-Test für das Ingest-Image und die Compose-Konfiguration erweitern. Bestehende Unit-/Integrationstests, PostgreSQL 16, API-Image-Build, Dependency-Audit, Gitleaks/Trivy und Frontend-Checks beibehalten.
- In PRs: `docker compose config` mit ungefährlichen CI-Variablen, `docker build` beider Images, Unit-Tests, PostgreSQL-Integrationstests, Compose-Health-/Migration-/Ingest-Fixture-Test und Secret-/Container-Scans. Keine Produktionscredentials oder produktiven DB-Dumps in CI.
- Release-Images bei erfolgreichem Gate in eine private Registry (z. B. GHCR) übertragen. Tag unveränderlich aus Release/Commit ableiten; nach Veröffentlichung Image-Digest erfassen, niemals `latest` als Produktionsreferenz verwenden. SBOM/Scan-Ergebnis und Source-Commit zum Release dokumentieren.
- Deployment ist zunächst **Continuous Delivery mit Freigabe**, nicht unbeaufsichtigtes Push-to-Production: geschützte GitHub-Environment-Freigabe; auf dem VPS nur Pull des freigegebenen Digests, Vorab-Backup, Migration (nur wenn freigegeben), Health-/Smoke-Test und klarer Rollback-Punkt. Ein schreibender GitHub-Runner auf dem VPS sowie allgemeiner Root-SSH-Zugang für CI sind zu vermeiden.
- Wenn ein automatisierter Deploy-Trigger eingeführt wird, nur dedizierter Deploy-Principal mit eingeschränktem Befehl/Umfang, host-key pinning, kurzlebigen/rotierbaren Credentials, GitHub Environment Approval und Audit-Log. Niemals Private Keys/Secrets als Repository-Datei, Build-Argument, Artefakt oder Workflow-Log ausgeben.
- Release enthält mindestens Image-Digests, DB-Migrationsstand, Compose-Konfigurationsversion (ohne Secretwerte), getestete Rollback-Version und Testergebnis. Ein Rollback darf Schemaänderungen nicht implizit rückwärts migrieren.
- Vorhandene Terraform-Validierung nicht als Contabo-VPS-Deployment-Test missverstehen; AWS Terraform bleibt für Altbestand relevant, bis die AWS-Ressourcen kontrolliert beendet sind.

## 6. Geplante Umsetzung in Phasen

### Phase 0 — Vorbedingungen und Sicherung

1. Betriebs-/Security-Inventar für AWS erstellen: ECS-Taskdefinition/Images, EventBridge-Regel, RDS/PostgreSQL-Version, Daten-/Tabellengröße, Secret-Typen und IAM-Umfang, API-Status, Backup-/Retention- und Alarmkonfiguration.
2. Konkrete Ziele für RPO/RTO, Aufbewahrung, erwartete Ausfallzeit und DNS/HTTPS klären; A1–A6 bestätigen und im Umsetzungs-/Betriebshandbuch festhalten.
3. Wiederherstellbarkeit des aktuellen AWS-Backups nachweisen und vor Cutover eine frische, verifizierte Sicherung anlegen.
4. Go/No-Go: Keine Migration, solange Rücksicherung und konsistenter DB-Export nicht erfolgreich demonstriert sind.

### Phase 1 — Portabilität im Code

1. Secret-Provider-Schnittstelle und file-backed Produktionsmodus implementieren; AWS-Modus nur für AWS-Altbetrieb erhalten. Keine Umgebungsfallbacks im Contabo-Produktionsmodus.
2. Sichere Einstellung für Datenbank-URL-Datei sowie API-Auth-/Proxy-Dateien ergänzen; Fehlerpfad- und Redactionstests ergänzen.
3. Rollen-/TLS-Konfiguration für PostgreSQL-16-Ziel spezifizieren; `sslmode=verify-full` samt CA-Test umsetzen, bevor VPS-Integrationstests starten.
4. Produktions-Fail-Closed-Verhalten für API und Ingest verifizieren; API bleibt bis zur gesonderten Freigabe abgeschaltet.
5. Go/No-Go: vollständiger Backend-Testsatz plus neue Secrets-/TLS-Tests bestanden.

### Phase 2 — Container-/Betriebsdefinition

1. Compose-Datei mit `db`, `migrate`, `ingest`, optionalem `api` und `proxy` anlegen; API-Profil standardmäßig nicht aktiv.
2. PostgreSQL TLS, Healthcheck, private Netzgrenzen, non-root, Read-only-Dateisysteme, Ressourcenlimits, Secret-Mounts, Logging-Rotation und persistentes Volume konfigurieren.
3. systemd-Service-/Timer-Dateien, Lock, Ablauf-Timeouts, Monitoring-/Alarmanweisung, Backup-/Restore-Skripte und ein Contabo-Runbook versionieren.
4. Go/No-Go: Compose syntaktisch gültig; Images laufen lokal unter non-root; kein Secret im Image-/Compose-Inspect-Ergebnis; Persistenz-/Restore-Tests bestanden.

### Phase 3 — CI und Release-Ablauf

1. Pipeline um Compose-/Ingest-Build, Datenbankintegration, Container-Scan, Compose-Smoke-Tests und Release-Digest ergänzen.
2. Pull-basiertes, freigegebenes Deployment und Rollback auf unveränderliche Image-Digests dokumentieren. Secret-Werte ausschließlich im Zielbetrieb bereitstellen.
3. Go/No-Go: PR-Gates blocken absichtlich fehlerhafte Tests/Scans; Produktionsfreigabe benötigt explizite Genehmigung.

### Phase 4 — Datenübernahme und Schattenbetrieb

1. Testmigration einer aktuellen, geschützten Kopie; keine produktiven Daten in CI.
2. Datenbankimport und Schema-/Counts-/Constraint-/TLS-Prüfung; zunächst keine geplanten Live-Snapshots ausführen.
3. Ein kontrollierter Fixture-Lauf auf VPS-Compose beweist Job, DB-Schreibpfad, strukturiertes Logging und idempotente Wiederholung.
4. Ein geplanter Login-/Snapshot-Live-Test ist nur nach Secret-/Egress-Freigabe, mit kontrollierter Wirkung und ohne parallelen AWS-Schreibjob auszuführen.
5. Go/No-Go: Backup/Restore, Testfälle in Abschnitt 7 und freigegebene Cutover-Checkliste sind vollständig grün.

### Phase 5 — Cutover und Beobachtung

1. AWS-EventBridge-Schedule kontrolliert pausieren; Zustand und letzten erfolgreichen Lauf dokumentieren.
2. Endgültigen konsistenten DB-Export bzw. Delta-Übernahme durchführen; Schreibstillstand, Import, Migrationstabelle und fachliche Counts prüfen.
3. VPS-Scheduler zunächst einmalig manuell starten, Resultat und DB-Änderung kontrollieren; erst danach systemd-Timer aktivieren.
4. Scheduler in den ersten sieben Tagesfenstern täglich prüfen: genau ein erwarteter Lauf, erfolgreicher Exitcode, Snapshot-/Marktwert-Fortschritt und keine Duplikate. AWS-Kapazitäten erst nach festgelegter Beobachtungs- und Rückfallfrist entfernen.
5. Rollback vor AWS-Abschaltung: VPS-Timer deaktivieren, parallele Writer vermeiden, Datenlage/Delta-Plan explizit prüfen, dann erst AWS-Writer wieder aktivieren. Nie zwei aktive Scheduler gleichzeitig.

### Phase 6 — API (separater Change)

API bleibt aus, bis alle folgenden Punkte gesondert abgenommen sind:

- File-backed Auth-Konfiguration und Proxy-Secret werden fail-closed geladen; Login-Limitierung, sichere Cookie-Attribute, JWT-Validierung und API-Proxy-Bearer-Check funktionieren unverändert.
- API hängt nur hinter HTTPS-Reverse-Proxy; Vercel-Proxy-Ziel, TLS, Host-/Forwarded-Header und exakt erlaubte Origins sind geprüft.
- Read-only DB-Rolle wird getrennt angelegt und Tests beweisen, dass Schreiboperationen verweigert werden.
- Health-/Readiness- und OpenAPI-Verhalten entsprechen dem Produktionsmodus; keine öffentlichen Debug-/Docs-Endpunkte oder direkte Uvicorn-Freigabe.
- Testfälle API-Auth in Abschnitt 7 bestanden und Release gesondert freigegeben.

## 7. Konkrete überprüfbare Testfälle

Die folgenden Tests sind Akzeptanzkriterien. Produktionscredentials werden hierfür nicht in Testausgaben oder Tickets übernommen.

| ID | Test / Durchführung | Erwartetes, überprüfbares Ergebnis |
|---|---|---|
| T01 | `python -m pytest backend/tests -q` (mit `PYTHONPATH=backend` gemäß Repository-Konvention) | Alle bestehenden Unit-/API-/Security-Tests bestehen. |
| T02 | PostgreSQL-16-Integrationstests mit isolierter Testdatenbank und `TEST_DATABASE_URL` | `pytest -m integration` besteht; Testdatenbank wird nach Ausführung nicht mit Produktionsdaten verwechselt. |
| T03 | In Produktion `APP_ENV=production`, `COMUNIO_REQUIRE_SECRET_MODE=true`, Datei fehlt, zusätzlich ENV-Fallback-Variablen gesetzt; Login-/Startpfad ausführen | Fail-closed: Exitcode ungleich null, keine ENV-Credentials verwendet; Ausgaben enthalten weder Credential noch Dateiinhalte. |
| T04 | Gültige Comunio-Secret-Datei mit Testwerten über injizierte Mock-/Fixture-Abhängigkeit laden | Nur erwartete Felder akzeptiert; keine Werte im Log; Datei wird nicht verändert. |
| T05 | Ungültiges JSON, fehlendes Passwortfeld, falsche Datei-Rechte und nicht vorhandene Secret-Datei testen | Kontrollierter Konfigurationsfehler vor Netzwerkaufruf; keine Fallback-Nutzung, kein Traceback mit Secretinhalt. |
| T06 | Secret-Redaction: repräsentative Login-, HTTP- und DB-Exceptions enthalten Testpasswort, Token, DSN, E-Mail und Antworttext | Captured Logs enthalten keine der sensitiven Testzeichenfolgen; nur erlaubter Fehlercode/Stage wird protokolliert. |
| T07 | `connect()` mit `sslmode=disable` und ohne SSL-Modus aufrufen | Verbindung wird vor psycopg2-Verbindungsaufbau abgelehnt. |
| T08 | PostgreSQL-TLS-Verbindung mit vertrauenswürdiger CA und korrektem Servernamen bzw. mit unbekannter CA/falschem Namen prüfen | Gültige `verify-full`-Verbindung besteht; beide Negativtests scheitern. |
| T09 | `docker compose config` mit synthetischen Platzhaltervariablen ausführen und Images bauen | Konfiguration gültig, Images reproduzierbar gebildet, kein Hostport für DB/API exponiert, kein Secret in Build-Kontext oder Image-Layern. |
| T10 | `docker inspect`/Compose-Config-/Image-Layer-Scan auf die Testumgebung anwenden | Es erscheinen nur Secret-Dateipfade, keine Secret-Inhalte, Passwörter oder DSNs. Produktive Werte dürfen in diesem Test nicht eingesetzt werden. |
| T11 | `docker compose up -d db`; auf Healthcheck warten; `migrations.runner` zweimal ausführen | DB wird gesund; erster Lauf wendet nur ausstehende Migrationen an; zweiter Lauf erzeugt keine Dubletten/Fehler; `schema_migrations` enthält jeden Dateinamen einmal. |
| T12 | Import einer Testdatenbank; Tabellen-/Constraint-/Zeilenanzahl vor und nach Export/Import vergleichen | Pflichtobjekte aus [AP-5/AP-6-Runbook](../../backend/OPERABILITY-AP5-AP6.md) vorhanden; kritische Counts und Unique-Constraints stimmen; keine unerwartete Datums-/Zeitzonenverschiebung. |
| T13 | Ingest mit `COMUNIO_SNAPSHOT_FILE` und nicht produktiven Fixtures einmal ausführen | Exitcode 0, erwartete Ereignisse `run_started`, `db_verify`, `run_success`, `records_written > 0`; keine echten Comunio-Zugangsdaten nötig. |
| T14 | Denselben Fixture-Snapshot am selben Tag zweimal einspielen | Keine doppelten `(player_id, snapshot_date)`-Marktwertzeilen; Upsert-/Unique-Constraint-Verhalten bleibt stabil; Counts entsprechen der definierten Idempotenz. |
| T15 | Comunio-Login-Mock schlägt zunächst fehl und danach erfolgreich; separater Test erschöpft alle Login-Versuche | Erfolgsfall nach erwarteter Zahl Versuche `login_recovered`, Exitcode 0; Erschöpfung liefert `run_failed stage=login`, Exitcode 1, und genau die konfigurierte Retryzahl. Test verwendet injizierte Sleep-Funktion, wartet nicht real 10 Minuten. |
| T16 | Snapshot-Mock mit transienten Fehlern und anschließendem Erfolg bzw. dauerhaftem Fehler | Erfolgsfall nach begrenztem Backoff; Erschöpfung beendet Job mit Exitcode 1 und sanitisiertem Fehler; keine unendliche Retry-Schleife. |
| T17 | systemd-Timer syntaktisch prüfen (`systemd-analyze verify`), Zeitpunkt mit UTC-Systemzeit und absichtlich verpasstem Termin testen | Nächster Lauf ist 06:00 UTC; `Persistent=true` verhält sich wie dokumentiert; nach verpasstem Termin läuft kein paralleler Doppeljob. |
| T18 | Zwei Scheduler-/manuelle Läufe gleichzeitig starten | Lock verhindert parallele DB-Schreibläufe; zweiter Lauf wird nachvollziehbar abgewiesen/übersprungen, erster Prozess wird nicht beschädigt. |
| T19 | systemd-Service mit absichtlich fehlerhaftem Image/DB-Verbindung starten | Nicht-null Exitcode wird im systemd-Status sichtbar und löst den definierten Alarm aus; kein Restart-Loop; keine sensiblen Details im Log. |
| T20 | Backup erstellen, Integrität prüfen, auf separater leeren PostgreSQL-16-Testinstanz wiederherstellen | Backup lesbar und entschlüsselbar im autorisierten Testkontext; Schemas, Migrationen und fachliche Counts stimmen; gemessene Wiederherstellungszeit liegt innerhalb des freigegebenen RTO. |
| T21 | DB-Container stoppen und neu starten; zusätzlich Host-Neustart in Staging simulieren | Persistentes Volume hält Daten; DB wird healthy; keine automatische Initialisierung überschreibt ein vorhandenes Volume. |
| T22 | API-Container im Standardprofil starten/auflisten | API wird nicht versehentlich aktiviert oder öffentlich gebunden. |
| T23 | (Nur API-Freigabe) Ohne Proxy-Bearer-Token, falsches Token, ohne/ungültige JWT-Session und mit gültiger Session testen | Ungültige Requests 401/403; gültige Proxy-/Session-Kombination erhält erwartete read-only Antwort; keine Auth-Fehlerdetail-Leaks. |
| T24 | (Nur API-Freigabe) DB-Zugriff über API-Rolle: `SELECT` plus versuchte `INSERT`-/`UPDATE`-Operation in isolierter Testumgebung | `SELECT` besteht; Schreibversuche werden von PostgreSQL verweigert. |
| T25 | HTTPS-Endpunkt und Weiterleitungen prüfen; HTTP-Aufruf, abgelaufenes Zertifikat-/falscher Host-Check in Staging | HTTP wird zu HTTPS umgeleitet oder abgelehnt; gültiges Zertifikat/Hostname vorhanden; keine Credentials über HTTP gesendet. |
| T26 | CI absichtlich mit fehlgeschlagenem Unit-Test, fehlerhaftem Compose, kritischem Containerfund bzw. Secret-Scanner-Testwert (nur Testmarker) ausführen | Release-Pipeline blockiert; Logs/Artefakte enthalten keine echten Credentials. |
| T27 | Freigegebene Version N deployen, Smoke-Test; danach N−1 Image-Digest zurücksetzen | Rollback auf vorheriges Image ist möglich; Datenbankänderungen werden nicht blind rückwärts migriert; Status wird protokolliert. |

**Schnittstellen-/Bestandsabnahme:** [OpenAPI-Contract-Test](../../backend/tests/test_openapi_contract.py), API-Tests und PostgreSQL-Integrationstests müssen zusätzlich in CI bestehen, auch wenn API zunächst deaktiviert bleibt. Bestehende Login-/Retry-/Idempotenz-Abnahmepunkte aus [AP-9-Runbook](../../backend/OPERABILITY-AP9.md) werden nicht durch bloße Container-Starttests ersetzt.

## 8. Sicherheits- und Funktionsanforderungen (nicht verhandelbar)

- Keine Secrets in Repository, Container-Layern, Terraform-Outputs, CI-Artefakten, Tickets, Befehlsargumenten oder Logs. Gitignore und Secret-Scanner für neue Secret-/Backup-/TLS-Pfade erweitern.
- Secret-Dateien ausschließlich root-beschränkt auf dem Host anlegen, nicht world-readable, read-only in nötige Container mounten und Rotationsprozess inklusive Dienstneustart/Cacheinvalidierung dokumentieren.
- Hostfirewall: nur notwendige öffentliche Ports (typischerweise HTTPS; SSH ausschließlich freigegebene Operatorzugänge und Quellen) offen. PostgreSQL-Port, Uvicorn und Managementports nicht öffentlich. Docker-Portfreigaben explizit kontrollieren; Firewall allein ist kein Ersatz für fehlende Compose-Portfreigabe.
- DB-TLS und HTTPS verpflichtend; Zertifikats- und Schlüsselrotation mit Tests. Keine Ingest-/API-DB-Verbindungen mit `sslmode=disable`.
- Ingest-DB-Rolle mit minimalen Schreibrechten, API-Rolle separat read-only, Host-/Compose-Administrationszugriff minimal. Kein dauerhafter Root-Prozess im Anwendungskontainer.
- API standardmäßig nicht verfügbar. Bei späterer Freigabe bleiben Vercel-Server-Proxy, Proxy-Token, Login-Session, Rate-Limit, CORS-Allowlist und HTTPS gemeinsam erforderlich; CORS allein ist kein Zugriffsschutz.
- SQL-Parametrisierung, Zeitreihen-Idempotenz, Snapshot-Retries, Login-Retry und klare Exitcodes dürfen nicht verändert oder abgeschwächt werden. Fachliche Counts und Snapshot-Datum gegen die AWS-Baseline vergleichen.
- Backups sind verschlüsselt, extern zum VPS gespeichert und regelmäßig wiederhergestellt. RPO/RTO, Retention und Restore-Verantwortung sind explizit zu dokumentieren.
- Einzel-VPS ist ein Single Point of Failure. Ein täglicher Backup-/Restore-Prozess verbessert Wiederherstellbarkeit, stellt aber weder automatische Hochverfügbarkeit noch 99,9-%-Uptime sicher. Abweichung zur Lastenheft-Anforderung muss akzeptiert oder durch Architekturmaßnahmen geschlossen werden.

## 9. Freigabekriterien / Definition of Done

- [ ] Secret-Provider für Contabo ist getestet, Produktionsmodus fail-closed und Log-Redaction belegt.
- [ ] PostgreSQL läuft isoliert, persistent, mit TLS-Validierung und getrennten Rollen.
- [ ] Migration/Import und Wiederherstellung sind in Testumgebung erfolgreich; Schema, Constraints und fachliche Counts sind abgeglichen.
- [ ] Compose, Docker-Härtung, systemd-Timer/Lock, UTC, Alarmierung und Logging sind automatisiert geprüft und dokumentiert.
- [ ] CI baut und scannt Ingest-/API-Images, testet Backend/PostgreSQL/Compose und verhindert Secrets sowie mutable Produktions-Tags.
- [ ] Backup wurde auf separater Testinstanz restored; RPO/RTO liegt im freigegebenen Rahmen.
- [ ] Kein paralleler AWS-/VPS-Writer; Cutover und Rollback sind als konkrete Operator-Schritte abgenommen.
- [ ] Sieben aufeinanderfolgende produktive Tagesfenster oder ein zuvor vereinbarter gleichwertiger Beobachtungsnachweis sind erfolgreich; keine doppelten Tagesmarktwerte.
- [ ] API ist weiterhin aus, bis der separate API-Freigabeumfang erfüllt ist.
- [ ] Restlücken — insbesondere Einzelserver-Verfügbarkeit, Secret-Manager-Auditierung und gegebenenfalls API-Aktivierung — sind ausdrücklich akzeptiert oder als Folgemaßnahme terminiert.

## 10. Entscheidungsprotokoll

1. **systemd-Timer statt Scheduler im App-Container:** Nutzt Ubuntu-Bordmittel, trennt Jobplanung von Anwendung, stellt Exitcodes/Logs bereit und lässt denselben Ingest-One-shot-Container wie heute laufen. Keine neue Scheduler-Abhängigkeit im Anwendungscode.
2. **Compose mit PostgreSQL im privaten Netz:** Passt zu Einzel-VPS-Betrieb und vorhandenem Docker-Image. Öffentliche DB-Ports und parallele Datenbankdienste werden vermieden; TLS bleibt dennoch verpflichtend.
3. **File-backed Secrets nur als expliziter Provider:** Entfernt AWS-Laufzeitabhängigkeit, ohne lokale ENV-Fallbacks in Produktion zu öffnen. Für höhere Audit-/Multi-Operator-Anforderungen ist ein dedizierter Secret-Manager statt Klartext-`.env` erforderlich.
4. **API separat und standardmäßig deaktiviert:** Bewahrt den aktuellen Sicherheitszustand; Migration des Ingests ist kein impliziter API-Go-live.
5. **Immutable Images plus genehmigter Rollout:** Erhält nachvollziehbare Releases und Rollback, ohne unkontrollierte CI-Root-Rechte auf dem VPS einzuführen.

## Quellen im Repository

- [Projektstatus und Gates](../../README.md)
- [Zielarchitektur](../../architecture.md)
- [Datenmodell](../../data_model.md)
- [Backend-Produktionskonfiguration](../../backend/src/config.py)
- [Ingest-Runner und Retry-Verhalten](../../backend/src/ingest/runner.py)
- [Comunio-Client und aktueller AWS-Secret-Zugriff](../../backend/src/ingest/comuniopy_client.py)
- [PostgreSQL-TLS-Verbindung](../../backend/src/database/connection.py)
- [API-Authentifizierung und Produktions-Gates](../../backend/src/api/auth.py), [API-App](../../backend/src/api/app.py)
- [Datenbankmigrationen](../../backend/migrations/)
- [Dockerfiles](../../backend/Dockerfile), [API-Dockerfile](../../backend/Dockerfile.api)
- [CI](../../.github/workflows/ci.yml)
- [AP-5/AP-6-Runbook](../../backend/OPERABILITY-AP5-AP6.md), [AP-7-Runbook](../../backend/OPERABILITY-AP7.md), [AP-9-Scheduler-Runbook](../../backend/OPERABILITY-AP9.md)
- [AWS-Baseline und API-Status](../../infra/aws/README.md)
- [Nicht-funktionale und Sicherheitsanforderungen](../../Lastenheft_Comunio_Projekt.md)
- [Historischer Security-Review (Stichtag beachten)](../code-review/2026-08-25-full-project-security-review.md)
