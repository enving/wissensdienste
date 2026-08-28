# Anleitung: MCP-Server auf Azure deployen und mit ChatGPT verbinden

Kurz-Runbook für den Deploy. Details stehen in [`mcp_server/README.md`](mcp_server/README.md). Der Server stellt das GDV-Stellungnahmen-Bündel als MCP-Connector bereit (Tools `search`/`fetch` u. a.); das Bündel ist im Image enthalten.

## Voraussetzungen

- Azure-Subscription + eine Resource Group.
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) (`az login`).
- Dieses Repo lokal ausgecheckt.
- Kein lokales Docker nötig (wir bauen in der Azure Container Registry).

```sh
az login
RG=rg-okf                # Resource Group (anlegen: az group create -n $RG -l westeurope)
ACR=acrokf$RANDOM        # global eindeutiger Registry-Name (nur Kleinbuchstaben/Zahlen)
LOC=westeurope
```

## 1. Image bauen (in der Cloud, ohne lokales Docker)

```sh
az group create -n $RG -l $LOC
az acr create -n $ACR -g $RG --sku Basic --admin-enabled true
# baut das Image aus dem Repo-Root in der Registry (Dockerfile liegt in mcp_server/):
az acr build --registry $ACR --image gdv-okf-mcp:latest -f mcp_server/Dockerfile .
```

> Alternative über GitHub: In diesem Repo einen GitHub-Actions-Workflow ergänzen, der bei Push das Image baut und nach GHCR/ACR pusht. Für den Start ist `az acr build` einfacher (kein CI-Setup, keine Secrets).

## 2. Container App anlegen

```sh
az containerapp env create -n aca-okf -g $RG -l $LOC
az containerapp create \
  --name gdv-okf-mcp -g $RG --environment aca-okf \
  --image $ACR.azurecr.io/gdv-okf-mcp:latest \
  --registry-server $ACR.azurecr.io \
  --target-port 8000 --ingress external \
  --min-replicas 1 --max-replicas 2 \
  --env-vars PORT=8000 BUNDLE_DIR=/app/bundle

az containerapp show -n gdv-okf-mcp -g $RG --query properties.configuration.ingress.fqdn -o tsv
```

Die ausgegebene URL ist dein Server. Test:

```sh
curl https://<FQDN>/health          # {"status":"ok","documents":...}
# MCP-Endpunkt: https://<FQDN>/mcp
```

An dieser Stelle läuft der Server **ohne Auth** (ok zum Testen mit Claude, NICHT für ChatGPT/öffentlich).

## 3. OAuth für ChatGPT aktivieren (Pflicht)

ChatGPT verlangt OAuth 2.1 + PKCE. Wir lagern die Autorisierung an **Microsoft Entra ID** aus (kein eigener Auth-Server nötig).

1. **Entra-App registrieren** (Azure Portal › Microsoft Entra ID › App registrations › New):
   - Redirect-URI (Typ Web): die von ChatGPT im Connector-Dialog angezeigte URI (Form `https://chatgpt.com/connector_platform_oauth_redirect`).
   - Unter *Certificates & secrets* ein Client-Secret erzeugen.
   - Client-ID, Secret, Tenant-ID notieren.
2. **Env-Variablen an der Container App setzen** und neu starten:

   ```sh
   az containerapp update -n gdv-okf-mcp -g $RG --set-env-vars \
     FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.azure.AzureProvider \
     FASTMCP_SERVER_AUTH_AZURE_CLIENT_ID=<client-id> \
     FASTMCP_SERVER_AUTH_AZURE_CLIENT_SECRET=<secret> \
     FASTMCP_SERVER_AUTH_AZURE_TENANT_ID=<tenant-id> \
     FASTMCP_SERVER_AUTH_AZURE_BASE_URL=https://<FQDN>
   ```

   > Die exakten Variablennamen können je FastMCP-Version leicht abweichen; im Zweifel die FastMCP-Auth-Doku der installierten Version prüfen (siehe `mcp_server/requirements.txt`, hier 3.4.x).
3. **In ChatGPT verbinden** (Settings › Connectors › Add): MCP-URL `https://<FQDN>/mcp` eintragen, OAuth-Zustimmung durchklicken. Danach kann ChatGPT die GDV-Stellungnahmen durchsuchen.

Für **Claude** genügt ohne Weiteres: `claude mcp add gdv --transport http https://<FQDN>/mcp`.

## 4. Inhalte aktualisieren

Neue Stellungnahmen einpflegen und neu ausrollen:

```sh
./scripts/refresh.sh                                   # scrape + convert + build + validate
az acr build --registry $ACR --image gdv-okf-mcp:latest -f mcp_server/Dockerfile .
az containerapp update -n gdv-okf-mcp -g $RG --image $ACR.azurecr.io/gdv-okf-mcp:latest
```

Das lässt sich später als Scheduled Job / GitHub Action automatisieren (siehe Haupt-`README.md`, Abschnitt „Empfehlungen zur produktiven Umsetzung").

## Kosten grob

Container Apps skaliert bei Last; mit `--min-replicas 1` läuft dauerhaft eine kleine Instanz (grob niedrige zweistellige €/Monat), ACR Basic ~5 €/Monat. Wenn ihr später semantische Suche über Azure AI Search ergänzt, kommt dessen Tier dazu (siehe Haupt-README).
