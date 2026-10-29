#!/usr/bin/env python3
"""Turn a local firmware build into a test release served by Home Assistant.

Test firmware must not go through GitHub: the release workflow publishes every
``v*`` tag as the latest release, and the HAUI Firmware entity of every panel
reads ``releases/latest/download/firmware-manifest.json`` and installs it.
This script instead writes the two files a release carries for over-the-air
updates into a folder Home Assistant serves (``/config/www`` is served as
``/local``):

- ``nspanel_haui_ota.bin`` — the OTA app image of the build
- ``firmware-manifest.json`` — the schema the release workflow writes
  (name / version / builds[].ota with the absolute image URL and its md5)

Point the test panel's *Firmware manifest URL* (device editor → Updates) at
the written manifest; its HAUI Firmware entity then offers each newer test
release, and the hub installs it like a GitHub release.

Build the firmware with ``yaml_version`` equal to ``--version``; the script
refuses an image without it.  The hub offers the manifest's firmware whenever
its version is newer than the one the panel runs, so an image that reports an
older version would be installed over and over.  Each test release needs a newer version
(``0.4.4-dev1``, ``0.4.4-dev2``, ...), because the hub only offers a newer one.

Usage:
    python scripts/dev_release.py \\
        --image esphome/.esphome/build/nspanel-test/build/firmware.ota.bin \\
        --version 0.4.4-dev1 \\
        --base-url http://homeassistant.local:8123/local/nspanel \\
        --out /Volumes/config/www/nspanel

Exit code 0 when both files were written, 1 when the image was refused.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

IMAGE_NAME = "nspanel_haui_ota.bin"
MANIFEST_NAME = "firmware-manifest.json"
# Mirrors the hub's checks (haui/controller/update.py): the app partition of
# the shipped partition table, and the first byte of an ESP32 app image (a
# factory image starts with 0xFF padding and must never be written over the air).
FIRMWARE_MAX_BYTES = 0x1C0000
ESP_IMAGE_MAGIC = 0xE9


def check_image(data: bytes, version: str) -> str | None:
    """Return why ``data`` cannot be released as ``version``, or None when it can."""
    if not data or data[0] != ESP_IMAGE_MAGIC:
        return (
            "not an ESP32 app image; use the OTA image (firmware.ota.bin), "
            "not the factory image"
        )
    if len(data) > FIRMWARE_MAX_BYTES:
        return f"{len(data)} bytes do not fit the {FIRMWARE_MAX_BYTES} byte app partition"
    # The build embeds its yaml_version as a C string (ESPHOME_PROJECT_VERSION).
    if b"\0" + version.encode() + b"\0" not in data:
        return (
            f"the image does not contain version {version!r}; build it with "
            f"yaml_version: '{version}' (the hub reinstalls a build whose version "
            "is older than the manifest's)"
        )
    return None


def build_manifest(version: str, image_url: str, md5: str, variant: str = "custom") -> dict:
    """The manifest in the schema the release workflow writes.

    ``variant`` mirrors what the running firmware reports as its build
    identity (``custom`` for a build from ``install.yaml``/``nspanel_haui_dev.yaml``;
    the GitHub release workflow writes ``universal`` for the prebuilt image).
    The hub refuses to install a manifest whose variant does not match the
    panel's, so a test release must name the variant of the panel that follows it.
    """
    return {
        "name": "NSPanel HAUI",
        "version": version,
        "variant": variant,
        "builds": [{"chipFamily": "ESP32", "ota": {"path": image_url, "md5": md5}}],
    }


def release(image: Path, version: str, base_url: str, out: Path, variant: str = "custom") -> tuple[Path, Path]:
    """Copy ``image`` into ``out`` and write its manifest next to it.

    Raises:
        ValueError: When the image or the base URL cannot be used
    """
    if not base_url.startswith(("http://", "https://")):
        raise ValueError(f"--base-url must start with http:// or https:// ({base_url!r})")
    base_url = base_url.rstrip("/")
    data = image.read_bytes()
    problem = check_image(data, version)
    if problem:
        raise ValueError(f"{image}: {problem}")
    out.mkdir(parents=True, exist_ok=True)
    image_out = out / IMAGE_NAME
    if image.resolve() != image_out.resolve():
        shutil.copyfile(image, image_out)
    manifest = build_manifest(
        version,
        f"{base_url}/{IMAGE_NAME}",
        hashlib.md5(data, usedforsecurity=False).hexdigest(),
        variant,
    )
    manifest_out = out / MANIFEST_NAME
    manifest_out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return image_out, manifest_out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--image", type=Path, required=True, help="firmware.ota.bin of the build")
    parser.add_argument(
        "--version", required=True, help="the build's yaml_version, e.g. 0.4.4-dev1"
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="URL the output folder is served at, e.g. http://homeassistant.local:8123/local/nspanel",
    )
    parser.add_argument(
        "--out", type=Path, required=True, help="output folder, e.g. Home Assistant's www/nspanel"
    )
    parser.add_argument(
        "--variant",
        default="custom",
        help="build variant the panel reports (universal for the prebuilt image, "
        "custom otherwise); only matching variants can install the release",
    )
    args = parser.parse_args(argv)
    try:
        image_out, manifest_out = release(
            args.image, args.version, args.base_url, args.out, args.variant
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
        return 1
    base_url = args.base_url.rstrip("/")
    print(f"wrote {image_out}")
    print(f"wrote {manifest_out}")
    print()
    print("With its Firmware manifest URL (device editor → Updates) set to")
    print(f"{base_url}/{MANIFEST_NAME}, the HAUI Firmware entity of a test panel")
    print("running an earlier test build offers it; install it there or with Device")
    print("Manager → Install firmware, or flash it with nspanel_haui.update_firmware")
    print(f"and url: {base_url}/{IMAGE_NAME}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
