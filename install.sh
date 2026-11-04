#!/usr/bin/env bash
set -u
fail() {
    printf '[FEHLER] %s\n' "$1" >&2
    if [[ -t 0 ]]; then read -r -p 'Zum Schließen Eingabetaste drücken … ' _; fi
    exit 1
}
cd -- "$(dirname -- "${BASH_SOURCE[0]}")" || fail 'Projektverzeichnis nicht erreichbar.'
command -v python3 >/dev/null 2>&1 || fail 'Python 3 fehlt. Python ab 3.10 mit venv-Unterstützung erforderlich.'
python3 scripts/install_local.py || fail 'Offline-Installation fehlgeschlagen. Hinweise oben beachten.'
