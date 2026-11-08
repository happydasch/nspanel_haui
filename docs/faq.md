---
title: Frequently Asked Questions
description: Common issues, troubleshooting, and tips for NSPanel HAUI
---

# FAQ
## I don't know how to start

Take a look at the [Panel Configuration](configuration/panels.md) reference and the [Panel Overview](panels/README.md) for details.

## How to upload a TFT file

The hub installs the TFT the firmware needs automatically when the device connects. To install it by hand:

- In the editor: **Device actions → Info → Install update → Display (TFT)**, then
  select a release, **From URL**, or **From local file**
- In Home Assistant: **Install** on the device's `HAUI Display` update entity
- Using a service: `nspanel_haui.update_tft` (add `url` to install a custom TFT file)

See the [Services Reference](services.md#tft-display-upload) for full details.

## Update is not possible

## Dev firmware looks older than the installed version

A panel running development firmware shows an older **latest version** (or an
update it cannot install) when it still follows the stable channel. Dev builds
are pre-releases of the *next* patch line (`0.4.5.dev123` when `0.4.4`
is stable) and are published only on the dev channel — switch the device's
**Firmware update channel** to **dev** and leave its **Firmware manifest URL**
empty; the hub then follows the newest
[published dev prerelease](release.md#published-development-firmware).
Dev prereleases ship the display TFT the dev firmware needs, so the **HAUI
Display** entity installs it after the firmware update. A panel that reports a version like
`dev-3-f243f33` — the old `dev-<run>-<sha>` tag scheme, used as `yaml_version`
by dev builds up to 0.4.4 — is not a valid version: the hub withholds firmware
offers until it is reflashed with a parseable build (see
[Release](release.md#published-development-firmware)). Current dev releases are
tagged with their PEP 440 version (for example `0.4.5.dev123`). A panel on a
build published before 2026-11-04 (`0.4.5.dev16+g778f2ce` style) is not offered
newer dev builds or the final release, because Home Assistant sorts the
`+g<sha>` segment above them: install a newer build once with **Install
firmware** and its version.

## Update is not possible

See [TFT Upload Failures](troubleshooting.md#tft-upload-failures).

## Error on sleep

See [Sleep Errors](troubleshooting.md#display-off-errors). The log entry is harmless.

## The display should change its brightness over the day

Use **Day/Night Profiles** in Device Settings → Day/Night Profiles. Choose a fixed local clock window or Home Assistant sunrise/sunset with independent minute offsets, then set Day and Night brightness, dimming, page, idle-page and timeout behavior. The global **Auto-Dimming** and **Auto Display-Off** switches remain independent of the profile; automations can control their live states. See [Day/Night profiles](configuration/device.md#daynight-profiles) and [Display dimming & off](configuration/device.md#display-dimming-off).

With the Day/Night schedule **disabled**, the ESPHome brightness sliders remain manual and the usual automation that writes `number.<device>_brightness_full` / `number.<device>_brightness_dimmed` still works.

## The display should turn off completely only at night

Use a Home Assistant automation to set `switch.<device>_use_auto_display_off` according to your schedule. HAUI does not overwrite automation-controlled auto-switch states on reconnects, page changes, profile changes, or unrelated settings saves. Turn the switch off to prevent automatic display-off; turn it on to allow off after the configured timeout. While the hub is disconnected, the display never turns off automatically and dims after the configured dimming timeout. See [Display dimming & off](configuration/device.md#display-dimming-off).

## My NSPanel devices are not discovered

See [Device Discovery Issues](troubleshooting.md#device-discovery-issues).
