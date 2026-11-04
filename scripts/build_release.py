"""Build reviewed source ZIPs locally. No Git, upload or dependency downloads."""
from hashlib import sha256
from pathlib import Path
import stat
import zipfile

ROOT = Path(__file__).resolve().parent.parent
FILES = """
.gitattributes
.gitignore
LICENSE
MANIFEST.in
README.md
pyproject.toml
install.sh
start.sh
install.bat
start.bat
install-mac.sh
start-mac.sh
docs/FORMAT.md
docs/TESTING.md
docs/GUI-REVIEW.md
docs/screenshots/gui-linux.png
docs/screenshots/gui-linux-150.png
docs/screenshots/gui-linux-200.png
scripts/build_release.py
scripts/install_local.py
scripts/launch.py
scripts/check_macos.py
scripts/preview_gui.py
src/eblocker_backup_explorer/__init__.py
src/eblocker_backup_explorer/app_parser.py
src/eblocker_backup_explorer/backup_reader.py
src/eblocker_backup_explorer/exporter.py
src/eblocker_backup_explorer/gui.py
src/eblocker_backup_explorer/main.py
tests/conftest.py
tests/test_app_parser.py
tests/test_backup_reader.py
tests/test_exporter.py
tests/test_gui.py
tests/test_scripts.py
tests/test_macos_scripts.py
tests/test_windows_package.py
""".split()


def main():
    payload = {}
    for name in sorted(FILES):
        path = ROOT / name
        if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
            raise ValueError(f"Expected regular reviewed file: {name}")
        payload[name] = path.read_bytes()
    manifest = "".join(f"{sha256(data).hexdigest()}  {name}\n"
                       for name, data in payload.items())
    payload["PACKAGE-CONTENTS.sha256"] = manifest.encode()
    output = ROOT / "dist" / "v0.1.0"
    output.mkdir(parents=True, exist_ok=True)
    checksums = []
    for platform in ("Linux", "Windows-11", "macOS"):
        target = output / f"eBlockerBackupExplorer-0.1.0-{platform}.zip"
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=9) as archive:
            for name, data in payload.items():
                info = zipfile.ZipInfo("eBlockerBackupExplorer/" + name,
                                       date_time=(2026, 11, 4, 0, 0, 0))
                info.create_system = 3
                mode = 0o755 if name.endswith(".sh") else 0o644
                info.external_attr = (stat.S_IFREG | mode) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data, compresslevel=9)
        with zipfile.ZipFile(target) as archive:
            assert archive.testzip() is None
            assert archive.namelist() == ["eBlockerBackupExplorer/" + n for n in payload]
            for name, data in payload.items():
                assert archive.read("eBlockerBackupExplorer/" + name) == data
        digest = sha256(target.read_bytes()).hexdigest()
        checksums.append(f"{digest}  {target.name}\n")
        print(f"{target.name}: {target.stat().st_size} bytes; SHA256 {digest}")
    (output / "SHA256SUMS").write_text("".join(checksums), encoding="ascii")
    print(f"Verified {len(payload)} entries per ZIP; identical source for all platforms.")


if __name__ == "__main__":
    main()
