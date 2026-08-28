# SPEC: Lokaler Test der semantischen Ergänzung (hybride Suche)

**Zweck.** Empirisch und ehrlich messen, ob eine **hybride Suche** (Stichwortsuche + semantische Suche, per RRF fusioniert) die Retrieval-Qualität des MCP-Wissensdienstes gegenüber der heutigen, rein lexikalischen Suche messbar verbessert. Das Ergebnis untermauert (oder widerlegt) das Versprechen "die Qualität wird besser". Der Test muss auch ein Negativergebnis sauber ausweisen; er ist eine Messung, kein Beweisauftrag.

**Kontext.** Kommerzielle RAG-Wissensordner (z. B. hochladbare Wissensordner in ChatGPT-artigen Tools, agentisches RAG mit Reasoning-Modell) sind bei reiner Frage-Antwort auf gut abgedeckten Themen bereits stark. Der Burggraben des MCP-Ansatzes liegt in Datierung, garantiertem Beleg, Aktualität und Systemunabhängigkeit (nicht im Test-Umfang hier, siehe `vergleich_vektordatenbank/`). Diese SPEC prüft die eine offene Achse: **holt semantische/hybride Suche das Retrieval auf ein vergleichbares Niveau, besonders bei Umschreibungen (Paraphrasen)?**

## Was gebaut wird

Ein einzelnes, idempotentes Skript, das für einen festen Fragenkatalog drei Retrieval-Verfahren über **denselben** OKF-Bestand vergleicht:

1. **Lexikalisch (Ist-Zustand):** `Bundle.search` aus `mcp_server/bundle.py` (exakt das, was `search`/`fetch` heute liefern).
2. **Rein semantisch (Baseline):** Embeddings via ollama, Kosinus-Ähnlichkeit. Chunking- und Embedding-Code aus `vergleich_vektordatenbank/vergleich_vektordb.py` wiederverwenden (nicht neu erfinden).
3. **Hybrid (neu):** Reciprocal Rank Fusion (RRF) der Ränge aus (1) und (2). `score(doc) = Σ 1/(k + rang_verfahren(doc))`, `k = 60`. Rang pro Verfahren aus der jeweiligen Top-Liste; nicht gerankte Dokumente tragen 0 bei.

Kein Framework, keine neue Abhängigkeit. Python 3.9, nur Standardbibliothek + ollama-HTTP. Ablage: eigener Ordner `semantische_erweiterung/hybrid_test.py` plus Ergebnisdatei `semantische_erweiterung/hybrid_ergebnisse.md`.

## Fragenkatalog und Goldstandard

Je Fall eine natürlichsprachige Frage. Wo Paraphrasen die lexikalische Schwäche treffen, zusätzlich eine **Paraphrasen-Variante** (das ist der Kern des Tests). Goldstandard = die bekannten einschlägigen Dokumente (Pfadstamm unter `bundles/gdv-stellungnahmen/stellungnahmen/`), abgeleitet aus `vergleich_vektordatenbank/ergebnisse_roh.txt` und `verifikation_user_stories.md`:

| Fall | Frage (natürlich) | Paraphrasen-Variante (falls relevant) | Gold-Dokumente (Pfadstamm) |
| --- | --- | --- | --- |
| U1 | Aktuelle Position zur Nachhaltigkeitsberichterstattung CSRD/ESRS | – | `2026/stellungnahme-zu-den-fachlichen-empfehlungen-der-efrag-zum-esrs-verein`, `2025/gdv-stellungnahme-zum-csrd-umsetzungsgesetz` |
| U2 | Frühere GDV-Positionen zum digitalen Euro und Veränderung über die Zeit | – | `2021/positionspapier-der-digitale-euro-aus-sicht-der-deutschen-versicherung`, `2023/stellungnahme-zum-legislativvorschlag-der-europaischen-kommission-zur` |
| U3 | Bürokratieabbau und unverzichtbare Statistik als rote Linie | **"welche Statistiken sind unverzichtbar / rote Linie"** (ohne die Textphrase "dürfen nicht zulasten … gehen") | `2026/stellungnahme-zum-entwurf-eines-ersten-unternehmensstatistikreformgese` |
| U4 | Welche Fachbereiche haben zu künstlicher Intelligenz Position bezogen | – | `2023/gdv-positionspapier-zum-beginn-der-trilogverhandlungen-zur-ki-verordnu`, `2022/positionspapier-zum-eu-rechtsrahmen-fur-kunstliche-intelligenz`, `2025/gdv-positionspapier-zur-definition-eines-ki-systems` |
| K | Zentrale Forderungen zum Solvency II Review (Extrapolation, Proportionalität, Berichtspflichten) | – | `2020/solvency-ii-konsultation-der-kommission-und-gdv-positionen`, `2024/gdv-stellungnahme-zur-umsetzung-des-neuen-proportionalitatsrahmens-unt` |
| S2-066 | Gemeinsames Verbändeschreiben zum Schrems-II-Urteil des EuGH finden | – | `2020/verbandepapier-zum-schrems-ii-urteil-des-eugh`, `2021/verbandeschreiben-zur-umsetzung-des-schrems-ii-urteils-des-eugh` (**beide** gesucht) |
| S2-058 | Zentrale GDV-Positionen und Forderungen zur FiDA-Verordnung | – | `2023/stellungnahme-zum-rahmenwerk-fur-den-zugang-zu-finanzdaten-fida`, `2024/positionspapier-fida-droht-ziele-zu-verfehlen-und-gefahrdet-damit-die`, `2024/stellungnahme-zur-fida-regulation` |

