# Sicherheitsreview: Self-hosted Monitoring-Design für den VPS-Betrieb

> **Architekturänderung 20.11.2026:** Diese Bewertung untersucht den
> ursprünglichen Entwurf mit WireGuard über einen öffentlichen Endpunkt.
> Variante 2 im [Monitoring-Plan](../architecture/self-hosted-monitoring-plan.md)
> wurde danach auf ein privates isoliertes L2 als WireGuard-Underlay
> umgestellt. Die nachfolgenden WAN-Port- und Tunnelangaben sind dafür
> historisch; die geänderte L2-Variante benötigt eine separate
> Sicherheitsprüfung vor Implementierung.

**Reviewdatum:** 2026-11-20  
**Umfang:** Repo-basierte Betriebs- und Sicherheitsgrenzen für VPS-API, PostgreSQL, Ingest, Secrets, Caddy/HTTPS, systemd und Docker Compose. Entwurf für Monitoring auf demselben oder einem zweiten VPS.  
**Code-/Live-Änderungen:** Keine. Es wurden weder Live-Systeme noch externe Dienste kontaktiert.  
**Produktionsfreigabe des heutigen Betriebszustands:** **NO-GO für einen unbeaufsichtigten Monitoring-Betrieb, bis Monitoring, Alarmzustellung, Backup-/Restore und die Abnahmetests umgesetzt sind.**  
**Zielarchitektur:** Für zuverlässige Fehlererkennung bevorzugt einen separaten Monitoring-VPS mit eng begrenztem WireGuard-Tunnel. Eine Installation auf demselben VPS ist möglich, aber keine unabhängige Überwachung dieses Hosts.

## Review-Plan

**Risiko: hoch:** Auf dem VPS befinden sich eine persistente Datenbank, API-Zugangsdaten, Comunio-Zugangsdaten, TLS-Private-Keys und ein schreibender Ingest. Eine Monitoring-Installation könnte durch zusätzliche DB-, Host- oder Docker-Rechte eine neue Vertrauensgrenze aufmachen.

Relevante Prüfbereiche:

1. Netzwerkisolation und Zugriffskontrolle für Datenbank, API, Proxy und Exporter (OWASP A01, Zero Trust)
2. Schutz von Secrets, Metriken und Logs vor Offenlegung (OWASP A02/A09, Datenschutz)
3. Least Privilege und Vertrauensgrenzen von Exportern, Host-Agenten und Docker (Zero Trust)
4. Ausfall-, Backup-, Alarmzustellungs- und Wiederherstellungsrisiken (Reliability)
5. Überwachung des täglichen Ingests ohne Erweiterung der Datenzugriffsrechte

## Repo-Befunde und konkrete Grenzen

- `infra/vps/compose.yaml`: PostgreSQL ist nur im internen `database`-Netz, ohne Host-Port. DB-Zugriff verlangt TLS-Clientzertifikat; `pg_hba.conf` lehnt Klartext-TCP ab. API und Ingest haben getrennte Credentials, TLS-Zertifikate und DB-Rollen. Ingest hat zusätzlich ein ausgehendes Netz.
- `infra/vps/compose.https.yaml`/`Caddyfile`: Nur Caddy publiziert 80/443; API bleibt hinter Caddy, API und Proxy kommunizieren über ein eigenes internes Netz. Caddy entfernt `Forwarded` und `CloudFront-Viewer-Address`. Keine Caddy-Admin-API aktivieren oder veröffentlichen.
- `backend/src/api/app.py`: `/health/live` und `/health/ready` sind absichtlich öffentlich; Readiness prüft DB-Erreichbarkeit, aber nicht Authentisierung, vollständige Datenaktualität oder Caddy/TLS. Es existiert kein dedizierter Prometheus-Metrics-Endpunkt.
- `backend/src/ingest/runner.py`/`snapshot_job.py`: Ingest läuft täglich per systemd-User-Timer und speichert Run-Status, Zeit, Ergebnis, Stage, Fehlercode und Schreibanzahl in `ingest_runs`; Logs verwenden eine geschlossene Fehlertaxonomie. Der Host-Lock `flock` verhindert überlappende reguläre manuelle und zeitgesteuerte Runs. Containerlogs sind begrenzt rotiert, nicht langfristig zentralisiert.
- `backend/src/api/repositories.py` und `data_model.md`: API-Daten umfassen Spieler-/Teamdaten, Marktwerte, Punkte und Transfermarkt-Snapshots. `owner_name` ist potenziell personenbezogen und nicht ohne Freigabe öffentlich zu verwenden. API-DB-Rolle ist read-only, aber für Monitoring nicht hinreichend eng, da sie lesenden Zugriff auf alle Tabellen erhalten kann.
- `infra/vps/README.md` dokumentiert als noch offen: Monitoring/Alarmierung, regelmäßige Backups und Restore-Monitoring sowie VPS-Speicherverschlüsselung. Der Betrieb akzeptiert derzeit das Risiko nicht erkannter Ausfälle; es gibt keine Routinechecks.

