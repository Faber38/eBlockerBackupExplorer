#!/usr/bin/env python3
"""Linux release assistant; run explicitly with ./github.sh, never from the app.

Only reviewed paths below may enter a commit. Extend this list after review when
adding project files. No build, dependency installation, force push or overwrite.
Secret detection is conservative pattern matching, not a substitute for review.
Run offline tests: python3 -m unittest discover -s tests -p test_publish_release.py
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

REPO = "Faber38/eBlockerBackupExplorer"
REMOTE = f"https://github.com/{REPO}.git"
APPROVED = frozenset("""
.gitattributes .gitignore LICENSE MANIFEST.in README.md pyproject.toml
install.sh start.sh install.bat start.bat install-mac.sh start-mac.sh
 docs/FORMAT.md docs/TESTING.md docs/GUI-REVIEW.md
 docs/screenshots/gui-linux.png docs/screenshots/gui-linux-150.png
 docs/screenshots/gui-linux-200.png
 scripts/build_release.py scripts/install_local.py scripts/launch.py
 scripts/check_macos.py scripts/preview_gui.py
 src/eblocker_backup_explorer/__init__.py
 src/eblocker_backup_explorer/app_parser.py
 src/eblocker_backup_explorer/backup_reader.py
 src/eblocker_backup_explorer/exporter.py
 src/eblocker_backup_explorer/gui.py
 src/eblocker_backup_explorer/main.py
 tests/conftest.py tests/test_app_parser.py tests/test_backup_reader.py
 tests/test_exporter.py tests/test_gui.py tests/test_scripts.py
 tests/test_macos_scripts.py tests/test_windows_package.py
 github.sh scripts/publish_release.py tests/test_publish_release.py
