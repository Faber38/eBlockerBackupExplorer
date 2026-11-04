"""Lokaler Desktop-Einstiegspunkt; keine automatischen Dateiöffnungen."""
import sys


def main() -> int:
    from PySide6.QtWidgets import QApplication
    from .gui import MainWindow

    app = QApplication([sys.argv[0]])
    app.setApplicationName("eBlocker Backup Explorer")
    app.setApplicationVersion("0.1.0")
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
