# Sicherheitsreview: Geplantes automatisches VPS-CD-Deployment

**Reviewdatum:** 2026-11-20  
**Umfang:** Repo-basierte CI- und VPS-Konfiguration, Betriebs-Runbook und dokumentierte Deployment-/Rollback-Verfahren. Es wurde keine Implementierung eines CD-Workflows vorgenommen.  
**Produktionsfreigabe für automatisches CD:** **NO-GO bis die P1-Entscheidungen umgesetzt und getestet sind.**  
**Bestätigte aktive Exploits in der vorhandenen CI:** 0. Die festgestellten P1-Risiken sind fehlende Sicherheitsentscheidungen und Vertrauensketten für das geplante Deployment, keine Behauptung, dass aktuell ein Workflow ungeschützt produktiv deployed.

## Review-Plan

**Risikoeinstufung: hoch.** Das Zielsystem enthält Produktionsdatenbank, Zugangsdaten, API und einen schreibenden Ingest. Geprüfte Kategorien:

1. GitHub-Actions-Berechtigungen, Trigger, Branch-/Environment-Freigaben und Secrets
2. Deploy-Authentisierung, SSH-Host-Authentizität und VPS-Rechte
3. Build-/Artifact-Integrität und Supply Chain
4. Rollback, Datenbankmigrationen und parallele Deployments

## Befundlage

In `.github/workflows/` existiert aktuell nur `ci.yml`; ein VPS-CD-Workflow, SSH-Aufruf, Registry-Publish oder Deployment-Credential ist im Repository nicht vorhanden. Die bestehende CI hat bereits gute Basiskontrollen: `.github/workflows/ci.yml` setzt global `permissions: contents: read`, beschränkt CodeQL separat auf `security-events: write`, pinnt Actions auf vollständige Commit-SHAs und verwendet bei Checkout `persist-credentials: false`. Die PR-Jobs erhalten im Workflow keine expliziten VPS-Secrets. Diese Maßnahmen sollten erhalten bleiben.

Das VPS-Runbook schreibt nicht geheime Compose-Inputs, hostseitige Secret-Dateien und unveränderliche Image-Referenzen vor (`infra/vps/README.md`, „Files and host-only inputs“ und „Safe prerequisites“). Es weist auch ausdrücklich darauf hin, dass Zugriff auf den Docker-Socket bzw. die Docker-Gruppe effektiv Root-Zugriff bedeutet. Es beschreibt jedoch derzeit einen manuellen Betrieb, keine vollständige Authentisierungs-, Freigabe- oder Artifact-Vertrauenskette für CD.

## Priorität 1 — Vor Aktivierung von automatischem Produktions-CD ⛔

### P1 — CI-Testartefakt und auf dem VPS ausgeführtes Image sind nicht kryptografisch verknüpft

- **Kategorie:** Supply Chain / Zero Trust / OWASP A08
- **Evidenz:** `.github/workflows/ci.yml` baut API- und Ingest-Images und protokolliert deren IDs („Record built image IDs“); es gibt keinen Registry-Publish-, Signatur-, Attestierungs- oder Deployment-Job. Das Runbook dokumentiert für den 16.11.2026 ein „lokal[]“ aus Commit `bb72b90` gebautes Ingest-Image, das auf den VPS geladen wurde (`infra/vps/README.md`, Betriebsverlauf). Die VPS-Konfiguration soll zwar immutable Referenzen verwenden, aber eine unveränderliche Referenz allein beweist weder Herkunft noch bestandene CI.
- **Risiko/Auswirkung:** Ein lokaler Neubau, ein vertauschtes Image oder ein kompromittierter Veröffentlichungsweg kann unbemerkt ein anderes Image als das geprüfte CI-Image ausrollen. Die aktuellen Image-IDs werden lediglich geloggt und sind kein wiederverwendbares, überprüfbares Release-Artefakt. Zusätzlich verwenden `backend/Dockerfile` und `backend/Dockerfile.api` `FROM python:3.11-slim` ohne Digest; `apt-get upgrade` bezieht beim Build jeweils den dann aktuellen Paketstand. Derselbe Commit ist dadurch nicht zwingend reproduzierbar.
- **Vorschlag:** Einmal in einem vertrauenswürdigen Build-Job bauen und testen/scannen; anschließend genau diese Images in eine Registry veröffentlichen und per `repository@sha256:…` deployen. Für jedes Release eine überprüfbare Build-Provenance/Attestation (Repository, geschützter Ref, Workflow-Lauf, Commit und Image-Digest) und SBOM erzeugen; VPS-seitig nur freigegebene Digests und erwartete Provenance akzeptieren. Für Basis-Images Digest-Pinning und kontrollierte Update-/Rebuild-Prozedur vorsehen. Keine Quellcode-Rebuilds auf dem VPS und keine Deployments per mutable Tag.
- **Validierung:** Negativtests mit falschem Digest, nicht freigegebener Workflow-Herkunft und verändertem Manifest müssen den Rollout vor dem Start ablehnen. Nach erfolgreicher Bereitstellung müssen Commit, Workflow-Lauf und laufende Image-Digests aus einem Auditpfad eindeutig zusammenpassen. Registry-Retention muss mindestens aktives und letztes freigegebenes Rollback-Image erhalten.

