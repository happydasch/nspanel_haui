from __future__ import annotations

import json
import re
from pathlib import Path

from custom_components.nspanel_haui.haui.version import firmware_version_mismatch

ROOT = Path(__file__).resolve().parent.parent


def test_manifest_version_matches_esphome_firmware_version() -> None:
    manifest = json.loads(
        (ROOT / "custom_components/nspanel_haui/manifest.json").read_text(encoding="utf-8")
    )
    yaml = (ROOT / "esphome/nspanel_haui/version.yaml").read_text(encoding="utf-8")
    match = re.search(r"(?m)^\s*yaml_version:\s*['\"]([^'\"]+)['\"]", yaml)

    assert match is not None
    assert manifest["version"] == match.group(1)


def test_firmware_version_mismatch_is_unknown_until_both_versions_are_reported() -> None:
    assert firmware_version_mismatch("0.4.5", "0.4.5") is False
    assert firmware_version_mismatch("0.4.5", "0.4.4") is True
    assert firmware_version_mismatch("0.4.5", "") is None
    assert firmware_version_mismatch("0.4.5", None) is None
