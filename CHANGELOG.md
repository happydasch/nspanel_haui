# Changelog

All notable changes to **NSPanel HAUI**, one line per change. The release notes
of each [GitHub release](https://github.com/happydasch/nspanel_haui/releases)
(prepared in `.github/release-notes/<tag>.md`) describe the changes in detail,
and [Update Process](docs/update-process.md) has the steps for every breaking
change.

Releases are tagged `vX.Y.Z` and follow [Semantic Versioning](https://semver.org/);
commit messages follow [Conventional Commits](https://www.conventionalcommits.org/).

## [0.4.6] — unreleased

## [0.4.5] — 2026-11-09

### Breaking changes

- Home Assistant 2026.11 is required; install and update through its
  Marketplace, which migrates HACS installs
  ([Upgrading](docs/update-process.md#15-home-assistant-202611-and-the-marketplace)).
- Firmware updates moved from the firmware to the integration's **HAUI
  Firmware** entity; panels on firmware 0.4.3 or older are updated once by hand
  ([Upgrading](docs/update-process.md#11-firmware-updates-moved-to-the-integration)).
- Custom firmware builds are never offered the universal release image; the
  manifest and the device state name the build variant.
- The display TFT follows the firmware manifest; another release's TFT installs
  only **From URL**
  ([Upgrading](docs/update-process.md#12-display-tft-updates-come-from-the-firmware-manifest)).
- Native OTA is encrypted with the API key; the `ota_password` substitution is
  gone, and panels on 0.4 firmware need no migration install
  ([#81](https://github.com/happydasch/nspanel_haui/issues/81),
  [ESPHome](docs/esphome.md#encrypted-native-ota)).
- The **Current Page** sensor moved to the firmware; delete the old integration
  entity ([Upgrading](docs/update-process.md#14-the-current-page-sensor-moved-to-the-firmware)).
- The firmware drops the `haui_discover`, `req_device_info` and `req_reconnect`
  actions and the `use_relay_left`/`use_relay_right` events, which the hub
  never used ([Upgrading](docs/update-process.md#16-unused-firmware-actions-and-events-removed)).
- The services raise an error when their `device` matches no running panel,
  instead of logging a warning and doing nothing
  ([Upgrading](docs/update-process.md#18-services-fail-on-a-device-that-is-no-panel)).
- The firmware drops the **Use Auto-Page** switch, **Timeout Page** number and `esphome.timeout` event; automatic page switching and each page's hold move to the hub. Empty Night idle keys no longer inherit Day; `use_auto_page`/`timeout_page` remain device settings.
- The `hub_idle_timeout` device setting is gone; the hub's own idle-page check replaces it ([Device Configuration](docs/configuration/device.md#automatic-page-switching)).
- Update the integration first, then install matching firmware and TFT; mixed hub and firmware versions are unsupported ([Upgrade guide](docs/update.md#automatic-page-switching-moved-to-the-hub)).
- Notification `type` (`info`/`warning`/`critical`) is replaced by `icon_color` and `sound` on `nspanel_haui.send_notification`; the `nspanel_haui.notification` event carries both instead of `notif_type`, and the ESPHome `send_notification` action requires the two new variables ([Upgrading](docs/update-process.md#20-notification-types-replaced-by-icon-colour-and-sound)).
- Persistent notifications now open immediately on every path and may re-open over the idle page; the `critical`-only idle guard is gone ([Notifications](docs/device.md#notifications)).

### Added

- Live preview in the editor: an interactive virtual panel run by the hub, in
  sandbox or live mode ([#85](https://github.com/happydasch/nspanel_haui/pull/85),
  [#86](https://github.com/happydasch/nspanel_haui/pull/86)).
- The live preview mirrors the device's queued notifications, read-only.
- Panel cards drawn by the hub: every card replays the hub's own render of its
  panel, unsaved edits included.
- [Screens overview](docs/screens.html) of every screen in landscape and
  portrait, regenerated after each dev build.
- [Development docs](https://happydasch.github.io/nspanel_haui/dev/) built from
  `dev`; the editor footer opens them on dev builds.
- Every popup can be edited; System, Blank, Settings and About stay fixed.
- **HAUI Firmware** update entity in the integration, with the **Firmware update
  channel** (`stable`/`dev`) and **Firmware manifest URL** settings.
- Day/Night profiles for brightness, dimming, idle page and display-off, by time
  window or sunrise/sunset.
- Cycle cards on the weather panel, up to four entity cards and configurable
  card timing.
- Inside temperature sensor picker for clock and weather panels.
- **Long press to go back** option for Clock, ClockTwo and Weather panels.
- Alarm panel action-button options: hidden arm modes and action icons
  ([#75](https://github.com/happydasch/nspanel_haui/pull/75)).
- **Current Page Number** sensor (the Nextion page id); it and **Current
  Page** are disabled by default ([ESPHome](docs/esphome.md#page)).
- **Install update** in the **Device Info** dialog installs the display TFT or
  the firmware, also from a URL or a local file
  ([Updating](docs/update.md#installing-a-local-tft-or-firmware-image)).
- **Firmware mismatch** in the Device Manager and Device Info when the HAUI
  version differs from the panel firmware's `yaml_version`; missing versions
  are not a mismatch ([Update Process](docs/update-process.md#in-the-editor)).
- **Enable updates** master switch and **Enable periodic update checks** toggle
  per panel.
- **Color scheme library** in **Device Colors**: built-in **Dark Color**,
  **Light Color**, **White** and **Black** schemes, plus custom schemes shared
  by every device in the hub and importable/exportable as JSON.
- Dark- and light-background weather, alarm and climate icon colors in each
  scheme; a device chooses its default icon variant, and pages with a static
  background use that background's variant.
- **Use color scheme** background for clock, word clock and weather panels:
  the TFT's solid dark/light fill in the scheme's background color with the
  scheme's text and state colors (new display TFT).
- The device YAML export carries the selected custom color scheme; importing it
  restores the scheme.

### Changed

- Changing a color of a built-in scheme in the Colors dialog creates and selects a custom copy automatically.
- Changing the display model asks before installing the matching TFT; saving the setting alone no longer flashes the display.
- Portrait function buttons are back in the header; portrait pages use the full
  height (portrait TFT).
- Repository scripts use `python -m` from the repository root, without import-path setup.
- Row toggles are a switch icon instead of a filled box.
- Cycle cards are off by default on clock and weather panels: only the time
  shows until **Show date**, **Show outside temperature** or other cards are
  enabled (clock panels cycled date and outside temperature before;
  [Upgrading](docs/update-process.md#17-cycle-cards-are-off-by-default)).
- A clock panel without a weather entity skips the outside temperature card
  instead of showing `--°C`.
- **Screen Power** is disabled by default, like **Restart Display**.
- The **Touch** and **Brightness** sensors are disabled by default; enable them
  on the device page before using them in automations.
- Firmware versions compare like Home Assistant's: a final release is offered
  over its dev builds, an unparseable version counts as unknown, and the
  editor's version chips use the same ordering.
- Dev prereleases ship both display TFTs, and dev panels install the TFT their
  firmware needs ([Release](docs/release.md#published-development-firmware)).
- CI fails a PR or push that changes a Nextion HMI without advancing the display
  TFT version and recompiling both TFTs
  ([Release](docs/release.md#published-development-firmware)).
- Panel titles and built-in popup titles are single words where possible, and
  every title is fitted to its header widget (longer ones end in `..`).
- **Auto-install firmware updates** is off by default; the display TFT still
  follows a firmware update on its own.
- The Device Manager finds new panels when it opens; its install picker moved
  to the **Info** dialog (**Install update**, **Redraw display**, **Download
  firmware**), preparing the 0.5 frontend redesign.
- The About page labels the integration version **HAUI Version** (it was
  **AD-Version**).
- The release notice opens once per release instead of after every update check;
  it can appear again after a restart or a channel change
  ([Update Process](docs/update-process.md#on-the-display)).
- A notification sent without an icon shows none and uses the full text width;
  its icon colour and sound are general notification fields
  ([Services](docs/services.md#nspanel_hauisend_notification)).
- Grid tile, alarm keypad/action-button and Clock Two word colors default to the
  active color scheme; their optional color settings override it per panel or
  item. Values saved from older versions keep overriding until **Reset existing
  device and panel color overrides**.
- Devices from older versions with a pure-white background override migrate to
  the **Light Color** scheme, all others start on **Dark Color**; unknown
  scheme IDs fall back to dark with a warning.
- Single-entity panels (light, media, vacuum, cover, climate, alarm) accept no
  item and hide their controls when the entity is unavailable or `unknown`;
  light, media and vacuum also show **Unavailable**, and an `unknown` item
  opens the Unavailable message instead of running its action.
- The live preview's hardware buttons show their relay (blue) or the state of
  any entity they switch (yellow; covers report open/closed by position and
  locks, climate, alarm, media and timer entities report their active state);
  **Simulated/Live** is a toolbar switch, and **More tools** shows **Show
  entities** and **Reset sandbox** (Simulated mode only, disabled until a
  simulated state changed).
- A hub reconnect no longer counts as an interaction: the current page is restored at full brightness for the configured dimming timeout, then normal brightness timeouts resume. The hub restarts the idle-page timeout after restoring the page; the idle page and auto-navigate-home now run from one level-triggered hub check ([Device](docs/device.md#display-state-dimmed-off-and-on)).

### Fixed

- The Colors dialog shows the device's saved color scheme in its selector again instead of the first built-in scheme.
- On hub disconnect, the firmware shows System at full brightness for `timeout_dim`, then dims without powering off; reconnect restores the current panel with the same grace ([Device](docs/device.md#display-state-dimmed-off-and-on)).
- Repeated automation changes to HAUI-owned display switches now trigger a warning and pause corrections until the next connect or settings save, preventing on/off feedback loops ([Device Configuration](docs/configuration/device.md#display-dimming-off)).
- The idle page opens reliably again after popups and reconnects: the hub
  checks the activity clock every second instead of relying on one-shot timers
  and firmware events.
- The display turns off after the display-off timeout with auto-dimming
  disabled; one firmware script now owns brightness and display state.
- The display state is published only when it actually changes.
- A tap shorter than the 200 ms coordinate poll counts as an interaction, so
  the display does not dim or turn off during use (firmware).
- Cycle cards switch to a shorter form instead of running past the time area,
  and use a smaller font when a character has no glyph in the large one.
- The `background`, `component_background` and `component_pressed` colour
  overrides reach flat widgets, sliders and pressed buttons.
- Pages load in the device's colours instead of changing colour after they
  are shown, and saved colours apply at once (new display TFT).
- A saved background of the shown clock, word clock or weather panel, and the
  word clock's options, apply at once instead of on the next page change.
- The clock, word clock and weather time/date text and cycle cards follow the
  scheme's text color, and the temperature text no longer turns from grey to
  white after the page is shown (new display TFT).
- The QR page's SSID/password text and the Settings brightness labels,
  percentages and icons use the scheme colors instead of the HMI's dark-only
  ones.
- The Light panel falls back to the panel title when its entity has no name.
- An open notification is no longer replaced by a force-shown one, and the open
  list refreshes.
- Stacked panels and popups show up and home; stacked grids and rows keep their
  close button.
- Grid, row and clock tiles that open a stacked panel or run an action
  (`navigate:`, `action:`) work again instead of showing the entity-unavailable
  notification.
- The unlock popup shows its keypad and title again, has the header of the
  panel it locks (previous and next in navigation), and its navigation works
  on every opening.
- A cleared number field in the panel editor resets the option to its default
  instead of saving 0.
- ESPHome entity ids resolve through the entity registry again, so config sync
  and the inside temperature work with area-prefixed ids
  ([#77](https://github.com/happydasch/nspanel_haui/pull/77)).
- System Health no longer crashes; deprecated device registry calls are gone
  ([#77](https://github.com/happydasch/nspanel_haui/pull/77)).
- The light power button no longer turns black for lights without colour.
- Clock and weather panels and weather rows show 0 °C.
- The home temperature stays visible when the weather entity reports no
  temperature.
- The clock's temperature card shows the panel's own weather on opening.
- Whole numbers print without ".0" (`1012hPa`, `21°C`).
- Dev releases are tagged with their version (`X.Y.Z.devN`), so the Marketplace
  orders them and offers updates correctly.
- Clock, word clock, weather and alarm pages are current after waking the
  display.
- The panel's update notice compares the firmware version, not the TFT version.
- TFT checks no longer guess the required version when the firmware does not
  report it.
- An unchanged display TFT is no longer reinstalled under a newer firmware
  release: the manifest names the TFT's own version and only a newer one
  installs ([#83](https://github.com/happydasch/nspanel_haui/issues/83)).
- Notification paging keeps the **Dismiss** button.
- Notification popups no longer keep the display lit.
- The persistent alert sound starts after quiet hours and is silent inside them.
- The notification indicator blink runs on the hub's worker thread.
- Notification text is wrapped with the display fonts' real glyph widths, and
  the page counter stays visible next to a long title
  ([#84](https://github.com/happydasch/nspanel_haui/issues/84)).
- The update notice shows the release notes as plain text instead of raw
  Markdown ([#84](https://github.com/happydasch/nspanel_haui/issues/84)).
- Notification ids are unique.
- Multi-line notification text renders its line breaks.
- Quotes and backslashes in display text are escaped.
- The services accept the NSPanel HAUI device their device selector offers, not
  only the panel's ESPHome device.
- A TFT upload or firmware install that ends without the panel rebooting is
  reported as failed instead of done.
- A failed TFT upload can be retried without rebooting the panel; the retry
  stopped after 4 KB (vendored `nextion` patch).
- Custom firmware builds find their required TFT in the release of their
  firmware version when the update channel's manifest ships none.
- Device dialogs: the TFT picker names the required TFT version, not the
  firmware version; **Download firmware** skips dev prereleases; disabled
  devices offer no actions that need a running panel; a failed reorder keeps
  the old order; **Remove** asks for confirmation.
- A firmware install request with an unreadable body is refused instead of
  installing the offered firmware on every panel.
- Update checks and installs no longer stall the panel, and a busy hub no
  longer drops the panel's connection.
- Popups, the settings panel and the big QR code no longer leave auto-dimming,
  the idle page or display-off switched off when a saved config reopens them.
- The display no longer turns off with auto display-off disabled: the hub sets
  an auto switch toggled anywhere else back to its setting right away.
- The relays keep their last state across firmware updates and reboots instead
  of switching off on every boot ([ESPHome](docs/esphome.md#interaction)).

### Contributors

Thanks to [@jameshiscott](https://github.com/jameshiscott) for the live preview
([#85](https://github.com/happydasch/nspanel_haui/pull/85),
[#86](https://github.com/happydasch/nspanel_haui/pull/86)) and **Long press to
go back**, and to [@quentinjourdan](https://github.com/quentinjourdan) for the
alarm action-button options ([#75](https://github.com/happydasch/nspanel_haui/pull/75))
and the entity registry fixes ([#77](https://github.com/happydasch/nspanel_haui/pull/77)).

## [0.4.4] — 2026-11-02

### Fixed

- `nspanel_haui.send_notification` accepts `timeout` again, so a notification
  can auto-dismiss ([#78](https://github.com/happydasch/nspanel_haui/issues/78);
  thanks to [@liviusefu](https://github.com/liviusefu)).

## [0.4.3] — 2026-10-28

### Breaking changes

- TFT installs moved from the firmware to the integration; the **Update
  Display** button and the `upload_tft` action are gone
  ([Upgrading](docs/update-process.md#10-tft-install-actions-moved-to-the-integration)).

### Added

- **HAUI Display** update entity for the display TFT.
- Install another firmware or TFT release, or one from a URL:
  `nspanel_haui.update_firmware` / `nspanel_haui.update_tft` with `version` or
  `url`, and pickers in the Device Manager.
- Device Manager actions **Check for updates** and **Install firmware**.
- `nspanel_haui.update_tft` targets a single panel.
- `scripts/dev_release.py` builds a local test firmware release.

### Changed

- Sounds are off by default (`sound_on_startup`, `sound_on_notification`).
- Production firmware leaves out the diagnostic sensors.
- The update settings are editable per device in the editor.
- Editor dialogs close on a click outside or Escape.

### Fixed

- **Return to the home panel after** works with an idle page.
- Panels can be deleted on the integration page.
- The buzzer no longer sticks on during firmware updates or reboots
  ([#62](https://github.com/happydasch/nspanel_haui/issues/62)).
- Universal-image panels keep their Wi-Fi across firmware updates.
- TFT installs from GitHub releases and GitHub manifest downloads work again
  (larger HTTP buffers).
- **Check for updates** reports its result and installs an outdated TFT.
- Firmware builds fetch the `nextion` patch together with the package.
- The TFT install after a firmware update finds the new release.
- The idle page exits on one touch when the display is on or dimmed.
- The update settings take effect; `check_on_connect` and an hourly
  `update_interval` are the defaults.
- Firmware auto-updates no longer depend on a TFT update.
- Update checks share one cached GitHub request per hub.
- Grid tiles resolve state-keyed colours, and their power buttons are no longer
  cut off.
- The internal temperature sensor is found through the entity registry.
- **Install TFT** stays available when the TFT version is unknown.

## [0.4.2] — 2026-10-27

### Breaking changes

- The ESPHome web server is no longer enabled by default
  ([ESPHome → Web server](docs/esphome.md#web-server-optional)).

### Added

- Firmware auto-update: an **HAUI Firmware** entity and a
  `firmware-manifest.json` per release; the firmware installs before the TFT.
- `scripts/bump_version.py` bumps every version source, the HMI files included.

### Changed

- CI checks version consistency and translations; the release rejects a tag
  that disagrees with `manifest.json`.

### Fixed

- Display reads work on released ESPHome (vendored `nextion` patch).
- The TFT no longer reinstalls after every reboot
  ([#63](https://github.com/happydasch/nspanel_haui/issues/63)).
- The buzzer stops when a TFT upload starts
  ([#62](https://github.com/happydasch/nspanel_haui/issues/62)).
- Portrait weather time and date are centred
  ([#64](https://github.com/happydasch/nspanel_haui/issues/64)).
- Failed TFT installs report why.

### Contributors

Thanks to [@jsenecal](https://github.com/jsenecal) for the reports behind
[#62](https://github.com/happydasch/nspanel_haui/issues/62),
[#63](https://github.com/happydasch/nspanel_haui/issues/63) and
[#64](https://github.com/happydasch/nspanel_haui/issues/64).

## [0.4.1] — 2026-10-26

### Fixed

- Display commands are paced so the Nextion serial buffer no longer overflows;
  Clock Two font size and background fixes.

## [0.4.0] — 2026-10-26

### Breaking changes

- Home Assistant 2026.10 and ESPHome 2026.10 are required.
- Both the ESPHome firmware and the Nextion TFT must be updated; the release
  ships the universal firmware `nspanel_haui.bin`.
- The idle-page service, display settings and ESPHome actions/events were
  renamed, without aliases.
- Notification auto-dismiss (`timeout`) was removed.
- Saved panels are not migrated; the renamed device settings are.
- Compatibility paths were removed: validation is required, and YAML imports,
  colours, templates, function buttons and vacuum batteries follow the
  documented formats.

See [Updating](docs/update.md) for the steps.

### Added

- Universal prebuilt firmware: one `nspanel_haui.bin` for any number of EU and
  US/portrait panels.
- Gesture navigation and named gesture sequences.
- Device discovery in the editor (**Device Manager → Scan**).
- Per-device dimming, page and display-off timeouts, and a display-off schedule.
- US display model (`display_model`) with the portrait TFT and US time/date
  formats.
- `nspanel_haui.send_notification` with per-notification text size, `notify`
  entities and `nspanel_haui.reset_last_interaction`.
- Home Assistant events `nspanel_haui.page_changed`, `nspanel_haui.notification`
  and `nspanel_haui.connection_changed`.
- Current page sensor per device.
- Device Manager with panel status, TFT install, firmware download and update
  state; connection details in Device Info.
- Idle panel carousel (`idle_panel_extra`).
- Vacuum battery sensor option and alarm keypad styling.
- Climate panel, `action` item type, preview thumbnails, entity picker with
  search and editor toasts.
- Nextion release gate (`verify_nextion.py`) and installation docs.

### Changed

- Device settings live in the panel store; one worker thread per device.
- The TFT auto-update compares versions on every connect.
- Tapping the clock's time advances the card.
- Edge swipes follow the display model.
- The startup sound plays only after a fresh boot.
- Long notifications are split into pages.
- Dark theme refresh with stepped surfaces.
- Settings and panels save without reloading the hub; removed devices stay
  removed.
- Device settings reach the firmware on save and on every connect.
- The `wakeup` service works without a wakeup panel.
- Climate, weather, row and QR pages follow their entities' state.
- Complete editor translations for de, en, fr, nl and pl.

### Fixed

- Touches, page changes and the heartbeat stay responsive.
- Actions for services without a target run.
- `hub_availability` resets on the last disconnect, not the first.
- Row pages flag stale entity values (`stale_data_seconds`).
- Popups pause auto-dimming on devices named with capitals or `-`.
- Text widgets on grid, row, select, notify and alarm keypad pages sit flat on
  the page background.
- Device settings from 0.3.x are migrated on upgrade.
- The notification indicator takes the idle button's slot when no right header
  slot is free.

[0.4.6]: https://github.com/happydasch/nspanel_haui/compare/v0.4.5...dev
[0.4.5]: https://github.com/happydasch/nspanel_haui/compare/v0.4.4...v0.4.5
[0.4.4]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.4
[0.4.3]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.3
[0.4.2]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.2
[0.4.1]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.1
[0.4.0]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.0
