# foerderrecht

Das **Zuwendungsrecht des Bundes** als Wissensdienst: 131 Dokumente aus dem
[Formularschrank des Bundes](https://foerderportal.bund.de/easy/easy_index.php?auswahl=easy_formularschrank)
— Richtlinien für Zuwendungsanträge, Allgemeine Nebenbestimmungen, Merkblätter,
Kalkulationshilfen — als Markdown mit Volltext und Metadaten, dazu ein MCP-Server, der sie
jedem KI-Agenten zugänglich macht.

Zum Mitnehmen und Selbst-Hosten. Der Dienst braucht kein Backend, keine API, keinen
Account: der Wissensbestand liegt als Dateien im Repo, der Server liest sie lokal.

## Wofür das gut ist

Fördermittel abzurechnen ist Detailarbeit an Regelwerken, die kaum jemand vollständig im
Kopf hat. *Darf ich diese Reisekosten abrechnen? Brauche ich für diese Beschaffung drei
Angebote? Gilt für meinen Bescheid die ANBest-P von 2019 oder von 2025?* Die Antworten
stehen in PDFs, die man erst finden, dann in der richtigen Fassung öffnen und dann an der
richtigen Stelle lesen muss.

Dieser Dienst legt diese Dokumente so ab, dass ein Agent sie direkt lesen und **mit
Fundstelle belegen** kann, statt aus dem Gedächtnis zu antworten.

Zwei Dinge entscheiden dabei über richtig und falsch, und beide sind im Dienst abgebildet:

- **Die Antragsart.** Auf Ausgabenbasis (AZA) gilt anderes als auf Kostenbasis (AZK), bei
  Aufträgen (AAA/AAK) noch einmal anderes. Dieselbe Frage hat je nach Antragsart eine
  andere Antwort. Deshalb ist die Antragsart der erste Schnitt durch den Bestand.
- **Die Fassung.** Für ein laufendes Vorhaben gilt die Fassung, die im *Zuwendungsbescheid*
  genannt ist — nicht die neueste. Die ANBest-P etwa liegt in sechs Fassungen von 2014 bis
  2025 vor. Das Register [Versionsketten](wissen/register/versionsketten.md) macht die
  Ablösefolge sichtbar, das Werkzeug `welche_fassung` beantwortet die Frage direkt.

## Aufbau

```
wissen/                       der Wissensbestand (erzeugt, aber eingecheckt)
  index.md                    Einstiege
  overview.md                 Aufbau und Navigationslogik für Agenten
  log.md                      Änderungshistorie
  dokumente/<antragsart>/     131 Dokumente, Volltext eingebettet
  gesetze/                    19 Rechtsgrundlagen als Verweisseiten
  register/
    nach-kategorie/           je Antragsart (AZA, AZK, AAA, AAK, AZV, ...)
    nach-ministerium/         je Ressort (BMWK, BMUV, BMEL, ...)
    nach-gesetz/              welche Dokumente sich auf welches Gesetz stützen
    versionsketten.md         welche Fassung welche ablöst
mcp_server/                   MCP-Server über wissen/ (FastMCP, streamable HTTP)
scripts/build_bundle.py       erzeugt wissen/ aus einem Knowledge-Graph-Export
```

Jedes Dokument verweist unter *Einordnung* auf seine Register, die Register verweisen
zurück. Der Bestand ist damit als Graph navigierbar, nicht nur als Liste.

## Loslegen

```sh
# Bestand durchsuchen, ohne irgendetwas zu installieren
python3 mcp_server/bundle.py Reisekosten

# MCP-Server starten
pip install -r mcp_server/requirements.txt
python mcp_server/server.py          # http://localhost:8000/mcp

# oder als Container, aus diesem Ordner heraus gebaut
docker build -f mcp_server/Dockerfile -t foerderrecht-mcp .
docker run -p 8000:8000 foerderrecht-mcp
```

Einbindung in einen Client und Deployment-Hinweise: [mcp_server/README.md](mcp_server/README.md).

## Werkzeuge des MCP-Servers

| Werkzeug | Wofür |
| --- | --- |
| `search` | Suche mit Filtern für Antragsart, Ressort, Dokumentart, Kürzel, Gesetz |
| `fetch` | Volltext eines Dokuments per id |
| `welche_fassung` | alle Fassungen eines Regelwerks mit Stand — nach Regelwerk gruppiert |
| `list_documents` | Metadaten-Liste rein über Facetten, ohne Suchbegriff |
| `get_register` | ein Register als Markdown |
| `get_overview` | die Navigationslogik, damit ein Client die Register nutzt statt zu raten |

`search` und `fetch` haben bewusst die Signatur, die OpenAIs MCP-Connectors für Deep
Research erwarten — damit funktioniert der Dienst dort ohne Zusatzarbeit.

## Bestand aktualisieren

`wissen/` wird aus einem Knowledge-Graph-Export erzeugt:

```sh
python scripts/build_bundle.py --graph pfad/zu/knowledge_graph.json
```

Das Skript setzt den Volltext aus den Text-Chunks in Originalreihenfolge zusammen,
gliedert ihn über das `headings`-Feld in Abschnitte, leitet Register und Versionsketten
aus den Kanten ab und schreibt `log.md` fort.

## Herkunft, Lizenz, Grenzen

**Quelle** ist der Formularschrank des Bundes auf `foerderportal.bund.de`. Die Dokumente
sind amtliche Werke im Sinne von § 5 UrhG und damit gemeinfrei. Die MIT-Lizenz dieses
Ordners deckt den **Code** (Build-Skript und MCP-Server), nicht die amtlichen Inhalte —
für die gilt ihr eigener Status. Rechtsgrundlagen sind nicht mitkopiert, sondern als
Verweisseiten auf `gesetze-im-internet.de` beziehungsweise EUR-Lex hinterlegt.

**Maßgeblich ist immer das Original-PDF**, das jedes Dokument unter *Quelle* verlinkt.
Der eingebettete Text ist eine maschinelle Umsetzung.

Bekannte Grenzen des Bestands, damit niemand darüber stolpert:

- **10 Dokumente haben keinen Text.** Reine Formular- und Tabellen-PDFs — Verwendungs­
  nachweise, Berichtsblätter — aus denen sich kein Fließtext extrahieren lässt. Sie sind
  mit Metadaten und Link enthalten und weisen im Volltext-Abschnitt darauf hin.
- **Tabellen und Formularfelder sind verkürzt.** Wo es auf die genaue Tabellenstruktur
  ankommt, führt am Original-PDF nichts vorbei.
- **Einzelne Metadaten widersprechen dem Titel.** Zwei Dokumente tragen „April 2025“ im
  Titel bei Stand 2019-06; zwei weitere sind laut Titel Kostenbasis, stehen aber unter der
  Antragsart AZA (Ausgabenbasis) — Fehler in den Metadaten der Quelle. Weil die Antragsart
  hier die wichtigste Navigationsachse ist, lohnt bei Grenzfällen der Blick in den Titel und
  ins PDF. Im Zweifel gilt, was im PDF steht.
- **Zwei Ablöseangaben wurden verworfen.** Die Ablösefolge stammt aus einer Heuristik über
  die Dokumentnummern; wo sie dem Stand-Feld widersprach (etwa „Fassung 2014 löst Fassung
  2025 ab“), ist sie nicht übernommen. Beide Fälle sind unter *Nicht übernommene
  Ablöseangaben* in den [Versionsketten](wissen/register/versionsketten.md) dokumentiert.
- **In den Formularen abgedruckte E-Mail-Adressen sind ersetzt.** Aktuelle Ansprechpartner
  stehen im verlinkten Original-PDF.

Dieser Dienst gibt amtliche Dokumente wieder. Er ist **keine Rechtsberatung**.
