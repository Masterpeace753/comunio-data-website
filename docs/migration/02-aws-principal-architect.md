# AWS-Principal-Architect-Plan: Migration nach Contabo Ubuntu

**Zweck:** kontrollierter Wechsel des Backend- und Datenbankbetriebs von AWS auf einen Ubuntu-VPS bei Contabo. Das Vercel-Frontend bleibt zunächst bestehen.
**Status:** Architektur- und Ablaufplan, keine Ausführung. Repository-Stand geprüft am 07.11.2026.
**Sicherheitsgrenze:** Dieses Dokument enthält keine Zugangsdaten. Es wurden weder Deployments noch SSH-Verbindungen oder Änderungen an AWS vorgenommen.

## 1. Befundlage

### Ist-Zustand laut Repository

- Die Anwendung persistiert historisierte Comunio-Snapshots in PostgreSQL; der Ingest ist ein Python-Container, die API eine separate FastAPI-Anwendung. Das Frontend ist eine Next.js-Anwendung auf Vercel. Siehe [Architektur](../../architecture.md), [Backend-Überblick](../../backend/README.md) und [Frontend-Verzeichnis](../../frontend/).
- Die AWS-Terraform-Baseline beschreibt ECS/Fargate, ECR, einen EventBridge-Schedule, SQS-DLQ, CloudWatch-Logs/Alarme, Secrets Manager und optionales RDS in einer VPC. Die Beispielkonfiguration nutzt `eu-central-1`, aktiviert den Schedule zunächst nicht und setzt `db_backup_retention_days = 1`. Das ist ein Beispielwert, kein Beleg für Live-Konfigurationen. Siehe [AWS-README](../../infra/aws/README.md), [Terraform-Variablen](../../infra/aws/terraform/variables.tf) und [DB-Ressource](../../infra/aws/terraform/database.tf).
- Das Schema besteht aus `teams`, `players`, `ingest_runs`, `market_values`, `player_points`, `transfermarket_snapshots`, `availability_events`, `audit_log` sowie `schema_migrations`. Fachliche Eindeutigkeit wird u. a. durch Constraints auf Spieler-/Team-IDs und `(player_id, snapshot_date)` gestützt. Siehe [SQL-Migrationen](../../backend/migrations/).
- Ingest-Snapshots sind idempotent angelegt: Tageswerte werden bei erneutem Lauf über `(player_id, snapshot_date)` aktualisiert. Der Scheduler-Runbook dokumentiert die tägliche Ausführung um 06:00 UTC, Login-Retries, EventBridge-Retries und DLQ. Siehe [AP-9-Runbook](../../backend/OPERABILITY-AP9.md) und [Snapshot-Persistenz](../../backend/src/ingest/snapshot_job.py).
- Die API ist laut Dokumentation deaktiviert. Terraform enthält neuere CloudFront-/internen-ALB-Konfigurationen, die laut [AWS-README](../../infra/aws/README.md) noch nicht angewendet wurden; ältere API-Endpunktangaben sind ausdrücklich kein Live-Statusnachweis. API-Verfügbarkeit und produktive Routing-Konfiguration sind vor der Migration unabhängig zu verifizieren.
- Terraform enthält Einstellungen für RDS-Verschlüsselung, private Erreichbarkeit, Aufbewahrung, Multi-AZ und Löschschutz. Ob/wie diese Parameter in AWS tatsächlich gesetzt sind, ist aus eingechecktem Code nicht ableitbar. Der S3-State-Backend-Code beschreibt Versionierung und Verschlüsselung, belegt aber nicht den aktuellen Zustand des AWS-Kontos. Siehe [State-Konfiguration](../../infra/aws/terraform/state_backend.tf) und [S3-Backend](../../infra/aws/terraform/backend.tf).

### Annahmen und offene Nachweise

Vor Freigabe müssen Verantwortliche mindestens folgende Punkte bestätigen:

1. Tatsächlich aktive AWS-Ressourcen, Region, AWS-Konto, laufende Kosten und aktuelle Terraform-State-Version.
2. Contabo-VPS-Produkt, Ubuntu-LTS-Version, CPU/RAM/SSD, öffentliche IP, Firewall, physischer Standort und Verfügbarkeit externer/offsite Backups.
3. Datenbankgröße, tägliches Wachstum, aktuelle PostgreSQL-Hauptversion, Erweiterungen, Encoding, Collation und Zeitzone.
4. Ob produktive API-Nutzer existieren, welcher API-Hostname aktuell im Vercel-Server-Proxy gesetzt ist und ob Vercel unverändert außerhalb des Migrationsumfangs bleibt.
5. Verbindliche RTO/RPO, zulässiges Wartungsfenster, Datenaufbewahrung, Datenschutz-/Compliance-Anforderungen und Budget.