## Sicherheitsbefunde

### Hoch — Monitoring/Alarmierung und Backup-/Restore-Überwachung fehlen noch

- **Kategorie:** Reliability / Zero Trust / Datenschutz & Verfügbarkeit
- **Evidenz:** `infra/vps/README.md`, „Deployment validation checklist and remaining work“ sowie „Outstanding operational work“; Backup-Scheduling, Monitoring und Alarmzustellung sind ausdrücklich offen. Der Ingest-Timer läuft täglich um 06:00 UTC (`infra/vps/systemd/comunio-ingest.timer`).
- **Auswirkung:** API-, DB-, Datenträger-, Timer-, Ingest- und Backupfehler können unbemerkt bleiben; ein grüner Container-Healthcheck sagt weder aus, dass ein Tageslauf erfolgreich war, noch dass die Daten aktuell sind. Ein lokaler Monitoring-Stack fällt bei Hostausfall zusammen mit dem Zielsystem aus.
- **Fix:** Separaten Monitoring-VPS mit Prometheus, Alertmanager, Grafana, Blackbox Exporter und optional Loki/Alloy vorsehen. Alarm auf ausgebliebene erfolgreiche Ingest-Runs und Backupfehler. Bei gleicher VPS-Installation externe oder unabhängige Zustellung für Hostausfälle vorsehen und die verbleibende fehlende Unabhängigkeit ausdrücklich akzeptieren. Backup-/Restore-Alarmierung nicht vor Implementierung regelmäßiger, überprüfbarer Backups als erledigt betrachten.
- **Validierung:** Host-/API-/DB-Ausfall, fehlender Tageslauf, Ingest-Fehler, voller Datenträger, ausgefallener Backupjob und nicht erreichbarer Alarmempfänger jeweils gezielt in einer Testumgebung auslösen; Alarmempfang, Runbook und Recovery dokumentieren.

### Hoch — Direkte DB- oder Docker-Hostrechte für das Monitoring würden die bestehende Least-Privilege-Grenze umgehen

- **Kategorie:** A01 Broken Access Control / Zero Trust
- **Evidenz:** `compose.yaml` isoliert `db` im internen `database`-Netz und beschränkt API-Zugang auf eine eigene `comunio_api_readonly`-Rolle; das Runbook warnt, dass Zugriff auf Docker-Socket bzw. Docker-Gruppe effektiv Root-Zugriff ist. Ein Monitoring-DB-Principal oder Monitoring-Exporter existiert nicht.
- **Auswirkung:** Ein privilegierter Exporter, eine kompromittierte Grafana-Instanz oder ein Monitoring-Secret mit Ingest-/API-Zugriff könnte sensible Daten lesen oder den Host übernehmen. Einfach Prometheus oder Grafana an das interne DB-Netz anzuschließen, schafft unnötige Netzwerkreichweite. Die bestehende API-Leserolle ist keine ausreichende Least-Privilege-Monitoring-Rolle.
- **Fix:** Keine Docker-Socket-Mounts, kein `privileged`, kein Host-PID-/Host-Netzwerk für Grafana, Prometheus oder Loki. Für Hostmetriken einen separaten, möglichst unprivilegierten node_exporter mit explizit ausgewählten Collectors einsetzen. Falls DB-Metriken nötig sind: separater DB-Exporter mit eigener PostgreSQL-Rolle, TLS-Clientzertifikat und nur erforderlichen Monitoringrechten. Für Ingest-Status Datenbankrechte soweit möglich auf notwendige Spalten der `ingest_runs` begrenzen oder ein lokales, nicht geheimnishaltiges systemd-Heartbeat-Textfile verwenden. Exporter nicht öffentlich und nur für den Monitoring-Peer erreichbar machen.
- **Validierung:** DB-Rolle mit Negativtests (keine SELECTs auf fachliche Tabellen, keine Schreib-/DDL-Rechte) prüfen; gerenderte Compose-Konfiguration auf Socket, Host-Modi, Privilegien und ungewollte DB-Netz-Mitgliedschaft testen. Von einer nicht autorisierten Quell-IP müssen Exporter-Ports geschlossen sein.

