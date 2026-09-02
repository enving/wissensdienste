"""build_bundle.py - baut den Wissensdienst `foerderrecht` aus einem Knowledge-Graph-Export.

Eingabe ist ein NetworkX-node-link-JSON (`knowledge_graph.json`) mit vier Knotenarten:

  document  ein PDF aus dem Formularschrank des Bundes (Metadaten, kein Text)
  chunk     ein Textabschnitt eines Dokuments, `<doc-id>_chunk_<n>`, mit `headings`
  law       ein Gesetz/eine Verordnung als Verweisziel (Stub, kein Volltext)
  concept   fachliche Klammer (Reisekosten, Personalkosten, ...)

und fünf Kantenarten: HAS_CHUNK, REFERENCES, SUPERSEDES, EQUIVALENT_TO, HAS_PART.

Ausgabe ist ein Ordner aus Markdown-Dateien: je Dokument eine Datei mit YAML-Frontmatter
und eingebettetem Volltext, dazu Gesetze als Verweisseiten und vier Register.

    python scripts/build_bundle.py --graph pfad/zu/knowledge_graph.json

Der Volltext wird aus den Chunks in Original-Reihenfolge zusammengesetzt und über das
Feld `headings` wieder in Abschnitte gegliedert. Maßgeblich bleibt immer das Original-PDF,
das jede Datei unter `quelle` verlinkt.
"""
import argparse
import collections
import datetime as dt
import json
import pathlib
import posixpath
import re
import sys
import unicodedata

INHALT = "wissen"   # Ordner mit dem eigentlichen Wissensbestand

# Kontaktadressen aus den Formularen werden nicht mitveröffentlicht: das maßgebliche
# Original-PDF ist in jeder Datei verlinkt und führt sie aktuell.
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_ERSATZ = "[Kontaktadresse: siehe Original-PDF]"

# Dokumentart aus dem Titel ableiten. Reihenfolge ist bedeutsam - der erste Treffer
# gewinnt, spezifische Muster stehen deshalb vor allgemeinen.
ART_REGELN = [
    (r"\bAnlage\b", "Anlage"),
    (r"Nebenbestimmung", "Nebenbestimmung"),
    (r"Richtlinie", "Richtlinie"),
    (r"Merkblatt|Hinweise|Leitfaden|Erläuterung", "Merkblatt"),
    (r"Vorkalkulation|Vorberechnung|Kalkulation", "Kalkulationshilfe"),
    (r"Antrag|Vorlage|Formular|Muster", "Formular"),
    (r"Rundschreiben|Bekanntmachung", "Bekanntmachung"),
    (r"Verordnung|Abschrift", "Rechtsgrundlage"),
]

KATEGORIE_TEXT = {
    "AZA (Ausgabenbasis)": "Zuwendungen auf Ausgabenbasis - der Regelfall für Hochschulen, "
                           "Forschungseinrichtungen und andere nicht gewerbliche Zuwendungsempfänger.",
    "AZK (Kostenbasis)": "Zuwendungen auf Kostenbasis - für Unternehmen der gewerblichen "
                         "Wirtschaft, die auf Basis von Selbstkosten abrechnen.",
    "AAA (Aufträge Ausgaben)": "Aufträge auf Ausgabenbasis - Beschaffung statt Zuwendung.",
    "AAK (Aufträge Kosten)": "Aufträge auf Kostenbasis - Beschaffung nach Selbstkostenpreisen.",
    "AZV (Zuweisungen/AZV)": "Zuweisungen an Gebietskörperschaften und Verwaltungs"
                             "vereinbarungen nach § 61 BHO.",
    "Altvorhaben": "Ältere Fassungen für laufende Vorhaben - maßgeblich ist die im "
                   "Bescheid genannte Fassung.",
    "Allgemein": "Übergreifende Regelwerke, Merkblätter und Rechtsgrundlagen ohne Bindung "
                 "an eine Antragsart.",
}

GESETZ_TITEL = {
    "BHO": "Bundeshaushaltsordnung",
    "VwVfG": "Verwaltungsverfahrensgesetz",
    "AO": "Abgabenordnung",
    "BGB": "Bürgerliches Gesetzbuch",
    "GWB": "Gesetz gegen Wettbewerbsbeschränkungen",
    "UVgO": "Unterschwellenvergabeordnung",
    "VOB": "Vergabe- und Vertragsordnung für Bauleistungen",
    "VOB/A": "VOB Teil A - Vergabe von Bauleistungen",
    "VOB/B": "VOB Teil B - Ausführung von Bauleistungen",
    "VgV": "Vergabeverordnung",
    "BRKG": "Bundesreisekostengesetz",
    "SGB_5": "Sozialgesetzbuch Fünftes Buch",
    "KHG": "Krankenhausfinanzierungsgesetz",
    "LUFTVG": "Luftverkehrsgesetz",
    "ATG": "Altersteilzeitgesetz",
    "AGVO": "Allgemeine Gruppenfreistellungsverordnung (EU) Nr. 651/2014",
    "AEUV": "Vertrag über die Arbeitsweise der Europäischen Union",
    "UStG": "Umsatzsteuergesetz",
}

