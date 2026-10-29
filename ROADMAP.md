# Roadmap

Development trajectory from **v0.3.2** toward **v1.0**. **v0.4.0 and v0.4.1
shipped on 2026-10-26 and v0.4.2 on 2026-10-27**, each tagged from a green
`master` commit and published by the release workflow.

**v0.4.3 was released on 2026-10-28.** Its landscape and portrait TFTs are
published; the remaining 0.4.x hardware acceptance and OTA risk checks are
tracked as the **v0.4.4 plan** below.

This file tracks **open work only** — goals and gates, not task lists. Shipped
changes are summarised in [CHANGELOG.md](CHANGELOG.md); the release runbook and
its known risks live in [docs/release.md](docs/release.md); day-to-day tasks
belong in the issue tracker.

**The 0.4.x install gate comes first.** The binary and TFT install must work
completely and the base and core functions must be proven on real hardware.
Nothing in v0.5 or v0.6 starts before that: a broken install or a core regression
blocks the next minor release, and remaining gate work is planned for `0.4.4`.
After the gate closes, **v0.5** adds multiple TFTs for normal- and high-speed
updates, stable and controllable manual/auto updates in the frontend, and a
Device Manager overhaul. **v0.6** adds Display Repair Mode — a simple TFT used to
repair an existing display.

---

## v0.4.x — finishing the binary and TFT install (current focus)

One job: make the install complete and working. New features wait.

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

## v0.4.4 — hardware acceptance and OTA risk closure (planned)

**Status: planned, unreleased.** The v0.4.3 code and TFTs are prepared; the
following items remain before the 0.4.x install gate can close:

- Complete the EU and US/portrait device passlist above, including universal
  image onboarding, TFT auto-update, notifications, sleep/wakeup, touch, core
  stability and editor add/remove/configuration flows.
- Canary-test unattended firmware OTA end to end: install, reboot, verify the
  matching TFT follows, and confirm the buzzer is silent during OTA and reboot.
- Investigate the old-bootloader OTA rollback warning; rollback capability is
  not confirmed and unattended updates should not be treated as rollback-safe.
- Issue #50 (notification enhancements) stays documentation-only: notification
  behavior is tracked and verified on both display models during this pass; no
  font-size or other notification implementation is planned.
- Internal temperature on clock/weather panels — make the entity-registry
  lookup work in production (lazy entity-registry import) and add an optional
  per-page **Inside temperature sensor** picker (default: NSPanel internal
  sensor).

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
    for HAUI. *Implemented on dev (0.4.4):* the integration owns the entity and
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
replacing the broader v0.4.4 passlist.

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
form validation feedback, preview renderer unification and dead-code pruning,
keyboard-navigable modals, and an accessibility pass (labels, ARIA, contrast).

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
- **Panel editors** — split-view preview built on the existing preview renderers,
  "create from template", inline rename/duplicate/reorder and field-level
  validation, replacing the generic toast with per-field feedback.

**Phasing:** API and data foundation with no UI change, then the general frontend
rework at behaviour parity (editor-polish items included), then Device Manager and
device settings, then panel editors, then the notification UX, then polish and
hardening.

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

- Release notes extracted from the `CHANGELOG.md` section instead of static text
  in `release.yml` (0.5).
- Pre-flight gates in `tests.yml`/`release.yml` so a tag cannot ship untested
  code — now runs on every push/PR (0.5).
- Scripted HMI patching for release-only edits — `tftVersion` scripting landed
  with the version-bump tooling (0.4.x); Send Component ID and other in-place
  edits still need the Editor or an extended patch spec (0.5+).
- Portrait layout as a build-time rotation instead of a second committed HMI
  (0.5+).
- Git LFS or release-only storage for the TFT binaries (0.5+).

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

### Hub management

- **Hub settings / options flow** — the hub has no settings today (its name is
  hard-coded and no options flow exists); allow renaming and updating settings
  after creation.
- **Multi-hub support** — only one hub is allowed today
  (`single_instance_allowed`); allow several entries with their own devices and
  settings.

### Platform maturity

- Developer devcontainer / quick-start script for contributors.
- REST API surface stabilised before v1.0 (version prefix, consistent shapes).
- ESPHome component tests for sensor/button/cover entities.

---

## v1.0 — Stable release

- All `bug`-labelled issues closed.
- `CHANGELOG.md` covering every release from 0.1.0.
- HACS default integration status (no longer "custom repository").
- Published on PyPI / HA add-on registry, if applicable.
- REST API docs published alongside user docs.
- Final branding pass: icons, screenshots, README hero image.

---

## Deferred / needs decision

- **Trim the HACS download** (`export-ignore` the Nextion binaries) — HACS users
  would lose the HMI sources.
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