### P1 — SSH-Authentisierung, Remote-Rechte und Host-Key-Prüfung sind für CD nicht festgelegt

- **Kategorie:** Zero Trust / A07 Identität und Zugriffskontrolle
- **Evidenz:** Es gibt keinen SSH-/CD-Workflow und keine dokumentierten SSH-Key-, `known_hosts`- oder Host-Key-Rotationswerte. Das Runbook benennt `serveradmin` als existierenden Betreiberaccount und erklärt, Docker-Gruppenzugehörigkeit sei Root-äquivalent (`infra/vps/README.md`, „Safe prerequisites“). Ein automatisierter Account samt wirksamer Berechtigungsbegrenzung ist nicht spezifiziert.
- **Risiko/Auswirkung:** Ein unbeschränkter SSH-Schlüssel oder ein Deployment-Account mit uneingeschränktem Docker-Zugriff wird praktisch zum Root-Zugang. Ohne geprüften Host-Key könnte ein MITM- oder DNS-/Routing-Angriff CI dazu bringen, Deployment-Material an einen fremden Host zu senden. Eine Workflow-Variable oder ein Eingabefeld, das beliebige Remote-Befehle annimmt, würde den VPS zusätzlich in einen allgemeinen Remote-Execution-Endpunkt verwandeln.
- **Vorschlag:** Einen getrennten Deployment-Principal festlegen, nicht den persönlichen `serveradmin`-Zugang. Bevorzugt kurzlebige SSH-Zertifikate über eine explizit abgesicherte SSH-CA-Integration; falls nicht verfügbar, einen dedizierten, rotierbaren Schlüssel ausschließlich in einer geschützten GitHub-`production`-Environment. Keine Produktionscredentials für PR- oder Fork-Workflows. Serverseitig keine interaktive Shell/PTY, Agent-/X11-/Port-Weiterleitung oder freie Befehle; nur einen root-eigenen, eng begrenzten Deployment-Einstieg mit validiertem Release-Manifest zulassen. Da Docker-Rechte root-äquivalent sind, keinen scheinbar unprivilegierten Docker-Gruppenzugang als Sicherheitsgrenze behandeln. Den SSH-Host-Key/Fingerprint außerhalb des Deployments verifizieren und als festes `known_hosts`-/Host-Key-Material hinterlegen; `StrictHostKeyChecking=yes` verwenden. **Nicht** zur Laufzeit unbestätigtes `ssh-keyscan` als Vertrauensanker nutzen.
- **Validierung:** Mit falschem/rotiertem Host-Key muss SSH vor Authentisierung abbrechen. Der Deployment-Principal darf weder beliebige Shell-Kommandos noch TTY-/Tunnelzugriff erhalten. Key-Widerruf/Rotation und Wiederherstellung müssen ohne Änderung an Anwendungsecrets getestet sein.

### P1 — Kein festgelegter GitHub-Freigabepunkt und kein Secret-Modell für Produktionsdeployments

