# Code Review: VPS-Migration, Phasen 1–3

**Reviewdatum:** 2026-11-07  
**Umfang:** `docs/migration/00-gesamtplan.md` (Phasen 1–3), Sicherheitsplan und tatsächlich eingecheckter Backend-/Container-Code. Keine Verbindung zu VPS/AWS, keine Live-Konfigurationsprüfung.  
**Produktionsreife:** **NO-GO für Cutover**, bis die Pflicht-Gates unten umgesetzt und nachgewiesen sind. Die API bleibt initial deaktiviert; ihre spätere Aktivierung ist ein separates Gate.  
**Kritische Issues:** 0 bekannte unmittelbare Code-Exploits im geprüften Umfang; mehrere Produktionsblocker und nicht implementierte Kontrollen.

## Review-Plan

Risiko: hoch (Produktionsdatenbank, Zugangsdaten, schreibender Ingest). Prüfkategorien:

1. Compose-/Container-Isolation und minimale Rechte
2. PostgreSQL-TLS, Secret-Injektion und Host-Dateirechte
3. Scheduler-Exklusivität, Migration und Backup/Restore
4. Proxy-/Client-IP-Vertrauen und API-Abschaltung

## Priorität 1 (vor Cutover beheben) ⛔

### P1 — VPS-Deployment-Grenzen sind noch nicht implementiert oder prüfbar

- **Kategorie:** Zero Trust / OWASP A05, A07
- **Evidenz:** Im Repository ist kein `infra/vps/`-Verzeichnis und keine Compose-Datei vorhanden. `backend/Dockerfile.api` startet Uvicorn mit `--host 0.0.0.0 --port 8000`; es gibt damit noch keine geprüfte Deployment-Grenze, die einen öffentlichen API-Port verhindert. Die AWS-Terraform-Grenzen gelten nicht automatisch für den VPS.
- **Auswirkung:** Eine spätere Compose-Definition könnte DB/API-Ports veröffentlichen oder unnötige Rechte/Host-Zugriffe erteilen. Laufende AWS- oder VPS-Zustände wurden nicht verifiziert.
- **Mindestfix:** Compose mit festen Image-Digests, persistentem benanntem DB-Volume, privaten Netzwerken, keinem PostgreSQL-Port-Publishing und ohne Docker-Socket, Host-Netzwerk, privilegierte Container oder unnötige Capabilities. `read_only`, `no-new-privileges`, `cap_drop: [ALL]` und begrenzte Ressourcen soweit kompatibel aktivieren. **API und Reverse Proxy in Phase 1–3 nicht starten oder veröffentlichen**; API erst nach separater Freigabe hinzufügen. Ingest nur als One-shot.
- **Validierung:** `docker compose config`; Compose-/Inspect-Prüfung auf veröffentlichte Ports, Mounts, Capabilities, User und Image-Digest. Auf einem isolierten Staging-Ziel nachweisen, dass DB/API nicht extern erreichbar sind und die API im Standardbetrieb nicht läuft.

### P1 — `sslmode=require` wird derzeit als ausreichend akzeptiert; `verify-full` ist nicht erzwungen

- **Kategorie:** OWASP A02 / Zero Trust
- **Evidenz:** `backend/src/database/connection.py::_ALLOWED_SSLMODES` erlaubt `require`, `verify-ca` und `verify-full`; `_validate_sslmode()` prüft nur den Modus in der URL. `backend/tests/test_security_policies.py::test_connect_accepts_secure_sslmode` akzeptiert ausdrücklich `sslmode=require` und mockt die eigentliche Verbindung. Eine VPS-CA oder PostgreSQL-TLS-Serverkonfiguration ist nicht im Repository belegt.
- **Auswirkung:** Verschlüsselung ist nicht gleich Serveridentitätsprüfung. `require` kann eine Verbindung zu einem nicht authentisierten DB-Endpunkt zulassen.
- **Mindestfix:** Für die VPS-Produktions-DSN `sslmode=verify-full` mit korrektem DNS-Namen und vertrauenswürdiger CA verbindlich verlangen; CA-Bereitstellung und Zertifikatsrotation dokumentieren. `require` nicht als Produktions-Fallback akzeptieren. PostgreSQL bleibt ohne Host-Portfreigabe.
- **Validierung:** Integration gegen TLS-PostgreSQL: korrekte CA und Hostname erfolgreich; falsche CA, falscher Hostname sowie `require`/`disable` im VPS-Produktionsprofil scheitern. Ein Unit-Test allein belegt keine Zertifikatsprüfung.

