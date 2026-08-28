#!/usr/bin/env python3
"""build_bundle.py - assemble the gdv-stellungnahmen OKF bundle from the catalog + markdown.

Reads GDV_Stellungnahmen/catalog.json and GDV_Stellungnahmen/md/<blob_id>.md and
generates a conformant OKF v0.1 bundle under bundles/gdv-stellungnahmen/:

  index.md                      root, declares okf_version
  overview.md                   orientation + how an agent answers U1-U4
  log.md                        dated change history
  stellungnahmen/<year>/<slug>.md   one concept per document, full text embedded
  register/nach-thema/<slug>.md     topic register concepts (U1, U4)
  register/nach-fachbereich/<slug>.md  Fachbereich DRAFT concepts (U4) - for review
  register/nach-gesetz/<slug>.md    law/initiative register concepts (U2)
  register/rote-linien.md           curated red-lines stub (U3), to be filled by Fachbereiche

Each document concept links to its Thema / Fachbereich / Gesetz register concepts and
each register links back, so the bundle is a clean navigable graph, not just an index tree.

Idempotent: regenerates the whole bundle directory from the current catalog + md cache.
"""
import datetime
import json
import os
import re
import unicodedata

HERE = os.path.dirname(__file__)
SRC = os.path.join(HERE, "..", "GDV_Stellungnahmen")
CATALOG = os.path.join(SRC, "catalog.json")
MD_DIR = os.path.join(SRC, "md")
BUNDLE = os.path.join(HERE, "..", "bundles", "gdv-stellungnahmen")
NOW = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
TODAY = NOW[:10]

# ---------------------------------------------------------------------------
# Fachbereich draft mapping (site topic -> proposed GDV Fachbereich).
# This is a DRAFT for the Fachbereiche to correct. "Regulierung"/"Politik" are
# cross-cutting and do not determine a Fachbereich on their own.
# ---------------------------------------------------------------------------
CROSSCUTTING = {"Regulierung", "Politik", "Politische Positionen", "GDV", "Versicherungswirtschaft", "Gesellschaft", "Europa"}
TOPIC_TO_FB = {
    "Schaden & Unfall": "Schaden- und Unfallversicherung",
    "Naturgefahren": "Schaden- und Unfallversicherung",
    "Klimafolgenanpassung": "Schaden- und Unfallversicherung",
    "Pflichtversicherung": "Schaden- und Unfallversicherung",
    "Mobilität": "Kraftfahrt und Mobilität",
    "E-Mobilität": "Kraftfahrt und Mobilität",
    "Transport & Logistik": "Kraftfahrt und Mobilität",
    "Rente & Vorsorge": "Lebensversicherung und Altersvorsorge",
    "Betriebliche Altersversorgung": "Lebensversicherung und Altersvorsorge",
    "Private Altersvorsorge": "Lebensversicherung und Altersvorsorge",
    "Nachhaltigkeit": "Nachhaltigkeit und Klima",
    "Klima": "Nachhaltigkeit und Klima",
    "Kreislaufwirtschaft": "Nachhaltigkeit und Klima",
    "Digitalisierung": "Digitalisierung, KI und Cyber",
    "Künstliche Intelligenz": "Digitalisierung, KI und Cyber",
    "Cybersicherheit": "Digitalisierung, KI und Cyber",
    "Steuern": "Steuern",
    "Wirtschaft": "Volkswirtschaft und Märkte",
    "Konjunktur & Märkte": "Volkswirtschaft und Märkte",
}
FB_CROSSCUTTING = "Recht und Regulierung (übergreifend)"

