import hashlib
import zipfile

import pytest
from eblocker_backup_explorer.backup_reader import APP_MEMBER, BackupError, read_backup


def test_reads_only_app_member_and_preserves_source(make_backup, module, monkeypatch):
    path = make_backup({"modules": [module]}, extra={
        "META-INF/MANIFEST.MF": "FORBIDDEN", "eblocker-config/httpsKeys.json": "FORBIDDEN",
        "eblocker-config/devices.json": "FORBIDDEN", "eblocker-config/network.json": "FORBIDDEN",
        "eblocker-config/dns.json": "FORBIDDEN", "eblocker-config/openVpnServer.json": "FORBIDDEN"})
    before = hashlib.sha256(path.read_bytes()).digest()
    original = zipfile.ZipFile.open
    opened = []
    def guarded(self, name, mode="r", *args, **kwargs):
        filename = name.filename if isinstance(name, zipfile.ZipInfo) else name
        assert filename == APP_MEMBER and mode == "r"
        opened.append(filename)
        return original(self, name, mode, *args, **kwargs)
    monkeypatch.setattr(zipfile.ZipFile, "open", guarded)
    backup = read_backup(path)
    assert len(backup.apps) == 1 and opened == [APP_MEMBER]
    assert "Nicht ermittelbar" in backup.version
    assert hashlib.sha256(path.read_bytes()).digest() == before


@pytest.mark.parametrize("sections", [[], ["users", "dns", "network", "openVpnClients"]])
def test_optional_other_sections(make_backup, module, sections):
    path = make_backup({"modules": [module]}, extra={f"eblocker-config/{s}.json": "INVALID" for s in sections})
    assert len(read_backup(path).apps) == 1


def test_empty_archive(make_backup):
    with pytest.raises(BackupError, match="fehlt"):
        read_backup(make_backup())


def test_missing_apps(make_backup):
    with pytest.raises(BackupError, match="fehlt"):
        read_backup(make_backup(extra={"other.json": "{}"}))


def test_invalid_zip(tmp_path):
    path = tmp_path / "invalid.eblcfg"
    path.write_bytes(b"not a ZIP")
    with pytest.raises(BackupError, match="ZIP"):
        read_backup(path)


@pytest.mark.parametrize("raw", [b"{bad SECRET", b"\xff", b'{"modules":[],"modules":[]}', b'NaN', b'{}'])
def test_invalid_json(make_backup, raw):
    with pytest.raises(BackupError) as exc:
        read_backup(make_backup(raw=raw))
    assert "SECRET" not in str(exc.value)


def test_empty_modules(make_backup):
    assert read_backup(make_backup({"modules": []})).apps == ()


def test_duplicate_archive_member(make_backup):
    path = make_backup({"modules": []})
    with pytest.warns(UserWarning):
        with zipfile.ZipFile(path, "a") as z:
            z.writestr(APP_MEMBER, "{}")
    with pytest.raises(BackupError, match="mehrere"):
        read_backup(path)


def test_size_limit(make_backup, monkeypatch):
    monkeypatch.setattr("eblocker_backup_explorer.backup_reader.MAX_APP_BYTES", 4)
    with pytest.raises(BackupError, match="Größenlimit"):
        read_backup(make_backup({"modules": []}))


def test_wrong_extension(tmp_path):
    with pytest.raises(BackupError, match="eblcfg"):
        read_backup(tmp_path / "data.zip")


def test_encrypted_member_rejected_without_open(make_backup, monkeypatch):
    path = make_backup({"modules": []})
    original = zipfile.ZipFile.infolist
    def encrypted(self):
        entries = original(self)
        for entry in entries:
            entry.flag_bits |= 1
        return entries
    monkeypatch.setattr(zipfile.ZipFile, "infolist", encrypted)
    def forbidden(*args, **kwargs):
        raise AssertionError("Verschlüsselte Inhalte dürfen nicht geöffnet werden")
    monkeypatch.setattr(zipfile.ZipFile, "open", forbidden)
    with pytest.raises(BackupError, match="Verschlüsselte"):
        read_backup(path)