### P1 — Dateibasierte Secrets fehlen; Container-UID und Lesbarkeit sind ungeklärt

- **Kategorie:** Secret Management / Zero Trust
- **Evidenz:** `backend/src/ingest/comuniopy_client.py` bezieht Secret-Mode aus AWS Secrets Manager; `backend/src/api/auth.py::get_auth_config()` verlangt `AUTH_SECRET_ARN`; `backend/src/api/app.py` verlangt in Produktion `API_PROXY_SECRET` und `AUTH_SECRET_ARN`. `backend/src/config.py` stellt keinen Datei-Provider bereit. Beide Dockerfiles wechseln auf `USER app`, legen aber keine feste numerische UID/GID fest.
- **Auswirkung:** Der VPS kann mit den bestehenden AWS-ARN-Abhängigkeiten nicht einfach sicher starten. Eine nur root-lesbare `0600`-Datei ist für den nicht privilegierten Containerprozess nicht lesbar; großzügige Rechte würden Secrets offenlegen. Das Verhalten lokaler Compose-Datei-Secrets darf nicht ohne Laufzeittest angenommen werden.
- **Mindestfix:** Vor Einsatz des Ingests einen expliziten, fail-closed Dateicredentials-Provider ergänzen und AWS-Provider/Produktionsprüfungen erhalten. Secrets dienst- und zweckgetrennt halten; aus Git, Build-Kontext, Image-Layern, Logs und Prozessargumenten ausschließen. Container-UID/GID explizit festlegen oder die effektiven IDs des gebauten Images feststellen. Host-Dateien nur für den nötigen Host-Principal/Container-Gruppenzugriff lesbar und im Container read-only bereitstellen; nicht pauschal world-readable machen. API-Credentials vor API-Freigabe weiterhin nicht bereitstellen/nutzen.
- **Validierung:** In einem echten Container als Laufzeit-UID/-GID prüfen, dass die vorgesehene Datei lesbar ist, ohne den Inhalt auszugeben. Fehlende, ungültige und unlesbare Credentials müssen fail-closed abbrechen; gesetzte ENV-Fallbacks dürfen die Datei-Sicherheitsgrenze nicht umgehen. Image-/Git-Secret-Scan mit Testmarkern.

### P1 — Migration-Backup und Restore sind Pflicht, regelmäßige Backups bleiben ausdrücklich Restrisiko

