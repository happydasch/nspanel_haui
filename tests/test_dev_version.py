"""The development build version is derived, never written into the tree.

A dev build is not a commit: ``dev_version`` only prints the version, which
``dev-firmware.yml`` injects into the image with ``esphome -s`` and uses as the tag.
"""

from __future__ import annotations

import importlib.util
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


def test_derives_dev_version_from_stable_and_previous_dev():
    assert dev_version.derive_dev_version("0.4.4", 17) == "0.4.5.dev17"
    assert dev_version.derive_dev_version("0.4.5.dev16", 17) == "0.4.5.dev17"


def test_rejects_unsupported_branch_version():
    with pytest.raises(ValueError, match="Expected a stable X.Y.Z"):
        dev_version.derive_dev_version("0.4.4-beta1", 17)


def test_the_next_patch_is_the_released_version_successor():
    assert dev_version.next_patch("0.5.4") == "0.5.5"
    assert dev_version.next_patch("0.9.9") == "0.9.10"
    with pytest.raises(ValueError, match="Expected a stable X.Y.Z release"):
        dev_version.next_patch("0.5.4.dev76")


def test_version_kind_is_shared_with_manual_bumps():
    assert dev_version.version_kind("0.4.5.dev17") == "dev"
    assert dev_version.version_kind("0.4.5.dev17+gabcdef0") is None
    assert dev_version.version_kind("0.4.5") == "stable"
    assert dev_version.version_kind("0.4.5-dev17") is None


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


def test_a_build_changes_no_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """The whole point: nothing in the tree is touched, so nothing is committed."""
    output = tmp_path / "github-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr(dev_version, "shipped_tft_version", lambda: "0.4.5")

    assert dev_version.main(["77", "--base", "0.5.4"]) == 0
    written = output.read_text(encoding="utf-8")
    assert "version=0.5.5.dev77" in written
    assert "tft_version=0.4.5" in written
    # No version file exists under tmp_path and none was created or read.
    assert sorted(p.name for p in tmp_path.iterdir()) == ["github-output"]
