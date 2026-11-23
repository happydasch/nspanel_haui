#!/usr/bin/env bash
# Compile the universal firmware and copy its two images to the repository root, for
# release.yml and dev-firmware.yml. They are not interchangeable: firmware.factory.bin
# (nspanel_haui.bin) is a full flash image for serial flashing, firmware.ota.bin
# (nspanel_haui_ota.bin) the app image the HTTP OTA platform writes.
#
# YAML_VERSION overrides the version the image reports, so a development build can
# carry X.Y.Z.devN without committing it: the branch keeps the released version.
set -euo pipefail

substitutions=()
if [ -n "${YAML_VERSION:-}" ]; then
  substitutions=(-s yaml_version "$YAML_VERSION")
fi

esphome "${substitutions[@]}" compile esphome/nspanel_haui_universal.yaml
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

