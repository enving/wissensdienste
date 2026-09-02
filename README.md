# wissensdienste

Öffentliche Wissensdienste: Fachdokumente so aufbereiten, dass KI-Agenten sie direkt und
belegbar beantworten können.

Jeder Dienst liegt in einem eigenen Unterordner mit eigenem README und folgt demselben
Muster — **Markdown-Bestand plus MCP-Server**:

- Der Bestand sind gewöhnliche Markdown-Dateien mit YAML-Frontmatter, eingecheckt und
  lesbar, je Dokument eine Datei mit Metadaten und Volltext. Kein Vektorindex, keine
  Datenbank, kein Binärformat.
- Register erschließen den Bestand über die Achsen, die in der jeweiligen Domäne zählen,
  und verlinken auf die Dokumente zurück. So ist er als Graph navigierbar, nicht nur als
  Liste.
- Darüber liegt ein MCP-Server, der die Dateien lokal liest. Kein Backend, kein API-Key,
  kein Account.

Zum Mitnehmen und Selbst-Hosten gedacht: Ordner klonen, Server starten, fertig. Wie ein
Bestand intern strukturiert ist, entscheidet der Dienst — `gdv-stellungnahmen-okf` folgt
dem [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog) (OKF)
und bringt dafür den repo-weiten `/okf`-Skill unter `.claude/skills/okf/` mit, andere
Dienste bleiben bei schlichtem Frontmatter.

## Dienste

- [`foerderrecht/`](foerderrecht/) — das Zuwendungsrecht des Bundes: 131 Dokumente aus dem
  Formularschrank (Richtlinien, Allgemeine Nebenbestimmungen, Merkblätter,
  Kalkulationshilfen) mit Volltext, 19 Rechtsgrundlagen als Verweisseiten, Register nach
  Antragsart, Ressort, Gesetz und Fassung. Beantwortet, welche Nebenbestimmungen für ein
  Vorhaben gelten und welche Fassung für einen Bescheid maßgeblich ist.

- [`gdv-stellungnahmen-okf/`](gdv-stellungnahmen-okf/) — öffentliche Positionspapiere und
  Stellungnahmen des GDV (Gesamtverband der Deutschen Versicherer) als OKF-Bündel plus
  MCP-Server. Referenzimplementierung der Pipeline: Scraper → PDF-zu-Markdown-Konvertierung
  → OKF-Bündelbau → MCP-Server.

Weitere Dienste folgen als weitere Unterordner.

## Lizenz

Der Code steht unter MIT (siehe [LICENSE](LICENSE) und die LICENSE-Datei je Dienst). Für die
aufbereiteten Inhalte gilt jeweils ihr eigener Status — die Herkunft und was daraus folgt,
steht im README des Dienstes.
