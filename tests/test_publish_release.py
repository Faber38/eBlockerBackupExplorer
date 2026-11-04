"""Offline integration tests: real temporary Git repos, simulated GitHub only."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SPEC = importlib.util.spec_from_file_location(
    "publisher", Path(__file__).resolve().parents[1] / "scripts/publish_release.py")
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


class FakePublisher(release.Publisher):
    def __init__(self, root, remote):
        super().__init__(root)
        self.remote = remote
        self.calls = []
        self.record = None
        self.uploaded = {}
        self.fail_push = False
        self.fail_upload = False

    def run(self, args, allowed=(0,)):
        self.calls.append(list(args))
        if args[0] == "gh":
            data = ""
            if args[1:3] == ["repo", "view"]:
                data = {"nameWithOwner": release.REPO, "viewerPermission": "WRITE",
                        "isArchived": False, "isPrivate": False}
            elif args[1] == "api":
                data = [self.record] if self.record else []
            elif args[1:3] == ["release", "create"]:
                assert self.record is None
                self.record = {"tag_name": self.tag, "name": self.title,
                               "body": self.notes, "draft": True, "prerelease": False,
                               "assets": []}
            elif args[1:3] == ["release", "upload"]:
                if self.fail_upload:
                    raise release.ReleaseError("Simulierter Upload-Abbruch")
                path = Path(args[4])
                assert path.name not in self.uploaded
                self.uploaded[path.name] = path.read_bytes()
                self.record["assets"].append({"name": path.name, "state": "uploaded",
                                               "size": path.stat().st_size})
            elif args[1:3] == ["release", "download"]:
                name = args[args.index("--pattern") + 1]
                directory = Path(args[args.index("--dir") + 1])
                (directory / name).write_bytes(self.uploaded[name])
            elif args[1:3] == ["release", "edit"]:
                self.record["draft"] = False
            else:
                assert args[1:3] == ["auth", "status"], args
            output = json.dumps(data).encode() if not isinstance(data, str) else data.encode()
            return subprocess.CompletedProcess(args, 0, output, b"")
        # The only commands with potential network access are redirected to a
        # local bare repository. No GitHub executable or connection is used.
        args = list(args)
        if "push" in args or "fetch" in args or "ls-remote" in args:
            if "push" in args and self.fail_push:
                raise release.ReleaseError("Simulierter Push-Abbruch")
            args = [str(self.remote) if a in ("origin", release.REMOTE) else a for a in args]
        return super().run(args, allowed)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {"GIT_CONFIG_NOSYSTEM": "1",
                                              "GIT_CONFIG_GLOBAL": "/dev/null"})
        environment.start()
        self.addCleanup(environment.stop)
        self.tmp = tempfile.TemporaryDirectory(prefix="release-offline-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "Projekt mit Leerzeichen"
        self.root.mkdir()
        self.remote = Path(self.tmp.name) / "remote.git"
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Offline Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "tag.gpgsign", "false")
        subprocess.run(["git", "init", "--bare", str(self.remote)], check=True, capture_output=True)
        self.write("pyproject.toml", '[project]\nname = "test"\nversion = "0.1.0"\n')
        self.write("README.md", "Reviewed source\n")
        self.write(".gitignore", "dist/\nrelease-preparation/\n*.eblcfg\n")
        self.git("add", "--", "pyproject.toml", "README.md", ".gitignore")
        for name in ("github.sh", "scripts/publish_release.py", "tests/test_publish_release.py"):
            source = Path(__file__).resolve().parents[1] / name
            self.write(name, source.read_text())
        self.write("release-preparation/RELEASE-NOTES-v0.1.0.txt", "Reviewed notes\n")
        self.folder = self.root / "dist/v0.1.0"
        self.folder.mkdir(parents=True)
        for platform in ("Linux", "Windows-11", "macOS"):
            with zipfile.ZipFile(self.folder / f"eBlockerBackupExplorer-0.1.0-{platform}.zip", "w") as archive:
                archive.writestr("eBlockerBackupExplorer/README.md", "Reviewed source\n")
        self.checksums()
        self.publisher = FakePublisher(self.root, self.remote)

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True,
                              check=True, text=True).stdout.strip()

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def checksums(self):
        (self.folder / "SHA256SUMS").write_text("".join(
            f"{release.digest(p.read_bytes())}  {p.name}\n" for p in sorted(self.folder.glob("*.zip"))))

    def execute(self, answer="ja"):
        with patch("builtins.input", return_value=answer), patch.object(release.shutil, "which", return_value="/fake/tool"), contextlib.redirect_stdout(io.StringIO()):
            self.publisher.execute()

    def assert_rejected(self, expression):
        with self.assertRaisesRegex(release.ReleaseError, expression):
            self.execute()

    def test_first_release_missing_origin_and_no_commit(self):
        self.execute()
        self.assertEqual(self.git("remote", "get-url", "origin"), release.REMOTE)
        self.assertEqual(self.git("log", "-1", "--format=%s"), "Release v0.1.0")
        self.assertEqual(self.git("cat-file", "-t", "v0.1.0"), "tag")
        self.assertEqual(len(self.publisher.uploaded), 4)
        self.assertFalse(self.publisher.record["draft"])
        tracked = self.git("ls-files").splitlines()
        self.assertIn("github.sh", tracked)
        self.assertIn("scripts/publish_release.py", tracked)
        self.assertNotIn("release-preparation/RELEASE-NOTES-v0.1.0.txt", tracked)

    def test_existing_commit_no_extra_commit(self):
        self.git("add", "--", *sorted(release.APPROVED.intersection(
            {p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file()})))
        self.git("commit", "-m", "Reviewed initial version")
        head = self.git("rev-parse", "HEAD")
        self.execute()
        self.assertEqual(self.git("rev-parse", "HEAD"), head)

    def test_wrong_origin(self):
        self.git("remote", "add", "origin", "https://example.invalid/other.git")
        self.assert_rejected("origin")
        self.assertEqual(self.git("remote", "get-url", "origin"), "https://example.invalid/other.git")

    def test_wrong_push_origin(self):
        self.git("remote", "add", "origin", release.REMOTE)
        self.git("remote", "set-url", "--push", "origin", "https://example.invalid/other.git")
        self.assert_rejected("origin")

    def test_missing_zip(self):
        next(self.folder.glob("*.zip")).unlink()
        self.assert_rejected("Datei fehlt")

    def test_invalid_checksum(self):
        next(self.folder.glob("*.zip")).write_bytes(b"changed")
        self.assert_rejected("Prüfsumme")

    def test_broken_zip_with_valid_checksum(self):
        next(self.folder.glob("*.zip")).write_bytes(b"not a zip")
        self.checksums()
        with self.assertRaises(zipfile.BadZipFile):
            self.execute()

    def test_existing_local_tag(self):
        self.git("add", "--", "github.sh", "scripts/publish_release.py", "tests/test_publish_release.py")
        self.git("commit", "-m", "Initial")
        self.git("tag", "-a", "v0.1.0", "-m", "Reviewed tag")
        tag = self.git("rev-parse", "v0.1.0")
        self.execute()
        self.assertEqual(self.git("rev-parse", "v0.1.0"), tag)

    def test_repeat_existing_release(self):
        self.execute()
        head = self.git("rev-parse", "HEAD")
        self.publisher.calls.clear()
        self.execute()
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        self.assertFalse(any("push" in call or "commit" in call or "upload" in call
                             or "create" in call for call in self.publisher.calls))

    def test_interrupted_push_and_retry(self):
        self.publisher.fail_push = True
        self.assert_rejected("Push-Abbruch")
        head = self.git("rev-parse", "HEAD")
        self.assertIsNone(self.publisher.record)
        self.assertEqual(sum("push" in call for call in self.publisher.calls), 1)
        self.publisher.fail_push = False
        self.execute()
        self.assertEqual(self.git("rev-parse", "HEAD"), head)

    def test_interrupted_upload_and_retry(self):
        self.publisher.fail_upload = True
        self.assert_rejected("Upload-Abbruch")
        self.assertTrue(self.publisher.record["draft"])
        self.publisher.fail_upload = False
        self.execute()
        self.assertEqual(len(self.publisher.uploaded), 4)
        self.assertEqual(sum(call[1:3] == ["release", "create"] for call in self.publisher.calls), 1)

    def test_untracked_backup_excluded(self):
        self.write("private.eblcfg", "sensitive backup")
        self.write("personal.conf", "personal config")
        self.execute()
        self.assertNotIn("private.eblcfg", self.git("ls-files"))
        self.assertNotIn("personal.conf", self.git("ls-files"))
        self.assertEqual((self.root / "private.eblcfg").read_text(), "sensitive backup")

    def test_staged_backup_rejected(self):
        self.write("private.eblcfg", "sensitive backup")
        self.git("add", "-f", "private.eblcfg")
        self.assert_rejected("Index enthält")

    def test_backup_in_history_rejected(self):
        self.write("private.eblcfg", "sensitive backup")
        self.git("add", "-f", "private.eblcfg")
        self.git("commit", "-m", "Synthetic unsafe history")
        self.git("rm", "private.eblcfg")
        self.git("commit", "-m", "Remove fixture")
        self.assert_rejected("Historie")

    def test_private_zip_entry_rejected(self):
        with zipfile.ZipFile(next(self.folder.glob("*.zip")), "a") as archive:
            archive.writestr("eBlockerBackupExplorer/private.eblcfg", "backup")
        self.checksums()
        self.assert_rejected("nicht freigegebene Datei")

    def test_literal_secret_rejected(self):
        self.write("README.md", 'password = "' + 'synthetic-credential' + '"\n')
        self.git("add", "README.md")
        self.assert_rejected("Datenschutzprüfung")

    def test_partially_staged_file_rejected(self):
        self.write("README.md", "Unstaged changes\n")
        self.assert_rejected("Index und Arbeitsdatei")

    def test_changed_existing_release_rejected(self):
        self.execute()
        self.write("README.md", "Next version\n")
        self.git("add", "README.md")
        self.assert_rejected("Version existiert bereits")

    def test_mismatched_existing_asset_rejected(self):
        self.execute()
        name = next(iter(self.publisher.uploaded))
        data = self.publisher.uploaded[name]
        self.publisher.uploaded[name] = b"x" * len(data)
        self.assert_rejected("abweichende Prüfsumme")

    def test_lightweight_tag_rejected(self):
        self.git("commit", "-m", "Initial")
        self.git("tag", "v0.1.0")
        self.assert_rejected("nicht annotiert")

    def test_decline_does_not_mutate_git(self):
        index = (self.root / ".git/index").read_bytes()
        self.execute("nein")
        self.assertEqual((self.root / ".git/index").read_bytes(), index)
        self.assertEqual(self.git("remote"), "")
        self.assertIsNone(self.publisher.head())
        self.assertIsNone(self.publisher.record)

    def test_wrong_branch(self):
        self.git("symbolic-ref", "HEAD", "refs/heads/development")
        self.assert_rejected("Branch main")

    def test_git_line_ending_normalization(self):
        self.write(".gitattributes", "*.bat text eol=crlf\n")
        self.write("install.bat", "@echo off\r\necho fixture\r\n")
        self.git("add", ".gitattributes", "install.bat")
        self.execute()
        self.assertIn("install.bat", self.git("ls-files"))

    def test_existing_remote_tag_restored_locally(self):
        self.execute()
        tag = self.git("rev-parse", "v0.1.0")
        self.git("tag", "-d", "v0.1.0")
        self.execute()
        self.assertEqual(self.git("rev-parse", "v0.1.0"), tag)

    def test_tag_for_other_commit_rejected(self):
        self.execute()
        self.write("README.md", "Different commit\n")
        self.git("add", "README.md")
        self.git("commit", "-m", "Different commit")
        self.assert_rejected("anderen Commit")

    def test_only_missing_assets_uploaded(self):
        self.execute()
        name = next(iter(self.publisher.uploaded))
        del self.publisher.uploaded[name]
        self.publisher.record["assets"] = [a for a in self.publisher.record["assets"] if a["name"] != name]
        self.publisher.calls.clear()
        self.execute()
        uploads = [c for c in self.publisher.calls if c[1:3] == ["release", "upload"]]
        self.assertEqual(len(uploads), 1)
        self.assertEqual(Path(uploads[0][4]).name, name)

    def test_unexpected_asset_rejected(self):
        self.execute()
        self.publisher.record["assets"].append({"name": "private.eblcfg"})
        self.assert_rejected("unerwartete")

    def test_changes_during_confirmation_rejected(self):
        def answer(_prompt):
            self.write("README.md", "Changed during confirmation\n")
            return "ja"
        with patch("builtins.input", side_effect=answer), patch.object(release.shutil, "which", return_value="/fake/tool"), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(release.ReleaseError):
                self.publisher.execute()
        self.assertIsNone(self.publisher.head())
        self.assertEqual(self.git("remote"), "")

    def test_approved_unstaged_change_committed(self):
        self.git("commit", "-m", "Initial reviewed files")
        self.write("README.md", "Reviewed update\n")
        self.execute()
        self.assertEqual(self.git("show", "HEAD:README.md"), "Reviewed update")

    def test_approved_unstaged_deletion_committed(self):
        self.git("commit", "-m", "Initial reviewed files")
        (self.root / "README.md").unlink()
        self.execute()
        self.assertNotIn("README.md", self.git("ls-files"))


if __name__ == "__main__":
    unittest.main()
