# Sicherheitsplan: AWS → Contabo Ubuntu

**Stand:** 2026-11-07  
**Umfang:** Sicherheitsplanung für die Migration dieses Repositories auf einen einzelnen Ubuntu-VPS. Keine SSH-Verbindung, keine produktiven Änderungen und keine Prüfung eines laufenden AWS- oder Contabo-Systems.  
**Produktionsfreigabe:** **NO-GO**, bis alle unten als Pflicht-Gates markierten Punkte umgesetzt und nachgewiesen sind.

## 1. Ausgangslage und Beleggrenzen

Der Plan stützt sich auf den eingecheckten Repository-Stand. Er belegt weder den aktuellen AWS-Livezustand noch eine bereits konfigurierte Contabo-Instanz. Eine Contabo-/Ubuntu-Zielkonfiguration, ein Domainname, Firewallzustand, Backupziel und tatsächliche Secret-Werte sind im Repository nicht nachgewiesen und werden hier nicht als vorhanden vorausgesetzt.

Relevante Befunde:

- Die API ist laut [README](../../README.md) und [AWS-Betriebsdokumentation](../../infra/aws/README.md) derzeit deaktiviert; die AWS-Konfiguration und Dokumentation sind nicht gleichbedeutend mit einem verifizierten Livezustand.
- Produktions-Auth und Comunio-Zugangsdaten sind derzeit AWS-spezifisch: [API-Auth lädt `AUTH_SECRET_ARN` über Secrets Manager](../../backend/src/api/auth.py), [der Ingest nutzt `AWS_REGION`/`COMUNIO_SECRET_NAME`](../../backend/src/ingest/comuniopy_client.py). Die App fordert in Produktion Auth- und Proxy-Konfiguration ([`app.py`](../../backend/src/api/app.py)) und den Secret-Modus ([`config.py`](../../backend/src/config.py)).
- Die API- und Datenbankverbindung erzwingt `sslmode=require` oder stärker; als Zielprofil nennt die Architektur `verify-full` ([DB-Verbindungsprüfung](../../backend/src/database/connection.py), [Security-Gates](../../architecture.md)).
- API-Login-Limits sind derzeit pro Python-Prozess im Speicher. Die IP-Auswahl bevorzugt `CloudFront-Viewer-Address`; das passt zur bisherigen CloudFront-Kette, ist aber für einen neuen Reverse Proxy nicht automatisch vertrauenswürdig ([`auth.py`](../../backend/src/api/auth.py), [AP-14-Befund](../code-review/2026-10-05-ap-14-security-review.md)).
- Das API-Image lauscht im Container auf `0.0.0.0:8000` ([`Dockerfile.api`](../../backend/Dockerfile.api)). Die neue VPS-Grenze muss daher explizit verhindern, dass API-Port oder PostgreSQL-Port öffentlich erreichbar sind.
- AWS trennt API-Read-only-DB-Rolle und Ingest-Credentials in separaten Secrets ([AWS-Runbook](../../infra/aws/README.md), [DB-Rollen-Provisionierung](../../backend/src/ops/provision_api_readonly_user.py)). Diese Trennung soll auf dem VPS erhalten bleiben.
- Die begleitenden Migrationspläne sehen einen einzelnen VPS, PostgreSQL 16 im internen Compose-Netz, einen systemd-Timer und verschlüsselte externe Backups vor; sie halten die API beim ersten Cutover zunächst deaktiviert ([Zielarchitektur](03-project-architecture-planner.md), [Implementierungsplan](05-software-engineer.md)). Das sind Zielentscheidungen, keine bereits vorhandene VPS-Konfiguration.

## 2. Zielbild und Sicherheitsgrenzen

```text
Internet -- HTTPS :443 --> Reverse Proxy (Nginx oder Caddy)
                              |-- nur intern --> FastAPI :8000
                              |-- keine DB-Weiterleitung
Ubuntu lokal/privates Docker-Netz:
  FastAPI --> PostgreSQL :5432 (TLS, nicht öffentlich)
  Ingest/Scheduler --> PostgreSQL (eigene Schreibrolle)
```

Der VPS stellt öffentlich nur HTTPS und – falls administrativ erforderlich – SSH bereit. Reverse Proxy, API, Datenbank und Ingest sind getrennte Dienste bzw. Container-Netze mit minimalen Rechten. PostgreSQL erhält keine öffentliche IP-/Portfreigabe. Die API erhält nur ihre Read-only-DB-Identität; der Ingest erhält eine separate Schreibidentität. Keine Komponente bekommt Root-Rechte im Normalbetrieb.

