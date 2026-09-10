# Schulessen (OPC WebApp) – Home Assistant Integration

Liest den Menüplan und den Bestellstatus aus der "OPC WebApp" (z.B.
`schulessen-bestellung.lspb.de` der Stadt Paderborn) aus. Dieses System wird
von OPC AG an viele deutsche Kommunen für die Schulessen-Bestellung
lizenziert – die Basis-URL ist daher konfigurierbar, andere Städte mit dem
gleichen Backend sollten ebenfalls funktionieren.

## Funktionsumfang

Bestellungen sind immer nur bis 15:00 Uhr am Vortag möglich. Deshalb zielen
die Warn-Entities nicht auf "heute" (das ist ja längst fixiert), sondern auf
den **nächsten Schultag** – den Tag, für den man jetzt noch etwas ändern
könnte.

- **`sensor.schulessen_bestellt_heute`** (Anzeigename "Schulessen aktuelles
  Essen") – zeigt bis 14:00 Uhr das heutige bestellte Gericht, danach
  automatisch das des nächsten Schultags (Umschalt-Stunde einstellbar über
  die Integrations-Optionen). Zustand ist nur der Gerichtname; `date`,
  `weekday` und `is_today` liegen als Attribute daneben, damit man sie in
  einer Karte frei formatieren kann, z.B.:

  ```yaml
  type: markdown
  content: >
    **{{ state_attr('sensor.schulessen_bestellt_heute', 'weekday') }}**
    ({{ state_attr('sensor.schulessen_bestellt_heute', 'date') }}):
    {{ states('sensor.schulessen_bestellt_heute') }}
  ```
- **`sensor.schulessen_naechster_schultag`** – bestelltes Gericht (oder
  "Nichts bestellt") für den nächsten Tag mit Angeboten.
- **`sensor.schulessen_menueplan`** – Liste aller kommenden Tage (aktuelle +
  nächste Woche) mit allen verfügbaren Gerichten je Tag und ob/welches
  bestellt wurde (Attribut `days`).
- **`sensor.schulessen_bestellungen_im_voraus`** – Anzahl der Tage ab heute,
  für die bereits eine Bestellung vorliegt.
- **`binary_sensor.schulessen_nicht_bestellt`** – **on**, wenn es für den
  nächsten Schultag Angebote gibt, aber nichts bestellt wurde. Damit lässt
  sich eine Erinnerungs-Automation bauen.

Die Integration bestellt nichts – sie liest nur.

## Action: `schulessen_lspb.refresh`

Ruft den Menüplan sofort neu ab, statt auf das reguläre Abfrageintervall zu
warten (Standard: alle 4 Stunden, einstellbar über die Integrations-Optionen).
Damit lässt sich das Intervall bewusst niedrig halten und stattdessen gezielt
kurz vor der 15-Uhr-Bestellgrenze ein frischer Abruf per Automation auslösen.

## Installation über HACS

1. Dieses Repository als "Custom Repository" (Kategorie: Integration) in
   HACS hinzufügen.
2. "Schulessen (OPC WebApp)" installieren, Home Assistant neu starten.
3. Einstellungen → Geräte & Dienste → Integration hinzufügen → "Schulessen
   (OPC WebApp)" suchen.
4. Kartennummer und Passwort eingeben (dieselben Zugangsdaten wie auf der
   Bestellseite). Basis-URL nur ändern, falls eine andere Stadt/Domain
   genutzt wird.

## Beispiel-Automation

Ruft kurz vor der Bestellgrenze (15:00 Uhr) frische Daten ab und warnt, falls
für den nächsten Schultag noch nichts bestellt wurde:

```yaml
alias: Erinnerung Schulessen nicht bestellt
trigger:
  - platform: time
    at: "14:45:00"
action:
  - service: schulessen_lspb.refresh
  - delay: "00:00:05"
  - condition: state
    entity_id: binary_sensor.schulessen_nicht_bestellt
    state: "on"
  - service: notify.mobile_app_dein_handy
    data:
      title: "Schulessen"
      message: "Für den nächsten Schultag wurde noch nichts bestellt!"
```

## Menüplan auf dem Dashboard anzeigen

Die Sensor-*Zustände* (z.B. "10 Tage" bei `sensor.schulessen_menueplan`) sind
bewusst kurz gehalten – Home-Assistant-Zustände sind für kurze Werte gedacht.
Die eigentlichen Gerichte mit Datum stecken im Attribut `days` und lassen
sich z.B. mit einer Markdown-Karte anzeigen:

```yaml
type: markdown
title: Schulessen Menüplan
content: >
  {% for day in state_attr('sensor.schulessen_menueplan', 'days') %}
  **{{ day.weekday }}, {{ day.date }}**
  {% for o in day.options %}
  - {{ '✅' if o.ordered else '▫️' }} {{ o.column }}: {{ o.description }} ({{ o.price }})
  {% endfor %}

  {% endfor %}
```

Für nur das heutige (bereits bestellte) Gericht direkt als Zustand reicht
`sensor.schulessen_bestellt_heute` bzw. für den nächsten Schultag
`sensor.schulessen_naechster_schultag` – beide zeigen den Gerichtnamen
direkt als Zustand, nicht als Zahl. Wollen Sie stattdessen *alle* heute
verfügbaren Gerichte (nicht nur das bestellte) sehen, nutzen Sie das
`options`-Attribut von `sensor.schulessen_bestellt_heute`:

```yaml
type: markdown
title: Heute verfügbar
content: >
  {% for o in state_attr('sensor.schulessen_bestellt_heute', 'options') %}
  - {{ '✅' if o.ordered else '▫️' }} {{ o.column }}: {{ o.description }} ({{ o.price }})
  {% endfor %}
```

## Hinweise / Grenzen

- Die Menüplan-Daten werden aus einem serverseitig gerenderten HTML-Fragment
  geparst (es gibt keine offizielle/dokumentierte JSON-API für den
  Menüplan). Ändert OPC AG das Frontend grundlegend, kann das Parsing
  brechen – bitte in diesem Fall ein Issue öffnen.
- Getestet gegen die Instanz der Stadt Paderborn. Rückmeldungen zu anderen
  Städten/Domains sind willkommen.

## Lizenz

MIT
