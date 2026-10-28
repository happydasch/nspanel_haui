"""Tests for the local test-release script (``scripts/dev_release.py``)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "http://homeassistant.local:8123/local/nspanel"
MANIFEST_URL = f"{BASE_URL}/firmware-manifest.json"


def _load():
    spec = importlib.util.spec_from_file_location(
        "dev_release", ROOT / "scripts" / "dev_release.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


dev_release = _load()


def _image(version="0.4.3-dev1", manifest_url=MANIFEST_URL, first=b"\xe9"):
    """A fake app image carrying the strings a real build embeds."""
    return first + b"\0app\0" + version.encode() + b"\0" + manifest_url.encode() + b"\0rest"


def _write(tmp_path, data):
    image = tmp_path / "firmware.ota.bin"
    image.write_bytes(data)
    return image


def test_release_writes_the_image_and_a_matching_manifest(tmp_path):
    data = _image()
    out = tmp_path / "www"

    image_out, manifest_out = dev_release.release(
        _write(tmp_path, data), "0.4.3-dev1", BASE_URL + "/", out
    )

    assert image_out.read_bytes() == data
    assert json.loads(manifest_out.read_text()) == {
        "name": "NSPanel HAUI",
        "version": "0.4.3-dev1",
        "builds": [
            {
                "chipFamily": "ESP32",
                "ota": {
                    "path": f"{BASE_URL}/nspanel_haui_ota.bin",
                    "md5": hashlib.md5(data, usedforsecurity=False).hexdigest(),
                },
            }
        ],
    }


@pytest.mark.parametrize(
    ("data", "error"),
    [
        pytest.param(_image(first=b"\xff"), "not the factory image", id="factory-image"),
        pytest.param(_image(version="0.4.2"), "yaml_version: '0.4.3-dev1'", id="other-version"),
        pytest.param(
            _image(manifest_url="https://github.com/x/firmware-manifest.json"),
            f"firmware_manifest_url: {MANIFEST_URL}",
            id="github-manifest",
        ),
        pytest.param(
            _image() + b"\0" * dev_release.FIRMWARE_MAX_BYTES, "app partition", id="too-big"
        ),
    ],
)
def test_release_refuses_an_image_that_would_misbehave(tmp_path, data, error):
    with pytest.raises(ValueError, match=error):
        dev_release.release(_write(tmp_path, data), "0.4.3-dev1", BASE_URL, tmp_path / "www")

    assert not (tmp_path / "www").exists()


def test_main_reports_a_refused_image(tmp_path, capsys):
    image = _write(tmp_path, _image(first=b"\xff"))

    code = dev_release.main(
        ["--image", str(image), "--version", "0.4.3-dev1", "--base-url", BASE_URL,
         "--out", str(tmp_path / "www")]
    )

    assert code == 1
    assert "factory image" in capsys.readouterr().err


def test_a_version_only_matches_as_a_whole_string():
    """``0.4.3`` must not match inside ``0.4.3-dev1``."""
    assert dev_release.check_image(_image(version="0.4.3-dev1"), "0.4.3", MANIFEST_URL)
