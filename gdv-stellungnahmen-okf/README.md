# GDV-Stellungnahmen als OKF-Bündel

Dieses Repository macht die öffentlichen **Positionspapiere und Stellungnahmen des GDV** für KI-Agenten direkt lesbar. Die Dokumente werden von [gdv.de/gdv/positionen](https://www.gdv.de/gdv/positionen) geladen, nach Markdown konvertiert und als [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog)-Bündel (OKF v0.1) abgelegt: je Dokument ein Konzept mit strukturierten Metadaten und eingebettetem Volltext. Vorbild ist das Beispiel-Repo `okf-bundles-example` (insbesondere das Korpus-Muster von `bgh-rechtsprechung`).

Single Point of Truth bleibt die GDV-Website. Maßgeblich ist immer das **Original-PDF**, das in jedem Konzept unter „Quelle" verlinkt ist; der eingebettete Text ist eine Konvenienz für die Suche.

## Was wurde gebaut

Eine dreistufige, wiederholbare Pipeline (reines System-Python, keine Fremdbibliotheken, keine Node-Abhängigkeit) plus das erzeugte Bündel.

```
scripts/
  scrape_gdv.py        1) Katalog von gdv.de/gdv/positionen scrapen (DE + EN)
  convert_docling.py   2) PDFs laden + via docling zu Markdown
  build_bundle.py      3) OKF-Bündel aus Katalog + Markdown erzeugen
  okf_validate.py      OKF-Konformitätsprüfer (Python-Port des Skill-Validators)
  okf-validate.mjs     vendored Node-Original (Parität, falls Node vorhanden)
GDV_Stellungnahmen/    Rohdaten-Arbeitsbereich (git-ignoriert)
  catalog.json         gescrapter Katalog (Metadaten aller Dokumente)
  pdf/  md/             heruntergeladene PDFs und konvertierte Markdown-Cache
bundles/gdv-stellungnahmen/   das fertige OKF-Bündel (siehe unten)
CLAUDE.md              Repo-Konventionen für Agenten (Overlay über den /okf-Skill)
.claude/ .agents/      der /okf-Skill (aus dem Beispiel-Repo übernommen)
```

### 1. Scraper (`scrape_gdv.py`)

Die Seite rendert eine Facettensuche mit „Mehr laden". Deren Button ruft ein paginiertes Fragment `/service/more/gdv/<node>?c=<kategorie>&pageNum=<N>` auf (aus dem JS-Bundle der Seite rekonstruiert). Der Scraper iteriert die Seiten, parst je Treffer Titel, Datum, Dokumenttyp (Stellungnahme/Positionspapier), Themen-Tags, PDF-URL und erkennt die Sprache. Ergebnis: `catalog.json`. Aktueller Stand: **348 Dokumente** (Zeitraum 2017 bis 2026), davon der Großteil deutsch, rund zwei Dutzend englisch.

### 2. Konvertierung (`convert_docling.py`)

Jedes PDF wird auf dem Host geladen (der docling-Container hat keinen ausgehenden Internetzugang) und an den lokal laufenden **docling-serve** (Colima, `http://localhost:5001/v1/convert/file`) geschickt. Bilder werden weggelassen (Platzhalter entfernt). Der Cache in `md/` macht den Lauf idempotent und inkrementell: bereits konvertierte Dokumente werden übersprungen, ein erneuter Lauf verarbeitet nur Neues. Fehlschläge landen in `convert_failures.json` für einen gezielten Wiederholungslauf.

Betriebshinweis: der docling-Container hat nur einen Modell-Worker, deshalb läuft die Konvertierung **sequenziell** (parallele Uploads bringen ihn per OOM zum Absturz), mit Wiederholungen (der Container startet automatisch neu). Die **Tabellenstruktur-Erkennung ist an** (`do_table_structure=true`, `table_mode=accurate`), damit Tabellen als Markdown-Tabellen erhalten bleiben. Das ist der Speicher-intensive Teil und braucht eine großzügige VM (die Colima-VM läuft hier mit 8 GB; Spitze rund 3,6 GB pro Dokument). Auf einer kleinen VM (rund 3,8 GB) stürzt der Container daran ab; dann per `TABLES=off python3 scripts/convert_docling.py` die Erkennung abschalten. Tabellen werden dann als Text linearisiert, was für die inhaltliche Suche ausreicht.

### 3. Bündelbau (`build_bundle.py`)

Erzeugt das komplette Bündel aus `catalog.json` und dem Markdown-Cache. Je Dokument ein Konzept mit Volltext; zusätzlich vier Register und ein Jahresbaum. Ableitungen:

- **Fachbereich (Entwurf):** aus den Themen der Website abgeleitet (Mapping `TOPIC_TO_FB` im Skript). Übergreifende Tags wie „Regulierung"/„Politik" bestimmen keinen Fachbereich allein; Dokumente ohne fachlichen Themenbezug landen unter „Recht und Regulierung (übergreifend)". Explizit als Entwurf markiert, von den Fachbereichen zu prüfen.
- **Gesetzes-/Vorhabensbezug:** erkannt aus Titel und Volltext gegen eine erweiterbare Liste bekannter Gesetze und EU-Vorhaben (Solvency II, VAG, KI-Verordnung, DORA, FiDA, CSRD/ESRS, Lieferkettengesetz/CSDDD, digitaler Euro, Jahressteuergesetz, Bürokratieabbau/Omnibus u. a.).

## Aufbau des Bündels

```
bundles/gdv-stellungnahmen/
  index.md                          Wurzel (okf_version), Einstiege
  overview.md                       Orientierung + wie U1-U4 beantwortet werden
  log.md                            Änderungshistorie
  stellungnahmen/<jahr>/<slug>.md   je Dokument ein Konzept, Volltext eingebettet
  register/
    nach-thema/<thema>.md           Themenregister (U1, U4)
    nach-gesetz/<gesetz>.md         Gesetzes-/Vorhabensregister (U2)
    nach-fachbereich/<fb>.md        Fachbereichs-Zuordnung, Entwurf (U4)
    rote-linien.md                  kuratierte rote Linien, Ausbaustufe (U3)
```

Jedes Dokument verweist im Abschnitt „Einordnung" auf seine Themen-, Fachbereichs- und Gesetzes-Register; die Register verweisen zurück. Das Bündel ist damit ein navigierbarer **Graph**, nicht nur eine Liste. Ein Agent startet bei `index.md` und steigt nur in die Zweige ab, die die Frage braucht.

## Wie ein Agent die User Stories beantwortet

| Story | Weg durchs Bündel |
| --- | --- |
| **U1** Aktuelle Position zu Thema X | [Themenregister](bundles/gdv-stellungnahmen/register/nach-thema/index.md) → Thema wählen → oberstes (neuestes) Dokument = aktueller Stand; Volltext liefert die Begründung. |
| **U2** Frühere Positionen zu einem geplanten Gesetz, Entwicklung über die Zeit | [Gesetzesregister](bundles/gdv-stellungnahmen/register/nach-gesetz/index.md) → Vorhaben wählen → chronologische Liste zeigt, ob und wie sich die Position verändert hat. |
| **U3** Rote Linien (z. B. unverzichtbare Statistiken) | [Rote Linien](bundles/gdv-stellungnahmen/register/rote-linien.md) plus Volltextsuche über alle Dokumente nach Formulierungen wie *unverzichtbar*, *zwingend*, *lehnt ab*, *Statistik*. |
| **U4** Fachbereichsübergreifende Themen | [Themenregister](bundles/gdv-stellungnahmen/register/nach-thema/index.md) und [Fachbereichsregister](bundles/gdv-stellungnahmen/register/nach-fachbereich/index.md) zeigen, welche Bereiche zu einem Thema positioniert sind. |

## Aktualisieren

Die GDV-Website ist der Single Point of Truth.

### Automatisch (wöchentlicher Cron-Job)

`scripts/weekly_check.sh` läuft jeden Montag um 08:30 Uhr (macOS-Crontab):

```
30 8 * * 1  bash .../scripts/weekly_check.sh >> .../logs/weekly_check.log 2>&1
```

Ablauf:
1. Aktuellen Katalog auf der GDV-Website scrapen (kein docling nötig).
2. Blob-IDs mit dem bisherigen Katalog vergleichen.
3. Keine neuen Dokumente: stilles Exit.
4. Neue Dokumente gefunden: macOS-Benachrichtigung + vollständige Pipeline (wenn docling-serve läuft) oder Hinweis zum manuellen Start (wenn Colima nicht läuft).

Log: `logs/weekly_check.log` im Repo-Verzeichnis.

Manueller Testlauf:

```sh
bash scripts/weekly_check.sh
```

### Manuell (einzelne Schritte)

```sh
# docling-serve muss laufen (Colima): docker ps | grep docling-serve
python3 scripts/scrape_gdv.py                 # Katalog neu ziehen
python3 scripts/convert_docling.py            # nur neue PDFs konvertieren (Cache!)
python3 scripts/build_bundle.py               # Bündel neu erzeugen
python3 scripts/okf_validate.py bundles/gdv-stellungnahmen --corpus   # prüfen
```

Wiederholungslauf nur für fehlgeschlagene Konvertierungen:

```sh
python3 scripts/convert_docling.py $(python3 -c "import json;print(' '.join(x['blob_id'] for x in json.load(open('GDV_Stellungnahmen/convert_failures.json'))))")
```

## Empfehlungen zur produktiven Umsetzung

1. **Scheduler / Cron für inkrementelle Aktualisierung.** Umgesetzt: `scripts/weekly_check.sh` läuft per macOS-Crontab jeden Montag 08:30 Uhr. Es scraped den Katalog, vergleicht Blob-IDs, und startet die vollständige Pipeline nur bei Fund (macOS-Benachrichtigung). Log: `logs/weekly_check.log`. Für die KI-Plattform bietet sich statt Host-Cron ein Container-/Kubernetes-CronJob oder eine Scheduled Pipeline (z. B. GitLab CI schedule) an, der docling-serve als Service mitzieht.

2. **Änderungserkennung.** Der Katalog trägt je Dokument die `blob_id`. Neue Dokumente haben neue IDs, sodass der Scheduler zuverlässig nur Neues konvertiert. Für inhaltliche Aktualisierungen desselben Dokuments vergibt GDV in der Regel eine neue Blob-URL; optional lässt sich ein Hash des PDFs mitführen, um stille Neufassungen zu erkennen.

3. **docling-Betrieb.** Läuft aktuell mit 8-GB-Colima-VM und aktiver Tabellenerkennung. Für mehr Tempo docling-serve mit mehreren Modell-Workern und Speicherlimit betreiben und die Konvertierung parallelisieren (`WORKERS` in `convert_docling.py`); auf knappem RAM `TABLES=off` setzen. In der KI-Plattform docling-serve als eigenständigen Service mit definierten Ressourcen einplanen.

4. **Ausbau mit den Fachbereichen.** Zwei Stellen sind bewusst als Entwurf angelegt und sollten mit den Fachbereichen geschärft werden:
   - Das **Fachbereichs-Mapping** (`TOPIC_TO_FB` in `build_bundle.py`) ist automatisch aus den groben Website-Themen abgeleitet. Die Fachbereiche sollten die Zuordnung bestätigen bzw. korrigieren; danach ist U4 belastbar.
   - Die **roten Linien** (`register/rote-linien.md`) sind ein kuratierter Platzhalter für U3. Je rote Linie ein Stichpunkt mit Beleg-Link auf die stützende(n) Stellungnahme(n). Sinnvoll wäre je Fachbereich eine kurze Liste („unverzichtbare Statistiken", „nicht verhandelbare Positionen").

   Für die inhaltliche Tiefe (feineres Tagging, weitere Register wie Rechtsgebiet oder Adressat des Vorhabens) lohnt eine kurze Abstimmung mit den Fachbereichen über die gewünschten Facetten.

5. **Qualitätssicherung.** Der Validator (`okf_validate.py`) gehört in den Scheduler als Gate (0 Fehler). Zusätzlich sinnvoll: Stichproben-Vergleich Volltext gegen PDF und eine Kennzahl über `convert_failures.json` (Konvertierungsquote).

## Validierung

```sh
python3 scripts/okf_validate.py bundles/gdv-stellungnahmen --corpus
```

Der Prüfer erzwingt die harte OKF-Regel (jedes Konzept hat ein nicht-leeres `type`) und warnt bei weichen Punkten (fehlende Linkziele, Konzept-zu-Index-Links). `--corpus` unterdrückt die Orphan-Warnung, weil die Dokumente zusätzlich über den Jahresbaum erreichbar sind.

## Grenzen

- **Konvertierungsqualität:** Tabellen sind linearisiert (siehe oben), Bilder fehlen. Für Zitate immer das Original-PDF heranziehen.
- **Fachbereich und rote Linien** sind Entwürfe (siehe Empfehlung 4).
- **Sprachgemisch:** DE und EN liegen gemischt im selben Register; die Sprache steht je Konzept im Feld `sprache`.
- **Vollständigkeit** richtet sich nach dem, was die Website unter „Positionen und Stellungnahmen" listet; ältere, nicht mehr gelistete Dokumente sind nicht enthalten.

## Lizenz

Werkzeuge und Struktur unter MIT (siehe `LICENSE`). Die Inhalte der Stellungnahmen sind Werke des GDV; maßgeblich bleibt das jeweilige Original auf gdv.de.
