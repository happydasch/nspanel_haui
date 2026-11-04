# Changelog

All notable changes to **NSPanel HAUI** are documented here.

The format relies on [Conventional Commits](https://www.conventionalcommits.org/)
for the messages this changelog is built from; releases are tagged `vX.Y.Z`
and follow [Semantic Versioning](https://semver.org/).

## [0.4.5] — unreleased

### Breaking changes

- **The display TFT follows the firmware manifest (one update path)** — the
  manifest each release ships now carries a `tft` block (version + per display
  model asset); the **HAUI Display** entity and the TFT install actions read
  it instead of looking up a matching GitHub release. The editor's TFT picker
  therefore lists only the manifest's TFT (plus **From URL**); installing an
  older release's TFT by version is no longer possible — use **From URL** for
  that. A manifest without a `tft` block (dev firmware ships no display TFT)
  offers no display update at all instead of failing to find a release.

- **Firmware updates moved from the firmware to the integration** — the
  firmware drops its `update: platform: http_request` **HAUI Firmware** entity
  and the `firmware_manifest_url` substitution; ESPHome keeps only its stock
  dashboard update entity. The integration now provides the **HAUI Firmware**
  entity, reads the release manifest itself and installs through the
  firmware's `install_firmware_url` action, so panels on firmware 0.4.2 (which
  lacks that action) must be updated once by hand. A test panel that followed
  local test releases through the substitution needs the new **Firmware
  manifest URL** device setting instead. See
  [Upgrading → Firmware updates](docs/upgrading.md#11-firmware-updates-moved-to-the-integration).
- **Firmware build variants fail closed** — a custom build from
  `esphome/install.yaml` (or the dev config) reports its variant and is never
  offered or installed the public universal release image, whose baked
  credentials would silently replace the panel's own. Panels whose firmware
  does not report a variant (0.4.3 and earlier) are treated the same: flash
  the new release once by hand (ESPHome or **Install firmware → From URL**),
  then the hub can update them again. The release manifest carries
  `"variant": "universal"`, the device state `firmware_variant`.
- **Native OTA is encrypted with the API key** — the `ota: platform: esphome`
  block uses `encryption:` (inheriting `api_encryption_key`) instead of
  `password: $ota_password`, so builds no longer warn that the password wastes
  flash and RAM; the `ota_password` substitution and secret are gone. The
  `on_begin` suspend hook and the `http_request` OTA platform are unchanged.
  Firmware built with ESPHome 2026.9 or later (every 0.4 release) already
  accepts the encrypted upload; older firmware needs one install with
  `allow_plaintext_upload`, and a `password:` on the OTA block of your own YAML
  now fails validation. See
  [ESPHome → Encrypted native OTA](docs/esphome.md#encrypted-native-ota)
  ([#81](https://github.com/happydasch/nspanel_haui/issues/81)).

### Added

- **Screens overview** — [`docs/screens.html`](docs/screens.html) shows
  every panel, popup and system screen in the landscape and portrait layout,
  rendered by the hub itself with sample data. The new **Screens** workflow
  regenerates the page and its PNGs (`docs/assets/screens/`) after each dev
  firmware build and commits them when a screen changed
  (`gen_preview_gallery.py --docs`). The README, the panel overview and the
  panel pages show these screenshots instead of the hand-drawn previews.
- **Every popup can be edited** — the editor's System Panels section offers
  **Edit** on every popup (`popup_*`), no longer only six entity popups
  (`popup_alarm`, `popup_timer`, Notify, Select and Unlock were missing). An
  edited popup keeps the built-in defaults it does not set, keeps its key and
  never joins navigation. On the popups the hub drives (Notify, Select,
  Unlock) the editor hides **Panel pin** and **Close automatically after** and
  the hub ignores them: a PIN on Unlock would re-open Unlock forever. System,
  Blank, Settings and About stay fixed: their cards are read-only, the API
  refuses a panel saved under their key, and the store drops one an earlier
  dev build saved (logged as a warning).
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
  empty means the channel's manifest (see next bullet). Test panels point it
  at the manifest `scripts/dev_release.py` writes.
- **Firmware update channel setting** — `update.firmware_update_channel`
  (`stable` or `dev`, default `stable`) picks the manifest the HAUI Firmware
  entity follows when the URL is empty: the latest stable GitHub release, or
  the newest release in the GitHub release list, dev prereleases included.
  The manifest URL still overrides the channel.
- **Firmware version comparison matches Home Assistant** — the hub compares
  versions with the same `AwesomeVersion` semantics the HAUI Firmware/HAUI
  Display entities use, so the two never disagree: a final release is offered
  over its dev builds (`0.4.5` over `0.4.5.dev3`), and an unparseable
  installed version (for example an old `dev-<run>-<sha>` build) is withheld
  as unknown instead of being re-offered on every check. Dev builds are
  validated to report a parseable next-patch version (`X.Y.(Z+1).dev<run>`).

- **Day/Night Profiles** — each device can select Day and Night display settings
  by a fixed local window or Home Assistant sunrise/sunset with minute offsets.
  Profiles cover brightness, dimming, page/idle target and display-off behavior;
  the independent Sleep schedule keeps its existing precedence. Existing
  brightness/ramp values are adopted on first activation, and when scheduling is
  disabled those ESPHome values remain manual. See
  [Device Configuration](docs/configuration/device.md#daynight-profiles).

- **Inside temperature sensor picker** — clock and weather panels can use any
  `sensor` entity for the inside temperature; leave empty for the NSPanel's
  internal sensor.
- **Notification line breaks** — multi-line notification text now renders its
  line breaks on the display instead of breaking the display command.
- **Optional notification auto-dismiss** — `nspanel_haui.send_notification`
  accepts a `timeout` (seconds); on expiry the notification leaves the queue
  and, when its popup is up, the queue advances. Without a timeout nothing
  auto-dismisses, so the behavior stays exactly as before.
- **Live preview in the editor** — the new **Live preview** button
  (`mdi:television-play`) opens an interactive virtual panel for the selected
  device, rendered from the real hub code: tap, drag and swipe with mouse or
  finger, press the hardware buttons, trigger the idle timeout. **Sandbox
  mode** (the default) simulates every entity change; **Live mode** calls Home
  Assistant, including the panel's relays from the hardware buttons, except
  for the panel's settings. A **Show entities** switch names the entity under
  the mouse. The preview fires no events for automations and never installs
  updates. A device has one virtual copy, shared by its open previews and its
  panel cards; it follows every save.
- **Reset sandbox** — the live preview's **Reset sandbox** button restores every
  simulated entity to its starting state without leaving sandbox mode, so a
  preview can be replayed from the beginning.
- **Panel cards drawn by the hub** — every panel card (user panels, system
  panels, popup aliases, landscape and portrait) shows its panel exactly as the
  device does: the hub renders the panel and the card replays the hub's
  display output in the Nextion simulator, built from the real HMI layout.
  Entity values, translations in the device's language, templates, the clock,
  the weather forecast and colour overrides are the hub's own; unsaved edits
  show right away, and a popup's card opens it for a sample (an entity of its
  domain, one that is on if there is one, an example notification or
  selection). The dozens of per-type preview renderers and the browser-side
  copy of the hub's rendering are gone: a new panel type needs only a correct
  `PageDescriptor.page_id`.
- **Long press to go back** — Clock, ClockTwo and Weather panels have no
  header buttons and could only be left by swiping. The new **Long press to go
  back** panel option (Advanced section) goes back on a one-second hold
  anywhere: to the panel this one was opened from, or to the home panel.
- **Alarm panel action-button options** — an **Action buttons** section in the
  alarm panel editor: **Hidden arm modes** leaves supported modes off the
  buttons (e.g. no *Home*), **Show action icons** puts the target state's icon
  before each label (left out when icon and label exceed the 10-byte button
  text), and text/background colours for the arm and the disarm buttons
  (empty = theme colours).

### Fixed

- **Panels follow the `background` colour override** — the hub cleared the
  page with the overridden `background`, but the HMI draws every flat widget
  (texts, icons, flat buttons) in its own page colour, so on the row,
  settings, notification, climate, timer, cover, light, media, vacuum, QR and
  alarm/unlock pages those widgets stayed dark grey boxes on the themed page.
  The hub now gives them the theme's `background` too; which widgets the HMI
  compiles with a theme colour is exported to
  `haui/mapping/theme_widgets.json`. The alarm keypad's **Keypad button
  background** and **Keypad text color** now default to the theme's
  `background` and `component_text` instead of the fixed default palette.
- **Controls follow `component_background`** — slider tracks, the row
  toggles' off state and the media progress bar kept the HMI's fixed grey, so
  the **Component → Background** color did nothing on content pages. They now
  use it (the toggles' on state uses `component_active`). With the default
  theme these tracks are one step darker than before ([40, 40, 40] instead of
  [49, 49, 49]), matching the documented page < header < cards < pressed steps.
- **Pressed buttons follow `component_pressed`** — the header buttons, flat
  buttons (timer arrows, alarm keys, media and cover controls, select and row
  buttons) and the highlighted climate mode and light function tiles kept the
  HMI's compiled pressed grey, so overriding **Component → Pressed** changed
  almost nothing. Their pressed state now uses it. The climate setpoint arrows
  and the vacuum entity buttons, which pressed to a lighter grey
  ([115, 115, 115]) left over from before the dark theme, press like every
  other button now.
- **An open notification is no longer replaced by the next one** — the hub
  recognised its notification popup and list by the panel type
  (`popup_notify`), but those panels have the page's type (`notify`,
  `select`), so the check never matched on a device: a force-show
  notification opened over the one being read, and the open list did not
  refresh when a notification arrived. The check now uses the panel key.
- **Stacked panels show the up arrow** — a cover, light, climate, media,
  vacuum, timer or alarm panel outside navigation was treated as a popup
  because its page *can* pop up, so its header showed home instead of the up
  arrow (and no home button). It now gets up + home like a stacked grid; only
  the system popups (`popup_*`, About, Settings) keep the popup header.
- **The unlock popup shows its keypad and title again** — the alarm page hides
  its keypad when it loads and the alarm panel shows it again, but the unlock
  popup on the same page did not, so a PIN-protected panel opened onto an
  empty screen with no way to enter the PIN. Its title also stayed empty when
  the locked panel has none: the system panel's empty title replaced the
  **Unlock Panel** fallback. Guarding a navigation panel with the home button
  on, its header showed home in place of the previous-panel button; it now
  shows the guarded panel's previous, home and next buttons. Those buttons
  (and swiping) also work every time now: the popup kept the guarded panel's
  navigation state after it closed, so from its second opening on navigation
  took the popup itself for the current panel and previous/next did nothing.
- **Internal temperature on clock/weather panels** — the registry lookup now
  works in production (Home Assistant's `HomeAssistant` object has no
  `helpers` attribute; use `homeassistant.helpers.entity_registry`), and the
  home temperature stays visible when the weather entity has no temperature
  attribute.
- **Light power button no longer turns black** — an on/off or brightness-only
  light reports no `rgb_color`, so its centre power button was drawn black
  (invisible on the dark theme) while the light was on. It now uses the
  `entity_on` colour.
- **Clock and weather panels show 0 °C** — an outside temperature of exactly
  0 °C was treated as missing, so the temperature (and on the weather panel
  the pressure) disappeared at freezing point. A weather entity shown as a
  row or info value had the same problem.
- **Clock temperature card on opening** — a clock whose first card is the
  outside or inside temperature drew it before reading the panel's weather
  entity: `--°C` on the first open, the previous panel's weather afterwards.
- **Whole numbers without ".0"** — the weather pressure, the climate current
  temperature and a weather entity's row value print `1012hPa` / `21°C`
  instead of `1012.0hPa` / `21.0°C`, so the panel and the editor preview
  show the same text.
- **HACS versioning of dev releases** — a `dev` prerelease is now tagged with
  its PEP 440 version (for example `0.4.5.dev123`) instead of
  `dev-<run>-<sha>`, and the tag points at a release commit that carries that
  same version in the integration `manifest.json`. HACS reads release tags as
  available versions and the installed copy's manifest `version` as the
  installed one, so the old unparseable tags compared by plain string
  inequality: an installed dev build kept offering itself as an update and dev
  releases were listed without a usable order. Dev releases now compare (and
  sort) correctly; already installed `dev-*` builds are offered the next
  versioned dev release once. The version carries no `+g<sha>` build segment
  (the commit is in the release name): AwesomeVersion sorts such a build above
  its final release and above later plain dev builds, so it would never be
  offered either. Dev builds published with the segment before 2026-11-04 need
  one manual install of a newer build. Only the newest 10 dev prereleases are
  kept, so the latest stable release stays within the 30 releases HACS reads.
- **Stale time after waking the display** — clock, word clock, weather and
  alarm pages keep updating while the display is off (the Nextion stays awake
  at brightness 0 with the hub connected), so a wake touch shows the current
  time and states instead of those from when the display turned off.

- **Firmware update notice compared the display TFT by mistake** — the
  "Update available" popup on the panel compared the newest GitHub release
  with the installed display `tft_version` instead of the installed firmware
  `yaml_version` (they can differ on firmware-only releases). It now compares
  like for like, so an up-to-date display can no longer hide a firmware update
  (nor a stale display invent one), and the version line shows
  `yaml_version → release`.
- **An unparseable firmware-manifest version is withheld from the HAUI
  Firmware entity** — Home Assistant falls back to "update available" when it
  cannot compare an offered version, so an incomparable manifest `version`
  would surface as an update on every check. It is now reported as unknown
  (no update) instead.
- **TFT updates no longer infer the required version from the firmware** — a
  firmware that did not report `tft_required_version` was treated as requiring
  its own `yaml_version`, so a display could be flagged outdated (or updated)
  on a guess. The hub now checks the TFT only when the firmware reports
  `tft_required_version`; the Device Manager shows **Unknown** instead of
  inventing a version.
- **Notification paging keeps the dismiss button** — the manual next-page
  button moved from the left-secondary to the inner-right header slot, so the
  outer-right **Dismiss** button stays available on buttonless notification
  popups (update notices, entity-unavailable, timer).
- **Notification popups no longer keep the display lit** — a queued
  notification popup suspended auto-dimming and auto display-off until it was
  dismissed, so a notification at night switched a dark panel on at full
  brightness and left it on. It now only holds off the automatic page switch;
  the display dims and turns off on its normal timers. A force-shown
  notification and a persistent alert's re-opened popup wake the display
  explicitly, except during quiet hours.
- **Persistent alert sound and quiet hours** — a persistent notification that
  arrived during quiet hours never started its repeating sound, not even after
  quiet hours ended, and one that arrived before them kept sounding through
  them. The repeat now always runs and is silent inside quiet hours.
- **Notification indicator blink runs on the hub's worker** — the blink timer
  ran page code on a thread of its own, racing page switches; it now uses the
  app's timers and skips blink ticks while the display is off.
- **Notification text fits the popup** — paging counted characters with
  guessed per-line figures, so short lines (e.g. the "Entity unavailable"
  text) overflowed the text box while ordinary messages were split across
  pages they did not need ("Someone is at the front door" took two pages at
  the large font). Text is now wrapped with the display fonts' real glyph
  widths (exported from the HMI to `haui/mapping/font_metrics.json`), a page
  holds the lines the box is tall and no more than the widget stores, and the
  automatic text size picks the largest font that fits the whole message on
  one page.
- **Notification ids are unique** — the `id` in `nspanel_haui.notification`
  events and the editor inbox was a Python object id, which is reused as soon
  as a notification is freed, so automations could mix notifications up and a
  stale inbox could dismiss the wrong one.
- **Notifications without an icon use the full text width** — since the
  severity default icon was dropped, an icon-less popup left the icon's area
  empty and kept the message in its narrow column. The message now fills the
  full-width text box (the full height in portrait), so more fits per page.
- **Quotes and backslashes in display text** — text was sent to the display
  without escaping, so a `"` in a notification, title or entity name ended the
  command's string early and the text (or the whole command) was lost, and a
  trailing `\` swallowed the closing quote. Both are now escaped as the Nextion
  expects (`\"`, `\\`); a `\r` written into a configured text still forces a
  line break. The editor's live preview decodes the same escapes.

### Planned

- Complete the remaining 0.4.x acceptance passlist on EU and US/portrait
  hardware, including the new firmware-OTA-to-TFT sequence and buzzer shutdown.
- Investigate the old-bootloader OTA rollback warning before treating unattended
  updates as safe.
- Notification-enhancement issue [#50](https://github.com/happydasch/nspanel_haui/issues/50)
  remains documentation-only: notification behavior is tracked and verified on
  both display models during this pass; no font-size or other notification
  implementation is planned.

See the [v0.4.5 roadmap](ROADMAP.md#v045--hardware-acceptance-and-ota-risk-closure-in-progress).

### Contributors

Thanks to [@jameshiscott](https://github.com/jameshiscott) for the live preview
in the editor ([#85](https://github.com/happydasch/nspanel_haui/pull/85),
[#86](https://github.com/happydasch/nspanel_haui/pull/86)) and the **Long press
to go back** panel option.

## [0.4.4] — 2026-11-02

### Fixed

- **Notification `timeout` accepted by the service schema (#78)** — the
  released service metadata advertised `timeout`, but the runtime schema
  rejected it with "not a valid option". The service now accepts and forwards
  the timeout, and the notification controller auto-dismisses timed
  notifications. Without a timeout, notifications continue to stay queued
  until dismissed, replaced or cleared. Thanks to [@liviusefu](https://github.com/liviusefu)
  for reporting the issue.

The TFT display files are unchanged from 0.4.3; panels keep their installed
TFT until a later release updates it.

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