### Mittel — Öffentliche Health-Endpunkte sind kein vollwertiger Monitoring- oder Sicherheitsnachweis

- **Kategorie:** OWASP A01/A09 / Informationsminimierung
- **Evidenz:** `backend/src/api/app.py` lässt `/health/live` und `/health/ready` ohne Authentisierung passieren; `/health/ready` führt `SELECT 1` aus. Die Endpunkte sind über die öffentliche API erreichbar.
- **Auswirkung:** Die Readiness gibt eine begrenzte Information zur DB-Verfügbarkeit preis und kann von außen abgefragt werden. Sie deckt keine erfolgreiche Authentisierung, Datenfrische, täglichen Ingest oder Backup-Erfolg ab. Ein zusätzlicher Metrics-Endpunkt mit Datenlabels wäre eine deutlich größere Offenlegung.
- **Fix:** Bestehende Health-Endpunkte nur als minimale Blackbox-Checks verwenden. Keine Secrets, SQL-Fehler, IDs, Versionen oder Dateninhalte darin ausgeben. Prometheus-Metriken ausschließlich über private Tunnel-/Exporter-Endpunkte bereitstellen; nicht pauschal einen öffentlichen `/metrics`-Pfad hinzufügen. Wenn Health-URLs öffentlich bleiben, Abfragevolumen/Verfügbarkeit beobachten und nur Statuscodes plus Latenzen auswerten.
- **Validierung:** Anonyme Health-Antworten auf minimale Inhalte prüfen; Tests auf keine DB-Fehlerdetails, Header, Credentials oder personenbezogenen Werte. Öffentliche Scans dürfen keinen Exporter- oder Prometheus-Port finden.

### Mittel — Zentralisierte Logs und Labels können Zugangsdaten, IPs oder personenbezogene Daten unnötig dauerhaft speichern

- **Kategorie:** A02 Cryptographic Failures / A09 Logging & Monitoring / Datenschutz
- **Evidenz:** `runner.py` loggt Run-IDs, Fehlerklassen, Stages und Schreibanzahlen; Compose rotiert JSON-Logs lokal. `Caddyfile` hat derzeit keine Access-Log-Konfiguration. Der Datenbestand beinhaltet Transfermarkt-Besitzernamen (`owner_name`), die das Datenmodell als potenziell personenbezogen einstuft. Das Runbook verbietet ausdrücklich Secrets, DSNs, private Schlüssel, Datenbankdumps und Rohantworten in Logs.
- **Auswirkung:** Ungefilterte Access-Logs oder individuelle Metriklabels können IP-Adressen, URLs/Queryparameter, Benutzernamen oder fachliche Daten länger und an weitere Systeme verbreiten als beabsichtigt. Ein kompromittiertes Logsystem würde darüber hinaus Secrets offenlegen, falls sie jemals in Logs gelangen.
- **Fix:** Nur für Betrieb notwendige Events übertragen; keine Request-/Response-Bodies, Cookies, `Authorization`, DSNs, Secret-Dateien oder Roh-Fehler. Query-Strings und unnötige Client-IP in Proxy-Logs unterdrücken oder anonymisieren. Metriklabels auf stabile, nicht personenbezogene Dimensionen begrenzen (Service, Statusklasse, Stage); niemals Spieler-/Team-/Besitzer-IDs oder Namen, Token, IPs oder beliebige URL-Pfade als Labels. TLS über den Tunnel, restriktive RBAC, kurze begründete Aufbewahrung, verschlüsselte Datenträger/Backups und dokumentierte Löschung für Loki festlegen.
- **Validierung:** Synthetische Secrets, Cookie-/Authorization-Header, Query-Strings und personenbezogene Testwerte durch Requests/Fehlerpfade führen und prüfen, dass weder Agent, Prometheus, Loki, Alerts, Dashboards noch Backup sie speichern. Retention-/Löschtest dokumentieren.

## Zielarchitektur und Werkzeuge (kostenlos, selbst betrieben)

