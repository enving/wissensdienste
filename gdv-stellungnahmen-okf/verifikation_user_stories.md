# Verifikation der lokalen Pipeline anhand der User Stories

Testdatum: 2026-07-09. Getestet gegen das OKF-Bündel `bundles/gdv-stellungnahmen` (348 Dokumente, Stand bis 2026-06-29), bereitgestellt über den lokalen MCP-Server (`mcp_server/server.py`, FastMCP 3.4.x, Streamable HTTP auf `localhost:8000/mcp`).

## Zweck und Aussagekraft

Dieses Dokument belegt, dass die vier Nutzerfragen (User Stories U1 bis U4) **allein aus der lokalen Pipeline** beantwortbar sind, also aus dem gescrapten und konvertierten GDV-Bestand, abgefragt über den MCP-Server. Es dient der inhaltlichen Bewertung der Antwortqualität und der Retrieval-Güte.

**Methodik (wichtig für die Beweiskraft):** Jede Frage wurde von einem **eigenen, kontextfreien KI-Agenten** beantwortet, der

- **keinen Zugriff auf unseren Chatverlauf oder auf den Ersteller der Pipeline** hatte (frisch gestartet, ohne Vorkontext),
- Informationen **ausschließlich über den MCP-Server** beziehen durfte (kein Vorwissen, keine Websuche, kein direkter Dateizugriff),
- **jeden MCP-Aufruf protokollieren** musste und jede Aussage mit Dokument-id und Quell-URL zu belegen hatte.

Das MCP-Transkript unter jeder Antwort ist der Prüfnachweis: Man sieht, welche Such-/Lese-Aufrufe der Agent gemacht hat und dass die Antwort daraus stammt, nicht aus Modellwissen. Die Agenten laufen auf einem Claude-Modell; entscheidend ist, dass sie ohne unseren Kontext arbeiten und nur über den MCP-Server an Inhalte kommen.

Die Retrieval-Schicht des Servers ist derzeit **lexikalisch** (Stichwort-/Feldsuche, keine Embeddings). Das ist bewusst der Startpunkt; die beobachteten Schwächen unten zeigen, wo semantische Suche später ansetzen würde.


## Systemprompt & Prompt Vorlage an den gekapselten Chat:
"
❯ Du testest einen Wissensdienst und beantwortest eine Fachfrage ausschließlich mit diesem Dienst.

  THEMA/FRAGE (User Story U1):
  "Was ist die aktuelle Position der Versicherungswirtschaft zum Thema Nachhaltigkeitsberichterstattung (CSRD/ESRS)? Was ist der aktuelle Informationsstand?"

  ZUGANG ZUM DIENST: Der Dienst ist ein MCP-Server über den Positionspapiere und Stellungnahmen des GDV (Gesamtverband der Deutschen Versicherer) abfragbar sind. Du erreichst ihn NUR über dieses Bash-Kommando (fester Pfad):

    WRAP='/pfad/zu/scratchpad/mcp_ask'

  Unterkommandos:
    bash "$WRAP" overview                          # Aufbau + Navigationslogik des Dienstes
    bash "$WRAP" search "suchbegriff" limit=8      # optional Filter: thema=... gesetz=... jahr=... dokumenttyp=... sprache=...
    bash "$WRAP" list thema="..." limit=20         # Metadatenliste, neueste zuerst
    bash "$WRAP" fetch "<id>"                       # Volltext + Metadaten eines Dokuments (id aus search/list)
    bash "$WRAP" register "nach-thema/<slug>"       # thematisches Register; auch nach-gesetz/<slug>, rote-linien

  STRIKTE REGELN:
  - Beziehe JEDE inhaltliche Aussage ausschließlich aus den Rückgaben dieser MCP-Kommandos.
  - Nutze KEIN Vorwissen, KEINE Websuche, lies KEINE lokalen Dateien direkt. Nur der Dienst zählt.
  - Belege jede Aussage mit Dokument-id und url. Lies mehrere relevante Dokumente per fetch.
  - Beginne mit overview, um die Navigation zu verstehen, dann recherchiere gezielt.
  - Wenn der Dienst etwas nicht hergibt, schreibe das ehrlich.

  Gib am Ende auf Deutsch aus (das ist dein finaler Antworttext):
  1. ANTWORT: strukturierte Beantwortung der Frage (aktuelle Position, Kernaussagen, Stand/Datum).
  2. VERWENDETE QUELLEN: Liste id + url + datum je genutztem Dokument.
  3. MCP-TRANSKRIPT: jede ausgeführte Kommandozeile, je ein Satz was zurückkam.
  4. SELBSTEINSCHÄTZUNG: Ließ sich die Frage aus dem Dienst beantworten? Welche Lücken/Schwächen fielen auf (Retrieval-Qualität, fehlende Dokumente, Aktualität)?
