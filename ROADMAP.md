# Roadmap

Development trajectory from **v0.3.2** toward **v1.0**. **v0.4.0 and v0.4.1
shipped on 2026-10-26, v0.4.2 on 2026-10-27, v0.4.3 on 2026-10-28 and
v0.4.4 on 2026-11-02**, each tagged from a green `master` commit and published
by the release workflow. v0.4.4 is a notification-timeout hotfix; its TFT
display files are unchanged from 0.4.3.

The remaining 0.4.x hardware acceptance and OTA risk checks are tracked as the
**v0.4.5 plan** below. The 0.4.5 feature set — including the live panel preview
contributed in [#85](https://github.com/happydasch/nspanel_haui/pull/85) and
[#86](https://github.com/happydasch/nspanel_haui/pull/86) — is already on `dev`;
the release waits on the hardware passlist.

This file tracks **open work only** — goals and gates, not task lists. Shipped
changes are summarised in [CHANGELOG.md](CHANGELOG.md); the release runbook and
its known risks live in [docs/release.md](docs/release.md); day-to-day tasks
belong in the issue tracker.

**The 0.4.x install gate comes first.** The binary and TFT install must work
completely and the base and core functions must be proven on real hardware.
Nothing in v0.5 or v0.6 starts before that: a broken install or a core regression
blocks the next minor release, and remaining gate work is planned for `0.4.5`.
After the gate closes, **v0.5** adds multiple TFTs for normal- and high-speed
updates, stable and controllable manual/auto updates in the frontend, and a
Device Manager overhaul. **v0.6** adds Display Repair Mode, an inspection and
cleanup of the Nextion scripts and Home Assistant hub settings; multi-hub support
remains subject to a needs decision.

---

## v0.4.x — finishing the binary and TFT install (current focus)

Primary job: close the install gate. Beyond the focused v0.4.x items below and
the live preview contributed for 0.4.5, broader work waits.

- **Universal binary** — flashes and runs; TFT installs and auto-updates
  end-to-end on both display models; base and core functions work on real EU and
  US panels.
- **Firmware auto-update** — implemented on dev (0.4.2): release manifests, the
  `HAUI Firmware` update entity and the TFT-after-reboot deferral are shipped
  (Changelog); the hardware confirmation of the full release flow remains on the
  passlist.
- **Sleep / idle behaviour** — touch wakes the panel, the `wakeup` service works
  reliably, and state survives sleep/wake cycles. *Known gap: touch-to-wake and
  idle-panel transitions are not reliable yet.*
- **Day/Night Profiles** — focused v0.4.x support for fixed-clock and
  sunrise/sunset Day/Night profiles covering display brightness, dimming,
  automatic-page/idle target and display-off behavior. This replaces common
  time-of-day brightness/timeout automations; it does not complete or change the
  broader v0.5 Device settings API/tab described below.
- **Notification behaviour** — HA persistence and `force_show`, ESPHome
  `send_notification` with `persistent`/`text_size`, long-message paging and
  severity default icons confirmed on hardware.
- **Recent fixes confirmed on hardware** — issue #62's TFT-upload buzzer fix,
  the #63 reinstall fix, and the #64 portrait weather alignment fix were
  confirmed by the reporter on a US/portrait panel running 0.4.2. The broader
  two-display-model passlist below is still outstanding.
- **Upgrade paths** — the five renamed 0.3.x device-setting keys migrate
  automatically; saved panels are not migrated and must be re-entered.
- **Release hygiene** — done on dev: `scripts/bump_version.py` /
  `scripts/bump_tft_version.py` script the version bump across manifest,
  `pyproject.toml`, `version.yaml` and both HMIs, and CI validates version
  consistency, translations and Nextion assets on every push/PR while the
  release workflow rejects a tag whose version disagrees with `manifest.json`.
  The pinned toolchain (Home Assistant `2026.10.4`, ESPHome `2026.10.0`)
  resolves cleanly in separate jobs; they cannot share an environment because of
  conflicting `cryptography` pins.

**Device passlist** — confirm on one EU and one US/portrait panel:

- **TFT auto-update** — an older TFT installs 0.4.0 about a minute after
  connecting, and About/Device Manager then show 0.4.0 (reconnect first if it
  looks stale). With `auto_install` off the "Outdated TFT-Version" popup appears.
  Tapping the time area advances the card.
- **Universal `nspanel_haui.bin`** — flash a fresh panel, join the device-named
  AP, enter Wi-Fi and add the device with the documented API key. Settings sync
  reaches the firmware, TFT auto-updates and the panel renders. Repeat on a
  second panel and confirm both get distinct names/APs from the same `.bin`.
- **Notifications** — popup, `force_show`, list, dismiss, persistent and critical
  sounds, quiet hours, `notify.*` entities and font sizes.
- **Wakeup / sleep** — wake on touch and via the service; sleep panels/carousel
  and auto-dim as configured; state survives sleep/wake cycles.
- **Touch and general functionality** — every widget responds and navigates;
  gestures work on both layouts; button rows, header actions and popups behave;
  no dead zones.
- **Core stability** — one worker per device; touches, page changes and the
  heartbeat stay responsive; `hub_availability` resets on the last disconnect;
  row/weather/QR values visible; a popup pauses auto-dim on a device named with
  capitals or `-`.
- **Editor** — add, remove, enable and disable a device, plus YAML import.

**Acceptance:** every passlist row green on both display models, both TFT assets
working from the published release, and the portrait device auto-updating
end-to-end. A failing row ships as a `0.4.x` patch; **v0.5 does not start until
this gate is green.**

### 0.4.3 — update-trigger fixes

The issues collected while validating 0.4.2 led to these changes on `dev`:

- **Automatic checks and configuration** — per-device update settings are
  merged over integration defaults; enabled checks run on connect/hourly. Firmware
  availability is now refreshed and handled independently of TFT release state.
- **Firmware install failures** — checked service dispatch now distinguishes an
  accepted `update.install` call from a failed Home Assistant service call, and
  the install attempt is available from the Device Manager when firmware is
  offered.
- **Manifest fetching** — ESPHome HTTP RX/TX buffers are increased for GitHub
  redirect headers and signed asset request targets.
- **Frontend status and retry** — the editor shows firmware availability, can
  refresh update info, and can trigger a firmware install; TFT failures continue
  to surface as explicit errors rather than silent success.
- **Release API usage** — release metadata is cached for one hour across the
  hub's devices; manual checks intentionally bypass the cache.
- **ESPHome diagnostic defaults** — uptime, heap, loop-time and reset-reason
  diagnostics are development-only; raw ADC and resistance sensors used by the
  temperature calculation remain disabled by default.

---

## v0.4.4 — notification `timeout` hotfix (shipped 2026-11-02)

**Status: shipped.** Issue #78 is fixed: `nspanel_haui.send_notification`
accepts the optional `timeout`, and timed notifications leave the queue when
their timeout expires. The TFT display files remain at 0.4.3, so panels keep
their installed TFT.

---

## v0.4.5 — hardware acceptance and OTA risk closure (in progress)

**Status: in progress.** The 0.4.5 feature set is on `dev` — see the
[0.4.5 changelog](CHANGELOG.md#045--unreleased) for the full list. It includes
the live panel preview in the editor ([#85](https://github.com/happydasch/nspanel_haui/pull/85),
[#86](https://github.com/happydasch/nspanel_haui/pull/86)) with its **Show
entities** tooltip, relay-switching hardware buttons, idle highlight and
**Reset sandbox**, plus **Panel cards drawn by the hub** (every card replays the
hub's own render), **Every popup can be edited**, **Long press to go back**,
Day/Night Profiles, the inside-temperature sensor picker, notification line
breaks and the notification text/icon/paging fixes, the
firmware-to-integration update move, alarm action-button options and versioned
dev releases.

The following items remain before the 0.4.x install gate can close:

- Complete the EU and US/portrait device passlist above, including universal
  image onboarding, TFT auto-update, notifications, sleep/wakeup, touch, core
  stability and editor add/remove/configuration flows.
- Canary-test unattended firmware OTA end to end: install, reboot, verify the
  matching TFT follows, and confirm the buzzer is silent during OTA and reboot.
- **TFT assets in releases and git** — both display TFTs
  (`nextion/nspanel_haui.tft`, `nextion/nspanel_haui_portrait.tft`) are
  committed to git and attached to every GitHub release, so the update
  controller and manual installs can fetch them. Confirm both assets are
  present on the published release and keep them in git through 0.5.
- Investigate the old-bootloader OTA rollback warning; rollback capability is
  not confirmed and unattended updates should not be treated as rollback-safe.
- **Encrypted native OTA** (issue #81) — implemented on `dev`: native OTA is
  encrypted with `api_encryption_key` instead of a password, and the migration
  is documented in [ESPHome → Encrypted native OTA](docs/esphome.md#encrypted-native-ota).
  Remaining: one wireless ESPHome install onto a panel that runs a 0.4
  password build, to confirm on hardware that the encrypted upload needs no
  migration step.
- Issue #50 (notification enhancements) stays documentation-only: notification
  behavior is tracked and verified on both display models during this pass; no
  font-size or other notification implementation is planned.

**Update-flow and notification polish (reported on hardware during this pass):**

- Notifications — full text instead of fragmented pages: **done on dev** (text
  is wrapped with the display fonts' real glyph widths and the automatic size
  fits the message on one page).
- Notifications — icon-less notifications use the whole notification space:
  **done on dev** (no severity default icon; the message fills the full-width
  box).
- Update — notify only once per available update and do not pester/overload
  the display with repeated update notifications. *Still open.*

- **ESPHome vs. HAUI sensor ownership review** — inventory the ESPHome sensor
  entities and HAUI sensor platform, then make the boundary explicit:
  - ESPHome owns device-side measurements and hardware/transport state
    (for example, internal temperature, Wi-Fi signal, touch/button state and
    display brightness). Keep request/response values, page-number updates and
    interaction tracking that only support the protocol internal; expose only
    stable device telemetry or diagnostics.
  - HAUI owns Home Assistant concepts derived from hub behavior. Its **Current
    page** sensor is the user-facing page/panel state, including panel type and
    title; the internal ESPHome `Page` template is its event source, not a
    second public page sensor. The clock/weather temperature picker selects an
    existing sensor entity and does not create another temperature sensor.
  - Move the **HAUI Firmware** update entity and its release-manifest check and
    install orchestration into the `nspanel_haui` integration. ESPHome should
    expose only its stock ESPHome update entity, not a second firmware updater
    for HAUI. *Implemented on dev (0.4.5):* the integration owns the entity and
    reads the manifest (per-device `firmware_manifest_url`, so test panels can
    follow local test releases); the firmware drops its `update:` block.
    Verify firmware OTA and TFT-update sequencing on hardware after the move.
  - Check for genuine duplicates in exposed state and availability (including
    ESPHome **Client Status** versus HAUI connection availability). Consolidate
    only signals with the same meaning and lifecycle; retain distinct device
    telemetry and HAUI-derived state. Document the chosen owner and verify
    entity visibility, names and update/unavailable behavior.

Issues #62/#63/#64 remain open on GitHub, but the reporter confirmed their
specific TFT-upload buzzer, post-reboot TFT-version and portrait weather fixes on
US/portrait hardware with 0.4.2. Do not treat those specific observations as
replacing the broader v0.4.5 passlist.

---

## v0.4.6 — dim/idle display wake flash

**Status: fixed in the working tree; release pending.**

- **Portrait HMI page fixes** — use the shared panel preview added in 0.4.5 to
  reproduce and debug portrait-only page rendering issues, then fix the portrait
  HMI so every page renders with the intended layout, backgrounds and colors.
  Keep the landscape/portrait component and geometry parity checks green, and
  verify the fixes by reviewing the affected pages in the simulator.
- **Periodic full-brightness flash while the display is dimmed or on the
  idle screen** — Fixed. ESPHome now stores one rollover-safe `millis()`
  timestamp and computes elapsed inactivity once for the display and page
  timers. Timeout/brightness setting changes and hub connection transitions do
  not change that timestamp; only touch, configured button presses, or explicit
  wake/reset actions do. This removes the reconnect reset that restarted the
  full-brightness ramp.

---

## v0.5 — Multiple TFTs, update control & Device Manager overhaul

Three pillars plus planned frontend, notification and device-settings work, after
the 0.4.x gate closes.

### Multiple TFTs

Keep the existing 115200 TFTs as the known-good **normal-speed** default — asset
names unchanged, so flashed panels keep auto-updating — and add a **high-speed**
variant at 921600 baud per display model. That is an 8× baud increase (~10× in
practice), turning an ~11 MB TFT update from ~16 min into ~2 min.

- Speed is chosen per device: the update controller downloads the matching TFT
  asset and the firmware configures the matching UART baud.
- A boot baud scan recovers mismatches without user action — it power-cycles
  `screen_power`, probes each Nextion-supported rate over `haui_uart`, and
  switches the UART to the detected rate; a boot check waits `BAUD_RATE_TIMEOUT`
  for `haui_disp->is_detected()` before scanning.
- The high-speed TFTs are compiled in the Nextion Editor and keep the
  landscape/portrait parity gates green; pacing stays at `max_queue_size: 800` /
  `max_commands_per_loop: 50`, with `command_spacing` decided from observed
  `on_buffer_overflow` events.
- Document the speed choice, update-time expectations, baud-scan recovery and
  upgrade caveats.

**Acceptance:** both speed variants install and run on both display models and
the universal image; a mismatched panel recovers without user action; the
high-speed variant is ~8–10× faster; flashed panels keep auto-updating on the
unchanged normal-speed assets; no UART buffer overflows under the update burst.

### Stable, controllable updates in the frontend

- **Manual updates** reach the device reliably, report a clear state
  (`checking`, `installing`, `done`, `error`), and never reboot-loop or reinstall
  an already-current TFT.
- **Automatic updates** work per device and globally for TFT and firmware, handle
  unknown versions without false "outdated" notices, never repeat an install
  after a reboot, and expose a visible retry policy that stops after failure.
- **Control** — explicit per-device and bulk update actions, clear progress and
  status, and a way to defer or cancel an update.
- **Status surface** — one place in the editor showing firmware and TFT versions
  plus update state per device.

### Device Manager overhaul

Consolidate the dialog after the v0.4 additions (layout, per-device actions,
stale states), support multi-device operations such as bulk firmware/TFT updates
and moving panels across devices (reordering works today), and show clear
per-device version and action state in the list.

### Remaining editor polish

Folded into the general frontend rework below, after the update work: panel-list
improvements (drag-reorder, inline rename, duplicate — reorder works through the
row menu today), edit-panel sidebar cleanup, a "create from template" flow, inline
form validation feedback, keyboard-navigable modals, and an accessibility pass
(labels, ARIA, contrast). The preview renderers were unified in 0.4.5: every card
is the hub's own render.

### Component cleanup & colour overrides

`color_overrides` reach only the colours the hub sends as commands: a widget the
hub never colours keeps the HMI's compiled palette value on the device. Since
0.4.5 the editor's panel cards replay the hub's own render, so they show exactly
that — recolouring layout colours in the browser would show a panel the device
never draws. Fix it where it happens, folded into the general frontend rework:

- Audit both HMIs for widgets that take a palette colour only from the compiled
  layout (page backgrounds, header and label widgets) and have the hub send
  their colour when it renders the page; cards follow without frontend work.
- Replace the simulator frame's hardcoded `#000` card background
  (`.pg-sim` in `frontend/previews/simulator-frame.js`) with the device theme.

### Frontend rework, notifications & device settings (planned)

Planned beyond the three pillars above; no v0.5 code starts before the 0.4.x
gate closes. Each phase ships on its own.

- **General frontend rework** — the panel and device requirements are known now,
  so rebuild the editor as one coherent app instead of layering patches on the
  original screen set: a shell over one observable store and view modules,
  dialogs and forms on the vendored Lit components, a responsive layout with
  keyboard-navigable modals, and an editor/preview split view. This supersedes
  the incremental patchwork the editor-polish items above describe, which land
  here instead. The static, unauthenticated, no-build-step serving contract
  stays — that is how `editor_panel.py` serves `frontend/` — so the rework is
  structural, not a framework or bundler swap.
- **Notifications** — add grouping and priority ordering to the controller plus a
  read-only queue/history API and a Notification Center in the editor. The
  service, `notify.*` and ESPHome entry points keep working, and the "never
  auto-dismiss" and critical force-show rules stay unchanged.
- **Device settings** — expose the existing per-device settings (speed,
  orientation, brightness, idle behaviour, notification defaults, update policy)
  through scoped read/update endpoints and a settings tab, stored per device and
  defaulted on load. The Device Manager section above gains that tab; its bulk
  actions and per-device state stay as planned there.
- **Device color schemes and first render** — add a device-level color scheme
  selector, with palettes predefined in the TFT to reduce the color commands
  needed on the first render. If the TFT cannot apply a scheme before the page is
  shown, ensure panel startup paints the complete page with the selected colors
  before it becomes visible. The first render must not flash the default palette
  or show a partially themed page; editor cards must continue to match the device
  render.
- **Panel editors** — split-view preview built on the hub's card render
  (`nspanel_haui/virtual_panel/render`, which already draws unsaved edits),
  "create from template", inline rename/duplicate/reorder and field-level
  validation, replacing the generic toast with per-field feedback.

**Phasing:** API and data foundation with no UI change, then the general frontend
rework at behaviour parity (editor-polish items included), then Device Manager and
device settings, then panel editors, then the notification UX, then polish and
hardening.

### Live preview: keep the Sandbox/Live toggle in sync

Since 0.4.5 every open live preview of a device and its panel cards run on one
virtual app (`VirtualPanelHost` in `virtual_panel.py`), so Sandbox/Live mode
belongs to the device, not to a preview. Switching the mode in one browser tab —
or opening a preview, which applies that tab's mode — changes it for every open
preview of the device, but the other tabs' toggles keep showing their old mode: a
tab can read **Sandbox** while its taps already call Home Assistant.

- Broadcast the mode to every viewer when it changes (a `{"type": "mode",
  "live": …}` message from `VirtualPanelHost.set_live`, also sent right after
  `started`), and have `virtual-panel-session.js` and the live-preview dialog
  update the toggle from it.
- Opening a preview joins the device's current mode instead of imposing the
  tab's default, so a second tab never switches a live preview back to sandbox.
- Bump the WebSocket protocol version; older open editors simply don't receive
  the new message.

**Acceptance:** with two previews of one device open, switching the mode in
either updates both toggles at once; a newly opened preview shows the device's
current mode; no tab ever shows a mode the app is not in.

### Deferred follow-ups

- **Shared text-style abstraction for panel options** (Discussion #57 follow-up) —
  the configurable alarm keypad styling shipped in v0.4.0 as the `keypad_font`,
  `keypad_bg_color` and `keypad_text_color` options with a one-off
  `_style_keypad()` helper. Generalising that into a shared text-style option
  trio plus apply helper for every page type is deferred: start only after the
  0.4.x acceptance gate closes and the compatibility cleanup lands — the vendored
  `esphome/nextion_patch/` and its `external_components` blocks removed, and
  `min_version`/`requirements-esphome.txt` bumped once a released ESPHome carries
  esphome#17744 and #21435 (expected 2026.11.0).

---

## Release tooling

Open items from the release-process review (runbook and known risks in
[docs/release.md](docs/release.md)):

- Pre-flight gates in `tests.yml`/`release.yml` so a tag cannot ship untested
  code — now runs on every push/PR (0.5).
- Scripted HMI patching for release-only edits — `tftVersion` scripting landed
  with the version-bump tooling (0.4.x); Send Component ID and other in-place
  edits still need the Editor or an extended patch spec (0.5+).
- Portrait layout as a build-time rotation instead of a second committed HMI
  (0.5+).
- TFT binaries stay committed to git and attached to releases (addressed in
  0.4.x); Git LFS or release-only storage is deferred until repo/zip size
  becomes a problem.

---

## v0.6 — Display repair mode, features & integrations

### Display repair mode

A simple, self-contained TFT whose only job is to repair an existing display.
When the normal TFT is broken, half-installed, stuck on the boot screen or
running the wrong baud rate, the repair TFT proves the panel is alive and accepts
a fresh normal TFT install — no Nextion Editor session required.

- A minimal repair TFT per display model, small enough to install even when the
  normal TFT is corrupt.
- A **Repair display** action in the editor that installs the repair TFT and then
  reinstalls the normal TFT for the device's model and speed — reachable from the
  Device Manager even in a failed update state.
- A documented recovery entry point (serial/OTA, boot handshake) and a verified
  return path to the normal TFT on real hardware.

**Acceptance:** a panel with a broken or mismatched TFT is restored to a working
normal TFT from the editor without a Nextion Editor session, on both display
models and both speed variants.

### Nextion script inspection & cleanup

The HMI event code (`Program.s`, page `Preinitialize`/`Postinitialize`, touch
press/release events, timers) has grown page by page and is not inventoried.
Before more behaviour moves onto the display, find out what the Nextion side can
do and clean up what it does today.

- **Inventory** — dump the event code of both HMIs (Nextion2Text) and record what
  each script does, which hub command or ESPHome event it pairs with, and where
  landscape and portrait differ.
- **Possibilities** — document the Nextion instruction set and limits that matter
  here (timers, system variables, `sendme`/`printh`, local state, sleep/wake
  hooks, script length and RAM) and decide which behaviour is better on the
  display than on the hub — for example instant touch feedback or page
  preparation that removes first-render commands.
- **Cleanup** — remove dead or duplicated scripts and automations that the hub or
  firmware already drives, align landscape and portrait, and keep the "logic in
  the Hub App" rule from [Nextion Editor](docs/nextion-editor.md#hard-rules) except
  where the inventory shows a reason to move it.

**Acceptance:** a documented inventory of every HMI script on both display models,
no unused or duplicated event code left, parity gates green, and every page
behaving unchanged on hardware after the cleanup.

### Hub management

- **Hub settings in Home Assistant** — add an integration options flow so the
  hub can be renamed and genuinely hub-scoped settings can be changed after
  setup. Keep per-device settings in the editor.

### Platform maturity

- Developer devcontainer / quick-start script for contributors.
- REST API surface stabilised before v1.0 (version prefix, consistent shapes).
- ESPHome component tests for sensor/button/cover entities.

---

## v1.0 — Stable release

- All `bug`-labelled issues closed.
- `CHANGELOG.md` covering every release from 0.1.0.
- Listed in the Home Assistant Marketplace catalog (a PR to `hacs/default`, the
  list the Marketplace reads), so users no longer add a custom repository or
  connect GitHub.
- Published on PyPI / HA add-on registry, if applicable.
- REST API docs published alongside user docs.
- Final branding pass: icons, screenshots, README hero image.

---

## Deferred / needs decision

- **Need for multiple hub entries** — the current model discovers and manages
  all eligible NSPanels under one hub, with settings scoped per device. No
  separate multi-hub use case is established yet, so retain the single-instance
  flow unless a concrete need for independent fleets/configuration is identified.
- **Trim the Marketplace download** (`export-ignore` the Nextion binaries) —
  Marketplace users would lose the HMI sources.
- **Runtime credential adoption for the universal image** — post-0.4; baked
  credentials stay shared for now.
- **`cls` background refresh** after sleep/wake or reconnect — needs hardware
  confirmation of how often it matters.
- **Byte-level TFT update progress** — needs firmware-side events.
- **Full update-pipeline integration test** — unit and endpoint tests exist; the
  end-to-end test is still open.

---

## Prior releases

- **0.1.x** — first versions as an AppDaemon app; ESPHome firmware with auto
  updates and the first panel set.
- **0.2.x** — configuration and entity handling; ClockTwo screensaver,
  configurable wakeup and notification sounds.
- **0.3.x** — native Home Assistant integration replaces AppDaemon and MQTT; the
  panel editor moves inside Home Assistant.
- **0.4.0** — first stable release with breaking changes: universal prebuilt
  firmware, US/portrait model, gesture navigation, device discovery, Panel
  Doctor, and per-device TFT install in the editor.
- **0.4.1** — Nextion serial RX buffer overflow fixes and Clock Two font/background
  fixes.

---

*Living document — priorities shift as the project grows. Open an issue or start
a discussion to propose changes; shipped work moves to [CHANGELOG.md](CHANGELOG.md).*
