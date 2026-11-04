"""Voraussetzungen der Mac-Skripte prüfen; keine Installation oder Netzwerkzugriffe."""
from pathlib import Path
import importlib
import platform
import struct
import sys

ROOT = Path(__file__).resolve().parent.parent


def main(runtime=False):
    if sys.platform != "darwin":
        print("[FEHLER] Diese Startskripte sind für macOS vorgesehen.")
        return 2
    if sys.version_info < (3, 10):
        print("[FEHLER] Python ab 3.10 erforderlich.")
        return 2
    if struct.calcsize("P") != 8 or platform.machine() not in ("arm64", "x86_64"):
        print("[FEHLER] Python in 64 Bit für Apple Silicon (arm64) oder Intel (x86_64) erforderlich.")
        return 2
    if runtime:
        if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
            print("[FEHLER] Bitte ausschließlich die lokale .venv verwenden: bash install-mac.sh")
            return 2
        try:
            pyside = importlib.import_module("PySide6")
            version = tuple(int(part) for part in pyside.__version__.split(".")[:2])
            if not (6, 6) <= version < (7, 0):
                raise ValueError
            importlib.import_module("PySide6.QtWidgets")
        except (ImportError, OSError, ValueError, AttributeError):
            print("[FEHLER] PySide6/Qt fehlt, ist nicht kompatibel oder kann nicht geladen werden. "
                  "Passende macOS-Wheels verwenden und bash install-mac.sh erneut ausführen.")
            return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main(runtime="--runtime" in sys.argv[1:]))