"

## Reproduktion

```sh
# 1. Server lokal starten (Python-Umgebung mit fastmcp):
BUNDLE_DIR=bundles/gdv-stellungnahmen PORT=8000 python mcp_server/server.py
# 2. Abfragen über das MCP-CLI (redet echtes MCP mit dem Server):
python mcp_server/mcp_ask.py overview
python mcp_server/mcp_ask.py search "solvency ii" limit=5
python mcp_server/mcp_ask.py fetch "<id-aus-search>"
python mcp_server/mcp_ask.py register "nach-gesetz/digitaler-euro"
```

Die getesteten Fragen sind konkrete Ausprägungen der generischen User Stories (die Platzhalter "Thema X" bzw. "Gesetz Y" wurden mit im Bestand gut vertretenen Beispielen gefüllt):

- **U1** (aktuelle Position zu Thema X): Nachhaltigkeitsberichterstattung (CSRD/ESRS)
- **U2** (frühere Positionen zu geplantem Gesetz + Entwicklung über die Zeit): Digitaler Euro
- **U3** (rote Linien / unverzichtbare Statistiken bei Bürokratieabbau): Unternehmensstatistik/Bürokratieabbau
- **U4** (fachbereichsübergreifende Sicht): Künstliche Intelligenz

---

# U1: Aktuelle Position zu einem Thema (Nachhaltigkeitsberichterstattung, CSRD/ESRS)

**Frage:** "Was ist die aktuelle Position der Versicherungswirtschaft zum Thema Nachhaltigkeitsberichterstattung (CSRD/ESRS)? Was ist der aktuelle Informationsstand?"

## Antwort des Agenten

Der GDV unterstützt die Nachhaltigkeitsberichterstattung im Grundsatz, hält den EU-Rahmen in seiner ursprünglichen Form aber für "überkomplex" und begrüßt daher die laufende Vereinfachung (Omnibus, ESRS-Reform). Kernbotschaft durchgehend: Vereinfachung ja, aber sie muss praktisch spürbar sein und darf die Aussagekraft nicht zerstören. Versicherer haben eine Doppelrolle (Ersteller und zugleich Nutzer/Investoren von Nachhaltigkeitsberichten).

**a) Grundhaltung / EU-Ebene (Omnibus)**
- Begrüßt die geplante Reduzierung des CSRD-Anwendungsbereichs um rund 80 Prozent (nur noch Unternehmen mit mehr als 1.000 Beschäftigten) und die zweijährige Verschiebung der Berichtspflichten (`stellungnahmen/2025/finale-verbandskommentierung-zum-ersten-omnibus-paket`, 2025-04-11).
- Begrüßt die Streichung sektorspezifischer ESRS, will keine zusätzlichen Leitlinien für Versicherer.
- Für Beibehaltung der doppelten Wesentlichkeit und der Prüfung mit "limited assurance" (kein "reasonable assurance").
- Fordert Verankerung der Vereinfachung auf Level-1-Ebene (Art. 29b EU-Bilanzrichtlinie), mind. 25 Prozent Bürokratie-Reduktion (35 Prozent für KMU).

