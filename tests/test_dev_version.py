from __future__ import annotations

import importlib.util
import json
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


def test_writes_the_shared_firmware_version_sources(tmp_path: Path):
    manifest_dir = tmp_path / "custom_components/nspanel_haui"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.json").write_text(
        json.dumps({"domain": "nspanel_haui", "version": "0.4.4"}, indent=2) + "\n",
        encoding="utf-8",
    )
    version_dir = tmp_path / "esphome/nspanel_haui"
    version_dir.mkdir(parents=True)
    (version_dir / "version.yaml").write_text(
        "substitutions:\n  yaml_version: '0.4.4'\n  tft_version: '0.4.3'\n",
        encoding="utf-8",
    )
    env_file = tmp_path / "github.env"

    assert dev_version.write_dev_version(tmp_path, 17, env_file) == "0.4.5.dev17"

    assert json.loads((manifest_dir / "manifest.json").read_text())["version"] == "0.4.5.dev17"
    assert "yaml_version: '0.4.5.dev17'" in (version_dir / "version.yaml").read_text()
    assert "tft_version: '0.4.3'" in (version_dir / "version.yaml").read_text()
    assert env_file.read_text() == "DEV_VERSION=0.4.5.dev17\n"


def test_writes_the_shipped_tft_version(tmp_path: Path):
    version_dir = tmp_path / "esphome/nspanel_haui"
    version_dir.mkdir(parents=True)
    version_file = version_dir / "version.yaml"
    version_file.write_text(
        "substitutions:\n  yaml_version: '0.4.5.dev17'\n  tft_version: '0.4.3'\n",
        encoding="utf-8",
    )
    env_file = tmp_path / "github.env"

    dev_version.write_tft_version(tmp_path, "0.4.5", env_file)

    assert "tft_version: '0.4.5'" in version_file.read_text()
    assert "yaml_version: '0.4.5.dev17'" in version_file.read_text()
    assert env_file.read_text() == "TFT_VERSION=0.4.5\n"


def test_version_kind_is_shared_with_manual_bumps():
    assert dev_version.version_kind("0.4.5.dev17") == "dev"
    assert dev_version.version_kind("0.4.5.dev17+gabcdef0") is None
    assert dev_version.version_kind("0.4.5") == "stable"
    assert dev_version.version_kind("0.4.5-dev17") is None