**Cutover-Grenze:** Die API bleibt beim ersten Daten-/Ingest-Cutover deaktiviert. Aktivierung und Vercel-Proxy-Umschaltung sind ein eigener, späterer Go-live mit erfolgreicher Auth-, TLS-, Header- und Rate-Limit-Abnahme; kein Test der API-Routen ist als Erlaubnis zur vorzeitigen Aktivierung zu verstehen.

**Proxy-Grundsatz:** Backend-Port nur an Loopback oder ein dediziertes internes Container-Netz binden. Der Reverse Proxy ist der einzige HTTP-Eingang. Eingehende `Forwarded`, `X-Forwarded-*` und `CloudFront-Viewer-Address`-Werte von Clients nicht als Identität übernehmen. Der Proxy muss solche Eingaben entfernen und die für den Backend-Hop benötigten Header selbst setzen. Uvicorn darf Proxy-Header ausschließlich vom tatsächlich vertrauenswürdigen Proxy-Peer akzeptieren. Für die Rate-Limit-IP im Backend muss die Anwendungslogik auf diesen Vertrauenspfad angepasst und getestet werden; ein vom Client gesetzter Header ist niemals eine belastbare Quell-IP.

## 3. Priorisierte Risiken und erforderliche Maßnahmen

### P1 — Hoch: AWS-spezifische Secrets verhindern einen sicheren VPS-Start

- **Kategorie:** Zero Trust / Secret Management
- **Repository-Beleg:** [`auth.py`](../../backend/src/api/auth.py) verlangt in Produktion `AUTH_SECRET_ARN` und liest Secrets Manager; [`comuniopy_client.py`](../../backend/src/ingest/comuniopy_client.py) lädt Comunio-Zugangsdaten über AWS; [`config.py`](../../backend/src/config.py) erzwingt im Produktionsmodus Secret-Mode.
- **Risiko:** Eine bloße Übernahme der AWS-Umgebungsvariablen oder ein Ausweichen auf `.env` kann zu Startfehlern oder ungeschützter Ablage von DB-, Login-, Proxy- und JWT-Secrets führen.
- **Fix/Gate:** Vor der VPS-Bereitstellung einen expliziten lokalen Secret-Provider implementieren und testen. Er muss mindestens `DATABASE_URL`, `API_PROXY_SECRET`, API-Auth-Konfiguration und Comunio-Zugangsdaten abdecken; der Code erwartet heute teils Umgebungsvariablen und teils AWS-ARNs. Bevorzugt systemd-Credentials (`LoadCredentialEncrypted=`) mit Zugriff nur für den jeweiligen Dienst; alternativ getrennte Dateien außerhalb des Repositories, Eigentümer `root`, Modus `0600`, Verzeichnis `0700`. Die Anwendung muss die Credentials direkt aus den bereitgestellten Dateien lesen. Keine Secrets in Git, Docker-Image/Layer, Terraform-State, Shell-Historie, Kommandozeilenargumenten, Logs oder öffentlich erreichbaren Environment-Endpunkten. Keine Secret-Dateien in Image-Build-Kontext oder Backup ohne Verschlüsselung.
- **Validierung:** Produktionsstart mit gültigen Credentials; Start mit fehlendem/ungültigem Secret muss fail-closed fehlschlagen. Rechte und Eigentümer aller Secret-Dateien prüfen; Git- und Image-Scan darf keine Werte finden. Keine Secret-Inhalte in Prüfprotokolle kopieren.

### P1 — Hoch: Header-Vertrauen und falsche Login-IP hinter neuem Proxy

