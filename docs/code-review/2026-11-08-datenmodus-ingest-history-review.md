# Code Review: Datenmodus – Ingest-Historie und Datenstand

**Reviewdatum:** 2026-11-08  
**Umfang:** Read-only, featurebezogene Sicherheits-Designprüfung. Geprüft wurden Repository-Dokumentation und bestehende API-/Proxy-Sicherheitsleitlinien auf hoher Ebene. Frontend-Komponentenbäume und Backend-Routenimplementierung wurden bewusst nicht geprüft. Keine Feature-Implementierung, Live-Systeme oder Deployment-Konfiguration getestet.  
**Produktionsreife:** **Bedingtes NO-GO bis die Kriterien unten implementiert und getestet sind.** Dies ist keine Feststellung eines konkreten Fehlers im nicht geprüften Feature-Code.

## Review-Plan

Risiko: mittel bis hoch. Ingest-Zeitpunkte und Resultate sind Betriebsmetadaten; Fehlerdetails können interne Infrastruktur- oder Dateninformationen offenlegen.

1. Authentisierung, Autorisierung und vertrauenswürdige Proxy-Grenze
2. Minimierung und sichere Darstellung von Betriebsdaten/Fehlern
3. Lesbarkeit, Pagination, Missbrauchs- und Verfügbarkeitsrisiken
4. HTTP-, CSRF-, Cache- und Anti-Enumeration-Eigenschaften

## Sicherheitskontext

Die Backend-Dokumentation beschreibt eine versionierte, read-only API mit begrenzter Pagination. Vorhandene Reviews dokumentieren für den API-Zugriff eine serverseitige Proxy-Grenze sowie Backend-Authentisierung; der Cookie-Existenzcheck für Seiten ist ausdrücklich nicht die API-Sicherheitsgrenze. Das neue Feature sollte diese bestehenden Kontrollen nutzen, nicht umgehen. CORS oder ein verborgenes UI-Element sind keine Autorisierung.

## Design-Gates / empfohlene Änderungen

### P1 — Betriebsmetadaten nur nach expliziter Autorisierung ausliefern

- **Kategorie:** OWASP A01 Broken Access Control / Zero Trust
- **Evidenz:** Das Feature soll Ingest-Versuche und deren Ergebnisse anzeigen. Die Feature-Routen und deren Berechtigungsprüfung waren ausdrücklich nicht Teil dieser Prüfung; daher ist der effektive Zugriff ungeprüft.
- **Risiko:** Unberechtigte Nutzer könnten Aktivitätsmuster, Datenaktualität oder Betriebsfehler ableiten. Ein nur im UI versteckter Link verhindert keinen direkten API-Aufruf.
- **Sichere Kriterien:** Den Abruf über dieselbe authentisierte API-/Proxy-Grenze wie geschützte Daten führen. Backend-seitig Sitzung/Token und gegebenenfalls Rolle oder Mandant prüfen; Autorisierung bei jedem Request, nicht anhand eines vom Client gelieferten Nutzer- oder Run-Identifiers. Falls Betriebsdaten nur für Betreiber bestimmt sind, serverseitig eine entsprechende Berechtigung verlangen. API-Antworten nicht aus einer öffentlichen oder gemeinsam genutzten Cache-Schicht bedienen.
- **Validierung:** Ohne Anmeldung, mit ungültiger/abgelaufener Sitzung und mit gültiger Sitzung ohne nötige Rolle jeweils Zugriff verweigern. Einen direkten API-Aufruf unabhängig von der UI testen. Keine Daten in Fehlerantworten für nicht autorisierte Nutzer.

### P1 — Antwort auf notwendige, freigegebene Metadaten begrenzen; Fehler sanitizen

