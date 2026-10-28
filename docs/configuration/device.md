---
title: Device Configuration
description: Device-level configuration keys for NSPanel HAUI
---

# Device Configuration

Device-level settings configure the NSPanel hardware behaviour — buttons, sounds, timeouts, and display states. Most of this is configured through the frontend (Device Manager and Device Settings dialogs) — there is no YAML configuration.

## Device Manager

Opened from the panel toolbar. Lists all configured devices and lets you add, remove, reorder, enable/disable, and open settings for a device.

- **Scan for devices** — Discovers ESPHome devices on the network that run
  HAUI firmware and offers them for batch-add. Discovered devices are added
  enabled and linked to their ESPHome entry.
- **Install TFT** — Open the device's **More** menu and choose **Install TFT**
  to trigger an install immediately (installs stay automatic on connect; this
  forces one now), even when the current display TFT version is unknown. The row
  shows **Display Unknown** / **Firmware Unknown** when those versions are not
  reported. An install refetches GitHub release metadata when the cached list
  lacks the firmware-matched TFT, so a list cached before a firmware update
  cannot hide the matching TFT release. When the install cannot start (device offline,
  no `yaml_version`, or the GitHub release is unreachable), the editor shows a
  toast with the reason instead of a success message. A request that never gets
  an answer (e.g. the device worker is blocked) times out after 20 seconds and
  shows a timeout toast instead of doing nothing.
- **Download firmware** — Opens the prebuilt `nspanel_haui.bin` of the latest
  release when one is attached, and explains the build-from-YAML path otherwise.
  This is the manual fallback. Once a device runs firmware that exposes the
  `HAUI Firmware` update entity and `firmware_auto_update` is on (the default),
  the hub asks Home Assistant to install the device's firmware update first and
  the matching TFT follows after the reboot. The first flash onto older firmware
  still has to be done manually through ESPHome, because that firmware has no
  update entity.
- **Install TFT retry** — After an install that the display never confirms
  (the device does not report the new TFT version within its timeout), the
  automatic path stops and reports an error. Press **Install TFT** again to
  start a fresh attempt; a manually requested install is not blocked by the
  previous unconfirmed one. Automatic installs stay disabled while an install
  remains unconfirmed, so a display that cannot report its version is not
  uploaded to forever.
- **Refresh display** — Re-renders the display.
- Each row shows the device's online/offline state, firmware and TFT versions,
  IP address and signal strength; a display whose TFT is older than the
  firmware version is flagged **update pending**.

The per-device fields:

- `name` string

  The name of the panel device. Set when adding a device.

- `esphome_device_id` string

  The ESPHome device ID this config entry is linked to. Set automatically during discovery/add.

- `enabled` bool

  Whether the device is active at runtime. Disabled devices are skipped without deleting their config. Toggled from the device row menu or the footer switch in Device Settings. Default `True`.

- `panels` list

  Per-device panel list, managed on the panel editing screen for the selected device.

## How Settings Are Saved

Every device setting, including `enabled`, and the device's panels are saved in Home Assistant's storage for the hub. The hub's config entry only lists the devices (name and ESPHome device ID).

- **Saving applies immediately.** Saving in the editor applies the new settings and panels to the running device without a restart. A setting you clear goes back to its default. Enabling or disabling a device reloads the hub.
- **New devices start enabled.** Devices found through ESPHome discovery are added enabled. A device you disable stays disabled, and a device you remove stays removed until you add it again.
- **Upgrading from 0.3.2 or earlier.** Settings that older versions kept in the config entry are not carried over. After updating, check each device's settings in the editor.

## Device Settings

Opened with **Device settings** in the toolbar for the selected device, or the **Settings** action in the toolbar menu. Fields are grouped into collapsible sections:

### General Settings

- `locale` string

  Display language — one of `en_US`, `de_DE`, `nl_NL`, `pl_PL`, `fr_FR`. Determines how dates, times, and numbers are formatted and which language is used for built-in text labels.