- **Kategorie:** Zero Trust / Authentifizierung / Rate-Limit-Umgehung
- **Repository-Beleg:** [`_login_client_ip()`](../../backend/src/api/auth.py) vertraut `CloudFront-Viewer-Address` vor der Peer-Adresse. Die bisherige AWS-Konfiguration setzt CloudFront als vorgeschalteten Proxy voraus ([Architektur AP-14](../../architecture.md)); das ist keine Contabo-Konfiguration.
- **Risiko:** Wird der Backend-Port direkt erreichbar oder ein clientgelieferter IP-Header ungeprüft akzeptiert, kann die Quell-IP gefälscht und das anwendungsseitige Login-Limit umgangen werden. Ohne korrektes Proxy-Setup können alle Anmeldungen als Proxy-IP gewertet werden.
- **Fix/Gate:** Backend nur intern binden; in Nginx/Caddy vom Client angelieferte Forwarding- und CloudFront-Header löschen/überschreiben. `CloudFront-Viewer-Address` auf dem VPS nicht weiterreichen. Uvicorn-Proxy-Vertrauen auf die konkrete lokale Proxy-Adresse begrenzen. Backend-Logik so ändern, dass nur aus einer verifizierten Proxy-Kette eine Client-IP verwendet wird; andernfalls Peer-Adresse verwenden. Diesen Vertrauenspfad mit Spoofing-Tests nachweisen.
- **Validierung:** Aus dem Internet sind nur die freigegebenen Ports erreichbar. Ein Testclient, der wechselnde `X-Forwarded-For`- und `CloudFront-Viewer-Address`-Werte sendet, erhält keine neuen Rate-Limit-Buckets. Proxy-IP und Quell-IP mit kontrolliertem Staging-Test verifizieren, ohne produktive Konten mit Fehlversuchen zu sperren.

### P1 — Hoch: TLS und Dienstabgrenzung müssen am VPS neu hergestellt werden

- **Kategorie:** OWASP A02 / Zero Trust
- **Repository-Beleg:** API-DB-Verbindungen lehnen `sslmode=disable` ab ([`connection.py`](../../backend/src/database/connection.py), [Tests](../../backend/tests/test_security_policies.py)). AWS-PostgreSQL ist im Terraform-Code nicht öffentlich und verschlüsselt ([`database.tf`](../../infra/aws/terraform/database.tf)); diese AWS-Eigenschaften werden durch einen VPS nicht übernommen.
- **Risiko:** Klartext-Login, öffentliche Datenbank oder öffentlich erreichbarer App-Port; `sslmode=require` allein prüft nicht die Identität des DB-Servers.
- **Fix/Gate:** Öffentliches TLS am Reverse Proxy mit gültigem Zertifikat, automatischer Verlängerung und HTTP→HTTPS-Redirect; TLS 1.2+; HSTS erst nach erfolgreicher HTTPS-Abnahme aktivieren. DB-TLS mit Zertifikatsprüfung und `sslmode=verify-full` als Zielprofil. PostgreSQL nur lokal bzw. im internen Netz annehmen lassen und Firewall-seitig TCP/5432 blockieren. Backend-Port 8000 nicht veröffentlichen. DB-Admin, API-Read-only- und Ingest-Rolle getrennt halten; der API-Rolle keine Schreibrechte erteilen.
- **Validierung:** Zertifikatskette, Hostname und TLS-Protokoll von außerhalb prüfen; HTTP-Login darf nicht möglich sein. Von einem externen Host müssen 5432 und 8000 geschlossen sein. SQL-Prüfung der DB-Rollen/Rechte durchführen; `sslmode=disable` muss von der Anwendung abgewiesen werden, `verify-full` erfolgreich sein.

### P2 — Mittel: In-Memory-Loginlimit ist nicht dauerhaft/clusterweit

- **Kategorie:** OWASP A07 / Verfügbarkeit
- **Repository-Beleg:** [`auth.py`](../../backend/src/api/auth.py) begrenzt Login-Versuche pro IP auf fünf in fünf Minuten, hält Zähler aber pro Prozess im Speicher; [`architecture.md`](../../architecture.md) dokumentiert, dass mehrere Tasks das Limit aufweichen.
- **Risiko:** Neustart setzt Zähler zurück; spätere Worker/Instanzen haben unabhängige Kontingente. Das ist kein alleiniger Schutz gegen breit verteilte Versuche.
- **Fix/Gate:** Für den Ein-VPS-Betrieb zusätzlich ein Proxy-seitiges Login-Limit mit verbindlicher Shared-Zone und angemessenen Burst-/Antwortwerten konfigurieren; Anwendungslimit als zweite Schicht beibehalten. Request-Body-Größe und Login-Timeout begrenzen. Wenn mehrere Backend-Prozesse oder VPS eingesetzt werden, gemeinsames Rate-Limit (z. B. zentraler Zähler) als Pflicht vor Skalierung.
- **Validierung:** Im Staging sechster Loginversuch innerhalb des Fensters erhält `429` samt `Retry-After`; Requests mit gefälschten Headern ändern die IP-Zuordnung nicht. Grenzwerte und legitime Wiederherstellung dokumentieren.

