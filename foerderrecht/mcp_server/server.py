"""server.py - MCP-Server über den Wissensdienst `foerderrecht`.

Stellt den Bestand jedem MCP-Client (Claude, ChatGPT, Cursor, ...) über streamable HTTP
bereit. Werkzeuge:

  search / fetch     die beiden Werkzeuge, die OpenAIs MCP-Connectors erwarten
                     (Deep Research), in ihrer genauen Signatur - damit ChatGPT ohne
                     Zusatzarbeit funktioniert.
  get_overview       gibt die Navigationslogik zurück, damit ein Client die Register
                     nutzt statt zu raten.
  list_documents     Metadaten-Liste mit Facettenfiltern.
  get_register       ein Register: nach-kategorie, nach-ministerium, nach-gesetz,
                     versionsketten.
  welche_fassung     die Ablösefolge zu einem Regelwerk - die Frage, bei der ein
                     falscher Treffer im Förderrecht teuer wird.

Die Suche ist heute lexikalisch (siehe bundle.Wissensbestand.search - die austauschbare
Nahtstelle). Lokale Embeddings oder ein Suchindex lassen sich dort einsetzen, ohne diese
Werkzeuge anzufassen.

Authentifizierung steht bewusst nicht in diesem Code. Sie wird beim Deploy über die
Umgebungsvariablen von FastMCP gesetzt (siehe mcp_server/README.md). Ohne gesetzte
Auth-Variablen läuft der Server offen - in Ordnung für lokalen Betrieb, nicht für einen
öffentlich erreichbaren Endpunkt.
"""
import os
import re
from typing import Optional

from fastmcp import FastMCP

from bundle import load_bundle

BESTAND = load_bundle()
_STATS = BESTAND.stats()

INSTRUCTIONS = f"""
Dieser Server stellt das Zuwendungsrecht des Bundes bereit: {_STATS['dokumente']} Dokumente
aus dem Formularschrank (Richtlinien, Allgemeine Nebenbestimmungen, Merkblätter,
Kalkulationshilfen) mit eingebettetem Volltext, dazu {_STATS['rechtsgrundlagen']}
Rechtsgrundlagen als Verweisseiten. Maßgeblich ist immer das Original-PDF (Feld `quelle`).

Zwei Dinge entscheiden im Förderrecht über richtig oder falsch:

1. **Die Antragsart.** Ausgabenbasis (AZA) und Kostenbasis (AZK) beantworten dieselbe Frage
   unterschiedlich, Aufträge (AAA/AAK) noch einmal anders. Kläre die Antragsart, bevor du
   ein Regelwerk heranziehst, und filtere mit `kategorie`.
2. **Die Fassung.** Für ein laufendes Vorhaben gilt die Fassung, die im Zuwendungsbescheid
   genannt ist - nicht die neueste. Prüfe mit `welche_fassung(...)` oder
   `get_register("versionsketten")`, welche Fassungen existieren, und benenne in der
   Antwort die Fassung, auf die du dich stützt.

So beantwortest du typische Fragen:
- Welche Nebenbestimmungen gelten? Antragsart klären, dann
  list_documents(kategorie=..., art="Nebenbestimmung").
- Darf ich diese Ausgabe abrechnen? search(query=..., kategorie=...) und mit der Nummer der
  Nebenbestimmung belegen.
- Worauf stützt sich eine Regel? search(..., gesetz="BHO") oder get_register("nach-gesetz").

Zitiere jede Aussage mit Dokumenttitel, Fassung (Feld `stand`) und der `quelle`-URL. Der
eingebettete Text ist eine maschinelle PDF-Umsetzung: Tabellen und Formularfelder können
verkürzt sein. Bei Zweifeln auf das Original-PDF verweisen statt zu paraphrasieren.
Dieser Dienst gibt amtliche Dokumente wieder - er ist keine Rechtsberatung.
""".strip()

mcp = FastMCP(name="foerderrecht", instructions=INSTRUCTIONS)


