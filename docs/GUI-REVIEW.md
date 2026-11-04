# GUI-Überarbeitung – historischer Zwischenstand

Dieser Bericht dokumentiert einen früheren Entwicklungsstand. Die damaligen
Testergebnisse sind keine aktuelle Release-Abnahme. Der aktuelle Prüfstatus steht
im [Testbericht](TESTING.md).

Als Referenz diente eine lokale Bildvorlage, die weder Bestandteil des öffentlichen
Repositories noch der Release-Pakete ist. Die bestehende Qt-GUI wurde gezielt überarbeitet;
Parser, Archivleser, Exportlogik und Datenschutzregeln sind unverändert.

## Vergleich

| Vorlage / Anforderung | Umsetzung |
| --- | --- |
| Orange Kopfzeile | Projekttitel auf durchgehend orangefarbener Kopfzeile |
| Kompakte Backupzeile | Dateiauswahl und lesbare, umbrechende Backupinformationen |
| Seitennavigation | Apps und Webseiten, mit den beiden Reitern synchronisiert |
| Suche und App-Filter nebeneinander | Dehnbares Suchfeld und Filter mit inhaltsabhängiger Breite |
| Helle Tabellen / dezente Auswahl | Wechselnde helle Zeilen, orange getönte Auswahl |
| Separate Anzahl | Eigene Spalte für die Anzahl eindeutiger Domains/IPs |
| Status | Aktiviert/Deaktiviert als fett gesetzter, farbiger Text; keine Schalter |
| Details unter der Tabelle | Metadaten links, vollständige scrollbar dargestellte Domainliste rechts |
| Kopieren bei Domains | Kleine Tasten für ausgewählte Domains und die gesamte App-Liste |
| Kleine Exportaktionen | TXT/CSV rechts unter dem Detailbereich; Tabellen-Kopieraktionen links |
| Datenschutz am unteren Rand | Dauerhafter Hinweisblock sowie Offline-/Lesehinweis in der Statusleiste |

Die Tabelle zeigt die erste Domain vollständig und die Anzahl weiterer Domains.
Die Detailansicht enthält weiterhin sämtliche Domains/IPs; Suche, Kopieren und Export
arbeiten unverändert mit der vollständigen Liste. Breite Spalten sind horizontal scrollbar.
Es wurden keine Funktionen entfernt. Nicht vorhandene Hilfe-/Einstellungsfunktionen
und die Schalter aus dem Mockup wurden nicht als funktionslose Bedienelemente ergänzt.

## Historische Nachweise (Zwischenstand)

- 52 Tests erfolgreich, darunter neun GUI-Tests.
- GUI-Tests zusätzlich erfolgreich bei 150 % und 200 % Skalierung.
- Fenstergrößen 900 × 700, 1180 × 760 und 1500 × 950 logische Pixel geprüft.
- Schaltflächen erhalten nur ihre benötigte Breite; Beschriftungen und Tabellenüberschriften
  werden anhand der tatsächlich verwendeten Schriftmetriken geprüft.
- Keine festgelegte Linux-Schriftfamilie; Qt verwendet die jeweilige Systemschrift.
- Lange Domainlisten, Unicode, Suche, Filter, Kopieren und Export weiterhin getestet.
- Screenshots mit ausschließlich synthetischen Daten visuell mit der Vorlage verglichen:
  [100 %](screenshots/gui-linux.png), [150 %](screenshots/gui-linux-150.png),
  [200 %](screenshots/gui-linux-200.png).

Die Screenshots wurden unter Linux mit Qt-Offscreen erzeugt. Der direkte X11-Versuch
scheiterte am nicht erreichbaren Display `:0`. Deshalb sind dies keine Aufnahmen aus
einer laufenden KDE-Sitzung. Windows 11 wurde hier nicht ausgeführt. Native Dialoge,
systemweite Zwischenablage und Windows-Schriftmetriken bleiben praktisch zu prüfen.

Reproduzieren (Linux, vom Projektverzeichnis):

```bash
PYTHONPATH=src QT_QPA_PLATFORM=offscreen .venv/bin/python scripts/preview_gui.py docs/screenshots/gui-linux.png
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
QT_QPA_PLATFORM=offscreen QT_SCALE_FACTOR=1.5 .venv/bin/python -m pytest tests/test_gui.py -q
QT_QPA_PLATFORM=offscreen QT_SCALE_FACTOR=2 .venv/bin/python -m pytest tests/test_gui.py -q
```

Das Vorschau-Skript öffnet keine Sicherung. Es erstellt nur die ausdrücklich angegebene
Bilddatei. Für einen nativen Linux-Screenshot in einer erreichbaren X11-Sitzung kann
`QT_QPA_PLATFORM=xcb` verwendet werden.

Kein Commit, Push oder Release durchgeführt.
