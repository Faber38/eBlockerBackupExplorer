#!/usr/bin/env bash
# Compatible with the Bash shipped with macOS; no package manager or sudo.
set -u
fail() {
    printf '[FEHLER] %s\n' "$1" >&2
    if [[ -t 0 ]]; then read -r -p 'Zum Schließen Eingabetaste drücken … ' _; fi
    exit 1
}
cd -- "$(dirname -- "${BASH_SOURCE[0]}")" || fail 'Projektverzeichnis nicht erreichbar.'
[[ ! -L .venv ]] || fail '.venv darf kein Verweis auf eine fremde Umgebung sein.'
if [[ -x .venv/bin/python ]]; then
    mac_python='.venv/bin/python'
else
    command -v python3 >/dev/null 2>&1 || fail 'Python 3 fehlt. Python ab 3.10 für Ihren Mac bereitstellen.'
    mac_python='python3'
fi
"$mac_python" scripts/check_macos.py || fail 'Python-Voraussetzungen nicht erfüllt. Hinweise oben beachten.'
"$mac_python" scripts/install_local.py || fail 'Lokale Offline-Installation fehlgeschlagen. Passende macOS-Wheels und Python/venv prüfen.'
.venv/bin/python scripts/check_macos.py --runtime || fail 'Lokale Python-/Qt-Umgebung nicht startbereit. Hinweise oben beachten.'
printf '%s\n' 'macOS-Installation abgeschlossen. Starten mit: bash start-mac.sh'
