# Förderrecht Bund - Formularschrank und Nebenbestimmungen

Die Richtlinien, Allgemeinen Nebenbestimmungen, Merkblätter und Formularerläuterungen aus
dem [Formularschrank des Bundes](https://foerderportal.bund.de/easy/easy_index.php?auswahl=easy_formularschrank),
je Dokument eine Markdown-Datei mit Metadaten und eingebettetem Volltext. Maßgeblich bleibt
stets das Original-PDF, das in jeder Datei unter *Quelle* verlinkt ist.

Der Dienst beantwortet die Fragen, die im Förderalltag tatsächlich gestellt werden:
*Welche Nebenbestimmungen gelten für mein Vorhaben? Darf ich diese Ausgabe abrechnen?
Welche Fassung gilt für meinen Bescheid?* Hier starten: [Überblick](overview.md).

# Einstiege

- **Nach Antragsart:** [Antragsartenregister](register/nach-kategorie/index.md). AZA, AZK,
  AAA, AAK, AZV. Die Antragsart entscheidet, welches Regelwerk überhaupt gilt - der
  wichtigste erste Schnitt.
- **Nach Ressort:** [Ressortregister](register/nach-ministerium/index.md). BMWK, BMUV,
  BMEL, BMDV und andere geben eigene Fassungen heraus.
- **Nach Rechtsgrundlage:** [Gesetzesregister](register/nach-gesetz/index.md). Welche
  Dokumente sich auf BHO, VwVfG, AGVO, VOB oder UVgO stützen.
- **Nach Fassung:** [Versionsketten](register/versionsketten.md). Welche Fassung welche
  ablöst - entscheidend, weil für ein Vorhaben die im Bescheid genannte Fassung gilt,
  nicht die neueste.
- **Strukturell:** [Dokumentbaum](dokumente/index.md), `dokumente/<antragsart>/<titel>-<nr>.md`.

# Stand

131 Dokumente aus dem Formularschrank, 19 Rechtsgrundlagen als
Verweisseiten. Antragsarten: AAA (Aufträge Ausgaben) (5), AAK (Aufträge Kosten) (5), AZA (Ausgabenbasis) (55), AZK (Kostenbasis) (25), AZV (Zuweisungen/AZV) (2), Allgemein (32), Altvorhaben (7).
Ressorts: BAFA, BLE, BMBF, BMDV, BMEL, BMFSFJ, BMLEH, BMUKN, BMUV, BMWE, BMWK. Erzeugt am 2026-09-02 mit `scripts/build_bundle.py`.
Siehe [log.md](log.md).

# Was dieser Dienst nicht enthält

- **Keine Gesetzestexte.** Gesetze sind Verweisseiten unter `gesetze/` mit Link auf die
  amtliche Fassung bei gesetze-im-internet.de beziehungsweise EUR-Lex.
- **Keine Kontaktadressen.** In den Formularen abgedruckte E-Mail-Adressen sind ersetzt;
  aktuelle Ansprechpartner stehen im verlinkten Original-PDF.
- **Keine Rechtsberatung.** Der Dienst gibt amtliche Dokumente wieder, er legt sie nicht aus.
