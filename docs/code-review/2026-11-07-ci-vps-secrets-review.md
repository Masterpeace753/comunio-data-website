# Code Review: CI und VPS-/Secret-Änderungen

**Reviewdatum:** 2026-11-07  
**Produktionsreife:** **NO-GO für VPS-Cutover oder API-Aktivierung**  
**Kritische Issues:** 0 bekannte unmittelbare Exploits im eingesehenen Code  
**Umfang:** `.github/workflows/ci.yml`, VPS-Compose/Systemd/HBA/Beispielkonfiguration, Secret-Provider und DB-TLS-Validierung im Backend sowie AWS-Dokumentation/Terraform-Staatsbackend. Arbeitsbaumänderungen konnten mangels Git-Status/Diff-Zugriff nicht von bereits committeten Dateien unterschieden werden. Keine Live-Systeme oder AWS-Ressourcen geprüft.

## Review-Plan

Hohes Risiko (Datenbank, Zugangsdaten, produktiver Ingest). Prüfschwerpunkte:

1. CI-Berechtigungen, Abhängigkeits-/Secret-/Konfigurationsscans und Fail-closed-Verhalten
2. VPS-Compose-Profile, Container-Identitäten/-Rechte und Secret-Dateien
3. TLS-Serveridentität und Client-Zertifikate
4. Rückwärtskompatibilität der AWS-Secret-Provider und AWS-Infrastruktur

## Priorität 1 (vor VPS-Produktionsbetrieb) ⛔

### P1 — VPS-Produktions-DSN kann `sslmode=require` statt Identitätsprüfung verwenden

- **Kategorie:** OWASP A02 / Zero Trust
- **Evidenz:** `backend/src/database/connection.py::_ALLOWED_SSLMODES` erlaubt `require`, `verify-ca` und `verify-full`; `_validate_sslmode()` prüft nur die Zulassungsliste. `backend/tests/test_security_policies.py::test_connect_accepts_secure_sslmode` akzeptiert ausdrücklich `require`. `infra/vps/README.md` verlangt für VPS-Datenbankverbindungen `sslmode=verify-full`.
- **Auswirkung:** `require` verschlüsselt, verifiziert aber nicht die Identität des DB-Servers. Eine versehentlich falsch konfigurierte VPS-DSN kann somit trotz erfolgreichem TLS-Test einen fremden Endpunkt akzeptieren.
- **Fix:** Für VPS-Betrieb eine explizite, fail-closed Policy erzwingen, die `verify-full`, vertrauenswürdige CA und den erwarteten Hostnamen `db` verlangt. Nicht unbesehen global `require` aus der gemeinsamen Verbindungsschicht entfernen: AWS-DSNs und `scripts/aws/provision-api-readonly-user.py` verwenden derzeit `require`. AWS-Verhalten erhalten oder separat migrieren.
- **Validierung:** Mit kurzlebiger synthetischer Test-CA und Testzertifikaten in einer isolierten PostgreSQL-Instanz: korrekte CA/SAN/Client-Zertifikat erfolgreich; falsche CA, falscher Hostname, fehlendes/falsches Client-Zertifikat und Klartextverbindung scheitern. Im VPS-Modus `require`, `verify-ca`, fehlendes `sslrootcert` und abweichender Host müssen schon vor Verbindungsaufbau scheitern. AWS-Kompatibilität parallel mit synthetischem AWS-Secret-Mock und bestehendem `require`-Pfad belegen.

## Priorität 2 (CI vor Merge erweitern)

### P2 — Keine gezielte CI-Prüfung der VPS-Compose-Sicherheitsinvarianten

