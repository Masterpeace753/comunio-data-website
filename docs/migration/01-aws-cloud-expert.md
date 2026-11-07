# Migrationsplan: AWS nach Contabo Ubuntu

**Ziel:** Die in diesem Repository dokumentierte Comunio-Datenplattform kontrolliert von AWS auf einen Contabo-Ubuntu-VPS umziehen. Dieser Plan beschreibt Vorbereitung, Datenübernahme, Scheduler, Schnittstellen, Cutover und Rückfall. Er führt keine Migration aus.

> **Sicherheitsgrenze:** Bei der Erstellung dieses Plans wurden weder AWS-Ressourcen noch produktive Daten verändert und keine SSH-Verbindung aufgebaut. Zugangsdaten, Secret-Inhalte, echte Datenbank-URLs und produktive Daten gehören nicht in dieses Dokument, Tickets, Shell-Historie oder Logs.

## 1. Befund aus dem Repository

### Produktivpfad und Abhängigkeiten

- Die dokumentierte Ingest-Strecke ist **EventBridge-Regel → ECS/Fargate-Aufgabe → PostgreSQL RDS**. Die Aufgabe startet `python -m src.ingest.runner --run-type scheduled --mode snapshot`; EventBridge hat zwei Zustellversuche und eine SQS-DLQ. Die Repository-Dokumentation nennt den täglichen Lauf um **06:00 UTC**. Terraform hat dieselbe Uhrzeit als Schedule-Ausdruck, aber `enable_schedule` standardmäßig **false**. Ob der produktive Zeitplan aktuell aktiviert ist, ist aus dem Repository nicht verifizierbar.
- Der Ingest liest Comunio-Zugangsdaten wahlweise aus **AWS Secrets Manager** (`boto3`, `AWS_REGION`, `COMUNIO_SECRET_NAME`) oder aus Umgebungsvariablen. In Produktion verlangt die Konfiguration Secret-Modus. Die DB-Verbindung verlangt TLS (`sslmode=require` oder stärker).
- Terraform beschreibt **RDS PostgreSQL**, nicht dessen tatsächlich ausgerollte Größe oder Zustand. Verschlüsselung, private Subnetze, Backups, Löschschutz und optional Multi-AZ sind konfigurierbar. Der DB-Engine-Major, Datenvolumen, RDS-Parameter, aktuelle Backup-Frist und Ist-Konfiguration müssen vor Umsetzung aus der autoritativen AWS-Konfiguration verifiziert werden.
- Die FastAPI ist im README und in `terraform.tfvars.example` als **deaktiviert** dokumentiert (`api_enabled = false`); der AWS-Runbook-Text enthält zugleich eine spätere CloudFront-/internen-ALB-Zielkonfiguration, die laut Runbook nicht angewendet wurde. Der aktuelle API-Produktivstatus und Frontend-Go-live sind deshalb **ungeklärt**. Nicht aus einer Dokumentationsnotiz auf einen laufenden Endpoint schließen.
- Wenn aktiviert, ist die API eine ECS/Fargate-Aufgabe hinter internem ALB und CloudFront. Die Anwendung benötigt eine separate schreibgeschützte DB-Rolle, API-Proxy-Secret und Auth-Secret. Die Authentifizierung lädt das Secret direkt aus Secrets Manager; der Proxy-Token wird als Env-Secret gesetzt. `CloudFront-Viewer-Address` wird für Login-Drosselung ausgewertet.
- Das Frontend ist Next.js und laut README auf Vercel; sein Server-Proxy verwendet `NEXT_PUBLIC_API_BASE_URL` und optional `API_PROXY_SECRET`. Die Vercel-Umgebung ist kein AWS-Infrastrukturteil, muss aber beim API-Umzug gezielt auf die neue API-Adresse umgestellt werden.
- DB-Schema-Migrationen liegen als nummerierte SQL-Dateien vor. Tabellen umfassen Teams, Spieler, Ingest-Läufe, Marktwerte, Punkte, Transfermarkt-Snapshots, Ereignisse und Audit-Log. Der Runner verfolgt ausgeführte Dateien in `schema_migrations`.

### Zentrale Quellen (Repository-relative Links)

