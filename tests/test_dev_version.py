"""The development build version is derived from the branch's cycle and the run number.

``dev_version`` only prints the version; ``dev-firmware.yml`` writes it into
``manifest.json`` and ``version.yaml`` before it compiles, and uses it as the tag.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "dev_version", ROOT / "scripts" / "release" / "dev_version.py"
)
assert _spec and _spec.loader

dev_version = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dev_version)


def test_the_dev_version_is_the_cycle_and_the_run_number():
    assert dev_version.dev_version_for_cycle("0.4.5", 17) == "0.4.5.dev17"
    assert dev_version.dev_version_for_cycle("0.6.0", "512") == "0.6.0.dev512"
    with pytest.raises(ValueError, match="not a publishable"):
        # A cycle that already carries the run number would nest another one.
        dev_version.dev_version_for_cycle("0.6.0.dev0", 17)


def test_rejects_unsupported_branch_version():
    with pytest.raises(ValueError, match="Expected a stable X.Y.Z"):
        dev_version.cycle_of("0.4.4-beta1")


def test_the_next_patch_is_the_released_version_successor():
    assert dev_version.next_patch("0.5.4") == "0.5.5"
    assert dev_version.next_patch("0.9.9") == "0.9.10"
    with pytest.raises(ValueError, match="Expected a stable X.Y.Z release"):
        dev_version.next_patch("0.5.4.dev76")


def test_the_cycle_of_a_version_is_the_release_it_leads_to():
    assert dev_version.cycle_of("0.6.0.dev97") == "0.6.0"
    # A stable version is a release that is done: the branch works toward its next patch.
    assert dev_version.cycle_of("0.5.8") == "0.5.9"
    with pytest.raises(ValueError, match="Expected a stable X.Y.Z or a X.Y.Z.devN"):
        dev_version.cycle_of("0.5.8+local")


def test_version_kind_is_shared_with_manual_bumps():
    assert dev_version.version_kind("0.4.5.dev17") == "dev"
    assert dev_version.version_kind("0.4.5.dev17+gabcdef0") is None
    assert dev_version.version_kind("0.4.5") == "stable"
    assert dev_version.version_kind("0.4.5-dev17") is None


def test_a_build_continues_the_cycle_the_branch_reports():
    """The regression this guards: a cycle opened with ``--base 0.6.0.dev0`` was lost.

    The next dispatch fell back to the newest stable tag's next patch and published
    ``0.5.9.dev99`` over the ``0.6.0.dev97`` the branch already carried.
    """
    assert dev_version.resolve_cycle(None, "0.6.0.dev97", "0.5.8") == "0.6.0"
    assert dev_version.resolve_cycle(None, "0.5.9.dev100", "0.5.8") == "0.5.9"
    # The cycle order is numeric, not lexical: 0.9.0 would win a string comparison.
    assert dev_version.resolve_cycle(None, "0.10.0.dev5", "0.9.0") == "0.10.0"


def test_a_stable_branch_version_starts_its_successor():
    """A merged release leaves a stable version on the branch; dev moves on."""
    assert dev_version.resolve_cycle(None, "0.6.0", "0.6.0") == "0.6.1"


def test_a_released_hotfix_is_a_floor_dev_cannot_go_below():
    """A hotfix tags on master before its pull request merges back into dev."""
    assert dev_version.resolve_cycle(None, "0.5.8", "0.5.9") == "0.5.10"


def test_a_requested_base_below_the_branch_is_refused():
    with pytest.raises(ValueError, match="never counts backwards"):
        dev_version.resolve_cycle("0.5.9.dev0", "0.6.0.dev97", "0.5.8")
    # Opening the cycle the branch already reports is not a downgrade, and a minor
    # or major step up is what the input is for.
    assert dev_version.resolve_cycle("0.6.0.dev0", "0.6.0.dev97", "0.5.8") == "0.6.0"
    assert dev_version.resolve_cycle("0.7.0.dev0", "0.6.0.dev97", "0.5.8") == "0.7.0"


def test_the_base_comes_from_the_newest_release_tag(tmp_path: Path):
    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q")
    # An annotated tag needs an identity, which a CI runner's checkout does not have.
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    git("commit", "-q", "--allow-empty", "-m", "one")
    with pytest.raises(ValueError, match="no vX.Y.Z tag"):
        dev_version.base_from_tags(tmp_path)

    git("tag", "-a", "v0.5.4", "-m", "v0.5.4")
    assert dev_version.base_from_tags(tmp_path) == "0.5.4"


def test_the_branch_version_is_the_manifest_version(tmp_path: Path):
    manifest = tmp_path / "custom_components" / "nspanel_haui" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"version": "0.6.0.dev97"}), encoding="utf-8")
    assert dev_version.branch_version(tmp_path) == "0.6.0.dev97"

    with pytest.raises(ValueError, match="no integration version"):
        dev_version.branch_version(tmp_path / "missing")


def test_a_build_changes_no_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """The whole point: nothing in the tree is touched, so nothing is committed."""
    output = tmp_path / "github-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr(dev_version, "shipped_tft_version", lambda: "1.1.0")
    monkeypatch.setattr(dev_version, "branch_version", lambda root: "0.5.5.dev76")
    monkeypatch.setattr(dev_version, "base_from_tags", lambda root: "0.5.4")

    assert dev_version.main(["77"]) == 0
    written = output.read_text(encoding="utf-8")
    assert "version=0.5.5.dev77" in written
    assert "tft_version=1.1.0" in written
    # No version file exists under tmp_path and none was created or read.
    assert sorted(p.name for p in tmp_path.iterdir()) == ["github-output"]


def test_a_build_that_would_count_backwards_fails_before_bumping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    output = tmp_path / "github-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr(dev_version, "branch_version", lambda root: "0.6.0.dev97")
    monkeypatch.setattr(dev_version, "base_from_tags", lambda root: "0.5.8")

    # Nothing is written and no version is printed, so the workflow cannot publish.
    assert dev_version.main(["99", "--base", "0.5.9.dev0"]) == 1
    assert not output.exists()
    assert "never counts backwards" in capsys.readouterr().err
