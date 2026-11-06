# Changelog

All notable changes to **NSPanel HAUI**, one line per change. The release notes
of each [GitHub release](https://github.com/happydasch/nspanel_haui/releases)
(prepared in `.github/release-notes/<tag>.md`) describe the changes in detail,
and [Upgrading](docs/upgrading.md) has the steps for every breaking change.

Releases are tagged `vX.Y.Z` and follow [Semantic Versioning](https://semver.org/);
commit messages follow [Conventional Commits](https://www.conventionalcommits.org/).

## [0.4.5] — unreleased

### Breaking changes

- Home Assistant 2026.11 is required; install and update through its
  Marketplace, which migrates HACS installs
  ([Upgrading](docs/upgrading.md#15-home-assistant-202611-and-the-marketplace)).
- Firmware updates moved from the firmware to the integration's **HAUI
  Firmware** entity; panels on firmware 0.4.3 or older are updated once by hand
  ([Upgrading](docs/upgrading.md#11-firmware-updates-moved-to-the-integration)).
- Custom firmware builds are never offered the universal release image; the
  manifest and the device state name the build variant.
- The display TFT follows the firmware manifest; another release's TFT installs
  only **From URL**
  ([Upgrading](docs/upgrading.md#12-display-tft-updates-come-from-the-firmware-manifest)).
- Native OTA is encrypted with the API key; the `ota_password` substitution is
  gone ([#81](https://github.com/happydasch/nspanel_haui/issues/81),
  [ESPHome](docs/esphome.md#encrypted-native-ota)).
- The **Current Page** sensor moved to the firmware; delete the old integration
  entity ([Upgrading](docs/upgrading.md#14-the-current-page-sensor-moved-to-the-firmware)).
- The firmware drops the `haui_discover`, `req_device_info` and `req_reconnect`
  actions and the `use_relay_left`/`use_relay_right` events, which the hub
  never used ([Upgrading](docs/upgrading.md#16-unused-firmware-actions-and-events-removed)).
- The services raise an error when their `device` matches no running panel,
  instead of logging a warning and doing nothing
  ([Upgrading](docs/upgrading.md#18-services-fail-on-a-device-that-is-no-panel)).
- The standalone firmware **Update Display** button and the `tft_update_url`
  substitution are gone; TFT management is the hub's **HAUI Display** update
  entity, `nspanel_haui.update_tft`, or **Device Manager → Install TFT**
  ([Upgrading](docs/upgrading.md#10-tft-install-actions-moved-to-the-integration)).

### Added

- Live preview in the editor: an interactive virtual panel run by the hub, in
  sandbox or live mode ([#85](https://github.com/happydasch/nspanel_haui/pull/85),
  [#86](https://github.com/happydasch/nspanel_haui/pull/86)).
- Panel cards drawn by the hub: every card replays the hub's own render of its
  panel, unsaved edits included.
- [Screens overview](docs/screens.html) of every screen in landscape and
  portrait, regenerated after each dev build.
- Every popup can be edited; System, Blank, Settings and About stay fixed.
- **HAUI Firmware** update entity in the integration, with the **Firmware update
  channel** (`stable`/`dev`) and **Firmware manifest URL** settings.
- Day/Night profiles for brightness, dimming, idle page and display-off, by time
  window or sunrise/sunset.
- Cycle cards on the weather panel, up to four entity cards and configurable
  card timing.
- Inside temperature sensor picker for clock and weather panels.
- **Long press to go back** option for Clock, ClockTwo and Weather panels.
- Alarm panel action-button options: hidden arm modes, action icons and button
  colours ([#75](https://github.com/happydasch/nspanel_haui/pull/75)).
- **Current Page Number** sensor (the Nextion page id); it and **Current
  Page** are disabled by default ([ESPHome](docs/esphome.md#page)).

### Changed

- Portrait function buttons are back in the header; portrait pages use the full
  height (portrait TFT).
- Row toggles are a switch icon instead of a filled box.
- Cycle cards are off by default on clock and weather panels: only the time
  shows until **Show date**, **Show outside temperature** or other cards are
  enabled (clock panels cycled date and outside temperature before;
  [Upgrading](docs/upgrading.md#17-cycle-cards-are-off-by-default)).
- **Screen Power** is disabled by default, like **Restart Display**.
- Firmware versions compare like Home Assistant's: a final release is offered
  over its dev builds, and an unparseable version counts as unknown.
- Dev prereleases ship both display TFTs, and dev panels install the TFT their
  firmware needs ([Release](docs/release.md#published-development-firmware)).

### Fixed

- Cycle cards switch to a shorter form instead of running past the time area.
- The `background`, `component_background` and `component_pressed` colour
  overrides reach flat widgets, sliders and pressed buttons.
- Pages load in the device's colours instead of changing colour after they
  are shown, and saved colours apply at once (new display TFT).
- A saved background of the shown clock, word clock or weather panel, and the
  word clock's options, apply at once instead of on the next page change.
- The clock and weather temperature text no longer turns from grey to white
  after the page is shown (new display TFT).
- An open notification is no longer replaced by a force-shown one, and the open
  list refreshes.
- Stacked panels and popups show up and home; stacked grids and rows keep their
  close button.
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
- The clock's temperature card shows the panel's own weather on opening.
- Whole numbers print without ".0" (`1012hPa`, `21°C`).
- Dev releases are tagged with their version (`X.Y.Z.devN`), so the Marketplace
  orders them and offers updates correctly.
- Clock, word clock, weather and alarm pages are current after waking the
  display.
- The panel's update notice compares the firmware version, not the TFT version.
- TFT checks no longer guess the required version when the firmware does not
  report it.
- Notification paging keeps the **Dismiss** button.
- Notification popups no longer keep the display lit.
- The persistent alert sound starts after quiet hours and is silent inside them.
- The notification indicator blink runs on the hub's worker thread.
- Notification text is wrapped with the display fonts' real glyph widths.
- Notification ids are unique.
- Notifications without an icon use the full text width.
- Multi-line notification text renders its line breaks.
- Quotes and backslashes in display text are escaped.
- The services accept the NSPanel HAUI device their device selector offers, not
  only the panel's ESPHome device.
- A TFT upload or firmware install that ends without the panel rebooting is
  reported as failed instead of done.
- Device Manager: the TFT picker names the required TFT version, not the
  firmware version; **Download firmware** skips dev prereleases; disabled
  devices offer no actions that need a running panel; a failed reorder keeps
  the old order; **Remove** asks for confirmation.

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
  ([Upgrading](docs/upgrading.md#10-tft-install-actions-moved-to-the-integration)).

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

See [Upgrading](docs/upgrading.md) for the steps.

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

[0.4.5]: https://github.com/happydasch/nspanel_haui/compare/v0.4.4...dev
[0.4.4]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.4
[0.4.3]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.3
[0.4.2]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.2
[0.4.1]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.1
[0.4.0]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.0