- [AWS-Baseline und API-Status](../../infra/aws/README.md)
- [Terraform-Hauptkonfiguration: ECS, IAM, Logs, Scheduler, DLQ und Alarme](../../infra/aws/terraform/main.tf)
- [RDS, SG-Regeln und DB-Secret](../../infra/aws/terraform/database.tf)
- [Schedule-, Netzwerk- und Engine-Variablen](../../infra/aws/terraform/variables.tf)
- [CloudFront/API-Ingress](../../infra/aws/terraform/cloudfront.tf)
- [Beispiel-Terraform-Eingaben](../../infra/aws/terraform/terraform.tfvars.example)
- [AWS-Konfigurations- und Bereitstellungsnotizen](../../infra/aws/README.md)
- [Backend-Umgebungsvariablen-Beispiel](../../backend/.env.example), [Settings](../../backend/src/config.py), [DB-Verbindung/TLS-Prüfung](../../backend/src/database/connection.py)
- [Ingest-Runner und Retry-Verhalten](../../backend/src/ingest/runner.py), [Comunio-Client/Secrets-Manager-Lesezugriff](../../backend/src/ingest/comuniopy_client.py)
- [Snapshot-Transaktionen und Upserts](../../backend/src/ingest/snapshot_job.py)
- [Migration-Runner](../../backend/migrations/runner.py), [Schema 001](../../backend/migrations/001_core_tables.sql), [Schema 002](../../backend/migrations/002_timeseries_tables.sql), [Schema 003](../../backend/migrations/003_events_audit_tables.sql)
- [API und Health-Endpunkte](../../backend/src/api/app.py), [API-Auth/Secrets Manager](../../backend/src/api/auth.py), [Read-only-Rollen-Provisionierung](../../backend/src/ops/provision_api_readonly_user.py)
- [Frontend-Env-Beispiel](../../frontend/.env.example), [Daten-Proxy](../../frontend/app/api/proxy/%5B...path%5D/route.ts), [Auth-Proxy](../../frontend/app/api/auth/%5B...path%5D/route.ts)
- [Datenbank-Export-Skript](../../scripts/aws/export-db.ps1) und [AWS-Runbook](../../backend/OPERABILITY-AP9.md)

## 2. Zielbild auf Contabo

Für den aktuellen Umfang ist ein einzelner Ubuntu-VPS die kostengünstige Zielvariante, aber er ersetzt nicht die Verfügbarkeits- und Managed-Services-Eigenschaften von RDS/ECS. Vor dem Umzug CPU/RAM, Disk, DB-Volumen und Wachstum messen und VPS-Größe danach dimensionieren. Für eine einzelne Maschine besteht ein gemeinsamer Ausfallbereich für API, Scheduler und Datenbank; falls dies nicht akzeptabel ist, PostgreSQL als separaten Managed-Dienst oder einen zweiten VPS vorsehen.

Vorgeschlagene Zuordnung:

| Heute (Repository/AWS) | Ziel |
|---|---|
| RDS PostgreSQL | PostgreSQL auf Ubuntu, nur lokal oder privatem Netzwerk erreichbar; Daten-Disk und verschlüsselte externe Backups |
| ECS/Fargate API (falls wirklich aktiv) | Backend-API als nicht-root Container oder systemd-Dienst hinter Nginx/Caddy; TLS am öffentlichen Reverse-Proxy |
| EventBridge → ECS-Aufgabe | systemd-Timer oder Cron startet einen **einmaligen** Container/Prozess mit explizitem Exit-Code |
| Secrets Manager/Task-Secret-Injection | root-geschützte Environment-Datei/Secret-Datei oder systemd Credentials; nie im Image, Git, Logs oder Prozessargumenten |
| CloudWatch Logs/Alarme/SNS | journald mit begrenzter Retention sowie externe Verfügbarkeits-/Fehleralarme und Backup-Monitoring |
| ECR | lokale Image-Builds oder private Registry; unveränderlichen Commit-Tag/Release verwenden |
| CloudFront/internes ALB | öffentlicher Reverse-Proxy mit HTTPS; API-Origin nur HTTPS von Vercel erreichbar, sofern der Browser nicht direkt zugreift |