- `display_model` string

  Hardware display model — one of `eu` (default) or `us`. Selects which TFT layout the display needs. The default `eu` covers every landscape-mounted panel (including a US panel mounted landscape, which is functionally identical); `us` is a US panel mounted portrait (buttons below the screen) and needs the rotated portrait TFT. The update controller downloads the matching TFT asset for the selected model. See [Display Models](display-models.md).

### Display dimming & off

- `use_auto_dimming` bool

  When enabled, the display dims automatically after `timeout_dimming` seconds of inactivity. This only changes the brightness — it never switches pages. Default `True`.

- `timeout_dimming` int

  Seconds of inactivity before the display dims (`0` = disabled, max `3600` in the editor). Default `10`.

- `use_auto_display_off` bool

  When enabled, the display turns off (brightness to zero) after `timeout_display_off` seconds of inactivity. This is a display-brightness behavior of the firmware; it never requires a page switch and needs no idle page configured. A touch or button press wakes the display again. Default `True`.

- `timeout_display_off` int

  Seconds of inactivity before the display turns off (`0` = disabled, max `3600` in the editor). Default `120`.

- `use_sleep_schedule` bool

  Enable a daily **display-off schedule** that drives `use_auto_display_off` by the clock: inside the window below the display may turn off after `timeout_display_off` seconds of inactivity; outside it the display never turns off automatically — it only dims (`use_auto_dimming`) while the idle page stays visible. While enabled, the window overrides the `use_auto_display_off` toggle. The hub applies the clock value itself on every start, reconnect and setting save, and at each window boundary, so no automation is needed to keep `switch.<device>_use_auto_display_off` in the right state during the day — this is the native replacement for automations that toggle it. Default `False`.

- `sleep_schedule_start` string

  Start of the display-off schedule window in `HH:MM` 24-hour format. Only used when `use_sleep_schedule` is enabled. Supports overnight ranges (e.g. `22:00`–`07:00`). If either start or end is empty, or a value is not in `HH:MM` format, the schedule is inactive and `use_auto_display_off` is used as-is (the malformed case is logged as a warning). Default empty.

- `sleep_schedule_end` string

  End of the display-off schedule window in `HH:MM` 24-hour format. Only used when `use_sleep_schedule` is enabled. Supports overnight ranges. If either start or end is empty, or a value is not in `HH:MM` format, the schedule is inactive and `use_auto_display_off` is used as-is. Default empty.

### Automatic page switching

- `use_auto_page` bool

  When enabled, the hub switches to the configured idle page (`idle_panel`) after `timeout_page` seconds of inactivity. This only changes the shown page — it neither dims nor turns the display off (use `use_auto_display_off` for that). A touch or button press returns to the panel you were on. Default `True`.

- `timeout_page` int

  Seconds of inactivity before the idle page opens (`0` = disabled, max `3600` in the editor). Default `30`.

- `debug_level` int

  Diagnostic logging verbosity shown in the dropdown as Off (`0`), Basic (`1`), or Verbose (`2`). Default `0`.

- `log_items` bool

  Log every item update of this device to the Home Assistant log, for troubleshooting. Default `False`.

- `stale_data_seconds` int

  Stale-data indicator: when an item's entity has not updated for this many seconds, the **Row** page renders its value dimmed with a `…` suffix instead of pretending the old value is current. `0` (default) disables the indicator. Set it just above the expected update interval of the slowest sensor you display (e.g. `300` for a 5-minute weather sensor).

### Time & Date

- `time_format` string

  strftime format for the time shown on the clock, clock-two and weather pages. Empty (default) inherits the global `%H:%M`; `%I:%M %p` gives the US 12-hour form (`2:30 PM`). Picking "Custom strftime…" in the editor lets you type any strftime directive.

- `date_format` string

  strftime format for the date shown on the clock and weather pages. Empty (default) inherits the global `%A, %d. %B %Y`. The US numeric form is `%m/%d/%Y` (`03/14/2026`), the US long form `%B %d, %Y` (`March 14, 2026`).

### Display Buttons

- `show_home_button` bool

  Show a home navigation button on panels. Default `False`.

- `show_idle_button` bool

  Show the idle button that manually opens the configured idle panel. Default `False`. The idle button can be displaced by the notification button: when a panel has no free right-side header slot (e.g. a grid/row with pagination in navigation), the notification button takes over the idle button's slot so unread notifications stay reachable — see [Notifications](../device.md#notifications).

