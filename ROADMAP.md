# Roadmap

Development trajectory from **v0.3.2** toward **v1.0**. **v0.4.0 is
feature-complete and in final validation**: the version is set in all four
places and the CHANGELOG entry is written. What remains for the tag is a pushed
CI run on the current candidate (backend and frontend suites, ruff, mypy,
docs), the **device passlist on real EU + US hardware**, and the `v0.4.0`
GitHub release. The release after that is **v0.5.0 — high-speed display update**.

This file tracks **open work only**. Shipped changes are summarised in
[CHANGELOG.md](CHANGELOG.md); completed rows are removed from here when a release
ships. The release runbook and its known risks live in
[docs/release.md](docs/release.md).

---

## v0.4.0 — Remaining release gates

### Release checklist

| Open item | Scope |
|-----------|-------|
| Run the device passlist below on real EU + US hardware | `haui/`, `esphome/`, `nextion/` |
| Publish the GitHub release: `release.yml` compiles the `.bin` and attaches both TFTs; tag `v0.4.0` after the passlist | GitHub Releases |
| Confirm the documented notification behaviour against real hardware during the passlist — HA service persistence, `force_show` and `require_ack`, the ESPHome `send_notification` action with optional `persistent`/`text_size`, popup long-message scrolling and severity default icons | `docs/services.md`, `docs/esphome.md`, `docs/panels/popup_notify.md`, `docs/device.md` |
| Confirm the 0.3.x upgrade path in the editor — the five renamed device-setting keys migrate automatically; saved panels are not migrated and must be re-entered and verified | `haui/`, `docs/upgrading.md` |

**Device passlist** — confirm on one EU and one US/portrait panel:

- **TFT auto-update** — with firmware 0.4.0 and an older TFT, the display
  installs TFT 0.4.0 about a minute after connecting; About/Device Manager then
  show 0.4.0 (reconnect first if it looks stale). With `auto_install` off, the
  "Outdated TFT-Version" popup appears. Tapping the time area advances the card
  (the `clock.tTime` Send Component ID fix).
- **Universal `nspanel_haui.bin`** — flash a fresh panel, join the device-named
  AP (e.g. `nspanel-haui-a1b2c3`), enter Wi-Fi, add the device with the
  documented API key. Settings sync reaches the firmware (entity-registry
  resolved), TFT auto-updates, panel renders. Repeat on a second panel and
  confirm both get distinct names/APs from the same `.bin`.
- **Notifications** — popup, `force_show`, list, dismiss, persistent and
  critical sounds, quiet hours, `notify.*` entities, font sizes, and
  `require_ack` looping until **Acknowledge**.
- **Wakeup / sleep** — wake on touch and via the `wakeup` service, sleep
  panel(s)/carousel and auto-dim as configured, state survives sleep/wake cycles.
- **Touch / general functionality** — every widget responds and navigates;
  gestures/swipes work on both layouts; button rows, header actions and popups
  behave; no dead zones.
- **Core stability** — one worker per device; touches, page changes and the
  heartbeat stay responsive; `hub_availability` resets on the last disconnect;
  ESPHome `min_version` 2026.10.0; row/weather/QR values visible; a popup pauses
  auto-dim on a device named with capitals or `-`.
- **Editor** — add / remove / enable / disable device and YAML import.

**Acceptance:** every passlist row green on both display models, both TFT assets
published, and the portrait device auto-updates end-to-end.

### Shipped in 0.4.0 (summary)

Full detail is in [CHANGELOG.md](CHANGELOG.md). The release closed the October
2026 code review: crash and wrong-state fixes, an admin-only editor API, panel
behaviour fixes, one worker thread per device, Python 3.14 + mypy in CI, dead
code removed, and device config consolidated onto the panel store. It also
completed the wiring audit (settings reach the firmware on save and connect,
action items without a target, "keep config" removal, `wakeup` without a wakeup
panel, page items follow entity state) and the release-readiness work (TFT
auto-update from the matching release, dual-update warning in the changelog).

---

## v0.5.0 — High-speed display update

Move the display to a high-speed link so TFT installs and runtime rendering run
at **921600 baud** instead of 115200 — an 8× baud increase (~10× in practice),
turning an ~11 MB TFT update from ~16 min into ~2 min. The bottleneck is the UART
baud rate; the TFT must enforce the rate on boot and a boot scan must recover
panels still on an old 115200 TFT after the firmware update.

| Task | Scope |
|------|-------|
| Raise the display UART to 921600 baud (`baud_rate: 115200 → 921600`); TFT upload inherits the rate (`upload_tft(baud=0)` uses the UART baud — `api.yaml`/`button.yaml` need no change), and the universal image inherits via the `hardware.yaml` package | `esphome/nspanel_haui/hardware.yaml` |
| Add the **boot baud-rate scan**: `baud_scan` power-cycles `screen_power`, probes every Nextion-supported rate directly over `haui_uart` (`get sleep\xff\xff\xff` probe), switches the UART to the detected rate; `baud_check_at_boot` waits a `BAUD_RATE_TIMEOUT` for `haui_disp->is_detected()` before scanning | `esphome/nspanel_haui/` (new script, wired into boot/watchdog) |
| Recompile **both** TFTs with `bauds=921600` in the boot event code (today `bauds=115200//Configure baudrate` at offset 7340991 in `nspanel_haui.HMI` and `nspanel_haui_portrait.HMI`); re-export both `.tft` in the Nextion Editor; run `scripts/verify_nextion.py --require-portrait` + `gen_portrait.py --check` parity gates | `nextion/`, scripts |
| Pacing at the higher rate: keep `max_queue_size: 800` / `max_commands_per_loop: 50`, decide on `command_spacing` (candidate: `1ms`) guided by observed `on_buffer_overflow` events | `esphome/nspanel_haui/display.yaml` |
| Docs: baud default, update-time expectations, baud-scan recovery behaviour, upgrade caveats | `docs/esphome.md`, `docs/nextion.md`, `docs/install.md`, `docs/troubleshooting.md` |
| Device passlist: fresh 921600 TFTs on EU + portrait hardware, upgrade path from a 115200 TFT (baud-scan recovery), universal prebuilt image, repeated auto-updates, no UART overflows under the update burst | — |

