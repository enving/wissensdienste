---
art: "Überblick"
titel: "Überblick: Förderrecht Bund"
kurzbeschreibung: "Was der Dienst enthält, wie er aufgebaut ist und wie ein Agent damit die typischen Förderfragen beantwortet."
schlagworte: ["foerderrecht", "overview"]
stand_bundle: 2026-09-02T10:18:51Z
---

# Überblick

Dieser Dienst macht das **Zuwendungsrecht des Bundes** für einen KI-Agenten direkt lesbar.
Grundlage ist der Formularschrank des Bundes: 131 Dokumente - Richtlinien für
Zuwendungsanträge, Allgemeine Nebenbestimmungen, Merkblätter, Kalkulationshilfen und
Formularerläuterungen. Jedes Dokument liegt unter `dokumente/<antragsart>/<titel>-<nr>.md`
mit strukturierten Metadaten (Antragsart, Kürzel, Ressort, Stand, Gesetzesbezug) und dem
**vollständigen Text** aus dem Original-PDF.

Dokumentarten im Bestand: Nebenbestimmung (44), Zuwendungsdokument (38), Merkblatt (24), Anlage (7), Formular (7), Richtlinie (5), Rechtsgrundlage (4), Bekanntmachung (1), Kalkulationshilfe (1).

# Aufbau

- `dokumente/<antragsart>/` - die Dokumente selbst, gruppiert nach Antragsart, Volltext eingebettet.
- `gesetze/` - Rechtsgrundlagen als Verweisseiten mit Link auf die amtliche Fassung. Der
  Dienst dupliziert keine Gesetzestexte.
- `register/nach-kategorie/` - je Antragsart ein Register.
- `register/nach-ministerium/` - je Ressort ein Register.
- `register/nach-gesetz/` - welche Dokumente sich auf welche Rechtsgrundlage stützen.
- `register/versionsketten.md` - die Ablösefolge der Fassungen.

Jedes Dokument verweist im Abschnitt *Einordnung* auf seine Register; die Register verweisen
zurück. Der Bestand ist damit als Graph navigierbar, nicht nur als Liste.

# Die Antragsart ist der erste Schnitt

Ob eine Ausgabe förderfähig ist, hängt zuerst daran, auf welcher Basis gefördert wird.
Dieselbe Frage hat auf Ausgabenbasis und auf Kostenbasis unterschiedliche Antworten.

- **AZA (Ausgabenbasis)** (55 Dokumente). Zuwendungen auf Ausgabenbasis - der Regelfall für Hochschulen, Forschungseinrichtungen und andere nicht gewerbliche Zuwendungsempfänger.
- **Allgemein** (32 Dokumente). Übergreifende Regelwerke, Merkblätter und Rechtsgrundlagen ohne Bindung an eine Antragsart.
- **AZK (Kostenbasis)** (25 Dokumente). Zuwendungen auf Kostenbasis - für Unternehmen der gewerblichen Wirtschaft, die auf Basis von Selbstkosten abrechnen.
- **Altvorhaben** (7 Dokumente). Ältere Fassungen für laufende Vorhaben - maßgeblich ist die im Bescheid genannte Fassung.
- **AAA (Aufträge Ausgaben)** (5 Dokumente). Aufträge auf Ausgabenbasis - Beschaffung statt Zuwendung.
- **AAK (Aufträge Kosten)** (5 Dokumente). Aufträge auf Kostenbasis - Beschaffung nach Selbstkostenpreisen.
- **AZV (Zuweisungen/AZV)** (2 Dokumente). Zuweisungen an Gebietskörperschaften und Verwaltungsvereinbarungen nach § 61 BHO.

# Fassungen sind nicht austauschbar

Für ein laufendes Vorhaben gilt die Fassung, die im **Zuwendungsbescheid** genannt ist -
nicht automatisch die neueste. Die ANBest-P etwa liegt in mehreren Fassungen vor, die
einander ablösen. Vor jeder Aussage zu einer konkreten Bewilligung deshalb die
[Versionsketten](register/versionsketten.md) prüfen und die Fassung benennen, auf die sich
die Antwort stützt.

# Häufig herangezogene Rechtsgrundlagen

- [VwVfG](gesetze/vwvfg.md) - Verwaltungsverfahrensgesetz, 17 Dokument(e)
- [BGB](gesetze/bgb.md) - Bürgerliches Gesetzbuch, 14 Dokument(e)
- [BHO](gesetze/bho.md) - Bundeshaushaltsordnung, 13 Dokument(e)
- [GWB](gesetze/gwb.md) - Gesetz gegen Wettbewerbsbeschränkungen, 5 Dokument(e)
- [UStG](gesetze/ustg.md) - Umsatzsteuergesetz, 4 Dokument(e)
- [InsO](gesetze/inso.md), 1 Dokument(e)
- [AEUV](gesetze/aeuv.md) - Vertrag über die Arbeitsweise der Europäischen Union, 0 Dokument(e)
- [AGVO](gesetze/agvo.md) - Allgemeine Gruppenfreistellungsverordnung (EU) Nr. 651/2014, 0 Dokument(e)

# So beantwortest du typische Fragen

- **"Welche Nebenbestimmungen gelten für mein Vorhaben?"** Erst die Antragsart klären
  (Ausgaben- oder Kostenbasis, Zuwendung oder Auftrag), dann über das
  [Antragsartenregister](register/nach-kategorie/index.md) die ANBest der passenden Art.
- **"Darf ich diese Ausgabe abrechnen?"** Volltextsuche in der einschlägigen ANBest und den
  Richtlinien der Antragsart. Die Antwort mit der Nummer der Nebenbestimmung belegen.
- **"Welche Fassung gilt?"** Über die [Versionsketten](register/versionsketten.md); die
  Fassung im Bescheid schlägt die neueste.
- **"Worauf stützt sich diese Regel?"** Über das
  [Gesetzesregister](register/nach-gesetz/index.md) zur Rechtsgrundlage, dann zur amtlichen
  Fassung bei gesetze-im-internet.de.

# Belegen

Antworten immer mit dem Dokumenttitel und der Original-PDF-URL aus dem Feld `quelle` belegen.
Der eingebettete Text ist eine maschinelle Umsetzung: Tabellen und Formularfelder können
verkürzt sein. Bei Zweifeln auf das Original-PDF verweisen statt den Text zu paraphrasieren.
