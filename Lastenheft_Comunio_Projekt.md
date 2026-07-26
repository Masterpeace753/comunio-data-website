Lastenheft — Comunio Projekt

1. Projektübersicht

Das Comunio-Projekt zielt darauf ab, eine moderne, skalierbare und benutzerfreundliche Plattform für Fantasy-Fußball bereitzustellen. Die Plattform soll Nutzern ermöglichen, Fußballteams zu verwalten, Spielertransfers durchzuführen, Statistiken einzusehen und mit anderen Teilnehmern zu interagieren. Das Projekt umfasst sowohl Backend- als auch Frontend-Entwicklung, Datenintegration, Sicherheitskonzepte und Betriebsanforderungen.

2. Ausgangslage

Die bestehende Comunio-Plattform weist technische und funktionale Einschränkungen auf, darunter Performance-Probleme, eingeschränkte Skalierbarkeit und veraltete Benutzeroberflächen. Ziel ist es, eine neue, robuste Architektur zu entwickeln, die moderne Technologien nutzt und zukünftige Erweiterungen ermöglicht.

3. Ziele

Bereitstellung einer stabilen und skalierbaren Plattform.

Verbesserung der Benutzerfreundlichkeit und des Designs.

Integration moderner Sicherheitsstandards.

Optimierung der Performance und Ladezeiten.

Erweiterung der Funktionalitäten für Team- und Spielerverwaltung.

4. Stakeholder

Projektleitung: Masterpeace

Entwicklungsteam: Architektur, Backend-, Frontend-, DevOps-Entwickler, Security

Nutzer: Comunio-Spieler, Administratoren

Externe Partner: Datenanbieter für Fußballstatistiken

5. Funktionale Anforderungen

5.1 Benutzerverwaltung

Registrierung und Login

Rollen- und Rechteverwaltung



6. Nicht-funktionale Anforderungen

6.1 Performance

Ladezeiten unter 2 Sekunden

Skalierbarkeit für hohe Nutzerzahlen

6.2 Sicherheit

Verschlüsselung aller Datenübertragungen

Schutz vor gängigen Angriffen (OWASP Top 10)

6.3 Verfügbarkeit

99,9% Uptime

Monitoring und Alerting

6.4 Wartbarkeit

Saubere Code-Struktur

Dokumentation aller Module

Automatisierte Tests

7. Systemarchitektur

Microservices-Architektur

REST-API für Backend-Kommunikation

Moderne Frontend-Technologien (z. B. React)

Containerisierung mit Docker und Orchestrierung über Kubernetes

AWS für Datenbank und Backend-Hosting

Vercel für Frontend-Hosting und Deployment

Täglicher Datenabruf wird über einen orchestrierten Batch-Job realisiert, der automatisiert und zeitgesteuert (z. B. via AWS Lambda oder AWS Step Functions) ausgeführt wird.

Der Job nutzt Idempotenz-Prinzipien, um bei Wiederholungen keine Duplikate zu erzeugen, und beinhaltet Fehlerbehandlung mit automatischen Wiederholungen.

Für den Comunio-Datenabruf wird das Tool ComunioPy verwendet, das eine einfache und zuverlässige Schnittstelle zur Comunio-API bietet.

Monitoring und Alerts sind integriert, um Ausfälle oder Verzögerungen frühzeitig zu erkennen und zu beheben.

8. Datenmodell

siehe anhang

9. Integrationen - spätere Release

Externe Fußballstatistik-API

E-Mail-Provider für Benachrichtigungen

15. Ausbaustufen Plan - zwingend Beachten

Stufe

Ziel

Ergebnis

Manueller Abruf

Daten erstmal kontrolliert holen

Stabiler Test‑Abruf

Täglicher Abruf

Automatisierung

Tägliche Updates

Backend‑API

Zugriffsschicht

Saubere Endpoints

Minimal‑Frontend

Erste UI

Basis‑Dashboard

Frontend‑Ausbau

Komfort

Vollwertige App

Features

Mehrwert

Alerts, Prognosen

Skalierung

Stabilität

Hohe Performance

Security

Sicherheit

DSGVO‑ready

CI/CD

Automatisierung

Professioneller Workflow

10. Risiken

Verzögerungen bei der Datenintegration

Performance-Probleme bei hoher Last

Sicherheitsrisiken durch externe APIs

11. Zeitplan

Analysephase: 2 Wochen

Architekturdesign: 3 Wochen

Entwicklung: 12 Wochen

Testphase: 4 Wochen

Deployment: 1 Woche

12. Budget



Infrastrukturkosten - so niedrig wie möglich



13. Abnahmekriterien

Erfüllung aller funktionalen Anforderungen

Erfolgreiche Durchführung aller Tests

Dokumentation vollständig

System stabil und performant

14. Anhang

Attribut

Typ / Format

Quelle

Berechnung nötig?

Spielername

String

Comunio API / Website.

Nein

Spieler ID

Integer/String

Comunio API / DB.

Nein

Team (aktuelles Team)

String

Comunio API / Team‑Zuordnung.

Nein

Position

Enum (z. B. TW, ABW, MITT, ST)

Comunio API / Spielerprofil.

Nein

Aktueller Marktwert

Zahl (z. €)

Comunio Live‑Daten / API / HTML Scrape.

Nein

Erster verfügbarer Marktwert (in DB)

Zahl (z. €) + Timestamp

Eigene DB (historische Einträge) oder API‑Historie; evtl. nur aus eigener DB zuverlässig.

Nein (wenn vorhanden)

Marktwertveränderung

Zahl (Δ €) und %

Berechnet: aktueller − erster / erster.

Ja

Auf Transfermarkt (Flag)

Boolean

Comunio Transfermarkt‑Listing / API oder Scrape.

Nein

Verfügbar in Team (Flag)

Boolean

Eigene Team‑Daten / API.

Nein

Historische Marktwerte (Time Series)

Zeitreihen (Datum, Wert)

Eigene DB; API liefert ggf. nur aktuelle Werte.

Nein (wenn gespeichert)

Komplette Statistiken

Spiele, Tore, Assists, Punkte, Karten, Minuten

Comunio Spielerstatistiken / externe Stat APIs; teilweise in Comunio sichtbar.

Nein

Letzte Aktualisierung (Timestamp)

ISO Datetime

API / Scrape Metadaten.

Nein

Quelle / Herkunft

String (API, Scrape, DB)

Metadaten

Nein

Verfügbarkeitshistorie

Events (z. B. auf Markt, verkauft, Teamzuweisung)

Eigene DB (Event‑Log)

Ja (aus Logs ableiten)

Ranking / Sortier‑Score

Zahl (z. z. B. Wertsteigerung pro Tag)

Berechnet

Ja

Visualisierungsmetadaten

Farbe, Icon, Tooltip‑Text

Frontend

Nein (Design)

Glossar

API-Dokumentation

Datenflussdiagramme

Testfälle