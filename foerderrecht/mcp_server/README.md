# MCP-Server für den Wissensdienst `foerderrecht`

Ein schlanker [FastMCP](https://github.com/jlowin/fastmcp)-Server, der den Bestand unter
`wissen/` für MCP-Clients (Claude, ChatGPT, Cursor …) über **Streamable HTTP** bereitstellt.
Er ist die austauschbare **Bedienschicht** über dem Bestand; die Markdown-Dateien bleiben
der Single Point of Truth, der Server ist nur ein Adapter.

Kein Backend, kein API-Key, kein Account — der Server liest die Dateien lokal.

## Werkzeuge

| Werkzeug | Zweck |
| --- | --- |
| `search(query, kategorie?, ministerium?, art?, kuerzel?, gesetz?, limit?)` | Suche; Rückgabe `{"results": [{id, title, url}]}`. Form entspricht dem OpenAI-MCP-Connector-Vertrag. |
| `fetch(id)` | Volltext + Metadaten eines Dokuments: `{id, title, text, url, metadata}`. |
| `welche_fassung(kuerzel)` | Alle Fassungen eines Regelwerks mit Stand, **nach Regelwerk gruppiert**. |
| `list_documents(...)` | Metadaten-Liste rein über Facetten, jüngste Fassung zuerst. |
| `get_register(name)` | Ein Register, z. B. `nach-kategorie/azk-kostenbasis`, `nach-gesetz`, `versionsketten`. |
| `get_overview()` | Navigationslogik aus `index.md` + `overview.md`. |

`search`/`fetch` decken den ChatGPT-Connector-Vertrag ab, die übrigen Werkzeuge geben
reicheren Zugriff. Die Domänenlogik — Antragsart zuerst, Fassung prüfen, mit Fundstelle
belegen — steckt zusätzlich in den Server-`instructions`, damit jeder Client sie ohne
Zusatzaufwand kennt.

### Warum `welche_fassung` ein eigenes Werkzeug ist

Im Förderrecht ist die falsche Fassung eine falsche Antwort. Dasselbe Regelwerk liegt
mehrfach vor — die ANBest-P in sechs Fassungen von 2014 bis 2025 —, und für ein laufendes
Vorhaben gilt die im Zuwendungsbescheid genannte, nicht die neueste. Eine reine Suche würde
hier eine beliebige Fassung obenauf spülen. `welche_fassung` legt stattdessen alle offen
und gruppiert sie nach Regelwerk, denn das Kürzelfeld allein trennt nicht: ANBest-P und
ANBest-P-Kosten tragen beide „ANBest-P“, sind aber verschiedene Regelwerke.

### Die Naht bei `search`

Retrieval ist heute **lexikalisch** (`bundle.py`, `Wissensbestand.search`) — keine externen
Abhängigkeiten, kein API-Key, brauchbar für deutsche Fachbegriffe und Kürzel. Relevanz wird
dabei in Fünferstufen gebündelt, bevor der Stand entscheidet: die Fassungen eines Regelwerks
unterscheiden sich lexikalisch kaum (ANBest-P: 32/32/32/31 Punkte), ohne diese Stufung
gewänne der Zufall statt der jüngeren Fassung.

Zum Aufrüsten (lokale Embeddings, ein Suchindex) nur `Wissensbestand.search` und `_score`
ersetzen; die Werkzeug-Signaturen bleiben gleich, Clients merken nichts.

## Lokal starten

Braucht Python ≥ 3.10 (FastMCP-Anforderung).

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -r mcp_server/requirements.txt
PORT=8000 python mcp_server/server.py
```

Server läuft auf `http://localhost:8000/mcp`, Healthcheck `http://localhost:8000/health`.

Ohne den MCP-Stack lässt sich der Bestand auch direkt durchsuchen:

```sh
python3 mcp_server/bundle.py ANBest-P Reisekosten
```

Schnelltest mit dem FastMCP-Client:

```python
import asyncio, json
from fastmcp import Client
async def main():
    async with Client("http://localhost:8000/mcp") as c:
        print([t.name for t in await c.list_tools()])
        r = await c.call_tool("welche_fassung", {"kuerzel": "ANBest-P"})
        print(json.dumps(r.structured_content, ensure_ascii=False, indent=2))
asyncio.run(main())
```

In **Claude Code** einbinden:

```sh
claude mcp add foerderrecht --transport http http://localhost:8000/mcp
```

## Docker

Der Bestand wird ins Image gebacken (unveränderlich, mit dem Code versioniert).
**Build-Kontext ist der Dienst-Ordner**, damit `wissen/` erreichbar ist:

```sh
docker build -f mcp_server/Dockerfile -t foerderrecht-mcp .
docker run -p 8000:8000 foerderrecht-mcp
curl localhost:8000/health     # {"status":"ok","dokumente":131}
```

Für einen Bestand, der sich ohne Rebuild ändern soll, stattdessen als Volume mounten:

```sh
docker run -p 8000:8000 -v "$PWD/wissen:/app/wissen:ro" -e WISSEN_DIR=/app/wissen foerderrecht-mcp
```

## Konfiguration

| Variable | Default | Bedeutung |
| --- | --- | --- |
| `WISSEN_DIR` | `../wissen` relativ zu `server.py` | Wurzel des Wissensbestands |
| `PORT` | `8000` | HTTP-Port |

## Authentifizierung

Bewusst **nicht** im Code. Ohne gesetzte Auth-Variablen läuft der Server offen — in Ordnung
für lokalen Betrieb und einen Smoke-Test, **nicht** für einen öffentlich erreichbaren
Endpunkt. Wer ihn ins Netz stellt, konfiguriert Auth beim Deploy über die
Umgebungsvariablen von FastMCP; ein ChatGPT-Connector verlangt OAuth 2.1 mit PKCE und damit
einen angebundenen Identity Provider.

Der Bestand selbst ist gemeinfreies amtliches Material — der Schutzbedarf liegt beim
Endpunkt (Missbrauch, Last), nicht beim Inhalt.