Prüfe die Pfadstämme beim Bauen gegen das tatsächliche Bündel; korrigiere sie, falls sich Dateinamen unterscheiden, und protokolliere jede Korrektur.

## Metriken

Pro Fall und Verfahren, Top-10 betrachtet:
- **Rang jedes Gold-Dokuments** (oder "nicht in Top-10").
- **Recall@5** (Anteil der Gold-Dokumente in den Top-5).
- **MRR** (Reciprocal Rank des ersten Gold-Treffers).

Aggregiert über alle Fälle: mittlerer Recall@5 und mittlerer MRR je Verfahren.

Zwei Sonderauswertungen, die das eigentliche Versprechen betreffen:
- **Paraphrasen-Fall U3:** Rang des Gold-Dokuments bei der Paraphrasen-Variante, lexikalisch vs. semantisch vs. hybrid. Dies ist der Kern-Nachweis ("schließt die Umschreibungs-Lücke").
- **Mehrfachtreffer S2-066:** Kommen **beide** Schrems-Papiere in die Top-5? (Reine Vektorsuche schaffte nur eines.)

## Erfolgskriterium (vorab festgelegt, damit das Ergebnis ehrlich bleibt)

Die hybride Suche gilt als bestätigt, wenn **alle** zutreffen:
1. Mittlerer Recall@5 (hybrid) ≥ Maximum aus lexikalisch und rein semantisch.
2. Paraphrasen-U3: Gold-Dokument hybrid in Top-3 (lexikalisch verfehlt es bei der Paraphrase).
3. S2-066: beide Gold-Papiere hybrid in Top-5.

Werden Kriterien verfehlt, ist das **so zu berichten** (kein Schönrechnen). Ein Teil- oder Negativergebnis ist ein wertvolles Resultat vor dem Antrag.

## Modelle

- Primär `nomic-embed-text` (identisch zur bestehenden Baseline in `ergebnisse_roh.txt`, macht die Zahlen vergleichbar).
- Zusätzlich, falls verfügbar, ein retrieval-gebautes Modell als realistische Produkt-Obergrenze: `snowflake-arctic-embed2` (siehe `CLAUDE.md`/`SPEC.md`). Über Umgebungsvariable `EMBED_MODEL` umschaltbar. Wenn nicht gepullt, überspringen und vermerken.

## Randbedingungen

- Python 3.9, nur Standardbibliothek + ollama-HTTP (`http://localhost:11434`). Keine neue Abhängigkeit, kein pandas/numpy.
- Voraussetzung Lauf: ollama läuft und Modell ist gepullt. Prüfen; wenn nicht erreichbar, klar melden und die genaue Startanweisung ausgeben (`ollama serve`, `ollama pull nomic-embed-text`), statt zu raten.
- Idempotent, kein Schreiben außerhalb `semantische_erweiterung/`.
- **Selbstprüfung (Pflicht):** Die RRF-Fusion mit einem `assert`-basierten `__main__`-Selbsttest auf einem winzigen synthetischen Beispiel absichern (bekannte Ränge → erwartete Fusionsreihenfolge). Läuft ohne ollama.

## Ergebnis (Deliverable)

`semantische_erweiterung/hybrid_ergebnisse.md` mit:
1. Tabelle Rang je Gold-Dokument je Verfahren, je Fall.
2. Aggregat (mittlerer Recall@5, MRR) je Verfahren.
3. Die zwei Sonderauswertungen (U3-Paraphrase, S2-066-Mehrfachtreffer).
4. Klares Fazit: Erfolgskriterium erfüllt / teilweise / nicht, mit einem Satz je Kriterium.
5. Reproduktionsbefehl.

Kurzfazit zusätzlich als Rückgabe an den Auftraggeber (3 bis 5 Sätze): Verbessert hybride Suche das Retrieval gegenüber dem lexikalischen Ist-Zustand, und reicht das, um im Antrag "die Qualität wird besser" zu belegen?
