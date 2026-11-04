from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from eblocker_backup_explorer.app_parser import WEBSITE_MODULE
from eblocker_backup_explorer.gui import MainWindow, PRIVACY


@pytest.fixture
def window(qapp):
    window = MainWindow()
    yield window
    window.close()
    window.deleteLater()
    qapp.processEvents()


def test_open_dialog_search_copy_export(window, make_backup, module, monkeypatch, tmp_path):
    path = make_backup({"modules": [module]})
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(path), ""))
    window.choose_backup()
    assert window.tables[0].rowCount() == 1
    assert path.name in window.info.text()
    window.search.setText("TWO.EXAMPLE")
    window.tables[0].selectRow(0)
    assert window.domains.count() == 3
    window.domains.item(1).setSelected(True)
    window.copy_selected_domains()
    assert QApplication.clipboard().text() == "two.example"
    window.copy_app_domains()
    assert QApplication.clipboard().text() == "one.example\ntwo.example\n192.0.2.1"
    window.copy_selected_entries()
    assert "one.example" in QApplication.clipboard().text()
    window.copy_visible_domains()
    assert "192.0.2.1" in QApplication.clipboard().text()
    target = tmp_path / "sichtbar.csv"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(target), ""))
    window.choose_export("csv")
    assert "two.example" in target.read_text(encoding="utf-8")
    window.search.setText("not-found.example")
    assert window.tables[0].rowCount() == 0 and window.domains.count() == 0
    assert "Alle Daten bleiben lokal" in PRIVACY


def test_websites_builtin_and_filtered_export(window, make_backup, module, monkeypatch, tmp_path):
    site = dict(module, id=9998, name=WEBSITE_MODULE, builtin=True, hidden=True,
                whitelistedDomains=["web.example"], whitelistedIPs=[])
    builtin = dict(module, id=5000, name="Integrierte App", builtin=True)
    window.load_backup(make_backup({"modules": [module, site, builtin]}))
    window.scope.setCurrentIndex(1)
    assert window.tables[0].rowCount() == 1
    window.scope.setCurrentIndex(2)
    assert window.tables[0].rowCount() == 1
    assert window.active_entries()[0].builtin
    window.tabs.setCurrentIndex(1)
    assert len(window.active_entries()) == 1
    target = tmp_path / "web.txt"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(target), ""))
    window.choose_export("txt")
    assert "web.example" in target.read_text() and "one.example" not in target.read_text()


def test_long_domain_list_plain_text(window, make_backup, module, qapp):
    long_domain = "long-subdomain-" * 15 + ".example"
    module.update(name="<b>Kein HTML</b>", whitelistedDomains=[long_domain] + [f"d{i}.example" for i in range(500)])
    window.load_backup(make_backup({"modules": [module]}))
    window.show()
    window.tables[0].selectRow(0)
    qapp.processEvents()
    assert "<b>Kein HTML</b>" in window.detail_text.toPlainText()
    assert window.domains.item(0).text() == long_domain
    assert window.domains.textElideMode() == Qt.TextElideMode.ElideNone
    assert window.domains.horizontalScrollBar().maximum() > 0
    assert window.domains.verticalScrollBar().maximum() > 0


def test_cancel_dialog_preserves_state(window, monkeypatch):
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: ("", ""))
    window.choose_backup()
    assert window.backup is None


def test_failed_open_clears_previous_data(window, make_backup, module, monkeypatch):
    window.load_backup(make_backup({"modules": [module]}))
    messages = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: messages.append(args[2]))
    assert not window.load_backup(Path("missing.eblcfg"))
    assert window.backup is None and window.tables[0].rowCount() == 0
    assert len(messages) == 1


def test_sidebar_navigation_and_compact_copy_buttons(window, make_backup, module, qapp):
    window.load_backup(make_backup({"modules": [module]}))
    window.show()
    window.tables[0].selectRow(0)
    window.copy_app_button.click()
    assert QApplication.clipboard().text() == "one.example\ntwo.example\n192.0.2.1"
    window.domains.item(0).setSelected(True)
    window.copy_domain_button.click()
    assert QApplication.clipboard().text() == "one.example"
    window.nav_buttons[1].click()
    assert window.tabs.currentIndex() == 1 and window.nav_buttons[1].isChecked()
    window.nav_buttons[1].click()
    assert window.nav_buttons[1].isChecked()
    window.tabs.setCurrentIndex(0)
    assert window.nav_buttons[0].isChecked() and not window.nav_buttons[1].isChecked()