Auf Ubuntu mindestens zeitnahe Sicherheitsupdates, SSH nur mit Schlüsseln und restriktiver Quell-IP, Firewall mit nur benötigten Ports (typisch 22 eingeschränkt, 80/443 öffentlich; PostgreSQL-Port **nicht** öffentlich), unprivilegierte Dienste, TLS, Fail2ban oder gleichwertige Schutzmaßnahmen, Monitoring von Speicherplatz/DB/Prozessen und dokumentierte Wiederherstellung einrichten. Diese Details sind Zielvorgaben, keine im Repository vorhandene Contabo-Konfiguration.

## 3. Migrationsphasen und Abnahmepunkte

### Phase A – Inventur und Freigabe (vor Änderungen)

1. Über einen autorisierten Operator-Prozess (nicht im Rahmen dieses Plans) Ist-Zustand feststellen: AWS-Region, aktive EventBridge-Regel/Zeitzone, letzte erfolgreiche Läufe und DLQ, ECS-Task-Image/Commit, API-Status/URL, tatsächliche RDS-Version und -Größe, Tabellenzeilen/-größen, DB-Rollen, Backup-Retention, Secrets und Vercel-Produktionsvariablen. Secret-Inhalte niemals ausgeben.
2. Repo-Revision und Image-Tag festhalten; alle laufenden AWS-Jobs und möglichen manuellen Aufrufe identifizieren. Herausfinden, ob API und Ingest dieselbe DB verwenden und welche Vercel-Projekte/Preview-Deployments die API aufrufen.
3. Ziel-Ubuntu, PostgreSQL-kompatible Version, verfügbaren Speicher inkl. temporärem Dump, DNS-Änderungsmöglichkeit, Backupziel außerhalb des VPS, Wartungsfenster, RPO/RTO und Verantwortliche bestätigen.
4. Zieldatenbank zunächst mit gleichen oder kompatiblen PostgreSQL-Major-Versionen wie RDS betreiben. Ein Major-Upgrade ist ein separates, getestetes Vorhaben. TLS muss für API und Ingest kompatibel mit der bestehenden `sslmode`-Validierung bleiben.
5. Zugangsdaten für Comunio, Datenbank, API-Proxy und API-Login über einen Secret-Manager des Betreibers bzw. sichere Deployment-Mechanismen neu bereitstellen/rotieren. Keine Secrets aus AWS-State, Terraform-Outputs oder alten Logs in ein Repo übernehmen.

**Gate A:** Ist-Zustand, Wartungsfenster, Rückfall-Verantwortung, getestetes externes Backup und vollständige Anwendungsliste sind bestätigt. Bei unklarer Datenbankversion, aktivem Scheduler oder unbekannter API-Adresse nicht weiter zum Cutover.

### Phase B – Zielsystem vorbereiten

1. Ubuntu absichern und überwachen. Backups verschlüsselt, mit begrenztem Zugriff und außerhalb des VPS ablegen; mindestens tägliche DB-Sicherung, Aufbewahrung und regelmäßigen Restore-Test einrichten.
2. PostgreSQL anlegen, Netzwerkzugriff auf lokale Dienste bzw. explizite vertrauenswürdige Clients begrenzen, TLS konfigurieren. Rollen trennen: Ingest mit benötigten Schreibrechten; API mit nur den `SELECT`-Rechten, die `provision_api_readonly_user.py` vorsieht. Kein Superuser in App-DSNs.
3. Backend exakt aus freigegebener Repo-Revision bauen. Vorab CI-/Backendtests und Container-Health-Check ausführen. Für API `GET /health/live` und `GET /health/ready` prüfen; `/health/ready` bestätigt DB-Verbindung.
4. Ohne live Comunio-Aufruf zunächst Schema in einer leeren Ziel-DB mittels `python -m migrations.runner` anwenden und die Tabellen/`schema_migrations` verifizieren. Im eigentlichen Restore wird das Schema dagegen aus dem Dump wiederhergestellt – nicht unbedacht ein zweites Mal parallel initialisieren.
5. API optional zunächst nur privat oder für einen begrenzten Testzugriff starten. Vercel-Zugriff über HTTPS testen; gültige Origin-Whitelist (`API_ALLOWED_ORIGINS`), Proxy-Token, sichere Session-Cookies und Login/Logout testen. Keine Auth-/DB-Secrets im Browser veröffentlichen.

