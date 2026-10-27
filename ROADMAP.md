# Roadmap

Development trajectory from **v0.3.2** toward **v1.0**. **v0.4.0 and v0.4.1
shipped on 2026-10-26 and v0.4.2 on 2026-10-27**, each tagged from a green
`master` commit and published by the release workflow.

The **dev** branch tracks **0.4.3**: the update-trigger gaps found while
validating 0.4.2 on hardware (see the collected issues below) plus the remaining
gate work. What the gate still needs is the hardware confirmation on the passlist
below.

This file tracks **open work only** — goals and gates, not task lists. Shipped
changes are summarised in [CHANGELOG.md](CHANGELOG.md); the release runbook and
its known risks live in [docs/release.md](docs/release.md); day-to-day tasks
belong in the issue tracker.

**The 0.4.x install gate comes first.** The binary and TFT install must work
completely and the base and core functions must be proven on real hardware.
Nothing in v0.5 or v0.6 starts before that: a broken install or a core regression
blocks the next minor release, and anything the passlist turns up ships as a
`0.4.x` patch. After the gate closes, **v0.5** adds multiple TFTs for normal- and
high-speed updates, stable and controllable manual/auto updates in the frontend,
and a Device Manager overhaul. **v0.6** adds Display Repair Mode — a simple TFT
used to repair an existing display.

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
- **Confirm recent fixes on hardware** — TFT reinstall (#63), buzzer stop (#62)
  and portrait weather time (#64) are fixed on dev (0.4.2, see Changelog); the
  hardware confirmation on the passlist below is what remains.
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

### 0.4.3 — collected issues

Issues found while validating 0.4.2 on hardware, collected for the next patch.

- **Automatic TFT/firmware updates never trigger.** `DEFAULT_CONFIG["update"]`
  (`auto_install`, `tft_filename`, `on_connect_delay`, `check_on_connect`,
  `update_interval`, `firmware_auto_update`) is never merged from config-entry
  data, the panel store or YAML import — `_build_config_dict` only merges device
  fields and `DEVICE_CONFIG_FIELDS` excludes `update` — and the frontend has no
  control for it. The shipped defaults are therefore hardcoded:
  `update_interval: 0` starts no timer and `check_on_connect: False` skips the
  check on connect, so `check_for_update()` — the GitHub-release check that also
  triggers the firmware install — never runs on its own. Expose the settings
  (options flow and/or device editor) and choose working defaults.
- **The device's `HAUI Firmware` entity cannot fetch the manifest.** ESPHome's
  default `http_request` RX buffer is 512 bytes against GitHub's ~5.4 KB redirect
  headers, so the entity never reports an available update and
  `firmware_auto_update` stays inert even when the hub's check runs. Raise
  `buffer_size_rx` in `base.yaml`.
- **Update settings are documented but not exposed.** `docs/configuration/device.md`,
  `docs/upgrading.md` and the 0.4.2 changelog tell users to set
  `firmware_auto_update: false` and call the update block "Global Defaults (not
  per-device, fixed)" — there is no control for either. Correct the wording once
  the settings are exposed.
- **No update status or manual check in the editor.** The editor shows TFT
  install state but not whether the device's firmware entity reports an update,
  and there is no "Check for updates" action; only "Install TFT" and "Download
  firmware" exist. Surface firmware availability and a manual refresh.
- **Release lookups are per device and unauthenticated.** Each device's update
  controller calls the GitHub releases API independently; enabling checks by
  default risks the 60-requests/hour IP limit. Cache the release list at hub
  level or read the manifest instead. The device's firmware entity polls every
  6 h, so request a refresh before evaluating or the hub can see a stale "no
  update" state.
- **Release hygiene.** #62/#63/#64 are fixed in the published 0.4.2 and still
  open; confirm on hardware and close them. Consider the deferred full
  update-pipeline integration test so the trigger path is covered end to end.

---

## v0.5 — Multiple TFTs, update control & Device Manager overhaul

Three pillars, after the 0.4.x gate closes.

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

After the update and Device Manager work: panel list improvements (drag-reorder,
inline rename, duplicate — reorder works through the row menu today), edit-panel
sidebar cleanup, a "create from template" flow, inline form validation feedback,
preview renderer unification and dead-code pruning, keyboard-navigable modals,
and an accessibility pass (labels, ARIA, contrast).

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
