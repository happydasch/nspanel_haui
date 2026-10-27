"""Tests for the release version-bump tooling.

``scripts/bump_version.py`` updates the four version sources that must agree
(manifest, pyproject, ESPHome ``version.yaml`` and the HMI ``tftVersion`` text).
These tests drive it against temporary copies so the repository files are never
touched, and verify the text sources plus the HMI binary edit.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
NEXTION = ROOT / "nextion"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


bump_tft = _load("bump_tft_version")
bump_version = _load("bump_version")


@pytest.fixture()
def version_files(tmp_path, monkeypatch):
    """Point the bump scripts at temporary copies of every version source."""
    manifest = tmp_path / "manifest.json"
    pyproject = tmp_path / "pyproject.toml"
    version_yaml = tmp_path / "version.yaml"
    manifest.write_text(
        json.dumps({"domain": "nspanel_haui", "version": "0.4.1"}, indent=2),
        encoding="utf-8",
    )
    pyproject.write_text(
        '[project]\nname = "nspanel-haui"\nversion = "0.4.1"\n',
        encoding="utf-8",
    )
    version_yaml.write_text(
        "---\nsubstitutions:\n  yaml_version: '0.4.1'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(bump_version, "MANIFEST", manifest)
    monkeypatch.setattr(bump_version, "PYPROJECT", pyproject)
    monkeypatch.setattr(bump_version, "VERSION_YAML", version_yaml)
    return manifest, pyproject, version_yaml


def _bump_text(version: str = "0.4.2", check: bool = False) -> bool:
    return bump_version.bump_text_sources(version, check)


def test_text_sources_bump_to_new_version(version_files):
    manifest, pyproject, version_yaml = version_files
    assert _bump_text("0.4.2") is True
    assert json.loads(manifest.read_text())["version"] == "0.4.2"
    assert 'version = "0.4.2"' in pyproject.read_text()
    assert "yaml_version: '0.4.2'" in version_yaml.read_text()


def test_text_sources_are_idempotent(version_files):
    _bump_text("0.4.2")
    manifest, pyproject, version_yaml = version_files
    assert _bump_text("0.4.2") is True
    assert json.loads(manifest.read_text())["version"] == "0.4.2"
    assert 'version = "0.4.2"' in pyproject.read_text()
    assert "yaml_version: '0.4.2'" in version_yaml.read_text()


def test_check_mode_reports_change_without_writing(version_files):
    manifest, pyproject, version_yaml = version_files
    assert _bump_text("0.4.2", check=True) is False
    assert json.loads(manifest.read_text())["version"] == "0.4.1"
    assert 'version = "0.4.1"' in pyproject.read_text()
    assert "yaml_version: '0.4.1'" in version_yaml.read_text()


def test_missing_pattern_fails(version_files, monkeypatch):
    pyproject = version_files[1]
    pyproject.write_text("[project]\nname = 'x'\n", encoding="utf-8")
    assert _bump_text("0.4.2") is False


# --- HMI bumping -----------------------------------------------------------


@pytest.fixture()
def hmi_copies(tmp_path):
    """Copy both release HMIs so the repository binaries are never modified."""
    landscape = tmp_path / "nspanel_haui.HMI"
    portrait = tmp_path / "nspanel_haui_portrait.HMI"
    shutil.copy2(NEXTION / "nspanel_haui.HMI", landscape)
    shutil.copy2(NEXTION / "nspanel_haui_portrait.HMI", portrait)
    return landscape, portrait


def _current_hmi_version(path: Path) -> str:
    raw = path.read_bytes()
    block = bump_tft.gp.parse_pages(raw)["system"]
    located = bump_tft._find_txt_record(raw, block)
    assert located is not None
    length_field, value_off = located
    (length,) = __import__("struct").unpack_from("<I", raw, length_field)
    return raw[value_off : length_field + 4 + length].decode("iso_8859_1")


def test_hmi_bump_writes_same_length_version(hmi_copies):
    landscape, _ = hmi_copies
    before = _current_hmi_version(landscape)
    # Use the same length as the committed value so the in-place edit is legal.
    new_version = before[:-1] + ("9" if before[-1] != "9" else "8")
    ok, message = bump_tft.bump_hmi(landscape, new_version)
    assert ok, message
    assert _current_hmi_version(landscape) == new_version


def test_hmi_bump_is_idempotent(hmi_copies):
    landscape, _ = hmi_copies
    version = _current_hmi_version(landscape)
    ok, _ = bump_tft.bump_hmi(landscape, version)
    assert ok
    ok, _ = bump_tft.bump_hmi(landscape, version)
    assert ok


def test_hmi_bump_rejects_length_change(hmi_copies):
    landscape, _ = hmi_copies
    ok, message = bump_tft.bump_hmi(landscape, "0.5")
    assert not ok
    assert "cannot write" in message


def test_hmi_bump_check_mode_does_not_write(hmi_copies):
    landscape, _ = hmi_copies
    before = _current_hmi_version(landscape)
    new_version = before[:-1] + ("9" if before[-1] != "9" else "8")
    ok, message = bump_tft.bump_hmi(landscape, new_version, check=True)
    assert not ok
    assert "would set" in message
    assert _current_hmi_version(landscape) == before


def test_bump_script_rejects_bad_version():
    assert bump_version.main(["1.2"]) == 2
    assert bump_version.main(["not-a-version"]) == 2


def test_bump_script_text_only(tmp_path, monkeypatch, version_files):
    """--text-only leaves the HMI binaries untouched."""
    monkeypatch.setattr(bump_version, "bump_hmis", lambda *a, **k: pytest.fail("HMI touched"))
    manifest = version_files[0]
    assert bump_version.main(["0.4.2", "--text-only"]) == 0
    assert json.loads(manifest.read_text())["version"] == "0.4.2"
