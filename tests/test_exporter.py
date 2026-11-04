import csv
import io
import os

import pytest
from eblocker_backup_explorer.app_parser import App
from eblocker_backup_explorer.exporter import export_apps, render_export


@pytest.mark.parametrize("format,delimiter", [("txt", "\t"), ("csv", ",")])
def test_unicode_export_and_newlines(tmp_path, format, delimiter):
    app = App("Äpfel", 'Text; "Zitat"\r\nZeile', ("münchen.example", "two.example"), True, False)
    source = tmp_path / "source.eblcfg"
    source.write_bytes(b"source remains untouched")
    target = tmp_path / f"export.{format}"
    export_apps(target, [app], format, source)
    rows = list(csv.reader(io.StringIO(target.read_bytes().decode("utf-8"), newline=""), delimiter=delimiter))
    assert len(rows) == 3 and rows[1][1] == "Äpfel"
    assert rows[1][2] == app.description and rows[1][-1] == "münchen.example"
    assert source.read_bytes() == b"source remains untouched"


def test_existing_target_and_source_protected(tmp_path):
    source = tmp_path / "source.eblcfg"
    source.write_bytes(b"protected")
    with pytest.raises(ValueError):
        export_apps(source, [], "txt", source)
    existing = tmp_path / "existing.txt"
    existing.write_text("keep")
    with pytest.raises(FileExistsError):
        export_apps(existing, [], "txt", source)
    assert existing.read_text() == "keep"


def test_hardlink_source_protected(tmp_path):
    source = tmp_path / "source.eblcfg"
    source.write_bytes(b"protected")
    alias = tmp_path / "alias.txt"
    os.link(source, alias)
    with pytest.raises(FileExistsError):
        export_apps(alias, [], "txt", source)
    assert source.read_bytes() == b"protected"


def test_csv_formula_protection():
    text = render_export([App("=1+2", "@formula", (), False, False)], "csv")
    assert "'=1+2" in text and "'@formula" in text
