"""Reproduzierbarer GUI-Screenshot, ausschließlich mit synthetischen Daten.

Vom Projektverzeichnis: PYTHONPATH=src QT_QPA_PLATFORM=offscreen
.venv/bin/python scripts/preview_gui.py docs/screenshots/gui-linux.png
"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from eblocker_backup_explorer.app_parser import App
from eblocker_backup_explorer.backup_reader import Backup
from eblocker_backup_explorer.gui import MainWindow


def main():
    application = QApplication([])
    application.setStyle("Fusion")
    window = MainWindow()
    window.backup = Backup(Path("synthetisches-beispiel.eblcfg"), (
        App("Paketverfolgung", "Paketstatus und Liefertermine", ("pakete.example",), False, True),
        App("Banking", "Online-Banking – Beispiel", ("bank.example", "login.bank.example"), False, False),
        App("3D-Drucker", "Vorlagen und Modelle für den 3D-Drucker", (
            "modelle.example", "api.modelle.example", "druck.example"), True, False),
        App("Mediathek", "Filme und Serien", ("video.example", "bilder.example"), True, False),
        App("Musik", "Musikbibliothek", ("musik.example",), False, True),
        App("Fotografie", "Fotos und Alben", ("fotos.example",), True, True),
        App("Wetter", "Lokale Wettervorhersage", ("wetter.example",), True, False),
        App("wissen.example", "", ("wissen.example",), True, False, True),
        App("nachrichten.example", "", ("nachrichten.example",), True, False, True),
    ))
    window.info.setText("Backup: synthetisches-beispiel.eblcfg  |  Version: Nicht ermittelbar\n"
                        "Eigene Apps: 4  ·  Eigene Webseiten: 2")
    window.refresh()
    window.show()
    window.tables[0].selectRow(2)
    application.processEvents()
    target = Path(sys.argv[1])
    target.parent.mkdir(parents=True, exist_ok=True)
    if not window.grab().save(str(target)):
        raise RuntimeError("Screenshot konnte nicht gespeichert werden.")
    print(f"Qt-Plattform: {application.platformName()}; Größe: {window.width()} × {window.height()}; "
          f"Skalierung: {window.devicePixelRatioF():g}")
    window.close()


if __name__ == "__main__":
    main()
