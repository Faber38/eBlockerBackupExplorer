"""Native, ausschließlich lesende Qt-Oberfläche für Linux und Windows."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QFileDialog, QFrame, QHeaderView, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox, QPushButton,
    QSizePolicy, QStyle, QSplitter, QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit,
    QVBoxLayout, QWidget,
)

from . import __version__
from .backup_reader import Backup, BackupError, read_backup
from .exporter import export_apps

PRIVACY = (
    "Dieses Programm liest ausschließlich App- und Webseitenfreigaben aus "
    "eBlocker-Sicherungsdateien.\n"
    "Passwörter, Zertifikate, private Schlüssel und andere sensible Backup-Inhalte "
    "werden nicht ausgelesen.\n"
    "Alle Daten bleiben lokal. Die Sicherungsdatei wird nicht verändert."
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.backup: Backup | None = None
        self.displayed = [[], []]
        self.setWindowTitle("eBlocker Backup Explorer · 0.1.0")
        self.resize(1180, 760)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        title = QLabel("eBlocker Backup Explorer")
        title.setObjectName("title")
        layout.addWidget(title)

        bar_widget = QWidget()
        bar_widget.setObjectName("backupBar")
        bar = QHBoxLayout(bar_widget)
        bar.setContentsMargins(14, 9, 14, 9)
        self.open_button = self.make_button("Backup öffnen …", self.choose_backup)
        self.open_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        bar.addWidget(self.open_button)
        self.info = QLabel("Keine Sicherung geöffnet")
        self.info.setTextFormat(Qt.TextFormat.PlainText)
        self.info.setWordWrap(True)
        self.info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bar.addWidget(self.info, 1)
        self.about_button = self.make_button("Über", self.show_about)
        self.about_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation))
        bar.addWidget(self.about_button)
        self.exit_button = self.make_button("Beenden", self.close)
        self.exit_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))
        bar.addWidget(self.exit_button)
        layout.addWidget(bar_widget)

        body = QHBoxLayout()
        body.setSpacing(0)
        navigation = QWidget()
        navigation.setObjectName("navigation")
        nav_layout = QVBoxLayout(navigation)
        nav_layout.setContentsMargins(8, 12, 8, 12)
        self.nav_buttons = []
        for index, label in enumerate(("Apps", "Webseiten")):
            button = self.make_button(label, lambda checked=False, i=index: self.select_tab(i))
            button.setCheckable(True)
            button.setObjectName("navButton")
            self.nav_buttons.append(button)
            nav_layout.addWidget(button)
        nav_layout.addStretch()
        body.addWidget(navigation)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 12, 14, 10)
        content_layout.setSpacing(10)
        search_bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Apps, Beschreibungen, Domains oder IPs durchsuchen …")
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("Suche")
        self.search.textChanged.connect(self.refresh)
        search_bar.addWidget(self.search, 1)
        self.scope = QComboBox()
        self.scope.addItems(["Alle Apps", "Nur eigene Apps", "Nur integrierte Apps"])
        self.scope.setAccessibleName("App-Filter")
        self.scope.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.scope.currentIndexChanged.connect(self.refresh)
        search_bar.addWidget(self.scope)
        content_layout.addLayout(search_bar)

        split = QSplitter(Qt.Orientation.Vertical)
        split.setChildrenCollapsible(False)
        self.tabs = QTabWidget()
        self.tables = []
        for title_text in ("Vertrauenswürdige Apps", "Vertrauenswürdige Webseiten"):
            table = QTableWidget(0, 6)
            table.setHorizontalHeaderLabels(["Name", "Beschreibung", "Erlaubte Domains/IPs", "Anzahl", "Status", "Typ"])
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
            table.setAlternatingRowColors(True)
            table.setShowGrid(False)
            table.setTextElideMode(Qt.TextElideMode.ElideNone)
            table.setWordWrap(False)
            table.verticalHeader().hide()
            table.verticalHeader().setDefaultSectionSize(table.fontMetrics().height() + 16)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setStretchLastSection(True)
            table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            table.itemSelectionChanged.connect(self.show_details)
            self.tables.append(table)
            self.tabs.addTab(table, title_text)
        self.tabs.currentChanged.connect(self.tab_changed)
        split.addWidget(self.tabs)

        detail = QFrame()
        detail.setObjectName("detailPanel")
        box = QVBoxLayout(detail)
        self.detail_heading = QLabel("Details · App oder Webseite auswählen")
        self.detail_heading.setTextFormat(Qt.TextFormat.PlainText)
        self.detail_heading.setWordWrap(True)
        self.detail_heading.setObjectName("detailHeading")
        box.addWidget(self.detail_heading)
        detail_row = QHBoxLayout()
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setFrameShape(QFrame.Shape.NoFrame)
        self.detail_text.setMinimumWidth(150)
        detail_row.addWidget(self.detail_text, 4)
        domains_box = QVBoxLayout()
        self.domain_heading = QLabel("Domains/IPs (0)")
        domains_box.addWidget(self.domain_heading)
        self.domains = QListWidget()
        self.domains.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.domains.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.domains.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.domains.setAccessibleName("Vollständige Domainliste")
        domains_box.addWidget(self.domains)
        detail_row.addLayout(domains_box, 5)
        domain_actions = QVBoxLayout()
        domain_actions.addStretch()
        self.copy_domain_button = self.make_button("Auswahl kopieren", self.copy_selected_domains)
        self.copy_domain_button.setToolTip("Ausgewählte Domains/IPs aus der Detailansicht kopieren")
        domain_actions.addWidget(self.copy_domain_button)
        self.copy_app_button = self.make_button("Alle kopieren", self.copy_app_domains)
        self.copy_app_button.setToolTip("Vollständige Domain-/IP-Liste dieser App kopieren")
        domain_actions.addWidget(self.copy_app_button)
        domain_actions.addStretch()
        detail_row.addLayout(domain_actions)
        box.addLayout(detail_row, 1)
        split.addWidget(detail)
        split.setSizes([320, 180])
        content_layout.addWidget(split, 1)

        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)
        self.copy_entries_button = self.make_button("Auswahl kopieren", self.copy_selected_entries)
        self.copy_entries_button.setToolTip("Domains/IPs der ausgewählten Tabellenzeilen kopieren")
        action_bar.addWidget(self.copy_entries_button)
        self.copy_visible_button = self.make_button("Alle angezeigten", self.copy_visible_domains)
        self.copy_visible_button.setToolTip("Alle Domains/IPs im aktiven, gefilterten Reiter kopieren")
        action_bar.addWidget(self.copy_visible_button)
        action_bar.addStretch()
        for format in ("txt", "csv"):
            button = self.make_button(f"{format.upper()} exportieren …",
                                      lambda checked=False, f=format: self.choose_export(f))
            button.setToolTip("Angezeigte Einträge des aktiven Reiters exportieren")
            action_bar.addWidget(button)
        content_layout.addLayout(action_bar)
        note = QLabel("Kopieren und Export: aktiver Reiter und aktuelle Suche.")
        note.setObjectName("hint")
        note.setWordWrap(True)
        content_layout.addWidget(note)

        privacy_panel = QFrame()
        privacy_panel.setObjectName("privacyPanel")
        privacy_layout = QHBoxLayout(privacy_panel)
        privacy_title = QLabel("Datenschutz\nund Sicherheit")
        privacy_title.setObjectName("privacyTitle")
        privacy_layout.addWidget(privacy_title)
        privacy = QLabel(PRIVACY)
        privacy.setWordWrap(True)
        privacy_layout.addWidget(privacy, 1)
        content_layout.addWidget(privacy_panel)
        body.addWidget(content, 1)
        layout.addLayout(body, 1)
        self.statusBar().addPermanentWidget(QLabel("Offline  |  Nur lesender Zugriff"))
        self.statusBar().showMessage("Bereit")
        self.setStyleSheet("""
            QWidget { background: #f8f9fb; color: #202731; }
            QLabel#title { background: #f47700; color: white; font-size: 19pt;
                           font-weight: bold; padding: 13px 22px; }
            QWidget#backupBar { border-bottom: 1px solid #d5dce5; }
            QWidget#navigation { background: #eaf0f6; border-right: 1px solid #d5dce5; }
            QPushButton { background: #fafbfc; border: 1px solid #b8c1cc;
                          border-radius: 4px; padding: 5px 12px; }
            QPushButton:hover { border-color: #e77a16; background: #fff1df; }
            QPushButton:focus { border: 1px solid #e77a16; }
            QPushButton#navButton { border: none; text-align: left; padding: 8px 16px; }
            QPushButton#navButton:checked { background: #f47700; color: white; font-weight: bold; }
            QLineEdit, QComboBox { background: white; border: 1px solid #b8c1cc;
                                  border-radius: 4px; padding: 5px 8px; }
            QTextEdit, QListWidget, QTableWidget { background: white;
                alternate-background-color: #f4f6f9; selection-background-color: #ffdab0;
                selection-color: #202731; border: 1px solid #d5dce5; }
            QTextEdit { background: transparent; border: none; }
            QListWidget::item { padding: 3px; }
            QHeaderView::section { background: #eaf0f6; padding: 7px 10px;
                                   border: 0px; font-weight: bold; }
            QTableWidget::item { padding: 4px 8px; border-bottom: 1px solid #edf0f4; }
            QTabWidget::pane { background: white; border: 1px solid #cbd3de; border-radius: 4px; }
            QTabBar::tab { background: #e8edf3; padding: 8px 14px;
                          border: 1px solid #d5dce5; border-top-left-radius: 5px;
                          border-top-right-radius: 5px; }
            QTabBar::tab:selected { background: #f47700; color: white; font-weight: bold; }
            QFrame#detailPanel { border: 1px solid #cbd3de; border-radius: 5px; }
            QLabel#detailHeading { font-weight: bold; color: #b95000; }
            QLabel#hint { color: #596474; }
            QFrame#privacyPanel { background: #fff2de; border: 1px solid #f3c58b; border-radius: 5px; }
            QFrame#privacyPanel QLabel { background: transparent; }
            QLabel#privacyTitle { color: #963c00; font-weight: bold; padding: 6px 12px 6px 2px; }
            QStatusBar { border-top: 1px solid #d5dce5; }
        """)
        self.tab_changed()

    def make_button(self, text, handler):
        button = QPushButton(text)
        button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        button.clicked.connect(handler)
        return button

    def show_about(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Über eBlocker Backup Explorer")
        dialog.setIcon(QMessageBox.Icon.Information)
        dialog.setTextFormat(Qt.TextFormat.PlainText)
        dialog.setText(
            f"eBlocker Backup Explorer\nVersion {__version__}\n\n"
            "Entwickler: Holger Mangold\n"
            "GitHub: Faber38/eBlockerBackupExplorer\n\n"
            "Beschreibung:\n"
            "Ein unabhängiges Werkzeug zum lokalen Auslesen von Apps, Domains und "
            "Webseitenfreigaben aus eBlocker-Backups.\n\n"
            "Unterstützte Systeme:\nLinux und Windows; macOS (ungetestet)\n\n"
            "Datenschutz:\n"
            "• Keine Passwörter erforderlich\n"
            "• Keine Zertifikate oder Schlüssel auslesen\n"
            "• Keine Netzwerkverbindungen\n"
            "• Backups werden nicht verändert\n"
            "• Ausschließlich lesender Zugriff\n\n"
            "Hinweis:\n"
            "Dies ist ein unabhängiges Community-Projekt und keine offizielle eBlocker-Anwendung."
        )
        dialog.setStandardButtons(QMessageBox.StandardButton.Close)
        dialog.button(QMessageBox.StandardButton.Close).setText("Schließen")
        try:
            dialog.exec()
        finally:
            dialog.deleteLater()

    def select_tab(self, index):
        self.tabs.setCurrentIndex(index)
        self.tab_changed()

    def tab_changed(self):
        for index, button in enumerate(self.nav_buttons):
            button.setChecked(index == self.tabs.currentIndex())
        self.show_details()

    def choose_backup(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "eBlocker-Sicherung öffnen", "", "eBlocker-Sicherung (*.eblcfg)")
        if filename:
            self.load_backup(Path(filename))

    def load_backup(self, path: Path) -> bool:
        try:
            backup = read_backup(path)
        except BackupError as exc:
            # Alte Daten entfernen, damit kein fehlgeschlagener Import verwechselt wird.
            self.backup = None
            self.info.setText("Keine Sicherung geöffnet")
            self.refresh()
            QMessageBox.warning(self, "Sicherung konnte nicht geöffnet werden", str(exc))
            return False
        self.backup = backup
        own = sum(not a.builtin and not a.website for a in backup.apps)
        websites = sum(a.website for a in backup.apps)
        self.info.setText(f"Backup: {backup.path.name}  |  Version: {backup.version}\n"
                          f"Eigene Apps: {own} · Eigene Webseiten: {websites}")
        self.refresh()
        return True

    def refresh(self):
        apps = self.backup.apps if self.backup else ()
        query = self.search.text()
        scope = self.scope.currentIndex()
        self.displayed = [
            [a for a in apps if not a.website and a.matches(query)
             and (scope == 0 or (scope == 1 and not a.builtin) or (scope == 2 and a.builtin))],
            [a for a in apps if a.website and a.matches(query)],
        ]
        for table, entries in zip(self.tables, self.displayed):
            table.blockSignals(True)
            table.setRowCount(0)
            table.setRowCount(len(entries))
            for row, app in enumerate(entries):
                values = (app.name, app.description,
                          (app.domains[0] if app.domains else "—")
                          + (f"  (+{len(app.domains) - 1} weitere)" if len(app.domains) > 1 else ""),
                          str(len(app.domains)), app.status, app.kind)
                for column, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    if column == 4:
                        item.setForeground(QColor("#17743a" if app.enabled else "#656b75"))
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    if column == 3:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    table.setItem(row, column, item)
            table.resizeColumnsToContents()
            # Vollständige Werte bleiben horizontal scrollbar, keine Ellipsen.
            table.blockSignals(False)
        for index, label in enumerate(("Vertrauenswürdige Apps", "Vertrauenswürdige Webseiten")):
            self.tabs.setTabText(index, f"{label} ({len(self.displayed[index])})")
        self.show_details()
        self.statusBar().showMessage(f"Gefiltert: {len(self.displayed[0])} Apps · "
                                     f"{len(self.displayed[1])} Webseiten")

    def active_entries(self):
        return self.displayed[self.tabs.currentIndex()]

    def selected_entries(self):
        table = self.tables[self.tabs.currentIndex()]
        entries = self.active_entries()
        return [entries[i.row()] for i in sorted(table.selectionModel().selectedRows(), key=lambda i: i.row())]

    def show_details(self):
        self.detail_text.clear()
        self.domains.clear()
        self.detail_heading.setText("Details · App oder Webseite auswählen")
        self.domain_heading.setText("Domains/IPs (0)")
        selected = self.selected_entries()
        if selected:
            app = selected[0]
            self.detail_heading.setText(f"Details: {app.name}")
            self.domain_heading.setText(f"Domains/IPs ({len(app.domains)})")
            self.detail_text.setPlainText(f"{app.name}\nBeschreibung: {app.description}\n"
                                         f"Status: {app.status}\nTyp: {app.kind}")
            self.domains.addItems(app.domains)

    def copy_text(self, values):
        text = "\n".join(dict.fromkeys(values))
        if text:
            QApplication.clipboard().setText(text)
            self.statusBar().showMessage("In die Zwischenablage kopiert")

    def copy_selected_domains(self):
        self.copy_text([item.text() for item in self.domains.selectedItems()])

    def copy_app_domains(self):
        self.copy_text([self.domains.item(i).text() for i in range(self.domains.count())])

    def copy_selected_entries(self):
        self.copy_text([d for a in self.selected_entries() for d in a.domains])

    def copy_visible_domains(self):
        self.copy_text([d for a in self.active_entries() for d in a.domains])

    def choose_export(self, format: str):
        if self.backup is None or not self.active_entries():
            QMessageBox.information(self, "Export", "Keine angezeigten Einträge zum Exportieren.")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Angezeigte Einträge exportieren (neue Datei)", f"freigaben.{format}",
            f"{format.upper()} (*.{format})")
        if not filename:
            return
        path = Path(filename)
        if not path.suffix:
            path = path.with_suffix("." + format)
        try:
            export_apps(path, self.active_entries(), format, self.backup.path)
        except (OSError, ValueError):
            QMessageBox.warning(self, "Export fehlgeschlagen",
                                "Bitte eine neue, beschreibbare Datei mit passender Endung wählen. "
                                "Vorhandene Dateien werden nicht überschrieben.")
            return
        self.statusBar().showMessage("Angezeigte Einträge als UTF-8 exportiert")
