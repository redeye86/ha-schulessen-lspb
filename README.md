# Schulessen (OPC WebApp) – Home Assistant Integration

Liest den Menüplan und den Bestellstatus aus der "OPC WebApp" (z.B.
`schulessen-bestellung.lspb.de` der Stadt Paderborn) aus. Dieses System wird
von OPC AG an viele deutsche Kommunen für die Schulessen-Bestellung
lizenziert – die Basis-URL ist daher konfigurierbar, andere Städte mit dem
gleichen Backend sollten ebenfalls funktionieren.

## Funktionsumfang

- **`sensor.schulessen_bestellt_heute`** – zeigt an, was für heute tatsächlich
  bestellt wurde (oder "Nichts bestellt").
- **`sensor.schulessen_verfuegbar_heute`** – Anzahl der heute verfügbaren
  Gerichte, mit allen Optionen (Name, Preis, bestellt ja/nein) als Attribut.
- **`binary_sensor.schulessen_nicht_bestellt`** – **on**, wenn es heute
  Angebote gibt, aber nichts bestellt wurde. Damit lässt sich eine
  Erinnerungs-Automation bauen.

Die Integration bestellt nichts – sie liest nur.

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

```yaml
alias: Erinnerung Schulessen nicht bestellt
trigger:
  - platform: time
    at: "18:00:00"
condition:
  - condition: state
    entity_id: binary_sensor.schulessen_nicht_bestellt
    state: "on"
action:
  - service: notify.mobile_app_dein_handy
    data:
      title: "Schulessen"
      message: "Für morgen wurde noch nichts bestellt!"
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