- **Kategorie:** Zero Trust / OWASP A05 / Secret Management
- **Evidenz:** `.github/workflows/ci.yml` wird auf `push` zu `main`/`master` und `pull_request` ausgeführt, hat derzeit aber keinen Deployment-Job. Branch Protection, verpflichtende Reviewer, geschützte Tags und ein GitHub-Environment `production` sind in den geprüften Workflow-Dateien nicht definiert. Das Runbook verlangt, dass Anwendungsecrets auf dem VPS verbleiben und nicht in Git, CI-Artefakte, Shellargumente, Service-Environment oder Logs gelangen (`infra/vps/README.md`, „Files and host-only inputs“).
- **Risiko/Auswirkung:** Wird CD direkt an PR-Ereignisse oder ungeprüfte Branches gekoppelt, können nicht vertrauenswürdige Änderungen Deployment-Credentials auslesen oder Produktionscode ausführen. Ein statischer, breit einsetzbarer Schlüssel oder VPS-Anwendungssecrets in GitHub würde die CI als zusätzliche Produktions-Secret-Angriffsfläche etablieren.
- **Vorschlag:** Nur erfolgreich geprüfte Commits aus einem geschützten Hauptbranch oder explizit geschützten Release-Tag deployen. Vor Produktionszugriff ein GitHub-Environment mit Branch-/Tag-Allowlist und obligatorischer unabhängiger Freigabe verlangen. Produktionsdeployments nie aus `pull_request_target` oder durch unvalidierte Artefakte eines PR-`workflow_run` starten. Workflow-weite Rechte minimal belassen; `packages: write` ausschließlich im Build-/Publish-Job und nur erforderliche Deployment-Rechte im Deploy-Job. `id-token: write` nur dann jobbezogen erteilen, wenn es konkret für kurzlebige Authentisierung verwendet wird. GitHub erhält keine DB-, Comunio-, API- oder TLS-Secrets; diese bleiben in den bestehenden hostseitigen Dateien. Ein eventuelles Registry-Pull-Token auf dem VPS ist separat und nur lesend auf die benötigten Pakete beschränkt.
- **Validierung:** Fork-PR und nicht geschützte Branches dürfen weder auf Deployment-Secrets zugreifen noch einen VPS-Zugriff auslösen. Ein Produktionslauf ist ohne Review/Freigabe nicht möglich. Action- und Workflow-Berechtigungen für jeden Event-Typ prüfen und sicherstellen, dass kein allgemeines PAT oder unnötiges `contents: write`/`packages: write` an Testjobs gelangt.

### P1 — Rollback ist nicht transaktional und Datenbankzustand ist nicht durch Image-Rollback rückgängig

- **Kategorie:** Verfügbarkeit / Datenintegrität / Reliability
- **Evidenz:** Das Runbook empfiehlt, vorherige Images aufzubewahren und bei Fehlern vorherige Image-Referenzen zu verwenden; bei Migrationen warnt es ausdrücklich, dass ein Restore neuere Daten verwerfen kann (`infra/vps/README.md`, „Player points upgrade“). Die Produktionsdatenbank ist persistent; der Dokumentationsstand nennt regelmäßige Backups und Monitoring weiterhin als offen (`infra/vps/README.md`, Betriebsstatus und „Deployment validation checklist“). Ein automatischer Gesundheits-, Rollback- oder Migrationsvertrag ist nicht vorhanden.
- **Risiko/Auswirkung:** Ein automatischer App-Rollback allein behebt keine inkompatible oder teilweise ausgeführte Migration. Eine automatische DB-Wiederherstellung kann seit dem Backup geschriebene Produktionsdaten vernichten. Ohne Erfolgskriterien kann ein Rollout trotz defekter API als erfolgreich gelten oder bei parallelen Ausführungen einen inkonsistenten Versionsstand hinterlassen.
- **Vorschlag:** Auto-Rollback auf den vorherigen freigegebenen API-/Ingest-Digest und die vorherige Release-Konfiguration begrenzen; niemals automatisch die Produktionsdatenbank zurücksetzen oder einen Backup-Restore starten. Schemaänderungen nach Expand/Contract mit zunächst rückwärtskompatiblen Releases gestalten; destruktive Migrationen, DB-Restores und Änderungen mit unklarer Rückwärtskompatibilität aus dem unbeaufsichtigten CD ausnehmen und als separates genehmigtes Operationsverfahren behandeln. Vor DB-Änderungen müssen Backup-/Restore-Verfahren, Aufbewahrung und Alarmierung festgelegt und ein Restore praktisch nachgewiesen sein. Gesundheitstests und API-/Ingest-spezifische Erfolgskriterien vor Freigabe definieren.
- **Validierung:** Fehler vor/nach Containerwechsel und während einer Migration in isolierter Umgebung simulieren. App-Rollback darf weder persistente Volumes löschen noch DB-Restore auslösen; Datenintegrität, API-Erreichbarkeit und wiederhergestellte Image-Digests sind nachzuweisen. Backup-/Restore-Probe und Rollback-Protokoll vor Produktionsfreigabe dokumentieren.

