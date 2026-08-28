# CLAUDE.md - Betriebs- und Kontextleitfaden für Claude

Dies ist der Arbeitskontext für Claude in diesem Repo (nicht fürs README). Wer die nächste Ausbaustufe umsetzt, bekommt `SPEC.md`; dieses Dokument ist der Hintergrund, den du kennen solltest.

## Was das hier ist und wohin es geht

Ziel: Fachdokumente (Piloten: die öffentlichen GDV-Positionspapiere/Stellungnahmen von gdv.de/gdv/positionen) so aufbereiten, dass ein KI-Assistent sie beantworten kann. Umgesetzt als OKF-Bündel (Markdown + YAML-Frontmatter) plus MCP-Server.

**Es ist ein Pilot, aber die eigentliche Leistung ist eine wiederverwendbare Pipeline.** Ziel ist, dass künftig gilt: "Hier sind Quellen/Unterlagen" -> Claude weiß, es sind die Stufen 1-2-3-4, füllt sie, und liefert am Ende ein Docker-Image, das sich deployen lässt. Deshalb: quell-agnostisch bauen, Microservice-Denke, Konfiguration statt Code, Doku und Repo-Struktur sauber halten. Nichts GDV-Spezifisches außerhalb des Scrapers hart kodieren.

**Arbeitsmodus: rein lokal.** Derzeit wird nur lokal entwickelt und optimiert (schneller, keine Cloud-Reibung). Azure/ChatGPT werden NICHT jetzt ausprobiert. Das finale Produkt wird gekapselt (Docker + MCP-Server) und lässt sich so an jede Deploy-Umgebung übergeben. Der Rechner ist stark (u.a. 32 GB VRAM), lokale Modelle (ollama) sind erwünscht.

## Die Pipeline (Stufen 1-2-3-4)

Alle Skripte unter `scripts/`, System-Python, keine Fremd-Deps, idempotent:

1. `scrape_gdv.py` -> `GDV_Stellungnahmen/catalog.json` (Metadaten). Quell-spezifisch; pro neuer Quelle neu.
2. `convert_docling.py` -> lädt PDFs (Host) und konvertiert via docling-serve (`:5001`) zu Markdown (`GDV_Stellungnahmen/md/`). Quell-agnostisch.
3. `build_bundle.py` -> baut `bundles/gdv-stellungnahmen/` (je Dokument ein Konzept mit Volltext + Frontmatter, plus Register nach Thema/Gesetz/Fachbereich + Jahresbaum). Quell-agnostisch bis auf das Fachbereichs-/Gesetzes-Mapping (Konstanten oben im Skript).
4. `mcp_server/server.py` (FastMCP, Streamable HTTP) -> stellt das Bündel bereit. Tools: `search`, `fetch`, `get_overview`, `list_documents`, `get_register`. Retrieval-Logik allein in `mcp_server/bundle.py` (`Bundle.search`), bewusst als Austauschpunkt ("search-Seam"). `mcp_server/mcp_ask.py` ist ein CLI zum Testen.

`scripts/refresh.sh` orchestriert 1-2-3 + Validierung. `scripts/okf_validate.py` ist der OKF-Prüfer (Python-Port des Skill-Validators, weil hier kein Node).

## Die vier Nutzerfragen (User Stories), auf die alles einzahlt

- **U1** Aktuelle Position der Versicherungswirtschaft zu Thema X (Informationsstand der Mitglieder).
- **U2** Frühere GDV-Positionen zu einem geplanten Gesetz; hat sich die Position über die Zeit geändert?
- **U3** Rote Linien / nicht verhandelbare Positionen (konkret: welche Statistiken wurden als unverzichtbar genannt, wenn Bürokratieabbau droht?).
- **U4** Fachbereichsübergreifende Sicht: wer im Haus hat zu einem Thema Position bezogen?

Diese vier steuern Struktur und Register des Bündels. `verifikation_user_stories.md` dokumentiert einen End-to-End-Test dieser Fragen über den MCP-Server (kontextfreie Agenten).

## Stand und nächster Schritt

Bündel steht: rund 348 Dokumente (347 Volltext, 1 metadata-only), 2017-2026, DE + EN, konform (`okf_validate.py`: 0 Fehler). MCP-Server läuft lokal und wurde real getestet. Nächster Schritt = `SPEC.md`: **hybride semantische Suche (BM25 + lokale Embeddings via ollama, RRF)** hinter dem search-Seam. Grund: die lexikalische Suche verfehlt Paraphrasen (siehe U3 in der Verifikation). Modellwahl im SPEC nach der Retrieval-Spalte (nicht Mean): Default `snowflake-arctic-embed-l-v2.0` (ollama `snowflake-arctic-embed2`, retrieval-gebaut, mehrsprachig, Apache-2.0), A/B gegen `F2LLM-v2-8B` (deutsches Retrieval-Board Platz 2, via HF), garantierter Fallback `bge-m3`. Empirisch an U1-U4 entscheiden; jina-v3 wegen Lizenz meiden.

## Fallstricke und Umgebungswissen (spart dir Zeit)

- **docling-serve** (colima, `:5001`) hat einen Modell-Worker und OOM-crasht bei paralleler Last -> Konvertierung sequenziell (`WORKERS=1`), mit Retries. Tabellenerkennung (`do_table_structure`) ist der Speicherfresser; bei knappem VM-RAM `TABLES=off`. Die VM wurde auf 8 GB gebracht, dann läuft Tabellen-an stabil. Container hat KEINEN Internetzugang -> PDFs auf dem Host laden, dann als Datei hochladen. 3 englische EFRAG/IFRS-PDFs crashen docling reproduzierbar (als metadata-only im Bündel).
- **Kein Node** auf dem Host, System-Python ist **3.9** (zu alt für fastmcp). Für den MCP-Server-Test gibt es ein venv mit **Python 3.13 + fastmcp** im Scratchpad; die Pipeline-Skripte laufen auf 3.9 (nur stdlib).
- **Docker-Build hier nicht möglich** (colima-Buildumgebung ohne DNS/Netz); Images baut man in der Cloud (`az acr build`) oder wo Netz ist. Server wurde daher per venv getestet, nicht per Image.
- **firecrawl** (`:3002`) läuft auch, wurde aber nicht gebraucht (Scraper nutzt den `pageNum`-Fragment-Endpoint der Seite direkt).
- **Commits:** nur der Nutzer als Autor, KEIN Claude-Co-Author-Trailer (ausdrücklicher Wunsch).

## OKF-Konventionen (kurz)

Format: Markdown-Dateien mit YAML-Frontmatter, Spec bei GoogleCloudPlatform/knowledge-catalog. Der `/okf`-Skill liegt eine Ebene höher unter `../.claude/skills/okf/` (repo-weit, für alle Wissensdienste). Harte Regel: jedes Konzept hat ein nicht-leeres `type`. Validieren: `python3 scripts/okf_validate.py bundles/gdv-stellungnahmen --corpus` (0 Fehler). Konzepte verlinken auf Konzepte (Register), nicht auf `index.md`; Ausnahme: `overview.md` und `register/rote-linien.md` dürfen auf Register-Indexe zeigen (nur Warnung). GDV-Konzeptformat und Regeln stehen im Skill und werden von `build_bundle.py` erzeugt: nicht handverlesen editieren, sondern regenerieren.

## Stil

Deutsches Bündel. Substanz zuerst, dann Hintergrund. Keine Gedankenstriche (em/en dashes); Punkte, Kommata, Doppelpunkte, Klammern.