### P2 — Mittel: Backup/Restore und Secret-Rotation sind nicht auf den VPS übertragbar

- **Kategorie:** Verfügbarkeit / Cryptographic Failures
- **Repository-Beleg:** AWS-RDS-Code sieht verschlüsselte Speicherung und konfigurierbare Aufbewahrung vor; Standardwerte für Backup, Löschschutz und Final Snapshot sind Variablen ([`database.tf`](../../infra/aws/terraform/database.tf), [`variables.tf`](../../infra/aws/terraform/variables.tf)). Das ist kein Beleg für ein VPS-Backup oder dessen Wiederherstellbarkeit.
- **Risiko:** Datenträger-/VPS-Ausfall, Ransomware, versehentliches Löschen oder Secret-Verlust; ein Backup auf demselben VPS schützt nicht vor dessen Ausfall.
- **Fix/Gate:** Vor Umschaltung RPO/RTO und Aufbewahrung mit Product Owner festlegen. Als Startvorschlag (Freigabe erforderlich): tägliche DB-Sicherung, mindestens 14 tägliche, 8 wöchentliche und 6 monatliche Generationen; zusätzlich verschlüsselte Offsite-Kopie mit getrenntem Zugriff. Backup-Schlüssel nicht nur auf dem VPS ablegen. Backups und Secret-Backups getrennt behandeln, Zugriff protokollieren und Lösch-/Aufbewahrungsregeln festlegen. Rotation für SSH-Zugänge, DB-Rollenpasswörter, API-Proxy-Secret, Auth-Passwort/JWT-Schlüssel und Comunio-Credentials dokumentieren. JWT-Key-Wechsel widerruft bestehende Tokens; Neustart/Reload der App nach Secret-Änderung ist erforderlich.
- **Validierung:** Mindestens eine verschlüsselte Sicherung erstellen, Prüfsumme/Lesbarkeit kontrollieren und Restore in isolierte Testdatenbank durchführen; Tabellen/Schema und repräsentative Datensätze vergleichen. Wiederherstellungsdauer gegen freigegebenes RTO messen. Rotationsübung in Staging durchführen und verifizieren, dass alte Credentials nicht mehr funktionieren.

## 4. Umsetzungsreihenfolge und konkrete Abnahme

### A. Zugang zum VPS (vor Installation)

1. Ubuntu LTS-Version, Anbieter-Konsole, Backupziel und zuständige Administratoren dokumentieren; MFA für Anbieterzugang aktivieren, sofern verfügbar.
2. Separates persönliches Administrationskonto, SSH-Schlüsselzugang, kein Root-Login und keine SSH-Passwortanmeldung einrichten. SSH nur für notwendige feste Quell-IP(s) oder über ein VPN freigeben. Änderungen mit einer zweiten, weiterhin offenen Administrationssitzung testen, bevor die erste geschlossen wird.
3. Anbieter-Firewall und Ubuntu-Firewall konsistent halten: öffentlich nur TCP/443 und freigegebenes SSH; TCP/80 nur für ACME/Redirect nach Bedarf. UDP/TCP 5432 und TCP 8000 nicht öffentlich freigeben.
4. Sicherheitsupdates automatisieren, Neustartbedarf überwachen und einen dokumentierten Patch-/Rollback-Verantwortlichen festlegen.

**Prüfungen:** `ss -lntup` zeigt keine öffentliche Listener-Bindung für 5432/8000. `sudo ufw status verbose` (oder das tatsächlich eingesetzte nftables-Äquivalent) entspricht dem freigegebenen Portplan. Externer Portscan aus einer autorisierten Prüfumgebung bestätigt nur freigegebene Ports; Anbieter-Firewall separat kontrollieren.

### B. Secret-Dateien und App-Umstellung

1. AWS-Secret-Provider durch dateibasierten Provider für DB-DSN, API-Proxy-Secret, API-Auth und Ingest ergänzen. Dateien nicht im Repository oder im Arbeitsverzeichnis des Deployments ablegen. Separate Credentials pro Dienst und Zweck verwenden; niemals Admin-DB-Zugang für API/Ingest übergeben.
2. Wenn systemd-Credentials eingesetzt werden, Dateien über `LoadCredentialEncrypted=` einbinden und nur dem betreffenden Service zugänglich machen. Ubuntu-/systemd-Unterstützung auf der konkreten Zielversion vorab prüfen. Fallback ausschließlich root-owned, `0600`/Verzeichnis `0700`, außerhalb von Git und Backup-Quellverzeichnissen. Keine `EnvironmentFile` mit Secretwerten als Standardverfahren.
3. Betriebssystembenutzer ohne Login-Shell für API und Ingest; nur nötige Leserechte auf jeweilige Credential-Dateien. Docker-Secrets/Volumes, falls Container eingesetzt werden, read-only und außerhalb des Image-Layers.

