# Roadmap

Development trajectory from **v0.5** toward **v1.0**. The last stable release is
**v0.5.7** (2026-11-27).

This file is the project's **direction**, not its backlog: the horizons it is
moving through and what every stable release must prove. Concrete features —
what they do, what "done" means, how expensive they are — live in
[FEATURE_WISHLIST.md](FEATURE_WISHLIST.md); shipped work is in
[CHANGELOG.md](CHANGELOG.md); the release runbook and its known risks are in
[docs/develop/release.md](docs/develop/release.md). What the project is for is in
the [documentation home](docs/README.md#how-it-works), and the
architectural invariants it holds are in
[Development](docs/develop/development.md#design-invariants).

## Horizons

Each horizon is a theme, not a list. The concrete features behind them are in
the [feature wishlist](FEATURE_WISHLIST.md), grouped in the same order: v0.5.x
in development, v0.6 next, then reaching a stable v1.0.

| Horizon | Theme | What it means |
|---|---|---|
| **Now — v0.5.x** | Speed and weight, Recoverability and ownership | 0.5.7 lands the 921600 display link, keeps the display assets out of every download and paints body foregrounds from the TFT; the Nextion side is inventoried and cleaned up. The **Repair display** action, its manifest `repair` block and both one-page repair TFTs land in 0.5.8, so a release installs the minimal file first and the TFT the firmware needs right after it, and a display that takes no ordinary file is recovered from the editor. Hub-scoped settings are editable in Home Assistant now: **Configure** on the integration card renames the hub and sets the display defaults every panel inherits, while per-device settings stay in the editor ([Hub settings](../user/hub-settings.md)). The boot scan and the install retry that 0.5.7 adds stay insurance for the silent display, and no panel has needed either yet. Removing the vendored Nextion patch waits on an ESPHome release that carries the TFT upload retry, so it left the cycle for the wishlist's *Firmware and dependencies*. |
| **Next — v0.6** | Content and everyday use | The panels people keep asking for but do not have (a fan, a graph, free text), a refreshed and larger background set, and the small options that decide whether a panel feels finished. |
| **v1.0 — stable** | Trust | Bugs closed, documentation complete, listed in the Marketplace catalog, REST API documented and frozen. |

## One TFT per display model

A release carries one display file per model, landscape and portrait, and a panel
installs the one its **Display Model** names. A faster link is not a second
artifact: the 921600 bps rate is set in `Program.s` inside that single TFT, the
firmware starts its UART at the same rate and scans down only for an older or
stock one, and a display that cannot hold a transfer at 921600 gets the same
install once more at 115200 bps. The earlier plan for separate high-speed and
normal-speed TFTs is dropped — a speed variant would double every display build
and every install for a link the one file already sets.

The repair pair does not reopen it: `nextion/nspanel_haui_repair.tft` and
`nextion/nspanel_haui_repair_portrait.tft` are one page each, installed only when
the normal file cannot be, and never a build a panel runs day to day
([The repair TFTs](docs/develop/nextion-editor.md#the-repair-tfts)).

## Release gates

Every stable release passes the CI jobs (`tests (3.14)`, `frontend`, `esphome`,
`docs`, `hassfest`, `hacs`) on the promotion pull request that carries it:
`master` is stable-only and a release commit reaches it no other way. Four
process gates are not automated and are proved once before a release may rely
on them:

- **Release-check recovery.** The documented recovery from a GitHub Actions run
  that failed before its jobs started — check githubstatus.com, close and reopen
  the PR or push a new head commit, then re-run the failed workflow — has not
  been exercised end to end. Prove it once on a dev-cycle PR before relying on
  it for a release
  ([release process](docs/develop/release.md#guardrails-and-known-gaps)).
- **Unattended updates.** `check_on_connect` and `update_interval` install
  updates without anyone watching, but no run has been recorded on real
  hardware: that the panel comes back on its own after a firmware install and
  the TFT that follows, and how long it takes. Prove it once with
  `firmware_auto_update` and `auto_install` on before relying on unattended
  updates ([updates Q&A](https://github.com/happydasch/nspanel_haui/discussions/69)).
- **Display recovery.** The boot scan's silent-display retries and the TFT
  install retry at 115200 bps are insurance, not a repair anybody has watched:
  the panel that came back on hardware did so on an ordinary fresh boot after a
  firmware update. Prove both once — a display that answers nothing after the
  first scan, and an install the display refuses at 921600 — before the
  troubleshooting guide treats them as the cure
  ([troubleshooting](docs/user/troubleshooting.md#the-panel-refuses-every-tft-upload)).
- **Display repair.** The repair path — a minimal file the display takes where
  the 11 MB one fails, the reboot it ends in, and the install queued 15 s after
  the panel reconnects — has not been run on hardware. Both repair projects are
  built to the developer guide's spec and committed, so a release carries the
  pair; the run is what is missing. Prove one repair end to end on a display that
  refuses its ordinary TFT before a release offers the action as the cure
  ([Display repair](docs/develop/update-process.md#display-repair)).

## Prior releases

- **0.1.x** — first versions as an AppDaemon app; ESPHome firmware with auto
  updates and the first panel set.
- **0.2.x** — configuration and entity handling; ClockTwo screensaver,
  configurable wakeup and notification sounds.
- **0.3.x** — native Home Assistant integration replaces AppDaemon and MQTT; the
  panel editor moves inside Home Assistant.
- **0.4.0 onward** — see [CHANGELOG.md](CHANGELOG.md).

---

*Living document — priorities shift as the project grows. Feature candidates go
to [FEATURE_WISHLIST.md](FEATURE_WISHLIST.md); shipped work moves to
[CHANGELOG.md](CHANGELOG.md).*
