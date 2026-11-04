"""Mac-Voraussetzungen und Shell-Abläufe unter Linux; keine macOS-Praxisabnahme."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def checker(tmp_path):
    spec = importlib.util.spec_from_file_location("check_macos", ROOT / "scripts/check_macos.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = tmp_path
    module.sys = SimpleNamespace(platform="darwin", version_info=(3, 12),
                                 prefix=str(tmp_path / ".venv"), base_prefix="/synthetic-python")
    module.platform = SimpleNamespace(machine=lambda: "arm64")
    module.struct = SimpleNamespace(calcsize=lambda _: 8)
    module.importlib = SimpleNamespace(import_module=lambda _: SimpleNamespace(__version__="6.11.2"))
    return module


@pytest.mark.parametrize("architecture", ["arm64", "x86_64"])
def test_supported_mac_python_architectures(checker, architecture):
    checker.platform.machine = lambda: architecture
    assert checker.main() == 0
    assert checker.main(runtime=True) == 0


@pytest.mark.parametrize("field,value,message", [
    ("platform", "linux", "macOS"),
    ("version_info", (3, 9), "Python ab 3.10"),
    ("prefix", "/foreign-venv", "lokale .venv"),
])
def test_mac_invalid_environment(checker, capsys, field, value, message):
    setattr(checker.sys, field, value)
    assert checker.main(runtime=True) == 2
    assert message in capsys.readouterr().out


@pytest.mark.parametrize("machine,bits", [("arm64", 4), ("unsupported", 8)])
def test_mac_unsupported_architecture(checker, machine, bits):
    checker.platform.machine = lambda: machine
    checker.struct.calcsize = lambda _: bits
    assert checker.main() == 2


@pytest.mark.parametrize("version", ["6.5.0", "7.0.0", "invalid"])
def test_mac_rejects_incompatible_qt(checker, version):
    checker.importlib.import_module = lambda _: SimpleNamespace(__version__=version)
    assert checker.main(runtime=True) == 3


def test_mac_missing_qt_library(checker, capsys):
    def missing(_):
        raise OSError("synthetic missing library")
    checker.importlib.import_module = missing
    assert checker.main(runtime=True) == 3
    assert "PySide6/Qt" in capsys.readouterr().out


@pytest.mark.skipif(os.name == "nt", reason="Shell-Abläufe benötigen Bash")
def test_mac_start_paths_errors_and_no_install(tmp_path):
    root = tmp_path / "Mac Projekt Ä mit Leerzeichen"
    root.mkdir()
    script = root / "start-mac.sh"
    shutil.copyfile(ROOT / "start-mac.sh", script)

    def run():
        return subprocess.run(["bash", str(script)], cwd=tmp_path, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True)

    result = run()
    assert result.returncode != 0 and "install-mac.sh" in result.stderr
    interpreter = root / ".venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text('#!/bin/sh\nprintf "%s|%s\\n" "$PWD" "$*" >> calls.txt\nexit 0\n')
    interpreter.chmod(0o755)
    result = run()
    assert result.returncode == 0
    assert (root / "calls.txt").read_text().splitlines() == [
        f"{root}|scripts/check_macos.py --runtime", f"{root}|scripts/launch.py"]
    interpreter.write_text('#!/bin/sh\nexit 3\n')
    result = run()
    assert result.returncode != 0 and "nicht startbereit" in result.stderr
    interpreter.write_text('#!/bin/sh\ncase "$1" in *launch.py) exit 7;; esac\nexit 0\n')
    result = run()
    assert result.returncode != 0 and "Start fehlgeschlagen" in result.stderr


@pytest.mark.skipif(os.name == "nt", reason="Shell-Abläufe benötigen Bash")
@pytest.mark.parametrize("existing", [False, True])
def test_mac_install_repeated_from_foreign_directory(tmp_path, existing):
    root = tmp_path / "Mac Installation Ä mit Leerzeichen"
    root.mkdir()
    script = root / "install-mac.sh"
    shutil.copyfile(ROOT / "install-mac.sh", script)
    bin_dir = tmp_path / "python-bin"
    bin_dir.mkdir()
    fake = bin_dir / "python3"
    fake.write_text('''#!/bin/sh
printf '%s|%s|%s\\n' "$PWD" "$0" "$*" >> calls.txt
if [ "$1" = scripts/install_local.py ] && [ ! -f .venv/bin/python ]; then
    mkdir -p .venv/bin
    cp "$0" .venv/bin/python
fi
exit 0
''')
    fake.chmod(0o755)
    if existing:
        (root / ".venv/bin").mkdir(parents=True)
        shutil.copy2(fake, root / ".venv/bin/python")
    env = os.environ.copy()
    env["PATH"] = str(bin_dir) + os.pathsep + env["PATH"]
    for _ in range(2):
        result = subprocess.run(["bash", str(script)], cwd=tmp_path, env=env,
                                stdin=subprocess.DEVNULL, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    calls = (root / "calls.txt").read_text().splitlines()
    assert len(calls) == 6
    assert all(line.startswith(str(root) + "|") for line in calls)
    assert all("|.venv/bin/python|" in line for line in calls[3:])
    assert [line.split("|")[-1] for line in calls] == [
        "scripts/check_macos.py", "scripts/install_local.py", "scripts/check_macos.py --runtime"] * 2


@pytest.mark.skipif(os.name == "nt", reason="Shell-Abläufe benötigen Bash")
def test_mac_scripts_reject_symlink_environment(tmp_path):
    (tmp_path / ".venv").symlink_to(tmp_path / "foreign")
    for name in ("install-mac.sh", "start-mac.sh"):
        shutil.copyfile(ROOT / name, tmp_path / name)
        result = subprocess.run(["bash", str(tmp_path / name)], stdin=subprocess.DEVNULL,
                                capture_output=True, text=True)
        assert result.returncode != 0
        assert "[FEHLER]" in result.stderr
