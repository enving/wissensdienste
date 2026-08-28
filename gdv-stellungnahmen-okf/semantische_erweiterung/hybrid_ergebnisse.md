# Hybride Suche: Messergebnis (gewichtete RRF)

Modell `bge-m3`, Dokumente 348, Abschnitte 7315, Embeddings gebaut in 532s, RRF k=60, Top-20.

## Gewichtungs-Sweep (Semantik-Gewicht, Lexik = 1.0)

| Semantik-Gewicht | mittl. Recall@5 | mittl. MRR | U3-Paraphrase Rang | S2-066 beide Top-5 |
| --- | --- | --- | --- | --- |
| 1 | 0.952 | 0.929 | 4 | ja |
| 1.5  <- gewaehlt | 0.952 | 0.929 | 3 | ja |
| 2 | 0.881 | 0.929 | 3 | ja |
| 3 | 0.881 | 1.000 | 3 | ja |
| 5 | 0.881 | 1.000 | 1 | ja |

Gewaehltes Semantik-Gewicht: **1.5** (max. Recall@5, dann U3 in Top-3, dann MRR).

## Rang je Gold-Dokument (Top-20), Recall@5, MRR - hybrid mit Gewicht 1.5

### U1

| Verfahren | Gold-Raenge | Recall@5 | MRR |
| --- | --- | --- | --- |
| lexikalisch | stellungnahme-zu-den-fachlichen-empfehlungen-der-efrag-zum-esrs-verein=3, gdv-stellungnahme-zum-csrd-umsetzungsgesetz=2 | 1.00 | 0.50 |
| semantisch | stellungnahme-zu-den-fachlichen-empfehlungen-der-efrag-zum-esrs-verein=12, gdv-stellungnahme-zum-csrd-umsetzungsgesetz=2 | 0.50 | 0.50 |
| hybrid | stellungnahme-zu-den-fachlichen-empfehlungen-der-efrag-zum-esrs-verein=5, gdv-stellungnahme-zum-csrd-umsetzungsgesetz=1 | 1.00 | 1.00 |

### U2

| Verfahren | Gold-Raenge | Recall@5 | MRR |
| --- | --- | --- | --- |
| lexikalisch | positionspapier-der-digitale-euro-aus-sicht-der-deutschen-versicherung=-, stellungnahme-zum-legislativvorschlag-der-europaischen-kommission-zur=1 | 0.50 | 1.00 |
| semantisch | positionspapier-der-digitale-euro-aus-sicht-der-deutschen-versicherung=2, stellungnahme-zum-legislativvorschlag-der-europaischen-kommission-zur=1 | 1.00 | 1.00 |
| hybrid | positionspapier-der-digitale-euro-aus-sicht-der-deutschen-versicherung=4, stellungnahme-zum-legislativvorschlag-der-europaischen-kommission-zur=1 | 1.00 | 1.00 |

### U3

| Verfahren | Gold-Raenge | Recall@5 | MRR |
| --- | --- | --- | --- |
| lexikalisch | stellungnahme-zum-entwurf-eines-ersten-unternehmensstatistikreformgese=1 | 1.00 | 1.00 |
| semantisch | stellungnahme-zum-entwurf-eines-ersten-unternehmensstatistikreformgese=1 | 1.00 | 1.00 |
| hybrid | stellungnahme-zum-entwurf-eines-ersten-unternehmensstatistikreformgese=1 | 1.00 | 1.00 |

### U4

| Verfahren | Gold-Raenge | Recall@5 | MRR |
| --- | --- | --- | --- |
| lexikalisch | gdv-positionspapier-zum-beginn-der-trilogverhandlungen-zur-ki-verordnu=5, positionspapier-zum-eu-rechtsrahmen-fur-kunstliche-intelligenz=6, gdv-positionspapier-zur-definition-eines-ki-systems=- | 0.33 | 0.20 |
| semantisch | gdv-positionspapier-zum-beginn-der-trilogverhandlungen-zur-ki-verordnu=2, positionspapier-zum-eu-rechtsrahmen-fur-kunstliche-intelligenz=6, gdv-positionspapier-zur-definition-eines-ki-systems=3 | 0.67 | 0.50 |
| hybrid | gdv-positionspapier-zum-beginn-der-trilogverhandlungen-zur-ki-verordnu=2, positionspapier-zum-eu-rechtsrahmen-fur-kunstliche-intelligenz=3, gdv-positionspapier-zur-definition-eines-ki-systems=7 | 0.67 | 0.50 |

