"""bundle.py - load and search an OKF bundle. Standard library only.

Indexes the gdv-stellungnahmen bundle from disk: parses each document concept's
frontmatter + body, and provides lexical search and lookups. Kept dependency-free
(no PyYAML) so it runs anywhere and is unit-testable without the MCP stack; the
frontmatter we emit in build_bundle.py is regular enough to parse directly.

The search() function is the deliberate seam: today it is lexical (term frequency
with field weighting). To upgrade retrieval later (local embeddings, Azure AI
Search), replace only the body of search() / rank() - the MCP tool signatures and
everything above stay the same.
"""
import json
import os
import re
import unicodedata

DOC_DIR = "stellungnahmen"
REGISTER_DIR = "register"
RESERVED = {"index.md", "log.md", "overview.md"}

_TOKEN = re.compile(r"[a-z0-9äöüß]+", re.I)


def _fold(s):
    s = s.lower()
    s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def tokenize(s):
    return [_fold(t) for t in _TOKEN.findall(s or "")]


def parse_frontmatter(text):
    """Return (meta: dict, body: str). Tolerates the flat YAML we emit."""
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    fm, body = m.group(1), m.group(2)
    meta = {}
    for line in fm.splitlines():
        if not line.strip() or line[:1].isspace():
            continue
        i = line.find(":")
        if i == -1:
            continue
        key, val = line[:i].strip(), line[i + 1:].strip()
        meta[key] = _parse_value(val)
    return meta, body


def _parse_value(val):
    if val == "":
        return ""
    if val[0] == "[":
        try:
            return json.loads(val)
        except Exception:
            return [v.strip().strip('"') for v in val.strip("[]").split(",") if v.strip()]
    if val[0] in "\"'":
        try:
            return json.loads(val)
        except Exception:
            return val.strip("\"'")
    return val


class Bundle:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.docs = {}       # id -> dict(meta + body + id)
        self._load()

    # ---- loading ----
    def _load(self):
        doc_root = os.path.join(self.root, DOC_DIR)
        for dirpath, _dirs, files in os.walk(doc_root):
            for fn in files:
                if fn in RESERVED or not fn.endswith(".md"):
                    continue
                path = os.path.join(dirpath, fn)
                cid = os.path.relpath(path, self.root)[:-3].replace(os.sep, "/")
                meta, body = parse_frontmatter(open(path, encoding="utf-8").read())
                if not meta.get("type"):
                    continue
                self.docs[cid] = {
                    "id": cid,
                    "title": meta.get("title", cid),
                    "description": meta.get("description", ""),
                    "datum": meta.get("datum", ""),
                    "dokumenttyp": meta.get("dokumenttyp", meta.get("type", "")),
                    "themen": meta.get("themen", []) or [],
                    "gesetzesbezug": meta.get("gesetzesbezug", []) or [],
                    "fachbereiche": meta.get("fachbereiche_entwurf", []) or [],
                    "sprache": meta.get("sprache", ""),
                    "url": meta.get("resource", ""),
                    "body": body,
                }

    def stats(self):
        return {
            "documents": len(self.docs),
            "themen": sorted({t for d in self.docs.values() for t in d["themen"]}),
            "gesetze": sorted({g for d in self.docs.values() for g in d["gesetzesbezug"]}),
            "jahre": sorted({d["datum"][:4] for d in self.docs.values() if d["datum"]}),
        }

    # ---- file reads for navigation tools ----
    def read_relative(self, rel):
        rel = rel.lstrip("/")
        path = os.path.abspath(os.path.join(self.root, rel))
        if not path.startswith(self.root) or not os.path.exists(path):
            return None
        return open(path, encoding="utf-8").read()

    def overview(self):
        parts = []
        for name in ("index.md", "overview.md"):
            txt = self.read_relative(name)
            if txt:
                parts.append(txt)
        return "\n\n---\n\n".join(parts)

    def register(self, name):
        # name like "nach-thema/regulierung" or "nach-thema" (index) or "rote-linien"
        for cand in (f"{REGISTER_DIR}/{name}.md", f"{REGISTER_DIR}/{name}/index.md", f"{REGISTER_DIR}/{name}"):
            txt = self.read_relative(cand)
            if txt:
                return txt
        return None

    def get(self, doc_id):
        return self.docs.get(doc_id.lstrip("/"))

    # ---- search (the swappable seam) ----
    def _matches_filter(self, d, flt):
        if not flt:
            return True
        for key in ("thema", "gesetz", "fachbereich", "dokumenttyp", "sprache"):
            want = flt.get(key)
            if not want:
                continue
            if key == "thema" and not any(_fold(want) in _fold(t) for t in d["themen"]):
                return False
            if key == "gesetz" and not any(_fold(want) in _fold(g) for g in d["gesetzesbezug"]):
                return False
            if key == "fachbereich" and not any(_fold(want) in _fold(f) for f in d["fachbereiche"]):
                return False
            if key == "dokumenttyp" and _fold(want) not in _fold(d["dokumenttyp"]):
                return False
            if key == "sprache" and _fold(want) != _fold(d["sprache"]):
                return False
        jahr = flt.get("jahr")
        if jahr and not d["datum"].startswith(str(jahr)):
            return False
        return True

    def search(self, query, flt=None, limit=10):
        """Lexical ranking. Title/themen/gesetz weighted above body; recency tiebreak."""
        q = tokenize(query)
        results = []
        for d in self.docs.values():
            if not self._matches_filter(d, flt):
                continue
            score = self._score(d, q) if q else 0.0
            if q and score <= 0:
                continue
            results.append((score, d))
        # with a query: by score then recency; without: newest first
        results.sort(key=lambda sd: (sd[0], sd[1]["datum"]), reverse=True)
        return [d for _s, d in results[:limit]]

    def _score(self, d, q):
        if not q:
            return 0.0
        title = tokenize(d["title"])
        facets = tokenize(" ".join(d["themen"] + d["gesetzesbezug"] + d["fachbereiche"]))
        desc = tokenize(d["description"])
        body = tokenize(d["body"])
        bodyset = set(body)
        from collections import Counter
        bc = Counter(body)
        score = 0.0
        for term in q:
            score += 6.0 * title.count(term)
            score += 4.0 * facets.count(term)
            score += 2.0 * desc.count(term)
            score += min(bc.get(term, 0), 8) * 0.5  # cap body TF so long docs do not dominate
            if term in bodyset:
                score += 0.5
        return score


def load_bundle():
    root = os.environ.get("BUNDLE_DIR")
    if not root:
        # default: sibling bundles/gdv-stellungnahmen relative to this file
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.join(here, "..", "bundles", "gdv-stellungnahmen")
    return Bundle(root)


if __name__ == "__main__":
    import sys
    b = load_bundle()
    print("stats:", json.dumps(b.stats(), ensure_ascii=False)[:400])
    if len(sys.argv) > 1:
        for d in b.search(" ".join(sys.argv[1:]), limit=8):
            print(f"  {d['datum']}  {d['dokumenttyp']:15.15}  {d['title'][:70]}")