**b) ESRS-Reform (fachlich zentraler Strang; 2025-09-29 und 2026-06-03)**
- Die von EFRAG angestrebte Reduktion der Datenpunkte um 57 Prozent sei praktisch noch nicht erreicht (vieles nur gekürzt/umklassifiziert).
- GHG-Emissionen: Entlastung bei unvollständiger Datenabdeckung (ESRS 1, para. 91) schließe ausgerechnet Scope-3-Emissionen aus; GDV fordert Streichung dieser Ausnahme, Bilanzierungsgrenze näher am GHG-Protocol, für Versicherer Prinzip der "tatsächlichen Kontrolle".
- Wesentlichkeit: "informed assessments" senke die Schwelle, schaffe Rechtsunsicherheit; Streichung und stärkere ISSB-Ausrichtung (IFRS S1/S2) gefordert.
- Anticipated Financial Effects: quantitative Angaben zu unsicher; qualitative Berichterstattung solle dauerhaft zulässig bleiben.
- Keine neuen Pflicht-Datenpunkte, keine Verweise auf externe freiwillige Standards (z.B. PCAF); "First Mover" nicht bestrafen.
- 2026-06-03 begrüßt der GDV Fortschritte im delegierten Rechtsakt (6. Mai 2026), fordert aber Nachbesserungen (GHG-Relief, AFE, ISSB-Interoperabilität).

**c) Nationale Umsetzung (CSRD-Umsetzungsgesetz, 2025-10-16)**
- Begrüßt das Gesetz "weitgehend", v.a. die Befreiung von Unternehmen mit 501 bis 1.000 Beschäftigten für 2025/2026.
- Nachbesserungen: Formatvorgaben über Offenlegungsansatz (§ 328 HGB), Rechtssicherheit beim Anwendungsbeginn, pragmatische Arbeitnehmereinbindung, Opt-out Prüferbestellung, 1:1-Umsetzung, Berücksichtigung kleiner nicht komplexer Versicherer, Entkopplung von ESRS- und EU-Taxonomie-Berichterstattung.

**Stand:** aktuellstes Dokument 2026-06-03; Gesamtbestand bis 2026-06-29. Hochaktuell.

## Verwendete Quellen (U1)

- `stellungnahmen/2026/stellungnahme-zu-den-fachlichen-empfehlungen-der-efrag-zum-esrs-verein` — 2026-06-03 — https://www.gdv.de/resource/blob/200836/eba218098baa6ddf421580b5b227e1d2/mi-esrs-konsultation-comment-on-efrag-s-technical-advice-on-the-esrs-simplification-mandate-data.pdf
- `stellungnahmen/2025/stellungnahme-zum-csrd-umsetzungsgesetz` — 2025-10-16 — https://www.gdv.de/resource/blob/193666/a4d3af5423755fdcaeb90153fbf800bc/stellungnahme-zum-csrd-umsetzungsgesetz-data.pdf
- `stellungnahmen/2025/positionspapier-zu-den-uberarbeiteten-entwurfen-des-esrs-englisch` — 2025-09-29 — https://www.gdv.de/resource/blob/192970/80cd34bf3e22c8af1f9d270fcfe0f583/mi-esrs-reform-stellungnahme-download-data.pdf
- `stellungnahmen/2025/finale-verbandskommentierung-zum-ersten-omnibus-paket` — 2025-04-11 — https://www.gdv.de/resource/blob/187480/801c14f330561dee351835936bb93bfb/eu-macht-vorschlaege-fuer-eine-effizientere-nachhaltigkeitsberichterstattung-download-data.pdf
- `stellungnahmen/2025/positionspapier-zur-geplanten-uberarbeitung-der-eu-nachhaltigkeitsberi` — 2025-05-06 (nur Kurzfassung)

## MCP-Transkript (U1)