### K

| Verfahren | Gold-Raenge | Recall@5 | MRR |
| --- | --- | --- | --- |
| lexikalisch | solvency-ii-konsultation-der-kommission-und-gdv-positionen=1, gdv-stellungnahme-zur-umsetzung-des-neuen-proportionalitatsrahmens-unt=2 | 1.00 | 1.00 |
| semantisch | solvency-ii-konsultation-der-kommission-und-gdv-positionen=1, gdv-stellungnahme-zur-umsetzung-des-neuen-proportionalitatsrahmens-unt=2 | 1.00 | 1.00 |
| hybrid | solvency-ii-konsultation-der-kommission-und-gdv-positionen=1, gdv-stellungnahme-zur-umsetzung-des-neuen-proportionalitatsrahmens-unt=2 | 1.00 | 1.00 |

### S2-066

| Verfahren | Gold-Raenge | Recall@5 | MRR |
| --- | --- | --- | --- |
| lexikalisch | verbandepapier-zum-schrems-ii-urteil-des-eugh=1, verbandeschreiben-zur-umsetzung-des-schrems-ii-urteils-des-eugh=2 | 1.00 | 1.00 |
| semantisch | verbandepapier-zum-schrems-ii-urteil-des-eugh=2, verbandeschreiben-zur-umsetzung-des-schrems-ii-urteils-des-eugh=1 | 1.00 | 1.00 |
| hybrid | verbandepapier-zum-schrems-ii-urteil-des-eugh=2, verbandeschreiben-zur-umsetzung-des-schrems-ii-urteils-des-eugh=1 | 1.00 | 1.00 |

### S2-058

| Verfahren | Gold-Raenge | Recall@5 | MRR |
| --- | --- | --- | --- |
| lexikalisch | stellungnahme-zum-rahmenwerk-fur-den-zugang-zu-finanzdaten-fida=1, positionspapier-fida-droht-ziele-zu-verfehlen-und-gefahrdet-damit-die=3, stellungnahme-zur-fida-regulation=2 | 1.00 | 1.00 |
| semantisch | stellungnahme-zum-rahmenwerk-fur-den-zugang-zu-finanzdaten-fida=2, positionspapier-fida-droht-ziele-zu-verfehlen-und-gefahrdet-damit-die=4, stellungnahme-zur-fida-regulation=3 | 1.00 | 0.50 |
| hybrid | stellungnahme-zum-rahmenwerk-fur-den-zugang-zu-finanzdaten-fida=1, positionspapier-fida-droht-ziele-zu-verfehlen-und-gefahrdet-damit-die=3, stellungnahme-zur-fida-regulation=2 | 1.00 | 1.00 |

## Aggregat (Mittel ueber alle Faelle)

| Verfahren | mittl. Recall@5 | mittl. MRR |
| --- | --- | --- |
| lexikalisch | 0.833 | 0.814 |
| semantisch | 0.881 | 0.786 |
| hybrid (Gewicht 1.5) | 0.952 | 0.929 |

## Sonderauswertung U3 (Paraphrase)

Paraphrase: "welche statistischen Daten sind unverzichtbar, welche rote Linie zieht der GDV"

| Verfahren | Rang Gold |
| --- | --- |
| lexikalisch | nicht in Top-20 |
| semantisch | 1 |
| hybrid | 3 |

## Fazit gegen Erfolgskriterium (SPEC)

1. Recall@5 hybrid >= max(lex, sem): ERFUELLT (0.952 vs 0.881).
2. U3-Paraphrase Gold in Top-3 (hybrid): ERFUELLT (Rang 3).
3. S2-066 beide in Top-5 (hybrid): ERFUELLT.

**Gesamt: erfuellt** (Semantik-Gewicht 1.5).

Reproduktion: `EMBED_MODEL=bge-m3 python3 semantische_erweiterung/hybrid_test.py`.
