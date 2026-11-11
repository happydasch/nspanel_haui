# Roadmap

Development trajectory from **v0.3.2** toward **v1.0**. **v0.4.0 and v0.4.1
shipped on 2026-10-26, v0.4.2 on 2026-10-27, v0.4.3 on 2026-10-28, v0.4.4 on
2026-11-02, v0.4.5 on 2026-11-09 and v0.4.6 on 2026-11-09**, each tagged from a
green `master` commit and published by the release workflow.

The 0.4.x hardware acceptance and OTA risk checks are closed. The 0.4.5 feature
set — including the live panel preview
contributed in [#85](https://github.com/happydasch/nspanel_haui/pull/85) and
[#86](https://github.com/happydasch/nspanel_haui/pull/86) — shipped in that
release. v0.4.6 was a one-line patch: the Marketplace could not compare a
two-part `homeassistant` minimum (`2026.11`) with the installed `2026.11.0` and
reported it as unmet
([#90](https://github.com/happydasch/nspanel_haui/issues/90)), so `hacs.json`
declares `2026.11.0`. The consolidation work planned for the 0.4.6 number moved
to **v0.4.7**, which pays down docs, CI and the dev release cadence before the
v0.5 frontend cycle.

This file tracks **open work only** — goals and gates, not task lists. Shipped
changes are summarised in [CHANGELOG.md](CHANGELOG.md); the release runbook and
its known risks live in [docs/release.md](docs/release.md); day-to-day tasks
belong in the issue tracker.

**The 0.4.x install gate is closed.** The binary and TFT install, firmware OTA
and the base and core functions are confirmed on real EU and US/portrait
hardware. The v0.4.7 cycle is a deliberate consolidation release — docs, one
simplified CI pipeline, fewer development releases and the frontend groundwork
for the next cycle. **v0.5** is then the frontend cycle: the Device Manager and
Device Info merge, unified profiles, default gestures in the editor, language and
regional formats in one place, the general editor rework, a notifications center,
device settings and update control, alongside multiple TFTs for normal- and
high-speed updates. **v0.6** adds Display Repair Mode, an inspection and cleanup
of the Nextion scripts and Home Assistant hub settings; multi-hub support remains
subject to a needs decision.

---

## v0.4.x — docs, CI & frontend groundwork (in progress) (current focus)

The install gate is closed. The hardware passlist and the update flow are
confirmed on one EU and one US/portrait panel — universal image onboarding, TFT
auto-update end to end, firmware OTA, encrypted native OTA, sleep/wake,
touch/navigation, core stability and the editor add/remove/YAML flows. This cycle
pays down docs, CI and the development release cadence before the v0.5 frontend
cycle.

---

**Docs.** Make `docs/` match the shipped editor and update flow again: one
navigation without duplicated device/update/service explanations, no stale 0.4.x
instructions, every documented action and option present in the current editor,
the [screens overview](docs/screens.html) linked from the panel docs, and the new
dev release cadence and simplified pipeline written into
[release process](docs/release.md) and [development](docs/development.md).

**Fewer development releases.** Development builds are dispatched manually
(2026-11-09) instead of running on every push to `dev`: a push no longer
publishes a prerelease, pushes a bot version commit or regenerates the screens.
Dispatch a build only when it changes what a device installs (firmware or
display inputs); hub-only, docs and frontend pushes ride along in the next one.
Keep the PEP 440 tag rules — the tag identical to the manifest version, no
non-version tags — so Marketplace ordering stays correct, and keep the bot
version commit off `dev` except when a build is dispatched.

**Release-check resilience.** The 2026-11-09 GitHub Actions outage failed runs
before their jobs started (no job ever ran and no retry was possible) and kept
the 0.4.6 release PR blocked until `tests (3.14)`, `frontend`, `hassfest` and
`hacs` all reported. The recovery path is now in the
[release runbook](docs/release.md#guardrails-and-known-gaps): check
githubstatus.com, close and reopen the PR (or push a new head commit), then
re-run the failed workflow so the missing jobs start. Verify the path once on a
dev-cycle PR before relying on it for a release.

**Frontend groundwork for v0.5.** Land the base the rework builds on without a
visible change: one observable store and typed API client behind the existing
views, agreed view-module boundaries, and a written v0.5 information
architecture and phasing (shell, panel editors, notification center, device
settings). The static, unauthenticated, no-build serving contract stays. The
visual target is `design/dashboard-prototype.html`; the agreed structure and
module ownership are in [the frontend architecture](docs/frontend.md).

**Panel preview generation** The assets should be created after new version was
released or manually. Preview and docs should also be updated.

**Other cleanup.** Remove the vendored `esphome/nextion_patch/` and its
`external_components` blocks and bump `min_version`/`requirements-esphome.txt`
once a released ESPHome 2026.11 contains the fixes; keep `CHANGELOG.md` and the
release notes in sync.

**Acceptance:** docs strict build green with no stale instructions; three CI
workflows with every gate still enforced; development builds dispatched only
when the device inputs change, with Marketplace ordering intact; the frontend
foundation merged with no visible change; the vendored Nextion patch removed
once ESPHome ships the fixes.

---

## v0.5 — Frontend cycle, multiple TFTs & update control

Three pillars plus the planned frontend, notification and device-settings work,
after the 0.4.x consolidation cycle.

**Device Manager and Device Info merge.** Collapse the two device surfaces into
one: the Device Manager owns the device list, selection, connection and version
status, WiFi/IP/RSSI, update state and the per-device actions, with Device
Settings opening from the same place. Remove the separate Device Info dialog and
the duplicated status/version rendering; polling stays scoped to the selected
device and behaviour is otherwise unchanged.

**Unified profiles (Day/Night and quiet hours).** Merge the separate Day/Night
Profiles and Quiet Hours settings into one general **Profiles** area: create any
number of named profiles, each holding the settings a profile owns today
(brightness, dim/page/display-off timeouts, idle page, do-not-disturb and sound
behaviour), and give each one a schedule that activates it — a fixed local clock
window or sunrise/sunset with offsets. Day, Night and quiet hours become
predefined profiles under the same model, with saved settings migrated onto
them. One profile is active at a time, applied on startup, reconnect, settings
save and schedule boundaries; the live auto-dimming and auto-display-off
switches stay independent.

**Default gestures in the editor.** Make the built-in single-swipe actions first
class and visible instead of hardcoded: left/right step through the navigation
panels, up opens About and down opens Settings, and the Gestures section shows
these defaults per device with each swipe overridable (open a panel, run an
action or disable it). `gesture_sequences` stay as the multi-swipe shortcuts on
top; an unset override falls back to the built-in binding and saving applies
without a restart.

**Language and regional formats in one place.** Fold the separate Time & Date
section into the Language section, so one area holds the display language and
its regional overrides — time and date formats plus the locale-aware date
pattern — together with the other language-driven settings. Behaviour is
unchanged: an empty override keeps the language's locale-based layout.

**Acceptance:** one device dialog with no duplicated status rendering; one
Profiles area whose named, scheduled profiles cover Day/Night and quiet hours
without losing saved settings; the default swipe actions shown and overridable in
the editor; the language and regional format settings in one section.

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

### Device Manager removal

The Device Manager and Device Info merge lands in this cycle, giving one
per-device surface. v0.5 builds the remaining operations on it: bulk firmware/TFT
updates, moving panels across devices (reordering works today), and per-device
version and action state that stays correct across stale or failed updates. Device
Manager will be reimplemented and not be a Dialog.

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

Planned beyond the three pillars above; the data/API foundation lands in v0.4.7
and the Device Manager merge is part of this cycle. Each phase ships on its own.

- **General frontend rework** — the panel and device requirements are known now,
  so rebuild the editor as one coherent app instead of layering patches on the
  original screen set: a shell over one observable store and view modules,
  dialogs and forms on the vendored Lit components, a responsive layout with
  keyboard-navigable modals, and an editor/preview split view. This supersedes
  the incremental patchwork the editor-polish items above describe, which land
  here instead. The static, unauthenticated, no-build-step serving contract
  stays — that is how `web/editor.py` serves `frontend/` — so the rework is
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

**Phasing:** the API and data foundation with no UI change (v0.4.7), then the
Device Manager and Device Info merge, unified profiles, default gestures and the
language/regional merge, then the general frontend rework at behaviour parity
(editor-polish items included), then device settings, then panel editors, then
the notification UX, then polish and hardening.

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
- **0.4.5** — live preview and hub-rendered panel cards, editable popups, the
  **HAUI Firmware** entity, encrypted native OTA and the Home Assistant 2026.11
  Marketplace migration.

---

*Living document — priorities shift as the project grows. Open an issue or start
a discussion to propose changes; shipped work moves to [CHANGELOG.md](CHANGELOG.md).*