- **Kategorie:** OWASP A01/A04/A05 – Datenminimierung und sichere Fehlerbehandlung
- **Evidenz:** Angeforderte Inhalte umfassen Historie/Resultate; Umfang und Datenfelder der geplanten Antwort sind nicht spezifiziert und wurden nicht im Code geprüft.
- **Risiko:** Rohmeldungen, Stacktraces, Quell-Payloads oder Infrastrukturdetails könnten Zugangsdaten, personenbezogene Daten, interne Pfade/Hostnamen, SQL oder Scrape-Inhalte offenlegen.
- **Sichere Kriterien:** Eine explizite Antwort-Allowlist definieren, zum Beispiel: UTC-Zeitpunkt, festes Status-Enum, Laufart, wenige aggregierte Zähler sowie ein stabiler, generischer Fehlercode. Den „aktuellen Datenstand“ aus einem erfolgreichen/committeten Datenlauf ableiten und seine Zeitzone sowie Bedeutung dokumentieren; fehlende oder veraltete Daten ausdrücklich als solche kennzeichnen. Keine Roh-Exception, Tracebacks, frei formulierten externen Fehlermeldungen, Credentials, URLs, Dateipfade, SQL, Quell-Datensätze oder unnötigen Identifikatoren zurückgeben. Fehlercodes serverseitig auf kurze, feste, nutzerverständliche Texte abbilden. Diagnosedetails allenfalls in zugriffsbeschränkte Logs mit Redaction schreiben; niemals Secretwerte loggen.
- **Validierung:** Fixture mit synthetischen Secret-/PII-Canaries in externem Fehlertext und Payload verwenden und sicherstellen, dass weder API-Antwort noch UI diese Werte enthalten. Testen, dass Fehlerfälle nur freigegebene Codes/Felder ausgeben.

### P2 — Historie begrenzen und Abrufe vor Enumeration/Last schützen

- **Kategorie:** OWASP A04 Insecure Design / Verfügbarkeit
- **Evidenz:** Die bestehende API dokumentiert eine maximale Seitengröße von 100; die Historienabfrage und ihre Filter-/Sortierparameter wurden nicht geprüft.
- **Risiko:** Unbegrenzte Historienabrufe oder teure freie Filter können Daten unnötig offenlegen und Datenbank/API durch wiederholte Abrufe belasten. Sequenzielle Run-IDs oder frei abfragbare IDs können Enumeration erleichtern.
- **Sichere Kriterien:** Begrenzte Standard- und Maximal-Seitengröße (z.B. 20 und höchstens 100), stabile Sortierung mit serverseitigem Cursor oder begrenztem Offset, passende DB-Indizes und definierte Aufbewahrungsgrenze. Nur erforderliche Filter zulassen; keine frei erratbaren Detail-Endpunkte, wenn eine Liste genügt. Rate Limits nach authentisiertem Principal und ergänzend global/Ingress anwenden, nicht ausschließlich anhand ungeprüfter Client-IP-Header. Bei Listen keine unnötig präzisen internen Sequenzen oder fremden Nutzer-/Mandanteninformationen ausgeben.
- **Validierung:** Grenzen, ungültige Cursor, leere/letzte Seite, stabile Sortierung und parallele wiederholte Abrufe testen; Datenbankabfrage für maximale Seite auf akzeptable Laufzeit/Plan prüfen. Rate-Limit-Verhalten über mehrere Worker/Instanzen berücksichtigen.

### P2 — Read-only-Abruf und CSRF-/Cache-Verhalten eindeutig halten

- **Kategorie:** OWASP A01 / A05 / Zero Trust
- **Evidenz:** Die angefragte Interaktion ist ein Klick auf „Datenmodus“; es ist nicht festgelegt, ob dieser lediglich Status lädt oder versehentlich einen Ingest auslösen könnte.
- **Risiko:** Ein per Cookie authentisierter, zustandsändernder GET-Aufruf wäre CSRF-anfällig und könnte durch Prefetching, Crawler oder Wiederholung ausgelöst werden. Gemeinsames Caching kann eingeloggte Resultate anderen Nutzern zeigen.
- **Sichere Kriterien:** Der Klick darf nur einen idempotenten GET zum Lesen auslösen; keine Ingest-Ausführung oder sonstige Mutation. `Cache-Control: private, no-store` für nutzer- oder betriebsbezogene Antworten setzen. Wenn später ein Ingest manuell ausgelöst werden soll: separater POST, strengere Rolle, CSRF-Schutz (Origin-Prüfung plus geeignetes Token bei Cookie-Authentisierung), SameSite-Cookie-Policy, Auditierung, Idempotenz und Rate Limit. CORS allein ist kein CSRF-Schutz.
- **Validierung:** GET darf Datenbankzustand nicht ändern und ein UI-Refresh darf keinen Lauf starten. CSRF-Negativtests für jeden späteren schreibenden Request; Response-Header und Cache-Verhalten prüfen.