Die dokumentierten 99,9 % Verfügbarkeit und Ladezeit unter 2 Sekunden sind Projektziele, kein Nachweis der erreichten Betriebs-SLOs ([Architektur, NFR](../../architecture.md)). Für einen einzelnen VPS ist 99,9 % ohne redundanten Host, getesteten Failover und unabhängige Netzwerk-/Storage-Redundanz **nicht** als zugesichert anzunehmen.

## 2. Entscheidungen für die Planung

Diese Empfehlungen sind Zielentscheidungen, vorbehaltlich der offenen Nachweise:

- **Migrationsumfang:** Datenbank und Backend-Runtime wechseln zu Contabo Ubuntu; Vercel bleibt bestehen. Kein paralleler Schreibbetrieb. Keine Schema- oder Featureänderungen im selben Cutover.
- **Datenbank:** PostgreSQL bleibt PostgreSQL; Version und Erweiterungen auf dem Ziel sind zunächst kompatibel zur Quelle. Datenübernahme per konsistentem `pg_dump`/`pg_restore` im Custom-Format, nicht durch Kopieren eines laufenden Datenverzeichnisses.
- **Wahrheit der Daten:** Vor Cutover ist AWS die schreibende Quelle. Nach dem finalen Import und expliziter Freigabe wird Contabo alleinige schreibende Quelle. AWS bleibt während der Rückfallfrist unangetastet und ohne Ingest-Schreibzugriff.
- **VPS-Sicherheitsgrenze:** PostgreSQL nur lokal bzw. über ein privates, explizit freigegebenes Netz erreichbar; keine öffentliche DB-Freigabe. API nur über TLS-Reverse-Proxy, Ubuntu-Sicherheitsupdates, restriktive Host-Firewall, nicht-root Runtime, minimale Rechte und geschützte Secrets. Keine Secrets in Images, Git, Logs oder Terraform-Variablen/State.
- **Betriebsmodell:** Infrastruktur und Konfiguration versioniert als IaC/automatisierte, überprüfbare Konfiguration; reproduzierbare Container-Images mit unveränderlichen Tags/Digests. Manuelle Konsolenschritte sind zu protokollierende Ausnahmen.
- **Backup:** AWS-Sicherung und unabhängige, verschlüsselte Offsite-Sicherung außerhalb des VPS-/Contabo-Kontos. Backup gilt erst nach erfolgreichem Restore-Test als belastbar.
- **RPO/RTO:** erst nach Betreiberfreigabe verbindlich. Als Mindest-Gate gelten ein erfolgreich wiederherstellbarer finaler Cutover-Dump und ein benanntes, getestetes Wiederherstellungsverfahren. Eine tägliche Offsite-Sicherung allein garantiert kein enges RPO.

## 3. Datenintegrität und Backup

### Vorbereitungs- und Sicherungsnachweise

1. AWS-Quelle anhand eines autorisierten Betriebsinventars feststellen; Terraform-Plan/State nur lesend prüfen. Unklare Abweichungen zwischen Code und Live-Zustand vor Änderungen klären.
2. PostgreSQL-Quellversion, Erweiterungen, Rollen, Größen, Schema-Migrationen und letzte erfolgreiche Ingest-Läufe dokumentieren. Datenbankzugriffe und Backup-Dateien vertraulich behandeln.
3. Vor Migrationsbeginn einen AWS-RDS-PITR-Wiederherstellungspfad und einen manuellen DB-Snapshot nachweisen, sofern tatsächlich RDS im Einsatz ist. Retention, Verschlüsselung und Löschschutz live überprüfen. Ein automatisches Backup oder Snapshot ohne Restore-Nachweis ist kein vollständiger DR-Test.
4. Einen logischen Export mit `pg_dump --format=custom` erstellen; benötigte Rollen/Globals separat und mit geeigneter Zugriffsbeschränkung sichern. Export verschlüsselt, mit Prüfsumme versehen und mindestens auf einem unabhängigen Offsite-Speicher ablegen. Keine Dumps oder Secrets ins Repository, in Tickets oder unverschlüsselte Operator-Geräte kopieren.
5. `pg_restore --list`, Prüfsumme, Dump-Größe, Exportzeitpunkt und erfolgreichen Test-Restore in einer isolierten Ziel-Datenbank protokollieren. Backup-Retention und Löschfristen vorab festlegen.
6. Zusätzlich VPS-Dateisystem-/Konfigurationssicherung vorsehen, jedoch niemals als Ersatz für PostgreSQL-konsistente Exporte. Backup-Zugriff und Schlüssel getrennt vom produktiven VPS verwalten.

