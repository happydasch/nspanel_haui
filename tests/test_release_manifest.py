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
    eu_tft.write_bytes(b"landscape TFT\x000.4.3\x00")
    us_tft.write_bytes(b"portrait TFT\x000.4.3\x00")

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
        "md5": hashlib.md5(b"landscape TFT\x000.4.3\x00", usedforsecurity=False).hexdigest(),
    }


def test_manifest_refuses_a_tft_that_does_not_carry_the_tft_version(tmp_path):
    ota = tmp_path / "firmware.ota.bin"
    eu_tft = tmp_path / "nspanel_haui.tft"
    us_tft = tmp_path / "nspanel_haui_portrait.tft"
    ota.write_bytes(b"ota image")
    eu_tft.write_bytes(b"landscape TFT\x000.4.3\x00")
    us_tft.write_bytes(b"portrait TFT\x000.4.2\x00")

    with pytest.raises(ValueError, match="nspanel_haui_portrait.tft does not carry"):
        generator.build_manifest("example/nspanel-haui", "v0.4.4", ota, eu_tft, us_tft, "0.4.3")


def test_main_reads_the_tft_version_from_esphome_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", "example/nspanel-haui")
    monkeypatch.setenv("GITHUB_REF_NAME", "v0.4.4")
    Path("nspanel_haui_ota.bin").write_bytes(b"ota image")
    Path("nextion").mkdir()
    Path("nextion/nspanel_haui.tft").write_bytes(b"landscape TFT\x000.4.3\x00")
    Path("nextion/nspanel_haui_portrait.tft").write_bytes(b"portrait TFT\x000.4.3\x00")
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


def _release_assets(tmp_path, tft_version="0.4.3"):
    """The files a release workflow assembles, minus the repair TFTs."""
    ota = tmp_path / "firmware.ota.bin"
    eu_tft = tmp_path / "nspanel_haui.tft"
    us_tft = tmp_path / "nspanel_haui_portrait.tft"
    ota.write_bytes(b"ota image")
    eu_tft.write_bytes(b"landscape TFT\x00" + tft_version.encode() + b"\x00")
    us_tft.write_bytes(b"portrait TFT\x00" + tft_version.encode() + b"\x00")
    return ota, eu_tft, us_tft


def _repair_tfts(tmp_path, version=None):
    version = version or generator.REPAIR_VERSION
    eu = tmp_path / "nspanel_haui_repair.tft"
    us = tmp_path / "nspanel_haui_repair_portrait.tft"
    eu.write_bytes(b"repair TFT\x00" + version.encode() + b"\x00")
    us.write_bytes(b"repair portrait TFT\x00" + version.encode() + b"\x00")
    return {"eu": eu, "us": us}


def test_manifest_names_the_repair_tfts_the_release_ships(tmp_path, monkeypatch):
    ota, eu_tft, us_tft = _release_assets(tmp_path)
    repair = _repair_tfts(tmp_path)
    monkeypatch.setattr(generator, "REPAIR_TFTS", repair)

    manifest = generator.build_manifest(
        "example/nspanel-haui", "v0.4.4", ota, eu_tft, us_tft, "0.4.3"
    )

    assert manifest["repair"]["version"] == generator.REPAIR_VERSION
    assert manifest["repair"]["assets"]["eu"] == {
        "path": (
            "https://github.com/example/nspanel-haui/releases/download/v0.4.4/"
            "nspanel_haui_repair.tft"
        ),
        "md5": hashlib.md5(b"repair TFT\x001\x00", usedforsecurity=False).hexdigest(),
    }
    assert manifest["repair"]["assets"]["us"]["path"].endswith("/nspanel_haui_repair_portrait.tft")


def test_manifest_leaves_the_repair_block_out_without_the_assets(tmp_path, monkeypatch):
    """A release that ships no repair TFT names none, so the hub reports that."""
    ota, eu_tft, us_tft = _release_assets(tmp_path)
    monkeypatch.setattr(generator, "REPAIR_TFTS", {"eu": tmp_path / "missing.tft"})

    manifest = generator.build_manifest(
        "example/nspanel-haui", "v0.4.4", ota, eu_tft, us_tft, "0.4.3"
    )

    assert "repair" not in manifest


def test_manifest_refuses_a_repair_tft_that_does_not_carry_its_version(tmp_path, monkeypatch):
    ota, eu_tft, us_tft = _release_assets(tmp_path)
    monkeypatch.setattr(generator, "REPAIR_TFTS", _repair_tfts(tmp_path, version="2"))

    with pytest.raises(ValueError, match="does not carry"):
        generator.build_manifest("example/nspanel-haui", "v0.4.4", ota, eu_tft, us_tft, "0.4.3")


def test_validate_manifest_refuses_a_partial_repair_block():
    manifest = generator.build_manifest_from_assets(
        "0.4.4",
        "universal",
        "https://x/ota.bin",
        "0f",
        {"version": "0.4.4", "assets": {"eu": {"path": "a.tft", "md5": "a"}}},
        {"version": "1", "assets": {"eu": {"path": "r.tft", "md5": "r"}}},
    )

    with pytest.raises(ValueError, match="us repair TFT"):
        generator.validate_manifest(manifest)


def test_committed_repair_tfts_carry_the_manifest_repair_version():
    """A release publishes these files only when they are committed and valid."""
    from scripts.verify_nextion.check_repair_tft import check_repair_tft

    missing = [path for path in generator.REPAIR_TFTS.values() if not path.exists()]
    if missing:
        pytest.skip("no repair TFTs are committed yet")
    for path in generator.REPAIR_TFTS.values():
        assert check_repair_tft(ROOT / path) is None


def test_repair_check_names_a_missing_and_a_wrong_version(tmp_path):
    from scripts.verify_nextion.check_repair_tft import check_repair_tft

    assert "missing" in (check_repair_tft(tmp_path / "nothing.tft") or "")
    wrong = tmp_path / "wrong.tft"
    wrong.write_bytes(b"repair TFT\x002\x00")
    assert "does not carry" in (check_repair_tft(wrong) or "")
    good = tmp_path / "good.tft"
    good.write_bytes(b"repair TFT\x00" + generator.REPAIR_VERSION.encode() + b"\x00")
    assert check_repair_tft(good) is None
