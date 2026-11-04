#!/usr/bin/env bash
set -u
fail() {
    printf '[FEHLER] %s\n' "$1" >&2
    if [[ -t 0 ]]; then read -r -p 'Zum Schließen Eingabetaste drücken … ' _; fi
    exit 1
}
cd -- "$(dirname -- "${BASH_SOURCE[0]}")" || fail 'Projektverzeichnis nicht erreichbar.'
[[ ! -L .venv && -x .venv/bin/python ]] || fail 'Lokale .venv fehlt. Bitte install.sh ausführen.'
.venv/bin/python scripts/launch.py || fail 'Start fehlgeschlagen. Lokale Installation und Qt/X11-Laufzeit prüfen.'