### Vergleich beim finalen Export/Import

Während des endgültigen Datenbankexports keine Ingest-Schreibvorgänge zulassen. Nach dem Import sind mindestens zu vergleichen:

- Anzahl je Tabelle sowie `schema_migrations`-Einträge und PostgreSQL-/Schema-Version;
- Schlüssel-/Eindeutigkeitsverletzungen und verwaiste Fremdschlüssel;
- Min-/Max-Datenwerte und Snapshot-Tage in `market_values` und `transfermarket_snapshots`;
- deterministische, tabellenweise Inhaltsprüfsummen über fachliche Spalten (volatile Zeitstempel separat bewerten);
- Sequenzstände für `BIGSERIAL`-Spalten, damit neue Inserts nicht mit vorhandenen IDs kollidieren;
- Stichproben und API-Antworten für Spieler, Teams, Historie und Transfermarkt gegen den Quellstand.

Migrationen nur nach Restore und Vergleich ausführen. Der [Migrations-Runner](../../backend/migrations/runner.py) führt noch nicht angewendete SQL-Dateien aus; keine ungeprüfte Schemaänderung als Teil des Infrastruktur-Cutovers einschleusen.

## 4. Ablauf mit Stop/Go-Gates

### Phase A – Inventur und Zielaufbau

- RTO/RPO, Wartungsfenster, Verantwortliche, DNS-/Vercel-Zugriff, Alarmierungsweg und Rückfallfrist bestätigen.
- Ist-Ressourcen in AWS und tatsächlichen API-/Scheduler-Zustand verifizieren. Datenbankzugang, DNS, Secrets oder Live-Konfiguration nicht aus Repository-Beispielen ableiten.
- Contabo-Kapazität anhand gemessener DB-Größe, Ingest-Laufzeit und API-Last dimensionieren; SSD-Freiraum für Wachstum, WAL und Backups einplanen.
- Zielhost gehärtet, gepatcht und überwacht bereitstellen; TLS-Zertifikat und Reverse-Proxy, Firewall, Zeitsynchronisation, Logrotation und Alarmierung testen. PostgreSQL und App nur mit separaten minimalen Rollen betreiben; API-Rolle read-only, Ingest-Rolle mit erforderlichen Schreibrechten.
- Container und Abhängigkeiten aus freigegebenem Commit bauen; lokale Backend- und PostgreSQL-Integrationstests gemäß [Backend-README](../../backend/README.md) ausführen.

**Go A:** Eigentümer haben Ziel-Sizing, RTO/RPO, Backup-Ort, TLS, Zugriffsschutz und Rückfallverantwortliche freigegeben. Restore eines Probe-Dumps und Health Checks funktionieren. Andernfalls kein Produktionsimport.

### Phase B – Probelauf und Betriebsnachweis

- Produktionsähnlichen Dump auf Contabo wiederherstellen und alle Integritätsvergleiche durchführen.
- Migrationen, API-Tests, Authentifizierung, TLS, `health/live`, `health/ready` und Vercel-Server-Proxy gegen den Ziel-API-Endpunkt testen.
- Einen kontrollierten Ingest im Test-/Staging-Kontext ausführen und Idempotenz bei Wiederholung prüfen. Keine parallelen produktiven Scheduler aktivieren.
- Cron/Scheduler auf dem Ziel zunächst deaktiviert lassen; Verhalten bei Ausfall, Retry, verspätetem Lauf, Alarm und manuellem Wiederanlauf testen. Runbooks und Zuständigkeit für den täglichen Erfolgsscheck aktualisieren.

**Go B:** Wiederhergestellte Daten sind fachlich gleichwertig, API-Vertrag/Autorisierung funktionieren, Tests sind grün und ein Backup lässt sich auf einem isolierten System zurückspielen.

### Phase C – Freeze und finaler Datenabgleich

