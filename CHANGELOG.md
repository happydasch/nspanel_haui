# Changelog

All notable changes to **NSPanel HAUI**, one line per change. The release notes
of each [GitHub release](https://github.com/happydasch/nspanel_haui/releases)
(prepared in `.github/release-notes/<tag>.md`) describe the changes in detail,
and [Update Process](docs/develop/update-process.md) has the steps for every breaking
change.

Releases are tagged `vX.Y.Z` and follow [Semantic Versioning](https://semver.org/);
commit messages follow [Conventional Commits](https://www.conventionalcommits.org/).

## [0.5.0] — unreleased

### Breaking changes

- Custom themes now use a shared theme library. Per-device `color_overrides` and `theme_overrides` are no longer supported. Hand-written config must use `theme_id` and `theme_variant`. The **Device Colors** sidebar is now the **Theme** sidebar on Preview, and the Appearance section is gone from device settings ([Themes](docs/user/configuration/themes.md), [Upgrading](docs/user/update.md#themes-replace-color-schemes)).
- A **Schedule** of entries (from/to as a time, or sunrise or sunset with an offset; sound, brightness, screen off and its duration) replaces the Day/Night profiles and the quiet hours; saved settings are not converted, and **Brightness** is a new device setting ([Upgrading](docs/develop/update-process.md#21-schedule-replaces-daynight-profiles-and-quiet-hours)).

### Changed

- The device settings sidebar has seven sections instead of nine: **General**, **Screen**, **Home & idle**, **Screen buttons & gestures**, **Hardware buttons**, **Sounds** and **Advanced**; rows in them open the **Theme**, **Schedule**, **Gestures** and **Updates** sidebars and show what each holds ([Device Configuration](docs/user/configuration/device.md#device-settings)).
- Editor saves now use scoped endpoints for one device's settings or panels, and a separate device-order endpoint; saving preserves other devices' data and reordering does not reload the hub.
- **Themes** are a shared library of predefined and custom palettes: the Theme sidebar on Preview selects one per device, edits shared semantic and state-icon colors, and imports or exports the library; applying a theme leaves panel and item colors as explicit overrides ([Themes](docs/user/configuration/themes.md)).
- Every panel, including editable popups, can override its color theme; an empty selection follows the device, and the selected theme colors the page, items and icons ([Panels](docs/user/configuration/panels.md), [Themes](docs/user/configuration/themes.md)).
- The **Theme** section of the device settings selects the device's theme from the same predefined and custom dropdown, with **New theme**, **Export all** and **Import**; editing a theme's colors stays in the Theme sidebar ([Themes](docs/user/configuration/themes.md)).
- Single swipes and multi-swipe sequences are one list, the device setting `gestures`: each gesture can step to the next or previous panel or open a panel, and saved `swipe_actions` and `gesture_sequences` are converted ([Gestures](docs/user/configuration/device.md#gestures)).
- The **Schedule** and **Gestures** cards use consistent collapsible entry rows with summaries and counts; a newly added entry opens for editing.
- The **Schedule** card in the device's **Panels** view supports multiple time windows, including sunrise/sunset offsets and windows across midnight, with per-window sound, brightness, dimming and display-off settings ([Schedule](docs/user/configuration/device.md#schedule)).
- The ESPHome firmware now caps dimmed brightness at the active full-brightness value, so a schedule entry with a low brightness cannot brighten the display when dimming begins.
- Frontend translations now cover all editor strings in English, German, French, Dutch and Polish, including the theme, schedule and gesture controls.
- Editor field hints show only while the pointer rests on the field or keyboard focus is in it, floating over the form instead of taking space; touch screens keep them visible.
- The documentation is split into a user guide (`docs/user/`) and a developer guide (`docs/develop/`), so page addresses changed (`install.html` is now `user/install.html`); the user pages are rewritten in plainer language and **Custom Integration** is merged into [Installation](docs/user/install.md).
- The sidebar editor is a Fleet/Device dashboard with linkable routes; the **Device Manager** and **Device Info** dialogs and the header's ⋯ menu are gone ([frontend](docs/develop/frontend.md#target-v05-dashboard)).
- Fleet scans for new panels when it opens, enables, disables and removes devices from their inventory row, installs every device's updates at once and lists the dated hub log of every device under **Latest events**, a repeated message once with its count.
- The Fleet screen below the carousel is a denser read: one summary strip (a state-coloured health line, the update and version figures, and a segment per device) instead of three tiles, 15 px card headings with count chips, a dense inventory table and the latest events as a timeline ([frontend](docs/develop/frontend.md#fleet-screen-regions)).
- Each Device view starts with a highlighted card of its next actions, above the workspace on a narrow screen: **Add panel**, with the **Settings** as a cog beside the card's title, led by **Install update** on the Preview while one is offered; **Updates** opens from the **Connection & device** card ([Configuration](docs/user/configuration/README.md#finding-the-editor)).
- The Preview's **Manage this device** card carries **Theme**, **Schedule** and **Gestures** as three plain buttons in one row, whatever the card's width; each opens its editor in the sidebar — **Theme** the shared theme editor, **Schedule** and **Gestures** their own, with an explicit **Save** — so the card never grows when an option is opened ([Configuration](docs/user/configuration/README.md#the-theme-sidebar)).
- The Device screen's **Connection & device** and **Diagnostics** cards replace Device Info; **Updates**, **Device settings**, **Theme** and **Logs** open in the sidebar, a full-screen page on a phone.
- **Logs** is a sidebar on the Device and Fleet screens: newest first and grouped by day, filtered by level or text, warnings and errors tagged, and a copy button for bug reports ([Device](docs/user/configuration/device.md)).
- Diagnostics shows the display state, the idle page countdown, the disconnects and late heartbeats of the last 24 hours and the current page's entities, and **Copy report** builds a bug report without entity ids or addresses ([Device health](docs/user/configuration/README.md#diagnostics)).
- The **Connection & device** card lists the four connection facts (uptime, Wi-Fi, current page, IP); the firmware and display versions are in **Diagnostics** and the **Updates** sidebar ([The Device Screen](docs/user/configuration/README.md#the-device-screen)).
- The device status API replaces `idle_page_active` with `idle_page` and adds `display_state` and `connection_health`; the `reset_interaction` endpoint is gone (the Live preview resets the timer) and hub log lines carry an ISO timestamp and the full level name.
- Panels: search, inline rename, duplicate, copy from another device (grouped by device in **Add panel**), and only the popups a device extends in the list (**Add panel → Extend a popup** offers the built-in ones); a panel is reordered by dragging its grip, so the row menu no longer carries **Move up** and **Move down**.
- Selecting a panel row describes it in the side column under the **Panels** card: its render (foldable to a thumbnail, remembered per browser), type, key, group, item count, Home/Idle role and its **Edit**, **Duplicate** and **Delete** actions; close the card or select the row again to return to the overview, which explains the panel groups and names the configured Home and Idle panels instead ([Panels](docs/user/configuration/panels.md)).
- The extra idle panels of the carousel (`idle_panel_extra`) are an ordered list of panels to add, remove and reorder in **Device Settings → Special pages**, alongside the home panel setting ([Panels](docs/user/configuration/panels.md#home-and-idle-panels)).
- Sidebars can be resized by dragging their edge, and the panel editor fits its sidebar: a preview that pins as a small thumbnail with the panel's name and type once scrolled, the item list open with its count, compact item rows, and a random entity in an entity popup's preview ([Configuration](docs/user/configuration/README.md#the-panel-editor)).
- The panel editor previews unsaved edits and marks the field that cannot be saved; **Add panel** previews every panel type and a panel thumbnail enlarges on hover or tap.
- **Add panel** renders every type with representative sample entities and example values, including a sample weather forecast; entity popup previews use an entity of the right domain when one is available ([The Panel List](docs/user/configuration/README.md#the-panel-list)).
- **Add panel** is a stack of collapsible groups, each led by its heading row (icon, name, count, chevron) and tinted while open, like the panel editor's sections: the panel types under **Backgrounds**, **Entities**, **Grouping** and **Tools**, then **Extend a popup** and **Copy an existing panel**; every type card leads with the panel's full-width render, and a search opens the groups it looks into ([The Panel List](docs/user/configuration/README.md#the-panel-list)).
- Device settings merge the language and the time and date formats into **Language & region**.
- The **Updates** sidebar leads with one status (up to date, update available, installing, failed, or why no update fits) above the firmware and display versions ([Update Process](docs/develop/update-process.md#editor-the-updates-sidebar)).
- The **Updates** sidebar's preferences are its **Update settings** card: the update channel, how often to check and whether a new version waits for you or installs automatically, with the rest folded under **Advanced**; each change saves by itself and **Check for updates** runs along the status card's bottom edge ([Update Process](docs/develop/update-process.md#editor-the-updates-sidebar)).
- The periodic update check interval is a preset from 15 minutes to one week, with a custom seconds value ([Update settings](docs/user/configuration/device.md#updates)).
- **Updates** no longer offers **Download firmware** and the `/api/nspanel_haui/firmware` endpoint is gone; download `nspanel_haui.bin` from the GitHub release.
- Preview: sounds and errors show as toasts, and its tools (**Reset sandbox**; in Live **Reset interaction** and **Redraw display**) are in the expanded **Diagnostics** card.
- Preview: a click on the **Current page** tile shows the panel's current page in the Simulated preview; the device status API adds `current_panel` ([Controls](docs/user/configuration/README.md#controls)).
- Panel cards show their last render, kept in the browser, until the hub's new one arrives, instead of a placeholder after every reload ([Configuration](docs/user/configuration/README.md#the-live-preview)).
- Editor performance: cards and the preview no longer redraw on every state change, one status poll runs and pauses in a background tab, modules are cached, and the entity picker lists at most 100 matches.
- Development builds of this cycle publish as `0.5.0.devN` instead of continuing
  the `0.4.8` patch line; the cycle base is committed with
  `scripts/bump_version.py` and the Development Firmware workflow keeps it when
  it writes its run number.
- Release checks: stable and development releases refuse a TFT that does not carry the configured `tft_version`, CI requires a `tft_version` bump when a compiled TFT changes as well as an HMI, and the redundant `verify_nextion.py` gate is folded into the layout spec checks and the test suite ([Release process](docs/develop/release.md#ci-gates-and-local-checks)).
- Development firmware builds run CI on the version commit they push to `dev`, which also deploys its screen overview to the dev docs; the commit no longer carries a skip-CI trailer ([Release process](docs/develop/release.md#published-development-firmware)).
- **Add panel** offers eight starter templates under **Start from a template**; a template opens in the editor with the entities it needs marked ([The Panel List](docs/user/configuration/README.md#the-panel-list)).
- The panel editor and the hub check each panel option against its type (entity domain, required entity, number range, choices, item limit, colour); a new or changed panel that breaks a rule cannot be saved, an unknown entity only warns, and older panels show **Check settings** ([The Panel Editor](docs/user/configuration/README.md#the-panel-editor)).
- A failed automatic firmware or display install is retried after **Wait between attempts** and stops after its attempt limit (3 by default) instead of retrying the firmware hourly forever and the display never ([Update Process](docs/develop/update-process.md#settings)).
- An automatic firmware install waits 10 minutes first; the Updates sidebar can install it now, put it off by an hour or a day, or skip the version ([Update Process](docs/develop/update-process.md#firmware)).
- **Install updates** on Fleet installs one device at a time on the hub, stops at the first failure and can cancel the devices still queued ([Update Process](docs/develop/update-process.md#installing-every-device-one-at-a-time)).
- A running firmware or display install shows its step and an estimate of the time left in the Updates sidebar and on Fleet ([Update Process](docs/develop/update-process.md#progress)).
- The device's time and date formats apply to every panel: date, time, date-and-time, `input_datetime` and `event` entities and timestamp and date sensors show their state in them instead of as ISO text ([Device Configuration](docs/user/configuration/device.md#general)).

### Fixed

- Device settings: a **Date format** other than Default now takes effect; the default **Locale-aware date layout** overrode it.
- Gestures: the last swipe of a gesture sequence no longer also runs its own swipe action, which navigated away from the panel the sequence had just opened.
- Unlock popup: the keypad takes the code again; since 0.4.5 it ignored every key, on the panel and in the preview, so a locked panel could not be opened.
- Device settings: a number field no longer snaps to its minimum (or loses an unfinished entry) while it is being edited.
- Editor sidebar: Tab and Shift+Tab stay inside the open panel editor or device settings instead of jumping to the close button or leaving the sidebar.
- Theme sidebar: built-in theme names are translated.
- Preview: the **Idle** control explains when the device has no idle panels instead of doing nothing.
- Panels: the idle-panel drag hint only appears when there are idle panels to reorder.
- Hub log: a panel's missing entity is warned about once, until it exists again, instead of on every render, which filled the log and pushed every other message out.
- Editor: a page left open across a Home Assistant restart that changed the editor reloads itself, instead of failing with "nspanel-simulator-frame has already been used" and showing a blank panel.
- Hub: grid and row updates and light colour drags run on the device's worker instead of a second thread, entity service calls reach Home Assistant in order, and a slow weather forecast no longer stalls the panel.
- Panels: a page no longer carries one panel's state into the next: the select popup forgets the previous popup's multiple selection and page, the unlock popup opens without the last code, light, weather and timer panels start from their own options, and a tap still being told apart from a swipe never reaches the next panel.
- Cover, climate, media and vacuum panels show their controls again when their entity comes back after being unavailable, instead of keeping them hidden until the panel is opened again.
- Connection: a panel that reboots without the hub timing out first is reported disconnected before it reconnects (`nspanel_haui.connection_changed` fires `false`, then `true`), so the update and idle handling reset as after any other drop.
- Updates: a check always answers the editor and the update entity, also for a release without a title or notes (which used to break the check); a firmware install never starts during a TFT upload, nor a TFT upload during a firmware install, even when one began while the other's files were fetched.
- Hub: a touch that recovers a lost page switch no longer leaves the page timeout armed to reload the page again 10 s later; a command the panel did not receive is sent again instead of being dropped as a duplicate; clearing the notifications closes an open notification list.
- Updates: a working TFT install no longer shows the error of an earlier failed attempt in the update entity, and a TFT install or release list whose check a newer one replaced says so instead of acting on a manifest that may be stale; idle page: saving while a later idle panel of the carousel is shown keeps it the idle page, so a touch still leaves it.
- Update notices: the release notice and the firmware install notice are queued notifications, so they never replace a notification you are reading; they appear in the notification list and fire `nspanel_haui.notification`, and the install notice leaves the queue when the install ends ([Update Process](docs/develop/update-process.md#on-the-display)).
- Updates: a firmware or TFT install and the TFT release list always answer the editor and the update entity, also when they fail on the hub after fetching or when the device's app stops meanwhile, instead of leaving the request waiting forever.
- Hub: every panel option, device setting and update setting has its default in one place (the panel type's option, `DEVICE_CONFIG`, `DEFAULT_CONFIG["update"]`); the pages and controllers no longer keep second copies, some of which had drifted from the declared default.

## [0.4.7] — 2026-11-11

### Changed

- CI is consolidated into three workflows: `ci.yml` runs every push/PR gate
  (plus the nightly validators) and deploys Pages from a docs build made once
  per run, and the development build commits the version and the regenerated
  screen overview as one `[skip ci]` bot commit (`screens_only` regenerates the
  screens alone).
- Development firmware builds are dispatched manually instead of running on
  every `dev` push, so commits no longer publish a prerelease, push a bot
  version commit or regenerate the screens.
- The editor now runs on one observable store and one typed API client behind
  the existing views, with the v0.5 frontend architecture documented in
  `docs/develop/frontend.md`.
- The preview's idle control toggles the idle page: pressing it again wakes
  back to the panel it covered (or home) and restarts the interaction timer, in
  both Simulated and Live mode
  ([Configuration](docs/user/configuration/README.md#the-live-preview)).

### Fixed

- Opening the Simulated preview starts the virtual panel over on its home panel
  with the real entity states, as switching back from Live already did.

## [0.4.6] — 2026-11-09

### Fixed

- The Marketplace no longer reports Home Assistant 2026.11.0 as too old:
  `hacs.json` declares the minimum as `2026.11.0`
  ([#90](https://github.com/happydasch/nspanel_haui/issues/90)).

## [0.4.5] — 2026-11-09

### Breaking changes

- Home Assistant 2026.11 is required; install and update through its
  Marketplace, which migrates HACS installs
  ([Upgrading](docs/develop/update-process.md#15-home-assistant-202611-and-the-marketplace)).
- Firmware updates moved from the firmware to the integration's **HAUI
  Firmware** entity; panels on firmware 0.4.3 or older are updated once by hand
  ([Upgrading](docs/develop/update-process.md#11-firmware-updates-moved-to-the-integration)).
- Custom firmware builds are never offered the universal release image; the
  manifest and the device state name the build variant.
- The display TFT follows the firmware manifest; another release's TFT installs
  only **From URL**
  ([Upgrading](docs/develop/update-process.md#12-display-tft-updates-come-from-the-firmware-manifest)).
- Native OTA is encrypted with the API key; the `ota_password` substitution is
  gone, and panels on 0.4 firmware need no migration install
  ([#81](https://github.com/happydasch/nspanel_haui/issues/81),
  [ESPHome](docs/develop/esphome.md#encrypted-native-ota)).
- The **Current Page** sensor moved to the firmware; delete the old integration
  entity ([Upgrading](docs/develop/update-process.md#14-the-current-page-sensor-moved-to-the-firmware)).
- The firmware drops the `haui_discover`, `req_device_info` and `req_reconnect`
  actions and the `use_relay_left`/`use_relay_right` events, which the hub
  never used ([Upgrading](docs/develop/update-process.md#16-unused-firmware-actions-and-events-removed)).
- The services raise an error when their `device` matches no running panel,
  instead of logging a warning and doing nothing
  ([Upgrading](docs/develop/update-process.md#18-services-fail-on-a-device-that-is-no-panel)).
- The firmware drops the **Use Auto-Page** switch, **Timeout Page** number and `esphome.timeout` event; automatic page switching and each page's hold move to the hub. Empty Night idle keys no longer inherit Day; `use_auto_page`/`timeout_page` remain device settings.
- The `hub_idle_timeout` device setting is gone; the hub's own idle-page check replaces it ([Device Configuration](docs/user/configuration/device.md#automatic-page-switching)).
- Update the integration first, then install matching firmware and TFT; mixed hub and firmware versions are unsupported ([Upgrade guide](docs/user/update.md#automatic-page-switching-moved-to-the-hub)).
- Notification `type` (`info`/`warning`/`critical`) is replaced by `icon_color` and `sound` on `nspanel_haui.send_notification`; the `nspanel_haui.notification` event carries both instead of `notif_type`, and the ESPHome `send_notification` action requires the two new variables ([Upgrading](docs/develop/update-process.md#20-notification-types-replaced-by-icon-colour-and-sound)).
- Persistent notifications now open immediately on every path and may re-open over the idle page; the `critical`-only idle guard is gone ([Notifications](docs/user/device.md#notifications)).

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
  Page** are disabled by default ([ESPHome](docs/develop/esphome.md#page)).
- **Install update** in the **Device Info** dialog installs the display TFT or
  the firmware, also from a URL or a local file
  ([Updating](docs/user/update.md#installing-a-local-tft-or-firmware-image)).
- **Firmware mismatch** in the Device Manager and Device Info when the HAUI
  version differs from the panel firmware's `yaml_version`; missing versions
  are not a mismatch ([Update Process](docs/develop/update-process.md#in-the-editor)).
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
  [Upgrading](docs/develop/update-process.md#17-cycle-cards-are-off-by-default)).
- A clock panel without a weather entity skips the outside temperature card
  instead of showing `--°C`.
- **Screen Power** is disabled by default, like **Restart Display**.
- The **Touch** and **Brightness** sensors are disabled by default; enable them
  on the device page before using them in automations.
- Firmware versions compare like Home Assistant's: a final release is offered
  over its dev builds, an unparseable version counts as unknown, and the
  editor's version chips use the same ordering.
- Dev prereleases ship both display TFTs, and dev panels install the TFT their
  firmware needs ([Release](docs/develop/release.md#published-development-firmware)).
- CI fails a PR or push that changes a Nextion HMI without advancing the display
  TFT version and recompiling both TFTs, reading the base HMI's version when the
  base predates `tft_version`
  ([Release](docs/develop/release.md#published-development-firmware)).
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
  ([Update Process](docs/develop/update-process.md#on-the-display)).
- A notification sent without an icon shows none and uses the full text width;
  its icon colour and sound are general notification fields
  ([Services](docs/user/services.md#nspanel_hauisend_notification)).
- Grid tile, alarm keypad/action-button and Clock Two word colors default to the
  active color scheme; their optional color settings override it per panel or
  item. Values saved from older versions keep overriding until **Reset existing
  panel and item color overrides**.
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
- A hub reconnect no longer counts as an interaction: the current page is restored at full brightness for the configured dimming timeout, then normal brightness timeouts resume. The hub restarts the idle-page timeout after restoring the page; the idle page and auto-navigate-home now run from one level-triggered hub check ([Device](docs/user/device.md#display-state-dimmed-off-and-on)).

### Fixed

- The Colors dialog shows the device's saved color scheme in its selector again instead of the first built-in scheme.
- On hub disconnect, the firmware shows System at full brightness for `timeout_dim`, then dims without powering off; reconnect restores the current panel with the same grace ([Device](docs/user/device.md#display-state-dimmed-off-and-on)).
- Repeated automation changes to HAUI-owned display switches now trigger a warning and pause corrections until the next connect or settings save, preventing on/off feedback loops ([Device Configuration](docs/user/configuration/device.md#display-dimming-off)).
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
  of switching off on every boot ([ESPHome](docs/develop/esphome.md#interaction)).

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
  ([Upgrading](docs/develop/update-process.md#10-tft-install-actions-moved-to-the-integration)).

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
  ([ESPHome → Web server](docs/develop/esphome.md#web-server-optional)).

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

See [Updating](docs/user/update.md) for the steps.

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

[0.5.0]: https://github.com/happydasch/nspanel_haui/compare/v0.4.7...dev
[0.4.7]: https://github.com/happydasch/nspanel_haui/compare/v0.4.6...v0.4.7
[0.4.6]: https://github.com/happydasch/nspanel_haui/compare/v0.4.5...v0.4.6
[0.4.5]: https://github.com/happydasch/nspanel_haui/compare/v0.4.4...v0.4.5
[0.4.4]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.4
[0.4.3]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.3
[0.4.2]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.2
[0.4.1]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.1
[0.4.0]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.0