## Empfohlene Tests vor Freigabe

- Authentisierung/Autorisierung serverseitig: anonym, abgelaufen, unberechtigte Rolle und erlaubte Rolle; direkter API-Aufruf statt UI-only-Test.
- Antwort-Allowlist und Fehler-Redaction mit synthetischen Secrets, PII, Stacktrace und externen Fehlermeldungen.
- Datenstandssemantik: letzter erfolgreicher Commit, fehlgeschlagener/nebenläufiger Lauf, keine Läufe, veralteter Stand und UTC-/Zeitzonenanzeige.
- Pagination-/Rate-Limit-Grenzen, stabile Sortierung und DB-Leistungsprobe bei maximaler Seite.
- GET bleibt rein lesend; keine Mutation beim Öffnen, Refresh, Prefetch oder Wiederholen. `no-store` für Antworten prüfen.
- Falls ein Auslösen von Ingest später ergänzt wird: getrennte Rollen-, CSRF-, Idempotenz-, Audit- und Missbrauchstests.

## Risikoübersicht

- Kritisch: 0 bestätigte
- Hoch: 0 bestätigte
- Mittel: 0 bestätigte
- Niedrig: 0 bestätigte
- **Offene Freigabepunkte:** Zugriffskontrolle, Antwortfelder, Fehlerbehandlung, Pagination/Rate Limits und Laufzeitverhalten sind mangels Implementierungsprüfung nicht verifiziert.

## Entscheidung

- **Produktionsreif:** **Nein, noch nicht nachgewiesen.**
- **Blockierend:** Vor Freigabe die P1-Kriterien für Autorisierung und Datenminimierung implementieren und testen; zusätzlich Pagination, Ratenbegrenzung sowie strikt read-only-/Cache-Verhalten verifizieren.
- Diese gezielte Designprüfung fand keine bestätigte Schwachstelle im Feature-Code, da die konkreten Routen und UI-Komponenten außerhalb des vereinbarten Prüfungsumfangs lagen.

## Nachtrag: Prüfung des konkreten Feature-Vertrags (2026-11-08)

Der vorgeschlagene Vertrag (`GET /api/v1/ingest/runs`, authentisiert, read-only, begrenzte Pagination; definierte Felder; geschlossenes `error_code`; Same-Origin-Proxy; kein Ingest beim Öffnen/Refresh) ist grundsätzlich sicherheitsorientiert und adressiert die wesentlichen Datenminimierungsrisiken.

**Must-change vor Freigabe:** „Authenticated“ und „same-origin frontend proxy“ allein legen keine Backend-Autorisierung fest. Das Backend muss auf jedem Abruf die bestehende gültige Nutzeridentität bzw. eine explizit definierte Berechtigung verifizieren; Proxy-Bearer oder Same-Origin dürfen nicht als alleiniger Nachweis der Endnutzerberechtigung gelten. Falls alle angemeldeten Nutzer die Betriebsdaten sehen dürfen, muss dies eine bewusste Autorisierungsentscheidung sein.

Weitere sichere Vertragsdetails:

