# MCP-Server für das GDV-Stellungnahmen-Bündel

Ein schlanker [FastMCP](https://github.com/jlowin/fastmcp)-Server, der das OKF-Bündel `bundles/gdv-stellungnahmen` für MCP-Clients (ChatGPT, Claude, Cursor …) über **Streamable HTTP** bereitstellt. Er ist die austauschbare **Bedienschicht** über dem Bündel; das Bündel bleibt der Single Point of Truth, der Server ist nur ein Adapter.

## Tools

| Tool | Zweck |
| --- | --- |
| `search(query, thema?, gesetz?, fachbereich?, jahr?, dokumenttyp?, sprache?, limit?)` | Suche; Rückgabe `{"results": [{id, title, url}]}`. Form entspricht dem OpenAI-MCP-Connector-Vertrag. |
| `fetch(id)` | Volltext + Metadaten eines Dokuments: `{id, title, text, url, metadata}`. |
| `get_overview()` | Navigationslogik des Bündels (U1–U4), aus `index.md` + `overview.md`. |
| `list_documents(...)` | Metadaten-Liste mit Facetten-Filtern, neueste zuerst. |
| `get_register(name)` | Ein Register, z. B. `nach-thema/regulierung`, `nach-gesetz/solvency-ii`, `rote-linien`. |

`search`/`fetch` decken den ChatGPT-Connector-Vertrag ab; die übrigen Tools geben reicheren, OKF-nativen Zugriff. Die U1–U4-Navigationslogik steckt zusätzlich in den Server-`instructions`, damit jeder Client sie ohne Zusatzaufwand kennt.

### Der `search`-Seam

Retrieval ist heute **lexikalisch** (`bundle.py`, `Bundle.search`) — keine externen Abhängigkeiten, kein API-Key, gut für deutsche Fachbegriffe und Gesetzesnamen. Zum Aufrüsten (lokale Embeddings, Azure AI Search) nur `Bundle.search`/`_score` ersetzen; die Tool-Signaturen bleiben gleich, Clients merken nichts.

## Lokal starten und testen

Braucht Python ≥ 3.10 (FastMCP-Anforderung).

```sh
python3 -m venv .venv && source .venv/bin/activate    # oder: uv venv
pip install -r mcp_server/requirements.txt
BUNDLE_DIR=bundles/gdv-stellungnahmen PORT=8000 python mcp_server/server.py
```

Server läuft dann auf `http://localhost:8000/mcp`, Healthcheck `http://localhost:8000/health`.
Schnelltest mit dem FastMCP-Client:

```python
import asyncio, json
from fastmcp import Client
async def main():
    async with Client("http://localhost:8000/mcp") as c:
        print([t.name for t in await c.list_tools()])
        r = await c.call_tool("search", {"query": "solvency ii", "limit": 3})
        print(json.dumps(r.structured_content, ensure_ascii=False, indent=2))
asyncio.run(main())
```

In **Claude Code** lokal einbinden:

```sh
claude mcp add gdv --transport http http://localhost:8000/mcp
```

## Docker

Das Bündel wird ins Image gebacken (immutable, mit dem Code versioniert). **Build-Kontext ist das Repo-Wurzelverzeichnis**, damit `bundles/` erreichbar ist:

```sh
docker build -f mcp_server/Dockerfile -t gdv-okf-mcp .
docker run -p 8000:8000 gdv-okf-mcp
curl localhost:8000/health     # {"status":"ok","documents":...}
```

Inhalt aktualisieren: `scripts/refresh.sh` → Image neu bauen → neu deployen. (Alternative: Bündel als Volume mounten und `BUNDLE_DIR` setzen, um Daten vom Image zu entkoppeln.)

## Deploy auf Azure Container Apps

```sh
# 1. Image in eine Azure Container Registry
az acr build --registry <ACR_NAME> --image gdv-okf-mcp:latest -f mcp_server/Dockerfile .

# 2. Container App anlegen (ingress extern, Port 8000)
az containerapp create \
  --name gdv-okf-mcp --resource-group <RG> --environment <ACA_ENV> \
  --image <ACR_NAME>.azurecr.io/gdv-okf-mcp:latest \
  --target-port 8000 --ingress external \
  --min-replicas 1 \
  --env-vars PORT=8000 BUNDLE_DIR=/app/bundle
```

Ergebnis: eine öffentliche HTTPS-URL `https://gdv-okf-mcp.<region>.azurecontainerapps.io`, MCP-Endpunkt `.../mcp`, Health `.../health`. Container Apps übernimmt TLS — wichtig, weil ChatGPT eine HTTPS-URL verlangt.

## Mit ChatGPT verbinden (OAuth 2.1 — Pflicht)

**ChatGPT akzeptiert keine Bearer-Token-MCP-Server; OAuth 2.1 + PKCE ist zwingend** (bestätigt in GBrains `docs/mcp/CHATGPT.md`). Der Server bringt bewusst **keinen eigenen OAuth-Server** mit — die sicherheitskritische Autorisierung wird an einen Identity Provider ausgelagert (Microsoft Entra ID), FastMCP übernimmt die MCP-seitige OAuth-Vermittlung. So musst du keinen Authorization Server selbst bauen.

Auth wird über **Umgebungsvariablen** aktiviert (kein Code-Change nötig). FastMCP liest `FASTMCP_SERVER_AUTH` und den provider-spezifischen Block. Grundmuster mit Entra ID:

```sh
# an der Container App setzen (Werte aus deiner Entra-App-Registrierung):
FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.azure.AzureProvider
FASTMCP_SERVER_AUTH_AZURE_CLIENT_ID=<app-client-id>
FASTMCP_SERVER_AUTH_AZURE_CLIENT_SECRET=<app-client-secret>
FASTMCP_SERVER_AUTH_AZURE_TENANT_ID=<tenant-id>
FASTMCP_SERVER_AUTH_AZURE_BASE_URL=https://gdv-okf-mcp.<region>.azurecontainerapps.io
```

Ablauf (analog zu GBrains ChatGPT-Setup, aber mit Entra als AS):

1. **Entra-App registrieren** (Azure Portal › App registrations): Web-Plattform, Redirect-URI von ChatGPT eintragen (aus dem ChatGPT-Connector-Screen, Form `https://chatgpt.com/connector_platform_oauth_redirect` o. ä.). Client-Secret erzeugen.
2. Obige Env-Variablen an der Container App setzen, App neu starten. FastMCP veröffentlicht dann die Discovery unter `/.well-known/oauth-authorization-server` (bzw. `/.well-known/oauth-protected-resource`), die ChatGPT automatisch findet.
3. **In ChatGPT** (Settings › Connectors › Add): MCP-URL `https://…/mcp`, den OAuth-Handshake bestätigen. Danach ist der Connector aktiv und ChatGPT kann `search`/`fetch` aufrufen.

> Version prüfen: Die exakten `FASTMCP_SERVER_AUTH_*`-Variablennamen und der Azure-Provider-Pfad hängen von der installierten FastMCP-Version ab (hier validiert: 3.4.x). Vor dem Livegang gegen die FastMCP-Auth-Doku deiner Version abgleichen. Der ChatGPT↔OAuth-Handshake muss einmal live getestet werden (öffentliche URL + ChatGPT-Konto); Code und Deployment sind dafür vorbereitet, der Roundtrip selbst ließ sich hier nicht ausführen.

Alternativen zu Entra: FastMCPs `OAuthProxy` überbrückt IdPs ohne Dynamic Client Registration (GitHub, Google, Auth0, WorkOS) zu MCP-Clients, die DCR erwarten (ChatGPT/Claude). Für einen schnellen Test taugt jeder dieser Provider; für GDV-intern ist Entra ID die naheliegende Wahl (Zugriffssteuerung, SSO).

## Mit Claude verbinden

Claude unterstützt zusätzlich Bearer-Token und stdio, ist also anspruchsloser. Remote:

```sh
claude mcp add gdv --transport http https://gdv-okf-mcp.<region>.azurecontainerapps.io/mcp
```

## Sicherheitshinweise

- Ohne gesetzte Auth-Env läuft der Server **offen** — nur für lokale Entwicklung / Azure-Smoke-Test, nie öffentlich ohne Auth.
- Alle Tools sind read-only (keine Schreibpfade), der Inhalt ist ohnehin öffentlich (gdv.de). Bei künftigen internen Bündeln: Auth erzwingen und den Zugriff über Entra-Gruppen einschränken.
