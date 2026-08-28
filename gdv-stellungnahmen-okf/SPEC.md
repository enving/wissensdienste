# SPEC: Hybride semantische Suche (nächster Schritt)

Dies ist der vollständige Auftrag für den nächsten Ausbauschritt. Er ist eigenständig; du brauchst keinen weiteren Kontext.

## Repo-Orientierung (das Nötigste)

Dieses Repo macht einen Dokumentenbestand für KI-Assistenten abfragbar. Vier Stufen, alle unter `scripts/` (System-Python, keine Fremd-Deps, idempotent):

1. `scrape_gdv.py` holt den Katalog einer Quelle nach `GDV_Stellungnahmen/catalog.json`.
2. `convert_docling.py` lädt die PDFs und wandelt sie via lokalem docling-serve (`:5001`) in Markdown (`GDV_Stellungnahmen/md/`).
3. `build_bundle.py` baut daraus ein OKF-Bündel (`bundles/gdv-stellungnahmen/`): je Dokument ein Markdown-Konzept mit YAML-Frontmatter (`title, datum, themen, gesetzesbezug, fachbereiche_entwurf, sprache, resource, ...`) und eingebettetem Volltext, plus Register.
4. `mcp_server/server.py` (FastMCP, Streamable HTTP) stellt das Bündel als MCP-Server bereit. Tools: `search`, `fetch`, `get_overview`, `list_documents`, `get_register`.

Die Retrieval-Logik liegt allein in `mcp_server/bundle.py`, Methode `Bundle.search()` / `Bundle._score()`. Sie ist **heute lexikalisch** (Stichwort-/Feldsuche). Das ist der bewusst gesetzte Austauschpunkt ("der `search`-Seam").

Bestand: rund 348 Dokumente, überwiegend Deutsch (ca. 320), einige Englisch (ca. 26). Rein lokaler Betrieb.

## Ziel

Ersetze die lexikalische Suche durch **hybride Suche = BM25 (lexikalisch) + semantisch (Embeddings), fusioniert per Reciprocal Rank Fusion (RRF)**. Damit werden Paraphrasen gefunden, die die reine Stichwortsuche verfehlt (siehe `verifikation_user_stories.md`, U3: die Frage nach "unverzichtbaren" Statistiken traf nicht, weil die Textstelle "dürfen nicht zulasten ... gehen" lautet).

**Nur die Innenseite des Seams ändern.** Die MCP-Tool-Signaturen, das Frontmatter-Schema und die Clients bleiben unverändert.

## Leitprinzip: wiederverwendbare Pipeline, nicht Einzellösung

Wir bauen einen Piloten, aber die Grundlage muss wiederverwendbar bleiben. Halte dich daran:

- **Quell-agnostisch.** Alles außer `scrape_gdv.py` ist quellunabhängig und darf nichts GDV-Spezifisches hart kodieren. Eine neue Quelle bedeutet künftig: neuer Scraper + Konfiguration, Stufen 2 bis 4 unverändert. Wenn du Embeddings einbaust, baue sie so, dass sie über jedes OKF-Bündel laufen, nicht nur über dieses.
- **Microservice-Denke.** Das Embedding/Index-Modul ist eine abgegrenzte Einheit mit klarer Schnittstelle (`build_index(bundle) -> index`, `search(query, filters) -> [docs]`). Keine verstreute Logik.
- **Konfiguration statt Code.** Modellname, Index-Pfad, Chunk-Größe, Gewichte kommen aus Umgebungsvariablen/Defaults, nicht aus Code-Änderungen.
- **Doku sauber halten.** Aktualisiere `mcp_server/README.md` und `scripts/refresh.sh`, wenn sich Betrieb/Schritte ändern.

## Aufgabe (konkret)

1. **Indexaufbau (offline, im Build).** Neues Skript `scripts/build_embeddings.py`: liest das gebaute Bündel, zerlegt jedes Dokument in Abschnitte (Chunks auf Absatz-/Überschriftenebene, ca. 200 bis 400 Tokens, mit Dokument-id + Titel als Kontext), berechnet je Chunk einen Embedding-Vektor und schreibt einen Index (Vektoren + Chunk→Dokument-Zuordnung) nach `GDV_Stellungnahmen/embeddings/` (git-ignoriert, regenerierbar). Idempotent: nur neue/geänderte Chunks neu einbetten (Content-Hash).
2. **Abfrage.** Erweitere `mcp_server/bundle.py`: `Bundle.search()` wird hybrid. Lexikalischer Teil = die bestehende `_score`-Logik (bleibt als BM25-artige Komponente). Semantischer Teil = Query einbetten, Cosinus-Ähnlichkeit gegen den Index, auf Dokumentebene aggregieren. Beide Ranglisten per **RRF** fusionieren. Facetten-Filter (thema/gesetz/jahr/...) wie bisher vorher anwenden. Fällt der Index oder ollama aus, sauber auf rein lexikalisch zurückfallen (kein harter Fehler).
3. **Lokales Embedding-Modell über ollama** (`http://localhost:11434`). Keine externe API, kein Cloud-Dienst. Modellwahl siehe unten.
4. **Integration.** `scripts/refresh.sh` um den Embedding-Schritt nach `build_bundle.py` ergänzen. `mcp_server/requirements.txt` um `numpy` (und, falls genutzt, einen ollama-HTTP-Aufruf per stdlib) ergänzen. Index-Verzeichnis in `.gitignore`.

