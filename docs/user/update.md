---
title: Updating
description: How to update NSPanel HAUI and where the breaking changes are documented
---

# Updating

NSPanel HAUI has three parts. Update them together, in this order:

| Part | What it is | How it is updated |
|------|------------|-------------------|
| Integration | The hub in Home Assistant, including the editor | Home Assistant's Marketplace, then a Home Assistant restart |
| Firmware | The software on the panel's ESP32 | By the hub: the panel's **HAUI Firmware** update |
| Display | The TFT file on the panel's screen | By the hub, automatically after the firmware |

The integration and firmware release versions are expected to match, but they are separate values: the integration version comes from the integration's `manifest.json`, while the firmware version is reported by ESPHome as `yaml_version`.
If they differ, the device's **Diagnostics** card shows **Firmware version does not match the integration**. The display has its own `tft_version`, which may differ: the hub updates the display only when the firmware needs a newer one.

## Update in four steps

1. **Read the release notes** and the [breaking changes](../develop/update-process.md#upgrading) of the release you are installing.
2. **Update the integration.** Update it in the Home Assistant **Marketplace**, then restart Home Assistant.
3. **Update the firmware.** Press **Install** on the panel's **HAUI Firmware** update (`update.<device>_haui_firmware`). The panel downloads the firmware, installs it and restarts.
4. **Wait for the display.** About a minute after the panel reconnects, the hub installs the TFT the firmware needs. This takes several minutes (about 13 on a portrait panel) and ends with one more restart.

The firmware update can show up before you have updated the integration, because both come with the same release. Update the integration first anyway.

## Other ways to update

The four steps are for the **universal firmware**, the `nspanel_haui.bin` that every release includes. Two cases are different:

- **Custom firmware** that you built from your own YAML: the hub never installs the release firmware on it, and **HAUI Firmware** shows *unknown*. Update it in the ESPHome dashboard (**Install → Wirelessly**). The display is still updated by the hub.
- **Firmware 0.4.3 or older**: install the new firmware once by hand. After that the hub updates it. See [Older firmware](../develop/update-process.md#older-firmware).

## Update settings

Update settings belong to each device. In the editor, open the device's **Updates** sidebar and change the **Update settings** card; each change is saved automatically, and text fields save after you pause typing. Three choices are always shown:

| Setting | Default | What it does |
|---------|---------|--------------|
| **Enable updates** (the switch beside the card's title) | on | Master switch. When off, the hub does not check for updates, installs nothing and refuses manual installs. |
| **Update channel** | **Stable** | Stable releases, or published **Development** builds, for both firmware and display. |
| **When a new version is found** | **Manual** | **Auto** installs new firmware as soon as a release is out. This can happen before you have updated the integration or read the release notes. |
| **Check for a new version** | **Every hour** | How often the hub looks for a newer release; **Never** turns the regular checks off. |

The rest is folded under **Advanced**:

| Setting | Default | What it does |
|---------|---------|--------------|
| **Custom manifest URL** | empty | A firmware manifest to follow instead of the channel. |
| **Check for updates on connect** | on | Also checks for a new release after the panel connects. |
| **Wait before an automatic firmware install** | 10 minutes | Shown with **Auto**. The firmware install waits this long first. Until then the **Updates** sidebar offers **Install now**, **In 1 hour**, **In 1 day** and **Skip this version**. |
| **Install display updates automatically** | on | Installs the display file right after a firmware update. When off, the panel asks first. |
| **Failed attempts before it stops** | 3 | After this many failed automatic attempts at one version, the device stops trying until you install it by hand or a newer version comes out. |
| **Wait between attempts** | 1 hour | How long a failed automatic install waits before it tries again. |

**Install updates** on the dashboard installs what every device is offered, one device after the other: a panel cannot be used while it updates, so they never all go at once. The first failure stops the devices after it, and you can cancel a device that has not started yet. While an update runs, the **Updates** sidebar and the dashboard show its step (starting, transferring, restarting and checking) and about how long is left.

During an update the panel shows a release notice (once per release) and an **Update** message while firmware is installed, both as notifications (they wait while you read another notification), and a question before the TFT install when **Install display updates automatically** is off.

All update settings are listed in [Device Configuration](configuration/device.md#updates). [Update Process](../develop/update-process.md#settings) explains when the hub checks for updates and which channels exist.

### Installing a local TFT or firmware image

To install your own file, open the **Updates** sidebar, press **Install** beside **Firmware** or **Display**, then choose **From local file** and one of:

- a compiled Nextion `.tft` file (up to 16 MiB)
- an ESPHome OTA `.bin` file (not a factory image)

The hub checks that the file is valid before it installs it. The panel downloads the file from Home Assistant, so it must be able to reach Home Assistant's **Internal URL**. See [Installing updates](../develop/update-process.md#editor-the-updates-sidebar) for the details.

## If something goes wrong

- **Try again.** Open the device's **Updates** sidebar and press **Install** beside **Firmware** or **Display (TFT)**. Choose an offered update, a release, **From URL** or **From local file**.
- **Display update fails.** [Troubleshooting](troubleshooting.md#tft-upload-failures) lists the common causes.
- **Go back to an older version.** The Marketplace does not downgrade. Restore a backup instead, see [Rollback](../develop/update-process.md#7-rollback).

## Upgrading from older versions

Some releases change behaviour or need extra steps. All breaking changes, the migration from 0.3.x and the steps for old firmware are listed in [Update Process → Upgrading](../develop/update-process.md#upgrading). The most recent ones:

### Automatic installs wait and retry

Two things behave differently:

- An automatic firmware install waits 10 minutes before it starts (**Wait before an automatic firmware install**). Set it to **Start right away** for the old behaviour.
- A display update the panel does not confirm is now tried again, up to 3 times an hour apart, instead of only once.

### Themes replace color schemes

The **Device Colors** sidebar is now the **Theme** editor, opened with the **Theme** button of **Manage this device** on the device's **Preview**. Choose the device's theme there; the Appearance section has been removed from device settings. Home and idle page assignments are in **Device Settings → Home & idle**.

When the integration loads the panel store, it does not migrate color schemes or per-device theme settings. Configure the device with `theme_id` and `theme_variant`, and add custom palettes to the shared theme library. Panel and item color settings are separate and unchanged. Use `theme_definition` for an included custom theme.

### Schedule replaces Day/Night profiles and quiet hours

The **Day/Night Profiles** and the **quiet hours** (do not disturb) are gone. One **Schedule** replaces both: a list of entries, each with a time window (from and to: a time, or sunrise or sunset with an offset in minutes) and the settings it applies: sound, full and dimmed brightness, dimming timeout and duration, screen off and its display-off timeout. See [Schedule](configuration/device.md#schedule).

Saved Day/Night and quiet-hours settings are **not converted**. After the update:

1. Open the device settings and set **Brightness** under **Screen**. It is the brightness outside the schedule.
2. Add a **Schedule** entry for each time window you had, for example one for the night with a low brightness, and one with **Sound** off for your former quiet hours.

What changed:

- The Night profile's own dimming timeout, dim ramp, dimmed brightness, page timeout and idle panel no longer exist. Dimming and the idle page follow the normal device settings, and a schedule entry may override the dimming values for its window.
- While a schedule has entries, the integration sets the **Use Auto Display-Off** switch itself. An automation that controls this switch no longer works together with a schedule.
- Install the firmware of this release as well: with it, the display does not get brighter when it dims while an entry's brightness is below the dimmed brightness.

### Notification types replaced by icon colour and sound

The `type` field (`info`, `warning`, `critical`) of `nspanel_haui.send_notification` is gone. Use these two fields instead:

- `icon_color` — the colour of the icon: `#rrggbb`, an RGB565 number, `[r, g, b]` or an integer string. Empty uses the theme's text colour.
- `sound` — `startup`, `tone`, `tone_up`, `tone_down`, `seq_up`, `seq_down`, `notification`, `alert`, `alert_fast`, `elise`, or `none` for silence.

What else changed:

- The [preset notification script](services.md#preset-notification-script) gives you the old types back.
- Persistent notifications now always open immediately, and they may open again over the idle page. A [schedule](configuration/device.md#schedule) entry with sound off still keeps the display dark.
- The `nspanel_haui.notification` event has `icon_color` and `sound` instead of `notif_type`.
- The ESPHome `send_notification` action has two new required variables, `icon_color` and `sound`. Custom YAML that calls the action must pass them: `icon_color: ""` with `sound: "notification"` behaves like the old `info`, and `sound: "alert"` is the old `critical` sound. Panels with older firmware keep working in this release: a missing colour uses the theme's text colour, a missing sound plays `notification`.

### Automatic page switching moved to the hub

Since 0.4.5 the hub switches to the idle page, not the firmware. What to do:

1. Update the integration first, then the firmware with the **HAUI Firmware** entity, then let the TFT install. Mixed hub and firmware versions are not supported.
2. Delete the leftover ESPHome entities **Use Auto-Page** and **Timeout Page**.
3. Remove automations that listen for the `esphome.timeout` page-timeout event. It no longer exists.

What changed:

- Automatic page switching uses the device settings `use_auto_page` and `timeout_page`. The `hub_idle_timeout` setting is gone.

The details are in [Update Process, 0.4.5](../develop/update-process.md#19-automatic-page-switching-moved-to-the-hub).
