---
title: Updating
description: How to update NSPanel HAUI and where the breaking changes are documented
---

# Updating

The three parts update together, in this order:

| Part | What it is | How it is updated |
|------|------------|-------------------|
| Integration | The hub in Home Assistant, including the editor | Marketplace, then a Home Assistant restart |
| Firmware | The software on the panel's ESP32 | By the hub: the panel's **HAUI Firmware** update |
| Display | The TFT file on the panel's screen | By the hub, automatically after the firmware |

Integration and firmware should match; otherwise **Diagnostics** shows **Firmware version does not match the integration**. The display's `tft_version` can differ: the hub updates it when the firmware needs a newer one.

## Update in four steps

1. **Read the release notes** and the [breaking changes](../develop/upgrading.md#upgrading) of the release you are installing.
2. **Update the integration** in the Home Assistant **Marketplace**, then restart Home Assistant.
3. **Update the firmware.** Press **Install** on the panel's **HAUI Firmware** update (`update.<device>_haui_firmware`). The panel downloads it and restarts.
4. **Wait for the display.** About a minute after the panel reconnects, the hub installs the required TFT, and the panel restarts once more when it is done. The write is paced by the display acknowledging each 4 KB chunk rather than by the link, so there is no fixed duration to quote: the **Updates** sidebar shows the time the install has run, and past 15 minutes it says the install is taking longer than usual.

The firmware update can appear before you have updated the integration, because both ship with the same release. Update the integration first anyway.

### The first boot after 0.5.7

Both shipped TFTs now talk to the panel at 921600 bps. A panel that still runs the previous 0.4.5 TFT answers at 115200, so its first boot after the firmware update scans the display rates: 8 s for the handshake, 4 s to power-cycle the display, and 1.6 s per rate probed, so about 15 s when the scan finds the display and about 35 s when it finds nothing. The TFT update then switches the display to 921600, and the first boot after that can take as long again while the firmware finds the new rate. Leave the panel powered; both boots end on their own, and later boots are immediate.

## Other ways to update

The four steps use the **universal firmware**, the `nspanel_haui.bin` every release includes. Two cases differ:

- **Custom firmware** from your own YAML: the hub never installs release firmware on it, and **HAUI Firmware** shows *unknown*. Update it in the ESPHome dashboard (**Install → Wirelessly**); the hub still updates the display.
- **Firmware 0.4.3 or older**: install the new firmware once by hand. The hub updates later releases. See [Older firmware](../develop/upgrading.md#older-firmware).

## Update settings

Settings belong to each device. In the editor, open the device's **Updates** sidebar and change the **Update settings** card. Changes save automatically; text fields save after you pause typing. **Enable updates** sits beside the title.

| Setting | Default | What it does |
|---------|---------|--------------|
| **Enable updates** | on | Master switch. When off, no checks, installs or manual installs. |
| **Update channel** | **Stable** | Stable releases, or published **Development** builds, for firmware and display. |
| **Check for a new version** | **Every hour** | How often the hub checks; **Never** turns regular checks off. |
| **Install firmware updates automatically** | off | Installs new firmware at release, possibly before you update the integration or read the notes. |

Under **Advanced**:

| Setting | Default | What it does |
|---------|---------|--------------|
| **Custom manifest URL** | empty | A firmware manifest to follow instead of the channel. |
| **Check for updates on connect** | on | Also checks after the panel connects. |
| **Wait before an automatic firmware install** | 10 minutes | With automatic installs on. Until it starts, the sidebar offers **Install now**, **In 1 hour**, **In 1 day** and **Skip this version**. |
| **Install display updates automatically** | on | Installs the TFT right after a firmware update. When off, the panel asks first. |
| **Failed attempts before it stops** | 3 | After this many failed automatic attempts at one version, the device waits for you or a newer version. |
| **Wait between attempts** | 1 hour | Delay before retrying a failed automatic install. |

**Install updates** on the dashboard installs what every device is offered, one device after another: a panel cannot be used while it updates. The first failure stops the devices after it, and you can cancel devices that have not started. The sidebar and dashboard show the current step and remaining time; the panel shows a release notice (once per release) and an **Update** notification during a firmware install, both waiting while you read another notification. With automatic display updates off, it asks before installing the TFT.

[Update Process](../develop/update-process.md#settings) explains checks and channels.

### Installing a local TFT or firmware image

Open the **Updates** sidebar, press **Install** beside **Firmware** or **Display**, then choose **From local file**:

- a compiled Nextion `.tft` file (up to 16 MiB)
- an ESPHome OTA `.bin` file (not a factory image)

The hub validates the file before installing it. The panel downloads it from Home Assistant, so it must reach Home Assistant's **Internal URL**. See [Installing updates](../develop/update-process.md#editor-the-updates-sidebar).

## If something goes wrong

- **Try again.** Open the **Updates** sidebar, press **Install** beside **Firmware** or **Display (TFT)**, and choose an offered update, a release, **From URL** or **From local file**.
- **Display update fails.** The sidebar, the **HAUI Display** entity and `nspanel_haui.update_tft` say why: the panel's own reason (no network, the server's answer, a refused display) or the reason the hub would not start the install. See [TFT Upload Failures](troubleshooting.md#tft-upload-failures).
- **An install that will not start.** A second install while one is running is refused with its start time instead of being reported as started; wait for it, or power-cycle the panel if the transfer never finishes.
- **Go back to an older version.** The Marketplace does not downgrade. Restore a backup; see [Rollback](../develop/upgrading.md#rollback).

## Upgrading from older versions

Breaking changes since 0.4.5, newest first. The full history, the 0.3.x migration and old-firmware steps are in [Upgrading](../develop/upgrading.md#upgrading).

### Display Model is a dropdown

The firmware's **Display Model** config entity is now a `select` with **Landscape** and **Portrait**, so the panel's device page in Home Assistant offers a dropdown instead of the number `0` (landscape) or `1` (portrait). `number.<device>_display_model` becomes `select.<device>_display_model`.

Nothing to re-enter: the hub writes the option on every connect, and the editor's **Display Model** setting under **Device Settings → General** is unchanged. Flash the firmware that ships with this version together with the integration, and point automations that referenced the old number entity at the select.

### The theme picks its own icon colors

**Theme variant** and the Theme sidebar palette question are gone. A theme decides its icon palette from its background: dark themes use dark-background icons, light themes such as **Light**, **White** or **Sky** the light-background ones. A theme cannot pair its page with the opposite contrast.

The hub drops `theme_variant` on load. Devices that ran a light theme with dark-background icons switch automatically; remove `theme_variant` from hand-written YAML and choose the theme with the page colors you want.

### A schedule entry that dims needs a dimmed brightness

A schedule entry with its own **Brightness dimmed** could leave that brightness behind after the entry ended when the device's **Brightness dimmed** was empty. The device setting is now required for such an entry and is the brightness outside the entry.

On load, the hub sets it to 20 % (the panel default) on affected devices and logs a warning. Check it under **Screen**.

### Automatic installs wait and retry

- An automatic firmware install waits 10 minutes (**Wait before an automatic firmware install**); choose **Start right away** for the old behavior.
- A display update the panel does not confirm is retried up to 3 times, an hour apart, instead of once.

### Background pages draw a picture

Clock, ClockTwo and Weather no longer offer **Use color scheme**. They can only paint pictures compiled into the display, so the old option just picked dark or light regardless of theme. **Background** now offers **Dark Color** (the default), **Light Color** and the decorative pictures; text and icons use the matching palette.

A panel saved with `scheme` or another unknown value falls back to the theme fill. Pick a background to be explicit.

### Themes replace color schemes

**Device Colors** is now the **Theme** editor, opened from the **Theme** field in **Device Settings → General** or the **Themes** button beside the side cards. The Appearance section is gone from device settings; **Home & idle** assignments are in device settings.

Color schemes and old per-device theme settings are not migrated. Set `theme_id`, add custom palettes to the shared library, and use `theme_definition` for an included custom theme. Panel and item colors are unchanged.

### Schedule replaces Day/Night profiles and quiet hours

**Day/Night Profiles** and **quiet hours** are replaced by one **Schedule**: entries with a time window (a time, or sunrise or sunset with an offset) and the settings they apply (sound, full and dimmed brightness, dimming timeout and duration, screen off and its timeout). See [Schedule](editor/device.md#schedule).

Saved settings are **not converted**. Set **Brightness full** under **Screen** for outside the schedule, then add an entry for each former time window, such as a low-brightness night entry and a sound-off quiet-hours entry.

- The Night profile's own dimming timeout, ramp, dimmed brightness, page timeout and idle panel are gone. Normal settings apply; an entry can override dimming for its window.
- While a schedule has entries, the integration controls **Use Auto Display-Off**. Automations that control it no longer work with a schedule.
- Install the matching firmware too: the display no longer brightens while dimming when an entry's brightness is below the dimmed brightness.

### Notification types replaced by icon colour and sound

The `type` field (`info`, `warning`, `critical`) of `nspanel_haui.send_notification` is gone. Use `icon_color` (`#rrggbb`, an RGB565 number, `[r, g, b]` or an integer string; empty uses the theme text colour) and `sound` (a `play_sound` name, or `none` for silence).

- The [preset notification script](actions.md#preset-notification-script) restores the old types.
- Persistent notifications open immediately and may open over the idle page. A schedule entry with sound off still keeps the display dark.
- The `nspanel_haui.notification` event has `icon_color` and `sound` instead of `notif_type`.
- The ESPHome `send_notification` action requires `icon_color` and `sound`. Custom YAML must pass them: `icon_color: ""` with `sound: "notification"` is the old `info`; `sound: "alert"` is the old `critical` sound. Older firmware still works: a missing colour uses the theme text colour, and a missing sound plays `notification`.

### Automatic page switching moved to the hub

Since 0.4.5 the hub switches to the idle page, not the firmware. Update the integration, then the firmware, then let the TFT install; mixed versions are unsupported. Delete the leftover ESPHome entities **Use Auto-Page** and **Timeout Page**, and remove automations listening for `esphome.timeout`; it no longer exists.

Page switching uses `use_auto_page` and `timeout_page`; `hub_idle_timeout` is gone. Details: [Upgrading, 0.4.5](../develop/upgrading.md#045).