1. Cutover ankündigen und Wartungsfenster starten; API-Schreibpfade (falls vorhanden) sperren.
2. AWS-Ingest-Schedule kontrolliert deaktivieren und prüfen, dass kein Fargate-Task mehr läuft oder nachstartet. Vor Cutover muss der letzte vollständige Ingest bekannt sein. Das AWS-Runbook dokumentiert den Scheduler und dessen DLQ; dessen Auslieferungs-Retry bedeutet nicht automatisch, dass ein gestarteter, fachlich fehlgeschlagener Job erneut ausgeführt wird ([AP-9-Runbook](../../backend/OPERABILITY-AP9.md)).
3. Letzten erfolgreichen Ingest-Zeitpunkt, Quelltabellenstände und Snapshot-Tage festhalten. Finalen konsistenten Export erstellen, Prüfsumme verifizieren und verschlüsselt übertragen.
4. Ziel zunächst ohne externe Schreibzugriffe importieren. Schema-, Sequenz-, Constraint-, Zeilen- und Inhaltsvergleiche abschließen; anschließend Read-only-Smoke-Tests durchführen.

**Go C:** Freeze bestätigt, kein laufender AWS-Schreiber, finale Sicherung gültig, alle Daten-Gates erfüllt und fachliche Abnahme erteilt. Bei Abweichung: Cutover abbrechen, AWS als Quelle belassen und Ursache untersuchen.

### Phase D – Umschalten

- Zunächst den API-Traffic kontrolliert auf den Contabo-Endpunkt lenken: bevorzugt den bestehenden Vercel-Server-Proxy auf eine serverseitige API-Origin-Konfiguration umstellen; keine Auth-/Proxy-Secrets im Browser verfügbar machen. Falls DNS geändert wird: TTL vorab reduzieren und Propagation berücksichtigen.
- TLS-, Auth-, API- und Datenbank-Health Checks über den tatsächlichen Nutzerpfad prüfen; Vercel darf nur den neuen HTTPS-Endpunkt verwenden.
- Nach API-Go-Live genau einen Ingest-Schedule auf Contabo aktivieren. Sicherstellen, dass AWS-Schedule ausgeschaltet bleibt. Ersten Lauf überwachen, `run_success`, plausiblen `records_written`-Wert, Datenintegrität und fehlende Duplikate bestätigen.
- Die Rückfallfrist mit AWS-Datenbank, Secrets und Infrastruktur intakt, aber ohne produktive Schreibvorgänge halten. Keine vorzeitige Ressourcenlöschung und kein paralleles Schreiben.

### Phase E – Beobachtung und AWS-Abschaltung

- Während der vereinbarten Rückfallfrist API-Fehler, TLS, Ressourcenverbrauch, tägliche Ingests, Backup-Erfolg und Wiederherstellbarkeit beobachten. Mindestens mehrere vollständige geplante Ingest-Fenster nachweisen; Anzahl und Dauer vorab festlegen.
- Nach Abnahme erst den AWS-Scheduler dauerhaft stilllegen, danach API-/ALB-/CloudFront/ECS/ECR-/Netzwerkressourcen anhand des verifizierten Inventars gezielt außer Betrieb nehmen. Reihenfolge von Abhängigkeiten und verbleibende Kosten dokumentieren.
- Vor jeder Datenbanklöschung finalen AWS-Snapshot, Export, Prüfsumme, Aufbewahrungsfrist und Wiederherstellungsberechtigung bestätigen. RDS-Löschschutz bewusst und separat freigeben; keine pauschale `terraform destroy`-Ausführung.
- AWS-Secrets erst nach bestätigtem Wechsel, Rotation/Neuausstellung benötigter Zugangsdaten und Ablauf der Rückfallfrist entfernen. Veraltete API-/DB-Zugangsdaten widerrufen bzw. rotieren.
- Terraform-State und S3-Versionen sind ein eigener Wiederherstellungs- und Sicherheitsgegenstand, nicht Anwendungsdaten: State sicher archivieren, Zugriff minimieren und niemals zusammen mit öffentlichen Artefakten exportieren. S3-Versionierung ermöglicht Wiederherstellung älterer Objektversionen, ersetzt aber weder DB-Backup noch Restore-Test.
- AWS erst als beendet melden, wenn Ressourceninventar, Kosten-/Billing-Check, Backup-Aufbewahrung, DNS/Vercel-Ziel und Verantwortlichkeit für Restbestände geprüft sind.

