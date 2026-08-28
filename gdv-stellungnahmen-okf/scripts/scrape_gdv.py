#!/usr/bin/env python3
"""scrape_gdv.py - harvest the full GDV positions/statements catalog.

Source: https://www.gdv.de/gdv/positionen  (Positionspapiere + Stellungnahmen, DE + EN).

The page renders a faceted-search widget. Its "Mehr laden" button calls a paginated
fragment endpoint (discovered by reading the site's JS bundle):

    /service/more/gdv/<NODE_ID>?c=<CATEGORY>&pageNum=<N>

Each page returns 9 result items until an empty page marks the end. We parse each
item (title, type, topic tags, date, description, pdf url), detect language, and
write a stable catalog.json. Re-running is safe; it overwrites the catalog.

No third-party deps (regex + stdlib), so it runs on the system Python.
"""
import html
import json
import os
import re
import sys
import time
import urllib.request

BASE = "https://www.gdv.de"
# The positions/statements search widget. NODE_ID and CATEGORY are taken from the
# page's search form (action="/service/refind/gdv/86764?c=136742,86808"). If GDV
# restructures the page, re-read those two values from the form and update here.
NODE_ID = "86764"
CATEGORY = "136742,86808"
MORE_URL = f"{BASE}/service/more/gdv/{NODE_ID}"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) GDV-OKF-Ingest/1.0"

OUT = os.path.join(os.path.dirname(__file__), "..", "GDV_Stellungnahmen", "catalog.json")

ITEM_RE = re.compile(r'<a\b([^>]*?)data-js-atom="search-result-item"[^>]*>(.*?)</a>', re.DOTALL)
ATTR_HREF = re.compile(r'href="([^"]+)"')
ATTR_TITLE = re.compile(r'title="([^"]*)"')
TYPE_TAG = re.compile(r'ibmix-search-result__type-tag">(.*?)</span>', re.DOTALL)
TOPIC_LI = re.compile(r'topic-tag-list-item">(.*?)</li>', re.DOTALL)
DATE_TAG = re.compile(r'ibmix-search-result__date">(.*?)</span>', re.DOTALL)
DESC_P = re.compile(r'ibmix-search-result__text[^>]*>(.*?)</p>', re.DOTALL)
TAGSTRIP = re.compile(r"<[^>]+>")

# quick DE/EN heuristic based on the TITLE (doc_type/description are always German).
EN_HINTS = re.compile(r"\b(the|and|of|for|on|to|in|a|position|statement|comments?|proposal|response|consultation|review|draft)\b", re.I)
DE_HINTS = re.compile(r"\b(und|der|die|das|den|des|zur|zum|für|von|mit|im|eine?|Positionspapier|Stellungnahme|Gesetz|Entwurf|Vorschläge?|Reform)\b", re.I)


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(TAGSTRIP.sub(" ", s or ""))).strip()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "ignore")


def detect_lang(title, *_ignored):
    # umlauts/ß in the title are a decisive German marker
    if re.search(r"[äöüßÄÖÜ]", title or ""):
        return "de"
    de = len(DE_HINTS.findall(title or ""))
    en = len(EN_HINTS.findall(title or ""))
    return "en" if en > de else "de"


def parse_iso_date(ddmmyyyy):
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", ddmmyyyy or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def blob_id(pdf_url):
    m = re.search(r"/resource/blob/(\d+)/", pdf_url)
    return m.group(1) if m else None


def parse_page(html_text):
    items = []
    for pre, body in ITEM_RE.findall(html_text):
        head = pre  # attributes of the <a> before data-js-atom
        # href/title may sit before or inside; search the whole anchor text
        whole = pre + body
        href_m = ATTR_HREF.search(head) or ATTR_HREF.search(whole)
        if not href_m:
            continue
        pdf = href_m.group(1)
        if ".pdf" not in pdf.lower():
            continue
        title = clean((ATTR_TITLE.search(head) or ATTR_TITLE.search(whole) or re.match("", "")).group(1)) if (ATTR_TITLE.search(head) or ATTR_TITLE.search(whole)) else ""
        typ = clean((TYPE_TAG.search(body).group(1) if TYPE_TAG.search(body) else ""))
        topics = [clean(t) for t in TOPIC_LI.findall(body)]
        date_raw = clean(DATE_TAG.search(body).group(1) if DATE_TAG.search(body) else "")
        desc = clean(DESC_P.search(body).group(1) if DESC_P.search(body) else "")
        pdf_abs = pdf if pdf.startswith("http") else BASE + pdf
        items.append({
            "blob_id": blob_id(pdf),
            "title": title,
            "doc_type": typ,           # "Positionspapier" | "Stellungnahme" | ...
            "topics": topics,          # site topic taxonomy
            "date": parse_iso_date(date_raw),
            "date_raw": date_raw,
            "description": desc,
            "pdf_url": pdf_abs,
            "language": detect_lang(title, desc, typ),
        })
    return items


def main():
    max_pages = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    catalog, seen = [], set()
    page = 0
    empty_streak = 0
    while page < max_pages:
        url = f"{MORE_URL}?c={CATEGORY}&pageNum={page}"
        try:
            body = fetch(url)
        except Exception as e:
            print(f"page {page}: fetch error {e}", file=sys.stderr)
            break
        items = parse_page(body)
        if not items:
            empty_streak += 1
            if empty_streak >= 2:   # tolerate one accidental empty page
                print(f"page {page}: empty (end of results)")
                break
        else:
            empty_streak = 0
        new = 0
        for it in items:
            key = it["blob_id"] or it["pdf_url"]
            if key in seen:
                continue
            seen.add(key)
            catalog.append(it)
            new += 1
        print(f"page {page}: {len(items)} items ({new} new), total {len(catalog)}")
        page += 1
        time.sleep(0.4)

    # newest first
    catalog.sort(key=lambda x: (x["date"] or "0000-00-00"), reverse=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"source": f"{BASE}/gdv/positionen", "count": len(catalog), "documents": catalog},
                  f, ensure_ascii=False, indent=2)
    # summary
    by_type, by_lang = {}, {}
    for d in catalog:
        by_type[d["doc_type"]] = by_type.get(d["doc_type"], 0) + 1
        by_lang[d["language"]] = by_lang.get(d["language"], 0) + 1
    print(f"\nWrote {len(catalog)} documents to {os.path.relpath(OUT)}")
    print("by type:", by_type)
    print("by language:", by_lang)


if __name__ == "__main__":
    main()
