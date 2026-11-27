# Feature wishlist

Every feature idea for NSPanel HAUI — the ones intended next, the ones under
consideration, and the ones deliberately parked. The three documents split the
picture like this:

- [`ROADMAP.md`](ROADMAP.md) — Direction: horizons and release gates.
- **`FEATURE_WISHLIST.md`** (this file) — Concrete features — intended, candidate
  and declined — plus the open scope decisions.
- [`CHANGELOG.md`](CHANGELOG.md) — What has shipped.

Sections follow the roadmap's horizons. v0.6 is in development now, focused on
new panels, a bigger background set and the options that make them feel
finished. Everything else stays in the open pool until it is selected. A
candidate is promoted by moving it into a version section with a
done-means sentence; when it ships it is recorded in `CHANGELOG.md` and the
entry is deleted, so nothing here describes something that already works.

**HMI** means Nextion page or widget work in both `nextion/*.HMI` files and both
TFTs; **FW** means the ESPHome package; **Hub** means Python only; **editor**
means the sidebar frontend.

Requests arrive as GitHub issues and in
[Discussions](https://github.com/happydasch/nspanel_haui/discussions) (usually
*Features & Ideas*). Once a request in a thread is concrete it is copied here, so
the pool does not depend on a thread staying visible — with a pointer back to the
discussion it came from when there is one.

## v0.6 — In development now

Content and everyday use: new panel types people keep asking for but do not have
(a fan, a graph, free text), a refreshed and larger background set, plus options
that make panels feel finished. Other candidates remain in the open pool until
selected for this cycle.

### Panels

New panel types need Nextion page work; the other entries extend existing panel
experiences.

- **Graph panel** — A line graph of a numeric sensor over a chosen window from
  Home Assistant history — house power, temperature, humidity, solar — with
  min/max and a colour per panel. The number on a tile says little without its
  shape.
- **Text / notes panel** — Multi-line static or templated text: a calendar
  agenda, a todo list, house rules, guest Wi-Fi. Today text only fits in a
  notification popup or a single `text` item.
- **Fan panel** — Off/low/medium/high as buttons when the fan has three speeds or
  fewer, a percentage slider when it supports `set_percentage`, and a preset-mode
  picker otherwise; show the active preset and an oscillation toggle when
  supported. A `fan` entity is only a tile today; light, climate, cover, media
  and vacuum all have a detail popup. A cheaper first step: render a `fan` item
  as a speed slider in the row panel when the entity supports `set_speed`, which
  the row already does for `number` / `input_number`.
- **Cover tilt and battery** — A second slider beside position so position *and*
  tilt are visible and settable at once, plus a battery level when the cover or
  a configured sensor reports one. `cover.py` handles `current_position` only —
  `set_cover_tilt_position` is never called, so tilt-only blinds cannot be aimed
  from the panel.
- **Water heater / humidifier panel** — A detail page for `water_heater` and
  `humidifier` entities: current and target temperature or humidity, a slider,
  and the supported operation modes. Both domains get a popup like climate and
  cover.
- **Utilities / energy dashboard** — A home-page energy view with grid import
  and export, home consumption and up to six configurable groups, each showing
  two values and a direction indicator. A compact alternative to a grid of power
  sensors.
- **Status panel on the display** — The editor's diagnostics card already covers
  this (see *Already possible*); the gap is the on-device view for someone
  standing at the panel: uptime, Wi-Fi RSSI, free heap, connection state and
  the last command error, reached from the settings panel. The firmware
  publishes the readings; decide first whether the space is better spent on
  something the panel can act on.
- **Calendar / agenda** — Upcoming calendar events with a lead time before each
  starts, as a list or as a compact block the clock panel can show. Overlaps the
  text panel; decide whether it is one feature or two.

### Backgrounds

