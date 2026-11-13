# Roadmap

Development trajectory from **v0.3.2** toward **v1.0**. **v0.4.0 and v0.4.1
shipped on 2026-10-26, v0.4.2 on 2026-10-27, v0.4.3 on 2026-10-28, v0.4.4 on
2026-11-02, v0.4.5 and v0.4.6 on 2026-11-09, and v0.4.7 on 2026-11-11**, each
tagged from a green `master` commit and published by the release workflow.

The 0.4.x hardware acceptance and OTA risk checks are closed, and **v0.4.7
closed the consolidation cycle**: one CI pipeline, development builds dispatched
by hand, and the editor's data foundation — one observable store, one typed API
client, the v0.5 architecture in [the frontend docs](docs/develop/frontend.md) and the
visual target `design/dashboard-prototype.html`. The 0.4.5 live panel preview
(contributed in [#85](https://github.com/happydasch/nspanel_haui/pull/85) and
[#86](https://github.com/happydasch/nspanel_haui/pull/86)) remains the
production preview; v0.4.6 was the Marketplace minimum-version hotfix.

This file tracks **open work only** — goals and gates, not task lists. Shipped
changes are summarised in [CHANGELOG.md](CHANGELOG.md); the release runbook and
its known risks live in [docs/develop/release.md](docs/develop/release.md); day-to-day tasks
belong in the issue tracker.

**v0.5 is the current cycle.** So far it has delivered the Fleet/Device
dashboard, contextual panel details, device-option sidebars, a unified list of
single- and multi-swipe gestures, device schedules with schedule-aware firmware
dimming, and the shared theme library with a selector in both Preview and device
settings. The editor strings are complete in English, German, French, Dutch and
Polish. The schedule replaces Day/Night profiles and quiet hours; upgrade details
are in the [release notes](.github/release-notes/v0.5.0.md).
The remaining 0.5 scope is multiple TFTs for normal- and high-speed updates,
stronger update controls, and the panel/device/accessibility polish below. See
[CHANGELOG.md](CHANGELOG.md) for the shipped work.
**v0.6** adds Display Repair Mode, an inspection and cleanup of the Nextion
scripts and Home Assistant hub settings; multi-hub support remains subject to a
needs decision.

---

## v0.5 — Frontend cycle, multiple TFTs & update control (current focus)

The Fleet/Device dashboard and panel workspace described in
[the frontend architecture](docs/develop/frontend.md) are in place: the shell,
device inventory, device settings and panel editor with its preview. The
remaining work below builds on that structure, one view per change, on the same
static, no-build serving contract.

### Carried over from v0.4.7

- **Remove the vendored Nextion patch.** `esphome/nextion_patch/` stays pinned to
  ESPHome 2026.10.0 because no released version contains the numeric-response
  fix ([esphome#17744](https://github.com/esphome/esphome/pull/17744)) or the TFT
  upload buffer option
  ([esphome#21435](https://github.com/esphome/esphome/pull/21435)), and the TFT
  upload retry fix is not upstream yet. Once a released ESPHome 2026.11 (or
  later) contains every fix listed in `esphome/nextion_patch/README.md`, bump
  `min_version` and `requirements-esphome.txt` together, delete the directory
  and its `external_components` blocks, and re-validate the firmware config and
  a compile.
- **Verify the release-check recovery path.** The 2026-11-09 GitHub Actions
  outage failed runs before their jobs started; the documented recovery (check
  githubstatus.com, close and reopen the PR or push a new head commit, then
  re-run the failed workflow) has not been exercised end to end. Prove it once
  on a dev-cycle PR before relying on it for a release
  ([release process](docs/develop/release.md#guardrails-and-known-gaps)).
- **Screen overview cadence.** The development build regenerates
  `docs/screens.html` and `docs/assets/screens/` and commits them with its
  version. A release that ships without a preceding dev build must run
  `python -m scripts.preview_gallery.gen_preview_gallery --docs` during release
  prep so the published screen overview matches the shipped panels.

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

The per-device Updates sidebar has a single status, grouped update settings
with draft/save, a release channel and optional manifest override, and manual
installs. One hub-wide update policy (with a per-device override) sets automatic
installs, a waiting period and a retry limit; a scheduled firmware install can be
started now, put off or skipped; Fleet installs every device one at a time on the
hub; and a running install shows its step and an estimate. Still open: verify the
step timings and a two-device rollout on real panels.

### Device operations

The Fleet dashboard lists, scans, adds, enables and removes devices, and the
Device screen carries status, diagnostics, settings and updates. Still open on
that surface: moving (not just copying) panels across devices and keeping each
device's version and action state correct across stale or failed updates.

### Remaining editor polish

The Add panel catalog has starter templates, and panel options are checked
against their type in the editor and on the hub. Still open: the rest of the
accessibility pass (contrast, screen-reader review of the dashboard, a keyboard
way to reorder devices, which only drag today).

### Frontend polish & themes (current cycle)

The data/API foundation landed in v0.4.7; the dashboard and scoped settings, panel
and device-order endpoints are in place. What remains of the editor work:

- **Device themes and first render** — the device-level theme selector and
  pre-page theme painting shipped in 0.4.5, and the shared theme library in 0.5.
  The remaining optimisation is to predefine palettes in the TFT so the first
  render needs fewer color commands, without flashing the default palette or
  showing a partially themed page; editor cards must continue to match the
  device render.
- **Panel editors** — starter templates and field-level checks of type-specific
  options are in place, alongside default-type creation, popup extension, copying
  an existing panel, unsaved previews, inline rename, duplicate and reorder.

---

## Release tooling

Open items from the release-process review (runbook and known risks in
[docs/develop/release.md](docs/develop/release.md)):

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
  device's **Updates** sidebar even in a failed update state.
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
  the Hub App" rule from [Nextion Editor](docs/develop/nextion-editor.md#hard-rules) except
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
- **Notification history** — keep past notifications, with a read-only API and a
  view in the editor; nothing exists in code yet. Moved out of 0.5.
- **Notification grouping and priority ordering** — mainly backend work in the
  notification controller. Moved out of 0.5; the read/dismiss queue API and the
  editor's queue center already shipped.

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
- **0.4.5** — live preview and hub-rendered panel cards, editable popups, the
  **HAUI Firmware** entity, encrypted native OTA and the Home Assistant 2026.11
  Marketplace migration.
- **0.4.6** — Marketplace minimum-version hotfix: `hacs.json` declares
  `2026.11.0`.
- **0.4.7** — consolidation release: one CI pipeline, manually dispatched
  development builds, the editor's store and typed API client foundation, the
  v0.5 architecture and design prototype; no firmware or display changes.

---

*Living document — priorities shift as the project grows. Open an issue or start
a discussion to propose changes; shipped work moves to [CHANGELOG.md](CHANGELOG.md).*