- **Kategorie:** Verfügbarkeit / Datenintegrität / Cryptographic Failures
- **Evidenz:** Es gibt keine VPS-Backup-/Restore-Implementierung. `scripts/aws/export-db.ps1` ist laut Gesamtplan kein vollständiges PostgreSQL-Backup. `00-gesamtplan.md` verlangt eine einmalige Migrationssicherung samt Restore-Probe, verschiebt regelmäßige externe Backups aber nach dem Umzug.
- **Auswirkung:** Ohne erfolgreich getestete, unabhängig und geschützt aufbewahrte Sicherung kann ein fehlerhafter Import nicht verlässlich zurückgenommen werden. Nach Cutover können alle seit der einmaligen Sicherung geschriebenen Daten bei VPS-Ausfall verloren gehen; RPO/RTO sind nicht nachgewiesen. Lokale Sicherung auf demselben VPS wäre kein Offsite-Schutz.
- **Mindestfix:** Vor Phase 3 finalen konsistenten PostgreSQL-Dump verschlüsselt übertragen und getrennt vom VPS geschützt aufbewahren. In einer isolierten leeren Zielinstanz wiederherstellen und Schema, `schema_migrations`, Constraints, Sequenzen und aussagekräftige Datenbestände vergleichen. Vor AWS-Abbau das bewusst verschobene Backup-Risiko samt fehlendem RPO/RTO ausdrücklich vom Betreiber akzeptieren lassen oder regelmäßige verschlüsselte externe Sicherungen samt Restore-Alarmierung vorziehen.
- **Validierung:** Restore-Probe und Integritätsvergleich dokumentieren, Laufzeit gegen vereinbartes RTO messen; sicherstellen, dass Backup/Schlüssel nicht in Git, CI-Artefakten oder unverschlüsselten Logs landen. Vor Cutover zusätzlich finalen Dump nach bestätigtem Schreibstopp erstellen.

## Priorität 2 (vor Aktivierung des VPS-Schedulers)

### P2 — Scheduler-/Lock-Konfiguration fehlt; Runner verhindert Parallelstarts nicht selbst

- **Kategorie:** Zuverlässigkeit / Datenintegrität
- **Evidenz:** Keine systemd-Unit/-Timer im Repository. `backend/src/ingest/runner.py::main()` startet bei jedem Aufruf einen Lauf und implementiert keinen exklusiven Host-Lock. `backend/src/ingest/snapshot_job.py::run_manual_snapshot()` legt für jeden Lauf einen `ingest_runs`-Datensatz an; Upserts schützen einzelne Daten vor Duplikaten, ersetzen aber keine Exklusivität.
- **Auswirkung:** Manuelle, nachgeholte oder doppelte Timerstarts können parallel schreiben und die Betriebsdiagnose erschweren. AWS und VPS gleichzeitig aktiv zu lassen verletzt die Ein-Writer-Grenze.
- **Mindestfix:** systemd-One-shot-Service und UTC-Timer für 06:00 UTC; explizite Entscheidung zu verpassten Läufen (`Persistent=`), NTP/Zeitsynchronität, Timeout und Retry-Gesamtzeit. Gemeinsamen atomaren Host-Lock auch für manuelle Starts verwenden. Fehler- und fehlender Heartbeat müssen alarmiert werden. Vor finalem Cutover AWS-Schedule deaktivieren und gestartete Tasks drainen; erst nach bestätigtem Schreibstopp VPS-Writer aktivieren.
- **Validierung:** `systemd-analyze verify`; UTC-Zeit und Neustart-/verpasster-Lauf-Verhalten testen. Zwei gleichzeitige Scheduler-/manuelle Läufe starten und nachweisen, dass nur einer arbeitet. Exitcode- und Missing-Heartbeat-Alarm testen. Cutover-Protokoll muss genau einen aktiven Writer/Scheduler belegen.

## API-/Proxy-Gate (nicht Cutover-Blocker, solange API nachweislich aus bleibt)