**Empfehlung für einen zweiten VPS:** Prometheus (Metriken und Regeln), Alertmanager (Routing), Grafana (Dashboards), Blackbox Exporter (HTTPS-Checks); optional Loki plus Grafana Alloy für begrenzte Logs. Auf dem Produktions-VPS: node_exporter, cAdvisor nur wenn Containermetriken wirklich benötigt werden, DB-Exporter optional und ein Ingest-Heartbeat. Komponenten sind Open-Source/free-to-self-host; Kosten für VPS, Speicher, Traffic und mögliche externe Benachrichtigungswege bleiben bestehen. Keine Cloud-Agenten, Telemetrie-Cloud oder SaaS-Abhängigkeit voraussetzen.

**Monitoring-Minimum:** Erreichbarkeit von API `/health/live` und `/health/ready` über HTTPS; Status/Latenz des öffentlichen Endpunkts; VPS CPU/RAM/Disk/Inodes; Containerstatus/Restart und Docker-Storage; PostgreSQL-Liveness/Verbindungen/Platz; letzter erfolgreicher Ingest (UTC-Zeitstempel), letzter Fehler und Alter der jüngsten fachlichen Daten; Backup-Erfolg, Alter des letzten erfolgreichen Backups und freier Backup-Speicher. Readiness allein ist kein ausreichender DB- oder Ingest-Alarm.

**Datenfrische/Heartbeat:** Für die sichere Anfangsversion ist ein hostlokaler systemd-Erfolgsmarker vorzuziehen: nur bei bestätigtem erfolgreichem geplantem Snapshot den Zeitstempel aktualisieren und durch node_exporter textfile collector exportieren. Ein Login-Test oder manueller Lauf darf nicht als geplanter Tageserfolg gelten. Der Marker allein belegt keine fachliche Datenfrische. Separat aus systemd-Journal/Service-Status Fehler und fehlenden Lauf alarmieren; keine Journal-Rohinhalte als Prometheus-Labels verwenden. Falls fachliche Prüfung der DB erforderlich ist, einen separaten TLS-DB-Monitoring-Principal mit minimalem Spaltenzugriff auf `ingest_runs` entwerfen und nur aggregierte Zustände nach außen geben. Die bestehende API-DB-Rolle mit SELECT auf alle Tabellen nicht wiederverwenden.

**Alarmbeispiele:** API nicht erreichbar über mehrere Minuten; Bereitschaft fehlerhaft; fehlender erfolgreicher Ingest bis zu einer festgelegten Karenz nach 06:00 UTC; letzter Ingest fehlgeschlagen oder ungewöhnlich geringe Datensatzanzahl; PostgreSQL/Container wiederholt neu gestartet; Root-/Docker-Disk oder Inodes kritisch; Zertifikat läuft bald ab; Backup älter als RPO, Backupjob fehlgeschlagen oder Restore-Probe überfällig; WireGuard-Peer/Exporter nicht erreichbar. Alertmanager benötigt `for`-Zeiten, damit kurze Neustarts nicht alarmieren, und einen getesteten „Dead man's switch“/Heartbeat zum unabhängigen Empfänger.

## Netzwerk- und Firewall-Design

Portnummern für Exporter sind Entwurfsbeispiele; nur tatsächlich aktivierte Dienste freischalten. Firewall sowohl beim VPS-Anbieter als auch auf dem Host konsistent konfigurieren; IPv4 und IPv6 gleichermaßen prüfen. Default inbound deny; established/related erlauben. Hostmanagement über explizit freigegebene Operator-IP-Adressen oder VPN, nicht aus dem Monitoring-Netz.

### Variante A — Monitoring auf demselben VPS