- **Kategorie:** Zero Trust / OWASP A05 / Reliability
- **Evidenz:** `.github/workflows/ci.yml` prüft Terraform nur unter `infra/aws/terraform`. Es gibt keinen expliziten Compose-Config-/Profil-Test oder Test, der Ports, `privileged`, Nutzer, Capabilities, Secret-Mounts und Netzwerke als Merge-Gates festschreibt. Der allgemeine Trivy-Filesystem-Scan ersetzt diese deterministischen Deployment-Invarianten nicht.
- **Auswirkung:** Sicherheitsregressionen wie versehentliches Port-Publishing, Aktivierung des API-Profils, Root-Laufzeit, zusätzliche Capabilities oder Secret-Werte in gerenderten Umgebungen könnten trotz grünem CI zusammengeführt werden.
- **Fix:** Eigenen VPS-Validierungsjob mit Docker Compose CLI und maschinenlesbarer Ausgabe (`docker compose ... config --format json`) ergänzen. Testdaten ausschließlich synthetisch und temporär erzeugen; keine echten Secretwerte, produktive Pfade, `docker inspect` aus produktiven Umgebungen oder Live-AWS-Zugriffe.
- **Prüfbare CI-Tests:**
  1. Für Standardprofil und einzeln/zusammen aktivierte `bootstrap`, `jobs`, `api` Profile `docker compose config --quiet` ausführen; Images als synthetische `repo@sha256:<64 hex>`-Werte, UID/GID als Testzahlen und Hostpfade in einem temporären Verzeichnis einsetzen. Keine Images pullen und keine Container starten.
  2. JSON-Ausgabe mit Python prüfen: Standardprofil startet nur `db`; kein Service hat `ports`; kein `privileged`, `network_mode: host`, Host-PID, Docker-Socket oder beschreibbaren Host-Secret-Mount; `db`, `ingest`, `api` laufen mit den konfigurierten numerischen Nicht-Root-IDs, `read_only`, `no-new-privileges`, `cap_drop: [ALL]`, Ressourcenlimits und den erwarteten privaten Netzwerken. Für `db-volume-init` die eng begrenzte Ausnahme UID 0 plus nur `CHOWN`/`FOWNER`, ohne Netz und ohne Secrets separat erlauben; `db-initdb` muss nicht-root und netzlos bleiben.
  3. Prüfen, dass `api` nur opt-in ist, keine Ports publiziert, keine Ingest-Secrets erhält und nur die getrennten API-Dateien mountet; ein API-Profil darf nicht stillschweigend Teil von `compose up` im Defaultprofil werden.
  4. In einem isolierten temporären Testverzeichnis synthetische Inhalt-Canaries in Dateien schreiben, Compose-Konfiguration rendern und maschinell sicherstellen, dass nur Pfade, nie Datei-Inhalte in `environment`, `command` oder gerenderten Compose-Text auftauchen. Danach Testdateien löschen; keine Canary-Ausgabe in CI-Logs.
  5. Mit Test-DB/Fixture prüfen: fehlende, leere, ungültige oder für die Container-UID unlesbare Secret-Datei bricht fail-closed ab; Fehler enthalten weder Secretinhalt noch DSN/Passwort. Gleichzeitige ENV- und FILE-Quellen müssen abgelehnt werden.

### P2 — Scan-Gates erfassen VPS-Images und VPS-Konfiguration nicht explizit

- **Kategorie:** OWASP A06 / Supply Chain / Zero Trust
- **Evidenz:** CI baut `backend/Dockerfile.api`, prüft dieses Image aber nicht explizit. Das VPS-Compose verweist zusätzlich auf getrennte PostgreSQL-/Ingest-/API-Images. Der dedizierte Trivy-Config-Schritt scannt ausschließlich `infra/aws/terraform`; der vorhandene Dateisystem-Scan ist kein expliziter Compose-Config-Gate und hat ein Schweregradlimit `HIGH,CRITICAL`.
- **Auswirkung:** Verwundbare Basis-/Anwendungs-Images, bekannte Fehlkonfigurationen in Compose oder Secret-Funde unterhalb der gesetzten Trivy-Schwelle können unbemerkt bleiben. Die Image-Tags `python:3.11-slim` in Dockerfiles sind nicht digest-gebunden.
- **Fix:** Expliziten Trivy-Config-Scan für `infra/vps` ergänzen und beide Backend-Images nach dem Build auf Schwachstellen/Secrets scannen; für produktionsfreigegebene Images Digest-Pinning und nachvollziehbare Update-/Rebuild-Prozedur sicherstellen. Secret-Scans (z.B. Gitleaks) getrennt von Trivy-Severity-Schwellen als blockierende Gates betreiben. Findings nur mit begründeter, eng begrenzter Ausnahme unterdrücken.
- **Validierung:** In einem temporären Scratch-Verzeichnis synthetische nicht-produktive Canary-/Fehlkonfigurationsdateien erzeugen und prüfen, dass jeder Scanner mit Fehlercode abbricht; Scanner-Logs dürfen den Canary nicht ausgeben. Separater Negativtest für ein absichtlich verwundbares, öffentliches Testfixture ist nur dann nötig, wenn die Scanner-Integration sonst nicht zuverlässig auf Exit-Code geprüft werden kann; keine echten Secrets und kein produktiver Scan-Upload.

### P2 — CI-Workflow hat keine explizit minimale `GITHUB_TOKEN`-Berechtigung