## Embedding-Modell: Wahl (empirisch entscheiden, nicht nach Leaderboard-Rang)

Der Bestand ist deutsch-dominiert mit englischem Anteil, also **mehrsprachiges** Modell, lokal, 32 GB VRAM verfügbar.

Zwei Vorbemerkungen, die die Wahl bestimmen:
- Das **deutsche** MTEB-Board wird von `codefuse-ai/F2LLM-v2` angeführt (nicht auf ollama); Qwen3-Embedding steht dort nicht oben. Keine Wette auf einen einzelnen Rang.
- Die Leaderboard-Spalte "Mean" mischt Classification/Clustering/PairClass. Für uns zählt allein **Retrieval**. Deshalb: an den echten U1-U4-Fragen testen, nicht am Mean.

Sortiert man das deutsche MTEB-Board nach der **Retrieval**-Spalte (das ist unsere Aufgabe), führt `codefuse-ai/F2LLM-v2` (Retr ~59, nicht auf ollama); direkt dahinter liegen retrieval-gebaute, kommerziell nutzbare Modelle wie Snowflake arctic-embed v2.0. `bge-m3` steht in der deutschen Retrieval-Spitze nicht oben. Qwen3-Embedding ist auf Englisch stark, auf Deutsch nicht führend.

Vorgehen:
- **Default (ollama, retrieval-gebaut, mehrsprachig, Apache-2.0): `snowflake-arctic-embed-l-v2.0`** (auf ollama als `snowflake-arctic-embed2`). Steht in der deutschen Retrieval-Spitze (Retr ~57), ist explizit ein Retrieval-Modell, klein, kommerziell nutzbar. Damit den Index bauen.
- **A/B-Kandidat für maximale Deutsch-Qualität: `codefuse-ai/F2LLM-v2-8B`** (deutsches Retrieval-Board Platz 2, Retr ~59, 7.6B, passt in 32 GB). Nicht auf ollama -> lokal via HF `sentence-transformers`/`transformers`. Lizenz vor Einsatz prüfen.
- **Garantierter ollama-Fallback: `bge-m3`** (rund 568M, MIT, `ollama pull bge-m3`). Nicht Retrieval-Spitze für Deutsch, aber nativ hybrid (dense + sparse) und immer verfügbar; als sicheres Rückfallmodell und Baseline nützlich. Alternativ `intfloat/multilingual-e5-large-instruct` (MIT, ollama).
- **Meiden:** `jina-embeddings-v3` (nicht-kommerzielle Lizenz, für GDV heikel).

Entscheide **empirisch**: Der Korpus ist klein und der Seam ist tauschbar; die 2 bis 4 Punkte Unterschied auf MTEB sind marginal und übertragen sich nicht zwingend auf unsere Fragen. Baue den Index mit dem Default, vergleiche gegen `F2LLM-v2-8B` an den realen U1-U4-Fragen (besonders der U3-Paraphrasenfrage) und nimm den, der real am besten trifft, nicht den höchsten Leaderboard-Wert. Das Modell ist Konfiguration (`EMBED_MODEL`). Zu Beginn per `ollama list` prüfen bzw. `ollama pull`; ist das Default-Modell nicht ziehbar, auf `bge-m3` ausweichen und im Log vermerken.

## Nicht-Ziele

- Kein Azure, kein Cloud-Deploy, keine externe Embedding-API. Nur lokal.
- MCP-Tool-Signaturen, Frontmatter-Schema, Client-Anbindung nicht verändern.
- Keine großen Frameworks (kein LangChain o. ä.); numpy + ollama-HTTP genügen bei dieser Größe.

## Deliverables

- `scripts/build_embeddings.py` (offline-Indexer, quell-agnostisch über ein OKF-Bündel).
- Angepasstes `mcp_server/bundle.py` (hybride `search`, mit Fallback).
- Aktualisierte `scripts/refresh.sh`, `mcp_server/requirements.txt`, `.gitignore`.
- Kurzer Abschnitt in `mcp_server/README.md`: wie der Index gebaut/aktualisiert wird, welches Modell, wie man auf lexikalisch-only zurückfällt.

## Akzeptanzkriterien

1. Rein lokal lauffähig (ollama + Python), keine Netz-/Cloud-Abhängigkeit zur Laufzeit.
2. Die U3-Paraphrasenfrage findet die Statistik-Stellungnahme, ohne dass das Stichwort "unverzichtbar" vorkommt (semantischer Treffer). Belege mit einem Vorher/Nachher-Beispiel.
3. Exakte Fachbegriffe (z. B. "Solvency II", "Art. 9") bleiben durch den lexikalischen Anteil zuverlässig auffindbar (hybrid, nicht nur semantisch).
4. `okf_validate.py` bleibt fehlerfrei; MCP-Tools verhalten sich unverändert (gleiche Signaturen/Rückgaben).
5. Index ist reproduzierbar aus dem Bündel und git-ignoriert; `refresh.sh` baut ihn mit.
6. Fällt ollama/der Index aus, antwortet `search` weiterhin (lexikalisch), ohne Absturz.

## Verifikation

Wiederhole die Methodik aus `verifikation_user_stories.md`: kontextfreie Agenten, Zugriff nur über den MCP-Server, insbesondere die U3-Frage (rote Linien) und die U1/U4-Fragen. Dokumentiere Vorher/Nachher der Trefferqualität.
