# eBlocker Backup Explorer

Kostenloses Werkzeug zum Anzeigen und Kopieren eigener Apps, Domains und
Webseitenfreigaben aus eBlocker-Backups.

Für Linux, Windows 11 und macOS. **macOS ist vorbereitet, aber noch nicht auf
einem echten Mac getestet.**

## Vorschau

![eBlocker Backup Explorer](docs/screenshots/gui-linux.png)

## Funktionen

- eBlocker-Backups (`.eblcfg`) öffnen
- Eigene Apps und Webseitenfreigaben anzeigen
- Domains und IP-Adressen durchsuchen
- Freigegebene Domains und IP-Adressen kopieren
- TXT- und CSV-Export
- Aktivierungsstatus anzeigen
- Keine Verbindung zum eBlocker notwendig

Unterstützt werden unverschlüsselte Backups. Angezeigt werden die im Backup
vorhandenen Apps und Webseitenfreigaben.

## Download

Die aktuelle Version und die ZIP-Pakete für alle Plattformen findest du bei den
[GitHub-Releases](https://github.com/Faber38/eBlockerBackupExplorer/releases).

## Installation

Python muss bereits installiert sein. Führe die folgenden Schritte im entpackten
Projektordner aus.

### Windows 11

1. Windows-ZIP herunterladen und entpacken.
2. Python 3.10 oder neuer (64 Bit) bereitstellen.
3. `install.bat` ausführen.
4. `start.bat` ausführen.

Die Installation lädt fehlende Python-Pakete aus dem Internet herunter.
Die Anwendung selbst arbeitet offline.

### Linux

1. Linux-ZIP herunterladen und entpacken.
2. Python 3.10 oder neuer mit `venv`-Unterstützung bereitstellen.
3. Benötigte Offline-Pakete im Ordner `wheelhouse/` bereitstellen (siehe unten).
4. Im Terminal `bash install.sh` ausführen.
5. Im Terminal `bash start.sh` ausführen.

Die Qt/X11-Systembibliotheken, darunter `libxcb-cursor0`, müssen vorhanden sein.

### macOS

1. macOS-ZIP herunterladen und entpacken.
2. Python 3.10 oder neuer (64 Bit) mit `venv`-Unterstützung bereitstellen.
3. Passende Offline-Pakete im Ordner `wheelhouse/` bereitstellen (siehe unten).
4. Im Terminal `bash install-mac.sh` ausführen.
5. Im Terminal `bash start-mac.sh` ausführen.

**macOS ist vorbereitet, aber noch nicht auf einem echten Mac getestet.**

Für Linux und macOS müssen die Offline-Pakete separat beschafft werden; sie sind
nicht in den ZIP-Dateien enthalten und werden bei der Installation nicht heruntergeladen.
Benötigt werden Wheels für `setuptools>=68`, `wheel`, `PySide6>=6.6,<7` und dessen
Abhängigkeiten (einschließlich `PySide6_Essentials`, `PySide6_Addons` und `shiboken6`).
Sie müssen zum Betriebssystem, zur Prozessorarchitektur und zur Python-Version passen.

## Datenschutz

- **Keine Passwörter erforderlich**
- **Keine Zertifikate oder Schlüssel werden gelesen**
- **Keine Netzwerkverbindungen durch die Anwendung**
- **Keine Veränderung der Backups**
- **Alle Daten bleiben lokal**

Die Anwendung liest ausschließlich die für Apps und Webseitenfreigaben benötigten
Informationen aus `appModules.json`.

## Lizenz

[MIT-Lizenz](LICENSE).

Unabhängiges Community-Projekt. Keine offizielle eBlocker-Anwendung.