### Phase C – RDS-Daten exportieren und importieren

**Bevorzugt: konsistenter nativer PostgreSQL-Dump** mit `pg_dump` in Custom-Format (`-Fc`) von RDS über einen autorisierten, TLS-gesicherten Zugriff. Den Dump in ein verschlüsseltes, zugriffsbeschränktes temporäres Verzeichnis/Transferziel schreiben. Keine SQL-Daten in Shell-Variablen oder CloudWatch-Logs streamen. Für Übernahme von Eigentümern/Rechten ggf. Globals/Rollen getrennt und geprüft behandeln; üblicherweise Anwendungsschema mit `--no-owner --no-acl` restaurieren und Zielrollen separat einrichten. Rollen-Export kann Passworthashes enthalten und ist besonders geschützt aufzubewahren.

1. Zunächst einen Probedump und Restore in eine leere Staging-DB durchführen, solange AWS unverändert bleibt. Größen, Tabellen, Constraints, Indizes, Sequenzen, Migrationseinträge, Sonderzeichen/JSONB und Zeitzonen kontrollieren.
2. Für den produktiven Dump entscheiden, ob kurzes Schreib-Freeze genügt (empfohlen bei dieser offenbar niedrigvolumigen Snapshot-Anwendung) oder ob ein separates getestetes CDC-Verfahren benötigt wird. Ein normaler Dump ist ein Snapshot, keine laufende Synchronisation.
3. Beim Freeze Ingest-Scheduler und manuelle Ingest-Aufrufe stoppen, laufende Task vollständig beenden lassen, anschließend finalen Dump erzeugen. Falls API aktiv ist, sie während der Datenkopie in Wartungs-/Read-only-Modus bringen; im Repo ist die API ohnehin als Read-only beschrieben. Prüfen, dass kein anderer Prozess DB-Schreibzugriff hat.
4. Auf Ubuntu Ziel-DB leeren/neu anlegen, Dump mit `pg_restore` einspielen. Bei Bedarf Schema/Objekte nach Fehlern in Staging korrigieren, nicht durch unkontrolliertes Überspringen von Fehlern. `schema_migrations` und alle enthaltenen Tabellen müssen konsistent sein.
5. Post-Restore `ANALYZE` ausführen und Sequenzwerte prüfen/auf Maximum der jeweiligen ID-Spalte setzen, damit spätere BIGSERIAL-Inserts nicht mit bestehenden IDs kollidieren. Anzahl Zeilen je Tabelle und repräsentative fachliche Abfragen gegen vorher notierte Quellwerte vergleichen; keine produktiven Datensätze in Logs oder Dokumentation kopieren.
6. Backend-Migration-Runner gegen die restaurierte Ziel-DB ausführen. Erwartung: keine bereits angewandte Migration wird erneut ausgeführt und das Schema bleibt unverändert. Integrationstests gegen Test-DB, dann Readiness-/API-Checks durchführen.
7. Erst nach fachlicher Abnahme und erfolgreichem Restore-Test die Exportdatei und lokale Kopien sicher löschen. Quelldaten/Backups entsprechend Aufbewahrung schützen.

**Wichtiger Hinweis zum vorhandenen Export-Skript:** `scripts/aws/export-db.ps1` ist **kein** sicherer oder robuster Migrationsweg: es sammelt alle Tabelleninhalte in Python, gibt SQL und JSON in die ECS-Task-Logs aus und schreibt daraus rekonstruierte Dumps; das erzeugt zusätzliche Kopien sensitiver Daten in CloudWatch-Logs, kann Größen-/Loglimits treffen und bildet z. B. Rollen/ACLs nicht vollständig ab. Dieses Skript für den Produktivexport nicht verwenden. Einen getesteten nativen `pg_dump`/`pg_restore`-Prozess wählen.

**Gate C:** Quell-/Ziel-Zeilenanzahlen, Constraints, Sequenzen, Migrationen und fachliche API-Abfragen stimmen überein; Restore und Health-Checks sind erfolgreich; es läuft noch kein Ziel-Scheduler.

### Phase D – Scheduler und Schnittstellen umstellen

#### Scheduler