# ---------------------------------------------------------------------------
# Gesetzes-/Vorhabensbezug: recognized laws and EU initiatives (U2). Extend freely.
# key -> (display name, regex to match in title+text)
# ---------------------------------------------------------------------------
GESETZE = {
    "solvency-ii": ("Solvency II", r"Solvency\s*II"),
    "vag": ("Versicherungsaufsichtsgesetz (VAG)", r"\bVAG\b|Versicherungsaufsichtsgesetz"),
    "ki-verordnung": ("KI-Verordnung (AI Act)", r"KI-Verordnung|AI\s*Act|KI-VO"),
    "dora": ("DORA (Digital Operational Resilience Act)", r"\bDORA\b"),
    "fida": ("FiDA (Financial Data Access)", r"\bFiDA\b|Financial Data Access"),
    "dsgvo": ("DSGVO / Datenschutz", r"DSGVO|Datenschutz-Grundverordnung|\bGDPR\b"),
    "lieferkettengesetz": ("Lieferkettengesetz / CSDDD", r"Lieferkettengesetz|Lieferketten|CSDDD|Sorgfaltspflicht"),
    "csrd-esrs": ("CSRD / ESRS (Nachhaltigkeitsberichterstattung)", r"\bCSRD\b|\bESRS\b|EFRAG|Nachhaltigkeitsbericht"),
    "digitaler-euro": ("Digitaler Euro", r"digitale[rn]?\s+Euro"),
    "jahressteuergesetz": ("Jahressteuergesetz", r"Jahressteuergesetz|\bJStG\b"),
    "buerokratieabbau": ("Bürokratieabbau / Omnibus", r"Bürokratieabbau|Bürokratieentlastung|Omnibus"),
    "geldwaesche": ("Geldwäsche / AML", r"Geldwäsche|Anti[- ]?Money|\bAMLA?\b"),
    "eu-kleinanleger": ("EU-Kleinanlegerstrategie (RIS)", r"Kleinanleger|Retail Investment"),
    "vsaag": ("VsAAG (Versicherungssanierung/-abwicklung)", r"\bVsAAG\b|Abwicklung.*Versicher"),
    "provisionen": ("Provisionen / Vermittlerrecht", r"Provision|Vermittler|IDD"),
}

# ---------------------------------------------------------------------------
def slugify(s, maxlen=70):
    s = unicodedata.normalize("NFKD", s)
    s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = s.encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return (s[:maxlen].rstrip("-")) or "dokument"


def yaml_list(items):
    return "[" + ", ".join(json.dumps(i, ensure_ascii=False) for i in items) + "]"


def fachbereiche_for(topics):
    fbs = []
    for t in topics:
        fb = TOPIC_TO_FB.get(t)
        if fb and fb not in fbs:
            fbs.append(fb)
    if not fbs:
        fbs = [FB_CROSSCUTTING]
    return fbs


def gesetze_for(text):
    hits = []
    for key, (name, rx) in GESETZE.items():
        if re.search(rx, text, re.I):
            hits.append((key, name))
    return hits