| Quelle → Ziel | Port/Protokoll | Richtung/Freigabe | Zweck / Grenze |
|---|---:|---|---|
| Internet → VPS | TCP 80/443 | Eingehend, nur Caddy | Bestehende öffentliche API. Kein API-, DB-, Exporter-, Grafana- oder Prometheus-Port. |
| freigegebene Operator-IP/VPN → VPS | TCP 22 | Eingehend, eng allowlisted | SSH-Administration; Schlüssel/SSH-CA, kein Passwortlogin sofern möglich. Nicht Monitoring-Exporter freigeben. |
| VPS → Internet | TCP 443, DNS/NTP eng begrenzt | Ausgehend nach Bedarf | ACME, OS-/Image-Updates, Comunio/API und ggf. Alertempfänger; kein pauschal offenes Inbound. |
| Prometheus → Exporter | interne Compose-Netze oder Loopback | Intern | Nur dedizierte Metrikendpunkte. Exporter nicht an öffentliche Hostinterfaces binden. |
| Caddy → API | internes `api-ingress`-Netz | Intern | Bestehender Reverse-Proxy-Pfad bleibt unverändert. |
| API/Ingest → DB | internes `database`-Netz, TLS/Clientzertifikat | Intern | Bestehende Rollen und HBA-Regeln; keine Weiterleitung vom Monitoring-Stack. |
| Grafana-Admin → Grafana | Loopback oder Operator-VPN | Eingehend intern | Kein direkt öffentliches Dashboard. SSH-Tunnel/VPN für Zugriff; unabhängige starke Admin-Identität. |
| Alertmanager → Benachrichtigung | ausgehend TLS | Ausgehend | Auf den expliziten Empfänger begrenzen. Ein rein lokaler Empfänger kann VPS-Ausfall nicht melden. |

Exporter dürfen weder Caddy-/API-Ports noch Docker-Socket öffnen. Compose-Isolation beibehalten: nicht das gesamte Monitoring an `database` hängen. Wo Prometheus- und Exporter-Container getrennte Netze benötigen, nur den einzelnen Exporter an die nötigen Netze anschließen. Für Hostmetriken Host-Agent und Binding so wählen, dass kein öffentlicher Listener entsteht.

**Verbleibender Nachteil:** VPS-Ausfall, Host-Firewallfehler, voller Datenträger, Kernel-/Docker-Ausfall und Verlust des gesamten Monitoring-Volumes legen Ziel und Monitoring gemeinsam lahm. Lokale Alertmanager-Queues, Dashboards und Logs sind ebenfalls nicht außerhalb dieses Ausfallbereichs gesichert. Diese Variante eignet sich nur bei ausdrücklicher Akzeptanz, dass ein kompletter VPS-Ausfall nicht automatisch von diesem Stack alarmiert werden kann.

### Variante B — Separater Monitoring-VPS (empfohlen)

| Quelle → Ziel | Port/Protokoll | Richtung/Freigabe | Zweck / Grenze |
|---|---:|---|---|
| Internet → Produktions-VPS | TCP 80/443 | Eingehend, nur Caddy | Bestehender öffentlicher API-Verkehr. |
| feste Monitoring-VPS-IP → Produktions-VPS | UDP 51820 (Beispiel) | Eingehend, einzige neue öffentliche Freigabe | WireGuard-Handshakes; alternativ anderer explizit festgelegter WG-Port. Kein Monitoring-Service direkt im WAN. |
| Monitoring-VPS (WireGuard-IP) → Produktions-VPS (WireGuard-IP) | TCP 9100/8080/9187 oder vereinbarte Exporterports | Über Tunnel, Quelle auf einzelne Monitor-IP begrenzen | Pull von Host-/Container-/DB-Metriken; nur eingeschaltete Exporter. Auf Zielhost und Cloud-Firewall auf WG-Interface/-IP beschränken. |
| Produktions-VPS (WireGuard-IP) → Monitoring-VPS (WireGuard-IP) | TCP 3100, optional | Über Tunnel, nur wenn Loki-Push gewählt | Einweg-Logtransport zum Loki-Ingest; nur von Produktions-Peer. Ingress nicht im öffentlichen Interface. |
| Operator-IP/VPN → Monitoring-VPS | TCP 22 und Grafana 3000 | Eingehend allowlisted bzw. VPN | Grafana nur über Operator-VPN/SSH-Tunnel; 9090 Prometheus, 9093 Alertmanager, 3100 Loki und Exporter nicht öffentlich. |
| Monitoring-VPS → Produktions-API | TCP 443 | Ausgehend TLS | Blackbox-Check des öffentlichen HTTPS-Endpunkts. Keine Zugangsdaten/Cookies mitsenden; nur minimale Health-URLs. |
| Monitoring-VPS → Produktions-Exporter | TCP über WG | Ausgehend, nur feste Peer-IP/Ports | Prometheus-Scrapes. Scrape-Identität zusätzlich durch Firewall/Tunnel begrenzen; Prometheus nicht auf dem Produktions-VPS exponieren. |
| beide Hosts → jeweilige Paket-/Zeit-/DNSziele | ausgehend nur erforderliche Ziele | Ausgehend | WireGuard-Endpoint, Updates, DNS/NTP und ausdrücklich gewählte Alertkanäle. |
| Produktions-VPS → Monitoring-VPS | keine allgemeine Route | Nicht routen | Kein Standardgateway über WG; kein Zugriff auf andere Monitor- oder Operator-Netze; IPv4/IPv6-Routen explizit begrenzen. |
| beliebige Internetquelle → DB/API-Uvicorn/Exporter/Grafana/Prometheus/Loki | 5432/8000/Exportermetriken/3000/9090/9093/3100 | Verweigern | Niemals öffentlich publizieren oder als Portweiterleitung konfigurieren. |

