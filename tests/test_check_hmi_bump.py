"""Tests for the display TFT version-bump gate (scripts/verify_nextion/check_hmi_bump.py)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.verify_nextion import check_hmi_bump
from scripts.verify_nextion.check_hmi_bump import evaluate, read_tft_version, version_key

LANDSCAPE = "nextion/nspanel_haui.HMI"
LANDSCAPE_TFT = "nextion/nspanel_haui.tft"
PORTRAIT = "nextion/nspanel_haui_portrait.HMI"


def test_read_tft_version_from_version_yaml():
    text = "---\nsubstitutions:\n  yaml_version: '0.4.5.dev40'\n  tft_version: '0.4.5.dev33'\n"
    assert read_tft_version(text) == "0.4.5.dev33"
    assert read_tft_version("no version here") == ""


def test_version_key_orders_pep440_dev_versions():
    assert version_key("0.4.5.dev33") < version_key("0.4.5.dev40")
    assert version_key("0.4.5.dev40") < version_key("0.4.5")
    assert version_key("0.4.5") < version_key("0.4.6.dev1")
    assert version_key("not-a-version") is None


def test_no_hmi_change_passes():
    ok, message = evaluate([], "0.4.5.dev33", "0.4.5.dev33")
    assert ok
    assert "no Nextion HMI" in message


def test_hmi_change_without_a_version_bump_fails():
    ok, message = evaluate([LANDSCAPE], "0.4.5.dev33", "0.4.5.dev33")
    assert not ok
    assert "did not advance" in message
    assert "recompile" in message


def test_hmi_change_with_a_dev_bump_passes():
    ok, _ = evaluate([LANDSCAPE, PORTRAIT], "0.4.5.dev33", "0.4.5.dev34")
    assert ok


def test_hmi_change_with_a_final_release_passes():
    ok, _ = evaluate([PORTRAIT], "0.4.5.dev33", "0.4.5")
    assert ok


def test_hmi_change_with_a_backwards_bump_fails():
    ok, message = evaluate([LANDSCAPE], "0.4.5.dev34", "0.4.5.dev33")
    assert not ok
    assert "did not advance" in message


def test_missing_version_fails():
    ok, message = evaluate([LANDSCAPE], "", "0.4.5.dev34")
    assert not ok
    assert "missing" in message


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _commit(root: Path, message: str) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


@pytest.fixture()
def repo(tmp_path, monkeypatch) -> Path:
    """A git repository whose base commit holds both display assets and tft_version."""
    root = tmp_path / "repo"
    (root / "nextion").mkdir(parents=True)
    (root / "esphome" / "nspanel_haui").mkdir(parents=True)
    (root / LANDSCAPE).write_bytes(b"hmi-1")
    (root / LANDSCAPE_TFT).write_bytes(b"tft-1")
    _write_tft_version(root, "0.4.5.dev33")
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _commit(root, "base")
    monkeypatch.setattr(check_hmi_bump, "ROOT", root)
    monkeypatch.setattr(
        check_hmi_bump, "VERSION_YAML", root / "esphome" / "nspanel_haui" / "version.yaml"
    )
    return root


def _write_tft_version(root: Path, version: str) -> None:
    (root / "esphome" / "nspanel_haui" / "version.yaml").write_text(
        f"---\nsubstitutions:\n  tft_version: '{version}'\n"
    )


def test_main_fails_on_a_changed_hmi_without_a_bump(repo):
    (repo / LANDSCAPE).write_bytes(b"hmi-2")
    _commit(repo, "edit screen")

    assert check_hmi_bump.main(["--base", "HEAD~1"]) == 1


def test_main_fails_on_a_recompiled_tft_without_a_bump(repo):
    (repo / LANDSCAPE_TFT).write_bytes(b"tft-2")
    _commit(repo, "recompile")

    assert check_hmi_bump.main(["--base", "HEAD~1"]) == 1


def test_main_passes_on_a_changed_hmi_with_a_bump(repo):
    (repo / LANDSCAPE).write_bytes(b"hmi-2")
    _write_tft_version(repo, "0.4.5.dev34")
    _commit(repo, "edit screen and bump")

    assert check_hmi_bump.main(["--base", "HEAD~1"]) == 0


def test_main_ignores_commits_without_a_display_change(repo):
    (repo / "README.md").write_text("docs only\n")
    _commit(repo, "docs only")

    assert check_hmi_bump.main(["--base", "HEAD~1"]) == 0
