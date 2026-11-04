# Prüfstatus 0.1.0

Stand: 4. November 2026. Entwicklung ausschließlich unter Linux.

## Automatisierte Prüfung

73 pytest-Tests bestanden unter Linux, Python 3.12, PySide6/Qt 6.11.2,
pytest 9.1.1. Nach einer ersten Prüfung mit bereits lokal verfügbaren Paketen
wurde eine eigene `.venv` ausschließlich aus vorhandenen lokalen Cache-Wheels
installiert. Die vollständige Testsuite besteht auch in dieser Projektumgebung.

Zusätzliche Läufe der elf GUI-Tests mit `QT_SCALE_FACTOR=1.5` und `2`: bestanden.
Die Layouttests prüfen 900 × 700, 1180 × 760 und 1500 × 950 logische Pixel,
Schaltflächengrößen, vollständige Tabellenüberschriften, Navigation und rein lesenden Status.
Die Oberfläche wurde mit synthetischen Daten im Offscreen-Modus gerendert und visuell geprüft.

Geprüft:

- Eigene/integrierte, aktivierte/deaktivierte Apps und Vorrang von `enabledStates`.
- Mehrere und doppelte Domains, IPs, Einzelfreigaben, veraltete Labels.
- Fehlende App-Datei, leeres Archiv, leere Modulliste, ungültiges ZIP/JSON,
  doppelte JSON-Schlüssel und ZIP-Einträge, Größenlimit, Verschlüsselungsablehnung.
- Ausschließlich `appModules.json` wird als ZIP-Inhalt geöffnet. Der Test ersetzt
  `ZipFile.open` und würde bei jedem anderen Bestandteil oder Schreibmodus scheitern.
- Unveränderte synthetische Quelldatei per SHA-256, Exportzielschutz auch bei Hardlinks.
- TXT/CSV, UTF-8, Unicode, CRLF in Beschreibungen, CSV-Formelschutz.
- Suche, App-Typfilter, getrennte Webseiten, Details, Kopieraktionen,
  Qt-Zwischenablage, Export der aktuellen Ansicht, Dialogabbruch und Fehlerbereinigung.
- Lange Domains ohne Ellipsen, horizontale und vertikale Scrollleisten.
- Linux-Start aus fremdem Arbeitsverzeichnis und Pfaden mit Leerzeichen;
  fehlende Umgebung und Startfehler; wiederholter Installer mit ausschließlich lokalen pip-Aufrufen.
- Shell-Syntaxprüfung mit `bash -n`.
- Modaler Über-Dialog mit Version, Entwickler, GitHub, Systemen und Datenschutzhinweisen;
  Schließen über die Dialogschaltfläche.
- Kompakte Über-/Beenden-Schaltflächen rechts in der Backupzeile; Beenden schließt
  das Hauptfenster ohne Rückfrage. Synthetische Backups bleiben bei beiden Aktionen
  per SHA-256 nachweislich unverändert.

Alle automatisierten Backup-Fixtures sind synthetisch. Python-Netzwerkverbindungen und
Namensauflösung sind in den Tests durch Fehler auslösende Ersetzungen gesperrt.
Das ist kein Betriebssystem-Firewallnachweis für sämtliche Qt-/OS-Komponenten.

Die Anwendung wurde lokal mit eBlocker-Backups der Versionen 4 und 5 erfolgreich getestet.
Dieser Praxisnachweis beruht auf Holgers Rückmeldung. Er ist unabhängig von der
weiterhin offenen automatischen Versionserkennung. Persönliche Backupinformationen
werden nicht in die öffentliche Dokumentation übernommen. Automatisierte Tests
verwenden ausschließlich synthetische Daten.

## Ergänzung macOS

15 zusätzliche Prüfungen in `tests/test_macos_scripts.py`: simuliertes macOS mit
arm64/x86_64, 64-Bit-Prüfung, ungeeignete Python-/Qt-Version, fremde Umgebung,
fehlende Qt-Bibliotheken sowie Shell-Abläufe für Start/Installation, Wiederholung,
Fehler und Symlink-Ablehnung. Shell-Aufrufe laufen unter Linux mit Test-Interpretern
in temporären Ordnern mit Leerzeichen/Umlauten; keine echte macOS-Installation.
Syntax von `install-mac.sh` und `start-mac.sh` mit `bash -n` geprüft.
Die Skripte verwenden einfache Bash-Konstrukte ohne zusätzliche Shellwerkzeuge.

Gemeinsamer Parser, Export, Suchlogik und native Qt-Dateidialoge sind unverändert.
Nur die Plattforminformation im Über-Dialog wurde um „macOS (ungetestet)“ ergänzt.
Für die Release-Vorbereitung wurden der explizite Online-Installer und vier
zugehörige Tests aus der bisherigen Windows-Test-ZIP in den gemeinsamen Quellstand
übernommen. Die neuen Pakete enthalten auch die Mac-Skripte.