def _treffer(d):
    return {"id": d["id"], "title": d["titel"], "url": d["quelle"]}


@mcp.tool
def search(
    query: str,
    kategorie: Optional[str] = None,
    ministerium: Optional[str] = None,
    art: Optional[str] = None,
    kuerzel: Optional[str] = None,
    gesetz: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Suche im Zuwendungsrecht des Bundes.

    Liefert die relevantesten Dokumente; bei vergleichbarer Relevanz die jüngere Fassung
    zuerst. Filter grenzen ein: kategorie (Antragsart, z. B. "AZA" oder "AZK"), ministerium
    (z. B. "BMWK"), art ("Nebenbestimmung", "Richtlinie", "Merkblatt", "Formular", ...),
    kuerzel (z. B. "ANBest-P"), gesetz (z. B. "BHO", "AGVO", "VOB/A").

    Rückgabe: {"results": [{"id", "title", "url"}, ...]}. Danach fetch(id) für den Volltext.
    Achtung: Dasselbe Regelwerk liegt in mehreren Fassungen vor - prüfe mit
    welche_fassung(kuerzel), welche gilt.
    """
    flt = {"kategorie": kategorie, "ministerium": ministerium, "art": art,
           "kuerzel": kuerzel, "gesetz": gesetz}
    flt = {k: v for k, v in flt.items() if v}
    hits = BESTAND.search(query, flt=flt or None, limit=max(1, min(limit, 50)))
    return {"results": [_treffer(d) for d in hits]}


@mcp.tool
def fetch(id: str) -> dict:
    """Hole den Volltext eines Dokuments per id (aus einem search-Treffer).

    Rückgabe: {"id", "title", "text", "url", "metadata"}. `text` ist der aus dem
    Original-PDF konvertierte Volltext samt Einordnung und Fassungshinweis; `url` verweist
    auf das maßgebliche PDF im Formularschrank des Bundes.
    """
    d = BESTAND.get(id)
    if not d:
        raise ValueError(f"Unbekannte id: {id}")
    return {
        "id": d["id"],
        "title": d["titel"],
        "text": d["rumpf"],
        "url": d["quelle"],
        "metadata": {
            "art": d["art"],
            "kuerzel": d["kuerzel"],
            "kategorie": d["kategorie"],
            "ministerium": d["ministerium"],
            "herausgeber": d["herausgeber"],
            "stand": d["stand"],
            "gesetzesbezug": d["gesetzesbezug"],
            "formular_id": d["formular_id"],
        },
    }


@mcp.tool
def get_overview() -> str:
    """Gib die Navigationslogik des Dienstes zurück (index.md + overview.md).

    Erklärt Aufbau, Register, die Rolle der Antragsart und den Umgang mit Fassungen.
    """
    return BESTAND.overview()


@mcp.tool
def list_documents(
    kategorie: Optional[str] = None,
    ministerium: Optional[str] = None,
    art: Optional[str] = None,
    kuerzel: Optional[str] = None,
    gesetz: Optional[str] = None,
    limit: int = 25,
) -> list:
    """Liste Dokumente (Metadaten, jüngste Fassung zuerst) mit optionalen Facettenfiltern.

    Ohne Suchbegriff, rein über Filter. Gut für "alle Nebenbestimmungen auf Kostenbasis"
    (kategorie="AZK", art="Nebenbestimmung") oder "was gibt das BMWK heraus".
    """
    flt = {"kategorie": kategorie, "ministerium": ministerium, "art": art,
           "kuerzel": kuerzel, "gesetz": gesetz}
    flt = {k: v for k, v in flt.items() if v}
    hits = BESTAND.search("", flt=flt or None, limit=max(1, min(limit, 200)))
    return [{
        "id": d["id"], "title": d["titel"], "art": d["art"], "kuerzel": d["kuerzel"],
        "kategorie": d["kategorie"], "ministerium": d["ministerium"], "stand": d["stand"],
        "gesetzesbezug": d["gesetzesbezug"], "url": d["quelle"],
    } for d in hits]


@mcp.tool
def get_register(name: str) -> str:
    """Gib ein Register zurück. Gültige Namen:

    "nach-kategorie" (Übersicht) oder "nach-kategorie/aza-ausgabenbasis" (eine Antragsart),
    "nach-ministerium" oder "nach-ministerium/bmwk", "nach-gesetz",
    "versionsketten" (welche Fassung welche ablöst).
    Register verlinken auf die zugehörigen Dokument-ids.
    """
    txt = BESTAND.register(name)
    if txt is None:
        raise ValueError(
            f"Unbekanntes Register: {name}. Verfügbar: nach-kategorie, nach-ministerium, "
            f"nach-gesetz, versionsketten.")
    return txt


def _familie(titel):
    """Regelwerksfamilie aus dem Titel: alles vor der Fassungsklammer am Ende.

    "... zur Projektförderung (ANBest-P; April 2025)"              -> "... zur Projektförderung"
    "... zur Projektförderung auf Kostenbasis (ANBest-P-Kosten; ...)" -> "... auf Kostenbasis"

    Nötig, weil das Kürzel allein nicht trennscharf ist: ANBest-P und ANBest-P-Kosten
    sind verschiedene Regelwerke, tragen im Bestand aber beide "ANBest-P" im Kürzelfeld.
    """
    return re.sub(r"\s*\([^)]*\)\s*$", "", titel or "").strip() or (titel or "")


@mcp.tool
def welche_fassung(kuerzel: str) -> dict:
    """Welche Fassungen eines Regelwerks es gibt und welche die jüngste ist.

    Für ein laufendes Vorhaben gilt die im Zuwendungsbescheid genannte Fassung, nicht
    automatisch die jüngste - deshalb liefert dieses Werkzeug alle Fassungen mit ihrem
    Stand, nicht nur eine Antwort. kuerzel z. B. "ANBest-P", "ANBest-GK", "ANBest-I".

    Die Treffer sind nach Regelwerk gruppiert: eine Suche nach "ANBest-P" findet auch
    "ANBest-P-Kosten", und das ist ein anderes Regelwerk mit eigener Fassungsreihe.

    Rückgabe: {"gesucht", "regelwerke": [{"regelwerk", "fassungen": [...älteste zuerst],
    "juengste"}, ...], "hinweis"}.
    """
    nadel = (kuerzel or "").lower().strip()
    if not nadel:
        raise ValueError("Bitte ein Kürzel angeben, z. B. \"ANBest-P\".")
    treffer = [d for d in BESTAND.docs.values() if nadel in (d["kuerzel"] or "").lower()]
    if not treffer:
        treffer = [d for d in BESTAND.docs.values() if nadel in (d["titel"] or "").lower()]
    if not treffer:
        raise ValueError(f"Kein Regelwerk zu '{kuerzel}' gefunden.")

    familien = {}
    for d in treffer:
        familien.setdefault(_familie(d["titel"]), []).append(d)

    regelwerke = []
    for name, docs in sorted(familien.items(), key=lambda kv: -len(kv[1])):
        fassungen = sorted(docs, key=lambda d: (d["stand"] or "", d["titel"]))
        regelwerke.append({
            "regelwerk": name,
            "fassungen": [{"id": d["id"], "title": d["titel"], "stand": d["stand"],
                           "url": d["quelle"]} for d in fassungen],
            "juengste": fassungen[-1]["id"],
        })

    return {
        "gesucht": kuerzel,
        "regelwerke": regelwerke,
        "hinweis": "Maßgeblich ist die im Zuwendungsbescheid genannte Fassung, nicht "
                   "automatisch die jüngste. Die vollständige Ablösefolge steht in "
                   "get_register(\"versionsketten\"); dort sind auch Ablöseangaben "
                   "vermerkt, die dem Stand-Feld widersprachen und deshalb nicht "
                   "übernommen wurden.",
    }


@mcp.custom_route("/health", methods=["GET"])
async def health(_request):
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "ok", "dokumente": _STATS["dokumente"]})


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
    )