- **Evidenz:** `backend/src/api/auth.py::_login_client_ip()` vertraut `CloudFront-Viewer-Address` vor der Peer-IP; der Header ist für einen neuen VPS-Proxy keine verifizierte Identität. Das Login-Limit `_attempts` ist pro Python-Prozess im Speicher. `backend/src/api/app.py` setzt zusätzlich API-Proxy-Bearer-Authentifizierung und Produktionsanforderungen, erzwingt aber nicht selbst eine vertrauenswürdige Proxy-Kette.
- **Risiko:** Bei späterer Erreichbarkeit können gefälschte Client-Header die IP-Zuordnung und damit das Login-Rate-Limit verfälschen; mehrere Prozesse/Neustarts schwächen das Prozesslimit.
- **Mindestfix vor API-Go-live:** Clientseitige `Forwarded`-/`X-Forwarded-*`-/CloudFront-Header am Proxy entfernen oder überschreiben; Backend-Port ausschließlich intern; Uvicorn-Proxy-Vertrauen auf den tatsächlichen Proxy-Peer begrenzen. Backend soll nur die vom vertrauenswürdigen Proxy gelieferte Client-IP verwenden, sonst Peer-IP. Proxy-seitiges Rate-Limit als zweite Schicht. Separate Read-only-DB-Rolle und eigener API-Freigabeschritt.
- **API-Abschaltung für Phase 1–3:** API-Service nicht starten, Port 8000 nicht veröffentlichen und keine Proxy-/Vercel-Umschaltung durchführen. Ein bestandener API-Test ist keine Aktivierungsfreigabe.
- **Spätere Tests:** Spoofing-Tests mit wechselnden CloudFront-/XFF-Werten; dieselbe echte Quell-IP muss demselben Rate-Limit-Bucket zugeordnet werden. Externen Porttest auf 8000/5432 durchführen; API-Tests nur in isoliertem Staging.

## Relevante Tests / Abnahme

1. Bestehende Basis: `backend/tests/test_security_policies.py`, `backend/tests/test_scheduled_runner.py`, `backend/tests/test_snapshot_job.py`, API- und PostgreSQL-Integrationstests; gesamte Backend-Suite gemäß Projektkonvention ausführen.
2. Neue Compose-Abnahme: Konfiguration mit synthetischen Werten rendern; Standardprofil enthält keine aktive API und veröffentlicht weder 5432 noch 8000. Image läuft ohne Root und ohne unnötige Capabilities.
3. TLS-Integration: `verify-full` mit gültigem Zertifikat erfolgreich; falsche CA und falscher DNS-Name scheitern.
4. Secret-UID-Abnahme: erfolgreicher Dateizugriff als tatsächliche Container-UID/GID, read-only Mount; fehlende/falsche Rechte und Secret fail-closed; keine Werte in Logs/Image/Git.
5. Timer-/Lock-Abnahme: 06:00 UTC, dokumentiertes Persistent-Verhalten, Parallelstart wird verhindert, Exitcode/Heartbeat löst Alarm aus.
6. Backup-/Restore-Abnahme: vollständiger Dump, geschützte Übertragung, Restore auf isolierter DB, Schema-/Datenvergleich und RTO-Messung.
7. Cutover-Abnahme: AWS-Writer beendet und deaktiviert, finaler Dump nach Schreibstopp, genau ein kontrollierter VPS-Lauf, Timer erst anschließend aktiv; Rückfallplan berücksichtigt bereits geschriebene VPS-Daten.

## Risikozusammenfassung

- Kritisch: 0 bestätigte unmittelbare Exploits im geprüften Quellcodeumfang
- Hoch: 4 Produktionsblocker (nicht belegte Deployment-Grenzen, fehlendes `verify-full`-Enforcement, fehlender lokaler Secret-Provider/UID-Nachweis, Backup-/Restore-Gate)
- Mittel: 1 Scheduler-/Parallelitätsblocker; Proxy/IP-Risiko als separates API-Gate
- Niedrig: 0

## Entscheidung

- **Production Ready:** Nein
- **Blocking Issues:** Compose-/Netzwerkgrenzen implementieren und testen; VPS-Produktions-TLS auf `verify-full` festlegen; Dateisecrets mit tatsächlicher Container-UID sicher bereitstellen; Migration-Dump und isolierten Restore nachweisen; UTC-Scheduler/Lock/Alarm testen; Ein-Writer-Cutover dokumentieren.
- **Freigabegrenze:** API bleibt während Phasen 1–3 deaktiviert. Reguläre externe Backups sind im Gesamtplan nachgelagert; AWS-Abbau bzw. längerer VPS-Produktivbetrieb erfordert dafür eine ausdrückliche Risikoentscheidung oder vorherige Backup-Automatisierung.