GESETZ_URL = {
    "AGVO": "https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32014R0651",
    "AEUV": "https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:12012E/TXT",
}


def slug(s, maxlen=70):
    s = (s or "").strip().lower()
    s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = s.replace("/", "-")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:maxlen].rstrip("-") or "dokument"


def mask_emails(text):
    return EMAIL.sub(EMAIL_ERSATZ, text or "")


def q(s):
    """Ein Skalar als JSON-String - deckt sich mit YAML und spart eine Abhängigkeit."""
    return json.dumps(s or "", ensure_ascii=False)


def qlist(items):
    return "[" + ", ".join(json.dumps(i, ensure_ascii=False) for i in items) + "]"


def frontmatter(pairs):
    """pairs: (key, bereits serialisierter Wert). Leere Werte fallen raus."""
    lines = ["---"]
    for k, v in pairs:
        if v in (None, "", "[]", '""'):
            continue
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def dokumentart(titel):
    for muster, art in ART_REGELN:
        if re.search(muster, titel or "", re.I):
            return art
    return "Zuwendungsdokument"


def gesetz_key(node_id):
    """`law_BHO` und `law_law_BRKG` zeigen auf dasselbe Gesetz - Präfixe abtragen."""
    k = node_id
    while k.startswith("law_"):
        k = k[4:]
    return k.replace("_", "/") if k.startswith("VOB") and "_" in k else k


class Graph:
    """Schmaler Lesezugriff auf den node-link-Export."""

    def __init__(self, path):
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        self.docs = [n for n in data["nodes"] if n.get("node_type") == "document"]
        # node_type fehlt bei einem Teil der Chunks; `type` ist dort verlässlich.
        self.chunks = collections.defaultdict(list)
        for n in data["nodes"]:
            if n.get("node_type") == "chunk" or n.get("type") == "chunk":
                doc_id, _, idx = n["id"].rpartition("_chunk_")
                if doc_id and idx.isdigit():
                    self.chunks[doc_id].append((int(idx), n))
        for lst in self.chunks.values():
            lst.sort(key=lambda t: t[0])
        self.laws = [n for n in data["nodes"] if n.get("node_type") == "law"]
        self.by_rel = collections.defaultdict(list)
        for e in data["edges"]:
            self.by_rel[e.get("relation")].append(e)

    def rel(self, name):
        return self.by_rel.get(name, [])

    def chunks_of(self, doc_id):
        return [n for _i, n in self.chunks.get(doc_id, ())]


# --------------------------------------------------------------------------- Dokumente

def dokument_seite(e, chunks, nach_id, ersetzt, ersetzt_durch, gleichwertig, stamp):
    fm = frontmatter([
        ("art", q(e["art"])),
        ("titel", q(e["titel"])),
        ("kurzbeschreibung", q(e["beschreibung"])),
        ("quelle", e["url"]),
        ("kuerzel", q(e["kuerzel"])),
        ("kategorie", q(e["kategorie"])),
        ("ministerium", q(e["ministerium"])),
        ("herausgeber", q(e["herausgeber"])),
        ("stand", q(e["stand"])),
        ("gesetzesbezug", qlist(e["gesetze"]) if e["gesetze"] else ""),
        ("formular_id", q(e["doc_id"])),
        ("schlagworte", qlist(e["schlagworte"])),
        ("stand_bundle", stamp),
    ])

    out = [fm, f"\n# {e['titel']}\n", "\n# Einordnung\n\n"]
    zeile = f"- Dokumentart: **{e['art']}**"
    if e["kuerzel"]:
        zeile += f", Kürzel **{e['kuerzel']}**"
    out.append(zeile + ".\n")
    out.append(f"- Antragsart: [{e['kategorie']}]"
               f"(/register/nach-kategorie/{e['kat_slug']}.md).\n")
    if e["ministerium"]:
        z = f"- Ressort: [{e['ministerium']}](/register/nach-ministerium/{slug(e['ministerium'])}.md)"
        if e["herausgeber"] and e["herausgeber"] != e["ministerium"]:
            z += f", herausgegeben von {e['herausgeber']}"
        out.append(z + ".\n")
    if e["stand"]:
        out.append(f"- Stand: {e['stand']}.\n")
    if e["gesetze"]:
        links = ", ".join(f"[{g}](/gesetze/{slug(g)}.md)" for g in e["gesetze"])
        out.append(f"- Rechtsgrundlagen, auf die dieses Dokument verweist: {links}.\n")

    vor = ersetzt.get(e["doc_id"])
    nach = ersetzt_durch.get(e["doc_id"])
    gleich = sorted(gleichwertig.get(e["doc_id"], ()))
    if vor or nach or gleich:
        out.append("\n# Fassung\n\n")
        if nach:
            n = nach_id.get(nach)
            ziel = f"[{n['titel']}](/{n['pfad']}.md)" if n else f"`{nach}`"
            out.append(f"- **Ersetzt durch eine neuere Fassung:** {ziel}. Für neue Vorhaben "
                       f"ist die neuere Fassung maßgeblich.\n")
        if vor:
            v = nach_id.get(vor)
            ziel = f"[{v['titel']}](/{v['pfad']}.md)" if v else f"`{vor}`"
            out.append(f"- Ersetzt die frühere Fassung {ziel}.\n")
        for g in gleich:
            if g in nach_id:
                x = nach_id[g]
                out.append(f"- Inhaltlich gleichwertig zu [{x['titel']}](/{x['pfad']}.md).\n")
        out.append("\nDie vollständige Kette steht im "
                   "[Register der Versionsketten](/register/versionsketten.md).\n")

    out.append("\n# Quelle\n\n")
    if e["url"]:
        out.append(f"Original-PDF im Formularschrank des Bundes: <{e['url']}>\n\n")
    out.append("Maßgeblich ist stets das Original-PDF. Der hier eingebettete Text ist eine "
               "maschinelle Umsetzung und kann Tabellen und Formularfelder verkürzt wiedergeben.\n")

    out.append("\n# Volltext\n")
    if not chunks:
        out.append("\n*Für dieses Dokument liegt kein extrahierter Text vor - "
                   "siehe Original-PDF unter Quelle.*\n")
    aktuell = None
    for c in chunks:
        heads = c.get("headings") or []
        head = heads[-1] if heads else None
        if head and head != aktuell:
            out.append(f"\n## {head}\n")
            aktuell = head
        text = mask_emails((c.get("text") or "").strip())
        if text:
            out.append(f"\n{text}\n")
    return "".join(out)


