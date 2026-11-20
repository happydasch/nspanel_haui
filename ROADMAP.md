# Roadmap

Development trajectory from **v0.5** toward **v1.0**. The last stable release is
**v0.5.2** (2026-11-17); v0.5.3 is in development on `dev`.

This file is the project's **direction**, not its backlog: the horizons it is
moving through and what every stable release must prove. Concrete features —
what they do, what "done" means, how expensive they are — live in
[FEATURE_WISHLIST.md](FEATURE_WISHLIST.md); shipped work is in
[CHANGELOG.md](CHANGELOG.md); the release runbook and its known risks are in
[docs/develop/release.md](docs/develop/release.md). What the project is for is in
the [documentation home](docs/README.md#what-the-project-is-for), and the
architectural invariants it holds are in
[Development](docs/develop/development.md#design-invariants).

## Horizons

Each horizon is a theme, not a list. The concrete features behind them are in
the [feature wishlist](FEATURE_WISHLIST.md), grouped in the same order: v0.5.x
in development, v0.6 next, then the open pool.

| Horizon | Theme | What it means |
|---|---|---|
| **Now — v0.5.x** | Speed and weight | Display installs take minutes rather than tens of minutes, the first render is cheaper, the vendored Nextion patch disappears, and the large TFT binaries leave the repository. |
| **Next — v0.6** | Recoverability and ownership | A damaged display is repaired from the editor; hub-scoped settings become editable in Home Assistant; the Nextion side is inventoried and cleaned up. |
| **After that** | Content and everyday use | The panels people keep asking for but do not have (a fan, a graph, free text) and the small options that decide whether a panel feels finished. |
| **v1.0 — stable** | Trust | Bugs closed, documentation complete, listed in the Marketplace catalog, REST API documented and frozen. |

## Release gates

Every stable release passes the CI jobs (`tests (3.14)`, `frontend`, `esphome`,
`docs`, `hassfest`, `hacs`) and `make release-preflight`, which also reports a
stale screen overview. Two process gates are not automated and are proved once
before a release may rely on them:

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