**Tunnel:** WireGuard mit separatem zufälligem privaten Schlüssel je VPS, festen Tunnel-Adressen, exakten `/32`-`AllowedIPs` für Peer-Routen, `PersistentKeepalive` nur falls NAT dies erfordert; kein `0.0.0.0/0`/`::/0` und kein allgemeiner Transit zwischen Netzen. Falls ein Prometheus-Container die Verbindung über den Monitoring-Host benötigt, ausschließlich dafür erforderliche Weiterleitung und gegebenenfalls SNAT gezielt erlauben und testen. Auf dem Produktions-VPS `wg0`-Firewall: nur Monitor-WireGuard-IP darf definierte Exporter erreichen; auf dem Monitor nur Produktions-Peer darf den ggf. aktivierten Loki-Ingest erreichen. SSH/Grafana sind nicht durch den Produktions-Peer erreichbar. Private Schlüssel nur root-lesbar, außerhalb Git und Compose-Umgebungsvariablen; Backup mit Zugriffsschutz. Peer-Key-Rotation/Widerruf vorab dokumentieren. WireGuard authentisiert Peers, ersetzt aber weder Firewall noch Exporter-Authentisierung/least privilege.

Prometheus ist bevorzugt Pull-basiert: Ein Tunnel-/Peer-Ausfall macht Targets „down“, ohne dass ein öffentlich erreichbarer Push-Endpunkt auf dem Produktiv-VPS benötigt wird. Loki ist optional Push-basiert und verlangt explizite Beschränkung auf den Tunnelpeer sowie TLS-/Authentisierung innerhalb des Tunnels oder zusätzliche mTLS. Für eine kleinere Betriebsfläche zunächst Metriken und Blackbox-Checks umsetzen, Logs später nur bei definiertem Zweck und Datenschutzkonzept ergänzen.

## Identitäten, Geheimnisse und Zugriff

- **Menschen:** getrennte Operator-Identität für Monitoring, rollenbasierte Dashboard-Rechte, MFA soweit verfügbar, keine anonymen Grafana-Dashboards. Produktions-SSH und Monitoring-SSH getrennte Schlüssel/Principals. Zugriff auf Docker-Socket bleibt als Root-äquivalent behandelt.
- **Maschinen:** WireGuard-Schlüssel pro VPS; eigener, enger DB-Monitoring-Principal, falls nötig; getrennte Loki-Ingest-Identität bzw. mTLS, falls Logs gepusht werden; keine Wiederverwendung des API-Proxy-Secrets, API-JWT-Secrets, Ingest-DB-URLs oder TLS-Clientschlüssels.
- **Secrets:** außerhalb Repository und Image, restriktive Dateirechte/UID, read-only in Container gemountet, keine CLI-Argumente, keine `docker inspect`-Environment-Secrets, keine Alertinhalte mit Werten. Zertifikate, WireGuard-Schlüssel, Grafana-Admin-Initialpasswort und Alert-Empfänger-Credentials rotierbar speichern.
- **Monitoring-DB-Rolle:** nur optional und erst nach Rollen-/Spaltenprüfung. Nur TLS mit dediziertem Zertifikat und Zertifikat-CN passend zur Rolle. Keine Superuser-/Ingest-Rechte, keine Schreibrechte; kein Zugriff auf `players`, `transfermarket_snapshots`, `owner_name`, Credentials oder vollständige fachliche Zeilen. Wenn notwendige Einschränkung nicht praktikabel ist, nur Host-/Service-Heartbeat überwachen und DB-Metrikumfang weglassen.
- **Datenminimierung:** keine Tokens, Cookies, Rohantworten, Request-Bodies, DSNs, Personen-/Spielernamen oder Datenbankinhalte in Metriken, Labels, Logs, Dashboards oder Alarmtext. Caddy-Logs nur nach expliziter Datenschutzentscheidung aktivieren; Pfad-/Query- und IP-Daten minimieren. Prometheus-Labels mit unbeschränkter Kardinalität vermeiden.
- **Speicherung:** Retention und Löschfristen pro Metriken/Logs konfigurieren; Metrik- und Logvolumes vor Hostdisk-Füllung schützen. Verschlüsselung im Transport (WireGuard plus TLS wo sinnvoll), bei ruhenden Daten bevorzugt verschlüsselte VPS-Volumes und verschlüsselte externe Backups. Ein verschlüsseltes Backup von Monitor-Konfiguration und ein Restore-Test sind erforderlich.