def beschreibung(art, kuerzel, kategorie, ministerium):
    teile = [art]
    if kuerzel:
        teile.append(f"({kuerzel})")
    teile.append("im Zuwendungsrecht des Bundes")
    if kategorie and kategorie != "Allgemein":
        teile.append(f"- {kategorie}")
    if ministerium:
        teile.append(f", Ressort {ministerium}")
    return " ".join(teile).replace(" ,", ",")


# --------------------------------------------------------------------------- Gesetze

def gesetz_seite(key, gslug, zitierend, teile, stamp):
    titel = GESETZ_TITEL.get(key, key)
    url = GESETZ_URL.get(key) or f"https://www.gesetze-im-internet.de/{gslug.replace('-', '_')}/"
    fm = frontmatter([
        ("art", q("Rechtsgrundlage")),
        ("titel", q(f"{key} - {titel}" if titel != key else key)),
        ("kurzbeschreibung", q(f"Rechtsgrundlage, auf die {len(zitierend)} "
                               f"Dokument(e) dieses Dienstes verweisen.")),
        ("quelle", url),
        ("kuerzel", q(key)),
        ("schlagworte", qlist(["foerderrecht", "rechtsgrundlage", gslug])),
        ("stand_bundle", stamp),
    ])
    out = [fm, f"\n# {key} - {titel}\n\n",
           "Verweisseite: Dieser Dienst enthält **nicht** den Gesetzestext, sondern verweist "
           "auf die amtliche Fassung. Der Volltext liegt unter der Quelle.\n",
           f"\n# Quelle\n\n<{url}>\n"]
    if teile:
        out.append("\n# Teile\n\n")
        out.extend(f"- [{p}](/gesetze/{slug(p)}.md)\n" for p in sorted(teile))
    out.append("\n# Verweisende Dokumente\n\n")
    if zitierend:
        out.extend(f"- [{e['titel']}](/{e['pfad']}.md) - {e['kategorie']}\n"
                   for e in sorted(zitierend, key=lambda x: (x["kategorie"], x["titel"])))
    else:
        out.append("*Kein Dokument verweist derzeit ausdrücklich auf diese Rechtsgrundlage; "
                   "sie ist als Kontext hinterlegt.*\n")
    return "".join(out)


# --------------------------------------------------------------------------- Register

def register_seite(titel, kurz, schlagworte, ueberschrift, intro, zeilen, stamp):
    fm = frontmatter([
        ("art", q("Register")),
        ("titel", q(titel)),
        ("kurzbeschreibung", q(kurz)),
        ("schlagworte", qlist(schlagworte)),
        ("stand_bundle", stamp),
    ])
    return "".join([fm, f"\n# {ueberschrift}\n\n{intro}\n\n", *zeilen])


