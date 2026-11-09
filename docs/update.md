---
title: Updating
description: How to update NSPanel HAUI and where the breaking changes are documented
---

# Updating

NSPanel HAUI has three parts, each with its own version:

| Part | What it is | How it is updated |
|------|------------|-------------------|
| Integration | The hub in Home Assistant, including the editor | Home Assistant's Marketplace, then a Home Assistant restart |
| Firmware | ESPHome on the panel's ESP32 | By the hub: the panel's **HAUI Firmware** update |
| Display | The TFT file on the panel's Nextion screen | By the hub, automatically after the firmware |

The HAUI integration version and firmware `yaml_version` must be the same; the
Device Manager flags a known mismatch. The display TFT has its own version and may
legitimately differ: firmware reports `tft_required_version`, and the hub updates
the display only when its installed `tft_version` is older than that requirement.
Keep the three parts compatible and complete the update as a set.

## Update in four steps

1. **Read the release notes** and the [breaking
   changes](update-process.md#upgrading) for the release you are installing.
2. **Update the integration.** Install or update it in the Home Assistant
   **Marketplace**, then restart Home Assistant.
3. **Update the firmware.** Press **Install** on the panel's **HAUI Firmware**
   update (`update.<device>_haui_firmware`). The panel downloads, flashes and
   restarts.
4. **Let the display follow.** About a minute after the panel reconnects, the
   hub installs the TFT the firmware needs. The upload takes several minutes
   (about 13 on a portrait panel) and ends with one more restart.

The firmware can show up before you have updated the integration, because both
ship with the same release. Update the integration first anyway.

## Alternative update paths

The four steps above are the default: a panel on the **universal firmware**, the
prebuilt `nspanel_haui.bin` every release ships. Two cases differ:

- **Custom firmware** built from your own YAML (`esphome/install.yaml`): the hub
  never installs the release image on it, and **HAUI Firmware** shows
  *unknown*. Update it in the ESPHome dashboard (**Install → Wirelessly**); its
  display TFT still follows through the hub.
- **Firmware 0.4.3 or older**: flash the new firmware once by hand; after that
  the hub updates it. See [Older firmware](update-process.md#older-firmware).

## Update settings

Each panel has its own settings: in the editor open the Device Manager, choose
**Settings** in the panel's menu and expand **Updates**.

| Setting | Default | What it does |
|---------|---------|--------------|
| **Enable updates** | on | Master switch. Off: no checks, no automatic installs, update entities unavailable, manual installs refused. |
| **Auto-install firmware updates** | off | Installs a new firmware on its own as soon as a release is out, possibly before you have updated the integration or read the release notes. |
| **Auto-install TFT updates** | on | Installs the display file right after a firmware update. Off: the panel asks first. |

[Update Process](update-process.md#settings) covers the checks, channels and
remaining options. During an update the panel shows a **release notice** (once
per release), an **Update** message while a firmware installs, and the TFT
question when **Auto-install TFT updates** is off.

### Installing a local TFT or firmware image

**Device actions → Info → Install update → From local file** takes a compiled Nextion
`.tft` (up to 16 MiB) or an ESPHome OTA app `.bin` (not a factory image). The hub
validates the Nextion signature or the ESP image magic and the app-partition
size before installing. It stages the file in memory for up to one hour and
serves it through a random HTTP(S) URL, so the device must reach Home
Assistant's configured **Internal URL**. See
[Installing updates](update-process.md#editor-device-info).

## If something goes wrong

- Retry from **Device actions** (⋮) → **Info** → **Install update**. Choose
  **Firmware** or **Display (TFT)**, then an offered update or release, **From
  URL**, or **From local file**.
- [Troubleshooting](troubleshooting.md#tft-upload-failures) lists the common
  causes of failed display updates.
- The Marketplace does not downgrade. To go back, restore a backup, see
  [Rollback](update-process.md#7-rollback).

## Upgrading from older versions

The breaking changes of each release, the 0.3.x migration and the steps for
older firmware are collected at the end of
[Update Process](update-process.md#upgrading).

### Notification types replaced by icon colour and sound

The `type` (`info`/`warning`/`critical`) field is gone from
`nspanel_haui.send_notification`. Use the generic fields instead:

- `icon_color` — `#rrggbb`, an RGB565 number, `[r, g, b]` or an integer
  string; empty keeps the theme's text colour.
- `sound` — `startup`, `tone`, `tone_up`, `tone_down`, `seq_up`, `seq_down`,
  `notification`, `alert`, `alert_fast`, `elise`, or `none` for silence.

Persistent notifications now open immediately on every path (service, notify
entities, ESPHome action) and may re-open their popup over the idle page;
quiet hours still keep the display dark. The
[preset notification script](services.md#preset-notification-script) recreates
the old presets. The `nspanel_haui.notification` event replaces `notif_type`
with `icon_color` and `sound`.

The ESPHome `send_notification` action gained two required variables:
`icon_color` and `sound`. Custom YAML calling the action must pass them;
`icon_color: ""` and `sound: "notification"` keep the old `info` behaviour, and
`sound: "alert"` matches the old `critical` sound. Panels still running a
firmware build without the new variables keep sending the old payload, and the
hub accepts it for this release: a missing icon colour uses the theme's text
colour and a missing sound plays `notification`.

### Automatic page switching moved to the hub

NSPanel HAUI 0.4.5 removes the firmware's **Use Auto-Page** switch, **Timeout
Page** number, and `esphome.timeout` page-timeout event. Automatic page switching
now uses the device's `use_auto_page` and `timeout_page` settings in the hub;
the old `hub_idle_timeout` setting is gone, with no separate fallback timer. A
timeout that passes while a page holds automatic switching opens on the next
one-second check after the hold ends, unless an interaction has reset the
clock. An empty Night `night_idle_panel` disables that idle page; it does not
inherit Day's `idle_panel`. Delete the orphaned ESPHome entities and remove
automations that listened for the page-timeout event.

Update the integration first, then install the matching firmware with the
panel's **HAUI Firmware** entity. Let the matching TFT install after the
firmware reboots. Mixed hub and firmware versions are unsupported. The hub's
page timeout, profile behavior, and the display-off fix are detailed in
[Update Process, 0.4.5](update-process.md#19-automatic-page-switching-moved-to-the-hub).
