---
title: Device Configuration
description: Device-level configuration keys for NSPanel HAUI
---

# Device Configuration

Device-level settings configure the NSPanel hardware behaviour — buttons, sounds, timeouts, and display states. Most of this is configured through the frontend (Device Manager and Device Settings dialogs) — there is no YAML configuration.

## Device Manager

Opened from the panel toolbar. Each time it opens, it automatically finds HAUI devices among Home Assistant's ESPHome config entries and offers unconfigured devices for batch-add. This is not a network scan. It also lets you remove, reorder, enable/disable, and open settings for a device.
- **Update status** — Rows show firmware and TFT versions and current install state.
  Start manual installs from **Device Info → Install update**, not from the
  Device Manager.
- **Install retry** — After an install that the display never confirms
  (the device does not report the new TFT version within its timeout), the
  automatic path stops and reports an error. Use **Device actions → Info →
  Install update → Display (TFT)** to start a fresh attempt; a manually requested
  install is not blocked by the previous unconfirmed one. Automatic installs
  stay disabled while an install remains unconfirmed, so a display that cannot
  report its version is not uploaded to forever.
- **Remove** — Asks for confirmation, then removes the device from the hub and
  deletes its settings and panels.
- **Disabled devices** — A disabled device runs no app on the hub, so its menu
  offers only **Enable**, reordering, **Settings** and **Remove**. Manual updates
  are available from Device Info after the device is enabled.
- Each row shows whether the device is enabled, its firmware and TFT versions,
  IP address and signal strength; a display whose TFT is older than the TFT
  version the firmware requires (its `tft_required_version`, which need not
  match the firmware version) is flagged **update pending**. Wi-Fi readings are resolved
  from the ESPHome entity registry and displayed independently; unavailable
  values are omitted or shown as **Unknown**, and an unknown signal does not
  mean the device is offline. The **Device Info** dialog shows the IP, SSID and
  signal readings from the same status data. **Download firmware** opens the latest stable
  release's prebuilt `nspanel_haui.bin` when attached (development prereleases
  are skipped); otherwise it explains the build-from-YAML path. Downloading a
  public image does not mean it is compatible with a custom device. Once a
  device runs firmware with the `install_firmware_url` action (0.4.3 and later)
  and `firmware_auto_update` is on, the hub installs newer compatible firmware
  and the matching TFT follows after reboot. Older firmware must be flashed
  once manually through ESPHome.

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
- **Deleting a device in Home Assistant.** **Delete** in the device's menu on *Settings → Devices & services → NSPanel HAUI* does the same as **Remove** in the device manager: the device leaves the hub, and its settings and panels are deleted.
- **Upgrading from 0.3.2 or earlier.** Settings that older versions kept in the config entry are not carried over. After updating, check each device's settings in the editor.

## Device Settings

Opened with **Device settings** in the toolbar for the selected device, or the **Settings** action in the toolbar menu. Fields are grouped into collapsible sections:

### General Settings

- `locale` string

  Display language — one of `en_US`, `de_DE`, `nl_NL`, `pl_PL`, `fr_FR`. Determines how dates, times, and numbers are formatted and which language is used for built-in text labels.

- `display_model` string

  Hardware display model — one of `eu` (default) or `us`. Selects which TFT layout the display needs. The default `eu` covers every landscape-mounted panel (including a US panel mounted landscape, which is functionally identical); `us` is a US panel mounted portrait (buttons below the screen) and needs the rotated portrait TFT. The update controller downloads the matching TFT asset for the selected model. See [Display Models](display-models.md).

