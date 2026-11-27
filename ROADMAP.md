# Roadmap

Development trajectory from **v0.6** toward **v1.0**. The last stable release is
**v0.5.8** (2026-11-27); the **v0.5** cycle it closed is recorded in the
[changelog](CHANGELOG.md).

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
the [feature wishlist](FEATURE_WISHLIST.md), grouped in the same order: v0.6 in
development, then reaching a stable v1.0.

| Horizon | Theme | What it means |
|---|---|---|
| **Now — v0.6** | Content and everyday use | 0.5 closed with v0.5.8, which shipped the 921600 display link, kept the display assets out of every download, painted body foregrounds from the TFT, added the hub's own settings on the integration card and the display repair path; the four hardware gates it opened stay listed below until they are proved. 0.6 turns to content: the panels people keep asking for but do not have (a fan, a graph, free text), a refreshed and larger background set, and the small options that decide whether a panel feels finished, each with its done-means sentence in the [feature wishlist](FEATURE_WISHLIST.md). |
| **v1.0 — stable** | Trust | Bugs closed, documentation complete, listed in the Marketplace catalog, REST API documented and frozen. The cycles between 0.6 and it are set one at a time, each when the one before it closes. |

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
process gates are not automated; each is proved once on hardware or on a
dev-cycle PR before a release relies on it as the cure it describes. 0.5.8
shipped the display repair ahead of its run, which is why that gate is marked
below rather than closed.

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
- **Display repair.** 0.5.8 ships the repair path — a minimal file the display takes
  where the 11 MB one fails, the reboot it ends in, and the install queued 15 s after
  the panel reconnects — after building both repair projects to the developer guide's
  spec and covering the action, the manifest's `repair` block and both files with
  tests. **The run on hardware is still missing**, and the release went out ahead of
  it: no display that refuses its ordinary TFT has been recovered this way yet, so
  the action is offered as a first attempt rather than a proven cure. A repair that
  fails ends the attempt and reports the error, so an unproven run costs the user
  nothing beyond the attempt. Prove one repair end to end before the troubleshooting
  guide promotes the action to the cure it is meant to be
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
