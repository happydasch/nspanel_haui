---
title: Frequently Asked Questions
description: Common issues, troubleshooting, and tips for NSPanel HAUI
---

# FAQ

## Getting started

### I don't know how to start

Follow the [Quick Start Guide](get-started.md). After that, the [Panel overview](panels/README.md) shows what each panel type does and the [examples](examples.md) show layouts for common rooms.

### My NSPanel devices are not discovered

Add the panel to Home Assistant's ESPHome integration first; the editor only lists panels it finds there. See [Device Discovery Issues](troubleshooting.md#device-discovery-issues).

## Updates

### How do I install a TFT file?

Normally you don't have to: the hub installs the TFT the firmware needs when the panel connects. To install one yourself:

- **In the editor:** press **Install** beside **Display** in the **Updates** sidebar, then choose a release, **From URL** or **From local file**.
- **In Home Assistant:** press **Install** on the panel's **HAUI Display** update entity.
- **In an automation:** call `nspanel_haui.update_tft`. Add `url` to install your own TFT file.

See [Services](services.md#nspanel_hauiupdate_tft) for the details.

### An update fails or is not possible

See [TFT Upload Failures](troubleshooting.md#tft-upload-failures) and [Updating → If something goes wrong](update.md#if-something-goes-wrong).

### A development firmware shows an older "latest version"

The panel still follows the stable channel. Development builds belong to the *next* release (`0.4.5.dev123` while `0.4.4` is the stable one) and are only published on the dev channel.

Open the device's **Updates** sidebar, set **Update channel** to **Development** and leave **Custom manifest URL** empty. The hub then follows the newest [development release](../develop/release.md#published-development-firmware), which also includes the matching display TFT.

Two older development builds need one manual step. Install a newer build once with **Install** beside **Firmware** in the **Updates** sidebar, then choose its version:

- a panel that reports a version like `dev-3-f243f33` (dev builds up to 0.4.4)
- a panel on a build like `0.4.5.dev16+g778f2ce` (published before 2026-11-04)

The hub cannot compare these versions correctly, so it never offers them an update.

## Display

### The log shows an error when the display turns off

The entry is harmless. See [Display-Off Errors](troubleshooting.md#display-off-errors).

### The display should change its brightness over the day

Use the **Schedule** option in **Manage this device** on the device's **Preview** view. Add an entry for each time window, from a time, sunrise or sunset (with an offset in minutes) to a time, sunrise or sunset, and set its brightness. Outside the entries, **Brightness full** and **Brightness dimmed** in the **Screen** section of the device settings apply. See [Schedule](configuration/device.md#schedule).

Without a schedule and without a **Brightness full** value, the brightness stays manual. An automation that sets `number.<device>_brightness_full` and `number.<device>_brightness_dimmed` works as before.

### The display should turn off completely only at night

Turn **Auto display off** off in the device settings and add a **Schedule** entry for the night with **Screen off** on. See [Schedule](configuration/device.md#schedule).

Without a schedule, a Home Assistant automation can switch `switch.<device>_use_auto_display_off` on in the evening and off in the morning. The integration does not change this switch on its own then, so the automation stays in control. See [Screen](configuration/device.md#screen).

While the panel has no connection to Home Assistant, the display never turns off; it only dims.