- Den EventBridge-Takt in Ubuntu explizit abbilden. Die Repo-Dokumentation sagt 06:00 UTC täglich. Ubuntu/systemd verwendet normalerweise lokale Systemzeit; daher Host auf UTC setzen oder den Timer mit klar ausgewiesener Zeitzone konfigurieren und Sommerzeitverhalten testen. Nicht allein die Terraform-Default-Zeit als Ist-Zustand annehmen.
- Der Timer startet `python -m src.ingest.runner --run-type scheduled --mode snapshot` im richtigen Arbeitsverzeichnis/Container. Secret- und DB-Umgebung nur zur Laufzeit injizieren. `flock` oder systemd-`Conflicts` verhindert überlappende Läufe; Job muss auch bei Fehlern mit Exit-Code ungleich null enden und Logs mit Laufstart/-ende, Dauer, Erfolgsstatus und Datensatzanzahl erzeugen, ohne Exception-Inhalte/DSNs/Tokens zu loggen.
- Fehlende EventBridge-Retry/DLQ-Abdeckung ersetzen: Alarm auf fehlgeschlagenen/ausgebliebenen Lauf, externe Benachrichtigung, begrenzte Retry-Strategie, dokumentierte manuelle Wiederholung und ein persistenter Alarm-/Run-Verlauf. App-eigene Login-Retries sind 3 Versuche im Abstand von 300 Sekunden; Snapshot-Fetch hat Backoff 2/4/8 Sekunden. Das sind keine Scheduler-Retries und können die Laufdauer verlängern.
- Zielzeitplan zunächst deaktiviert lassen. Erst nach abgeschlossenem DB-/API-Test genau einen Scheduler aktivieren; AWS/EventBridge davor deaktivieren, um Doppelabrufe und konkurrierende Upserts zu vermeiden.

#### API und Frontend

- Wenn die API aktuell produktiv verwendet wird, eine neue HTTPS-Adresse unter der tatsächlichen API-Domain bzw. einem freigegebenen DNS-Namen aufsetzen, Zertifikat erneuern und Vercel serverseitigen Origin umstellen (`NEXT_PUBLIC_API_BASE_URL`). `API_PROXY_SECRET` auf beiden Seiten sicher und identisch konfigurieren; bei Neuvergabe kontrolliert rotieren.
- API-Endpunkte und Frontend-Proxy-Pfade beibehalten: `/health/live`, `/health/ready`, `/auth/login`, `/auth/me`, `/auth/logout`, `/api/v1/...`. `GET`-/`POST`-Verhalten, Query-Strings, Cookies und `Set-Cookie`-Weitergabe prüfen. Der API-Proxy verwendet 8-Sekunden-Timeout und `cache: no-store`; der API-Endpunkt darf keine Authentifizierungsantworten cachen.
- Die aktuelle API-Anwendung nutzt AWS Secrets Manager direkt über `boto3` für `AUTH_SECRET_ARN`; der Comunio-Client nutzt ihn für `COMUNIO_SECRET_NAME`. Nur eine korrekte Env-Änderung genügt nicht: vor AWS-Abschaltung entweder diese Lesezugriffe auf einen Secret-Provider ohne AWS umstellen oder die entsprechenden Secret-Variablen/Dateien sicher zur Laufzeit bereitstellen. `APP_ENV=production` erzwingt Secret-Modus für Ingest und setzt API-Anforderungen an Auth/Proxy voraus.
- API-Auth nutzt `Secure`, `HttpOnly`, `SameSite=Strict` Cookies. Browserzugriff verlangt HTTPS. Der Login-Throttle ist pro Prozess im Speicher; mehrere Worker oder Neustarts umgehen die gemeinsame Grenze. `CloudFront-Viewer-Address` ist AWS-spezifisch; ohne vertrauenswürdigen Proxy darf kein beliebiger Client-Header als IP-Vertrauen dienen. Hinter Reverse-Proxy ausschließlich vom Proxy gesetzte Client-IP-Header akzeptieren und Proxy-Header-Behandlung passend konfigurieren; Throttling idealerweise gemeinsam/persistent lösen.
- `API_ALLOWED_ORIGINS` exakt auf die reale Frontend-Origin begrenzen. Nicht unbedacht `*` oder die ALB-/VPS-IP in Vercel setzen. Prüfen, ob Preview-/Staging-Deployments Zugriff benötigen.