## Noch nicht bestätigt

| Prüfung | Status |
| --- | --- |
| Lokale Praxistests mit eBlocker 4 und 5 | Laut Holgers Rückmeldung erfolgreich |
| Automatische Erkennung der eBlocker-Version | Weiterhin offen: Manifest wird nicht geöffnet |
| KDE/X11 auf Pop!_OS | Offen: Sandbox verhindert Anlegen des Xvfb-Display-Sockets |
| Native Linux-Dateidialoge und systemweite Zwischenablage | Manueller Test offen |
| Windows 11 Installation | Laut Holgers Rückmeldung erfolgreich; Wiederholung nicht separat bestätigt |
| Windows 11 Start, Backup öffnen, Domains anzeigen/kopieren | Laut Holgers Rückmeldung erfolgreich |
| Windows 11 TXT-/CSV-Export | Nicht praktisch getestet; Exportlogik automatisiert unter Linux geprüft |
| Neu erstellte Release-ZIP mit install.bat/start.bat | Automatisierte Prüfung unter Linux; erneuter Windows-Praxistest dieses Pakets offen |
| macOS Apple Silicon (arm64) | Skripte vorbereitet; echter Praxistest offen |
| macOS Intel (x86_64) | Skripte vorbereitet; echter Praxistest offen |

Der X11-Test ist nicht bestanden: Qt konnte das Xvfb-Display nicht erreichen;
Xvfb meldete verweigerte lokale Socket-Erstellung. `libxcb-cursor0` ist vorhanden.
Es wurden weder Systempakete noch Dienste geändert und keine Beschränkungen umgangen.

## Manuelle Plattformabnahme

Auf jeder Zielplattform ausschließlich synthetische Backups verwenden:

1. Vollständiges Projekt in einen Pfad mit Leerzeichen und Umlauten legen.
2. Ohne Umgebung starten: verständlicher Fehler, Fenster bleibt offen.
3. Offline-Wheels bereitstellen, Installation zweimal ausführen; globale Python-Umgebung unverändert.
4. Start aus fremdem Arbeitsverzeichnis; keine Paketinstallation beim Start.
5. Nativen Dateidialog öffnen, abbrechen, gültige und ungültige Sicherung auswählen.
6. Eigene/integrierte Apps, Webseiten und Statusanzeigen vergleichen.
7. Nach Namen, Beschreibung und Domain/IP suchen, auch mit anderer Großschreibung.
8. Lange Domains und mindestens 500 Einträge bei 100 %, 150 % und 200 % Skalierung prüfen.
9. Einzelne/mehrere/alle Domains kopieren und in einen lokalen Texteditor einfügen.
10. TXT und CSV mit Umlauten, Anführungszeichen und Zeilenumbrüchen exportieren.
11. Bestehendes Exportziel und Backup als Ziel auswählen: beide bleiben unverändert.
12. Windows: Test-ZIP vollständig in einen Benutzerordner entpacken; vorhandenes
    Python x64 verwenden, install.bat zweimal und start.bat ausführen. Keine
    Administratorrechte, Registry-Einträge oder globalen Paketänderungen zulassen.

Windows-/macOS-Fehler mit Version, Architektur, Skalierung und reproduzierbaren synthetischen Schritten
zurückmelden. Korrekturen ausschließlich unter Linux vornehmen, danach die betroffene Zielplattform erneut testen.
Keine echten Backups oder vertraulichen Inhalte in Fehlerberichte aufnehmen.

## Release-Prüfung am 4. November 2026

Windows-Praxisstatus beruht auf Holgers Angaben im Vorbereitungsauftrag, nicht auf
einem hier ausgeführten Windows-Lauf. macOS bleibt vorbereitet und praktisch ungetestet.
Die vier übernommenen Windows-Pakettests prüfen Installer-Aufrufe und Batch-Dateien
unter Linux; sie ersetzen keinen Windows-Praxistest. Release-Pakete enthalten keine
Wheels. Linux/macOS benötigen separat bereitgestellte, passende Offline-Pakete.

Aktueller Linux-Startcheck: `bash start.sh` startet mit `QT_QPA_PLATFORM=offscreen`
und lief bis zum kontrollierten Abbruch nach drei Sekunden. Mit `QT_QPA_PLATFORM=xcb`
scheitert der Start am nicht erreichbaren Display `:0`. Ein sichtbarer KDE/X11-Start
ist damit weiterhin nicht bestätigt. Shell-Syntaxprüfung aller vier Shellskripte bestanden.