**Prüfungen:** `systemctl show <dienst> -p User -p LoadCredential` nur als Metadatenprüfung; Dateirechte mit `stat` prüfen, keine Datei ausgeben. Fehlende Credentials müssen den Produktionsstart verhindern. `git status`/Secret-Scan und Prüfung des finalen Image-Inhalts durchführen.

### C. TLS, Proxy und Datenbank

1. Reverse Proxy als einzige öffentliche HTTP-Grenze installieren; API nur intern binden. Keine Proxy-Regel für DB-Port, keine öffentlich zugänglichen Admin-/Metrics-Routen.
2. DNS und Zertifikat vor Aktivierung prüfen; Zertifikatsverlängerung alarmieren. Auth-/API-Antworten nicht cachen; `Set-Cookie`, `Cookie`, `Authorization` und `Origin` nur soweit für den vorgesehenen gleich-origin Proxy erforderlich weiterleiten. `Cache-Control: private, no-store` für Authentifizierungsantworten beibehalten (Frontend-Proxy-Beleg: [`route.ts`](../../frontend/app/api/auth/%5B...path%5D/route.ts), [API-Proxy](../../frontend/app/api/proxy/%5B...path%5D/route.ts)).
3. Forwarding-Header am Proxy neu setzen, nicht vom Client übernehmen; Backend vertraut ausschließlich dem Proxy-Peer. `CloudFront-Viewer-Address` aus der VPS-Kette entfernen.
4. PostgreSQL nur im privaten Dienstnetz, verschlüsselte Volumes/Backups und TLS-Verbindungen. API-DB-Nutzer auf `SELECT` begrenzen; Ingest-Schreibrolle und DB-Admin getrennt halten. PostgreSQL-Zugriff aus dem Internet muss fehlschlagen.
5. Für den Datenumzug einen konsistenten PostgreSQL-Export über TLS erzeugen und während Transport/temporärer Ablage verschlüsseln. Zugangsdaten nicht in Prozessargumente oder Tickets schreiben. Import in eine isolierte Ziel-DB; Schema, Migrationstand und fachliche Zähl-/Integritätsprüfungen vergleichen. Temporäre Exportdateien nach erfolgreicher Abnahme sicher entfernen. Die konkrete Export-/Importfolge und Rollback-Freigabe stehen im [Implementierungsplan](05-software-engineer.md); sie sind vor dem Cutover mit den tatsächlichen AWS-Endpunkten und Datenmengen zu konkretisieren.

**Prüfungen:** `curl -I http://<host>` ergibt nur Redirect bzw. keine Auth-Daten; `curl -I https://<host>` zeigt gültige TLS-Antwort. `openssl s_client -connect <host>:443 -servername <host>` zeigt vertrauenswürdige Kette und passenden Namen. Zertifikatsablauf-/Renewal-Test in Staging. Externes `nc`/Verbindung auf 5432 und 8000 muss scheitern. DB-seitig TLS und Rollenprivilegien prüfen.

### D. Anmeldung, Limits und Header

1. Exakte `Origin`-Allowlist auf den tatsächlich verwendeten Frontend-Origin setzen; keine Produktions-Defaults `localhost` übernehmen. Bestehende Backend-Prüfung für schreibende Auth-Aufrufe und sichere Cookie-Attribute beibehalten ([`app.py`](../../backend/src/api/app.py), [`auth.py`](../../backend/src/api/auth.py)).
2. Proxy-Rate-Limit auf `/auth/login`, Backend-Limit als zweite Ebene. Login-/Auth-Antworten nicht cachen. Kein Debug-/Traceback-Output und keine Secretwerte in Fehlerantworten.
3. Vor Livegang testen, dass unauthentifizierte API-Aufrufe `401` liefern, ungültige Origin-Requests abgewiesen werden, erfolgreiches Login ein `Secure`, `HttpOnly`, `SameSite=Strict`-Cookie ausstellt und Logout es löscht.