""".split())
SECRET = re.compile(
    rb"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----|"
    rb"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16})\b|"
    rb"(?i:https?://[^\s/:]+:[^\s/@]+@)|"
    rb'''(?im:^\s*["']?(?:password|passwd|secret|token|api_key|api_secret|access_token)["']?\s*[:=]\s*["'][^"'\r\n]+["'])'''
)


class ReleaseError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise ReleaseError(message)


def scan(data):
    require(not SECRET.search(data),
            "Datenschutzprüfung: möglicher Schlüssel oder Passwort gefunden; Inhalt wird nicht ausgegeben.")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def regular(root, relative):
    path = root / relative
    require(not any(p.is_symlink() for p in (path, *path.parents)),
            "Symbolische Links sind für Release-Eingaben nicht erlaubt.")
    require(path.is_file(), f"Erforderliche Datei fehlt: {relative}")
    return path


def version_at(root):
    # Python 3.10 has no tomllib. Accept only one explicit stable project version.
    text = regular(root, "pyproject.toml").read_text(encoding="utf-8")
    section = re.search(r"(?ms)^\[project\]\s*\n(.*?)(?=^\[|\Z)", text)
    values = re.findall(r'^version\s*=\s*[\"\'](\d+\.\d+\.\d+)[\"\']\s*(?:#.*)?$',
                        section[1] if section else "", re.M)
    require(len(values) == 1, "Eindeutige Version X.Y.Z in [project] von pyproject.toml erforderlich.")
    return values[0]


def artifacts(root, version):
    folder = Path("dist") / ("v" + version)
    names = [f"eBlockerBackupExplorer-{version}-{platform}.zip"
             for platform in ("Linux", "Windows-11", "macOS")]
    paths = [regular(root, folder / name) for name in [*names, "SHA256SUMS"]]
    sums = {}
    for line in paths[-1].read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"([a-fA-F0-9]{64}) [ *](.+)", line)
        require(match is not None, "Ungültiges Format in SHA256SUMS.")
        checksum, name = match.groups()
        require(name not in sums, "Doppelter Eintrag in SHA256SUMS.")
        sums[name] = checksum.lower()
    require(set(sums) == set(names), "SHA256SUMS muss genau die drei erwarteten ZIPs enthalten.")
    for path in paths[:-1]:
        require(digest(path.read_bytes()) == sums[path.name], "SHA256-Prüfsumme stimmt nicht: " + path.name)
        with zipfile.ZipFile(path) as archive:
            require(archive.testzip() is None, "ZIP-Integritätsprüfung fehlgeschlagen.")
            seen = set()
            require(bool(archive.infolist()), "Leeres ZIP ist nicht erlaubt.")
            for info in archive.infolist():
                parts = PurePosixPath(info.filename).parts
                require(len(parts) >= 2 and parts[0] == "eBlockerBackupExplorer",
                        "ZIP enthält einen nicht freigegebenen Pfad.")
                name = "/".join(parts[1:])
                require(name in APPROVED or name == "PACKAGE-CONTENTS.sha256",
                        "ZIP enthält eine nicht freigegebene Datei.")
                require(info.filename == "eBlockerBackupExplorer/" + name and name not in seen
                        and not info.is_dir() and (info.external_attr >> 16) & 0o170000 in (0, 0o100000),
                        "ZIP enthält doppelte Pfade, Links oder Sonderdateien.")
                seen.add(name)
                scan(archive.read(info))
    return {p.name: (p, digest(p.read_bytes())) for p in paths}


class Publisher:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.phase = "Vorprüfung"

    def run(self, args, allowed=(0,)):
        result = subprocess.run(args, cwd=self.root, capture_output=True,
                                env=dict(os.environ, GH_HOST="github.com", GH_PROMPT_DISABLED="1",
                                         GIT_TERMINAL_PROMPT="0"))
        require(result.returncode in allowed,
                f"{args[0]} fehlgeschlagen (Exit-Code {result.returncode}); "
                "Anmeldung, Verbindung und Repository-Zustand prüfen. Keine automatische Wiederholung.")
        return result

    def git(self, *args, allowed=(0,)):
        return self.run(["git", *args], allowed).stdout.decode().rstrip("\n")

    def gh(self, *args):
        return self.run(["gh", *args]).stdout.decode()

    def head(self):
        result = self.run(["git", "rev-parse", "--verify", "--quiet", "HEAD"], (0, 1))
        return result.stdout.decode().strip() if result.returncode == 0 else None

    def origin(self):
        if "origin" not in self.git("remote").splitlines():
            return False
        for options in ((), ("--push",)):
            urls = self.git("remote", "get-url", *options, "--all", "origin").splitlines()
            require(urls == [REMOTE], "origin (Fetch/Push) muss exakt dem vorgesehenen HTTPS-Ziel entsprechen; keine Änderung vorgenommen.")
        return True

    def snapshot(self):
        require(self.git("branch", "--show-current") == "main", "Branch main erforderlich.")
        for marker in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply"):
            require(not (self.root / self.git("rev-parse", "--git-path", marker)).exists(),
                    "Laufende Git-Operation zuerst abschließen.")
        require(self.git("rev-parse", "--is-shallow-repository") == "false",
                "Datenschutzprüfung benötigt die vollständige Git-Historie.")
        require(not self.git("replace", "-l"), "Git-Replacement-Objekte sind nicht erlaubt.")
        staged = set(filter(None, self.git("diff", "--cached", "--name-only", "-z").split("\0")))
        unstaged = set(filter(None, self.git("diff", "--name-only", "-z").split("\0")))
        index = {}
        for entry in self.git("ls-files", "--stage", "-z").split("\0"):
            if not entry:
                continue
            metadata, name = entry.split("\t", 1)
            mode, oid, stage = metadata.split()
            require(name in APPROVED and mode in ("100644", "100755") and stage == "0",
                    "Index enthält nicht freigegebene Dateien, Links oder Konflikte.")
            data = self.run(["git", "cat-file", "blob", oid]).stdout
            scan(data)
            index[name] = (mode, oid)
            # Do not silently replace partially staged work or staged old contents.
            if name in staged:
                regular(self.root, name)
                require(self.git("hash-object", "--path=" + name, "--", name) == oid,
                        "Index und Arbeitsdatei unterscheiden sich: " + name + ". Änderungen zuerst bewusst vormerken.")
        head = self.head()
        scanned = set()
        if head:
            for commit in self.git("rev-list", head).splitlines():
                for entry in self.git("ls-tree", "-r", "-z", commit).split("\0"):
                    if not entry:
                        continue
                    meta, name = entry.split("\t", 1)
                    mode, kind, oid = meta.split()
                    require(name in APPROVED and mode in ("100644", "100755") and kind == "blob",
                            "Historie enthält nicht freigegebene Dateien oder Links; Veröffentlichung gestoppt.")
                    if oid not in scanned:
                        scan(self.run(["git", "cat-file", "blob", oid]).stdout)
                        scanned.add(oid)
        files = {}
        for name in sorted(APPROVED):
            path = self.root / name
            if path.exists() or path.is_symlink():
                data = regular(self.root, name).read_bytes()
                scan(data)
                files[name] = (digest(data), bool(path.stat().st_mode & 0o111))
        self.git("diff", "--cached", "--check")
        changed = bool(staged)
        # Stage only scanned, explicitly approved paths, including deletions.
        new_files = set(files) - set(index)
        require(not (new_files & staged), "Vorgemerkte Löschung und vorhandene Datei widersprechen sich.")
        require(unstaged <= APPROVED, "Nicht freigegebene Arbeitsänderungen gefunden.")
        additions = sorted(new_files | unstaged)
        return head, index, files, changed, additions

    def remote_refs(self):
        output = self.git("ls-remote", REMOTE, "refs/heads/main",
                          f"refs/tags/{self.tag}", f"refs/tags/{self.tag}^{{}}")
        return {ref: oid for oid, ref in (line.split() for line in output.splitlines())}

    def release(self):
        matches = []
        page = 1
        while True:
            data = json.loads(self.gh("api", "--hostname", "github.com", "--method", "GET",
                                     f"repos/{REPO}/releases?per_page=100&page={page}"))
            require(isinstance(data, list), "Ungültige GitHub-Releaseliste.")
            matches.extend(r for r in data if r.get("tag_name") == self.tag)
            if len(data) < 100:
                break
            page += 1
        require(len(matches) <= 1, "Mehrere Releases für dieselbe Version gefunden.")
        return matches[0] if matches else None

    def state(self, head, pending):
        ref = f"refs/tags/{self.tag}"
        exists = self.run(["git", "show-ref", "--verify", "--quiet", ref], (0, 1)).returncode == 0
        local = None
        if exists:
            require(self.git("cat-file", "-t", ref) == "tag", "Vorhandener lokaler Tag ist nicht annotiert.")
            require(self.git("rev-parse", ref + "^{commit}") == head, "Lokaler Tag zeigt auf einen anderen Commit.")
            local = self.git("rev-parse", ref)
        refs = self.remote_refs()
        remote = refs.get(ref)
        if remote:
            require(refs.get(ref + "^{}") == head, "Remote-Tag ist nicht annotiert oder zeigt auf einen anderen Commit.")
            require(local is None or local == remote, "Lokaler und entfernter Tag unterscheiden sich.")
        release = self.release()
        require(not (pending and (local or remote or release)),
                "Version existiert bereits, aber Commit-Änderungen sind vorhanden. Version bewusst prüfen.")
        if release:
            require(remote and release.get("name") == self.title and not release.get("prerelease")
                    and release.get("body", "").replace("\r\n", "\n").strip() == self.notes.strip(),
                    "Vorhandenes Release passt nicht zu Tag, Titel oder lokalen Release-Notes.")
        return local, refs, release

    def verify_assets(self, release):
        assets = release.get("assets", []) if release else []
        names = [a.get("name") for a in assets]
        require(len(names) == len(set(names)) and set(names) <= set(self.assets),
                "Release enthält unerwartete oder doppelte Dateien; kein Überschreiben.")
        for asset in assets:
            name = asset["name"]
            path, expected = self.assets[name]
            require(asset.get("state") == "uploaded" and asset.get("size") == path.stat().st_size,
                    "Vorhandene Release-Datei hat falsche Größe oder ist unvollständig.")
            # Download comparison also works where GitHub provides no digest field.
            with tempfile.TemporaryDirectory(prefix="eblocker-verify-") as tmp:
                self.gh("release", "download", self.tag, "--repo", REPO,
                        "--pattern", name, "--dir", tmp)
                require(digest((Path(tmp) / name).read_bytes()) == expected,
                        "Hochgeladene Datei hat eine abweichende Prüfsumme; kein Überschreiben.")
        return set(self.assets) - set(names)

    def execute(self):
        require(sys.platform.startswith("linux") and sys.version_info >= (3, 10),
                "Der Assistent benötigt Linux und Python 3.10 oder neuer.")
        for tool in ("git", "gh"):
            require(shutil.which(tool), f"Benötigtes Programm fehlt: {tool}")
        require(self.git("rev-parse", "--show-toplevel") == str(self.root), "Falsches Projektverzeichnis.")
        self.gh("auth", "status", "--hostname", "github.com")
        repo = json.loads(self.gh("repo", "view", REPO, "--json", "nameWithOwner,viewerPermission,isArchived,isPrivate"))
        require(repo.get("nameWithOwner") == REPO and not repo.get("isArchived")
                and not repo.get("isPrivate") and repo.get("viewerPermission") in ("ADMIN", "MAINTAIN", "WRITE"),
                "GitHub-Ziel oder Schreibberechtigung stimmt nicht.")
        origin = self.origin()
        version = version_at(self.root)
        self.tag = "v" + version
        self.title = "eBlocker Backup Explorer " + self.tag
        notes_path = regular(self.root, f"release-preparation/RELEASE-NOTES-{self.tag}.txt")
        self.notes = notes_path.read_text(encoding="utf-8")
        require(self.notes.strip(), "Release-Notes sind leer.")
        scan(self.notes.encode())
        self.assets = artifacts(self.root, version)
        before = self.snapshot()
        head, _, _, changed, additions = before
        pending = changed or bool(additions)
        require(head or pending, "Keine freigegebenen Dateien für den ersten Commit vorhanden.")
        _, _, release = self.state(head, pending)
        self.verify_assets(release)
        print(f"Version: {self.tag}\nBranch: main\nGitHub-Ziel: {REPO}\n"
              f"Commit: {head or 'Erstveröffentlichung ohne Commit'}\nCommit-Änderungen:")
        print(self.git("diff", "--cached", "--stat") or "Keine vorgemerkten Änderungen.")
        for name in additions:
            print("  Freigegebene Arbeitsänderung: " + name)
        unknown = self.git("ls-files", "--others", "--exclude-standard", "-z").split("\0")
        print(f"Nicht freigegebene unversionierte Dateien bleiben ausgeschlossen: {sum(bool(n) and n not in APPROVED for n in unknown)}")
        print("Release-Dateien:")
        for name, (path, checksum) in self.assets.items():
            print(f"  {name} ({path.stat().st_size} Bytes, SHA256 {checksum})")
        print("Datenschutz: Freigabeliste und Inhaltsmuster geprüft; die persönliche Prüfung auf sensible Inhalte bleibt erforderlich.")
        if input("Diese Version jetzt veröffentlichen? [j/N]: ").strip().lower() not in ("j", "ja"):
            print("Abgebrochen; keine Veröffentlichungsschritte ausgeführt.")
            return
        self.phase = "Zustandsprüfung nach Bestätigung"
        require(self.snapshot() == before and self.origin() == origin
                and version_at(self.root) == version and notes_path.read_text(encoding="utf-8") == self.notes
                and artifacts(self.root, version) == self.assets,
                "Lokale Eingaben wurden während der Bestätigung verändert.")
        self.state(head, pending)
        if not origin:
            self.git("remote", "add", "origin", REMOTE)
        self.phase = "Commit"
        if additions:
            self.git("add", "-A", "--", *additions)
        self.snapshot()  # Inspect actual staged blobs after any Git filters.
        if pending:
            self.git("commit", "-m", f"Release {self.tag}")
        head = self.head()
        require(head and not self.git("diff", "HEAD", "--name-only"), "Arbeitsstand nach Commit nicht sauber.")
        after = self.snapshot()  # Include committed history and hook changes.
        require(after[2] == before[2], "Projektdateien wurden während des Commits verändert.")
        local, refs, release = self.state(head, False)
        self.phase = "Push von main"
        if refs.get("refs/heads/main") != head:
            self.git("-c", "push.followTags=false", "push", "origin", f"{head}:refs/heads/main")
        require(self.remote_refs().get("refs/heads/main") == head, "main wurde nicht wie erwartet hochgeladen.")
        self.phase = "Annotierter Tag"
        ref = f"refs/tags/{self.tag}"
        if not local:
            if refs.get(ref):
                self.git("fetch", "--no-tags", "origin", f"{ref}:{ref}")
            else:
                self.git("tag", "-a", self.tag, head, "-m", self.title)
        if not refs.get(ref):
            self.git("-c", "push.followTags=false", "push", "origin", f"{ref}:{ref}")
        _, refs, release = self.state(head, False)
        require(refs.get(ref), "Remote-Tag fehlt nach Push.")
        self.phase = "Release und Upload"
        require(artifacts(self.root, version) == self.assets
                and notes_path.read_text(encoding="utf-8") == self.notes,
                "Release-Dateien oder Release-Notes wurden verändert.")
        # A draft prevents incomplete new releases from becoming public. Resume it
        # only after matching its tag, notes and existing files byte for byte.
        if release is None:
            self.gh("release", "create", self.tag, "--repo", REPO, "--verify-tag",
                    "--draft", "--title", self.title, "--notes-file", str(notes_path))
            release = self.release()
            require(release is not None, "Release fehlt nach Erstellung.")
        missing = self.verify_assets(release)
        for name in sorted(missing):
            self.gh("release", "upload", self.tag, str(self.assets[name][0]), "--repo", REPO)
        self.phase = "Abschlussprüfung"
        _, _, release = self.state(head, False)
        require(release is not None and not self.verify_assets(release), "Release-Dateien fehlen.")
        if release.get("draft"):
            self.gh("release", "edit", self.tag, "--repo", REPO, "--draft=false")
        _, refs, release = self.state(head, False)
        require(release is not None and not release.get("draft")
                and refs.get("refs/heads/main") == head and not self.verify_assets(release),
                "Release-Abschlussprüfung fehlgeschlagen.")
        print(self.git("status", "--short", "--branch"))
        print(f"Release erfolgreich geprüft: https://github.com/{REPO}/releases/tag/{self.tag}")


def main():
    publisher = Publisher(Path(__file__).resolve().parents[1])
    try:
        publisher.execute()
    except (ReleaseError, OSError, ValueError, KeyError, TypeError, EOFError,
            zipfile.BadZipFile, RuntimeError, KeyboardInterrupt) as exc:
        detail = str(exc) if isinstance(exc, ReleaseError) else "Lokale Datei, Antwort oder Eingabe konnte nicht verarbeitet werden."
        print(f"[FEHLER] {publisher.phase}: {detail}", file=sys.stderr)
        print("Gestoppt. Erfolgreiche Teilschritte bleiben erhalten und werden beim nächsten Aufruf geprüft.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
