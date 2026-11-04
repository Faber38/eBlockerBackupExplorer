import importlib.util
from pathlib import Path
import os
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parent.parent


def installer():
    spec = importlib.util.spec_from_file_location("install_local", ROOT / "scripts/install_local.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_offline_installer_missing_wheels(tmp_path, monkeypatch, capsys):
    module = installer()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    assert module.main() == 2
    assert "Offline-Pakete fehlen" in capsys.readouterr().out
    assert not (tmp_path / ".venv").exists()


def test_repeated_installer_uses_only_local_env(tmp_path, monkeypatch):
    module = installer()
    root = tmp_path / "Projekt mit Leerzeichen Ä"
    interpreter = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    interpreter.parent.mkdir(parents=True)
    interpreter.touch()
    (root / "wheelhouse").mkdir()
    monkeypatch.setattr(module, "ROOT", root)
    calls = []
    monkeypatch.setattr(module.subprocess, "run", lambda args, **kwargs: calls.append((args, kwargs)))
    for _ in range(2):
        assert module.main() == 0
    assert len(calls) == 8
    assert all(call[0][0] == str(interpreter) for call in calls)
    for args, kwargs in calls:
        if "pip" in args:
            assert "--no-index" in args and "--isolated" in args
            assert kwargs["env"]["PIP_NO_INDEX"] == "1"
            assert str(root / "wheelhouse") in args


@pytest.mark.skipif(os.name == "nt", reason="Linux-Shellskripte")
def test_start_script_from_other_directory_with_spaces(tmp_path):
    root = tmp_path / "Projekt mit Leerzeichen"
    root.mkdir()
    shutil.copyfile(ROOT / "start.sh", root / "start.sh")
    missing = subprocess.run(["bash", str(root / "start.sh")], cwd=tmp_path, stdin=subprocess.DEVNULL,
                             capture_output=True, text=True)
    assert missing.returncode != 0 and "Lokale .venv fehlt" in missing.stderr
    bin_dir = root / ".venv/bin"
    bin_dir.mkdir(parents=True)
    fake = bin_dir / "python"
    fake.write_text('#!/bin/sh\nprintf "%s\\n" "$PWD" "$1"\nexit 0\n')
    fake.chmod(0o755)
    result = subprocess.run(["bash", str(root / "start.sh")], cwd=tmp_path,
                            capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.splitlines() == [str(root), "scripts/launch.py"]
    fake.write_text('#!/bin/sh\nexit 7\n')
    failed = subprocess.run(["bash", str(root / "start.sh")], cwd=tmp_path, stdin=subprocess.DEVNULL,
                            capture_output=True, text=True)
    assert failed.returncode != 0 and "Start fehlgeschlagen" in failed.stderr
