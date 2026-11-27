#!/usr/bin/env bash
# Compile the universal firmware and copy its two images to the repository root, for
# release.yml and dev-firmware.yml. They are not interchangeable: firmware.factory.bin
# (nspanel_haui.bin) is a full flash image for serial flashing, firmware.ota.bin
# (nspanel_haui_ota.bin) the app image the HTTP OTA platform writes.
#
# The image reports yaml_version, which both workflows write before calling this
# (scripts.bump_version), so the image, the tag and the branch cannot disagree.
set -euo pipefail

esphome compile esphome/nspanel_haui_universal.yaml
factory=$(find esphome/.esphome -name firmware.factory.bin -path "*nspanel-haui*" -print -quit)
if [ -z "$factory" ]; then
  echo "firmware.factory.bin not found after compile" >&2
  exit 1
fi
ota="$(dirname "$factory")/firmware.ota.bin"
if [ ! -f "$ota" ]; then
  echo "firmware.ota.bin not found after compile" >&2
  exit 1
fi
cp "$factory" nspanel_haui.bin
cp "$ota" nspanel_haui_ota.bin
ls -lh nspanel_haui.bin nspanel_haui_ota.bin