- `overview` — Aufbau, Navigationslogik (348 Dokumente, U1 über oberstes/neuestes Dokument im Themenregister).
- `search "CSRD Nachhaltigkeitsberichterstattung ESRS" limit=10` — 10 einschlägige Dokumente 2022 bis 2026.
- `register "nach-thema/nachhaltigkeit"` — 33 Dokumente, neueste zuerst.
- `register "nach-gesetz/csrd-esrs"` — 39 Dokumente zum Vorhaben.
- `fetch` der vier Kern-Dokumente (2026-06-03, 2025-10-16, 2025-09-29, 2025-04-11) — Volltexte mit Paragraphenverweisen.

## Selbsteinschätzung des Agenten (U1)

Sehr gut beantwortbar; Bestand dicht und aktuell; Navigationslogik zuverlässig. Beobachtete Schwächen: (1) **Retrieval-Rauschen** im Gesetzesregister (themenfremde Dokumente unter `nach-gesetz/csrd-esrs`, z.B. Containerverluste, RVG); Themenregister war präziser. (2) **docling-Konvertierungsartefakte** in großen Tabellen, vereinzelt Tippfehler. (3) Mehrere Kern-Papiere nur **auf Englisch**, obwohl `sprache: de`. (4) Kleinere Datumsinkonsistenz (Metadatum vs. Unterschriftsdatum im Text).

---

# U2: Frühere Positionen zu einem geplanten Gesetz + Entwicklung über die Zeit (Digitaler Euro)

**Frage:** "Ein Gesetz zum digitalen Euro ist geplant und wir werden konsultiert. Was sagen frühere GDV-Stellungnahmen dazu? Hat sich die Position im Zeitverlauf verändert?"

## Antwort des Agenten

Das Gesetzesregister "Digitaler Euro" enthält drei Dokumente (2021 bis 2023) mit grundsätzlich konstanter, im Zeitverlauf konkreter werdender Position.

**Was frühere Stellungnahmen sagen:**
- Grundsatz: GDV begrüßt den digitalen Euro durchgängig (monetäre Souveränität, internationale Rolle des Euro, weniger Abhängigkeit von nicht-europäischen/privaten Zahlungsdienstleistern).
- Funktion: reines Zahlungsmittel, nicht Wertaufbewahrung; 2023 begrüßt der GDV den Ausschluss einer Verzinsung.
- Finanzstabilität: Vermeidung von Disintermediation/"digitalem Bank Run", Zugangsbegrenzung (2021: 3.000 Euro je Bürger als "guter Ausgangspunkt"); 2023 begrüßt, dass die EZB damit betraut wird.
- Verhältnis zu privaten Zahlungssystemen: ergänzen, nicht ersetzen.
- Sicherheit/Datenschutz: höchste Standards, wie Bargeld.
- Programmierbarkeit/M2M: 2021 Diskussionspunkt; 2023 konkret unterstützt (Industrie 4.0), mit Hinweis auf Anpassung des Autorisierungsrahmens (Art. 49 PSR-Vorschlag).
- Branchenspezifisch (neu 2023): keine Annahmepflicht des digitalen Euro in Versicherungsverträgen, wo bisher keine Barzahlung üblich (konkrete Änderungen an Art. 9/10 des Vorschlags).
- Nachhaltigkeit: energieeffiziente, perspektivisch klimaneutrale Ausgestaltung (2021).

**Zeitliche Entwicklung:** 2021-08-11 prinzipienbasierte Zustimmung (offene Gestaltungsfragen) → 2023-08-09 inhaltlich unveränderte Zustimmung, aber konkret am Gesetzestext, mit neuer branchenspezifischer Forderung (keine Annahmepflicht). **Keine Kehrtwende**, sondern Verfeinerung von allgemeinen Prinzipien zu konkreten Änderungswünschen. Keine Stellungnahme jünger als 08/2023 im Register.

## Verwendete Quellen (U2, chronologisch)