## Ausfall- und Betriebsrisiken

1. **Selber VPS:** keine unabhängige Erkennung von Host-/Provider-/Kernel-Ausfall. Monitoring kann den überwachten Dienst zusätzlich belasten; Retention kann Disk-Füllung verursachen. Benachrichtigung über einen Empfänger auf demselben Host ist nicht belastbar.
2. **Zweiter VPS:** zusätzlicher monatlicher Aufwand und Patch-/Backup-/TLS-/Firewall-Betrieb; Tunnel-, Routing-, Zeit- und Peer-Key-Probleme können falsche Down-Alerts erzeugen. Monitoring-VPS oder Tunnel wird zum neuen hochprivilegierten Angriffsziel, daher keine DB-Admin- oder Docker-Hostrechte dorthin geben.
3. **Alarmkanal:** vollständig selbst gehostete Zustellung kann nicht zuverlässig den gleichzeitigen Ausfall ihres eigenen Hosts melden. Für unabhängige Zustellung entweder Alertmanager auf dem zweiten VPS und dessen Benachrichtigung zu einem separaten, verfügbaren Ziel (z. B. bestehender Maildienst/Pushkanal) oder unabhängigen dritten Heartbeat-Empfänger wählen. Das externe Ziel ist eine bewusste Ausnahme von „vollständig selbst gehostet“; andernfalls die Lücke ausdrücklich akzeptieren.
4. **Backups:** Monitoring ersetzt kein Datenbankbackup. Es muss sowohl Backup-Jobstatus als auch Backup-Alter/Integrität und regelmäßig praktisch getestete Wiederherstellung überwachen. Niemals DB-Dumps ungeprüft nach Grafana/Loki übertragen.
5. **Konfigurationsdrift:** Änderungen an Firewall, Docker Compose, IPv6, DNS, VPS-IP, Tunnel-Keys, Zertifikaten und API-Domain können Scrapes oder Schutzregeln unbeabsichtigt öffnen. Regelmäßige Außen- und Tunnel-Portprüfungen in Abnahme-/Änderungsprozesse aufnehmen.

## Abnahme- und Sicherheitstests (keine Tests im Rahmen dieses Reviews ausgeführt)