- **Kategorie:** OWASP A05 / Supply Chain
- **Evidenz:** `.github/workflows/ci.yml` deklariert keine `permissions:`. Der Gitleaks-Schritt erhält `secrets.GITHUB_TOKEN`; mehrere Actions werden nur per Versions-Tag referenziert (`actions/checkout@v6`, `gitleaks-action@v2`, `trivy-action@v0.36.0`).
- **Auswirkung:** Effektive Tokenrechte hängen von Repository-/Organisationsdefaults ab; kompromittierte oder nachträglich verschobene Action-Tags erhöhen den Impact eines CI-Angriffs, insbesondere bei PR-Ausführung.
- **Fix:** Workflow-weit minimale Rechte setzen (grundsätzlich `contents: read`; nur tatsächlich benötigte Zusatzrechte jobbezogen gewähren). Actions auf vollständige Commit-SHAs pinnen und Updates automatisiert/prüfbar pflegen. Keine AWS-Schlüssel oder VPS-Zugangsdaten in PR- oder Scan-Jobs bereitstellen; den für Gitleaks erforderlichen Token auf das Minimum beschränken.
- **Validierung:** CI-Ereignistypen einschließlich Fork-PR prüfen; sicherstellen, dass kein Job schreibende Repository-/Deployment-Rechte oder AWS-OIDC-Zugriff erhält und Secret-Scans dennoch auf Pull Requests laufen.

## AWS-Rückwärtskompatibilität

- Die VPS-Datei-Provider (`COMUNIO_SECRET_FILE`, `DATABASE_URL_FILE`, `AUTH_SECRET_FILE`, `API_PROXY_SECRET_FILE`) sind additive Betriebswege. Tests müssen weiterhin den AWS-ARN-/Secrets-Manager-Pfad (`COMUNIO_SECRET_NAME`, `AUTH_SECRET_ARN`) prüfen und beide Quellen gleichzeitig ablehnen.
- Keine AWS-Terraform-Änderung, kein `plan/apply`, kein Abschalten von API/ECS/RDS und kein Wechsel der AWS-DSN-Policy aus diesem Review ableiten. Die vorhandenen AWS-Validierungs-/Build-Jobs müssen als Regression-Gates erhalten bleiben.
- Ohne AWS-Credentials testen: Secrets-Manager mit synthetischen Testantworten mocken; prüfen, dass VPS-Tests keine AWS-Instanzmetadaten, Default-Credentials oder reale AWS-Endpunkte ansprechen.

## Bereits gute Kontrollen und Restrisiken

- VPS-Compose hat keine veröffentlichten DB/API-Ports; API ist opt-in. Runtime-Services setzen numerische Nutzer, schreibgeschütztes Root-Dateisystem, `cap_drop: ALL`, `no-new-privileges`, Limits und read-only Secret-/TLS-Dateimounts. Der einmalige Volume-Init-Container läuft zwar als UID 0, ist aber nicht `privileged` und hat laut Compose nur eng begrenzte Rechte.
- `pg_hba.conf` weist Klartext-TCP zurück und fordert Client-Zertifikate; die DB hat nur ein internes Netzwerk. Dies belegt noch nicht, dass die tatsächlich gestartete Anwendung Servername und CA korrekt prüft.
- Es gibt in dieser Prüfung keinen Nachweis, dass echte Secrets im Repository liegen oder dass die CI-Scans erfolgreich gelaufen sind. Gitleaks/Trivy-Ergebnisse, Containerlaufzeit als echte IDs, TLS-Negativtests, Backup-/Restore und Host-Monitoring bleiben zu verifizieren.
- Die Ingest-Bridge erlaubt ausgehenden Netzwerkverkehr. Externe Aufrufe sind betrieblich nötig; Egress-Begrenzung/Monitoring und das Verhindern unnötiger Zielverbindungen bleiben Restrisiken.

## Risk Summary

- Critical: 0
- High: 1 (VPS-DSN kann Serveridentität ungeprüft lassen)
- Medium: 3 (VPS-Invarianten nicht CI-geprüft; Scanabdeckung/Image-Supply-Chain; Token-/Action-Härtung)
- Low: 0

## Decision

- **Production Ready:** **No**
- **Blocking Issues:** VPS-`verify-full` im Anwendungspfad fail-closed erzwingen und durch synthetische TLS-Positiv-/Negativtests belegen; VPS-Compose-/Secret-/Image-Gates in CI ergänzen; AWS-Provider und AWS-Betriebsverhalten regressionsprüfen. Zusätzlich gelten die vorhandenen Betriebsblocker (isolierter Restore, Monitoring, Host-Admin/Timer-Freigabe und explizite Cutover-Zustimmung).
- **Tests tatsächlich ausgeführt:** Keine. Review war statische Dateiprüfung; es gab keinen Git-Diff-/Status-, Docker-, Terraform-, CI-, AWS- oder VPS-Zugriff.