def schreibe_register(root, eintraege, gesetze, nach_id, ersetzt, ersetzt_durch,
                      gleichwertig, verworfen, stamp):
    reg = root / "register"

    # -- nach Antragsart --------------------------------------------------------
    nach_kat = collections.defaultdict(list)
    for e in eintraege:
        nach_kat[e["kategorie"]].append(e)

    zeilen = [f"- [{k}]({slug(k)}.md) - {len(v)} Dokument(e). {KATEGORIE_TEXT.get(k, '')}\n"
              for k, v in sorted(nach_kat.items())]
    write(reg / "nach-kategorie" / "index.md", register_seite(
        "Register: nach Antragsart",
        "Alle Antragsarten des Formularschranks mit ihren Dokumenten.",
        ["register", "kategorie"], "Register: nach Antragsart",
        "Die Antragsart bestimmt, welches Regelwerk gilt. Wähle zuerst hier.",
        zeilen, stamp))

    for kat, docs in nach_kat.items():
        zeilen = [f"- [{e['titel']}](/{e['pfad']}.md) - {e['art']}"
                  + (f", {e['ministerium']}" if e["ministerium"] else "") + "\n"
                  for e in sorted(docs, key=lambda x: (x["art"], x["titel"]))]
        write(reg / "nach-kategorie" / f"{slug(kat)}.md", register_seite(
            f"Antragsart: {kat}", KATEGORIE_TEXT.get(kat, f"Dokumente der Antragsart {kat}."),
            ["register", "kategorie", slug(kat)], kat,
            KATEGORIE_TEXT.get(kat, "") + f"\n\n{len(docs)} Dokument(e). Zurück zum "
            "[Register](/register/nach-kategorie/index.md).", zeilen, stamp))

    # -- nach Ressort -----------------------------------------------------------
    nach_min = collections.defaultdict(list)
    for e in eintraege:
        if e["ministerium"]:
            nach_min[e["ministerium"]].append(e)

    zeilen = [f"- [{m}]({slug(m)}.md) - {len(v)} Dokument(e)\n"
              for m, v in sorted(nach_min.items())]
    write(reg / "nach-ministerium" / "index.md", register_seite(
        "Register: nach Ressort", "Zuwendungsdokumente nach herausgebendem Bundesressort.",
        ["register", "ministerium"], "Register: nach Ressort",
        "Ressorts geben eigene Fassungen heraus. Prüfe, welches Ressort dein Vorhaben fördert.",
        zeilen, stamp))

    for m, docs in nach_min.items():
        zeilen = [f"- [{e['titel']}](/{e['pfad']}.md) - {e['kategorie']}\n"
                  for e in sorted(docs, key=lambda x: (x["kategorie"], x["titel"]))]
        write(reg / "nach-ministerium" / f"{slug(m)}.md", register_seite(
            f"Ressort: {m}", f"Dokumente des Ressorts {m} im Zuwendungsrecht des Bundes.",
            ["register", "ministerium", slug(m)], m,
            f"{len(docs)} Dokument(e). Zurück zum "
            "[Register](/register/nach-ministerium/index.md).", zeilen, stamp))

    # -- nach Rechtsgrundlage ---------------------------------------------------
    zeilen = []
    for g in sorted(gesetze, key=lambda x: -len(x["zitierend"])):
        titel = GESETZ_TITEL.get(g["key"], "")
        zeilen.append(f"- [{g['key']}](/gesetze/{g['slug']}.md)"
                      + (f" - {titel}" if titel else "")
                      + f" ({len(g['zitierend'])} Dokument(e))\n")
    write(reg / "nach-gesetz" / "index.md", register_seite(
        "Register: nach Rechtsgrundlage",
        "Gesetze und Verordnungen, auf die die Dokumente dieses Dienstes verweisen.",
        ["register", "gesetz"], "Register: nach Rechtsgrundlage",
        "Welche Dokumente sich auf eine Rechtsgrundlage stützen. Der Gesetzestext selbst "
        "liegt bei der amtlichen Quelle.", zeilen, stamp))

    # -- Versionsketten ---------------------------------------------------------
    ketten = []
    for e in eintraege:
        if e["doc_id"] in ersetzt_durch and e["doc_id"] not in ersetzt:
            kette, cur, gesehen = [e], e["doc_id"], set()
            while cur in ersetzt_durch and cur not in gesehen:
                gesehen.add(cur)
                cur = ersetzt_durch[cur]
                nxt = nach_id.get(cur)
                if not nxt:
                    break
                kette.append(nxt)
            if len(kette) > 1:
                ketten.append(kette)

    zeilen = []
    for kette in sorted(ketten, key=lambda c: c[0]["titel"]):
        zeilen.append(f"\n## {kette[-1]['titel']}\n\n")
        zeilen.append("Älteste zuerst, die **letzte Fassung ist maßgeblich** "
                      "für neue Vorhaben:\n\n")
        for i, e in enumerate(kette):
            marker = " **(aktuelle Fassung)**" if i == len(kette) - 1 else ""
            stand = f" - Stand {e['stand']}" if e["stand"] else ""
            zeilen.append(f"{i + 1}. [{e['titel']}](/{e['pfad']}.md){stand}{marker}\n")

    paare = set()
    for a, bs in gleichwertig.items():
        for b in bs:
            if a in nach_id and b in nach_id and (b, a) not in paare:
                paare.add((a, b))
    if paare:
        zeilen.append("\n## Inhaltlich gleichwertige Fassungen\n\n")
        zeilen.append("Unterschiedliche Dokumentnummern, gleicher Regelungsgehalt - etwa "
                      "dieselbe Fassung in zwei Ressortausgaben:\n\n")
        for a, b in sorted(paare):
            zeilen.append(f"- [{nach_id[a]['titel']}](/{nach_id[a]['pfad']}.md) "
                          f"= [{nach_id[b]['titel']}](/{nach_id[b]['pfad']}.md)\n")

    if verworfen:
        zeilen.append("\n## Nicht übernommene Ablöseangaben\n\n")
        zeilen.append("Die Ablösefolge stammt aus einer Heuristik über die Dokumentnummern. "
                      "Wo sie dem Stand-Feld der Dokumente widerspricht, ist sie hier nicht "
                      "übernommen - im Zweifel gilt das Stand-Feld und das Original-PDF:\n\n")
        for neu, alt, grund in sorted(verworfen):
            t_neu = nach_id.get(neu, {}).get("titel", neu)
            t_alt = nach_id.get(alt, {}).get("titel", alt)
            zeilen.append(f"- `{neu}` ({t_neu[:60]}) soll `{alt}` ({t_alt[:60]}) ablösen - "
                          f"verworfen: {grund}.\n")

    write(reg / "versionsketten.md", register_seite(
        "Register: Versionsketten",
        "Welche Fassung eines Regelwerks welche ablöst und welche aktuell gilt.",
        ["register", "versionen", "fassung"], "Versionsketten",
        "Zuwendungsdokumente erscheinen in Fassungen. Für ein laufendes Vorhaben gilt die "
        "im Zuwendungsbescheid genannte Fassung - nicht automatisch die neueste. Dieses "
        "Register macht die Ablösefolge sichtbar.", zeilen, stamp))

    write(reg / "index.md",
          "# Register\n\n"
          "- [Nach Antragsart](nach-kategorie/index.md) - AZA, AZK, AAA, AAK, AZV, "
          "Altvorhaben, Allgemein.\n"
          "- [Nach Ressort](nach-ministerium/index.md) - welches Bundesministerium die "
          "Fassung herausgibt.\n"
          "- [Nach Rechtsgrundlage](nach-gesetz/index.md) - welche Dokumente sich auf "
          "welches Gesetz stützen.\n"
          "- [Versionsketten](versionsketten.md) - welche Fassung welche ablöst.\n")


