# Vergleich: hochgeladener Wissensordner (Vektordatenbank) gegen MCP-Wissensdienst

Persistierte Testergebnisse zum Vergleich MCP-Wissensdienst gegen einen hochgeladenen
Wissensordner. Ziel: die Behauptung "strukturierte Suche schlägt reine Vektorsuche bei
Datierung, Vollständigkeit und Fachbereichs-Sicht" reproduzierbar belegen.

## Was verglichen wird

Ein hochgeladener Wissensordner (z. B. ein ChatGPT-Custom-GPT-Wissensordner) macht beim
Abruf im Kern dies: Dokumente in Abschnitte zerlegen, jeden Abschnitt einbetten, die
Frage einbetten, per Ähnlichkeit die nächsten Abschnitte zurückgeben. `vergleich_vektordb.py`
bildet genau das lokal ab (Embeddings via ollama `nomic-embed-text`, über alle 348
Dokumente des Bündels) und stellt es der heutigen MCP-Suche gegenüber (lexikalisch, aus
`mcp_server/bundle.py`, also exakt das, was die Tools `search`/`fetch` liefern).

Fairness: Für beide Seiten wird dieselbe natürlichsprachige Frage verwendet, ohne Filter
und ohne mehrstufige Recherche. Der MCP-Server kann in der Praxis mehr (Facetten-Filter
nach Gesetz/Thema/Jahr, Register, mehrstufige Navigation); das ist in
`verifikation_user_stories.md` dokumentiert und hier bewusst ausgeklammert, um das reine
Retrieval vergleichbar zu halten.

## Reproduktion

```sh
# Voraussetzung: ollama läuft lokal mit Embedding-Modell
ollama pull nomic-embed-text
python3 vergleich_vektordatenbank/vergleich_vektordb.py | tee vergleich_vektordatenbank/ergebnisse_roh.txt
```

Die vollständige Ausgabe des letzten Laufs liegt in `ergebnisse_roh.txt` (348 Dokumente,
4.830 Abschnitte, Embeddings in rund 130 Sekunden).

## Ergebnis je Anwendungsfall (Kurzfassung)

| Fall | MCP (lexikalisch) | Hochgeladener Wissensordner (Vektor) |
| --- | --- | --- |
| **U1** CSRD/ESRS | findet die CSRD/ESRS-Papiere; einschlägige neueste ESRS-Stellungnahme (2026-06-03) unter den Top-Treffern | findet die richtigen ESRS-Papiere, aber **ohne Datumslogik** (neuestes Papier 2026-06-03 nur auf Rang 3) und mit einem Fehltreffer (KI-Papier 2021) |
| **U2** digitaler Euro | findet die einschlägige Euro-Stellungnahme (2023) | findet die zwei Euro-Papiere (2021, 2023), aber verrauscht (KI-, Anwaltsrecht-Treffer) und **ohne Chronologie** |
| **U3** rote Linie/Statistik | Statistik-Papier (Unternehmensstatistikreformgesetz 2026-04-22) auf **Rang 1**, Gegenposition (Modernisierungsagenda) unter den Top-5 | dasselbe Statistik-Papier nur auf **Rang 4**, hinter weniger einschlägigen Bürokratie-Papieren; nicht priorisiert |
| **U4** KI fachbereichsübergreifend | KI-Papiere gemischt mit Fehltreffern; **keine** Fachbereichs-Sicht aus reiner Suche | KI-Papiere gut getroffen, aber mit Fehltreffern (Kfz, Fahrzeug-Zulassung) und **ohne** Fachbereichs-Sicht |
| **K** Solvency-II-Review | Top-5 durchweg Solvency-II-relevant | Top-5 durchweg Solvency-II-relevant (hier gleichwertig gut) |
| **S2-066** Schrems-II-Papier finden | **beide** Verbändepapiere auf Rang 1 und 2 (2020-09-22, 2021-05-06) | nur **eines** (2021) auf Rang 1, das zweite nicht in den Top-5; dazu Rauschen |
| **S2-058** FiDA | vollständiger FiDA-Strang (2023, 2024) unter den Top-Treffern | die drei Kern-FiDA-Papiere (2023, 2024) in den Top-3 (hier gleichwertig gut) |

## Auswertung (ehrlich)

- **Der semantische Vorteil des Vektoransatzes ist echt.** Bei gut abgedeckten Themen
  (K Solvency II, S2-058 FiDA) sind die Vektortreffer gleichwertig zur Stichwortsuche.
  Genau diesen Vorteil übernimmt der MCP-Weg über die geplante hybride Suche (SPEC.md).
- **Ohne Struktur bleibt die Vektorsuche schwächer, wo es auf Ordnung ankommt.** Sie kennt
  kein Datum (U1: neuestes Papier nicht zuerst), keinen Zeitverlauf (U2) und keine
  Fachbereichs-Sicht (U4). Bei U3 reiht sie das entscheidende Statistik-Papier weit hinten
  ein, während die Stichwortsuche es an die Spitze setzt. Bei S2-066 findet sie nur eines
  von zwei gesuchten Dokumenten.
- **Fehltreffer.** Die reine Ähnlichkeitssuche mischt themenfremde Papiere unter die
  Ergebnisse (KI-Papier bei U1, Anwaltsrecht bei U2, Kfz bei U4).

Der eigentliche Unterschied ist damit architektonisch: manueller Upload statt
automatischer Aktualisierung, keine Metadaten/Register,
keine Kuratierung, keine Belegstruktur (Dokumentkennung und Original-Link), und der Ordner
ist an ein Produkt gebunden statt eine Quelle für viele KI-Systeme zu sein.

## Hinweise zur Reproduzierbarkeit

- Absolute Ähnlichkeitswerte und Randplätze (etwa Rang 4 gegenüber Rang 6) können zwischen
  Läufen und Modellen leicht schwanken (Embedding-Varianz, Chunk-Zuschnitt). Die
  qualitativen Befunde oben sind stabil.
- Modell wechselbar über `EMBED_MODEL` (z. B. `bge-m3`). Der Vergleich ist absichtlich
  modellunabhängig gedacht; es geht nicht um den besten Embedding-Wert, sondern um den
  strukturellen Unterschied der Ansätze.

## Dateien

- `vergleich_vektordb.py` - das Vergleichsskript (Standardbibliothek plus ollama-HTTP).
- `ergebnisse_roh.txt` - vollständige Ausgabe des letzten Laufs (Top-5 je Fall, beide Ansätze).