## Priorität 2 — Vor erstem automatischem Rollout festlegen

### P2 — Deployment-Konkurrenz und manuelle Operatorläufe müssen synchronisiert werden

- **Kategorie:** Zero Trust / Reliability / Datenintegrität
- **Evidenz:** `infra/vps/systemd/comunio-ingest@.service` verwendet `flock` für den Ingest; das Runbook verbietet direkte Compose-Starts und verlangt während dokumentierter Migrationen denselben Ingest-Lock (`infra/vps/README.md`, „systemd user timer and shared lock“ und „Player points upgrade“). Für konkurrierende GitHub-Deployments existiert keine Concurrency-Regel, und ein gemeinsamer Host-Lock zwischen künftiger CD, Operatoren und systemd ist nicht spezifiziert.
- **Risiko/Auswirkung:** Zwei Deployments oder ein Deployment parallel zu Migration/Ingest können Release-Referenzen überschreiben, Services mit gemischten Versionen hinterlassen oder den Datenbankzustand während einer Änderung belasten. Der bestehende Ingest-Lock allein ist keine allgemeine Deployment-Sperre.
- **Vorschlag:** GitHub-seitig einen einzelnen Produktions-Concurrency-Group verwenden und keine laufenden Deployments automatisch abbrechen. Zusätzlich einen Host-seitigen exklusiven Deployment-Lock etablieren, den gleichermaßen CD und unterstützte manuelle Operationsverfahren verwenden; bestehende Ingest-Sperre in Migrations-/Schemafenstern ausdrücklich berücksichtigen. Keine unkoordinierten direkten `docker compose`-Rollouts.
- **Validierung:** Zwei gleichzeitige Deploymentanforderungen und ein Rollout während aktivem Ingest müssen definiert serialisiert oder vor jeder Änderung fail-closed abgelehnt werden. Nach Abbruch/Timeout muss der Host-Lock sicher freigegeben werden; Releasezustand bleibt eindeutig.

### P2 — Image-Scan-Ergebnis ist nicht automatisch ein ausreichendes Release-Gate

- **Kategorie:** OWASP A06 / Supply Chain
- **Evidenz:** `.github/workflows/ci.yml` gibt alle HIGH/CRITICAL-Befunde für API-/Ingest-Images aus, hat für den allgemeinen Berichtsschritt `exit-code: 0`; ein gesonderter Schritt blockiert nur fixierbare HIGH/CRITICAL-Befunde. Das ist eine sichtbare und teilweise blockierende Kontrolle, aber kein dokumentierter Freigabeschwellenwert für ein Produktionsrelease.
- **Risiko/Auswirkung:** Nicht behobene, derzeit nicht fixierbare HIGH/CRITICAL-Befunde können trotz erfolgreichem Job enthalten sein. Ein künftiger CD-Workflow könnte ein Image deployen, ohne Ausnahmen, Scannerstatus oder Freigabe zu prüfen.
- **Vorschlag:** Freigabekriterien für Scannerstatus, offene Alerts und zeitlich begrenzte Risikoausnahmen explizit definieren. Ein fehlgeschlagener/übersprungener Scanner darf kein Release freigeben. Scans müssen den exakt zu deployenden Digest prüfen; Laufzeitschutz oder erneutes Bauen nach dem Scan ersetzt dieses Gate nicht.
- **Validierung:** Testen, dass Scanfehler und nicht genehmigte Findings den Release-/Deploy-Job blockieren und genehmigte Ausnahmen dokumentiert, ablaufend und eng auf konkrete Befunde begrenzt sind.