# --------------------------------------------------------------------------- Wurzel

def schreibe_wurzel(root, eintraege, gesetze, heute):
    kats = collections.Counter(e["kategorie"] for e in eintraege)
    ressorts = sorted({e["ministerium"] for e in eintraege if e["ministerium"]})
    write(root / "index.md", f"""# Förderrecht Bund - Formularschrank und Nebenbestimmungen

Die Richtlinien, Allgemeinen Nebenbestimmungen, Merkblätter und Formularerläuterungen aus
dem [Formularschrank des Bundes](https://foerderportal.bund.de/easy/easy_index.php?auswahl=easy_formularschrank),
je Dokument eine Markdown-Datei mit Metadaten und eingebettetem Volltext. Maßgeblich bleibt
stets das Original-PDF, das in jeder Datei unter *Quelle* verlinkt ist.

Der Dienst beantwortet die Fragen, die im Förderalltag tatsächlich gestellt werden:
*Welche Nebenbestimmungen gelten für mein Vorhaben? Darf ich diese Ausgabe abrechnen?
Welche Fassung gilt für meinen Bescheid?* Hier starten: [Überblick](overview.md).

# Einstiege

- **Nach Antragsart:** [Antragsartenregister](register/nach-kategorie/index.md). AZA, AZK,
  AAA, AAK, AZV. Die Antragsart entscheidet, welches Regelwerk überhaupt gilt - der
  wichtigste erste Schnitt.
- **Nach Ressort:** [Ressortregister](register/nach-ministerium/index.md). BMWK, BMUV,
  BMEL, BMDV und andere geben eigene Fassungen heraus.
- **Nach Rechtsgrundlage:** [Gesetzesregister](register/nach-gesetz/index.md). Welche
  Dokumente sich auf BHO, VwVfG, AGVO, VOB oder UVgO stützen.
- **Nach Fassung:** [Versionsketten](register/versionsketten.md). Welche Fassung welche
  ablöst - entscheidend, weil für ein Vorhaben die im Bescheid genannte Fassung gilt,
  nicht die neueste.
- **Strukturell:** [Dokumentbaum](dokumente/index.md), `dokumente/<antragsart>/<titel>-<nr>.md`.

# Stand

{len(eintraege)} Dokumente aus dem Formularschrank, {len(gesetze)} Rechtsgrundlagen als
Verweisseiten. Antragsarten: {', '.join(f'{k} ({v})' for k, v in sorted(kats.items()))}.
Ressorts: {', '.join(ressorts)}. Erzeugt am {heute} mit `scripts/build_bundle.py`.
Siehe [log.md](log.md).

# Was dieser Dienst nicht enthält

- **Keine Gesetzestexte.** Gesetze sind Verweisseiten unter `gesetze/` mit Link auf die
  amtliche Fassung bei gesetze-im-internet.de beziehungsweise EUR-Lex.
- **Keine Kontaktadressen.** In den Formularen abgedruckte E-Mail-Adressen sind ersetzt;
  aktuelle Ansprechpartner stehen im verlinkten Original-PDF.
- **Keine Rechtsberatung.** Der Dienst gibt amtliche Dokumente wieder, er legt sie nicht aus.
""")