## 5. Rollback

**Auslöser:** Datenabweichung, fehlgeschlagene API-/Auth-Smokes, unerklärliche 5xx/Timeouts, ausgefallener Ingest, nicht erfolgreiches Backup oder Sicherheitsvorfall. Schwellen und Entscheidungshoheit vorab festlegen.

1. Contabo-Scheduler und alle Schreibzugriffe sofort anhalten; Zustand und Zeitpunkt sichern.
2. Nutzertraffic zurück auf den AWS-Endpunkt schalten, sofern dieser nachweislich verfügbar und sicher ist. Bei API-Problemen vor dem Wechsel der Datenquelle zunächst nur den Traffic zurücklenken.
3. **Datenbank-Rollback nach aktivem Contabo-Ingest ist kein bloßer DNS-Schritt:** zunächst Contabo als Schreiber einfrieren, seit Cutover entstandene Daten in einer kontrollierten Rücksynchronisation sichern und fachlich abgleichen. AWS erst dann wieder zum Schreiber machen, wenn feststeht, dass keine bestätigten Datensätze verloren gehen. Andernfalls Contabo als Datenquelle behalten und die API/Anwendung reparieren.
4. AWS-Schedule nur nach Datenabgleich und expliziter Freigabe reaktivieren. Doppelte Tages-Snapshots anhand der Unique-Constraints vermeiden und den nächsten Lauf kontrolliert überwachen.
5. Vorfall, Datenstand, Wiederherstellung und Abweichungen dokumentieren; danach erneutes Go/No-Go.

Die Rückfallfrist endet erst, wenn die neue Plattform die vereinbarten stabilen Ingest-Fenster, Backups und Restore-Tests nachweist und die Datenverantwortlichen den AWS-Rückweg formell freigeben.

## 6. Betriebsrisiken und Verfügbarkeit

| Risiko | Auswirkung | Gegenmaßnahme / Abnahme |
|---|---|---|
| Einzelner VPS / Host- oder Storage-Ausfall | API und Ingest fallen gemeinsam aus; RTO durch Neuaufbau/Restore | Offsite-Backups und dokumentierter Ersatzhost-Restore; 99,9-%-Ziel nicht ohne redundanten Aufbau behaupten |
| Fehlerhafter oder unvollständiger DB-Export | Historienverlust oder inkonsistente API-Daten | Freeze, Checksummen, tabellarische Vergleiche, Restore-Test, finaler Export vor Umschaltung |
| Split Brain: AWS und VPS schreiben parallel | Doppelte oder auseinanderlaufende Daten | Ein aktiver Schreiber, Scheduler-Lock, Laufkontrolle und dokumentierte Ownership |
| Nicht reproduzierbare Runtime/Config | Verzögerter Wiederanlauf | Unveränderliche Image-Version, Konfigurationsinventar, IaC, Deployment-/Restore-Runbook |
| Öffentliche DB, geleakte Zugangsdaten oder unsichere API | Datenabfluss/Übernahme | DB nicht öffentlich, TLS, Least Privilege, Secret-Rotation, Host-Firewall, gepatchtes Ubuntu, minimierte Logs |
| Verlust AWS-Alarmierung/DLQ | Fehlgeschlagene Läufe bleiben unbemerkt | Zielseitige Laufzeit-/Freshness-Alarme, tägliche Ingest-Erfolgskontrolle, getesteter Alarmkanal |
| Externe Abhängigkeit (Comunio/Vercel/Netz) | Snapshot- oder Frontend-Ausfall | Fehlerzustände und Retries überwachen; Änderungen am Datenprovider getrennt vom Plattformwechsel halten |
| Einzelner Offsite-Backup-Speicher | Backup und Produktivsystem gleichzeitig verloren | unabhängige Fehlerdomäne, getrennte Zugangsdaten, Verschlüsselung und regelmäßige Restore-Proben |

### Abwägung nach AWS Well-Architected Framework

