"""hybrid_test.py - misst, ob hybride Suche (lexikalisch + semantisch, gewichtete
RRF) das Retrieval gegenueber der heutigen rein lexikalischen MCP-Suche verbessert.

Siehe SPEC_semantischeErgaenzung_Test.md im Repo-Wurzelverzeichnis.

Drei Verfahren ueber denselben Bestand:
  1) lexikalisch  = mcp_server/bundle.py Bundle.search (Ist-Zustand von search/fetch)
  2) semantisch   = ollama-Embeddings, Kosinus, bestes Chunk je Dokument
  3) hybrid       = gewichtete Reciprocal Rank Fusion (RRF, k=60) aus 1) und 2)

Es wird EINMAL eingebettet und dann ein kleiner Gewichtungs-Sweep (Semantik-Gewicht)
ausgewertet; das beste Gewicht wird nach dem Gesamtbild gewaehlt (mittlerer Recall@5,
Tiebreak: U3-Paraphrase in Top-3, dann MRR), nicht von Hand auf einen Fall getrimmt.

Selbsttest der RRF-Fusion laeuft ohne ollama. Der Messlauf braucht ollama.

Aufruf (aus Repo-Wurzel oder aus diesem Ordner):
    python3 semantische_erweiterung/hybrid_test.py
Modell umschaltbar:
    EMBED_MODEL=bge-m3 python3 semantische_erweiterung/hybrid_test.py
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

OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
USE_NOMIC_PREFIX = "nomic" in MODEL.lower()  # nur nomic nutzt search_document/search_query
CHUNK_WORDS = 180
BATCH = 64
K_RRF = 60
TOPN = 20
SEM_WEIGHTS = [1.0, 1.5, 2.0, 3.0, 5.0]   # Semantik-Gewicht im Sweep (Lexik = 1.0)
OUT = os.path.join(HERE, "hybrid_ergebnisse.md")

CASES = [
    {"id": "U1", "q": "Aktuelle Position der Versicherungswirtschaft zur Nachhaltigkeitsberichterstattung CSRD ESRS",
     "gold": ["2026/stellungnahme-zu-den-fachlichen-empfehlungen-der-efrag-zum-esrs-verein",
              "2025/gdv-stellungnahme-zum-csrd-umsetzungsgesetz"]},
    {"id": "U2", "q": "Fruehere GDV-Positionen zum digitalen Euro und Veraenderung ueber die Zeit",
     "gold": ["2021/positionspapier-der-digitale-euro-aus-sicht-der-deutschen-versicherung",
              "2023/stellungnahme-zum-legislativvorschlag-der-europaischen-kommission-zur"]},
    {"id": "U3", "q": "Buerokratieabbau darf nicht zulasten verlaesslicher statistischer Grundlagen gehen",
     "para": "welche statistischen Daten sind unverzichtbar, welche rote Linie zieht der GDV",
     "gold": ["2026/stellungnahme-zum-entwurf-eines-ersten-unternehmensstatistikreformgese"]},
    {"id": "U4", "q": "Welche Fachbereiche des GDV haben zu kuenstlicher Intelligenz Position bezogen",
     "gold": ["2023/gdv-positionspapier-zum-beginn-der-trilogverhandlungen-zur-ki-verordnu",
              "2022/positionspapier-zum-eu-rechtsrahmen-fur-kunstliche-intelligenz",
              "2025/gdv-positionspapier-zur-definition-eines-ki-systems"]},
    {"id": "K", "q": "Zentrale Forderungen des GDV zum Solvency II Review Extrapolation Proportionalitaet Berichtspflichten",
     "gold": ["2020/solvency-ii-konsultation-der-kommission-und-gdv-positionen",
              "2024/gdv-stellungnahme-zur-umsetzung-des-neuen-proportionalitatsrahmens-unt"]},
    {"id": "S2-066", "q": "Gemeinsames Verbaendeschreiben zum Schrems II Urteil des EuGH finden",
     "gold": ["2020/verbandepapier-zum-schrems-ii-urteil-des-eugh",
              "2021/verbandeschreiben-zur-umsetzung-des-schrems-ii-urteils-des-eugh"]},
    {"id": "S2-058", "q": "Zentrale GDV-Positionen und Forderungen zur FiDA-Verordnung Financial Data Access",
     "gold": ["2023/stellungnahme-zum-rahmenwerk-fur-den-zugang-zu-finanzdaten-fida",
              "2024/positionspapier-fida-droht-ziele-zu-verfehlen-und-gefahrdet-damit-die",
              "2024/stellungnahme-zur-fida-regulation"]},
]


# ---------- gewichtete RRF (Kern, testbar ohne ollama) ----------
def rrf_fuse(ranked_lists, k=K_RRF, weights=None):
    """ranked_lists: Liste von ID-Listen (Rang 1 = Index 0). weights: Gewicht je Liste
    (Default alle 1.0). Rueckgabe: fusionierte ID-Liste, absteigend nach RRF-Score."""
    if weights is None:
        weights = [1.0] * len(ranked_lists)
    score = {}
    for lst, w in zip(ranked_lists, weights):
        for rank, doc_id in enumerate(lst, start=1):
            score[doc_id] = score.get(doc_id, 0.0) + w / (k + rank)
    return sorted(score, key=lambda d: score[d], reverse=True)


def _selftest():
    fused = rrf_fuse([["a", "b", "c"], ["a", "b", "d"]])
    assert fused[:2] == ["a", "b"], fused
    assert rrf_fuse([[], []]) == []
    assert rrf_fuse([["x", "y", "z"]]) == ["x", "y", "z"]
    # Gewicht zieht das in der starken Liste hohe Dokument nach vorn
    assert rrf_fuse([["b", "a"], ["a", "c"]], weights=[1.0, 3.0])[0] == "a"
    print("RRF-Selbsttest ok")


# ---------- Metriken ----------
def ranks_of_gold(ranked_ids, gold_stems):
    out = {}
    for g in gold_stems:
        r = None
        for i, doc_id in enumerate(ranked_ids, start=1):
            if g in doc_id:
                r = i
                break
        out[g] = r
    return out


def recall_at(ranks, n=5):
    return sum(1 for r in ranks.values() if r is not None and r <= n) / len(ranks)


def mrr(ranks):
    found = [r for r in ranks.values() if r is not None]
    return 1.0 / min(found) if found else 0.0


def mean(xs):
    return sum(xs) / len(xs)


# ---------- ollama ----------
def ollama_up():
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=3):
            return True
    except Exception:
        return False


def embed(texts):
    req = urllib.request.Request(
        OLLAMA + "/api/embed",
        data=json.dumps({"model": MODEL, "input": texts}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())["embeddings"]


def norm(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


# ---------- Messlauf ----------
def run():
    sys.path.insert(0, os.path.join(REPO, "mcp_server"))
    import bundle as B  # noqa: E402

    b = B.Bundle(BUNDLE)
    all_ids = list(b.docs.keys())
    missing = [(c["id"], g) for c in CASES for g in c["gold"] if not any(g in i for i in all_ids)]

    # semantischen Index einmal bauen
    chunks, owner = [], []
    for d in b.docs.values():
        words = d["body"].split()
        for i in range(0, len(words), CHUNK_WORDS):
            piece = " ".join(words[i:i + CHUNK_WORDS])
            if len(piece) < 40:
                continue
            prefix = "search_document: " if USE_NOMIC_PREFIX else ""
            chunks.append(prefix + d["title"] + "\n" + piece)
            owner.append(d["id"])
    t0 = time.time()
    vecs = []
    for i in range(0, len(chunks), BATCH):
        vecs.extend(norm(v) for v in embed(chunks[i:i + BATCH]))
    build_s = time.time() - t0

    def lexical(query):
        return [r["id"] for r in b.search(query, limit=TOPN)]

    def semantic(query):
        qv = norm(embed([("search_query: " if USE_NOMIC_PREFIX else "") + query])[0])
        best = {}
        for cid, v in zip(owner, vecs):
            s = sum(a * c for a, c in zip(qv, v))
            if s > best.get(cid, -1.0):
                best[cid] = s
        return [cid for cid, _ in sorted(best.items(), key=lambda kv: kv[1], reverse=True)[:TOPN]]

    # gewichtsunabhaengige Ranglisten je Fall einmal berechnen
    prep = {c["id"]: (lexical(c["q"]), semantic(c["q"]), c["gold"]) for c in CASES}
    u3 = next(c for c in CASES if c["id"] == "U3")
    u3p = (lexical(u3["para"]), semantic(u3["para"]), u3["gold"])

    def hybrid_list(lx, sm, wsem):
        return rrf_fuse([lx, sm], weights=[1.0, wsem])[:TOPN]

    def eval_weight(wsem):
        r5s, mrrs = [], []
        for lx, sm, gold in prep.values():
            rk = ranks_of_gold(hybrid_list(lx, sm, wsem), gold)
            r5s.append(recall_at(rk, 5))
            mrrs.append(mrr(rk))
        u3rank = ranks_of_gold(hybrid_list(u3p[0], u3p[1], wsem), u3["gold"])[u3["gold"][0]]
        lx, sm, gold = prep["S2-066"]
        both = all(r is not None and r <= 5 for r in ranks_of_gold(hybrid_list(lx, sm, wsem), gold).values())
        return mean(r5s), mean(mrrs), u3rank, both

    # Sweep + Auswahl (Recall@5, dann U3 in Top-3, dann MRR)
    sweep = [(w,) + eval_weight(w) for w in SEM_WEIGHTS]
    best_w = max(sweep, key=lambda t: (round(t[1], 4),
                                       1 if (t[3] is not None and t[3] <= 3) else 0,
                                       round(t[2], 4)))[0]

    # Baselines (gewichtsunabhaengig) fuer die Ausgabe
    def base_agg(idx):  # idx 0=lexikalisch, 1=semantisch
        r5s = [recall_at(ranks_of_gold(prep[c["id"]][idx], c["gold"]), 5) for c in CASES]
        mrrs = [mrr(ranks_of_gold(prep[c["id"]][idx], c["gold"])) for c in CASES]
        return mean(r5s), mean(mrrs)

    L = []
    L.append("# Hybride Suche: Messergebnis (gewichtete RRF)\n")
    L.append(f"Modell `{MODEL}`, Dokumente {len(b.docs)}, Abschnitte {len(chunks)}, "
             f"Embeddings gebaut in {build_s:.0f}s, RRF k={K_RRF}, Top-{TOPN}.\n")
    if missing:
        L.append("**Achtung, Gold-Staemme nicht gefunden:** "
                 + ", ".join(f"{cid}: `{g}`" for cid, g in missing) + "\n")

    L.append("## Gewichtungs-Sweep (Semantik-Gewicht, Lexik = 1.0)\n")
    L.append("| Semantik-Gewicht | mittl. Recall@5 | mittl. MRR | U3-Paraphrase Rang | S2-066 beide Top-5 |")
    L.append("| --- | --- | --- | --- | --- |")
    for w, r5, mr, u3r, both in sweep:
        mark = "  <- gewaehlt" if w == best_w else ""
        L.append(f"| {w:g}{mark} | {r5:.3f} | {mr:.3f} | {u3r if u3r else 'nicht in Top-%d' % TOPN} | {'ja' if both else 'nein'} |")
    L.append(f"\nGewaehltes Semantik-Gewicht: **{best_w:g}** (max. Recall@5, dann U3 in Top-3, dann MRR).\n")

    L.append("## Rang je Gold-Dokument (Top-%d), Recall@5, MRR - hybrid mit Gewicht %g\n" % (TOPN, best_w))
    for c in CASES:
        lx, sm, gold = prep[c["id"]]
        rows = [("lexikalisch", lx), ("semantisch", sm), ("hybrid", hybrid_list(lx, sm, best_w))]
        L.append(f"### {c['id']}\n")
        L.append("| Verfahren | Gold-Raenge | Recall@5 | MRR |")
        L.append("| --- | --- | --- | --- |")
        for name, lst in rows:
            rk = ranks_of_gold(lst, gold)
            rk_str = ", ".join(f"{os.path.basename(g)}={rk[g] if rk[g] else '-'}" for g in gold)
            L.append(f"| {name} | {rk_str} | {recall_at(rk, 5):.2f} | {mrr(rk):.2f} |")
        L.append("")

    lex_r5, lex_mrr = base_agg(0)
    sem_r5, sem_mrr = base_agg(1)
    hy_r5, hy_mrr, u3_rank, s066_both = eval_weight(best_w)
    L.append("## Aggregat (Mittel ueber alle Faelle)\n")
    L.append("| Verfahren | mittl. Recall@5 | mittl. MRR |")
    L.append("| --- | --- | --- |")
    L.append(f"| lexikalisch | {lex_r5:.3f} | {lex_mrr:.3f} |")
    L.append(f"| semantisch | {sem_r5:.3f} | {sem_mrr:.3f} |")
    L.append(f"| hybrid (Gewicht {best_w:g}) | {hy_r5:.3f} | {hy_mrr:.3f} |\n")

    L.append("## Sonderauswertung U3 (Paraphrase)\n")
    L.append(f"Paraphrase: \"{u3['para']}\"\n")
    L.append("| Verfahren | Rang Gold |")
    L.append("| --- | --- |")
    for name, lst in [("lexikalisch", u3p[0]), ("semantisch", u3p[1]),
                      ("hybrid", hybrid_list(u3p[0], u3p[1], best_w))]:
        r = ranks_of_gold(lst, u3["gold"])[u3["gold"][0]]
        L.append(f"| {name} | {r if r else 'nicht in Top-%d' % TOPN} |")
    L.append("")

    L.append("## Fazit gegen Erfolgskriterium (SPEC)\n")
    base_r5 = max(lex_r5, sem_r5)
    k1 = hy_r5 >= base_r5
    k2 = u3_rank is not None and u3_rank <= 3
    k3 = s066_both
    L.append(f"1. Recall@5 hybrid >= max(lex, sem): {'ERFUELLT' if k1 else 'NICHT'} ({hy_r5:.3f} vs {base_r5:.3f}).")
    L.append(f"2. U3-Paraphrase Gold in Top-3 (hybrid): {'ERFUELLT' if k2 else 'NICHT'} (Rang {u3_rank}).")
    L.append(f"3. S2-066 beide in Top-5 (hybrid): {'ERFUELLT' if k3 else 'NICHT'}.")
    verdict = "erfuellt" if (k1 and k2 and k3) else ("teilweise erfuellt" if (k1 or k2 or k3) else "nicht erfuellt")
    L.append(f"\n**Gesamt: {verdict}** (Semantik-Gewicht {best_w:g}).\n")
    L.append(f"Reproduktion: `EMBED_MODEL={MODEL} python3 semantische_erweiterung/hybrid_test.py`.\n")

    with open(OUT, "w") as f:
        f.write("\n".join(L))
    print(f"Ergebnis geschrieben: {OUT}\nGewaehltes Gewicht: {best_w:g}  Gesamt: {verdict}")


if __name__ == "__main__":
    _selftest()
    if not ollama_up():
        print(f"\nollama nicht erreichbar unter {OLLAMA}. Messlauf uebersprungen.\n"
              f"Zum Messen:\n  ollama serve\n  ollama pull {MODEL}\n"
              f"  EMBED_MODEL={MODEL} python3 semantische_erweiterung/hybrid_test.py")
        sys.exit(0)
    run()
