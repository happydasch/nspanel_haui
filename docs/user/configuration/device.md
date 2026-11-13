---
title: Device Configuration
description: Device-level configuration keys for NSPanel HAUI
---

# Device Configuration

Device settings control the panel itself: language, brightness and timeouts, buttons, sounds and colors. You change them in the editor; there is no YAML configuration.

This page first explains how to manage devices, then lists every setting. Each setting is shown with its key, which is the name used in logs and in other parts of this documentation.

## Managing devices

The dashboard is the editor's start screen. It shows every device as a card and as a row of the **Device inventory**.

**Adding a device.** When the editor opens, it looks for panels in Home Assistant's ESPHome integration and lists new ones under **Discovered Devices**. Select **Add**, or **Add All**. Reloading the editor searches again; while you have no device yet, the dashboard also offers **Scan for devices**. The search only looks at Home Assistant's ESPHome devices. It does not scan your network.

**What a row shows.** The firmware version, the display (TFT) version and the IP address, and an **Update** badge when an update is available. A display that needs a newer TFT is marked **update pending**. A value the panel has not reported yet is shown as **Unknown**; an unknown Wi-Fi signal does not mean the panel is offline.

**What you can do.**

- **Reorder** — drag a card or a row by its grip.
- **Settings** — at the end of each row.
- **More** menu — **Open device**, **Panels**, **Settings**, **Firmware and display updates**, **Logs**, **Enable** / **Disable** and **Remove**.
- **Disable** — a disabled device stays in the list with its settings but is not served by the hub. Enable it again from the **More** menu or with the **Device Enabled** switch in its settings. Updates are only available for enabled devices.
- **Remove** — asks for confirmation, then removes the device and deletes its settings and panels.

Every device has these basic fields:

| Key | Description |
|-----|-------------|
| `name` | The name of the panel. Set when the device is added. |
| `esphome_device_id` | The ESPHome device this panel belongs to. Set automatically. |
| `enabled` | Whether the hub serves the device. Default: on. |
| `panels` | The device's panels, managed in the **Panels** view. |

## How Settings Are Saved

All device settings and panels are kept in Home Assistant's storage.

- **Saving applies immediately.** No restart is needed. A setting you clear goes back to its default. Enabling or disabling a device reloads the hub.
- **New devices start enabled.** A device you disable stays disabled. A device you remove stays removed until you add it again.
- **Deleting in Home Assistant is the same as Remove.** **Delete** in the device's menu on *Settings → Devices & services → NSPanel HAUI* removes the device with its settings and panels.
- **Upgrading from 0.3.2 or earlier.** The settings of those versions are not carried over. After the update, check every device's settings in the editor.

## Device Settings

Open them with **Settings** in the device's **Connection & device** card, in the action card of its **Preview**, or in its row on the dashboard. The settings are grouped into sections.

### Language & region