- `stellungnahmen/2021/positionspapier-der-digitale-euro-aus-sicht-der-deutschen-versicherung` — 2021-08-11 — https://www.gdv.de/resource/blob/69168/c6808ce9b9e918fcef3019fb13560152/positionspapier-digitaler-euro-data.pdf
- `stellungnahmen/2023/positionspapier-digitale-identitaten-in-deutschland` — 2023-07-06 (nur Randbezug) — https://www.gdv.de/resource/blob/137116/1fc3fa08320da2957b8d6993ef6bdbb8/digitale-identitaeten-data.pdf
- `stellungnahmen/2023/stellungnahme-zum-legislativvorschlag-der-europaischen-kommission-zur` — 2023-08-09 — https://www.gdv.de/resource/blob/186916/c79743879a88cc6e72cfdec704b26e00/stellungnahme-zum-legislativvorschlag-der-europaeischen-kommission-zur-einfuehrung-des-digitalen-euro-data.pdf

## MCP-Transkript (U2)

- `overview`; `register "nach-gesetz/index"` (15 Vorhaben, "Digitaler Euro" mit 3 Dokumenten); `register "nach-gesetz/digitaler-euro"` (chronologisch); `search "digitaler Euro" limit=12`; `search "digitales Zentralbankgeld CBDC Zahlungsverkehr"`; `fetch` der Dokumente 2021 und 2023; Kontroll-`fetch` von Randtreffern (Digitale Identitäten; Echtzeitüberweisungen 2022, ausgeschlossen).

## Selbsteinschätzung des Agenten (U2)

Gut beantwortbar; Zeitverlauf klar erkennbar (sauberer Vorher/Nachher-Vergleich). Schwächen: (1) dünne Datenbasis (nur zwei substantielle Dokumente, ein Registereintrag nur Randtreffer); (2) **keine Stellungnahme jünger als 08/2023**, obwohl Bestand bis 2026 reicht (keine aktuelle Position zur laufenden Trilog-Phase).

---

# U3: Rote Linien / unverzichtbare Statistiken bei Bürokratieabbau

**Frage:** "Neues Gesetz zum Bürokratieabbau geplant. Wir sind dafür, sorgen uns aber, dass wichtige Statistiken/Datenerhebungen für die Versicherungswirtschaft abgebaut werden. Welche Statistiken/Daten/Pflichten hat der GDV in der Vergangenheit als unverzichtbar bezeichnet? Was sind rote Linien?"

## Antwort des Agenten

**Vorbehalt:** Das Register `rote-linien` ist im Dienst noch nicht befüllt (als Fachbereichs-Ausbau vorgesehen). Es gibt keine kuratierte Liste; die Antwort stützt sich auf Volltextsuche. Der einzige Kerntreffer ist die Stellungnahme zum Ersten Unternehmensstatistikreformgesetz (2026-04-22).

**Rote Linie (belegte Zitate):**
- "Der GDV unterstützt den Bürokratieabbau im Unternehmensstatistikrecht, mahnt jedoch an, dass Effizienzgewinne nicht zulasten verlässlicher statistischer Grundlagen für Wirtschaft, Risikoanalyse und Vertragsanwendung gehen dürfen."
- "Für die Versicherungswirtschaft sind verlässliche Daten eine zentrale Grundlage ihrer Geschäftstätigkeit. Versicherer bewerten Risiken, kalkulieren Prämien, steuern Kapitalanlagen und erfüllen langfristige vertragliche Verpflichtungen. Hierfür benötigen sie belastbare statistische Informationen, u. a. aus der amtlichen Statistik."
- Bewertungsmaßstab: "... nicht allein an der formalen Rückführung auf EU-Mindestvorgaben ausgerichtet werden. Maßgeblich ist darüber hinaus, ob statistische Erhebungen und Datenreihen einen erkennbaren Nutzen etwa für Markttransparenz, Risikobewertung, Vertragsanwendung und volkswirtschaftliche Analyse haben."
- Leitsatz: "so viel Datenerhebung wie nötig und so effizient wie möglich" bzw. "... dort nachzusteuern, wo der Wegfall von Erhebungen oder Merkmalen zu einem unverhältnismäßigen Informationsverlust führen würde."

