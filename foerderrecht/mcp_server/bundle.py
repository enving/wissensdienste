"""bundle.py - lädt und durchsucht den Wissensbestand unter `wissen/`. Nur Standardbibliothek.

Liest jede Markdown-Datei unter `dokumente/` und `gesetze/`, zerlegt sie in Frontmatter
und Rumpf und stellt lexikalische Suche sowie Einzelabruf bereit. Bewusst ohne PyYAML,
damit der Loader ohne den MCP-Stack testbar ist; das Frontmatter, das build_bundle.py
schreibt, ist regelmäßig genug, um es direkt zu lesen.

`search()` ist die vorgesehene Nahtstelle: heute rein lexikalisch (Termfrequenz mit
Feldgewichtung). Für bessere Treffer später lokale Embeddings oder einen Suchindex
einsetzen - dann ändert sich nur der Rumpf von `search()` und `_score()`, die
MCP-Werkzeuge darüber bleiben unverändert.
"""
import json
import os
import re
import unicodedata
from collections import Counter

DOK_DIR = "dokumente"
GESETZ_DIR = "gesetze"
REGISTER_DIR = "register"
RESERVIERT = {"index.md", "log.md", "overview.md"}

_TOKEN = re.compile(r"[a-z0-9äöüß§]+", re.I)


def _fold(s):
    s = (s or "").lower()
    s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def tokenize(s):
    return [_fold(t) for t in _TOKEN.findall(s or "")]


def parse_frontmatter(text):
    """(meta: dict, rumpf: str). Verträgt das flache YAML, das build_bundle.py schreibt."""
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    kopf, rumpf = m.group(1), m.group(2)
    meta = {}
    for line in kopf.splitlines():
        if not line.strip() or line[:1].isspace():
            continue
        i = line.find(":")
        if i == -1:
            continue
        meta[line[:i].strip()] = _wert(line[i + 1:].strip())
    return meta, rumpf


def _wert(v):
    if v == "":
        return ""
    if v[0] == "[":
        try:
            return json.loads(v)
        except ValueError:
            return [x.strip().strip('"') for x in v.strip("[]").split(",") if x.strip()]
    if v[0] in "\"'":
        try:
            return json.loads(v)
        except ValueError:
            return v.strip("\"'")
    return v