**Acceptance:** TFT installs run ~8-10× faster on both display models and the
universal image; a panel still running an old 115200 TFT regains its display
after a firmware update without user action; no UART buffer overflows during
the auto-update burst.

---

## Release tooling

Open items from the release-process review (see
[docs/release.md](docs/release.md) for the current runbook and its known risks):

| Item | Target | Scope |
|------|--------|-------|
| `scripts/bump_version.py`: one command updates manifest, pyproject and ESPHome YAML and prints the HMI value to set; a test asserts the text files agree | 0.5 | `scripts/`, `tests/` |
| Release notes extracted from the `CHANGELOG.md` section instead of the static text in `release.yml` | 0.5 | `.github/workflows/release.yml` |
| Pre-flight in `release.yml` (`pytest`, `ruff`, `mypy`, `mkdocs build --strict`, `gen_portrait --check`, `gen_preview --check-missing`) so a tag cannot ship untested code | 0.5 | `.github/workflows/release.yml` |
| Scripted HMI patching for the release-only edits (`tftVersion`, Send Component ID), keeping the Editor as fallback | 0.5+ | `scripts/`, `nextion/` |
| Portrait layout as a build-time rotation instead of a second committed HMI | 0.5+ | `nextion/`, `scripts/gen_portrait/` |
| Git LFS or release-only storage for the TFT binaries | 0.5+ | repo |

---

## v0.5 — Frontend maturity

### Device manager

| Item | Priority | Scope |
|------|----------|-------|
| Allow multi‑device operations: bulk firmware/TFT update, move panels across devices (reordering devices works today) | Later | `frontend/` |
| Frontend Device Manager cleanup — consolidate the dialog after the v0.4 additions (layout, per‑device actions, stale states) | Next | `frontend/dialogs/device-manager.js` |

### Page / Panel management

| Item | Priority | Scope |
|------|----------|-------|
| Improve the panel list view — drag‑to‑reorder, inline rename, duplicate panel (reorder works through the row menu today) | Next | `frontend/` |
| Edit-panel sidebar cleanup — tidy the panel edit sidebar: selection state, actions, empty states | Next | `frontend/` |
| Add a "create from template" flow for common panel configurations | Later | `frontend/` |

### Editor UI polish

| Item | Priority | Scope |
|------|----------|-------|
| Form validation feedback (inline errors, required‑field indicators) | Next | `frontend/` |
| Preview cleanup — unify the panel preview renderers and styles, prune dead code (portrait re-flow included) | Next | `frontend/previews/`, `frontend/panel-previews.js` |
| Keyboard‑navigable modals and consistent focus management | Later | `frontend/` |
| Accessibility pass — labelled form controls, ARIA attributes, colour contrast | Later | `frontend/` |

---

## v0.6 — Features & integrations

### Platform maturity

| Item | Priority | Scope |
|------|----------|-------|
| Add a developer devcontainer / quick‑start script for new contributors | Next | `.devcontainer/`, `scripts/` |
| Stabilise the REST API surface before v1.0 (version prefix, consistent response shapes) | Next | `api.py` |
| ESPHome component tests that verify sensor/button/cover entities compile and behave | Later | `esphome/` tests |

---

## v1.0 — Stable release

| Item | Priority | Scope |
|------|----------|-------|
| All known bugs with the `bug` label closed | — | cross‑repo |
| `CHANGELOG.md` covering every release from 0.1.0 through 1.0 (started with 0.4) | — | root |
| HACS default integration status (no longer "custom repository") | Next | `hacs.json`, repo settings |
| Published on PyPI / HA add‑on registry (if applicable) | Later | CI / release |
| REST API docs published alongside user docs (`docs/services.md` and `docs/communication.md` cover services and the device protocol) | Later | `docs/api.md` (new) |
| Final branding pass: icons, screenshots, README hero image | Later | root assets |

---

## Deferred / needs decision

| Item | Why it waits | Scope |
|------|--------------|-------|
| Trim the HACS download: `export-ignore` the Nextion binaries | HACS users would lose the HMI sources | `.gitattributes` |
| Firmware OTA from Home Assistant | ESPHome exposes no supported OTA service; keep it a documented manual step | `frontend/`, `api.py` |
| Runtime credential adoption for the universal image | Post-0.4; the baked credentials stay shared for now | `esphome/` |
| `cls` background refresh after sleep/wake or reconnect | Needs hardware confirmation of how often it matters | `haui/abstract/`, `haui/controller/` |
| Byte-level TFT update progress | Needs firmware-side events | `esphome/`, `frontend/` |
| Full update-pipeline integration test | Unit and endpoint tests exist; the end-to-end test is still open | `tests/` |

---

## Prior releases

| Version | Summary |
|---------|---------|
| **0.1.x** | First versions as an AppDaemon app — ESPHome firmware with auto updates; weather, clock, grid, row, light, media, vacuum, QR, cover, climate and timer panels; panel locking and popups |
| **0.2.x** | Configuration and entity handling — ClockTwo screensaver, configurable wakeup, startup and notification sounds, notifications on the display |
| **0.3.x** | Native Home Assistant custom integration replaces AppDaemon and MQTT; panel editor inside Home Assistant |

---

*This roadmap is a living document. Priorities shift as the project grows — open an issue or start a discussion to propose changes.*