| Key | Default | Description |
|-----|---------|-------------|
| `locale` | `en_US` | Display language: `en_US`, `de_DE`, `nl_NL`, `pl_PL`, `fr_FR` or `sk_SK` (Slovak). Sets the language of built-in texts and the format of dates, times and numbers. |
| `time_format` | `%H:%M` | Time format on the Clock, ClockTwo and Weather panels. `%I:%M %p` gives the 12-hour form (`2:30 PM`). Choose **Custom strftime…** to type any [strftime](https://strftime.org/) format. |
| `date_format` | `%A, %d. %B %Y` | Date format on the Clock and Weather panels. US examples: `%m/%d/%Y` (`03/14/2026`), `%B %d, %Y` (`March 14, 2026`). |

For Slovak, select **Slovenčina** (`sk_SK`) on the device. The editor and Home Assistant integration dialogs follow your Home Assistant profile language; select Slovak there as well. Slovak dates use localized weekdays and month names, for example `štvrtok 12. novembra 2026`. The ClockTwo word matrix has its own separate language setting and currently supports English, German and Polish.

### General Settings

| Key | Default | Description |
|-----|---------|-------------|
| `display_model` | `eu` | `eu` for every panel mounted in landscape, `us` for a US panel mounted in portrait. After you change it, the editor asks whether to install the matching display file. See [Display Models](display-models.md). |
| `log_level` | `INFO` | How much this device writes to the Home Assistant log: Critical, Error, Warning, Info or Debug. Debug adds state changes and the commands sent to the display. |
| `stale_data_seconds` | `0` (off) | Marks old values on the **Row** panel: a value whose entity has not updated for this many seconds is dimmed and ends in `…`. Set it a little above the update interval of your slowest sensor, for example `300` for a sensor that updates every 5 minutes. |

To see Debug messages in the Home Assistant log, Home Assistant must allow them too. Add this to your [logger configuration](https://www.home-assistant.io/integrations/logger/):

```yaml
logger:
  logs:
    custom_components.nspanel_haui: debug
```

### Display dimming & off

These settings only change the brightness. They never change the panel that is shown. See [Display states](../device.md#display-state-dimmed-off-and-on) for how they work together.

| Key | Default | Description |
|-----|---------|-------------|
| `brightness` | empty | Full display brightness, 0–100 %. Empty: the integration does not set it, and the brightness set on the panel stays. A [schedule](#schedule) needs a value here. |
| `brightness_dim` | empty | Brightness the display dims to, 0–100 %. Empty: the integration does not set it, and the value set on the panel stays. |
| `use_auto_dimming` | on | Dim the display after `timeout_dimming` seconds without interaction. |
| `timeout_dimming` | `10` | Seconds until the display dims. `0` turns it off, the maximum is `3600`. |
| `duration_dimming` | `2` | Seconds the fade between full and dimmed brightness takes, `0`–`5`. |
| `use_auto_display_off` | on | Turn the display off after `timeout_display_off` seconds without interaction. |
| `timeout_display_off` | `120` | Seconds until the display turns off. `0` turns it off, the maximum is `3600`. |

Good to know:

- The two switches also exist on the panel as **Use Auto-Dimming** and **Use Auto Display-Off**. The integration sets them only when you change the setting here. Otherwise it leaves them alone, so an automation can control them. The exception is **Use Auto Display-Off** while a [schedule](#schedule) has entries: the integration then sets it itself.
- With a `brightness` or `brightness_dim` value, the integration sets the panel's **Brightness Full** resp. **Brightness Dimmed** number on every connect and at every schedule boundary. A brightness changed on the panel's Settings page lasts only until then.
- Without a connection to Home Assistant the display dims after the dimming timeout, even when auto-dimming is off, and it never turns off.

### Schedule

The schedule changes sound, brightness, dimming and display-off at set times, for example a dark and silent panel at night. It is a list of entries; you can add as many as you like. In the device's **Preview** view, open **Manage this device** and choose **Schedule**: its sidebar holds the whole schedule. Set the default brightness, dimming and display-off values there too: they apply outside every entry and are the fallback for entry fields left empty. The Schedule button's tooltip says how many entries there are, and each entry folds to its own summary row.

Each entry has a time window and these settings:

| Key | Description |
|-----|-------------|
| `start` / `end` | **From** and **To**: a time as `HH:MM`, `sunrise` or `sunset`. The window can cross midnight. The entry ends just before the end time. |
| `start_offset` / `end_offset` | Minutes to shift a `sunrise` or `sunset` boundary, from `-720` to `720` (default `0`). Negative is earlier, positive is later. Not used for a time. |
| `sound` | Off: no sounds are played, and a notification does not wake the display. |
| `brightness` | **Brightness full**: full display brightness during the entry, 0–100 %. |
| `brightness_dim` | **Brightness dimmed**: brightness the display dims to during the entry, 0–100 %. |
| `timeout_dimming` | **Dimming timeout**: seconds without interaction until the display dims, `0`–`3600`. |
| `duration_dimming` | **Dimming duration**: seconds the fade between full and dimmed brightness takes, `0`–`5`. |
| `display_off` | **Screen off**: whether the display turns off during the entry. |
| `timeout_display_off` | **Display-off timeout**: seconds without interaction until the display turns off, `0`–`3600`. |

The entry's `sound` and `display_off` settings are always explicit. Its brightness, dimming timeout/duration and display-off timeout are optional: leave one empty and the matching default in the Schedule settings applies. The editor shows those fallback values; for brightness fields, when no hub value is set it also shows the panel's own **Brightness Full** or **Brightness Dimmed** reading, so the schedule never invents a brightness the panel does not use.

```yaml
brightness: 80
brightness_dim: 20
schedule:
  - start: "sunset"
    start_offset: -30
    end: "22:00"
    sound: true
    brightness: 40
    display_off: false
  - start: "22:00"
    end: "sunrise"
    sound: false
    brightness: 5
    brightness_dim: 2
    timeout_dimming: 5
    display_off: true
    timeout_display_off: 30
```

Good to know:

- Outside every entry, the Schedule settings' **Notification sound** toggle controls whether notification sounds play; its brightness, dimming and display-off settings also apply. These are the same device settings available in [Display dimming & off](#display-dimming-off) and [Notifications](#notifications).
- A schedule needs a full-brightness value, because the integration must know what to restore when an entry ends. When you add the first entry, the Schedule settings take the panel's **Brightness Full** number as their default if no hub value is set; while either brightness default is empty, the settings show the panel's current reading.
- When entries overlap, the first one in the list wins.
- Automatic page switching is not part of an entry. It always follows the normal settings.
- `sunrise` and `sunset` are the times at Home Assistant's location. Where the sun does not rise or set on a day (polar day or night), an entry that uses it is not active that day and the log has a warning.
- While the schedule has entries, the integration sets the panel's **Use Auto Display-Off** switch itself, from the active entry or from `use_auto_display_off`. An automation cannot control that switch then.
- An entry that starts or ends does not count as a touch.

### Automatic page switching

| Key | Default | Description |
|-----|---------|-------------|
| `use_auto_page` | on | Open the next idle panel after `timeout_page` seconds without interaction. This only changes the panel; it does not dim the display or turn it off. A touch leaves the idle panel again. |
| `timeout_page` | `30` | Seconds until the next idle panel opens. `0` turns it off, the maximum is `3600`. |

The idle panels themselves are set in **Device Settings → Special pages**. The panel's firmware no longer has the **Use Auto-Page** switch and the **Timeout Page** number.

### Display Buttons

| Key | Default | Description |
|-----|---------|-------------|
| `show_home_button` | off | Show a home button in the header of panels. |
| `show_idle_button` | off | Show a button that opens the idle panel. |
| `show_notifications_button` | on | Show the notifications button on panels that support it. |

On a panel without a free place on the right of the header, the notifications button takes the place of the idle button. See [Notifications](../device.md#notifications).

### Gestures

`gestures` sets what swipes from a screen edge do. It is a list: each gesture is one or more swipes in order and the action they run. In the device's **Preview** view, open **Manage this device** and choose **Gestures**. The editor works like the [Schedule](#schedule) editor: **Add gesture** adds an entry, each gesture folds to one row (its swipes and its action), and **Save** writes your changes to the device.

| Field | Description |
|-------|-------------|
| `swipes` | One or more of `swipe_left`, `swipe_right`, `swipe_up`, `swipe_down`, in order. In the editor, add swipes in order and drag them to reorder. |
| `action` | `next_panel` opens the next panel in the navigation, `prev_panel` the previous one. A panel key opens that panel, for example `sys_about` or the key of one of your panels. Empty (**- None -** in the editor) does nothing. |
| `timeframe` | Seconds from the first swipe to the last, 1–60. Only a gesture of several swipes uses it. |

The default gestures are the navigation:

| Swipes | Action |
|--------|--------|
| `swipe_left` (from the right edge to the left) | `next_panel` |
| `swipe_right` (from the left edge to the right) | `prev_panel` |
| `swipe_up` (from the bottom edge up) | `sys_about` |
| `swipe_down` (from the top edge down) | `sys_settings` |

How a swipe picks its gesture:

- A swipe runs one action at most. Of the gestures it completes, the one with the most swipes wins, then the first in the list. With a gesture `swipe_left`, `swipe_right` that opens your lights panel, the first swipe still steps to the next panel, and the second opens the lights panel instead of stepping back.
- The swipes of a gesture that ran are used up: they do not also start or complete another gesture.
- A wrong swipe, or a last swipe after the time limit, breaks a gesture of several swipes. It starts again with the next swipe that matches its first.
- A swipe that no gesture uses does nothing, so remove a gesture to turn its swipe off.
- A gesture without swipes or without an action does nothing, so an entry you just added is harmless while you fill it in.

Before 0.5.0 the single swipes were fixed and `gesture_sequences` held the sequences (`sequence`, `timeframe` and the panel to `open`). The integration converts saved sequences into gestures after the default ones when it loads the device settings, and when it imports a YAML file.


### Notifications

| Key | Default | Description |
|-----|---------|-------------|
| `sound_on_startup` | off | Play a short tone when the panel connects to Home Assistant after it started. A Wi-Fi reconnect stays silent. |
| `sound_on_notification` | off | Play the sound of each notification. Also used for the Timer panel's alert; set the default in **Notifications** or in **Manage this device → Schedule**. |
| `persistent_sound_interval` | `5` | Seconds between repeats of the sound while a persistent notification waits. The popup itself opens again about every 60 seconds. |

To silence the panel at certain times, add a [schedule](#schedule) entry with sound off.

### Panel Assignments

| Key | Description |
|-----|-------------|
| `home_panel` | The panel shown when you navigate home. Empty: the first navigation panel. |
| `idle_panel` | The first panel in the idle sequence. Empty with no `idle_panel_extra`: no panel is opened automatically. |
| `idle_panel_extra` | The remaining panels in the idle sequence. Each automatic page switch opens the next panel, cycling through the sequence. The editor shows both fields as one ordered **Idle panels** list. |

You can set these in **Device Settings → Special pages**.

### Hardware Buttons

| Key | Default | Description |
|-----|---------|-------------|
| `use_relay_left` / `use_relay_right` | on | The button switches its built-in relay. Turn it off to toggle an entity instead. The relays keep their state across restarts, updates and power losses. |
| `button_left_entity` / `button_right_entity` | empty | The entity the button toggles. Only shown when the relay is turned off for that button. |
| `reset_interaction_on_button` | on | A button press also wakes the display and leaves the idle panel. When off, the button only switches its relay or entity. |

### Idle & Wake Behavior

| Key | Default | Description |
|-----|---------|-------------|
| `snapshot_max_age_seconds` | `-1` | Which panel is shown after you leave the idle panel. **Always restore** (`-1`): the panel you were on. **Never restore** (`0`): the home panel. **Custom time limit…** (a number of seconds): the panel you were on if you left it less than that long ago, otherwise the home panel. |
| `auto_navigate_home_timeout` | `0` (off) | Go back to the home panel after this many seconds without interaction. Set it shorter than the dimming and display-off timeouts. If the idle panel opens first, it stays, and leaving it goes to the home panel. |

## Themes

In the device's **Preview** view, open **Manage this device** and choose **Theme**: its sidebar selects the device's theme and edits semantic page colors and weather, alarm and climate state-icon palettes. The selection is saved immediately; press **Apply** to save color changes or **Cancel** to discard them. The custom theme library is shared by the hub's devices; each device selects its own theme. Editing colors changes the selected shared theme, creating a custom copy when needed.

See [Themes](themes.md) for predefined and custom themes, the icon variant, shared color editing and import/export.

### Background pages

The Clock, Weather and ClockTwo panels have a **Background** setting:

- **A picture.** Every picture belongs to either the dark or the light colors, so text and icons stay readable on it.
- **Use color scheme.** A plain dark or light background instead of a picture, chosen to match the selected theme's background color. Text and icons use the theme's colors. The display only has these two plain backgrounds; a custom background color selects the closer one.

The backgrounds and their names:

| Background | Name | Text and icon colors |
|------------|------|----------------------|
| Use color scheme | `scheme` | From the selected theme |
| Dark Color | `dark` | For a dark background |
| Light Color | `light` | For a light background |
| Modern, Spring, Summer, Autumn, Winter | `modern`, `spring`, `summer`, `autumn`, `winter` | For a dark background |
| Dog 1, Dog 2, Cat | `dog_1`, `dog_2`, `cat` | For a dark background |

**A background that changes.** Choose **Template…** in the Background field and enter a Home Assistant template that results in one of the names above. The template is evaluated when the panel opens. This example shows the dark background at night:

```jinja
{{ 'dark' if is_state('sun.sun', 'below_horizon') else 'modern' }}
```

See [Display color behavior](../../develop/design.md#themes-and-colors) for how colors are applied on the display.

## Updates

The **Update settings** card in a device's **Updates** sidebar controls update checks and installs for that device. Changes save automatically; text fields save after you pause typing. The **Enable updates** switch, **Update channel** (stable or development releases for firmware and display) and optional custom firmware manifest URL are grouped together. **Release checks**, **Firmware** (auto-install) and **Display** (auto-install TFT) are separate groups. [Updating](../update.md) explains how to update; [Update Process](../../develop/update-process.md) explains every step in detail.

| Key | Default | Description |
|-----|---------|-------------|
| `enabled` | on | Master switch. When off, the hub does not check for updates and installs nothing, the update entities are unavailable and manual installs are refused. An install that is already running finishes. |
| `check_on_connect` | on | Check for a new release after the panel connects. |
| `update_interval` | `3600` | Seconds between regular checks. The editor offers common intervals from 15 minutes to one week, plus a custom seconds value. `0`, or turning off **Enable periodic update checks**, turns them off. |
| `firmware_update_channel` | `stable` | Selects the stable or development release channel for both firmware and display updates. |
| `firmware_manifest_url` | empty | Optional firmware manifest URL that overrides the channel's firmware release, e.g. a [local test release](../../develop/release.md#test-firmware-updates-with-a-local-release); the display continues to follow the matching TFT. |
| `firmware_auto_update` | off | Install new firmware without asking. The display file follows after the restart. |
| `auto_install` | on | Install the display file (TFT) without asking. When off, the panel asks first. |

Good to know:

- Each **Firmware** and **Display** row in the **Updates** sidebar has an **Install** button while updates are enabled. Choose a release, **From URL** or **From local file**. **Check for updates** looks for a new release right away.
- **After a manual install the hub waits.** If you install another release or a file from a URL, automatic firmware updates pause until Home Assistant restarts or you install the offered update. A TFT installed from a URL is kept until the firmware version changes or Home Assistant restarts. See [`nspanel_haui.update_firmware`](../services.md#nspanel_hauiupdate_firmware) and [`nspanel_haui.update_tft`](../services.md#nspanel_hauiupdate_tft).
- **Custom firmware is never replaced by the release firmware.** A panel with firmware built from your own YAML (see [Installation](../install.md)) is not offered the universal release firmware, so its credentials stay yours. Install your own builds with **Install** beside **Firmware**, then **From URL**. Firmware older than 0.4.4 is treated the same way: install a newer firmware once by hand.
- **A failed display install is not repeated automatically.** If the display never reports its new version, the editor shows an error. Start it again with **Install** beside **Display (TFT)**.
- **In Home Assistant** the firmware is the **HAUI Firmware** update entity and the display is the **HAUI Display** update entity on the device page. See [Services](../services.md#haui-firmware-update-entity).

## Settings without an editor field

These settings exist but cannot be changed in the editor. They keep their defaults.

| Key | Default | Description |
|-----|---------|-------------|
| `page_settle_delay` | `0.1` | Seconds the hub waits after opening a page before it draws it. |
| `date_format_locale` | `full` | A named date format (`full`, `long`, `medium`, `short`, `E`, `EEEE`) with translated day and month names. |
| `on_connect_delay` | `60` | Seconds between a connect and the display file check. |
| `heartbeat_interval` / `overdue_factor` | `5.0` / `2.0` | How often the hub and the panel check their connection, and after how many missed checks the connection counts as lost. |
| `page_timeout` | `10.0` | Seconds the hub waits for the display to confirm a page change. |