The pictures behind Clock, Clock Two and Weather are compiled into the TFTs, so
a change to them is HMI and TFT work; the docs show the result
([Background pages](docs/user/editor/themes.md#background-pages)).

- **Update and refresh the background set** — The decorative pictures have
  barely changed since the first releases, and their dimmed crop is the look
  users see most. Rework them — a new source where a picture no longer fits, a
  fresh crop and dim pass where it does — while keeping every key and its
  contrast variant. Done: both orientations carry the refreshed set, each key
  keeps its palette, and the docs gallery and card renders show the same
  pictures.
- **Show the backgrounds in the docs** — The Background pages section lists
  the pictures as a table, so nobody can see what **Modern**, **Spring** or
  **Cat** looks like before choosing one. Add a gallery of every picture in
  landscape and portrait, named with the palette it draws, generated from the
  same tiles the TFTs carry so it cannot drift from the display. Done: the
  themes page shows every background, and the normal generated-asset check
  fails while the gallery is stale.
- **More background pictures** — Grow the set beyond the seasons and the pets
  with a new batch — for example sea, forest, city or abstract art. Include at
  least one light picture, since **Light Color** is the only choice for a
  light palette today, and give each a portrait crop and a `BACKGROUND_VARIANTS`
  entry. Done: both HMIs and TFTs carry the pictures, the **Background** list
  offers them, and the docs gallery shows them.

### Panel options and interaction polish

- **Confirm before acting** — A per-item confirmation (or hold-to-run) for actions
  that should not fire on a stray tap: garage door, alarm disarm, "all lights
  off". Reuses the popup layer.
- **Hide when zero / deadband** — Hide a value — or the whole tile — while it is
  `0`, with a buffer so it does not flicker at the boundary. Fits the per-state
  `value` / `icon` / `color` overrides that already exist.
- **Show only while a condition holds** — An optional per-item condition, for
  example only while a window contact is `on`, so a page shows what matters now.
  Hidden items are skipped when pages are counted, so filtering one entry does not
  leave an empty page. Keep the key distinct from `state`, which already reads a
  value from an attribute.
- **Dash for unavailable values** — Show `–` instead of the last or a zero-ish
  number when an entity is `unavailable`. The item is already coloured as
  unavailable; the text should match.
- **Sort items by name** — Render a page's items alphabetically instead of in
  configured order, as a panel option.
- **Shrink to fit** — An option to reduce a long value's font instead of clipping
  it — bus times, calendar summaries, long sensor states. `fit_text` already
  exists for notifications to build on.
- **Notification grouping and priority** — Group or prioritise pending
  notifications instead of playing them strictly in arrival order, and keep past
  notifications after they are dismissed, with a read-only API and a view in the
  editor.
- **A maximum notification text size** — `text_size` already picks a font per
  message and `auto` takes the largest that fits; a per-device maximum would let a
  short welcome be large while an alert stays small. (Discussion
  [#93](https://github.com/happydasch/nspanel_haui/discussions/93).)
- **Status entity on a tile** — An optional second entity that colours the tile,
  so a navigation tile can show "two lights on in the kitchen" while still
  navigating there. Internal `navigate` items have no entity today, so `state`,
  `color` and `icon` cannot follow one.
- **Decimals per item** — A per-item format so a verbose reading prints as `20.1`
  instead of overflowing the tile, and a small unit keeps the digits it needs.
- **Say so when an icon is unknown** — Log a warning, and mark the tile, when a
  template or override produces an icon the display does not know, instead of
  silently drawing the generic fallback glyph.
- **Section headings** — Let a `text` item render as a heading, larger and dimmer,
  to group the rows of a long page without adding a widget type.
- **Volume step** — A configurable media volume step that the buttons move by and
  the slider snaps to, instead of the integration's own default.
- **Media mute** — A mute/unmute control on the media panel when the player
  supports volume mute, with the button state following `is_volume_muted`.
- **Stop at the last page** — An option to stop paging at the last page instead of
  wrapping to the first, for panels whose page order matters.
- **Alarm buttons that fill the card** — Hiding a mode (`hidden_arm_modes`) leaves
  its share of the action row empty, `arm_button_color` colours every arm button
  alike, and the 10-byte label cuts a translated *Disarm* together with its icon.
  A size or width per arm button, a colour worth setting per mode, and room for the
  label. (Discussion
  [#93](https://github.com/happydasch/nspanel_haui/discussions/93).)
- **Keypad feedback and state colours** — The keypad carries one flat style: font
  size, background, digit colour. Missing are a pressed-state look, a tint by
  alarm state, a border or corner radius, a different style for `CLR`/`DEL`, and
  the same options on the unlock popup. (Discussion
  [#71](https://github.com/happydasch/nspanel_haui/discussions/71).)
- **A font per item** — Grid and row items override name, icon, value, state and
  colour; the font stays a page setting, so one long name or one big number cannot
  be tuned without touching the page. (Discussion
  [#93](https://github.com/happydasch/nspanel_haui/discussions/93).)
- **QR content override** — Let the QR panel encode arbitrary text or a URL, not
  only a Wi-Fi network, while keeping the SSID/password form as a shortcut.
  Useful for guest links, support pages and login URLs.
- **Weather forecast secondary metric** — Choose which extra value appears under
  each day's high/low pair: precipitation probability, wind speed, UV index,
  sunshine duration or thunderstorm probability. Reuse the existing forecast
  sub-value slot, format it with the entity's units, and fall back to the low
  temperature when the integration lacks the chosen field.
- **Step buttons beside the sliders** — `–` / `+` at the ends of the brightness
  and position sliders, 10% per tap, so a value can be nudged precisely on a wall
  panel instead of dragged.
- **Hours in the timer** — A third field, so long timers are not dialled in
  minutes, with a quick-add that steps by 15, 30 and 60.
- **Actionable notifications** — The popup already has a left and a right button
  and a callback hook; the notification controller uses them for *Dismiss* only.
  What is missing is the user side: labels and an action per button (fire an
  event or call an action), so the panel can answer a question instead of only
  acknowledging it.

## After that — Open pool

Unscheduled candidates remain here until they are selected for a release.

### Icons and images

- **Custom full-color icons for GRID panels** — Let a grid item use a PNG icon
  (ideally with transparency) instead of the built-in MDI font glyph, chosen in
  the editor and kept across firmware updates, with an on/off pair where the
  entity has two states. Needs picture assets in both HMIs and TFTs, an editor
  image library or upload path, and a per-item mapping; the display's memory and
  picture capacity decide how large a library is practical, so a small curated
  set may be the first step. Done: a grid item shows a custom image on both
  display models, survives an update, and falls back to its MDI icon when the
  image is missing. *Area: Icons.*
  ([#105](https://github.com/happydasch/nspanel_haui/issues/105))

### Display and idle behaviour

- **Wake on sensor and hold the display** — When any configured binary sensor
  turns `on`, wake the display and leave the idle page; while any remains `on`,
  keep the panel awake (dim, but lit) instead of following the dim/off timers.
  The timers start again after the last one turns `off`. Natural fit for a
  `wakeup_entities` device setting checked in the existing 1 s navigation tick,
  beside `AUTO_PAGE_HOLD`. Today it takes an automation polling
  `reset_last_interaction`.
- **Page-wide disconnected state** — Per-entity staleness exists
  (`stale_data_seconds`); what is missing is a device-wide "the hub is not
  answering" treatment that dims all values together and marks the buttons that
  would do nothing.
- **Boot straight to the idle page** — Skip the flash of the home panel on boot
  and land on the configured idle panel (or the home panel, per setting), at dim
  brightness until the user touches it.
- **Device-wide child lock** — Lock the touchscreen behind an optional PIN across
  panels, including the hardware buttons, rather than only the per-panel
  `unlock_code`.
- **Cleaning mode** — Ignore touch input until it is released, by a hold or a
  service, so wiping the screen does not fire a dozen actions. Separate from the
  child lock: no PIN, and it ends when the owner says so.
- **Background refresh after wake or reconnect** — A page can keep areas from
  before the display slept or the hub reconnected because the page is never
  cleared (`cls`). Confirm on hardware how often it actually matters, then
  decide whether the hub should refresh the page on wake.
- **Navigable idle-page items** — Let an item on the idle page carry a navigation
  target, so a status icon opens its detail page instead of only leaving the idle
  page.

### Hardware and sensors

- **Display as a light** — Expose the screen as a dimmable light entity, so
  automations can turn it on or off and set brightness with the same actions as
  other lights. It follows the screen's actual state; auto-dim and display-off
  keep working, and turning the light off leaves the panel dark until it is
  turned on or touched.
- **Automatic panel temperature calibration** — A reference temperature or
  climate entity in the same room slowly adjusts the panel's **Temperature
  Correction**, so the built-in sensor stops reading high from the panel's own
  heat. Start after a warm-up period, move in whole correction steps with
  hysteresis, pause when the reference is missing or stale, and keep the last
  correction across restarts.
- **Hardware button hold action** — A second action for a long press on each
  physical button, separate from the short-press relay or entity toggle and
  configurable per side.
- **Hardware button relay fallback** — When a physical button is set to toggle a
  Home Assistant entity, let it switch its built-in relay instead while Home
  Assistant is unreachable, so the button keeps working during an outage.
  Opt-in, and only on panels whose relay is safe for the connected load.

### Climate

- **Forecast precision** — Stop rounding every forecast value to an integer:
  `weather.py` sets `FORECAST_PRECISION = 0` (and `TEMP_PRECISION = 0`), so a
  pressure in inHg can only ever read `30`. A precision option or unit-aware
  decimals. **Also fixes a bug.**
- **Alternate climate entity by condition** — One binary sensor decides which
  climate entity a panel shows — underfloor heating in winter, HVAC in summer —
  instead of two panels the user switches by hand.
- **Dew-point / humidity guard** — Warn when cooling would condense; a
  display-only hint is cheap, an interlock is not.
- **Presets in spare mode slots** — When a climate entity has fewer HVAC modes
  than the six mode buttons, fill the remaining slots with up to five presets and
  highlight the active one; keep the preset picker when there are more. The
  active preset stays visible without opening the list.
- **Climate context values and actions** — Show what the unit is doing —
  `heating`, `idle (cool)` — and up to four extra values such as humidity, valve
  position and outdoor temperature, plus two configurable action buttons for the
  controls used most. The page already reloads the underlying attributes; the
  extra slots need HMI space.
- **Per-entity temperature offset** — A correction applied when a climate sensor
  reads consistently high or low.

### Content and localization

- **More display languages** — Add locales beyond the current six, starting with
  the most requested community languages. Runtime locale selection, date/time
  formatting and translated state names already exist; each new locale needs a
  translation file, font coverage and a review of the word clock.

### Updates and display models

- **Update failure actions** — The hub already fires
  `nspanel_haui.display_update_changed` and
  `nspanel_haui.firmware_update_changed` with `last_error`, so an automation
  can react today. What is left is the built-in half: an on-panel notification
  and an optional configured action, so a failed install is visible without
  writing one.
- **Rotation / flip display models** — Beyond `eu` / `us`: allow a flipped mount
  (a batch was assembled upside down) and a landscape US panel with the buttons
  on the left, instead of shipping a custom TFT per mounting variant. The
  firmware `display_model` select and the Nextion direction byte already exist;
  needs verification on hardware.
- **Byte-level TFT progress** — Report install progress in bytes instead of
  "uploading", which needs firmware-side events.

## v1.0 — Stable

The v1.0 horizon is trust: bugs closed, documentation complete, the Marketplace
listing and a frozen REST API. The wishlist item behind it:

- **REST API surface before v1.0** — Version prefix and consistent shapes across
  the `api/` views, so the editor and third-party callers have a contract.

## Not user-visible — Tooling and tests

These decide how quickly everything else can move; they are scheduled as
capacity allows, not tied to a horizon.

- **Devcontainer / quick-start** — A reproducible contributor environment so
  "clone and run the tests" does not need a paragraph of setup.
- **ESPHome component tests** — Tests for the sensor, button and cover entities
  the firmware exposes, which today are only exercised by a compile.
- **End-to-end update pipeline test** — Unit and endpoint tests exist; an
  integration test from "release published" to "device updated" is still open.
- **Listener and render-budget regression tests** — Assert that a panel registers
  one listener per visible item, that opening it repeatedly does not grow that
  count, and that the densest page stays within a bounded command batch — the
  three ways a busy event stream could make a panel feel slow.

### Firmware and dependencies

- **Remove the vendored Nextion patch** — ESPHome 2026.11.0 (released
  2026-11-18) carries two of the fixes this patch used to add: the
  numeric-response delivery
  ([esphome#17744](https://github.com/esphome/esphome/pull/17744)) and the TFT
  upload buffer option
  ([esphome#21435](https://github.com/esphome/esphome/pull/21435)), both verified
  in the tag's own `nextion` sources. Two local changes are left: the TFT upload
  retry (`upload_first_chunk_sent_` is never reset upstream) and the per-upload
  detail 0.5.4 and 0.5.7 report — the named `tft_upload_error_` reasons and the
  `tft_upload_display_fault()` flag that decides whether a failure is worth
  retrying at 115200 bps. The flag is worth filing upstream with the retry, since
  a lower rate is a caller's decision; the error strings are ours either way.
  Left open by the v0.5 cycle, since no released ESPHome carries the retry yet;
  after one does: bump `min_version` and `requirements-esphome.txt` together,
  delete the directory and its `external_components` blocks and re-validate the
  firmware config and a compile. *Area: Dependencies.*

### Release tooling

Open items from the release-process review (runbook and known risks in
[docs/develop/release.md](docs/develop/release.md)):

- **HMI as a build artifact (nxwright)** — A spike extracted `nextion/nspanel_haui.HMI` into text source
  with nxwright 0.2.0, rebuilt the project and compiled a TFT using the shipped TFT as the firmware
  reference. The 30,432-line TFT listing and the decompiled sources matched; only page lock flags and a
  four-byte picture encoding detail differed. Next: choose the source layout, then verify/build TFTs in CI
  and stop committing the compiled display binaries.
- **Portrait as a build-time rotation** — Derive the portrait HMI from the
  landscape one instead of committing a second HMI and keeping both in sync by
  hand.

## Open decisions

Only the questions that shape scope remain here. The shared credentials in the
universal image are tracked with the release risks in
[Release process](docs/develop/release.md#guardrails-and-known-gaps).

- **Multiple hub entries** — One hub entry discovers and manages every eligible
  NSPanel, with settings scoped per device. No separate multi-hub use case is
  established yet, so the single-instance flow stands until one appears.

## Already possible — do not re-request

These are covered today; the linked docs show how.

- Per-item **name / icon / value / state / colour** overrides, including one value
  per state and template colours —
  [Item configuration](docs/user/editor/items.md).
- **Paged lists** for pickers with more than eight options (light effects, fan
  presets, `select`).
- **Climate presets, fan mode, swing mode**, and hvac-mode buttons trimmed to what
  the entity actually supports —
  [Climate panel](docs/user/panels/panel_climate.md).
- **Light effects** and per-light `rgb_color` colouring.
- **Media panel** with multi-room grouping, Sonos favourites, shuffle and repeat,
  and a source picker.
- **Detail popups** for alarm, climate, cover, light, media player, select,
  timer and vacuum, each overridable per item with `popup_key`.
- **Notification queue** with `icon_color`, `sound`, `timeout`, `force_show`,
  persistent looping, and a queue view in the editor —
  [Notifications](docs/user/actions.md).
- **Per-message notification text size** — `text_size` on the action, the notify
  entities, the popup panel and the ESPHome action, as `auto` (the largest font
  that fits) or a font id — [Notifications](docs/user/actions.md).
- **Quiet hours, and a panel that stays dark** — A schedule entry with `sound`
  off silences notifications inside its window while they still queue, and its
  `display_off`/`brightness` keep the panel dark; nothing is dropped, delayed or
  hidden — [Device settings](docs/user/editor/device.md).
- **Notification readability** — `text_size` sets the size per message, a
  per-panel theme sets the contrast (the theme library's light and dark
  palettes), and `persistent: true` keeps a message on screen until it is
  dismissed — [Notifications](docs/user/actions.md).
- **Themes** with light/dark icon palettes, a shared library and per-panel themes.
- **Schedules**, **gestures**, the **idle page** with carousel, **snapshot
  restore** and **auto-navigate home** — [Device settings](docs/user/editor/device.md).
- **A fast display link, without a second TFT** — every released TFT boots the
  Nextion at 921600 bps and the firmware starts its UART there, so there is no
  faster build to install and no slow one to replace: one file per display model
  carries the rate, and a fallback to 115200 bps is the same file installed
  again, not a different one.
- **Local relay toggling without Home Assistant**, encrypted OTA, TFT retry on
  upload, per-device update channels and one-at-a-time fleet rollouts.
- **Custom RTTTL melodies** through the firmware's `play_rtttl` action.
- **One place for the versions** — the editor's device row shows the firmware
  and TFT versions side by side with a **Mismatch** badge, and the diagnostics
  card lists integration, firmware and TFT versions (plus the required TFT)
  and puts them in **Copy report**.
- **A TFT install only counts as done when the panel confirms it** — an
  unconfirmed upload is marked failed and is not reinstalled in a loop,
  instead of reporting the file the panel never took.
- **A version mismatch is reported, not enforced** — the editor flags it for the
  device; only an incompatible firmware *build variant* is refused, with the
  reason and the one manual flash it needs.
- **A diagnostics view of the device** — the editor's diagnostics card shows
  uptime, Wi-Fi signal, connection state and drops, update state with its error,
  recent log warnings and a **Copy report**; Home Assistant's *Download
  diagnostics* gives the same snapshot as JSON.
- **Forecast highs above lows** — the daily forecast pairs the day's temperature
  with its `templow` underneath, and the icon follows the condition (including
  `clear-night`) rather than a daytime default.
- The **editor**: live preview, hub-rendered panel cards, REST API, per-device
  YAML export, backups.

## Considered and declined

Kept for the record, so the same idea is not re-evaluated every few months.

- **Panels owning their own thermostat / PID climate add-ons** — The hub runs
  inside Home Assistant. Climate logic belongs to a climate integration;
  duplicating it on the panel forks the source of truth.
- **ESPectre CSI motion detection, BLE tracker, Bluetooth proxy** — Firmware-only
  features with no hub-side surface; better served by a dedicated ESPHome
  component.
- **Chips or a global status-icon bar as a general concept** — Panels are
  configured per entity and per item; a chip abstraction would be a second way to
  say the same thing, and a global bar would take header space from per-panel
  actions.
- **A Blueprint / automation-driven renderer** — The hub renders from Home
  Assistant state directly; the template layer in between was the alternative
  architecture and was dropped for exactly this reason.
- **Raw canvas / arbitrary Nextion commands** — A blank page driven by Home
  Assistant automations with raw drawing commands would bypass the page API, the
  command replay contract and validation. The text/notes panel covers the
  legitimate use case.
- **Custom PCB to replace the Nextion** — Out of scope for this repository,
  though it is the ceiling behind most display limitations.
- **Automatic dithering / fake transparency** — An HMI technique worth
  remembering if translucent tiles are ever wanted; not worth it on its own.
- **Separate high-speed and normal-speed TFTs** — Shipping a 921600 bps build
  next to a 115200 one, as the v0.5 plan once considered. Dropped: the rate is
  set inside the TFT, so one file per display model serves both, the firmware
  starts its UART at 921600 and scans down only for an older or stock TFT, and a
  display that cannot hold a transfer gets the same install once more at
  115200 bps. A second artifact would double every display build and every
  install for a link the single file already sets, and leave a panel on the
  "slow" one with nothing it can do about it.
- **Camera or doorbell video on the panel** — The Nextion draws static pictures
  only; there is no video path, and refreshing frames over the serial link would
  be unusable.
- **Emoji and full CJK font coverage** — The charset is curated on purpose —
  Latin, Greek, Cyrillic, Hebrew, Arabic, Thai and a hand-picked Chinese set — and
  compiled into every TFT; full ideograph coverage or emoji would mean
  regenerating the fonts for little gain.
- **Configuration values that follow the clock or another entity** — One setting
  whose value depends on the hour, the day or a sensor, such as a brightness by
  time of day. Schedules, automations and template sensors already express this in
  Home Assistant, and a second condition language on the panel would only be a
  worse copy of them. Closed as won't-fix in issue
  [#8](https://github.com/happydasch/nspanel_haui/issues/8).

---

*Living document — add candidates, argue for one, or delete an entry that has
shipped or lost its reason to exist.*
