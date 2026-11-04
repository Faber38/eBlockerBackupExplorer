import json
import os
import socket
import zipfile

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Netzwerkzugriff im Test verboten")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)


@pytest.fixture
def module():
    return dict(id=10001, name="Beispiel ÄÖÜ", description={"de": "Eigene Freigabe", "en": "Example"},
                whitelistedDomains=["one.example", "two.example", "one.example"],
                whitelistedIPs=["192.0.2.1"], enabled=True, builtin=False, hidden=False)


@pytest.fixture
def make_backup(tmp_path):
    def make(data=None, *, raw=None, extra=None, name="synthetisch.eblcfg"):
        path = tmp_path / name
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            if data is not None or raw is not None:
                archive.writestr("eblocker-config/appModules.json", raw if raw is not None else json.dumps(data))
            for key, value in (extra or {}).items():
                archive.writestr(key, value)
        return path
    return make


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    return app