- `show_notifications_button` bool

  Show the notifications button on supported panels. Default `True`.

### Gestures

A single swipe always navigates: left/right step through the navigation
panels, up opens the About page, down opens Settings. Gesture sequences add
shortcuts on top of that.

- `gesture_sequences` list

  Each entry opens a panel when its swipes arrive in the given order within
  the time limit: `sequence` (one or more of `swipe_left`, `swipe_right`,
  `swipe_up`, `swipe_down`), `timeframe` (1–60 seconds from the first swipe
  to the last) and `open` (the panel key to open). A wrong swipe cancels the
  sequence; the single-swipe navigation still happens for every swipe. In the
  editor, type the swipes separated by commas, set the time limit and pick
  the panel. Saving applies at once — no restart needed. Default: none.

### Notifications

- `sound_on_startup` bool

  Play a short tone when the display connects to Home Assistant after a restart or power cycle. The tone plays only on a fresh boot — a Wi-Fi reconnect while the device stayed running stays silent (the firmware reports its uptime with the connection request; devices without it fall back to playing on every connect). Default `False`.

- `sound_on_notification` bool

  Play an alert tone whenever a new notification is received. Notifications of type `critical` use the `alert` sound, and a `persistent` notification repeats its tone until dismissed. The timer panel's finish alert follows this setting too. Default `False`.

- `persistent_sound_interval` int

  Seconds between repeats of the alert tone while a persistent notification waits to be dismissed. This controls the sound only — the notification popup itself re-opens about every 60 seconds. Default `5`.

- `use_do_not_disturb` bool

  Enable quiet hours to silence all sounds during the time window set below. Notifications are still queued and shown. Default `False`.

- `quiet_hours_start` string

  Start of the quiet hours window in `HH:MM` 24-hour format. Only used when `use_do_not_disturb` is enabled. Supports overnight ranges (e.g. `22:00`–`07:00`). If either start or end is empty, sounds are never silenced; a value not in `HH:MM` format is ignored the same way and logged as a warning. Default empty.

- `quiet_hours_end` string

  End of the quiet hours window in `HH:MM` 24-hour format. Only used when `use_do_not_disturb` is enabled. Supports overnight ranges. If either start or end is empty, sounds are never silenced; a value not in `HH:MM` format is ignored the same way and logged as a warning. Default empty.

### Panel Assignments

- `home_panel` string

  Panel key shown when navigating home, or when the idle page is exited without a snapshot to restore. Empty means no home panel set (the first navigation panel is used).

- `idle_panel` string

  The **idle page**: panel key opened by `use_auto_page` (automatic page switching) after the page timeout. It is a navigation target only — it never represents display-off. Empty means automatic page switching has no page to open. 

- `idle_panel_extra` string

  Comma-separated panel keys for a **carousel**: each automatic page switch advances to the next panel in `idle_panel` + `idle_panel_extra`, cycling through them as a screensaver. Empty (default) shows only `idle_panel`.

### Hardware Buttons

- `use_relay_left` / `use_relay_right` bool

  Whether the left/right hardware button toggles its internal relay. Disable to assign a Home Assistant entity instead. Default `True` for both.

- `button_left_entity` / `button_right_entity` string

  Entity ID toggled by the left/right hardware button. Only shown (and used) when the corresponding relay is disabled. Default empty.

- `reset_interaction_on_button` bool

  Whether hardware button presses reset the idle/interaction timer (and wake the display). When `False`, button presses only toggle the relay/entity and don't count as user interaction. Default `True`.

### Idle & Wake Behavior

- `snapshot_max_age_seconds` int

  Whether the panel you were on before the idle page is restored when the idle page is exited (wake):
  - **Always restore** (`-1`, default) — always restore the snapshot.
  - **Never restore** (`0`) — always go to the home panel.
  - **Custom time limit...** (`>0`) — only restore if the snapshot is newer than this many seconds.

  With Auto display-off, the display can still turn off and wake without any page switch — this setting only applies when an idle page was actually shown.

