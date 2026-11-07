# Code Review: Vercel-Proxy → VPS API Client-IP-Vertrauen

**Reviewdatum:** 2026-11-07  
**Umfang:** Frontend-API-Routen, Login-Formular, Backend-Proxy-Authentifizierung und Login-Rate-Limit. Keine Live-Vercel-/VPS-Prüfung; keine Dateien der Anwendung oder Infrastruktur geändert.  
**Produktionsentscheidung:** VPS-Go-live **nur mit behobenem Rate-Limit-Vertrauenspfad**. AWS-Verhalten nicht ungeprüft ändern, da die AWS-API live ist.

## Codepfad und Vertrauensgrenzen

1. `frontend/components/auth/LoginForm.tsx` sendet Login an same-origin `POST /api/auth/login`.
2. `frontend/app/api/auth/[...path]/route.ts` erlaubt ausschließlich `login`, `logout`, `me`; baut für den Upstream eine Header-Allowlist auf, reicht `Cookie`, `Origin` und `Content-Type` weiter und ergänzt `Authorization: Bearer <API_PROXY_SECRET>` serverseitig. Die Route leitet derzeit **keine** Client-IP- oder Forwarding-Header weiter.
3. Datenabfragen laufen über `frontend/lib/api/client.ts` zu `/api/proxy/...`; `frontend/app/api/proxy/[...path]/route.ts` erlaubt nur GET, reicht Session-Cookie und serverseitiges Proxy-Secret weiter und setzt ebenfalls keine Client-IP-Header.
4. `frontend/proxy.ts` überspringt `/api/*`; sein Cookie-Existenzcheck schützt nur Seiten, nicht API-Routen. Die Backend-JWT-Prüfung und das Proxy-Bearer-Secret bleiben die Sicherheitsgrenze.
5. `backend/src/api/app.py` verlangt das Proxy-Bearer-Secret für `/auth/*` und `/api/v1/*`. Danach nutzt `backend/src/api/auth.py::_login_client_ip()` ungeprüft `CloudFront-Viewer-Address`, sofern vorhanden, andernfalls `request.client.host`. Das Loginlimit ist pro Prozess im Speicher (5 Versuche/5 Minuten).

## Befund — VPS-Loginlimit erhält keine verifizierte Endnutzer-IP

- **Schweregrad:** Mittel (Verfügbarkeit / Zero Trust)
- **Evidenz:** Die Vercel-Routen reichen keine IP-Header weiter. Beim VPS-Backend ist daher die beobachtete Peer-Adresse die Vercel-Egress-Adresse oder – hinter lokalem Reverse Proxy – dessen Peer-Adresse. Der aktuelle Code vertraut weiterhin jedem ankommenden `CloudFront-Viewer-Address`-Header, ohne den Peer zu prüfen.
- **Auswirkung:** Ein per-IP-Limit kann alle Nutzer unter derselben Vercel-/Proxy-Peer-IP in einen Bucket legen. Fünf fehlgeschlagene Logins können dann legitime Logins für fünf Minuten blockieren. Umgekehrt darf ein beliebiger `X-Forwarded-For`-/CloudFront-Wert nicht ungeprüft übernommen werden.
- **AWS-Abgrenzung:** In der vorhandenen AWS-Architektur wird `CloudFront-Viewer-Address` innerhalb der CloudFront→ALB-Vertrauensgrenze verwendet. Die live AWS-API darf durch eine globale Codeänderung nicht unbeabsichtigt gebrochen werden. AWS- und VPS-Vertrauenspfade müssen explizit getrennt konfiguriert sein.

## Ist Client-IP über Vercel verifizierbar?

**Nicht durch den aktuellen Vercel→VPS-Request und nicht durch einen beliebigen weitergereichten Header.** Der VPS kann aus `X-Forwarded-For` allein nicht erkennen, ob der Wert vom Browser, von Vercel oder einem anderen Proxy stammt. Die Vercel Function kann möglicherweise eine Plattform-Client-IP-Metadatenquelle lesen; Repository-Code und Tests belegen weder deren Verfügbarkeit noch, dass Vercel clientgelieferte gleichnamige Header zuverlässig überschreibt. Das muss anhand des zum Deployment passenden Vercel-Vertrags geprüft und mit einem echten Deployment getestet werden. Es ist keine Ende-zu-Ende kryptographische Client-IP-Bescheinigung.

