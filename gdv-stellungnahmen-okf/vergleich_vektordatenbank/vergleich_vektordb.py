"""vergleich_vektordb.py - ehrlicher Vergleich: hochgeladener Wissensordner
(Vektordatenbank) gegen den MCP-Wissensdienst, ueber denselben Bestand.

Hintergrund
-----------
Ein hochgeladener Wissensordner (z. B. ein ChatGPT-Custom-GPT-Wissensordner) macht
beim Abruf im Kern dies: Dokumente in Abschnitte zerlegen, jeden Abschnitt in einen
Vektor einbetten, die Frage einbetten und per Aehnlichkeit die naechsten Abschnitte
zurueckgeben. Dieses Skript bildet genau das lokal ab (Embeddings via ollama), ueber
alle Dokumente des OKF-Buendels, und stellt es der heutigen MCP-Suche gegenueber
(lexikalisch, aus mcp_server/bundle.py, also exakt das, was die Tools search/fetch
liefern).

Zweck ist die Persistenz der Testergebnisse, damit sie reproduzierbar bleiben.
Der Punkt des Vergleichs ist architektonisch, nicht "welches Embedding-Modell":
die Vektorsuche findet semantisch oft gut, hat aber kein Datum, keine Struktur,
keine Register/Filter, keinen garantierten Beleg und wird nur manuell aktuell.

Voraussetzungen
---------------
- Python 3.9+ (nur Standardbibliothek).
- ollama laeuft lokal (http://localhost:11434) mit einem Embedding-Modell.
  Default: nomic-embed-text  (ollama pull nomic-embed-text)
- Das gebaute Buendel unter bundles/gdv-stellungnahmen.

Aufruf (aus dem Repo-Wurzelverzeichnis oder aus diesem Ordner):
    python3 vergleich_vektordatenbank/vergleich_vektordb.py
Modell ueberschreibbar:
    EMBED_MODEL=bge-m3 python3 vergleich_vektordatenbank/vergleich_vektordb.py

Ergebnisse werden nach stdout geschrieben; die im Repo abgelegte Fassung steht in
vergleich_vektordatenbank/ergebnisse_roh.txt (mit `python3 ... | tee` erzeugt).
"""
import json
import math
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BUNDLE = os.path.join(REPO, "bundles", "gdv-stellungnahmen")
sys.path.insert(0, os.path.join(REPO, "mcp_server"))
import bundle as B  # noqa: E402  (nach sys.path-Anpassung)

OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/api/embed"
MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
CHUNK_WORDS = 180
CAP_CHUNKS_PER_DOC = 25   # begrenzt die Arbeit; deckt den substantiellen Teil ab
BATCH = 64

# Je Anwendungsfall eine natuerlichsprachige Frage. Fuer Vektor- UND MCP-Suche wird
# dieselbe Eingabe verwendet (fairer Vergleich, keine Filter). Der MCP-Server bietet
# zusaetzlich Facetten-Filter (gesetz/thema/jahr), die die Treffer weiter schaerfen;
# siehe verifikation_user_stories.md.
QUERIES = {
    "U1 CSRD/ESRS aktuelle Position":
        "Aktuelle Position der Versicherungswirtschaft zur Nachhaltigkeitsberichterstattung CSRD ESRS",
    "U2 digitaler Euro Zeitverlauf":
        "Fruehere GDV-Positionen zum digitalen Euro und Veraenderung ueber die Zeit",
    "U3 rote Linie unverzichtbare Statistik":
        "Buerokratieabbau darf nicht zulasten verlaesslicher statistischer Grundlagen gehen welche Daten sind unverzichtbar rote Linie",
    "U4 KI fachbereichsuebergreifend":
        "Welche Fachbereiche des GDV haben zu kuenstlicher Intelligenz Position bezogen Kernaussagen",
    "K Solvency II Review Forderungen":
        "Zentrale Forderungen des GDV zum Solvency II Review Extrapolation Zinskurve Proportionalitaet Berichtspflichten",
    "S2-066 Auffinden gemeinsames Schreiben Schrems II":
        "Bereits veroeffentlichtes gemeinsames Schreiben der Wirtschaftsverbaende unter anderem GDV zum Schrems II Urteil des EuGH finden",
    "S2-058 FiDA belastbare Argumente":
        "Zentrale GDV-Positionen und Forderungen zur FiDA-Verordnung Financial Data Access fuer belastbare zitierbare Antworten auf Rueckfragen",
}


def embed(texts):
    req = urllib.request.Request(
        OLLAMA,
        data=json.dumps({"model": MODEL, "input": texts}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())["embeddings"]


def norm(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def main():
    b = B.Bundle(BUNDLE)
    docmeta = {d["id"]: d for d in b.docs.values()}

    # --- Index (das, was ein hochgeladener Wissensordner intern aufbaut) ---
    chunks, owner = [], []
    for d in b.docs.values():
        words = d["body"].split()
        n = 0
        for i in range(0, len(words), CHUNK_WORDS):
            if n >= CAP_CHUNKS_PER_DOC:
                break
            piece = " ".join(words[i:i + CHUNK_WORDS])
            if len(piece) < 40:
                continue
            chunks.append("search_document: " + d["title"] + "\n" + piece)
            owner.append(d["id"])
            n += 1
    print(f"Modell={MODEL}  Dokumente={len(b.docs)}  Abschnitte={len(chunks)}", flush=True)

    vecs, t0 = [], time.time()
    for i in range(0, len(chunks), BATCH):
        vecs.extend(norm(v) for v in embed(chunks[i:i + BATCH]))
    print(f"Embeddings gebaut in {time.time() - t0:.0f}s\n", flush=True)

    def top(scores):
        return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:5]

    for label, q in QUERIES.items():
        print("=" * 100)
        print(f"ANWENDUNGSFALL: {label}")
        print(f"Frage: {q}\n")

        # MCP (lexikalisch, wie search/fetch)
        print("  [MCP-Wissensdienst: lexikalische Suche]")
        for d in b.search(q, limit=5):
            print(f"    {d['datum']}  {d['id']}")

        # Vektor (wie hochgeladener Wissensordner)
        qv = norm(embed(["search_query: " + q])[0])
        best = {}
        for cid, v in zip(owner, vecs):
            s = sum(a * c for a, c in zip(qv, v))
            if s > best.get(cid, -1.0):
                best[cid] = s
        print("  [Hochgeladener Wissensordner: Vektorsuche]")
        for cid, s in top(best):
            d = docmeta[cid]
            print(f"    {s:.3f}  {d['datum']}  {d['id']}")
        print()


if __name__ == "__main__":
    main()
