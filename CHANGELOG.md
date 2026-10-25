# Changelog

All notable changes to **NSPanel HAUI** are documented here.

The format relies on [Conventional Commits](https://www.conventionalcommits.org/)
for the messages this changelog is built from; releases are tagged `vX.Y.Z`
and follow [Semantic Versioning](https://semver.org/).

## [0.4.0] — unreleased

### Breaking changes

- **HA service and display settings were renamed** — the idle-page service and
  automatic display-off settings/entities now use the new vocabulary. No aliases
  are kept; update automations and dashboard entity references.
- **ESPHome API names changed** — the display actions and events use explicit
  display-on/display-off names, and notification actions are consolidated into
  one action with optional `persistent` and `text_size` variables.
- **Notification auto-dismiss was removed** — the `timeout` field is gone from
  `nspanel_haui.send_notification`, the ESPHome `send_notification` action/event
  and the `nspanel_haui.notification` event. Notifications stay in the queue
  until dismissed on the panel, replaced or cleared; queued notifications play
  through one popup after another. For alarms that must be acknowledged, use
  `require_ack: true` (it re-opens the popup periodically until **Acknowledge**
  is pressed).
- **Saved panels are not migrated** — re-enter pre-0.4 panel settings in the
  editor and verify forecast type and panel navigation settings. (Device
  settings *are* migrated automatically; see **Fixed** below and the
  [Upgrade guide](docs/upgrading.md).)
- **Several compatibility paths were removed** — validation is required, YAML
  imports require the documented root shape, and color/template/function-button
  and vacuum battery configuration follow the current documented formats.
  See the [Upgrade guide](docs/upgrading.md) for exact changes and update steps.

### Added

- **Universal prebuilt firmware** (`nspanel_haui.bin`) — one binary for EU and
  US/portrait panels, provisioned over its open access point (Wi-Fi entered
  once at first boot). `name_add_mac_suffix: true` appends the last six MAC
  digits at runtime, so **one binary installs any number of panels**: each gets
  a unique hostname, mDNS name and setup AP without a per-device ESPHome build.
  Compiled and attached by the new release workflow, gated on the Nextion
  release checks.
- **Gesture navigation** — left/right swipes move through navigation panels, up
  opens About, down opens Settings. Named gesture sequences (timeframe,
  sequence, open target) are configurable in the editor and saved without a
  restart.
- **Device discovery** in the editor — Device Manager → Scan finds ESPHome
  devices on the network and offers to add them.
- **Configurable display auto-behaviour** — dimming, page transition and display-off
  timeouts per device (`timeout_dimming` / `timeout_page` / `timeout_display_off`).
- **Display-off schedule** (`use_sleep_schedule` / `sleep_schedule_start` /
  `sleep_schedule_end`) — a daily window during which `use_auto_display_off`
  may turn the display off after `timeout_display_off` seconds of inactivity;
  outside the window the display never turns off automatically (it only
  dims). The hub applies the schedule itself at every start, reconnect, save
  and window boundary, replacing automations that toggle the switch.
- **Vacuum battery sensor** option — point the vacuum panel at a dedicated
  sensor instead of relying on the deprecated battery attributes.
- **Alarm keypad styling** — font size, background and text colour per alarm
  panel.
- **Nextion release gate** — `scripts/verify_nextion.py` blocks a release
  until `clock.tTime` reports taps (Send Component ID), `system.tftVersion`
  matches the integration version, and the portrait asset exists.
- **US display-model support** — `display_model` (`eu` / `us`) picks the
  matching TFT release asset and per-device US time/date formats
  (`%I:%M %p`, `%m/%d/%Y`). The US portrait TFT ships with the release.
- **Ack-required notifications** — `require_ack` re-opens the popup and loops
  the alert sound until the user presses **Acknowledge**.
- **Notification services and entities** — the new `nspanel_haui.send_notification`
  service (title, message, icon, severity, persistent, force-show,
  acknowledge and text-size fields), standard `notify.<device>` /
  `notify.<device>_persistent_notification` entities, the
  `nspanel_haui.reset_last_interaction` service, and the renamed `idle` service
  (was `sleep`).
- **Per-notification text size** — `text_size` (`"auto"` or a font size 1-3)
  on `nspanel_haui.send_notification` and the `send_notification` ESPHome
  action controls the popup font per notification.
- **HA-native events** for automations: `nspanel_haui.page_changed`,
  `nspanel_haui.notification`, `nspanel_haui.connection_changed`.
- **Current-page string sensor** per device, for automation triggers
  (the internal numeric `page` sensor is unchanged).
- **Panel Doctor** — device status now reports disconnect reason, offline-since,
  connection uptime and the integration version; the editor's Device Info and
  Device Manager dialogs surface them with a stale-data indicator.
- **TFT update workflow** — the editor can trigger TFT installs per device
  (Device Manager → Install TFT) and shows the update state
  (`checking`/`installing`/`done`/`error` + version and last error) in the
  Device Manager and Device Info dialogs.
- **Firmware download** — Device Manager → Download firmware opens the
  prebuilt `.bin` of the latest release when one is attached, and
  explains the build-from-YAML path otherwise.
- **Idle panel carousel** (`idle_panel_extra`) — each idle cycle advances to the
  next screensaver panel.
- **Device Manager** view in the editor listing all NSPanels (online/offline,
  firmware/TFT versions, IP, signal strength) with add/remove/enable/disable
  and display refresh actions.
- **Install TFT** action per device in the editor (TFT installs remain
  automatic on connect; the button triggers an install immediately).
- Thermostat/Climate panel with setpoint adjustment.
- `action` item type to trigger HA automations / scripts from a panel button.
- Preview thumbnails for every panel type in the editor grid view.
- Entity picker with search and domain filter.
- Toasts for save/delete/error events in the editor.
- Dedicated flashing/installation documentation (`docs/install.md`).

### Changed

- **Device settings have one home**: `config_entry.data` holds only the hub
  identity and per-device identity; all settings and panels live in the panel
  store. One worker thread per device.
- TFT auto-update compares on every connect and installs the version the
  firmware needs (right away or after a display prompt, per `auto_install`).
- `clock.tTime` now reports taps with its component ID so tapping the time
  advances the card (TFT 0.4.0).
- Edge-swipe gestures use the device's display model: the hub syncs
  `display_model` to a firmware `Display Model` number, so portrait panels
  detect edge swipes on 320×480 like landscape panels do on 450×320.
- The startup sound plays only after a fresh boot, not on Wi-Fi reconnects.
- **Dark-theme refresh** with stepped surfaces (page `#101010` < header
  `#181818` < cards `#282828` < pressed `#313131`, text `#e0e0e0`), mirrored by
  the editor previews; both TFTs compile their content widgets with the new
  page colour, so text and buttons don't show as lighter boxes.
- **Background behaviour documented** — picture-background pages (About,
  Clock, Clock Two, Weather) skip the colour clear by design and keep their
  compiled picture; solid pages keep applying the device `background`
  override via `cls`. See `docs/configuration/device.md`.
- Settings and panels save without reloading the hub; removed devices stay
  removed ("keep config" removal does not re-add them).
- Device settings reach the firmware on save **and** on every connect —
  config-sync and network-info reads resolve entities through Home Assistant's
  entity registry, so a panel renamed or given an area (as happens with the
  universal image) still gets its settings and health data.
- The `wakeup` service works without a wakeup panel.
- Climate/weather/row/QR pages follow their entities' state as documented.
- Editor translations: complete baselines for all five locales (`de`, `en`,
  `fr`, `nl`, `pl`).
- Requires Python 3.14 (Home Assistant 2026.5) and ESPHome 2026.10.0.

### Fixed

- One worker per device; touches, page changes and the heartbeat stay
  responsive (concurrency cleanup).
- Actions for services without a target run; page items behave as configured.
- `hub_availability` resets on the last disconnect (not on the first).
- Row pages visually flag stale entity values (`stale_data_seconds`).
- Popups pause auto-dim correctly on devices named with capitals or `-`.

- **Device settings from 0.3.x are migrated on upgrade.** The store loader now
  renames the legacy config keys in place (`sleep_panel` → `idle_panel`,
  `sleep_panel_extra` → `idle_panel_extra`, `show_sleep_button` →
  `show_idle_button`, `use_auto_sleeping` → `use_auto_display_off`,
  `timeout_sleep` → `timeout_display_off`) and saves them back. Previously an
  unset `idle_panel` made the idle page and the header idle button silently
  no-ops, and auto display-off could not be toggled off from a stored
  `use_auto_sleeping`.
- **The notification indicator falls back to the idle button's slot when there
  is no free right header slot.** When a panel claims both right header slots
  (grid/row pagination on the home panel, ...) and notifications are enabled,
  the notification indicator takes over the idle button's slot on the home
  panel so unread notifications stay reachable instead of disappearing.

> **Update warning:** both the ESPHome firmware **and** the Nextion TFT changed
> since 0.3.2 — you must update **both**. On first connect after updating the
> integration, the display installs the matching TFT automatically (or asks,
> depending on `auto_install`). The release ships the universal prebuilt
> firmware `nspanel_haui.bin` — flash it, join the access point named after the
> device (e.g. `nspanel-haui-a1b2c3`, the MAC suffix keeps every AP unique) to
> enter your Wi-Fi, then add the device with the documented API key (see
> `docs/install.md`).
>
> **This is the first stable release with breaking changes.** Pre-0.4 saved
> **panels** are not migrated — re-enter them in the editor after updating
> (the five renamed device-setting keys *are* migrated automatically, see
> the [Upgrade guide](docs/upgrading.md)). The idle-page service, several
> ESPHome actions/events and two config entities were renamed, and no aliases
> are kept.

[0.4.0]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.0