## Umsetzbare Empfehlung

1. **Jetzt Header-Allowlist beibehalten:** Keine rohen `Forwarded`, `X-Forwarded-For`, `X-Real-IP` oder `CloudFront-Viewer-Address` vom Browser übernehmen. Das derzeitige explizite Weiterleiten ausgewählter Header ist eine gute Grenze.
2. **Vercel-Eingangsrate begrenzen:** Login-Rate-Limit am Vercel-Eingang oder in der Auth-Route mit einem geteilten, persistenten Limiter durchsetzen. Als IP-Schlüssel ausschließlich eine von Vercel dokumentierte und verifizierte Ingress-IP-Quelle verwenden; rohe Clientheader ignorieren. Wenn dieser Nachweis nicht möglich ist, Vercel-Edge-/Firewall-Schutz und zusätzliche account-/globalbasierte Limits verwenden, nicht eine erfundene Backend-Client-IP.
3. **Optionales IP-Attest nur bei verifiziertem Vercel-Metadatum:** Die Vercel-Route entfernt alle eingehenden IP-Header und setzt einen einzelnen normalisierten `X-Verified-Client-IP`-Wert aus der geprüften Plattformquelle. Backend akzeptiert ihn nur im dedizierten VPS-Modus und nur auf dem authentisierten Server-zu-Server-Pfad mit `API_PROXY_SECRET`; andernfalls Peer-Adresse verwenden. Ein beliebiger Headername oder das Bearer-Secret allein macht einen ungeprüften IP-Wert nicht vertrauenswürdig.
4. **VPS-Netzpfad eng halten:** API nur hinter HTTPS und nicht direkt öffentlich; Uvicorn vertraut bei lokalem Reverse Proxy nur dessen konkrete Adresse (`forwarded-allow-ips`), niemals `*`. Statische Egress-Allowlisting nur einsetzen, wenn Vercel-Egress tatsächlich fest und für das Projekt verfügbar ist. AWS-CloudFront-Vertrauen separat erhalten.
5. **Backend-Limiter ergänzen:** Bestehendes Prozesslimit nicht als alleinige VPS-Abwehr betrachten. Proxy-/Edge-IP-Limit mit account-/globalbasiertem Schutz kombinieren; shared state nutzen, wenn mehrere Worker/Instanzen oder Neustartresilienz erforderlich sind.

## Tests vor VPS-Go-live

- Frontend-Vitest für beide Proxy-Routen: gefälschte `Forwarded`, `X-Forwarded-For`, `X-Real-IP` und `CloudFront-Viewer-Address` erscheinen nicht im Upstream-Request; Bearer-Secret erscheint nie in Browserantworten.
- Vercel-Staging-End-to-End: echte Ingress-IP über den bestätigten Vercel-Metadatenpfad; parallel Requests mit gefälschten Headern senden und nachweisen, dass die Zuordnung unverändert bleibt. Ohne verifizierbare Plattformquelle darf keine client-IP-basierte Backend-Zuordnung aktiviert werden.
- Backend-Tests: VPS-Modus ignoriert CloudFront-/XFF-Header von nicht vertrauenswürdigen Peers; nur gültige, konfigurierte Proxy-Attestierung kann einen Client-IP-Bucket setzen. AWS-Modus behält den CloudFront-Vertrag.
- Rate-Limit-Test über mindestens zwei Function-/Backend-Instanzen: Grenzwert wird geteilt; fünf Angriffe von einer Quelle beeinträchtigen nicht andere Quellen. Wiederholungen mit wechselnden gefälschten Headern umgehen das Limit nicht.
- Direkter VPS-Aufruf ohne Proxy-Bearer wird abgewiesen; Backend-Port ist extern nicht erreichbar. Origin-/CORS-Prüfungen nicht als Ersatz für Proxy-Authentifizierung werten.

## Entscheidung

- **VPS-Produktion:** Noch nicht freigabefähig, bis Vercel-IP-Quelle und Login-Limiter end-to-end validiert sind oder eine Alternative ohne Backend-Client-IP eingerichtet ist.
- **AWS live:** Bestehenden CloudFront-Vertrauenspfad separat beibehalten; kein ungetesteter globaler Headerwechsel.
