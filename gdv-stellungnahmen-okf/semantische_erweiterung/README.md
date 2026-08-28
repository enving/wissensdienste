# Semantische Erweiterung (lokaler Test)

Lokale Ausbaustufe des MCP-Wissensdienstes: **hybride Suche** (Stichwortsuche + semantische Suche via Embeddings, per Reciprocal Rank Fusion kombiniert). Dieser Ordner enthält den Test, der misst, ob die hybride Suche das Retrieval gegenüber der heutigen, rein lexikalischen MCP-Suche verbessert.

Spezifikation: `../SPEC_semantischeErgänzung_Test.md`.

## Inhalt

- `hybrid_test.py` - vergleicht lexikalisch (`mcp_server/bundle.py`) vs. rein semantisch (ollama-Embeddings) vs. hybrid (RRF) über die 7 Anwendungsfälle (U1-U4, K, S2-066, S2-058). Enthält einen `assert`-Selbsttest der RRF-Fusion (läuft ohne ollama).
- `hybrid_ergebnisse.md` - Messergebnis (entsteht beim Lauf): Rang je Gold-Dokument, Recall@5, MRR, Sonderauswertungen (U3-Paraphrase, S2-066-Mehrfachtreffer) und Fazit gegen das Erfolgskriterium.

## Ausführen

```sh
# ollama muss laufen und ein Embedding-Modell bereitstehen
ollama pull nomic-embed-text
python3 semantische_erweiterung/hybrid_test.py
# Modell umschaltbar:
EMBED_MODEL=snowflake-arctic-embed2 python3 semantische_erweiterung/hybrid_test.py
```

Python 3.9, nur Standardbibliothek + ollama-HTTP. Keine weitere Abhängigkeit. Idempotent, schreibt nur in diesen Ordner.