def schreibe_overview(root, eintraege, gesetze, stamp):
    kats = collections.Counter(e["kategorie"] for e in eintraege)
    arten = collections.Counter(e["art"] for e in eintraege)
    top = sorted(gesetze, key=lambda x: -len(x["zitierend"]))[:8]
    fm = frontmatter([
        ("art", q("Überblick")),
        ("titel", q("Überblick: Förderrecht Bund")),
        ("kurzbeschreibung", q("Was der Dienst enthält, wie er aufgebaut ist und wie ein "
                               "Agent damit die typischen Förderfragen beantwortet.")),
        ("schlagworte", qlist(["foerderrecht", "overview"])),
        ("stand_bundle", stamp),
    ])
    kat_zeilen = "\n".join(f"- **{k}** ({v} Dokumente). {KATEGORIE_TEXT.get(k, '')}"
                           for k, v in sorted(kats.items(), key=lambda x: -x[1]))
    gesetz_zeilen = "\n".join(
        f"- [{g['key']}](/gesetze/{g['slug']}.md)"
        + (f" - {GESETZ_TITEL[g['key']]}" if g["key"] in GESETZ_TITEL else "")
        + f", {len(g['zitierend'])} Dokument(e)" for g in top)

    write(root / "overview.md", f"""{fm}
# Überblick

Dieser Dienst macht das **Zuwendungsrecht des Bundes** für einen KI-Agenten direkt lesbar.
Grundlage ist der Formularschrank des Bundes: {len(eintraege)} Dokumente - Richtlinien für
Zuwendungsanträge, Allgemeine Nebenbestimmungen, Merkblätter, Kalkulationshilfen und
Formularerläuterungen. Jedes Dokument liegt unter `dokumente/<antragsart>/<titel>-<nr>.md`
mit strukturierten Metadaten (Antragsart, Kürzel, Ressort, Stand, Gesetzesbezug) und dem
**vollständigen Text** aus dem Original-PDF.

Dokumentarten im Bestand: {', '.join(f'{k} ({v})' for k, v in arten.most_common())}.

# Aufbau

- `dokumente/<antragsart>/` - die Dokumente selbst, gruppiert nach Antragsart, Volltext eingebettet.
- `gesetze/` - Rechtsgrundlagen als Verweisseiten mit Link auf die amtliche Fassung. Der
  Dienst dupliziert keine Gesetzestexte.
- `register/nach-kategorie/` - je Antragsart ein Register.
- `register/nach-ministerium/` - je Ressort ein Register.
- `register/nach-gesetz/` - welche Dokumente sich auf welche Rechtsgrundlage stützen.
- `register/versionsketten.md` - die Ablösefolge der Fassungen.

Jedes Dokument verweist im Abschnitt *Einordnung* auf seine Register; die Register verweisen
zurück. Der Bestand ist damit als Graph navigierbar, nicht nur als Liste.

# Die Antragsart ist der erste Schnitt

Ob eine Ausgabe förderfähig ist, hängt zuerst daran, auf welcher Basis gefördert wird.
Dieselbe Frage hat auf Ausgabenbasis und auf Kostenbasis unterschiedliche Antworten.

{kat_zeilen}

# Fassungen sind nicht austauschbar

Für ein laufendes Vorhaben gilt die Fassung, die im **Zuwendungsbescheid** genannt ist -
nicht automatisch die neueste. Die ANBest-P etwa liegt in mehreren Fassungen vor, die
einander ablösen. Vor jeder Aussage zu einer konkreten Bewilligung deshalb die
[Versionsketten](/register/versionsketten.md) prüfen und die Fassung benennen, auf die sich
die Antwort stützt.

# Häufig herangezogene Rechtsgrundlagen

{gesetz_zeilen}

# So beantwortest du typische Fragen

- **"Welche Nebenbestimmungen gelten für mein Vorhaben?"** Erst die Antragsart klären
  (Ausgaben- oder Kostenbasis, Zuwendung oder Auftrag), dann über das
  [Antragsartenregister](/register/nach-kategorie/index.md) die ANBest der passenden Art.
- **"Darf ich diese Ausgabe abrechnen?"** Volltextsuche in der einschlägigen ANBest und den
  Richtlinien der Antragsart. Die Antwort mit der Nummer der Nebenbestimmung belegen.
- **"Welche Fassung gilt?"** Über die [Versionsketten](/register/versionsketten.md); die
  Fassung im Bescheid schlägt die neueste.
- **"Worauf stützt sich diese Regel?"** Über das
  [Gesetzesregister](/register/nach-gesetz/index.md) zur Rechtsgrundlage, dann zur amtlichen
  Fassung bei gesetze-im-internet.de.

# Belegen

Antworten immer mit dem Dokumenttitel und der Original-PDF-URL aus dem Feld `quelle` belegen.
Der eingebettete Text ist eine maschinelle Umsetzung: Tabellen und Formularfelder können
verkürzt sein. Bei Zweifeln auf das Original-PDF verweisen statt den Text zu paraphrasieren.
""")


