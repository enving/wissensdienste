# wissensdienste

Öffentliche Wissensdienste: Fachdokumente so aufbereiten, dass KI-Agenten sie direkt und belegbar beantworten können. Jeder Dienst liegt in einem eigenen Unterordner mit eigenem README; das gemeinsame Werkzeug ist der [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog) (OKF), umgesetzt als Markdown-Bündel plus MCP-Server. Der `/okf`-Skill unter `.claude/skills/okf/` gilt repo-weit für alle Dienste hier.

## Dienste

- [`gdv-stellungnahmen-okf/`](gdv-stellungnahmen-okf/) - öffentliche Positionspapiere und Stellungnahmen des GDV (Gesamtverband der Deutschen Versicherer) als OKF-Bündel plus MCP-Server. Referenzimplementierung der Pipeline: Scraper -> PDF-zu-Markdown-Konvertierung -> OKF-Bündelbau -> MCP-Server.

Weitere Dienste folgen als weitere Unterordner.
