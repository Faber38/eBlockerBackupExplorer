"""Strikt lesender ZIP-Zugriff. Genau ein erlaubter Inhaltsbestandteil."""
from dataclasses import dataclass
import json
from pathlib import Path
import zipfile
import zlib

from .app_parser import App, AppDataError, parse_apps

APP_MEMBER = "eblocker-config/appModules.json"
MAX_APP_BYTES = 16 * 1024 * 1024
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024


class BackupError(ValueError):
    """Nutzbare Fehlermeldung ohne vertrauliche Archivdaten."""


@dataclass(frozen=True)
class Backup:
    path: Path
    apps: tuple[App, ...]
    version: str = "Nicht ermittelbar (Datenschutzmodus)"


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise BackupError("appModules.json enthält doppelte JSON-Schlüssel.")
        result[key] = value
    return result


def read_backup(path: str | Path) -> Backup:
    source = Path(path)
    try:
        if not source.is_file() or source.suffix.lower() != ".eblcfg":
            raise BackupError("Bitte eine reguläre .eblcfg-Datei auswählen.")
        if source.stat().st_size > MAX_ARCHIVE_BYTES:
            raise BackupError("Die Sicherungsdatei überschreitet das Größenlimit von 256 MiB.")
        with zipfile.ZipFile(source, "r") as archive:
            matches = [i for i in archive.infolist() if i.filename == APP_MEMBER]
            if not matches:
                raise BackupError("appModules.json fehlt in dieser Sicherung.")
            if len(matches) != 1:
                raise BackupError("Die Sicherung enthält mehrere appModules.json-Einträge.")
            member = matches[0]
            if member.flag_bits & 1:
                raise BackupError("Verschlüsselte App-Daten werden nicht unterstützt.")
            if member.file_size > MAX_APP_BYTES:
                raise BackupError("appModules.json überschreitet das Größenlimit von 16 MiB.")
            # Kein extract(), kein testzip(), keine Manifest- oder sonstigen Inhaltszugriffe.
            with archive.open(member, "r") as stream:
                payload = stream.read(MAX_APP_BYTES + 1)
            if len(payload) > MAX_APP_BYTES:
                raise BackupError("appModules.json ist zu groß.")
        data = json.loads(payload.decode("utf-8-sig"), object_pairs_hook=_unique_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        return Backup(source.resolve(), parse_apps(data))
    except BackupError:
        raise
    except AppDataError as exc:
        raise BackupError(str(exc)) from None
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError):
        raise BackupError("appModules.json enthält ungültige JSON-Daten.") from None
    except (zipfile.BadZipFile, zipfile.LargeZipFile, EOFError, zlib.error):
        raise BackupError("Die Datei ist kein gültiges, unbeschädigtes ZIP-Backup.") from None
    except (RuntimeError, NotImplementedError):
        raise BackupError("Das Archivformat wird nicht unterstützt; keine Entschlüsselung möglich.") from None
    except OSError:
        raise BackupError("Die Sicherungsdatei konnte nicht gelesen werden.") from None
