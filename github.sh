#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if ! command -v python3 >/dev/null 2>&1; then
    echo '[FEHLER] Python 3.10 oder neuer wird benötigt.' >&2
    exit 1
fi
exec python3 -B scripts/publish_release.py