**Gate D:** Es gibt nur einen aktiven Scheduler; Zieljob läuft erfolgreich; API (falls aktiv) und Frontend funktionieren unter HTTPS inkl. Login, Cookies, CORS und repräsentativen Listen-/Detail-/Historie-Abfragen.

## 4. Sicherer Cutover-Ablauf

1. Freigabe und Kommunikationsfenster festlegen; letzten erfolgreichen AWS-Ingest, Quelldatenbank-Snapshot/Backup und Restorepfad bestätigen. Bestehende AWS-Ressourcen zunächst ausdrücklich **nicht löschen**.
2. Zielsystem vorbereiten, Probelauf und Restore nachweisen. AWS-Zeitplan bis zum angekündigten Freeze aktiv lassen, danach AWS-EventBridge-Regel deaktivieren und prüfen, dass keine bereits gestartete ECS-Aufgabe mehr schreibt. Keine manuelle AWS-Aufgabe während der Sperre starten.
3. Falls Datenbank exportiert wird: Schreibzugriffe sperren, finalen konsistenten RDS-Dump ziehen, Ziel wiederherstellen und Validierung aus Gate C wiederholen. Die AWS-DB bis Ende der Beobachtungsphase als unveränderte Rückfallquelle halten.
4. Ziel-App mit AWS-Job noch deaktiviert starten. Readiness und API prüfen. Vercel-Umgebungsvariable auf neue HTTPS-API setzen, Deploy abschließen; bei eigener Domain DNS mit niedriger TTL vorab planen. Falls Domain/Frontend auf Vercel verbleibt, ist nur der API-Origin umzustellen, nicht das Frontend selbst.
5. Nach DNS-/Origin-Prüfung und Funktionstest ausschließlich den Ziel-Scheduler aktivieren. ersten Lauf beobachten, DB-Run-Status und Änderungs-/Zeilenmetriken prüfen. Wegen `market_values`-Upsert auf `(player_id, snapshot_date)` können Wiederholungen am selben Tag Werte aktualisieren; gleichzeitige Jobs trotzdem unterbinden.
6. Für vereinbartes Beobachtungsfenster (mindestens mehrere Scheduler-Zyklen oder explizit verkürzte Abnahme) AWS-Dienste, Datenbank und Backups weiterlaufen lassen. Änderungen an Ziel-DB in der Beobachtungsphase dokumentieren; danach ist AWS-Rückkehr nicht automatisch ohne Datenverlust möglich.

## 5. Rückfallplan

### Auslöser

DB-Prüfsummen/Counts nicht plausibel, Migrationen/Sequenzen fehlerhaft, Zieljob mehrfach fehlgeschlagen, API nicht stabil/readiness rot, Auth/Cookie/CORS defekt, Datenaktualität verletzt oder Zielsystem nicht sicher erreichbar.

### Rückfall, solange Ziel noch keine exklusiven neuen Daten erzeugt hat

1. Ziel-Scheduler sofort deaktivieren und laufenden Job beenden; Ziel-API auf Wartungsmodus/keine neuen Zugriffe setzen.
2. API-Origin/DNS/Vercel-Variable auf den zuvor verifizierten AWS-HTTPS-Pfad zurückstellen. **Nur** einen tatsächlich funktionsfähigen, authentifizierten AWS-Endpunkt nutzen; ein historischer HTTP-ALB ist laut AWS-Runbook unsicher und darf keine Tokens/Cookies erhalten.
3. AWS-EventBridge-Schedule kontrolliert wieder aktivieren, nachdem geprüft wurde, dass kein AWS-Lauf überlappt. AWS-RDS-Stand vor Cutover als maßgebliche Datenbank verwenden. Smoke-Test, dann Rückfall kommunizieren.
4. Zielserver und exportierte Dumps unverändert sichern, Fehlerursache untersuchen und mit neuer Freigabe erneut planen.

### Rückfall nach Ziel-Schreibzugriff