def schreibe_log(root, eintraege, gesetze, heute):
    path = root / "log.md"
    kats = collections.Counter(e["kategorie"] for e in eintraege)
    eintrag = (f"## {heute}\n\n"
               f"- Neu erzeugt aus dem Formularschrank des Bundes: {len(eintraege)} Dokumente "
               f"({', '.join(f'{k}: {v}' for k, v in sorted(kats.items()))}), "
               f"{len(gesetze)} Rechtsgrundlagen als Verweisseiten, vier Register "
               f"(Antragsart, Ressort, Rechtsgrundlage, Versionsketten).\n")
    if path.exists():
        alt = path.read_text(encoding="utf-8")
        if f"## {heute}" in alt:
            return
        kopf, _, rest = alt.partition("\n\n")
        write(path, f"{kopf}\n\n{eintrag}\n{rest.lstrip()}")
    else:
        write(path, f"# Änderungshistorie\n\nNeueste zuerst.\n\n{eintrag}")


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- Bau

def pruefe_abloesefolge(graph):
    """SUPERSEDES-Kanten gegen das Stand-Feld prüfen.

    Der Graph leitet die Ablösefolge heuristisch aus Dateinamen ab und liegt dabei
    gelegentlich daneben - im Ausgangsbestand etwa "ANBest-P Januar 2014 ersetzt
    ANBest-P-Kosten September 2025", also elf Jahre rückwärts. Eine Fassung kann nur
    eine ältere ablösen, deshalb verwerfen wir jede Kante, deren Nachfolger nicht
    nachweislich jünger ist. Fehlt bei einem der beiden das Stand-Feld, lassen wir
    die Kante stehen - dann ist sie unbelegt, aber nicht widerlegt.

    Rückgabe: (ersetzt: {neu -> alt}, verworfen: [(neu, alt, grund), ...]).
    """
    stand = {n["id"]: (n.get("stand") or "") for n in graph.docs}
    ersetzt, verworfen = {}, []
    for e in graph.rel("SUPERSEDES"):
        neu, alt = e["source"], e["target"]
        s_neu, s_alt = stand.get(neu, ""), stand.get(alt, "")
        if s_neu and s_alt and s_neu <= s_alt:
            grund = ("gleicher Stand" if s_neu == s_alt
                     else f"Nachfolger ist älter ({s_neu} vor {s_alt})")
            verworfen.append((neu, alt, grund))
            continue
        ersetzt[neu] = alt
    return ersetzt, verworfen


def relativiere_links(root):
    """Bestands-absolute Links (/register/...) in relative umschreiben.

    Beim Erzeugen ist "/register/nach-gesetz/index.md" die bequeme Schreibweise: sie ist
    unabhängig davon, von wo aus verlinkt wird. Im Browser zeigt sie aber auf die
    Repo-Wurzel und damit ins Leere. Ein Durchgang am Ende macht daraus Links, die sowohl
    auf GitHub als auch in einem Editor funktionieren.

    Rückgabe: (umgeschriebene Links, Links ohne Ziel).
    """
    seiten = sorted(root.rglob("*.md"))
    vorhanden = {p.relative_to(root).as_posix() for p in seiten}
    muster = re.compile(r"\]\((/[^)]+)\)")
    umgeschrieben, tot = 0, []

    for seite in seiten:
        von = seite.parent.relative_to(root).as_posix()
        text = seite.read_text(encoding="utf-8")

        def ersetze(m):
            nonlocal umgeschrieben
            ziel = m.group(1).lstrip("/")
            if ziel not in vorhanden:
                tot.append((seite.relative_to(root).as_posix(), m.group(1)))
                return m.group(0)
            umgeschrieben += 1
            return "](" + posixpath.relpath(ziel, von or ".") + ")"

        neu = muster.sub(ersetze, text)
        if neu != text:
            seite.write_text(neu, encoding="utf-8")
    return umgeschrieben, tot


