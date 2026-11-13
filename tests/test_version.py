from __future__ import annotations

import json
from pathlib import Path

from custom_components.nspanel_haui.haui.version import (
    get_integration_version,
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
