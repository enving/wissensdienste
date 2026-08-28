---
type: Überblick
title: "Überblick: GDV-Stellungnahmen"
description: "Was das Bündel enthält, wie es aufgebaut ist und wie ein Agent die Nutzerfragen U1 bis U4 damit beantwortet."
tags: ["gdv", "overview"]
timestamp: 2026-08-17T07:10:58Z
---

# Überblick

Dieses Bündel bündelt die öffentlichen **Positionspapiere und Stellungnahmen des GDV** so, dass ein KI-Agent sie direkt lesen kann. Jedes Dokument ist ein Konzept unter `stellungnahmen/<jahr>/<slug>.md` mit strukturierten Metadaten (Datum, Dokumenttyp, Themen, Fachbereich-Entwurf, Gesetzesbezug, Sprache) und dem **vollständigen Text** aus dem Original-PDF.

Der Bestand (353 Dokumente, 2017-05-01 bis 2026-08-05) ist über vier Register erschlossen, die auf die Nutzerfragen zugeschnitten sind.

# Aufbau

- `stellungnahmen/<jahr>/<slug>.md` — die Dokumente selbst, gruppiert nach Jahr, Volltext eingebettet.
- `register/nach-thema/` — je Thema ein Register, das alle Dokumente dazu chronologisch listet.
- `register/nach-gesetz/` — je erkanntem Gesetz/EU-Vorhaben ein Register.
- `register/nach-fachbereich/` — Entwurf einer Fachbereichs-Zuordnung (von den Fachbereichen zu bestätigen).
- `register/rote-linien.md` — kuratierte rote Linien (Ausbaustufe).

Jedes Dokument verweist im Abschnitt *Einordnung* auf seine Themen-, Fachbereichs- und Gesetzes-Register; die Register verweisen zurück. So ist der Bestand als Graph navigierbar, nicht nur als Liste.

Häufige Themen: Regulierung, Politik, Schaden & Unfall, Digitalisierung, Rente & Vorsorge, Nachhaltigkeit.

# So werden die Nutzerfragen beantwortet

- **U1 (aktuelle Position zu Thema X):** Über das [Themenregister](/register/nach-thema/index.md) das Thema wählen; das oberste (neueste) Dokument gibt den aktuellen Stand, der eingebettete Volltext die Begründung.
- **U2 (frühere Positionen zu einem geplanten Gesetz, Entwicklung über die Zeit):** Über das [Gesetzesregister](/register/nach-gesetz/index.md) das Vorhaben wählen; die chronologische Liste je Thema/Gesetz zeigt, ob und wie sich die Position verändert hat.
- **U3 (rote Linien, z. B. unverzichtbare Statistiken):** Über [Rote Linien](/register/rote-linien.md) und Volltextsuche über alle Dokumente nach Formulierungen wie *unverzichtbar*, *zwingend erforderlich*, *lehnt ab*, *Statistik*.
- **U4 (fachbereichsübergreifende Themen):** Über das [Themenregister](/register/nach-thema/index.md) und das [Fachbereichsregister](/register/nach-fachbereich/index.md) sehen, welche Fachbereiche zu einem Thema Position bezogen haben.