1. **Bestandsaufnahme:** reale IPv4-/IPv6-Listener, VPS-Provider-Firewall und Host-Firewall autorisiert inventarisieren. Erwartung: öffentlich nur Caddy 80/443, SSH nur aus freigegebenem Adminpfad und bei Variante B ein WireGuard-UDP-Port auf dem Produktions-VPS für den Monitoring-Peer. `5432`, `8000`, Grafana, Prometheus, Alertmanager und Exporter sind extern geschlossen.
2. **Netzwerk-Negativtests:** aus nicht autorisiertem Internet, aus beliebiger anderer Quell-IP und vom nicht autorisierten Tunnelpeer auf jeden Exporter-/Admin-/DB-Port testen; Verbindung muss scheitern. Über WG muss nur die definierte Peer-IP die ausgewählten Exporter erreichen. Tunnel darf weder Default-Route noch fremde Subnetze routen.
3. **Identität/Secrets:** WireGuard-Peer mit falschem/entzogenem Schlüssel ablehnen; Schlüsselrotation nachweisen. Dateirechte und Container-Mounts prüfen. API-, Ingest-, DB- und TLS-Secrets dürfen nicht in Compose-Renderings, Logs, Labels, Alertmanager-Text oder Metrikwerten erscheinen.
4. **DB-Rechte:** dedizierter Monitoring-Principal (falls genutzt) muss erwartete aggregierte Monitoringabfrage ausführen können, aber fachliche Tabellen/Spalten und jede Schreib-/DDL-Operation verweigern. Falsches oder abgelaufenes Clientzertifikat und Klartextverbindung müssen abgewiesen werden.
5. **Daten-/Datenschutz:** Beispielrequest mit sensiblen Queryparametern, Auth-Cookie, Authorization-Header und synthetischem Owner-/Spielernamen erzeugen; keine Speicherung in zentralen Logs, Metriklabels, Dashboards, Alerts oder Backups. Retention- und Löschtest durchführen.
6. **Alarmierung:** In Staging nacheinander API-Down, DB-Down, fehlenden/fehlgeschlagenen Ingest, niedrige Schreibzahl, Disk-/Inode-Schwelle, fehlendes Backup und Tunnel-Down auslösen. Karenzen, Deduplizierung, Wiederherstellung/Resolved-Meldung und tatsächliche Zustellung testen. Für gleichen VPS den nicht erkannten Totalverlust und für zweiten VPS den Ausfall des Alertempfängers ausdrücklich prüfen.
7. **Resilienz:** Neustart von Monitor/Agent/Exporter und WireGuard, voller Metrikspeicher, unzugängliches Loki und ungültige Grafana-Konfiguration simulieren. Ziel-API und Ingest dürfen davon nicht blockiert werden; Prometheus-Volumen darf nicht die Produktionsdisk füllen. Monitor-Konfiguration/Backups wiederherstellen.
8. **Runbooks:** Alarmowner, Bereitschafts-/Kontaktpfad, Ingest-Nachholung, Zertifikats-/Peer-Rotation, Backuprestore und manuelle Überbrückung bei Monitor-Ausfall dokumentieren.

## Empfehlung und Produktionsentscheidung

- **Bevorzugt:** separater zweiter VPS, WireGuard mit Default-Deny und festem Peer-/Port-Allowlisting, Prometheus Pull über den Tunnel und nicht öffentliche Exporter; Grafana nur für Operator-VPN/SSH-Tunnel. Optional erst später eng begrenzte Logübertragung.
- **Zulässig mit dokumentierter Einschränkung:** gleicher VPS, wenn Kosten/Einfachheit über unabhängige Erkennung gestellt werden und ein externer/ausgelagerter Alarmempfänger vorhanden ist. Kein Dashboard/Exporter im öffentlichen Netz und keine zusätzlichen DB-/Docker-Rechte.
- **NO-GO bis zur Umsetzung:** Monitoring ohne getestete Alarmzustellung; Öffnung von DB-/API-/Exporter-Ports im WAN; Einsatz des API-DB-Users oder von Docker-Socket/Root für Monitoring; ungefilterter Export von Proxy-/Anwendungslogs; fehlender Ingest-/Backup-Frischealarm.
- **Keine Live-Validierung:** Firewall, aktive Listener, tatsächliche Zertifikate, VPS-Firewall und Zustand der Systeme wurden nicht untersucht. Die dokumentierte VPS-Konfiguration und README sind Repo-Evidenz, keine Bestätigung der Laufzeit.

## Risikozusammenfassung

- Kritisch: 0 bestätigte
- Hoch: 2 (fehlendes Monitoring/Alarmierung; neues Monitoring darf DB-/Docker-Grenzen nicht erweitern)
- Mittel: 2 (öffentliche Health-Endpoints als begrenzte Info; Datenschutz-/Retentionrisiko bei Log-/Metrikexport)
- Niedrig: 0

## Entscheidung

- **Produktionsreif für den bestehenden Betriebszustand mit unbeaufsichtigtem Betrieb:** **Nein.**
- **Empfohlene Zielvariante:** separater Monitoring-VPS mit WireGuard-Tunnel und unabhängiger Alarmzustellung.
- **Blocker zur Abnahme:** enges Firewall-/Peer-Allowlisting; getrennte Identitäten und Secrets; keine allgemeinen DB-/Docker-Rechte; bewiesene minimale Telemetrie; getestete Ingest-, DB-, Disk-, Backup- und Alarmfälle; dokumentierte Ausfall- und Restorepfade.
- **Restrisiken:** Ausfall des Monitoring-VPS bzw. Benachrichtigungskanals; falsch positive/negative Alarme; Provider-/Kernel-Ausfall; Datenleck durch unbeabsichtigte Log-/Label-Kardinalität; keine Repo-Evidenz für effektive Live-Firewall-/IPv6-Regeln oder vorhandene externe Alarmziele.