**Prüfungen (Staging):** automatisierte Backend-/Frontend-Suites aus [AP-14-Abnahme](../../architecture.md) ausführen. Unauthentifizierte `/api/v1`- und `/auth/me`-Requests müssen abgewiesen werden. Kontrollierter Fehlversuch-Test muss das Limit auslösen; anschließend korrekte Zugangsdaten prüfen. Spoofed Forwarding-Header darf weder Quell-IP noch Limit umgehen. Keine Brute-Force- oder Lasttests gegen produktive Konten.

### E. Backup, Logging und Rotation

1. Strukturierte Logs für Login-Erfolg/-Fehler, Dienststart, Backup, Restore, Deploy, SSH/Sudo und Sicherheitsupdates; keine Passwörter, Cookies/JWT, `Authorization`, DSNs, Secret-Inhalte oder Request-Bodies. IP-Logging auf Zweck und Aufbewahrung begrenzen; Zugriff auf Logs beschränken.
2. Logrotation, Speicherlimit und Alarm bei vollem Datenträger einrichten. Zeit synchronisieren und Logs nach festgelegter Frist löschen; Offsite-Log-Export nur verschlüsselt und mit Zugriffskontrolle.
3. Backup nach dem freigegebenen Zeitplan automatisieren. Backupjob muss Fehler melden, nicht nur Exit-Code verbergen. Restore zunächst isoliert, niemals über die einzige produktive DB.
4. Rotationstermine und Ereignisrotation festlegen: bei Personalwechsel, Verdacht/Incident oder Anbieter-/Geräteverlust sofort; außerdem nach einem durch Verantwortliche freigegebenen periodischen Intervall. Beim JWT-Schlüsselwechsel Sessions absichtlich widerrufen; Proxy-Secret und DB-Passwörter koordiniert aktualisieren und Dienste kontrolliert neu starten.

**Prüfungen:** kontrollierter Testlog enthält keine Secret-/Cookie-/DSN-Muster. Rotation wird mit alter/neuer Test-Credential geprüft. Täglicher Backup-Erfolg und Speicherstand alarmieren; regelmäßiger Restore-Nachweis wird mit Datum, Dauer, Prüfer und Ergebnis protokolliert.

## 5. Verantwortlichkeiten / Freigaben

| Rolle | Verantwortung vor Go-live |
|---|---|
| **VPS-/Systemadministrator** | SSH-/MFA-Zugänge, Ubuntu-Patches, Firewall, Dienstkonten, Dateirechte, TLS-Erneuerung, Monitoring und Host-Incident-Reaktion. |
| **Anwendungs-/Backend-Verantwortlicher** | AWS-unabhängiger Secret-Provider, sichere Header-Vertrauenslogik, Login-Limit, API-/Ingest-Trennung, Tests, Releases und Secret-Rotation in der Anwendung. |
| **Datenbankverantwortlicher** | TLS, private Erreichbarkeit, Rollen/Grants, Backup/Restore, DB-Passwortrotation und Datenintegrität nach Migration. |
| **Product Owner / Datenverantwortlicher** | RPO/RTO, Backup-Aufbewahrung, zulässige Wartungsfenster, Umschalt- und Rückfallentscheidung sowie fachliche Datenabnahme. |
| **Security-Freigebender** | unabhängige Abnahme der Ports, TLS, Header-/Rate-Limit-Tests, Secret-Handling, Logs und Restore-Probe; schriftliche Go/No-Go-Entscheidung. |

## 6. Go/No-Go

**GO erst, wenn** AWS-spezifische Secret-Zugriffe für den VPS sicher ersetzt sind; SSH und Providerzugang gehärtet sind; nur freigegebene Ports offen sind; Backend-/DB-Ports extern unerreichbar sind; HTTPS und DB-TLS geprüft sind; Proxy-Header vertrauenswürdig behandelt werden; Login-/Rate-Limit- und Auth-Tests bestehen; Rollen minimal berechtigt sind; ein verschlüsseltes Offsite-Backup erfolgreich wiederhergestellt wurde; Rotation und Logging geprüft sind; alle Verantwortlichen die Risiken und RPO/RTO schriftlich freigegeben haben.

**NO-GO** bei `.env`/Secret im Repository oder Image, öffentlich erreichbarer PostgreSQL-/API-Port, ungeprüftem TLS, vom Client übernommenen IP-Headern, fehlendem Restore-Nachweis, unbekanntem Secret-Eigentümer oder nicht getesteter Rückfallmöglichkeit. Ein Repository-Test allein beweist weder korrekte VPS-Konfiguration noch Produktionssicherheit.