- `auto_navigate_home_timeout` int

  After this many seconds without interaction on another panel, go back to the home panel. Set it shorter than the dimming and display-off timeouts. `0` = off (default).

- `hub_idle_timeout` int

  Hub-side idle page fallback: open the idle page (`idle_panel`) after this many seconds without interaction, also when the device doesn't report its own page timeout (for example with auto page off). `0` = off (default).

## Color Overrides

Opened from its own dialog (separate from Device Settings). Lets you override individual entries of the built-in `COLORS` palette per device.

- `color_overrides` dict

  RGB565 color values keyed by color name. Unknown keys are ignored (logged) and values are clamped to `0`-`65535`. Default `{}` (empty).

  **Background: solid colour vs picture.** Pages without a picture background are cleared with the `background` colour on every panel switch (`cls <RGB565>`), so the device-level override applies there. About, Clock, Clock Two and Weather are *picture-background* pages: they keep the pre-rendered picture selected by the panel's `background` option and skip the colour clear entirely. On those pages neither the `background` override nor the header colours apply — the compiled picture and its palette win. This is by design (the picture is the background); to change their look, change the picture or edit the HMI. The remaining `COLORS` entries still theme the cards, buttons and text on solid pages as usual.

## Fields not yet exposed in the editor

These exist in the underlying config but have no UI control yet, so they stay at their defaults:

- `page_settle_delay` float — delay in seconds before settling a new page after navigation (debounce for page events). Default `0.1`.
- `date_format_locale` string — Locale-aware date pattern name (`full`, `long`, `medium`, `short`, `E`, `EEEE`) rendered with translated day/month names. Empty inherits the global `full`. Set both `date_format` and `date_format_locale` to `""` only together when you want a pure strftime date.

## Updates

The device editor's **Updates** section controls release checks and automatic installs. These settings are stored per device and merged over the integration defaults, so a device that is never opened in the editor still runs the shipped defaults.

- `check_on_connect` (default `True`) — run a release check after the device connects.
- `update_interval` (default `3600` seconds, hourly; `0` disables) — periodic release check.
- `firmware_auto_update` (default `True`) — independently checks the device's
  `HAUI Firmware` update entity and asks Home Assistant to install an offered
  firmware update. This check does not depend on the TFT being out of date.
  After reboot, the TFT follows the version required by the new firmware. Turn
  this off to disable unattended firmware installs; the explicit **Install
  firmware** action remains available when an update is offered.
- `auto_install` (default `True`) — install the TFT the firmware needs without asking. When off, the display asks first. A TFT installed by hand with a `version` or `url` ([`nspanel_haui.update_tft`](../services.md#nspanel_hauiupdate_tft)) is kept until the firmware version changes or Home Assistant restarts.

`tft_filename` (default `nspanel_haui.tft`) and `on_connect_delay` (default `60` seconds before the TFT check after a connect) remain integration defaults and are not exposed in the editor.

Home Assistant shows the display TFT as the **HAUI Display** update entity next
to **HAUI Firmware** on the device page; its **Install** runs the same TFT
install as **Install TFT** (see [Services](../services.md#haui-display-update-entity)).

A TFT install the display never confirms is reported as an error in the editor
instead of being retried automatically; press **Install TFT** to retry. The
Device Manager action menu has **Install firmware** when the `HAUI Firmware`
entity reports an available update, and **Check for updates** to refresh both
firmware availability and GitHub release info immediately (bypassing the
one-hour hub-level release cache). The check also compares the display's TFT
with the version the firmware needs and installs an outdated TFT (or asks on
the display when `auto_install` is off), and the editor shows its outcome: up
to date with the latest release, a firmware update started or available, a TFT
install started, or why the check failed.

## Global Defaults (not per-device, fixed)

The following are hardcoded defaults, not exposed anywhere in the frontend:

- **Display formats** — global defaults `time_format` (`%H:%M`), `date_format` (`%A, %d. %B %Y`), `date_format_locale` (`full`); each can be overridden per device (see Time & Date above)
- **Connection** — `heartbeat_interval` (`5.0`s), `overdue_factor` (`2.0`)
- **Navigation** — `page_timeout` (`10.0`s)