- `log_level` string

  Standard logging threshold for this device's app messages in the Home Assistant log, shown in the dropdown as Critical, Error, Warning, Info, or Debug. Default `"INFO"`. `DEBUG` adds detailed diagnostics — entity/attribute state changes and the display commands exchanged with the panel — on top of the routine Info lifecycle messages.

  The threshold sets what the hub *emits*; Home Assistant still decides what is *displayed*: to see Debug records in the HA log, add `logger: custom_components.nspanel_haui: debug` to your [logger configuration](https://www.home-assistant.io/integrations/logger/).

- **Logs** dialog — the **Logs** button in the toolbar opens the last 50 of the 100 most recent in-memory HAUI messages for the selected running device. It is a diagnostic buffer of the hub app, not a complete Home Assistant or ESPHome log viewer: firmware logs and HA messages from other integrations are not included, and the buffer is not written to disk.

### Display dimming & off

- `use_auto_dimming` bool

  When enabled, the display dims automatically after `timeout_dimming` seconds of inactivity. This only changes the brightness — it never switches pages. The hub also uses this timeout as the full-brightness grace after disconnect and reconnect. Do not drive the ESPHome switch from an automation; use the HAUI settings and schedules. Default `True`.

- `timeout_dimming` int

  Seconds of inactivity before the display dims (`0` = disabled, max `3600` in the editor). Default `10`.

- `use_auto_display_off` bool

  When enabled, the display turns off (brightness to zero) after `timeout_display_off` seconds of inactivity. This is a display-brightness behavior of the firmware; it never requires a page switch and needs no idle page configured. A touch, or a hardware-button press when `reset_interaction_on_button` is enabled, wakes the display again. Do not drive the ESPHome switch from an automation; use the HAUI Sleep schedule or Day/Night Profiles instead. Default `True`.

- `timeout_display_off` int

  Seconds of inactivity before the display turns off (`0` = disabled, max `3600` in the editor). Default `120`.

- `use_sleep_schedule` bool

  Enable a daily **display-off schedule** that drives the effective `use_auto_display_off` setting by the clock: inside the window below the display may turn off after the active profile's display-off timeout; outside it the display never turns off automatically — it only dims while the idle page stays visible. When Day/Night Profiles are enabled, this window overrides the active profile's `use_auto_display_off` toggle. The hub applies the clock value itself on every start, reconnect and setting save, and at each window boundary, so no automation is needed to keep `switch.<device>_use_auto_display_off` in the right state during the day — this is the native replacement for automations that toggle it. Default `False`.

- `sleep_schedule_start` string

  Start of the display-off schedule window in `HH:MM` 24-hour format. Only used when `use_sleep_schedule` is enabled. Supports overnight ranges (e.g. `22:00`–`07:00`). If either start or end is empty, or a value is not in `HH:MM` format, the schedule is inactive and `use_auto_display_off` is used as-is (the malformed case is logged as a warning). Default empty.

- `sleep_schedule_end` string

  End of the display-off schedule window in `HH:MM` 24-hour format. Only used when `use_sleep_schedule` is enabled. Supports overnight ranges. If either start or end is empty, or a value is not in `HH:MM` format, the schedule is inactive and `use_auto_display_off` is used as-is. Default empty.


### Day/Night profiles

The **Day/Night Profiles** section can automatically select two complete display-behavior profiles. `day_night_schedule_mode` is `off` (default), `fixed`, or `sun`. When off, existing brightness and dim-ramp values remain manual in the ESPHome Settings page; the hub does not sync them. When enabled, the hub owns the active profile's brightness and dim-ramp settings and reapplies it at startup, reconnect, settings save, and each schedule boundary.

- `day_night_schedule_mode` string

  `off` (default) leaves Day/Night scheduling disabled. `fixed` selects Night within a local clock window; `sun` selects Night from sunset to sunrise using Home Assistant's location and timezone.

- `day_night_start` / `day_night_end` string

  Fixed-clock Night start and end in `HH:MM` (24-hour) format. Defaults are `21:00` and `07:00`; overnight windows are supported. Night includes the start time and ends immediately before the configured end time. Empty, invalid, or identical times log a warning and use Day.

- `day_night_sunset_offset` / `day_night_sunrise_offset` int

  Solar schedule offsets in minutes (`-720` to `720`, default `0`). Positive values are after the event and negative values are before it. If Home Assistant cannot calculate both events for the configured location (for example, during polar day/night), the hub logs the error and safely applies Day until solar events are available again.

- `day_night_profiles_initialized` bool

  Integration-managed migration marker (default `False`). The hub sets it after it has adopted restored ESPHome brightness/ramp values or confirmed explicit Day values; it is not an editor setting.

**Day profile:** the existing `use_auto_dimming`, `timeout_dimming`, `use_auto_page`, `timeout_page`, `idle_panel`, `use_auto_display_off`, and `timeout_display_off` settings are the Day values. `use_auto_page`, `timeout_page`, and `idle_panel` are read by the hub; the firmware no longer exposes a page-switch switch or timeout number. The additional brightness/ramp values are `day_brightness_full` (0–100%), `day_brightness_dimmed` (0–100%), and `day_duration_dim` (0–5 seconds). Dimmed brightness must not exceed full brightness. On first activation, unset Day brightness and ramp values are adopted from the device's restored ESPHome numbers and saved, so existing manual settings are preserved. If an adopted brightness would violate the dimmed/full relationship, only the unset value is adjusted (dimmed is clamped to full, or full is raised to dimmed); explicit Day values are preserved. If restored ESPHome values are not yet available, the hub waits before marking migration complete or applying Day brightness/ramp.

**Night profile:** configure `night_use_auto_dimming`, `night_timeout_dimming`, `night_duration_dim`, `night_use_auto_page`, `night_timeout_page`, `night_idle_panel`, `night_use_auto_display_off`, `night_timeout_display_off`, `night_brightness_full`, and `night_brightness_dimmed`. Their defaults mirror the previous firmware behavior where applicable (auto toggles enabled, dim/page/display-off timeouts 10/30/120 seconds, brightness 50/20%, ramp 2 seconds). Brightness is constrained to 0–100%, ramp to 0–5 seconds, and timeouts to 0–3600 seconds. Page switching is hub-side; dimming/display-off settings and brightness/ramp continue to sync with the firmware. Day and Night idle destinations are independent: an empty `night_idle_panel` disables the idle page at night rather than inheriting Day's `idle_panel`. If automatic page switching is enabled for the active profile and its idle key is empty while the other profile has one configured, the hub logs a warning.

The separate `use_sleep_schedule` remains authoritative for effective automatic display-off when its window is valid: it allows display-off inside its window and prevents it outside, overriding either profile's `use_auto_display_off` value. Invalid/incomplete sleep windows continue to leave the profile's auto display-off setting in charge.

Profile timeouts are applied without counting as a touch. Firmware brightness and ramp number callbacks recalculate the inactivity baseline, so when a profile change writes those values the display may briefly change brightness before settling; a timeout-only change does not do this. This feature replaces time-of-day automations that write brightness and behavior timeout entities.

### Automatic page switching

`use_auto_page`, `timeout_page`, and the Day/Night idle panel keys are hub
settings. The firmware no longer exposes the **Use Auto-Page** switch or
**Timeout Page** number.

- `use_auto_page` bool

  When enabled, the hub switches to the configured idle page (`idle_panel`) after `timeout_page` seconds of inactivity. This only changes the shown page — it neither dims nor turns the display off (use `use_auto_display_off` for that). A touch, or a hardware-button press when `reset_interaction_on_button` is enabled, exits the idle page and restores the previous panel. Default `True`.

- `timeout_page` int

  Seconds of inactivity before the idle page opens (`0` = disabled, max `3600` in the editor). Default `30`. The hub re-evaluates this and the activity clock once per second, so a saved change applies on the next check; a reconnect restarts the timeout after the page is restored.

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

  Show the idle button that manually opens the configured idle panel. Default `False`. The idle button can be displaced by the notification button: when a panel has no free right-side header slot (e.g. a grid/row with pagination), the notification button takes over the idle button's slot so unread notifications stay reachable — see [Notifications](../device.md#notifications).

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

  Enable quiet hours to silence all sounds during the time window set below. Notifications are still queued and shown, but do not wake the display; a persistent notification's repeating tone pauses until quiet hours end. Default `False`.

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

  When enabled (default), a hardware button press resets the idle/interaction timer, wakes the display, and exits the idle page. When `False`, the button still toggles its relay or entity but does not wake the display or count as user interaction.

### Idle & Wake Behavior

- `snapshot_max_age_seconds` int

  Whether the panel you were on before the idle page is restored when the idle page is exited (wake):
  - **Always restore** (`-1`, default) — always restore the snapshot.
  - **Never restore** (`0`) — always go to the home panel.
  - **Custom time limit...** (`>0`) — only restore if the snapshot is newer than this many seconds.

  With Auto display-off, the display can still turn off and wake without any page switch — this setting only applies when an idle page was actually shown.

- `auto_navigate_home_timeout` int

  After this many seconds without interaction on another panel, go back to the home panel. Set it shorter than the dimming and display-off timeouts. When the idle page opens first (`timeout_page` is shorter), the idle page stays, and leaving it goes to the home panel instead of the panel you were on. `0` = off (default).

## Color schemes

Opened from **Editor → Colors**. Color schemes are the source of semantic color definitions used by pages and entity/domain state icons. Built-in schemes are **Dark Color**, **Light Color**, **White**, and **Black**; custom schemes are shared by every device in the same hub. The active scheme is referenced by ID (`color_scheme_id`) instead of being copied into per-device colors. Use **Save as** to create a custom scheme, edit it, then **Import** or **Export** the custom scheme library as versioned JSON.

A scheme contains the global page roles and the dark- and light-background weather, alarm, and climate state colors. The separate `color_scheme` setting (`dark` or `light`) selects the default icon contrast variant; a page with a static light/dark background selects the matching variant locally.

On solid-color pages and background pages set to **Use color scheme**, existing `color_overrides` and saved panel/item color values are compatibility overrides and take precedence. In the Colors dialog, check **Reset existing device and panel color overrides** when applying a scheme to clear them and use the scheme consistently. This reset removes legacy Grid tile, Alarm keypad/action, and Clock Two word-color values. Pages using a decorative background image instead use that image's paired dark/light contrast palette. The generic per-item `color` remains for intentional entity-specific styling. The Light panel's color picker controls the Home Assistant light entity, not the HAUI palette.

### Background pages

Clock, Weather, and Clock Two have a **Background** setting. Every decorative image background has an explicit light/dark contrast assignment, controlling text, time/date cards, and domain icons together. Select **Use color scheme** to replace the decorative image with the TFT's solid dark or light fill chosen from the selected scheme's `background` color; the active scheme supplies foreground and state colors. The HMI has solid fills for dark and light backgrounds, so custom background colors choose the matching contrast fill rather than uploading a new image.

On solid-color pages, the hub sends scheme colors before navigation and the page paints them during its HMI `Preinitialize` event. The background pages instead draw their configured background and use the paired contrast palette. See [Display color behavior](../design.md#colors).

## Fields not yet exposed in the editor

These exist in the underlying config but have no UI control yet, so they stay at their defaults:

- `page_settle_delay` float — delay in seconds before settling a new page after navigation (debounce for page events). Default `0.1`.
- `date_format_locale` string — Locale-aware date pattern name (`full`, `long`, `medium`, `short`, `E`, `EEEE`) rendered with translated day/month names. Empty inherits the global `full`. Set both `date_format` and `date_format_locale` to `""` only together when you want a pure strftime date.

## Updates

The device editor's **Updates** section controls release checks and installs. These settings are stored per device and merged over the integration defaults, so a device that is never opened in the editor still runs the shipped defaults. [Update Process](../update-process.md) walks through the whole process: when checks run, what happens with updates on or off, and how to install an update.

- `enabled` (default `True`) — master switch. When off, no update checks or firmware/display installs run, the HAUI Firmware and HAUI Display update entities become unavailable, and manual update actions/pickers are refused. An install already in progress is allowed to finish. Per-device check and auto-install settings are preserved and take effect again when updates are re-enabled.
- `check_on_connect` (default `True`) — run a release check after the device connects. This and the periodic interval below control checks only while `enabled` is on.
- `update_interval` (default `3600` seconds, hourly; `0` disables) — periodic
  release check. The **Enable periodic update checks** toggle in the device
  editor sets this to `0` when off; turning it back on restores hourly checks.
  The interval can be changed while enabled.
- `firmware_auto_update` (default `False`) — when enabled, on every release
  check installs the firmware the manifest offers when it is newer than the one
  the device runs (see `firmware_update_channel`/`firmware_manifest_url`).
  This check does not depend on the TFT being out of date. After reboot, the
  display TFT follows the new firmware's manifest. Enable this to allow
  unattended firmware installs. **Install update** is available in Device Info
  whenever updates are enabled, even if there is no currently offered update;
  it provides the full choice of firmware or TFT, releases, URL, or local file.
  Installing another release or a URL pauses this check until Home Assistant
  restarts or the offered update is installed (see
  [`nspanel_haui.update_firmware`](../services.md#nspanel_hauiupdate_firmware)).
- `firmware_update_channel` (`stable` or `dev`, default `stable`) — which
  firmware manifest the **HAUI Firmware** entity follows when
  `firmware_manifest_url` is empty: the latest stable GitHub release, or the
  newest [published development firmware](../release.md#published-development-firmware)
  (the newest release in the GitHub release list, dev prereleases included). It
  also controls GitHub release notifications: `stable` ignores
  prereleases, while `dev` considers them. Pointing a universal test panel at
  `dev` makes it follow every successful `dev`-branch build; the entity then
  never shows an older "latest" than the installed dev build.
- **Firmware build variants** — the hub only offers or installs firmware whose
  manifest `variant` matches the one the device reports. The prebuilt release
  image is `universal`; a build from
  [`esphome/install.yaml`](../install.md) (or the dev config) reports
  `custom`. A custom panel is therefore never offered the public universal
  image (`firmware_auto_update`, the **HAUI Firmware** entity and the editor's
  firmware picker all withhold it), so its API/OTA credentials cannot be
  silently replaced. Flash a custom build with **Install update → Firmware →
  From URL** instead. Firmware older than 0.4.4 reports no variant and is treated the
  same: it is not offered the release image — flash the new firmware once
  manually (ESPHome or From URL) and the hub can update it afterwards.
- `firmware_manifest_url` (empty by default) — the manifest that names the
  firmware the **HAUI Firmware** entity offers: its version, image URL and md5
  (plus the display TFT, see below). Leave the editor field empty for the
  channel selected above. A URL here always overrides the channel — point a
  custom test panel at a
  [local test release](../release.md#test-firmware-updates-with-a-local-release)
  to follow test builds instead. A changed URL (or channel) is read as soon as
  the settings are saved.
- `auto_install` (default `True`) — install the TFT the firmware's manifest
  ships without asking. When off, the display asks first. A TFT installed by
  hand with a URL ([`nspanel_haui.update_tft`](../services.md#nspanel_hauiupdate_tft))
  is kept until the firmware version changes or Home Assistant restarts.

The display TFT is part of the firmware's manifest (`tft` block): the **HAUI
Display** entity offers the TFT the manifest names for the device's display
model, and installing it downloads the manifest's asset. A manifest without a
`tft` block — a local test release names none — offers no display update at
all: the entity reports the installed TFT and stays up to date instead of
offering a release that cannot be found.

`on_connect_delay` (default `60` seconds before the TFT check after a connect)
remains an integration default and is not exposed in the editor.

Home Assistant shows the firmware as the **HAUI Firmware** update entity and
the display TFT as the **HAUI Display** update entity on the device page. Their
**Install** uses the same tracked installers as Device Info's **Install update**
action and the integration's update services (see
[Services](../services.md#haui-firmware-update-entity)).

A TFT install the display never confirms is reported as an error in the editor
instead of being retried automatically; press **Install update → Display (TFT)**
in Device Info to retry. The same picker offers firmware and TFT releases, **From
URL**, and **From local file**. Scheduled checks discover updates; the editor has
no manual **Check for updates** action. The HA update entities do not poll, so
the editor's former forced refresh is not available there; configured automatic
firmware updates are still handled by scheduled checks, and the TFT requirement
is checked separately after the device connects. A new GitHub release advisory
is shown at most once per release and points users to the configured manifest
as the firmware/display install source.

## Global Defaults (not per-device, fixed)

The following are hardcoded defaults, not exposed anywhere in the frontend:

- **Display formats** — global defaults `time_format` (`%H:%M`), `date_format` (`%A, %d. %B %Y`), `date_format_locale` (`full`); each can be overridden per device (see Time & Date above)
- **Connection** — `heartbeat_interval` (`5.0`s), `overdue_factor` (`2.0`)
- **Navigation** — `page_timeout` (`10.0`s)
