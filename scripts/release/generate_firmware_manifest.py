#!/usr/bin/env python3
"""Generate the GitHub release firmware manifest from the built artifacts.

The ``tft_version`` in ``esphome/nspanel_haui/version.yaml`` tracks the TFT
version separately from the firmware tag. The release uploads the TFT assets,
but the manifest must advertise the embedded TFT version when a release does
not include a TFT update.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

VERSION_YAML = Path("esphome/nspanel_haui/version.yaml")


def _md5(path: Path) -> str:
    """Return the release asset's MD5 checksum."""
    return hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()


def build_manifest_from_assets(
    version: str,
    variant: str,
    ota_url: str,
    ota_md5: str,
    tft: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the shared manifest schema from already-resolved asset metadata."""
    if variant not in {"universal", "custom"}:
        raise ValueError(f"unknown firmware variant {variant!r}")
    manifest: dict[str, Any] = {
        "name": "NSPanel HAUI",
        "version": version,
        "variant": variant,
        "builds": [
            {
                "chipFamily": "ESP32",
                "ota": {"path": ota_url, "md5": ota_md5},
            }
        ],
    }
    if tft is not None:
        manifest["tft"] = tft
    return manifest


def build_manifest(
    repo: str,
    tag: str,
    ota_image: Path,
    eu_tft: Path,
    us_tft: Path,
    tft_version: str | None = None,
) -> dict[str, Any]:
    """Build a release manifest with the TFT version required by its firmware."""
    version = tag.removeprefix("v")
    display_version = (tft_version or "").strip() or version
    release_url = f"https://github.com/{repo}/releases/download/{tag}"
    return build_manifest_from_assets(
        version,
        "universal",
        f"{release_url}/nspanel_haui_ota.bin",
        _md5(ota_image),
        {
            "version": display_version,
            "assets": {
                "eu": {
                    "path": f"{release_url}/nspanel_haui.tft",
                    "md5": _md5(eu_tft),
                },
                "us": {
                    "path": f"{release_url}/nspanel_haui_portrait.tft",
                    "md5": _md5(us_tft),
                },
            },
        },
    )


def _read_tft_version(path: Path) -> str:
    """Read the TFT release version from the shared ESPHome version package."""
    text = path.read_text(encoding="utf-8")
    match = re.search(r"(?m)^\s*tft_version:\s*'([^']+)'", text)
    if match is None:
        raise ValueError(f"{path}: tft_version is missing")
    return match.group(1)


def main() -> None:
    """Write the release manifest for the artifacts in the workflow workspace."""
    manifest = build_manifest(
        repo=os.environ["GITHUB_REPOSITORY"],
        tag=os.environ["GITHUB_REF_NAME"],
        ota_image=Path("nspanel_haui_ota.bin"),
        eu_tft=Path("nextion/nspanel_haui.tft"),
        us_tft=Path("nextion/nspanel_haui_portrait.tft"),
        tft_version=_read_tft_version(VERSION_YAML),
    )
    manifest_path = Path("firmware-manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