def first_para(md):
    for block in re.split(r"\n\s*\n", md):
        b = re.sub(r"[#>*_`\-]", "", block).strip()
        b = re.sub(r"\s+", " ", b)
        if len(b) > 60:
            return b[:300]
    return ""


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    docs = json.load(open(CATALOG, encoding="utf-8"))["documents"]
    # Include every catalog document. Those whose PDF converted carry the full text;
    # the few that docling could not parse become metadata-only concepts (still
    # discoverable, PDF one click away) so the corpus stays complete.
    ready = []
    with_text = 0
    for d in docs:
        md_path = os.path.join(MD_DIR, f"{d['blob_id']}.md") if d["blob_id"] else None
        if md_path and os.path.exists(md_path) and os.path.getsize(md_path) > 0:
            d["_md"] = open(md_path, encoding="utf-8").read()
            d["_has_text"] = True
            with_text += 1
        else:
            d["_md"] = ""
            d["_has_text"] = False
        ready.append(d)
    print(f"documents: {len(ready)} ({with_text} with full text, {len(ready) - with_text} metadata-only)")

    # assign slugs, paths, fachbereiche, gesetze
    used = set()
    for d in ready:
        year = (d["date"] or "0000")[:4]
        base = slugify(d["title"])
        slug = base
        key = f"{year}/{slug}"
        if key in used:
            slug = f"{base}-{d['blob_id']}"
        used.add(f"{year}/{slug}")
        d["_year"] = year
        d["_slug"] = slug
        d["_path"] = f"stellungnahmen/{year}/{slug}.md"      # concept id path
        d["_fbs"] = fachbereiche_for(d["topics"])
        d["_gesetze"] = gesetze_for((d["title"] + " " + d["_md"][:4000]))
        d["_desc"] = d["description"] or first_para(d["_md"])

    # ---- indexes: group by topic / fachbereich / gesetz / year ----
    from collections import defaultdict
    by_topic = defaultdict(list)
    by_fb = defaultdict(list)
    by_gesetz = defaultdict(list)
    by_year = defaultdict(list)
    for d in ready:
        for t in d["topics"]:
            by_topic[t].append(d)
        for fb in d["_fbs"]:
            by_fb[fb].append(d)
        for k, name in d["_gesetze"]:
            by_gesetz[k].append(d)
        by_year[d["_year"]].append(d)

    def newest(lst):
        return sorted(lst, key=lambda x: x["date"] or "0000-00-00", reverse=True)

    topic_slug = {t: slugify(t) for t in by_topic}
    fb_slug = {fb: slugify(fb) for fb in by_fb}

    # ================= document concepts =================
    for d in ready:
        fm = [
            "---",
            f'type: {d["doc_type"] or "Stellungnahme"}',
            f'title: {json.dumps(d["title"], ensure_ascii=False)}',
            f'description: {json.dumps(d["_desc"], ensure_ascii=False)}',
            f'resource: {d["pdf_url"]}',
            f'datum: {d["date"]}',
            f'dokumenttyp: {json.dumps(d["doc_type"], ensure_ascii=False)}',
            f'themen: {yaml_list(d["topics"])}',
            f'fachbereiche_entwurf: {yaml_list(d["_fbs"])}',
            f'gesetzesbezug: {yaml_list([n for _, n in d["_gesetze"]])}',
            f'sprache: {d["language"]}',
            f'blob_id: "{d["blob_id"]}"',
            f'tags: {yaml_list(["gdv", "stellungnahme" if d["doc_type"]=="Stellungnahme" else "positionspapier", *[topic_slug[t] for t in d["topics"]]])}',
            f"timestamp: {NOW}",
            "---",
            "",
            f"# {d['title']}",
            "",
        ]
        body = []
        if d["_desc"]:
            body += ["# Kurzfassung", "", d["_desc"], ""]
        # Einordnung: concept-to-concept links (topics, fachbereiche, gesetze)
        ein = ["# Einordnung", ""]
        ein.append(f"- Dokumenttyp: **{d['doc_type']}**, veröffentlicht am **{d['date']}** (Sprache: {d['language']}).")
        if d["topics"]:
            links = ", ".join(f"[{t}](/register/nach-thema/{topic_slug[t]}.md)" for t in d["topics"])
            ein.append(f"- Themen: {links}.")
        if d["_fbs"]:
            links = ", ".join(f"[{fb}](/register/nach-fachbereich/{fb_slug[fb]}.md)" for fb in d["_fbs"])
            ein.append(f"- Fachbereich (Entwurf): {links}.")
        if d["_gesetze"]:
            links = ", ".join(f"[{n}](/register/nach-gesetz/{k}.md)" for k, n in d["_gesetze"])
            ein.append(f"- Gesetzes-/Vorhabensbezug: {links}.")
        ein.append("")
        body += ein
        if d["_has_text"]:
            body += ["# Volltext", "",
                     "Aus dem Original-PDF konvertiert (docling, ohne Bilder). Maßgeblich ist stets das Original-PDF (siehe Quelle).",
                     "", d["_md"].strip(), ""]
        else:
            body += ["# Volltext", "",
                     "Volltext derzeit nicht verfügbar (automatische PDF-Konvertierung fehlgeschlagen). Maßgeblich und vollständig ist das Original-PDF (siehe Quelle).",
                     ""]
        body += ["# Quelle", "",
                 f"[{d['title']} (PDF, gdv.de)]({d['pdf_url']})", ""]
        write(os.path.join(BUNDLE, d["_path"]), "\n".join(fm + body))

    # ================= year index tree =================
    for year, lst in by_year.items():
        lines = [f"# Stellungnahmen {year}", "", f"{len(lst)} Dokument(e), neueste zuerst.", ""]
        for d in newest(lst):
            lines.append(f"- [{d['title']}]({d['_slug']}.md) — {d['date']} · {d['doc_type']}"
                         + (f" · {', '.join(d['topics'])}" if d["topics"] else ""))
        write(os.path.join(BUNDLE, "stellungnahmen", year, "index.md"), "\n".join(lines) + "\n")

    years = sorted(by_year, reverse=True)
    idx = ["# Stellungnahmen nach Jahr", "",
           "Strukturell-chronologischer Einstieg (schrittweise Offenlegung). Pfad: `stellungnahmen/<jahr>/<slug>.md`.", ""]
    for y in years:
        idx.append(f"- [{y}]({y}/index.md) — {len(by_year[y])} Dokument(e)")
    write(os.path.join(BUNDLE, "stellungnahmen", "index.md"), "\n".join(idx) + "\n")

    # ================= thema register =================
    for t, lst in by_topic.items():
        lst = newest(lst)
        oldest = lst[-1]["date"]
        newest_d = lst[0]["date"]
        fm = ["---", "type: Themenregister",
              f'title: {json.dumps("GDV-Positionen: " + t, ensure_ascii=False)}',
              f'description: {json.dumps(f"Alle GDV-Stellungnahmen und Positionspapiere zum Thema {t}, neueste zuerst.", ensure_ascii=False)}',
              f'thema: {json.dumps(t, ensure_ascii=False)}',
              f"anzahl: {len(lst)}",
              f"zeitraum: {oldest}/{newest_d}",
              f"tags: {yaml_list(['gdv','themenregister',topic_slug[t]])}",
              f"timestamp: {NOW}", "---", "",
              f"# GDV-Positionen zum Thema: {t}", "",
              f"{len(lst)} Dokument(e) im Zeitraum {oldest} bis {newest_d}, neueste zuerst. "
              "Für die aktuelle Position das oberste Dokument lesen; die Reihenfolge zeigt die Entwicklung im Zeitverlauf.", ""]
        rows = []
        for d in lst:
            rows.append(f"- [{d['title']}](/{d['_path']}) — {d['date']} · {d['doc_type']}")
        write(os.path.join(BUNDLE, "register", "nach-thema", f"{topic_slug[t]}.md"),
              "\n".join(fm + rows) + "\n")
    # thema index
    ti = ["# Register: nach Thema", "",
          "Themeneinstieg (U1, U4): welche Position die Versicherungswirtschaft zu einem Thema vertritt, und über welche Themen ein Vorhaben streut.", ""]
    for t in sorted(by_topic, key=lambda x: -len(by_topic[x])):
        ti.append(f"- [{t}]({topic_slug[t]}.md) — {len(by_topic[t])} Dokument(e)")
    write(os.path.join(BUNDLE, "register", "nach-thema", "index.md"), "\n".join(ti) + "\n")

    # ================= fachbereich register (Entwurf) =================
    for fb, lst in by_fb.items():
        lst = newest(lst)
        fm = ["---", "type: Fachbereich-Register (Entwurf)",
              f'title: {json.dumps("Fachbereich (Entwurf): " + fb, ensure_ascii=False)}',
              f'description: {json.dumps(f"Entwurf einer Fachbereichs-Zuordnung: GDV-Stellungnahmen mit Bezug zu {fb}. Von den Fachbereichen zu prüfen.", ensure_ascii=False)}',
              "status: entwurf",
              f'fachbereich: {json.dumps(fb, ensure_ascii=False)}',
              f"anzahl: {len(lst)}",
              f"tags: {yaml_list(['gdv','fachbereich-entwurf',fb_slug[fb]])}",
              f"timestamp: {NOW}", "---", "",
              f"# Fachbereich (Entwurf): {fb}", "",
              "> Automatischer Entwurf aus der Themen-Zuordnung der Website. Von den Fachbereichen zu bestätigen oder zu korrigieren "
              "(siehe [Rote Linien](/register/rote-linien.md) und README).", "",
              f"{len(lst)} zugeordnete(s) Dokument(e), neueste zuerst.", ""]
        rows = [f"- [{d['title']}](/{d['_path']}) — {d['date']} · {', '.join(d['topics']) or '—'}" for d in lst]
        write(os.path.join(BUNDLE, "register", "nach-fachbereich", f"{fb_slug[fb]}.md"),
              "\n".join(fm + rows) + "\n")
    fi = ["# Register: nach Fachbereich (Entwurf)", "",
          "Entwurf einer Fachbereichs-Zuordnung (U4). Automatisch aus den Themen abgeleitet, von den Fachbereichen zu prüfen.", ""]
    for fb in sorted(by_fb, key=lambda x: -len(by_fb[x])):
        fi.append(f"- [{fb}]({fb_slug[fb]}.md) — {len(by_fb[fb])} Dokument(e)")
    write(os.path.join(BUNDLE, "register", "nach-fachbereich", "index.md"), "\n".join(fi) + "\n")

    # ================= gesetz register =================
    for k, lst in by_gesetz.items():
        name = GESETZE[k][0]
        lst = newest(lst)
        fm = ["---", "type: Gesetzesregister",
              f'title: {json.dumps("GDV-Positionen zu: " + name, ensure_ascii=False)}',
              f'description: {json.dumps(f"GDV-Stellungnahmen mit Bezug zu {name}, neueste zuerst.", ensure_ascii=False)}',
              f'gesetz: {json.dumps(name, ensure_ascii=False)}',
              f"anzahl: {len(lst)}",
              f"tags: {yaml_list(['gdv','gesetzesregister',k])}",
              f"timestamp: {NOW}", "---", "",
              f"# GDV-Positionen zu: {name}", "",
              f"{len(lst)} Dokument(e), neueste zuerst. Nützlich, wenn zu einem geplanten/laufenden Vorhaben frühere GDV-Positionen gesucht werden (U2).", ""]
        rows = [f"- [{d['title']}](/{d['_path']}) — {d['date']} · {d['doc_type']}" for d in lst]
        write(os.path.join(BUNDLE, "register", "nach-gesetz", f"{k}.md"), "\n".join(fm + rows) + "\n")
    gi = ["# Register: nach Gesetz / Vorhaben", "",
          "Einstieg über konkrete Gesetze und EU-Vorhaben (U2). Erkannt aus Titel und Volltext; die Liste ist erweiterbar (siehe scripts/build_bundle.py).", ""]
    for k in sorted(by_gesetz, key=lambda x: -len(by_gesetz[x])):
        gi.append(f"- [{GESETZE[k][0]}]({k}.md) — {len(by_gesetz[k])} Dokument(e)")
    write(os.path.join(BUNDLE, "register", "nach-gesetz", "index.md"), "\n".join(gi) + "\n")

    # ================= rote linien (U3) stub =================
    rl = ["---", "type: Playbook",
          'title: "Rote Linien der GDV-Positionierung (Ausbaustufe)"',
          'description: "Kuratierte Sammlung nicht verhandelbarer Positionen der Versicherungswirtschaft; von den Fachbereichen zu befüllen."',
          "status: entwurf",
          'tags: ["gdv", "rote-linien", "playbook"]',
          f"timestamp: {NOW}", "---", "",
          "# Rote Linien der GDV-Positionierung", "",
          "Diese Seite beantwortet U3: *Was sind unverzichtbare, nicht verhandelbare Positionen?* "
          "Beispiel: unverzichtbare Statistiken, die bei einem Bürokratieabbau nicht wegfallen dürfen.", "",
          "## Vorgehen", "",
          "Der Volltext aller Stellungnahmen ist im Bündel eingebettet, daher lassen sich rote Linien direkt per Suche finden. "
          "Nützliche Einstiege:", "",
          "- Volltextsuche über `stellungnahmen/**/*.md` nach Formulierungen wie *unverzichtbar*, *zwingend*, *darf nicht*, *lehnt ab*, *Statistik*, *unerlässlich*.",
          "- Thematisch über das [Themenregister](/register/nach-thema/index.md) und das [Gesetzesregister](/register/nach-gesetz/index.md) eingrenzen.", "",
          "## Kuratierte rote Linien", "",
          "> Noch nicht befüllt. Diese Sektion ist als Fachbereichs-Ausbau vorgesehen: je rote Linie ein Stichpunkt mit Beleg-Link "
          "auf die Stellungnahme(n), die sie stützt. Siehe README, Abschnitt \"Ausbau mit den Fachbereichen\".", ""]
    write(os.path.join(BUNDLE, "register", "rote-linien.md"), "\n".join(rl) + "\n")

    # register index
    ri = ["# Register", "",
          "Thematische und rechtliche Einstiege in den Bestand.", "",
          "- [nach Thema](nach-thema/index.md) — Position zu einem Thema (U1), themenübergreifende Sicht (U4)",
          "- [nach Fachbereich (Entwurf)](nach-fachbereich/index.md) — wer im Haus zu einem Thema positioniert ist (U4)",
          "- [nach Gesetz / Vorhaben](nach-gesetz/index.md) — frühere Positionen zu einem Vorhaben (U2)",
          "- [Rote Linien](rote-linien.md) — nicht verhandelbare Positionen (U3)", ""]
    write(os.path.join(BUNDLE, "register", "index.md"), "\n".join(ri) + "\n")

    # ================= root index.md =================
    total = len(ready)
    span = f"{min(d['date'] for d in ready)} bis {max(d['date'] for d in ready)}"
    n_state = sum(1 for d in ready if d["doc_type"] == "Stellungnahme")
    n_pos = sum(1 for d in ready if d["doc_type"] == "Positionspapier")
    root = f"""---
okf_version: "0.1"
---

# GDV-Stellungnahmen

Ein OKF-Bündel der öffentlichen Positionspapiere und Stellungnahmen des Gesamtverbands der Deutschen Versicherer (GDV), je Dokument ein Konzept mit Metadaten und eingebettetem Volltext (aus dem Original-PDF konvertiert). Quelle und Single Point of Truth ist [gdv.de/gdv/positionen](https://www.gdv.de/gdv/positionen). Maßgeblich bleibt stets das Original-PDF, das in jedem Konzept unter der Quelle verlinkt ist.

Das Bündel ist auf Vollständigkeit angelegt und bleibt navigierbar über mehrere Einstiege statt einer flachen Liste. Hier starten: [Überblick](overview.md).

# Einstiege

- **Nach Thema:** [Themenregister](register/nach-thema/index.md). Welche Position die Versicherungswirtschaft zu einem Thema vertritt (U1) und über welche Themen ein Vorhaben streut (U4).
- **Nach Gesetz / Vorhaben:** [Gesetzesregister](register/nach-gesetz/index.md). Frühere GDV-Positionen zu einem konkreten Gesetz oder EU-Vorhaben (U2).
- **Nach Fachbereich (Entwurf):** [Fachbereichsregister](register/nach-fachbereich/index.md). Welcher Fachbereich zu einem Thema positioniert ist (U4). Automatischer Entwurf, von den Fachbereichen zu prüfen.
- **Rote Linien:** [Rote Linien](register/rote-linien.md). Nicht verhandelbare Positionen (U3), als Fachbereichs-Ausbau angelegt.
- **Nach Jahr:** [Chronologie](stellungnahmen/index.md). Struktureller Einstieg als Baum: `stellungnahmen/<jahr>/<slug>.md`.

# Stand

{total} Dokument(e) ({n_state} Stellungnahmen, {n_pos} Positionspapiere), Zeitraum {span}. Deutsch und Englisch. Erzeugt am {TODAY} mit den Skripten unter `scripts/` (scrape_gdv.py, convert_docling.py, build_bundle.py). Siehe [log.md](log.md).
"""
    write(os.path.join(BUNDLE, "index.md"), root)

    # ================= overview.md =================
    top5 = sorted(by_topic, key=lambda x: -len(by_topic[x]))[:6]
    overview = f"""---
type: Überblick
title: "Überblick: GDV-Stellungnahmen"
description: "Was das Bündel enthält, wie es aufgebaut ist und wie ein Agent die Nutzerfragen U1 bis U4 damit beantwortet."
tags: ["gdv", "overview"]
timestamp: {NOW}
---

# Überblick

Dieses Bündel bündelt die öffentlichen **Positionspapiere und Stellungnahmen des GDV** so, dass ein KI-Agent sie direkt lesen kann. Jedes Dokument ist ein Konzept unter `stellungnahmen/<jahr>/<slug>.md` mit strukturierten Metadaten (Datum, Dokumenttyp, Themen, Fachbereich-Entwurf, Gesetzesbezug, Sprache) und dem **vollständigen Text** aus dem Original-PDF.

Der Bestand ({total} Dokumente, {span}) ist über vier Register erschlossen, die auf die Nutzerfragen zugeschnitten sind.

# Aufbau

- `stellungnahmen/<jahr>/<slug>.md` — die Dokumente selbst, gruppiert nach Jahr, Volltext eingebettet.
- `register/nach-thema/` — je Thema ein Register, das alle Dokumente dazu chronologisch listet.
- `register/nach-gesetz/` — je erkanntem Gesetz/EU-Vorhaben ein Register.
- `register/nach-fachbereich/` — Entwurf einer Fachbereichs-Zuordnung (von den Fachbereichen zu bestätigen).
- `register/rote-linien.md` — kuratierte rote Linien (Ausbaustufe).

Jedes Dokument verweist im Abschnitt *Einordnung* auf seine Themen-, Fachbereichs- und Gesetzes-Register; die Register verweisen zurück. So ist der Bestand als Graph navigierbar, nicht nur als Liste.

Häufige Themen: {", ".join(top5)}.

# So werden die Nutzerfragen beantwortet

- **U1 (aktuelle Position zu Thema X):** Über das [Themenregister](/register/nach-thema/index.md) das Thema wählen; das oberste (neueste) Dokument gibt den aktuellen Stand, der eingebettete Volltext die Begründung.
- **U2 (frühere Positionen zu einem geplanten Gesetz, Entwicklung über die Zeit):** Über das [Gesetzesregister](/register/nach-gesetz/index.md) das Vorhaben wählen; die chronologische Liste je Thema/Gesetz zeigt, ob und wie sich die Position verändert hat.
- **U3 (rote Linien, z. B. unverzichtbare Statistiken):** Über [Rote Linien](/register/rote-linien.md) und Volltextsuche über alle Dokumente nach Formulierungen wie *unverzichtbar*, *zwingend erforderlich*, *lehnt ab*, *Statistik*.
- **U4 (fachbereichsübergreifende Themen):** Über das [Themenregister](/register/nach-thema/index.md) und das [Fachbereichsregister](/register/nach-fachbereich/index.md) sehen, welche Fachbereiche zu einem Thema Position bezogen haben.
"""
    write(os.path.join(BUNDLE, "overview.md"), overview)

    # ================= log.md (append-only; create if missing) =================
    log_path = os.path.join(BUNDLE, "log.md")
    entry = (f"## {TODAY}\n\n"
             f"- Bündel neu erzeugt aus gdv.de/gdv/positionen: {total} Dokumente "
             f"({n_state} Stellungnahmen, {n_pos} Positionspapiere), {len(by_topic)} Themen, "
             f"{len(by_gesetz)} Gesetzes-/Vorhabensregister, {len(by_fb)} Fachbereichs-Entwürfe. Zeitraum {span}.\n")
    if os.path.exists(log_path):
        old = open(log_path, encoding="utf-8").read()
        if f"## {TODAY}" not in old:
            head, _, rest = old.partition("\n\n")
            write(log_path, f"{head}\n\n{entry}\n{rest}")
    else:
        write(log_path, f"# Änderungshistorie\n\nNeueste zuerst.\n\n{entry}")

    print(f"wrote {len(ready)} document concepts, "
          f"{len(by_topic)} topics, {len(by_fb)} fachbereiche, {len(by_gesetz)} gesetze, {len(by_year)} years")


if __name__ == "__main__":
    main()
