"""Tests for the GitHub release firmware manifest generator."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "generate_firmware_manifest", ROOT / "scripts" / "release" / "generate_firmware_manifest.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


generator = _load_generator()


def test_manifest_keeps_the_embedded_tft_version_when_pinned(tmp_path):
    ota = tmp_path / "firmware.ota.bin"
    eu_tft = tmp_path / "nspanel_haui.tft"
    us_tft = tmp_path / "nspanel_haui_portrait.tft"
    ota.write_bytes(b"ota image")
    eu_tft.write_bytes(b"landscape TFT")
    us_tft.write_bytes(b"portrait TFT")

    manifest = generator.build_manifest(
        "example/nspanel-haui",
        "v0.4.4",
        ota,
        eu_tft,
        us_tft,
        tft_version="0.4.3",
    )

    assert manifest["version"] == "0.4.4"
    assert manifest["tft"]["version"] == "0.4.3"
    assert manifest["tft"]["assets"]["eu"] == {
        "path": "https://github.com/example/nspanel-haui/releases/download/v0.4.4/nspanel_haui.tft",
        "md5": hashlib.md5(b"landscape TFT", usedforsecurity=False).hexdigest(),
    }


def test_main_reads_the_tft_version_from_esphome_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", "example/nspanel-haui")
    monkeypatch.setenv("GITHUB_REF_NAME", "v0.4.4")
    Path("nspanel_haui_ota.bin").write_bytes(b"ota image")
    Path("nextion").mkdir()
    Path("nextion/nspanel_haui.tft").write_bytes(b"landscape TFT")
    Path("nextion/nspanel_haui_portrait.tft").write_bytes(b"portrait TFT")
    version_file = Path("esphome/nspanel_haui/version.yaml")
    version_file.parent.mkdir(parents=True)
    version_file.write_text(
        "substitutions:" + chr(10) + "  tft_version: '0.4.3'" + chr(10), encoding="utf-8"
    )
    monkeypatch.setattr(generator, "VERSION_YAML", version_file)

    generator.main([])

    manifest = json.loads(Path("firmware-manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "0.4.4"
    assert manifest["tft"]["version"] == "0.4.3"

    generator.main(["--tag", "0.4.5.dev7", "--name", "NSPanel HAUI Development"])

    manifest = json.loads(Path("firmware-manifest.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "NSPanel HAUI Development"
    assert manifest["version"] == "0.4.5.dev7"
    assert manifest["builds"][0]["ota"]["path"].endswith(
        "/download/0.4.5.dev7/nspanel_haui_ota.bin"
    )


def test_validate_manifest_refuses_a_manifest_without_tft_assets():
    manifest = generator.build_manifest_from_assets("0.4.4", "universal", "https://x/ota.bin", "0f")

    with pytest.raises(ValueError, match="TFT assets"):
        generator.validate_manifest(manifest)