- `run id` nur zurückgeben, wenn die UI ihn benötigt; dann opak und nicht sequenziell/erratbar, ohne darin interne Daten zu kodieren.
- `stage`, `type`, `status` und `error_code` ausschließlich aus serverseitigen Allowlisten. Zähler nichtnegativ und plausibel begrenzen. Zeitstempel in UTC; `current_data_date` als Datum des letzten erfolgreich committeten Datenstands definieren, nicht als Zeitpunkt des letzten Versuchs.
- Pagination mit harter Maximalgröße, deterministischer Sortierung und validiertem Cursor; keine beliebig teuren ungebegrenzten Offsets. Abrufe rate-limiten und Antworten mit `Cache-Control: private, no-store` versehen.
- Der GET bleibt ohne Seiteneffekt. Cookie-basierte Authentisierung und Same-Origin-Konfiguration dürfen keine permissive CORS-Freigabe oder gemeinsam gecachte Antworten erlauben.

**Minimale Freigabetests:** (1) unauthentisiert/abgelaufen/ohne erforderliche Berechtigung abweisen, einschließlich direktem Backend-Aufruf und Aufruf durch den Frontend-Proxy; (2) Response-Schema-Allowlist sowie ungültige/unerwartete Fehlercodes testen, mit Secret-/Traceback-Canaries in synthetischen Fehlern; (3) Pagination-Maximum, ungültigen/manipulierten Cursor, stabile Reihenfolge und Rate Limit prüfen; (4) GET und UI-Öffnen/Refresh dürfen keinen Runner/Job auslösen oder Daten verändern; (5) `no-store` und fehlende Cross-Origin-Freigabe für diese geschützte Antwort verifizieren.

**Bewertung des Vertrags:** Kein weiterer grundsätzlicher Blocker, sofern die Autorisierungspräzisierung und die genannten Grenzen Bestandteil der Implementierung werden. Die Feature-Implementierung selbst wurde weiterhin nicht geprüft.

## Final-Code-Verifikation (2026-11-08)

**Umfang:** Bounded inspection of the feature endpoint, auth/cache middleware, repository query, schemas, ingest registration/runner, migration, frontend dialog/client/proxy, and relevant tests. No files outside this feature path were broadly reviewed. Tests were inspected but not executed.

### Finding resolved

#### Low — Proxy error responses did not explicitly carry no-store (resolved)

- **Category:** OWASP A05 / cache privacy
- **Evidence:** The `api_not_configured` and `api_timeout` `NextResponse.json()` branches initially lacked an explicit cache policy.
- **Fix/validation:** Both branches now set `Cache-Control: private, no-store, max-age=0`. Proxy tests pass for successful upstream responses, missing configuration, and upstream timeout.

### Non-blocking scalability note

The endpoint caps page size at 100 and orders by `(started_at DESC, id DESC)` with a matching index. It accepts an unbounded nonnegative offset and calculates `COUNT(*)` on each request. Given the stated authenticated single-user audience and expected small run history, this is **not a current security finding or release blocker**. Reassess if run history grows substantially, the endpoint gains more users, or observed query latency warrants keyset pagination, retention limits, or avoiding exact totals.

### Gates verified

- Backend requires the authenticated session and, when configured, the server-side proxy bearer; tests verify proxy credentials alone do not replace the session.
- API response model excludes `error_message`; type/status/stage/error code are closed enums or mapped to safe unknown values. Repository selects only the allowlisted columns; the legacy raw `error_message` column is not selected.
- Migration `004_ingest_run_status_metadata.sql` adds only `stage`/`error_code` and an ordering index. No raw error field was added.
- Dialog fetches only on open/page/retry; `getIngestRuns` uses the read-only GET client path. UI tests cover opening, pagination and retry; no ingest trigger is present in the inspected component.
- `snapshot_job._mark_ingest_run()` commits after updating the run. On success, this commits the preceding snapshot writes and success status together; my prior concern that the success path was uncommitted was incorrect.
- Normal API/proxy upstream responses and local proxy error responses carry no-store. Frontend tests passed (33 tests), including proxy failure cases; ESLint passed.

**Corrected final recommendation:** No remaining blocker identified in the inspected feature path. Pagination remains a non-blocking scalability consideration for the stated single-user deployment.