AWS-RDS und Contabo-DB sind dann auseinander gelaufen. Nicht einfach DNS zurücksetzen und AWS-Scheduler starten: neu erzeugte Ziel-Snapshots könnten fehlen, gleiche Tageswerte könnten voneinander abweichen und IDs/Run-Historie ebenfalls. Zielschreibzugriffe stoppen, beide Datenbanken geschützt sichern, Differenz fachlich und tabellenweise abgleichen. Entscheiden zwischen kontrolliertem Forward-Fix, erneutem finalen Export/Import zurück nach AWS oder akzeptiertem Verlust seit Cutover. Erst nach Validierung genau eine DB als führend festlegen und genau einen Scheduler aktivieren. Das ist ein manuelles Datenrecovery, kein automatisches Rollback.

**Rückfallbedingung:** AWS-DB, Taskdefinition/Image, Secrets und Infrastruktur nicht abbauen, bevor Cutover abgenommen, Daten-Retention entschieden und ein Wiederherstellungsplan getestet wurde. Terraform nicht unüberlegt anwenden: Konfigurationsänderungen sind nicht gleich tatsächlicher AWS-Status, und `terraform destroy` ist kein Rückfallmechanismus.

## 6. Prüfung, Betrieb und Abschluss

- Vor Produktivfreigabe: Backendtests (`pytest`), PostgreSQL-Integrationstests, `migrations.runner`, API-Healthchecks, TLS-Prüfung, Vercel-Proxy-Tests, Auth-Tests und ein kontrollierter Ingest-Test mit anschließendem DB-Abgleich.
- Im Betrieb überwachen: Erfolg/Alter des letzten Ingests, Laufzeit/Exit-Code, DB-Verbindung und -Speicher, Disk-Schwellen, HTTP-5xx/Latenz, Login-Fehler, TLS-Zertifikatsablauf, Backup-Erfolg und regelmäßigen Restore-Test.
- AWS-Kosten erst nach stabiler Zielphase reduzieren. Danach AWS-Scheduler deaktivieren lassen; ECS/ECR/CloudWatch/SQS/Secrets/CloudFront/RDS/Netzwerkressourcen einzeln anhand Ist-Nutzung und Retention abbauen. Terraform-State und Backups geschützt archivieren; nicht mehr benötigte Secrets nach Freigabe rotieren/widerrufen. Kein pauschales Löschen aller AWS-Ressourcen.

## 7. Annahmen und Unsicherheiten

1. **Ist-Infrastruktur wurde nicht abgefragt.** Terraform-Dateien und Markdown beschreiben Soll-/frühere Zustände; AWS-API, Terraform-State und Logs wurden für diesen Plan nicht untersucht. Aktivierte Dienste, Schedule, tatsächliche RDS-Version/-Größe, Datenvolumen und Endpoint sind daher unbestätigt.
2. README nennt aktive tägliche ECS-Aufgabe um 06:00 UTC und RDS, während Terraform-Defaults den Scheduler deaktivieren. Maßgeblich ist der freigegebene Ist-Zustand, nicht einer dieser Textwerte allein.
3. API-Status ist widersprüchlich: Haupt-README/Terraform-Beispiel sagen deaktiviert; AWS-Runbook beschreibt eine CloudFront-Zielkonfiguration und frühere API-Tests. Ob Nutzer oder Vercel aktuell einen Dienst verwenden, muss vor dem Umzug geklärt werden.
4. Es gibt im Repository keine Contabo-/Ubuntu-Zielkonfiguration, keine aktuelle Backupgröße und keinen nachgewiesenen nativen RDS-Dump/Restore. Ressourcenbedarf, Laufzeiten, Datenübertragungsdauer, Kosten und RPO/RTO können daher nicht seriös beziffert werden.
5. Annahme für den Basisplan: Datenvolumen erlaubt Wartungsfenster und konsistenten finalen Dump/Restore. Falls dies nicht zutrifft, ist ein getesteter PostgreSQL-Replikations-/CDC-Plan erforderlich; Replikation wird hier nicht als vorhanden vorausgesetzt.
6. Secrets werden nicht inventarisiert oder kopiert. Vor dem Cutover müssen Secret-Inventar, Rotationen und Zugriff durch zuständige Betreiber sicher erfolgen, ohne Werte offenzulegen.
7. DNS-Anbieter, Domainkontrolle, Vercel-Projekt/Variablen und Status des Frontends sind nicht aus einer ausführbaren Umgebung verifiziert.

