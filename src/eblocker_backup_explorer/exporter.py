"""Export ausschließlich der vom Aufrufer angezeigten App-/Domaininformationen."""
import csv
import io
import os
from pathlib import Path
from collections.abc import Sequence

from .app_parser import App

HEADER = ("Typ", "Name", "Beschreibung", "Status", "Domain/IP")


def render_export(apps: Sequence[App], format: str) -> str:
    if format not in ("txt", "csv"):
        raise ValueError("Unbekanntes Exportformat.")
    rows = [(a.kind, a.name, a.description, a.status, d)
            for a in apps for d in (a.domains or ("",))]
    out = io.StringIO(newline="")
    # Auch TXT ist sauber maskiertes, tabulatorgetrenntes UTF-8.
    writer = csv.writer(out, delimiter="," if format == "csv" else "\t", lineterminator="\n")
    writer.writerow(HEADER)
    for row in rows:
        # Keine ausführbaren Tabellenformeln beim Öffnen eines CSV-Exports.
        writer.writerow(["'" + v if format == "csv" and v.lstrip().startswith(("=", "+", "-", "@")) else v
                         for v in row])
    return out.getvalue()


def export_apps(path: str | Path, apps: Sequence[App], format: str, source: Path) -> None:
    target = Path(path)
    if target.suffix.lower() != "." + format or target.resolve() == source.resolve():
        raise ValueError("Bitte eine neue TXT- oder CSV-Datei als Exportziel wählen.")
    # Exklusives Erstellen schützt Quellen, Symlinks und Hardlinks auch bei Dateitausch.
    # Vorhandene Dateien werden niemals überschrieben.
    content = render_export(apps, format).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(target, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