**Gegenrichtung (wichtig für ein faires Bild):** In der Modernisierungsagenda für Staat und Verwaltung (2026-04-21) nennt der GDV die ESZB-Versicherungsstatistik der Bundesbank und diverse aufsichtsrechtliche Berichtspflichten selbst als Belastungen, die er reduziert/entdoppelt sehen will. Der GDV verteidigt Statistiken also nicht pauschal, sondern will Doppelmeldungen abbauen.

**Fazit:** Belegbare rote Linie = Bürokratieabbau ja, aber kein "unverhältnismäßiger Informationsverlust" bei Risikobewertung, Prämienkalkulation, Schadenregulierung, Aufsicht, volkswirtschaftlicher Analyse; entscheidend ist der Nutzen, nicht die EU-Mindestvorgabe. Eine namentliche Liste einzelner "unverzichtbarer" Statistiken gibt der Dienst nicht her.

## Verwendete Quellen (U3)

- `stellungnahmen/2026/stellungnahme-zum-entwurf-eines-ersten-unternehmensstatistikreformgese` — 2026-04-22 (Hauptbeleg) — https://www.gdv.de/resource/blob/198682/820f06a28a102437fdebcd78fd6c62f8/stn-unternehmensstatistikreformgesetz-data.pdf
- `stellungnahmen/2026/positionspapier-zur-modernisierungsagenda-fur-staat-und-verwaltung-bun` — 2026-04-21 (Gegenrichtung) — https://www.gdv.de/resource/blob/198454/6a6fe9b526f2d33978b7ec6b2baadbd7/positionspapier-zur-modernisierungsagenda-fuer-staat-und-verwaltung-data.pdf
- Geprüft, aber ohne Statistik-Verteidigung: `stellungnahmen/2024/...burokratieentlastungsgeset` (Eigenentlastung); `stellungnahmen/2026/gemeinsame-verbande-stellungnahme-zum-datenschutzrechtlichen-teil-des` ("unverzichtbar" nur im DSGVO-Kontext).

## MCP-Transkript (U3)

- `overview`; `register "rote-linien"` (leer/Stub); `search "Bürokratieabbau" limit=10`; `search "Statistik unverzichtbar" limit=10`; `search "Meldepflicht Berichtspflicht" limit=10`; `search "unverzichtbar" limit=10`; `fetch` Unternehmensstatistikreformgesetz; `register "nach-gesetz/buerokratieabbau"` (27 Dokumente); Kontroll-`fetch` von Bürokratieentlastungsgesetz und Datenschutz-Omnibus; `fetch` Modernisierungsagenda.

## Selbsteinschätzung des Agenten (U3)

Teilweise beantwortbar; Kernaussage gut belegbar. Wichtige Schwächen: (1) **`rote-linien`-Register leer** (kein vom Fachbereich bestätigter Kanon). (2) **Lexikalische Suche fand die rote-Linien-Vokabeln schlecht**: "unverzichtbar" trifft im Statistik-Kontext gar nicht; die eigentliche rote Linie ist als "dürfen nicht zulasten ... gehen" / "unverhältnismäßiger Informationsverlust" formuliert. Der Treffer kam über "Bürokratieabbau"/"Statistik", nicht über die erwarteten Schlagworte. (3) Keine namentliche Liste einzelner Statistiken. (4) Positionierung nicht einseitig (Gegenrichtung Modernisierungsagenda).

---

# U4: Fachbereichsübergreifende Sicht (Künstliche Intelligenz)

**Frage:** "Zum Thema Künstliche Intelligenz: Welche Fachbereiche/Themenfelder des GDV haben dazu Position bezogen, und was sind die Kernaussagen?"

## Antwort des Agenten

Der Dienst erschließt KI über das Themenregister "Künstliche Intelligenz" (5 Dokumente, 2022 bis 2023) und den Fachbereich-Entwurf "Digitalisierung, KI und Cyber" (41 Dokumente); zusätzlich weist jedes Dokument Fachbereich-Entwürfe aus.

