"""server.py - MCP server over the gdv-stellungnahmen OKF bundle.

Exposes the bundle to any MCP client (ChatGPT, Claude, Cursor, ...) over
streamable HTTP. Tools:

  search / fetch     the two tools OpenAI's MCP connectors expect (deep research),
                     in their exact I/O shape, so ChatGPT works out of the box.
  get_overview       returns the bundle's navigation logic (U1-U4) so a client
                     learns how to use the registers instead of guessing.
  list_documents     metadata listing with facet filters.
  get_register       a Thema / Gesetz / Fachbereich register, or "rote-linien".

Retrieval today is lexical (see bundle.Bundle.search - the swappable seam). Swap
that for local embeddings or Azure AI Search later without touching these tools.

Auth is intentionally NOT in this code. Configure it at deploy time via FastMCP's
environment variables (see mcp_server/README.md). With no auth env set the server
runs open - fine for local dev and an Azure smoke test, NOT for a public ChatGPT
connector (ChatGPT requires OAuth 2.1 + PKCE; wire an IdP per the README).
"""
import os
from typing import Optional

from fastmcp import FastMCP

from bundle import load_bundle

BUNDLE = load_bundle()
_STATS = BUNDLE.stats()

INSTRUCTIONS = f"""
Dieser Server stellt die öffentlichen Positionspapiere und Stellungnahmen des GDV
(Gesamtverband der Deutschen Versicherer) bereit: {_STATS['documents']} Dokumente,
Volltext eingebettet, mit Metadaten (Datum, Themen, Gesetzesbezug, Dokumenttyp).
Quelle und maßgeblich ist immer das Original-PDF (Feld url).

So beantwortest du typische Fragen:
- Aktuelle Position zu Thema X: search(query=X) oder list_documents(thema=X); das
  neueste Dokument (oberstes) gibt den aktuellen Stand, dann fetch(id) für Details.
- Frühere Positionen zu einem Gesetz/Vorhaben und deren Entwicklung: nutze den
  gesetz-Filter (z. B. "Solvency II", "KI-Verordnung") und ordne nach Datum, um
  Veränderungen über die Zeit zu erkennen.
- Rote Linien / nicht verhandelbare Positionen: get_register("rote-linien") plus
  Volltextsuche nach Formulierungen wie "unverzichtbar", "lehnt ab", "zwingend".
- Fachbereichsübergreifende Sicht: list_documents(thema=...) bzw. der
  fachbereich-Filter zeigt, wer zu einem Thema positioniert ist.

Rufe get_overview() auf, wenn du die Navigationslogik brauchst. Zitiere Aussagen
immer mit der Dokument-url (Original-PDF).
""".strip()

mcp = FastMCP(name="gdv-stellungnahmen", instructions=INSTRUCTIONS)


def _result(d):
    return {"id": d["id"], "title": d["title"], "url": d["url"]}


@mcp.tool
def search(
    query: str,
    thema: Optional[str] = None,
    gesetz: Optional[str] = None,
    fachbereich: Optional[str] = None,
    jahr: Optional[str] = None,
    dokumenttyp: Optional[str] = None,
    sprache: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Suche in den GDV-Stellungnahmen und Positionspapieren.

    Liefert die relevantesten Dokumente (bei gleicher Relevanz das neueste zuerst).
    Optionale Filter grenzen ein: thema (z. B. "Rente & Vorsorge"), gesetz
    (z. B. "Solvency II"), fachbereich, jahr (z. B. "2025"), dokumenttyp
    ("Stellungnahme"/"Positionspapier"), sprache ("de"/"en").

    Rückgabe: {"results": [{"id", "title", "url"}, ...]}. Nutze fetch(id) für den
    Volltext eines Treffers.
    """
    flt = {"thema": thema, "gesetz": gesetz, "fachbereich": fachbereich,
           "jahr": jahr, "dokumenttyp": dokumenttyp, "sprache": sprache}
    flt = {k: v for k, v in flt.items() if v}
    hits = BUNDLE.search(query, flt=flt or None, limit=max(1, min(limit, 50)))
    return {"results": [_result(d) for d in hits]}


@mcp.tool
def fetch(id: str) -> dict:
    """Hole den Volltext eines Dokuments per id (aus einem search-Treffer).

    Rückgabe: {"id", "title", "text", "url", "metadata"}. `text` ist der aus dem
    Original-PDF konvertierte Volltext; `url` verweist auf das maßgebliche PDF.
    """
    d = BUNDLE.get(id)
    if not d:
        raise ValueError(f"Unbekannte id: {id}")
    return {
        "id": d["id"],
        "title": d["title"],
        "text": d["body"],
        "url": d["url"],
        "metadata": {
            "datum": d["datum"],
            "dokumenttyp": d["dokumenttyp"],
            "themen": d["themen"],
            "gesetzesbezug": d["gesetzesbezug"],
            "fachbereiche_entwurf": d["fachbereiche"],
            "sprache": d["sprache"],
        },
    }


@mcp.tool
def get_overview() -> str:
    """Gib die Navigationslogik des Bündels zurück (Wurzel-index.md + overview.md).

    Erklärt Aufbau und Register und wie man die Nutzerfragen U1-U4 beantwortet.
    """
    return BUNDLE.overview()


@mcp.tool
def list_documents(
    thema: Optional[str] = None,
    gesetz: Optional[str] = None,
    fachbereich: Optional[str] = None,
    jahr: Optional[str] = None,
    dokumenttyp: Optional[str] = None,
    sprache: Optional[str] = None,
    limit: int = 25,
) -> list:
    """Liste Dokumente (Metadaten, neueste zuerst) mit optionalen Facetten-Filtern.

    Ohne query, rein über Filter (thema, gesetz, fachbereich, jahr, dokumenttyp,
    sprache). Gut für "alle Positionen zu Thema X" oder "was gab es 2025 zu Y".
    """
    flt = {"thema": thema, "gesetz": gesetz, "fachbereich": fachbereich,
           "jahr": jahr, "dokumenttyp": dokumenttyp, "sprache": sprache}
    flt = {k: v for k, v in flt.items() if v}
    hits = BUNDLE.search("", flt=flt or None, limit=max(1, min(limit, 200)))
    return [{
        "id": d["id"], "title": d["title"], "datum": d["datum"],
        "dokumenttyp": d["dokumenttyp"], "themen": d["themen"],
        "gesetzesbezug": d["gesetzesbezug"], "sprache": d["sprache"], "url": d["url"],
    } for d in hits]


@mcp.tool
def get_register(name: str) -> str:
    """Gib ein Register zurück. Namen z. B.:

    "nach-thema" (Übersicht) oder "nach-thema/regulierung" (ein Thema),
    "nach-gesetz" oder "nach-gesetz/solvency-ii", "nach-fachbereich" (Entwurf),
    "rote-linien" (U3). Register verlinken auf die zugehörigen Dokument-ids.
    """
    txt = BUNDLE.register(name)
    if txt is None:
        raise ValueError(f"Unbekanntes Register: {name}")
    return txt


@mcp.custom_route("/health", methods=["GET"])
async def health(_request):
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "ok", "documents": _STATS["documents"]})


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
    )