- **Operational Excellence:** weniger AWS-Dienste, dafür mehr Eigenbetrieb auf dem VPS. Runbooks, IaC, Monitoring und Restore-Übungen sind Pflicht; Betriebsaufwand verlagert sich zum Projektteam.
- **Security:** IAM/Rollen und AWS Secrets Manager werden durch Host-/Linux-Rechte und ein eigenständig betriebenes Secret-Verfahren ersetzt. Mehr Kontrolle, aber höhere Patch-, Schlüssel- und Perimeter-Verantwortung.
- **Reliability:** ein VPS senkt Komplexität und Kosten, opfert aber Managed-RDS-/Multi-AZ-Resilienz. RTO/RPO und HA sind zu verifizieren bzw. explizit niedriger zu priorisieren.
- **Performance Efficiency:** direkte App-/DB-Nähe kann Latenz und Ressourcenverbrauch reduzieren; feste VPS-Kapazität und Single-Host-Engpass ersetzen elastische ECS-Skalierung.
- **Cost Optimization:** AWS-Servicekosten entfallen schrittweise, dafür entstehen feste VPS-, Offsite-Backup-, Monitoring- und Bereitschaftskosten. Gesamtkosten inklusive menschlicher Betriebszeit vergleichen.
- **Sustainability:** besser passende, ausgelastete feste Kapazität kann Ressourcen vermeiden; zu große Dauerinstanz oder redundante, ungenutzte Hosts können den Vorteil aufheben. Verbrauch und Sizing regelmäßig prüfen.

## 7. Abnahmekriterien

Migrationsfreigabe nur, wenn alle zutreffenden Kriterien erfüllt und mit Zeitstempel/Verantwortlichem dokumentiert sind:

- [ ] RTO, RPO, Wartungsfenster, Verfügbarkeitsziel und Rückfallfrist schriftlich freigegeben.
- [ ] AWS-Live-Inventar, Region, Datenbankversion, Scheduler-Zustand und tatsächliche API-Exposition verifiziert; keine Annahme aus Beispiel-Terraform als Live-Nachweis.
- [ ] Mindestens ein finaler, verschlüsselter, checksum-validierter Dump ist auf Contabo wiederhergestellt worden; ein unabhängiger Offsite-Restore ist erfolgreich getestet.
- [ ] Tabellenstände, fachliche Schlüssel, Fremdschlüssel, Schema-Migrationen, Sequenzen und Stichproben stimmen mit der final eingefrorenen AWS-Quelle überein.
- [ ] Backend- und PostgreSQL-Integrationstests sowie API-Vertragstests sind grün; Authentifizierung, TLS, `/health/live`, `/health/ready` und Vercel-Proxy funktionieren über den vorgesehenen Produktionspfad.
- [ ] PostgreSQL ist nicht öffentlich erreichbar; Dienste laufen mit minimalen Rechten; Secrets sind nicht in Code, Image, Logs, Browser oder öffentlich erreichbarer Konfiguration.
- [ ] AWS-Schreiber ist deaktiviert, genau ein Contabo-Scheduler ist aktiv, und ein produktiver Ingest wurde erfolgreich ohne Duplikate abgeschlossen.
- [ ] Monitoring alarmiert bei fehlendem Tageslauf, Fehlern, Plattenplatz-/Speichermangel, API-Ausfall und fehlgeschlagenem Backup; Alarmzustellung wurde getestet.
- [ ] Rollback wurde als Ablauf einschließlich der Datenrückführung nach einem VPS-Schreibvorgang geprüft; Ansprechpartner und Freigabeweg sind benannt.
- [ ] AWS-Abschaltung ist durch Ressourcenkontrolle, Daten-/State-Aufbewahrung, Credential-Widerruf und Billing-Prüfung abgeschlossen.

## 8. AWS-Dokumentationsbezug

Aktuelle Herstellerreferenzen, geprüft am 07.11.2026:

- [Amazon RDS: automatische Backups und Point-in-Time-Recovery](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html) – RDS-Backups können innerhalb der konfigurierten Retention zur Wiederherstellung dienen; endgültige Aufbewahrung beim Löschen und Restore müssen explizit geplant werden.
- [Amazon ECS: geplante Tasks mit EventBridge Scheduler](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/tasks-scheduled-eventbridge-scheduler.html) – Scheduler-Konfiguration und IAM-Ausführungsrolle sind Teil des Betriebsinventars.
- [Amazon EventBridge: Retry Policy](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rule-retry-policy.html) – Zustell-Retries betreffen die Target-Zustellung; eine DLQ verhindert nicht automatisch fachliche Fehler innerhalb eines erfolgreich gestarteten Containers.
- [Amazon S3: Versionierung](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html) – Versionierung kann frühere Objektversionen wiederherstellen, ist aber keine PostgreSQL-Backup- oder Wiederherstellungsstrategie.