**Federführend: "Digitalisierung, KI und Cyber" (Entwurf).** Kernaussagen im Zeitverlauf:
- Technologieneutrale, risikobasierte Regulierung, "so viel wie nötig, so wenig wie möglich"; bestehendes Recht gilt auch für KI; Versicherungsbereich kein Hochrisiko-Sektor, keine Sonderregulierung (2020, 2022).
- KI-Definition nicht zu weit fassen; klassische statistische Verfahren (Regression, GLMs) sind keine KI; OECD-Definition begrüßt (2023, jüngstes Papier 2025 "Definition eines KI-Systems").
- Generative KI/Basismodelle: Versicherer meist "Downstream-Provider"; zu strenge Auflagen = Wettbewerbsnachteil (2023).
- Umsetzung der KI-Verordnung innovationsfreundlich halten; Bürokratie darf KI-Einsatz nicht bremsen (2024).

**Übergreifend: KI-Haftung.** Die Stellungnahme zur Produkthaftungs-/KI-Haftungsrichtlinie (2022) ist **drei** Fachbereichen zugeordnet: Volkswirtschaft und Märkte, Digitalisierung/KI/Cyber, Schaden- und Unfallversicherung. Kernaussage: vorgesehene Beweiserleichterungen gehen zu weit; bewährte Produkthaftungsprinzipien erhalten.

**Zusammenfassung:** Position bezogen v.a. "Digitalisierung, KI und Cyber" (federführend) sowie im Haftungskontext "Volkswirtschaft und Märkte" und "Schaden- und Unfallversicherung". Eine eigenständige KI-Position weiterer Fachbereiche ließ sich nicht belegen (die AGG-Stellungnahme 2026 tauchte als Fehltreffer auf, erwähnt KI im Volltext aber nicht).

## Verwendete Quellen (U4)

- `stellungnahmen/2020/digitalisierung-daten-und-kunstliche-intelligenz` — 2020-11-27
- `stellungnahmen/2022/positionspapier-zum-eu-rechtsrahmen-fur-kunstliche-intelligenz` — 2022-03-02
- `stellungnahmen/2022/eu-kommissionsvorschlage-zur-produkthaftung-und-einer-neuen-ki-haftung-120836` — 2022-12-19
- `stellungnahmen/2023/gdv-positionspapier-zum-beginn-der-trilogverhandlungen-zur-ki-verordnu` — 2023-07-17
- `stellungnahmen/2023/positionspapier-zu-basismodellen-und-generativer-ki-fur-die-trilogverh` — 2023-09-28
- `stellungnahmen/2024/die-forderungen-der-deutschen-wirtschaft-zur-umsetzung-der-ki-verordnu` — 2024-06-11
- `stellungnahmen/2025/gdv-positionspapier-zur-definition-eines-ki-systems` — 2025-12-22

## MCP-Transkript (U4)

- `overview`; `register "nach-fachbereich"` (8 Fachbereiche; "Digitalisierung, KI und Cyber" 41 Dok.); `register "nach-thema"` (26 Themen; "Künstliche Intelligenz" 5 Dok., "Digitalisierung" 39); `register "nach-thema/kunstliche-intelligenz"`; `search "Künstliche Intelligenz" limit=12`; `register "nach-fachbereich/digitalisierung-ki-und-cyber"`; `fetch` von 6 KI-Papieren (2020 bis 2025); Filtertests `fachbereich="Lebensversicherung und Altersvorsorge"` / `"Schaden- und Unfallversicherung"`; `register "nach-gesetz/ki-verordnung"` (8 Dok.).

## Selbsteinschätzung des Agenten (U4)