def build(graph, root, now):
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    heute = now.strftime("%Y-%m-%d")

    ersetzt, verworfen = pruefe_abloesefolge(graph)
    ersetzt_durch = {v: k for k, v in ersetzt.items()}
    gleichwertig = collections.defaultdict(set)
    for e in graph.rel("EQUIVALENT_TO"):
        gleichwertig[e["source"]].add(e["target"])
        gleichwertig[e["target"]].add(e["source"])

    doc_gesetze = collections.defaultdict(set)
    for e in graph.rel("REFERENCES"):
        if str(e["target"]).startswith("law_"):
            doc_gesetze[str(e["source"]).split("_chunk_")[0]].add(gesetz_key(e["target"]))

    eintraege = []
    for d in graph.docs:
        titel = (d.get("title") or "").strip() or f"Dokument {d['id']}"
        kategorie = d.get("category") or "Allgemein"
        art = dokumentart(titel)
        kuerzel = d.get("kuerzel") or ""
        # Ressortkürzel kommen im Graph gemischt vor (BLE/ble, bmwe, bmleh);
        # als Registerschlüssel müssen sie eindeutig sein.
        ministerium = (d.get("ministerium") or "").upper()
        kat_slug = slug(kategorie)
        eintraege.append({
            "doc_id": d["id"],
            # Die id wandert in den Dateinamen und macht ihn eindeutig; sie muss dafür
            # geslugt werden - drei ids enthalten "." oder "/" (z.B. "A/BNBest-P/BMU").
            "pfad": f"dokumente/{kat_slug}/{slug(titel, 60)}-{slug(str(d['id']), 24)}",
            "titel": titel,
            "art": art,
            "kategorie": kategorie,
            "kat_slug": kat_slug,
            "kuerzel": kuerzel,
            "ministerium": ministerium,
            "herausgeber": (d.get("herausgeber") or "").upper(),
            "stand": d.get("stand") or "",
            "url": d.get("url") or "",
            "gesetze": sorted(doc_gesetze.get(d["id"], ())),
            "beschreibung": beschreibung(art, kuerzel, kategorie, ministerium),
            "schlagworte": sorted({"foerderrecht", "bund", slug(kategorie, 30),
                                   *([slug(kuerzel, 30)] if kuerzel else []),
                                   *([slug(ministerium, 30)] if ministerium else [])}),
        })

    nach_id = {e["doc_id"]: e for e in eintraege}

    for e in eintraege:
        chunks = graph.chunks_of(e["doc_id"])
        e["chunks"] = len(chunks)
        write(root / f"{e['pfad']}.md",
              dokument_seite(e, chunks, nach_id, ersetzt, ersetzt_durch, gleichwertig, stamp))

    # Gesetze
    keys = {gesetz_key(n["id"]) for n in graph.laws}
    keys |= {g for e in eintraege for g in e["gesetze"]}
    teile = collections.defaultdict(list)
    for e in graph.rel("HAS_PART"):
        teile[gesetz_key(e["source"])].append(gesetz_key(e["target"]))

    gesetze = []
    for key in sorted(keys):
        zitierend = [e for e in eintraege if key in e["gesetze"]]
        gslug = slug(key)
        gesetze.append({"key": key, "slug": gslug, "zitierend": zitierend})
        write(root / "gesetze" / f"{gslug}.md",
              gesetz_seite(key, gslug, zitierend, teile.get(key, []), stamp))

    # Dokumentbaum-Index
    nach_kat = collections.defaultdict(list)
    for e in eintraege:
        nach_kat[e["kategorie"]].append(e)
    write(root / "dokumente" / "index.md",
          "# Dokumente\n\nStruktureller Einstieg als Baum, "
          "`dokumente/<antragsart>/<titel>-<nr>.md`.\n\n"
          + "".join(f"- [{k}]({slug(k)}/index.md) - {len(v)} Dokument(e)\n"
                    for k, v in sorted(nach_kat.items())))
    for kat, docs in nach_kat.items():
        write(root / "dokumente" / slug(kat) / "index.md",
              f"# {kat}\n\n" + "".join(
                  f"- [{e['titel']}]({pathlib.Path(e['pfad']).name}.md)\n"
                  for e in sorted(docs, key=lambda x: x["titel"])))

    schreibe_register(root, eintraege, gesetze, nach_id, ersetzt, ersetzt_durch,
                      gleichwertig, verworfen, stamp)
    schreibe_wurzel(root, eintraege, gesetze, heute)
    schreibe_overview(root, eintraege, gesetze, stamp)
    schreibe_log(root, eintraege, gesetze, heute)

    umgeschrieben, tot = relativiere_links(root)
    return eintraege, gesetze, verworfen, umgeschrieben, tot


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--graph", required=True, help="Pfad zu knowledge_graph.json")
    ap.add_argument("--out", default=None,
                    help="Zielordner (Default: ../wissen neben diesem Skript)")
    args = ap.parse_args()

    root = pathlib.Path(args.out) if args.out else \
        pathlib.Path(__file__).resolve().parents[1] / INHALT
    eintraege, gesetze, verworfen, umgeschrieben, tot = build(
        Graph(args.graph), root, dt.datetime.now(dt.timezone.utc))

    print(f"Geschrieben nach {root}")
    print(f"  {len(eintraege)} Dokumente, {len(gesetze)} Rechtsgrundlagen")
    print(f"  {umgeschrieben} Links relativiert")
    if tot:
        print(f"  ACHTUNG: {len(tot)} Link(s) ohne Ziel:")
        for seite, ziel in tot[:10]:
            print(f"    - {seite} -> {ziel}")
    if verworfen:
        print(f"  {len(verworfen)} SUPERSEDES-Kante(n) verworfen (Stand widerspricht):")
        for neu, alt, grund in verworfen:
            print(f"    - {neu} -> {alt}: {grund}")
    ohne = [e for e in eintraege if not e["chunks"]]
    if ohne:
        print(f"  Hinweis: {len(ohne)} Dokument(e) ohne extrahierten Text:")
        for e in ohne[:10]:
            print(f"    - {e['doc_id']}  {e['titel'][:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
