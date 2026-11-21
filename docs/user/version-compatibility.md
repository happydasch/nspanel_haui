---
title: Version compatibility
description: Which Home Assistant, firmware and display versions work together
---

# Version compatibility

NSPanel HAUI ships the integration and the firmware together, and the hub installs the matching display TFT.
This page lists what each part needs, so an upgrade does not leave the parts disagreeing.

## Supported versions

| Part | Requirement |
|------|-------------|
| Home Assistant | 2026.11 or later |
| Integration | The latest stable release |
| Firmware | The latest stable release for the panel's update channel; installed by the hub |
| Display TFT | Installed by the hub; its version can differ from the firmware's |
| ESPHome, custom builds | 2026.11.0 or later, enforced when the firmware is compiled |

The prebuilt `nspanel_haui.bin` needs no local ESPHome installation. You only need ESPHome to
[build your own firmware](../develop/esphome.md#installation), and an older ESPHome refuses the build with a
clear `min_version` error.

Home Assistant cannot be older than the Marketplace requirement above: the integration is installed and
updated through it.

## Firmware and display versions

The firmware and the display are updated independently:

- The **HAUI Firmware** update entity installs a newer firmware image.
- The **HAUI Display** entity installs the TFT the firmware requires.
- A firmware-only release keeps its display version, so the panel is not sent a TFT it does not need.
- The editor's device row shows both versions and marks a mismatch. The diagnostics card also shows the TFT
  version the firmware requires.

The hub checks the firmware build variant before installing an update. A universal image is not installed on
a custom build, and a custom build is not replaced by the universal image.

## Upgrade order

1. Update the integration.
2. Let the hub update the firmware; it follows the installed release or the channel you selected.
3. The hub installs the matching TFT after the panel reconnects.

The hub can update a panel whose firmware is older than the integration. It reports the version mismatch in
the editor rather than blocking the panel; only an incompatible firmware build variant is refused. If a panel
is too old for a feature, install the current firmware from its **Updates** sidebar, then reopen the editor.

## Development releases

Development releases use a PEP 440 version such as `0.5.3.dev42`. They are published as GitHub prereleases and
are not supported for everyday use. To try one, set the device's **Update channel** to **Development** in the
**Updates** sidebar; switch back to **Stable** to leave it.

Development firmware and development display assets are built together, so keep the panel on the same channel
as the integration. A panel that reports an older development format may need one manual firmware install; see
the [FAQ](faq.md#a-development-firmware-shows-an-older-latest-version).