## Zielbild und Reihenfolge für den Hauptagenten

1. **Noch keinen automatischen VPS-Zugang in CI aktivieren.** Zuerst Freigabeprozess, Branch-/Tag-Schutz, GitHub-Environment und Deployment-Principal festlegen.
2. **Build once, deploy by digest:** erfolgreiche CI baut und scannt ein Image, veröffentlicht es unveränderlich mit Herkunftsattestierung/SBOM; Produktionsfreigabe deployt denselben Digest und keine lokale VPS-Neuerstellung.
3. **VPS als kontrollierter Executor:** fest verifizierter SSH-Host-Key, beschränkte Authentisierung, keine PR-Secrets und kein allgemeiner Remote-Shellzugang; hostseitige Secrets bleiben unverändert außerhalb des Releases.
4. **Deployment atomar und serialisiert:** vorab geprüfte Release-Manifestdatei, Produktionsfreigabe, GitHub- und Host-Locks, readiness checks, Auditspur und Rollback nur für Anwendungsversionen.
5. **DB-Verfahren getrennt behandeln:** rückwärtskompatible Migrationen automatisierbar machen, destructive Änderungen/Restore explizit aus dem Standard-CD ausnehmen, Backup-/Restore- und Alarmierungsrisiko vor Freigabe schließen oder ausdrücklich akzeptieren lassen.

## Annahmen und Grenzen

- **Annahme:** Gemeint ist zunächst ein automatisches Deployment der Backend-Images/Compose-Konfiguration auf den VPS. Die bereits automatisierte Vercel-Frontend-Deploymentkette ist nicht als VPS-SSH-Deployment bewertet.
- **Annahme:** Ein künftiger Workflow soll Zugriff auf die Produktionsumgebung erhalten. Der Repo-Stand belegt nicht, welche GitHub-Branch-Protection-, Environment- oder Organisationsrichtlinien außerhalb der Dateien eingerichtet sind.
- **Annahme:** Der VPS zieht Images selbst oder erhält sie über einen Registry-Zugang. Repository und Runbook bestimmen den finalen Transportweg nicht; jede Wahl muss dieselben Digest-/Provenance-Gates einhalten.
- **Nicht geprüft:** Live-GitHub-Einstellungen, tatsächliche Secrets, VPS-SSH-Daemon-/Firewallkonfiguration, GitHub-Environment-Reviewer, Registry-Zugriffsrechte, aktuelle Images und Live-Rollbackfähigkeit. Kein Test, Deployment oder externer Zugriff wurde ausgeführt.

## Risikozusammenfassung

- Kritisch: 0 bestätigte
- Hoch: 4 Design-/Freigabeblocker für automatisches Produktions-CD
- Mittel: 2 (Concurrency/Locking, Release-Gate für Scanbefunde)
- Niedrig: 0

## Entscheidung

- **Produktionsreif für automatisches VPS-CD:** **Nein — bis alle P1-Punkte entschieden, umgesetzt und getestet sind.**
- **Derzeitiger Bestand:** CI enthält bereits gute minimale Berechtigungen und Action-SHA-Pins; es wurde kein bestehender VPS-CD-Workflow und keine aktive CI-SSH-Authentisierung gefunden. Daher kein bestätigter aktueller CI-zu-VPS-Exploit.
- **Blockierende Freigaben:** Herkunfts-/Digestbindung der exakt geprüften Images; abgesicherte GitHub-Freigabe und Secret-Grenze; authentischer VPS-Host-Key und begrenzte Remote-Rechte; getesteter App-Rollback ohne automatischen Datenbank-Restore.
