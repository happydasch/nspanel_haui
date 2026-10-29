# Changelog

All notable changes to **NSPanel HAUI** are documented here.

The format relies on [Conventional Commits](https://www.conventionalcommits.org/)
for the messages this changelog is built from; releases are tagged `vX.Y.Z`
and follow [Semantic Versioning](https://semver.org/).

## [0.4.4] — unreleased

### Breaking changes

- **Firmware updates moved from the firmware to the integration** — the
  firmware drops its `update: platform: http_request` **HAUI Firmware** entity
  and the `firmware_manifest_url` substitution; ESPHome keeps only its stock
  dashboard update entity. The integration now provides the **HAUI Firmware**
  entity, reads the release manifest itself and installs through the
  firmware's `install_firmware_url` action, so panels on firmware 0.4.2 (which
  lacks that action) must be updated once by hand. A test panel that followed
  local test releases through the substitution needs the new **Firmware
  manifest URL** device setting instead. See
  [Upgrading → Firmware updates](docs/upgrading.md#11-firmware-updates-moved-to-the-integration).- **Firmware build variants fail closed** — a custom build from
  `esphome/install.yaml` (or the dev config) reports its variant and is never
  offered or installed the public universal release image, whose baked
  credentials would silently replace the panel's own. Panels whose firmware
  does not report a variant (0.4.3 and earlier) are treated the same: flash
  the new release once by hand (ESPHome or **Install firmware → From URL**),
  then the hub can update them again. The release manifest carries
  `"variant": "universal"`, the device state `firmware_variant`.

### Added

- **HAUI Firmware update entity in the integration** — each linked panel gets
  `update.<device>_haui_firmware` next to **HAUI Display**: installed version
  `yaml_version`, latest version from the firmware manifest, *installing* (and
  available) while the panel flashes and reboots. The hub fires
  `nspanel_haui.firmware_update_changed` events for it. An install that does
  not end in a reboot within ten minutes, or a reboot into the old version, is
  reported as an error instead of staying *installing*. The entity id the
  firmware's own entity held is reclaimed once ESPHome removed that entity.
- **Firmware manifest URL setting** — `update.firmware_manifest_url` (device
  editor → Updates) names the manifest the HAUI Firmware entity follows;
  empty means the latest GitHub release. Test panels point it at the manifest
  `scripts/dev_release.py` writes.

- **Inside temperature sensor picker** — clock and weather panels can use any
  `sensor` entity for the inside temperature; leave empty for the NSPanel's
  internal sensor.- **Inside temperature sensor picker** — clock and weather panels can use any
  `sensor` entity for the inside temperature; leave empty for the NSPanel's
  internal sensor.
- **Notification line breaks** — multi-line notification text now renders its
  line breaks on the display instead of breaking the display command.
- **Optional notification auto-dismiss** — `nspanel_haui.send_notification`
  accepts a `timeout` (seconds); on expiry the notification leaves the queue
  and, when its popup is up, the queue advances. Without a timeout nothing
  auto-dismisses, so the behavior stays exactly as before.

### Fixed

- **Internal temperature on clock/weather panels** — the registry lookup now
  works in production (Home Assistant's `HomeAssistant` object has no
  `helpers` attribute; use `homeassistant.helpers.entity_registry`), and the
  home temperature stays visible when the weather entity has no temperature
  attribute.
- **Stale time after waking the display** — clock, word clock, weather and
  alarm pages keep updating while the display is off (the Nextion stays awake
  at brightness 0 with the hub connected), so a wake touch shows the current
  time and states instead of those from when the display turned off.

### Planned

- Complete the remaining 0.4.x acceptance passlist on EU and US/portrait
  hardware, including the new firmware-OTA-to-TFT sequence and buzzer shutdown.
- Investigate the old-bootloader OTA rollback warning before treating unattended
  updates as safe.
- Notification-enhancement issue [#50](https://github.com/happydasch/nspanel_haui/issues/50)
  remains documentation-only: notification behavior is tracked and verified on
  both display models during this pass; no font-size or other notification
  implementation is planned.

See the [v0.4.4 roadmap](ROADMAP.md#v044--hardware-acceptance-and-ota-risk-closure-planned).

### Added

- **Alarm panel action-button options** — an **Action buttons** section in the
  alarm panel editor: **Hidden arm modes** leaves supported modes off the
  buttons (e.g. no *Home*), **Show action icons** puts the target state's icon
  before each label (left out when icon and label exceed the 10-byte button
  text), and text/background colours for the arm and the disarm buttons
  (empty = theme colours).

## [0.4.3] — 2026-10-28

### Breaking changes

- **TFT installs moved from the firmware to the integration** — the firmware
  drops the **Update Display** button and the `esphome.<device>_upload_tft`
  action, and the `tft_update_url_portrait` substitution is no longer used.
  Install the TFT with the new **HAUI Display** update entity or
  `nspanel_haui.update_tft` (which now takes an optional `url`).
  `esphome.<device>_upload_tft_url` remains as the hub's transport. See
  [Upgrading → TFT install actions](docs/upgrading.md#10-tft-install-actions-moved-to-the-integration).

### Added

- **HAUI Display update entity** — each linked panel gets
  `update.<device>_haui_display` next to the firmware's **HAUI Firmware**
  entity. It shows the installed TFT and the TFT the firmware needs, installs
  it, and stays *installing* (and available) while the upload keeps the device
  offline. The hub fires `nspanel_haui.display_update_changed` events for it.
- **Local test firmware releases** — `scripts/dev_release.py` turns a local
  build into `nspanel_haui_ota.bin` plus `firmware-manifest.json` for Home
  Assistant's `/local` folder, so firmware updates can be tested without a
  GitHub tag (which every panel would install). It refuses factory images and
  builds whose `yaml_version` or manifest URL does not match. See
  [Release process → local release](docs/release.md#test-firmware-updates-with-a-local-release).
- **Another firmware release or a custom build can be installed** — the
  firmware gains an `install_firmware_url` action (ESPHome's
  `ota.http_request.flash`), and the hub uses it for
  `nspanel_haui.update_firmware` with `version` or `url` and for the Device
  Manager's **Install firmware** picker (offered update, releases with an
  over-the-air image — v0.4.2 and later — or a URL). The hub reads the md5 from
  the release manifest or downloads a URL to compute it, and refuses factory
  images. A hand-installed firmware pauses the automatic firmware update until
  Home Assistant restarts or the offered update is installed. Flash this
  firmware first; older firmware can only install the offered update.
- **The editor's Install TFT action picks the TFT** — the Device Manager's
  **Install TFT** opens a picker in the device row: the version the firmware
  needs, any GitHub release that ships this display model's TFT, or a URL.
- **Another TFT release can be installed, older ones included** —
  `nspanel_haui.update_tft` takes an optional `version`, and the **HAUI
  Display** entity supports `update.install` with `version`. A TFT installed
  with `version` or `url` is no longer replaced by the automatic check right
  after its own reboot; it stays until the firmware version changes or Home
  Assistant restarts.
- **`nspanel_haui.update_tft` installs a TFT from a URL** — the optional `url`
  field replaces calling `esphome.<device>_upload_tft_url` directly and keeps
  the install tracked; it counts as done once the display reports its version
  after the upload's reboot.

### Fixed

- **"Return to the home panel after" works with an idle page** — when
  `timeout_page` was shorter than `auto_navigate_home_timeout`, the idle page
  opened first, the return-home timer gave up, and waking restored the panel
  you were on, so the display never got back home. Once the timeout has passed,
  leaving the idle page now opens the home panel.
- **Panels can be deleted on the integration page** — the device menu on
  *Settings → Devices & services → NSPanel HAUI* offered only **Disable**.
  **Delete** now removes the panel from the hub like **Remove** in the editor's
  device manager, including its settings and panels.
- **Buzzer no longer sticks on during firmware updates or reboots (#62)** — the
  RTTTL player turns a note off only from the ESP32 main loop, and 0.4.2 stopped
  it only before a TFT upload. A firmware install (the **HAUI Firmware** entity,
  firmware auto-update, or an ESPHome dashboard OTA) blocks the main loop the
  same way, and a reboot resets only the CPUs, not the buzzer's LEDC output, so
  the note playing at that moment kept sounding through the download or the boot.
  Both OTA platforms' `on_begin` and `esphome: on_shutdown` now run
  `suspend_activities` too. Flash the updated ESPHome firmware to activate the fix.
- **Universal-image panels keep their Wi-Fi across firmware updates** — the
  universal image baked a never-matching Wi-Fi network, and with a network in
  the YAML ESPHome keys the Wi-Fi entered on the captive portal to the build's
  config hash. Every firmware update with a changed config (including the
  **HAUI Firmware** auto-update) forgot it, and the panel fell back to its setup
  access point. The image now carries no network of its own, so ESPHome uses a
  fixed key, and a one-time boot step moves Wi-Fi saved by an older build to it.
- **TFT installs from GitHub releases work again** — GitHub redirects release
  TFTs to a signed URL of about 870 characters, which overflowed the display
  component's 512-byte default HTTP TX buffer (`HTTP_CLIENT: Out of buffer`),
  so every hub TFT install failed before the first byte and timed out after 20
  minutes. The vendored `nextion` component backports
  `tft_upload_http_buffer_size_tx` (esphome/esphome#21435) and the firmware sets
  it to 2048. Update the firmware first; the TFT follows after the reboot.
- **Check for updates reports its result and installs an outdated TFT** — the
  editor only said "Checking for updates" and a panel that was already current
  got no answer, so the check looked broken. It now shows whether the panel is
  up to date (with the latest release), a firmware update started or is
  available, a TFT install started, or why the GitHub check failed. The check
  also runs the TFT version check, which otherwise only ran after a connect.
- **Firmware builds fetch the nextion patch with the package** — the
  `external_components` entry for `esphome/nextion_patch` kept ESPHome's
  default 1-day cache, so a build could combine a fresh `display.yaml` with an
  older patch and fail with "[tft_upload_http_buffer_size_tx] is an invalid
  option". It now uses `refresh: 0s`.
- **The TFT install after a firmware update finds the new release** — a
  firmware install skips the GitHub release fetch, so the TFT check after its
  reboot could look up the new version in a release list cached before it was
  published and fail with "No GitHub release". A cached list without the
  requested TFT is now refetched once.

- **The idle page exits on one touch when the display is on or dim** — the
  two-touch wake guard armed while the display was dark stayed armed after the
  display turned on or dimmed, so leaving the idle page needed two touches even
  though the screen was visible. The guard is now treated as stale after the
  wake-touch duplicate window and the first touch exits; "off" keeps the
  two-touch behavior.
- **Update checks now run with the shipped defaults** — `check_on_connect`
  (now `True` by default) and `update_interval` (now `3600` seconds, hourly;
  `0` still disables) were previously unreachable user settings: the top-level
  `update` block was never merged into the running configuration, so every
  device kept the pristine defaults. Per-device update settings are now
  deep-merged from the device store over the integration defaults.
- **Firmware auto-updates no longer depend on a TFT update.** The firmware
  entity is refreshed and checked independently, so a device whose TFT is
  already current can still install a newer ESPHome firmware. Service failures
  are reported instead of being marked as a started install.
- **Firmware updates can be triggered from the editor.** The device action menu
  offers **Install firmware** when HA reports an update, and the action confirms
  the manifest state before calling `update.install`.
- **TFT updates have a device-targeted Home Assistant service.**
  `nspanel_haui.update_tft` appears once in the HA service list and requires
  selecting a single NSPanel, then installs the TFT matching that firmware.
  This avoids guessing which per-device ESPHome upload action belongs to a panel.
- **The device can fetch GitHub manifests again** — the ESPHome `http_request`
  RX buffer is raised to 8192 bytes for redirect headers and its TX buffer to
  2048 bytes for signed redirect request targets (the ESP-IDF defaults are 512
  bytes).
- **The editor can check for updates and show firmware availability** — the
  device action menu has **Check for updates** (bypassing the one-hour
  hub-level release cache) and the device list shows when the `HAUI Firmware`
  entity reports an update.
- **One GitHub request per hub, not per device** — update controllers share a
  module-level releases cache for an hour, keeping a multi-device hub inside
  GitHub's unauthenticated rate limit. A manual check bypasses the cache.
- **Grid tiles resolve state-keyed colours** — a state-keyed or templated
  `back_color`/`text_color` was passed raw to the colour parser, which renders
  it black; tiles now resolve those values and refresh their background and
  text colours when the entity state changes. The editor preview does the same.
- **Grid power buttons are no longer cut off at the bottom** — a tile refresh
  that left the power button's own colours unchanged (an attribute update,
  turning the page) redrew the tile icon, whose box overlaps the bottom of the
  power button, without redrawing the button. The power button is now redrawn
  after the icon.
- **The internal temperature sensor shows up again on the clock and weather
  panels** — the display looked it up as `sensor.{device_slug}_temperature`,
  which misses installations where the HAUI device name differs from the
  ESPHome node name (renames, area-prefixed entity ids). The sensor is now
  resolved through the entity registry by its ESPHome-authored name
  (`Temperature`), falling back to the classic id when the registry has no
  match.

- **The Device Manager's More menu can install the TFT.** **Install TFT** stays
  available when the panel has not reported its current TFT version; missing
  firmware/display versions are shown as **Unknown** instead of being hidden.

### Changed

- **Sounds are off by default** — `sound_on_startup` and
  `sound_on_notification` now default to `False`, so a new panel stays silent:
  no startup tone, no notification or persistent-notification tones and no
  timer finish alert. Panels whose device settings were saved in the editor
  keep their stored values; panels still on the defaults turn silent after the
  update. Turn them back on under **Device settings → Notifications**.
- **Optional diagnostics stay out of production by default** — `Uptime`,
  `Heap Free`, `Heap Max Block`, `Loop Time` and `Reset Reason` are included only
  by the local development config through `debug.yaml`; the shared production
  package and universal image omit them. The raw ADC and resistance sensors used
  for the internal temperature calculation remain `disabled_by_default: true`.
- The update settings (`check_on_connect`, `update_interval`,
  `firmware_auto_update`, `auto_install`) are editable per device in the
  editor's **Updates** section.
- **Editor dialogs close on a click outside** — Device Settings, the panel
  editor, Device Colors and the Device Manager now close like the other
  dialogs when you click the dimmed background or press Escape. Unsaved
  changes are discarded, as with the close button.

## [0.4.2] — 2026-10-27

### Breaking changes

- **The ESPHome web server is no longer enabled by default** — the firmware
  ships without `web_server` to free the flash and RAM that the HTTP OTA path
  (TLS, JSON, `http_request`) needs. After flashing the new firmware the
  device's web UI on port 80 and Home Assistant's "Visit" link disappear until
  you enable the component yourself: add a `web_server:` block to your own
  device YAML (see [ESPHome Component → Web server](docs/esphome.md#web-server-optional)).
  `esphome/nspanel_haui_dev.yaml` keeps the web server for local development.

### Added

- **Firmware auto-update** — the release workflow now attaches a
  `firmware-manifest.json` to every release and the firmware exposes an
  `update: platform: http_request` entity named **HAUI Firmware**. When the hub
  finds a newer release and `firmware_auto_update` is on (the default), it asks
  Home Assistant to install the device's firmware update first; the TFT the new
  firmware needs is installed after the device reboots. A firmware install that
  would collide with a running TFT upload is deferred. Set
  `firmware_auto_update: false` to keep the previous notice-only behaviour.
- **Version bump tooling** — `scripts/bump_version.py` updates the manifest,
  `pyproject.toml`, ESPHome `version.yaml` and both HMI `system.tftVersion`
  values in one command, so a release no longer needs a Nextion Editor visit
  just to type the new version.  The HMI edit is in place and only legal for a
  same-length version; a length-changing bump still needs the Editor.
  `scripts/bump_tft_version.py` bumps only the HMI text and is reused by the
  combined script.  Both have a `--check` dry run and are covered by
  `tests/test_bump_version.py`.

### Changed

- **Update checks now install the firmware first** — when a newer release exists
  and the device reports an installable firmware update, the hub triggers the
  firmware install before the TFT. The device reboots into the new firmware and
  then installs the matching TFT on the next connect. Set
  `firmware_auto_update: false` to restore the notice-only behaviour. Flash the
  updated firmware once so the `HAUI Firmware` update entity exists.
- **CI now validates version consistency and translations** — the tests workflow
  checks that the version sources agree (`scripts/bump_version.py --check`) and
  that translation files are up to date; the release workflow rejects a tag whose
  version disagrees with `manifest.json`, so a release cannot ship a mismatched
  version. The tests workflow also validates the Nextion assets and runs `ruff`
  on `scripts/`.

### Fixed

- **Firmware display reads work on released ESPHome again** — the
  numeric-response delivery fix for the stock `nextion` component
  ([esphome PR #17744](https://github.com/esphome/esphome/pull/17744)) was
  merged two days after the 2026.10.0 release tag was cut, so *no released
  ESPHome* contains it; without it every display read logged
  `Numeric return but '…' invalid type 0` and the value was dropped (`page` /
  `dim` errors after every interaction, lost `res_val`/`res_txt`/TFT-version
  reads). The firmware configs now ship a temporary vendored patch
  (`esphome/nextion_patch/`, the 2026.10.0 component plus the cherry-picked
  fix) and override the stock component with it through `external_components`
  — shipped in the `nspanel_haui.yaml` package, so installed setups pick it up
  with their next `esphome config` run; the universal/dev configs use a local
  source so CI and the release build validate the actual checkout. Recompile
  and flash the firmware once. The patch and its override blocks are removed
  (and `min_version` raised) when a released ESPHome contains #17744
  (2026.11.0).
- **TFT no longer reinstalls after every reboot (#63)** — the hub compared the
  firmware's `yaml_version` against the `tft_version` snapshot captured during the
  boot handshake, when the display had not answered yet. The empty value parsed as
  `0.0.0`, so the hub considered the TFT outdated, uploaded it, rebooted the ESP32,
  and repeated the loop. An unknown version is now treated as *unknown*: the hub
  requests a fresh device state and only evaluates known versions. A recent
  unconfirmed install is no longer auto-retried — use **Install TFT** in the editor
  to retry manually. The `INSTALLING` state now survives the reboot, and a matching
  version reported on reconnect marks the install `done`.
- **Buzzer stops when a TFT upload starts (#62)** — `upload_tft()` blocks the ESP32
  main loop for the whole transfer, so a playing RTTTL tune never had its note
  turned off and kept sounding until the reboot. The three upload entry points
  (the Update Display button and the `upload_tft`/`upload_tft_url` actions) now run
  a shared `suspend_activities` script first, which stops the buzzer; future
  stoppable components only need to be added there. Flash the updated ESPHome
  firmware to activate the fix.
- **Portrait weather time and date are centered (#64)** — the full-width portrait
  `tTime`/`tDate` widgets kept the landscape right-alignment attribute and drew
  against the screen edge. `PORTRAIT_ATTRS` now centers them; recompile the portrait
  TFT to activate the fix.
- **Failed TFT installs report why** — the update controller returns its state
  (idle/checking/installing/error/done) from `install_tft`/`run_update_display`, the
  REST API responds with HTTP 502 and the editor shows a toast when the upload
  command could not be sent. A GitHub API failure during the update check no longer
  raises out of the timer callback.

### Contributors

Thanks to [@jsenecal](https://github.com/jsenecal), whose reports drove the three
hardware fixes in this release: TFT reinstalls after every reboot
([#63](https://github.com/happydasch/nspanel_haui/issues/63)), the buzzer
continuing through a TFT upload ([#62](https://github.com/happydasch/nspanel_haui/issues/62))
and the off-centre portrait weather time and date
([#64](https://github.com/happydasch/nspanel_haui/issues/64)).

## [0.4.1] — 2026-10-26

### Fixed

- **Prevent Nextion serial RX buffer overflows** — pace every firmware display command
  with ESPHome's Nextion command pacer; Clock Two now queues its complete word matrix
  as one render batch. Flash the updated ESPHome firmware to activate pacing. Also
  includes the previously fixed Clock Two font-size and background issues.

## [0.4.0] — 2026-10-26

### Breaking changes

- **Minimum Home Assistant version raised to 2026.10** — `hacs.json` now
  declares `2026.10` (0.3.2 declared `2026.5`). Home Assistant 2026.5–2026.9 no
  longer satisfy the requirement; update Home Assistant before upgrading. The
  integration targets the 2026.10 device/config-entry APIs.
- **ESPHome 2026.10 or later is required** — the device configs set
  `min_version: 2026.10.0` and the release is built with a pinned ESPHome
  `2026.10.0`.
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
  through one popup after another. For alerts that must not be missed, use
  `persistent: true`: it loops the alert sound and re-opens its popup
  periodically until the notification is dismissed.
- **Saved panels are not migrated** — re-enter pre-0.4 panel settings in the
  editor and verify forecast type and panel navigation settings. (The five
  renamed device-setting keys *are* migrated automatically; see **Fixed**
  below and the [Upgrade guide](docs/upgrading.md).)
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
- **Nextion release gate** — `scripts/verify_nextion/verify_nextion.py` blocks a release
  until `clock.tTime` reports taps (Send Component ID), `system.tftVersion`
  matches the integration version, and the portrait asset exists.
- **US display-model support** — `display_model` (`eu` / `us`) picks the
  matching TFT release asset and per-device US time/date formats
  (`%I:%M %p`, `%m/%d/%Y`). The US portrait TFT ships with the release.
- **Notification services and entities** — the new `nspanel_haui.send_notification`
  service (`title`, `message`, `icon`, `type` (severity), `persistent`,
  `force_show` and `text_size` fields), standard `notify.<device>` /
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
- **Long notification messages are split into static pages.** The title shows a
  `(page/total)` counter and the header's left-secondary button advances to the
  next page; paging is manual — nothing advances on its own — and the button
  disappears on the final page, which stays visible, so long messages are read
  page by page instead of being truncated.
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
- Requires Python 3.14 (Home Assistant 2026.10) and ESPHome 2026.10.0.

### Fixed

- One worker per device; touches, page changes and the heartbeat stay
  responsive (concurrency cleanup).
- Actions for services without a target run; page items behave as configured.
- `hub_availability` resets on the last disconnect (not on the first).
- Row pages visually flag stale entity values (`stale_data_seconds`).
- Popups pause auto-dim correctly on devices named with capitals or `-`.
- Text-bearing widgets on grid, row, select, notify and alarm-keypad panels sit
  flat on the page background; runtime painting no longer draws a lighter
  component box behind tiles, labels and keys.

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

[0.4.2]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.2
[0.4.1]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.1
[0.4.0]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.0