Überwiegend beantwortbar; Fachbereichs-/Themenstruktur half für die übergreifende Sicht (v.a. die Mehrfach-Zuordnung bei KI-Haftung). Schwächen: (1) Fachbereichs-Zuordnung ist **automatischer Entwurf**, kann von faktischer Federführung abweichen. (2) Enges Thema "Künstliche Intelligenz" **unvollständig** (nur 5 Dok., endet 2023; neuere KI-Papiere nur unter "Digitalisierung"). (3) Freitextsuche liefert **Fehltreffer** (AGG-2026 ohne KI-Bezug). (4) Kein einziger Filter, der die volle KI-Sicht quer über alle Register herstellt.

---

# Übergreifende Bewertung

## Was gut funktioniert

- **Alle vier Fragen sind allein aus der Pipeline beantwortbar**, mit belegten Zitaten, korrekter Chronologie und Quellen-URLs. Die Antworten stammen nachweislich aus dem MCP-Server (Transkripte), nicht aus Modellwissen.
- **Navigationslogik** (overview → Register → fetch) funktioniert zuverlässig; das "neueste Dokument im Register = aktuelle Position" (U1) und die chronologische Ordnung (U2) tragen.
- **Metadaten/Frontmatter** (`datum`, `themen`, `gesetzesbezug`, `fachbereiche_entwurf`) ermöglichen genau die schwierigen Sichten: Zeitverlauf (U2) und fachbereichsübergreifend (U4).
- **Bestand ist dicht und aktuell** (bis 2026-06); für gut regulierte Themen (CSRD/ESRS, KI) viele Dokumente.

## Beobachtete Schwächen (Kandidaten für die nächste Ausbaustufe)

1. **Lexikalische Suche verfehlt Paraphrasen** (U3 am deutlichsten): Konzepte wie "rote Linie / unverzichtbar" sind im Text anders formuliert ("dürfen nicht zulasten ... gehen"). → Stärkstes Argument für **semantische Suche/Embeddings** hinter dem `search`-Tool.
2. **Gesetzesregister mit Fehlzuordnungen** (U1, U4): Die automatische, stichwortbasierte Gesetzeserkennung nimmt themenfremde Dokumente auf (z.B. Containerverluste unter CSRD/ESRS; AGG-2026 als KI-Treffer). → Präzisere Erkennung oder manuelle Kuratierung der Register.
3. **Website-Themen-Taxonomie inkonsistent** (U4): Das enge Thema "Künstliche Intelligenz" endet 2023; neuere KI-Papiere hängen nur unter "Digitalisierung". → Ergänzende, konsistente Verschlagwortung (auch ein Fachbereichs-Thema).
4. **`rote-linien`-Register ist leer** (U3) und **Fachbereichs-Zuordnung ist Entwurf** (U4). → Beides ist der geplante Fachbereichs-Ausbau; U3/U4 werden dadurch erst richtig belastbar.
5. **Konvertierungsartefakte** (U1): docling-Tabellen enthalten Rauschen/Tippfehler. Für Zitate bleibt das Original-PDF maßgeblich (ist verlinkt).
6. **Sprach-/Aktualitätslücken**: einige Papiere nur englisch trotz `sprache: de` (U1); zu manchen Vorhaben keine ganz aktuellen Stellungnahmen (U2: digitaler Euro nur bis 08/2023).

## Bewertungsleitfaden für die fachliche Prüfung

Bitte je User Story prüfen:
- Ist die inhaltliche Aussage **fachlich korrekt** und vollständig gegenüber den verlinkten Original-PDFs?
- Sind die **richtigen/wichtigsten** Dokumente gefunden worden, oder fehlen zentrale Stellungnahmen?
- Stimmt die **zeitliche Einordnung** (U2) bzw. die **Fachbereichs-Zuordnung** (U4)?
- Sind die zitierten **roten Linien** (U3) so tatsächlich Position des GDV, und welche weiteren gehören kuratiert ergänzt?

Rückmeldungen zu 1 bis 4 (Suche, Register, Taxonomie, Kuratierung) fließen direkt in die nächste Ausbaustufe (semantische Suche, bestätigtes Fachbereichs-Mapping, gefülltes rote-Linien-Register).
