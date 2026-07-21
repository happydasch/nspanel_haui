---
title: Device Configuration
description: Device-level configuration keys for NSPanel HAUI
---

# Device Configuration

Device-level settings configure the NSPanel hardware behaviour — buttons, sounds, timeouts, and display states. All of this is configured through the frontend (Device Manager and Device Settings dialogs) — there is no YAML configuration.

## Device Manager

Opened from the panel toolbar. Lists all configured devices and lets you add, remove, reorder, enable/disable, and open settings for a device.

- `name` string

  The name of the panel device. Set when adding a device.

- `esphome_device_id` string

  The ESPHome device ID this config entry is linked to. Set automatically during discovery/add.

- `enabled` bool

  Whether the device is active at runtime. Disabled devices are skipped without deleting their config. Toggled from the device row menu or the footer switch in Device Settings. Default `True`.

- `panels` list

  Per-device panel list, managed on the panel editing screen for the selected device.

## Device Settings

Opened via the "Settings" action on a device in Device Manager. Fields are grouped into collapsible sections:

### General Settings

- `locale` string

  Display language — one of `en_US`, `de_DE`, `nl_NL`, `pl_PL`, `fr_FR`. Determines how dates, times, and numbers are formatted and which language is used for built-in text labels.

- `debug_level` int

  Diagnostic logging verbosity shown in the dropdown as Off (`0`), Basic (`1`), or Verbose (`2`). Default `0`.
- `log_items` bool

  Log display item updates and commands for debugging. Default `False`.


### Display Buttons

- `show_home_button` bool

  Show a home navigation button on panels. Default `False`.

- `show_sleep_button` bool

  Show a sleep button on the home panel. Default `False`.

- `show_notifications_button` bool

  Show the notifications button on supported panels. Default `True`.

### Notifications

- `sound_on_startup` bool

  Play a short tone when the display connects to Home Assistant after a restart or power cycle. Default `True`.

- `sound_on_notification` bool

  Play an alert tone whenever a new notification is received. Default `True`.

- `use_do_not_disturb` bool

  Enable quiet hours to suppress notification sounds during a specified time window. When enabled, sounds are only played within the quiet hours window set below. Default `False`.

- `quiet_hours_start` string

  Start of the quiet hours window in `HH:MM` 24-hour format. Only used when `use_do_not_disturb` is enabled. Supports overnight ranges (e.g. `22:00`–`07:00`). Leave empty to allow sounds at any time within the DND window. Default empty.

- `quiet_hours_end` string

  End of the quiet hours window in `HH:MM` 24-hour format. Only used when `use_do_not_disturb` is enabled. Supports overnight ranges. Leave empty to allow sounds at any time within the DND window. Default empty.

### Panel Assignments

- `home_panel` string

  Panel key shown when navigating home or returning from dim/sleep. Empty means no home panel set.

- `sleep_panel` string

  Panel key shown when the display enters sleep mode. Empty means no sleep panel set.

- `wakeup_panel` string

  Panel key shown briefly when the display wakes from sleep. Empty means no wakeup panel set.

### Hardware Buttons

- `use_relay_left` / `use_relay_right` bool

  Whether the left/right hardware button toggles its internal relay. Disable to assign a Home Assistant entity instead. Default `True` for both.

- `button_left_entity` / `button_right_entity` string

  Entity ID toggled by the left/right hardware button. Only shown (and used) when the corresponding relay is disabled. Default empty.

- `reset_interaction_on_button` bool

  Whether hardware button presses reset the idle/interaction timer (and wake the display). When `False`, button presses only toggle the relay/entity and don't count as user interaction. Default `True`.

### Sleep and Wakeup

- `snapshot_max_age_seconds` int

  Whether the last-viewed panel is restored when waking from sleep/dim, shown as a mode select:
  - **Always restore** (`-1`, default) — always restore the snapshot.
  - **Never restore** (`0`) — always go to the home panel.
  - **Custom time limit...** (`>0`) — only restore if the snapshot is newer than this many seconds.

- `hub_idle_timeout` int

  Hub-side idle timeout in seconds. A fallback sleep timer that triggers when the device doesn't publish `esphome.timeout` events (e.g. on panels that suppress idle). `0` disables this fallback. Default `0`.

- `auto_navigate_home_timeout` int

  After this many seconds of inactivity on a non-home panel, auto-navigate back to the home panel. `0` disables auto-navigate. Default `0`.

## Color Overrides

Opened from its own dialog (separate from Device Settings). Lets you override individual entries of the built-in `COLORS` palette per device.

- `color_overrides` dict

  RGB565 color values keyed by color name. Unknown keys are ignored (logged) and values are clamped to `0`-`65535`. Default `{}` (empty).

## Fields not yet exposed in the UI

These exist in the underlying config but have no frontend control yet, so they stay at their defaults:

- `page_settle_delay` float — delay in seconds before settling a new page after navigation (debounce for page events). Default `0.1`.

## Global Defaults (not per-device, fixed)

The following are hardcoded defaults, not exposed anywhere in the frontend:

- **Connection** — `heartbeat_interval` (`5.0`s), `overdue_factor` (`2.0`)
- **Update** — `auto_install` (`True`), `auto_update` (`False`), `tft_filename` (`nspanel_haui.tft`), `check_on_connect` (`False`), `on_connect_delay` (`60`s), `update_interval` (`0` = disabled)
- **Navigation** — `page_timeout` (`10.0`s)