@pytest.mark.parametrize("width,height", [(900, 700), (1180, 760), (1500, 950)])
def test_layout_readability_and_readonly_status(window, make_backup, module, qapp, width, height):
    from PySide6.QtWidgets import QAbstractItemView, QPushButton
    window.load_backup(make_backup({"modules": [module]}))
    window.resize(width, height)
    window.show()
    qapp.processEvents()
    assert window.width() == width
    assert window.search.mapTo(window, window.search.rect().topLeft()).y() == window.scope.mapTo(
        window, window.scope.rect().topLeft()).y()
    for button in window.findChildren(QPushButton):
        assert button.width() >= button.sizeHint().width()
        assert button.width() < width / 3
        assert button.height() >= button.sizeHint().height()
    for table in window.tables:
        assert table.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
        for column in range(table.columnCount()):
            header = table.horizontalHeaderItem(column)
            # Header padding is additional to the full text width.
            font = table.horizontalHeader().font()
            font.setBold(True)
            from PySide6.QtGui import QFontMetrics
            assert table.columnWidth(column) >= QFontMetrics(font).horizontalAdvance(header.text()) + 20
    assert window.tables[0].item(0, 4).text() == "Aktiviert"
    assert window.tables[0].cellWidget(0, 4) is None  # No interactive switch.
    assert window.tables[0].item(0, 3).text() == "3"


def test_about_modal_content_close_and_backup_unchanged(window, make_backup, module, qapp):
    import hashlib
    from PySide6.QtCore import QTimer

    path = make_backup({"modules": [module]})
    before = hashlib.sha256(path.read_bytes()).digest()
    window.load_backup(path)
    window.show()
    observed = {}

    def inspect_and_close():
        dialog = QApplication.activeModalWidget()
        observed["is_message_box"] = isinstance(dialog, QMessageBox)
        if isinstance(dialog, QMessageBox):
            observed["modal"] = dialog.isModal()
            observed["text"] = dialog.text()
            observed["format"] = dialog.textFormat()
            button = dialog.button(QMessageBox.StandardButton.Close)
            observed["close_label"] = button.text()
            button.click()
            observed["closed"] = not dialog.isVisible()

    QTimer.singleShot(0, inspect_and_close)
    window.about_button.click()
    assert observed["is_message_box"] and observed["modal"] and observed["closed"]
    assert observed["format"] == Qt.TextFormat.PlainText
    assert observed["close_label"] == "Schließen"
    for text in ("eBlocker Backup Explorer", "Version 0.1.0", "Entwickler: Holger Mangold",
                 "GitHub: Faber38/eBlockerBackupExplorer", "Linux und Windows; macOS (ungetestet)",
                 "Keine Passwörter erforderlich", "Keine Zertifikate oder Schlüssel auslesen",
                 "Keine Netzwerkverbindungen", "Backups werden nicht verändert",
                 "Ausschließlich lesender Zugriff", "keine offizielle eBlocker-Anwendung"):
        assert text in observed["text"]
    assert window.isVisible()
    assert hashlib.sha256(path.read_bytes()).digest() == before


def test_exit_button_closes_window_without_changing_backup(window, make_backup, module, qapp):
    import hashlib
    path = make_backup({"modules": [module]})
    before = hashlib.sha256(path.read_bytes()).digest()
    window.load_backup(path)
    window.show()
    qapp.processEvents()
    assert window.isVisible()
    assert window.about_button.parentWidget() == window.open_button.parentWidget()
    assert window.exit_button.parentWidget() == window.open_button.parentWidget()
    assert window.info.geometry().right() < window.about_button.geometry().left()
    assert window.about_button.geometry().right() < window.exit_button.geometry().left()
    assert not window.about_button.icon().isNull()
    assert not window.exit_button.icon().isNull()
    window.exit_button.click()
    qapp.processEvents()
    assert not window.isVisible()
    assert hashlib.sha256(path.read_bytes()).digest() == before
