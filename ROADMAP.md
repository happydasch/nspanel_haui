# Roadmap

Development trajectory from **v0.3.2** toward **v1.0**. **v0.4.0 and v0.4.1
shipped on 2026-10-26, v0.4.2 on 2026-10-27, v0.4.3 on 2026-10-28, v0.4.4 on
2026-11-02 and v0.4.5 on 2026-11-09**, each tagged from a green `master` commit
and published by the release workflow.

The 0.4.x hardware acceptance and OTA risk checks are closed; the remaining gate
item is notification verification on real hardware, tracked as the **v0.4.6
plan** below. The 0.4.5 feature set — including the live panel preview
contributed in [#85](https://github.com/happydasch/nspanel_haui/pull/85) and
[#86](https://github.com/happydasch/nspanel_haui/pull/86) — shipped in that
release. A defect found by the remaining notification pass ships as a 0.4.6
patch.

This file tracks **open work only** — goals and gates, not task lists. Shipped
changes are summarised in [CHANGELOG.md](CHANGELOG.md); the release runbook and
its known risks live in [docs/release.md](docs/release.md); day-to-day tasks
belong in the issue tracker.

**The 0.4.x install gate comes first.** The binary and TFT install, firmware OTA
and the base and core functions are confirmed on real EU and US/portrait
hardware; only notification behaviour remains. Nothing in v0.5 or v0.6 starts
before that row is green. After the gate closes, **v0.5** adds
multiple TFTs for normal- and high-speed updates, stable and controllable
manual/auto updates in the frontend, and a Device Manager overhaul. **v0.6** adds Display Repair Mode, an inspection and
cleanup of the Nextion scripts and Home Assistant hub settings; multi-hub support
remains subject to a needs decision.

---

## v0.4.x — finishing the binary and TFT install (current focus)

Primary job: close the install gate. The hardware passlist and the update flow
are confirmed on one EU and one US/portrait panel — universal image onboarding,
TFT auto-update end to end, firmware OTA, encrypted native OTA, sleep/wake,
touch/navigation, core stability and the editor add/remove/YAML flows. Only
notification behaviour remains.

**Remaining passlist row** — confirm on one EU and one US/portrait panel:

- **Notifications** — popup, `force_show`, list, dismiss, persistent and critical
  sounds, quiet hours, `notify.*` entities and font sizes, including
  long-message paging and the update popup text
  ([#84](https://github.com/happydasch/nspanel_haui/issues/84)).

**Acceptance:** the notification row green on both display models and both TFT
assets working from the published release. A failing row ships as a `0.4.x`
patch; **v0.5 does not start until this gate is green.**

---

## v0.4.6 — notification verification (in progress)

**Status: in progress on `dev`.** v0.4.5 shipped on 2026-11-09 — see the
[0.4.5 changelog](CHANGELOG.md#045--2026-11-09) for the full list and
[v0.4.5 release notes](.github/release-notes/v0.4.5.md) for the details. The
release gate itself is still open:

- Complete the notification passlist row above, including long-message paging and
  the update popup text, on both display models.
- Fix any defect the pass finds as a 0.4.6 patch and re-verify it.

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

- **Automatic updates** work per device and in one global policy for TFT and
  firmware, and expose a visible retry policy that stops after failure.
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
never draws. The HMI audit and the pre-page theme painting shipped in 0.4.5; one
fix remains:

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
- **Device color schemes and first render** — the device-level scheme selector
  and pre-page theme painting shipped in 0.4.5. The remaining optimisation is to
  predefine palettes in the TFT so the first render needs fewer color commands,
  without flashing the default palette or showing a partially themed page;
  editor cards must continue to match the device render.
- **Panel editors** — split-view preview built on the hub's card render
  (`nspanel_haui/virtual_panel/render`, which already draws unsaved edits),
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

- Scripted HMI patching for release-only edits — `tftVersion` scripting landed
  with the version-bump tooling (0.4.x); Send Component ID and other in-place
  edits still need the Editor or an extended patch spec (0.5+).
- Portrait layout as a build-time rotation instead of a second committed HMI
  (0.5+).

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
- **TFT storage** — the binaries stay committed to git and attached to releases
  until repo/zip size makes Git LFS or release-only storage worthwhile.
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
- **0.4.2** — firmware auto-update through release manifests, TFT upload and
  reboot fixes.
- **0.4.3** — TFT installs move to the integration; per-device update settings
  and the **HAUI Display** entity.
- **0.4.4** — notification `timeout` hotfix; the TFT files stay at 0.4.3.

---

*Living document — priorities shift as the project grows. Open an issue or start
a discussion to propose changes; shipped work moves to [CHANGELOG.md](CHANGELOG.md).*
