#!/usr/bin/env python3
"""Turn a local firmware build into a test release served by Home Assistant.

Test firmware must not go through GitHub: the release workflow publishes every
``v*`` tag as the latest release, and every panel's HAUI Firmware entity reads
``releases/latest/download/firmware-manifest.json`` and installs it.  This
script instead writes the two files a release carries for over-the-air
updates into a folder Home Assistant serves (``/config/www`` is served as
``/local``):

- ``nspanel_haui_ota.bin`` — the OTA app image of the build
- ``firmware-manifest.json`` — the schema the release workflow writes
  (name / version / builds[].ota with the absolute image URL and its md5)

Build the test panel's firmware with two substitutions, and the script refuses
an image that lacks either:

- ``yaml_version`` equal to ``--version``: ESPHome offers an update whenever
  the manifest version differs from the running build's, so a mismatch would
  install the image over and over.  Each test release needs a newer version
  (``0.4.3-dev1``, ``0.4.3-dev2``, ...), because Home Assistant only turns the
  update entity on for a newer version.
- ``firmware_manifest_url`` pointing at the written manifest: a build that
  still reads the GitHub manifest sees the release as an update, and the hub
  reinstalls the release over the test build.

Usage:
    python scripts/dev_release.py \\
        --image esphome/.esphome/build/nspanel-test/build/firmware.ota.bin \\
        --version 0.4.3-dev1 \\
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


def check_image(data: bytes, version: str, manifest_url: str) -> str | None:
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
            f"yaml_version: '{version}' (ESPHome reinstalls a build whose version "
            "differs from the manifest)"
        )
    # Without it the installed build reads the GitHub manifest again, sees the
    # release version as an update and the hub reinstalls the release over it.
    if b"\0" + manifest_url.encode() + b"\0" not in data:
        return (
            f"the image does not read {manifest_url}; build it with "
            f"firmware_manifest_url: {manifest_url}"
        )
    return None


def build_manifest(version: str, image_url: str, md5: str) -> dict:
    """The manifest in the schema the release workflow writes."""
    return {
        "name": "NSPanel HAUI",
        "version": version,
        "builds": [{"chipFamily": "ESP32", "ota": {"path": image_url, "md5": md5}}],
    }


def release(image: Path, version: str, base_url: str, out: Path) -> tuple[Path, Path]:
    """Copy ``image`` into ``out`` and write its manifest next to it.

    Raises:
        ValueError: When the image or the base URL cannot be used
    """
    if not base_url.startswith(("http://", "https://")):
        raise ValueError(f"--base-url must start with http:// or https:// ({base_url!r})")
    base_url = base_url.rstrip("/")
    data = image.read_bytes()
    problem = check_image(data, version, f"{base_url}/{MANIFEST_NAME}")
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
    )
    manifest_out = out / MANIFEST_NAME
    manifest_out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return image_out, manifest_out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--image", type=Path, required=True, help="firmware.ota.bin of the build")
    parser.add_argument(
        "--version", required=True, help="the build's yaml_version, e.g. 0.4.3-dev1"
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="URL the output folder is served at, e.g. http://homeassistant.local:8123/local/nspanel",
    )
    parser.add_argument(
        "--out", type=Path, required=True, help="output folder, e.g. Home Assistant's www/nspanel"
    )
    args = parser.parse_args(argv)
    try:
        image_out, manifest_out = release(args.image, args.version, args.base_url, args.out)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    base_url = args.base_url.rstrip("/")
    print(f"wrote {image_out}")
    print(f"wrote {manifest_out}")
    print()
    print("The HAUI Firmware entity of a panel running an earlier test build offers it;")
    print("install it there or with Device Manager → Install firmware, or flash it with")
    print(f"nspanel_haui.update_firmware and url: {base_url}/{IMAGE_NAME}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
