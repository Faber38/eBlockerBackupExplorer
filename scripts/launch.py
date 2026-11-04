"""Startprüfung ohne Installation, Update, Netzwerk oder Protokolldateien."""
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parent.parent
    if sys.version_info < (3, 10) or Path(sys.prefix).resolve() != (root / ".venv").resolve():
        print("[FEHLER] Eine lokale .venv mit Python ab 3.10 ist erforderlich. Bitte install ausführen.")
        return 2
    try:
        from eblocker_backup_explorer.main import main as run
        return run()
    except ImportError:
        print("[FEHLER] Anwendung oder PySide6 fehlt. Bitte die lokale Installation mit install prüfen.")
        return 3
    except Exception:
        # Niemals unkontrolliert Archivdaten in einen Traceback schreiben.
        print("[FEHLER] Die Anwendung konnte nicht ordnungsgemäß ausgeführt werden.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
