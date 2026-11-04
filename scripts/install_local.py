"""Lokale Installation; Internetzugriff nur mit ausdrücklichem --online."""
from pathlib import Path
import os
import struct
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent.parent


def main(online=False):
    if sys.version_info < (3, 10) or (os.name == "nt" and struct.calcsize("P") != 8):
        print("[FEHLER] Python ab 3.10 erforderlich; unter Windows nur 64 Bit.")
        return 2
    target = ROOT / ".venv"
    interpreter = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    wheels = ROOT / "wheelhouse"
    if target.is_symlink():
        print("[FEHLER] .venv darf kein Verweis auf eine fremde Umgebung sein.")
        return 2
    if not online and not wheels.is_dir():
        print("[FEHLER] Offline-Pakete fehlen. Passende Wheels in wheelhouse bereitstellen; siehe README.")
        return 2
    try:
        if not interpreter.is_file():
            venv.EnvBuilder(with_pip=True).create(target)
        # Keine fremden oder verschobenen Umgebungen unbeabsichtigt verändern.
        subprocess.run([str(interpreter), "-c",
                        "import sys; from pathlib import Path; "
                        "assert sys.version_info >= (3,10); "
                        "assert sys.prefix != sys.base_prefix; "
                        "assert Path(sys.prefix).resolve() == Path(sys.argv[1]).resolve()",
                        str(target)], check=True)
        env = os.environ.copy()
        env.update(PIP_NO_INDEX="0" if online else "1", PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_CONFIG_FILE=os.devnull)
        common = [str(interpreter), "-m", "pip", "--isolated", "install", "--no-cache-dir"]
        if online:
            print("Installation: Fehlende Python-Pakete dürfen jetzt von PyPI geladen werden.", flush=True)
            common += ["--index-url", "https://pypi.org/simple"]
            if wheels.is_dir():
                common += ["--find-links", str(wheels)]
        else:
            common += ["--no-index", "--find-links", str(wheels)]
        subprocess.run(common + ["setuptools>=68", "wheel"], env=env, check=True)
        subprocess.run(common + ["--no-build-isolation", str(ROOT)], env=env, check=True)
        subprocess.run([str(interpreter), "-c", "import PySide6; import eblocker_backup_explorer"], check=True)
    except (OSError, subprocess.CalledProcessError):
        print("[FEHLER] Lokale Installation fehlgeschlagen. Python/venv sowie Internetzugang "
              "(bei --online) oder passende Offline-Wheels prüfen. Danach install erneut ausführen.")
        return 1
    print("Installation abgeschlossen. Anwendung mit start.sh bzw. start.bat öffnen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(online="--online" in sys.argv[1:]))