class Wissensbestand:
    def __init__(self, wurzel):
        self.wurzel = os.path.abspath(wurzel)
        self.docs = {}
        self._laden()

    def _laden(self):
        for teil in (DOK_DIR, GESETZ_DIR):
            basis = os.path.join(self.wurzel, teil)
            for pfad, _dirs, dateien in os.walk(basis):
                for fn in dateien:
                    if fn in RESERVIERT or not fn.endswith(".md"):
                        continue
                    voll = os.path.join(pfad, fn)
                    doc_id = os.path.relpath(voll, self.wurzel)[:-3].replace(os.sep, "/")
                    meta, rumpf = parse_frontmatter(
                        open(voll, encoding="utf-8").read())
                    if not meta.get("art"):
                        continue
                    self.docs[doc_id] = {
                        "id": doc_id,
                        "ist_gesetz": teil == GESETZ_DIR,
                        "titel": meta.get("titel", doc_id),
                        "art": meta.get("art", ""),
                        "kurzbeschreibung": meta.get("kurzbeschreibung", ""),
                        "kuerzel": meta.get("kuerzel", ""),
                        "kategorie": meta.get("kategorie", ""),
                        "ministerium": meta.get("ministerium", ""),
                        "herausgeber": meta.get("herausgeber", ""),
                        "stand": meta.get("stand", ""),
                        "gesetzesbezug": meta.get("gesetzesbezug", []) or [],
                        "formular_id": meta.get("formular_id", ""),
                        "quelle": meta.get("quelle", ""),
                        "rumpf": rumpf,
                    }

    def stats(self):
        # nach Ordner unterscheiden, nicht nach `art`: einige Dokumente tragen
        # zu Recht die Art "Rechtsgrundlage" (z.B. Abschriften von Verordnungen)
        dokumente = [d for d in self.docs.values() if not d["ist_gesetz"]]
        return {
            "dokumente": len(dokumente),
            "rechtsgrundlagen": len(self.docs) - len(dokumente),
            "kategorien": sorted({d["kategorie"] for d in dokumente if d["kategorie"]}),
            "ministerien": sorted({d["ministerium"] for d in dokumente if d["ministerium"]}),
            "arten": sorted({d["art"] for d in dokumente if d["art"]}),
        }

    # ---- Dateizugriff für die Navigationswerkzeuge ----
    def lies(self, rel):
        rel = rel.lstrip("/")
        pfad = os.path.abspath(os.path.join(self.wurzel, rel))
        if not pfad.startswith(self.wurzel) or not os.path.isfile(pfad):
            return None
        return open(pfad, encoding="utf-8").read()

    def overview(self):
        teile = [t for t in (self.lies("index.md"), self.lies("overview.md")) if t]
        return "\n\n---\n\n".join(teile)

    def register(self, name):
        name = name.strip().lstrip("/")
        for kandidat in (f"{REGISTER_DIR}/{name}.md",
                         f"{REGISTER_DIR}/{name}/index.md",
                         f"{REGISTER_DIR}/{name}"):
            txt = self.lies(kandidat)
            if txt:
                return txt
        return None

    def get(self, doc_id):
        return self.docs.get(doc_id.lstrip("/"))

    # ---- Suche (die austauschbare Nahtstelle) ----
    def _passt(self, d, flt):
        if not flt:
            return True
        for feld in ("kategorie", "ministerium", "art", "kuerzel"):
            wunsch = flt.get(feld)
            if wunsch and _fold(wunsch) not in _fold(d[feld]):
                return False
        gesetz = flt.get("gesetz")
        if gesetz and not any(_fold(gesetz) == _fold(g) for g in d["gesetzesbezug"]):
            return False
        return True

    def search(self, query, flt=None, limit=10):
        """Lexikalisch. Titel, Kürzel und Kategorie wiegen schwerer als der Volltext;
        bei gleichem Score gewinnt der jüngere Stand."""
        q = tokenize(query)
        treffer = []
        for d in self.docs.values():
            if not self._passt(d, flt):
                continue
            score = self._score(d, q) if q else 0.0
            if q and score <= 0:
                continue
            treffer.append((score, d))
        # Relevanz in Fünferstufen bündeln, dann entscheidet der Stand. Derselbe
        # Regelungstext liegt hier in bis zu sechs Fassungen vor, die sich lexikalisch
        # kaum unterscheiden (ANBest-P: 32/32/32/31 Punkte) - ohne diese Stufung
        # gewinnt die Reihenfolge der Zufall statt die geltende Fassung.
        treffer.sort(key=lambda sd: (round(sd[0] / 5), sd[1]["stand"]), reverse=True)
        return [d for _s, d in treffer[:limit]]

    def _score(self, d, q):
        titel = tokenize(d["titel"])
        facetten = tokenize(" ".join(
            [d["kuerzel"], d["kategorie"], d["ministerium"], *d["gesetzesbezug"]]))
        kurz = tokenize(d["kurzbeschreibung"])
        rumpf = Counter(tokenize(d["rumpf"]))
        score = 0.0
        for term in q:
            score += 6.0 * titel.count(term)
            score += 4.0 * facetten.count(term)
            score += 2.0 * kurz.count(term)
            # Termfrequenz im Rumpf deckeln, damit lange Dokumente nicht dominieren
            score += min(rumpf.get(term, 0), 8) * 0.5
            if rumpf.get(term):
                score += 0.5
        return score


def load_bundle():
    wurzel = os.environ.get("WISSEN_DIR")
    if not wurzel:
        hier = os.path.dirname(os.path.abspath(__file__))
        wurzel = os.path.join(hier, "..", "wissen")
    return Wissensbestand(wurzel)


if __name__ == "__main__":
    import sys
    b = load_bundle()
    print("stats:", json.dumps(b.stats(), ensure_ascii=False)[:400])
    if len(sys.argv) > 1:
        for d in b.search(" ".join(sys.argv[1:]), limit=8):
            print(f"  {d['stand'] or '        '}  {d['art']:20.20}  {d['titel'][:70]}")
