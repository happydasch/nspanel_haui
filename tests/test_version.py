from __future__ import annotations

import json
from pathlib import Path

from custom_components.nspanel_haui.haui.version import (
    HUB_API_VERSION,
    get_integration_version,
    hub_api_compatible,
    integration_version_mismatch,
)

ROOT = Path(__file__).resolve().parent.parent


def test_integration_version_is_read_from_manifest() -> None:
    manifest = json.loads(
        (ROOT / "custom_components/nspanel_haui/manifest.json").read_text(encoding="utf-8")
    )

    assert get_integration_version() == manifest["version"]


def test_integration_version_mismatch_is_unknown_until_both_versions_are_reported() -> None:
    assert integration_version_mismatch("0.4.5", "0.4.5") is False
    assert integration_version_mismatch("0.4.5", "0.4.4") is True
    assert integration_version_mismatch("0.4.5", "") is None
    assert integration_version_mismatch("0.4.5", None) is None


def test_hub_api_compatible_compares_the_major_version() -> None:
    assert HUB_API_VERSION == "1.0"
    assert hub_api_compatible("1.0") is True
    assert hub_api_compatible("1.7") is True
    assert hub_api_compatible("2.0") is False


def test_hub_api_compatible_is_unknown_when_the_firmware_does_not_report_it() -> None:
    assert hub_api_compatible("") is None
    assert hub_api_compatible(None) is None


def test_hub_api_compatible_rejects_a_malformed_version() -> None:
    assert hub_api_compatible("api-one") is False
