"""Zusätzliche Paketprüfung unter Linux; kein Ersatz für Windows-Praxistests."""
from pathlib import Path
import os
import subprocess

import pytest
from test_scripts import installer

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("existing", [False, True])
def test_online_installer_uses_only_local_venv(tmp_path, monkeypatch, existing):
    module = installer()
    root = tmp_path / "Windows Test Ä mit Leerzeichen"
    root.mkdir()
    interpreter = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if existing:
        interpreter.parent.mkdir(parents=True)
        interpreter.touch()
    created = []
    class Builder:
        def __init__(self, with_pip):
            assert with_pip
        def create(self, target):
            created.append(target)
    monkeypatch.setattr(module, "ROOT", root)
    monkeypatch.setattr(module.venv, "EnvBuilder", Builder)
    calls = []
    monkeypatch.setattr(module.subprocess, "run", lambda args, **kw: calls.append((args, kw)))
    assert module.main(online=True) == 0
    assert created == ([] if existing else [root / ".venv"])
    assert len(calls) == 4
    assert all(args[0] == str(interpreter) for args, kw in calls)
    for args, kw in calls:
        if "pip" in args:
            assert "--index-url" in args and "https://pypi.org/simple" in args
            assert "--no-index" not in args and "--user" not in args
            assert kw["env"]["PIP_NO_INDEX"] == "0"
            assert kw["check"]
    assert not (root / "wheelhouse").exists()


def test_online_installer_reports_failure(tmp_path, monkeypatch, capsys):
    module = installer()
    interpreter = tmp_path / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    interpreter.parent.mkdir(parents=True)
    interpreter.touch()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])
    monkeypatch.setattr(module.subprocess, "run", fail)
    assert module.main(online=True) == 1
    assert "[FEHLER]" in capsys.readouterr().out


def test_batch_package_paths_and_download_separation():
    install = (ROOT / "install.bat").read_bytes()
    start = (ROOT / "start.bat").read_bytes()
    for content in (install, start):
        assert b'cd /d "%~dp0"' in content
        assert b'DisableDelayedExpansion' in content
        assert b'pause' in content
        assert b'\n' not in content.replace(b'\r\n', b'')
        assert b'/home/' not in content
    assert install.count(b'"scripts\\install_local.py" --online') == 3
    assert b'".venv\\Scripts\\python.exe" "scripts\\launch.py"' in start
    assert b'--online' not in start and b' -m pip ' not in start
    assert (ROOT / "scripts/install_local.py").is_file()
    assert (ROOT / "scripts/launch.py").is_file()
