# Release process & strategy

Audience: maintainers. This page documents how a release is cut today, what CI
enforces and the known risks of the setup. It is the single place to start when
preparing a release; the design rationale behind individual decisions stays in
[Development](development.md), and planned improvements are tracked in the
[Roadmap](https://github.com/happydasch/nspanel_haui/blob/master/ROADMAP.md#release-tooling).

## What a release ships

| Artifact | Source | Consumer |
|----------|--------|----------|
| Integration (HACS/zip) | `custom_components/nspanel_haui/` at the tag | Home Assistant users |
| `nspanel_haui.bin` | compiled by CI from `esphome/nspanel_haui_universal.yaml` | flashed onto the ESP32 (EU and US panels, same binary) |
| `nspanel_haui.tft` | `nextion/nspanel_haui.HMI`, compiled in Nextion Editor | landscape panels |
| `nspanel_haui_portrait.tft` | `nextion/nspanel_haui_portrait.HMI`, generated from the landscape HMI by `scripts/gen_portrait` | `display_model: us` panels |

The three binary artifact names are a **frozen contract**: `haui/device_config.py`
maps `display_model` to those filenames and `haui/controller/update.py` downloads
them from the GitHub release whose tag matches the firmware's `yaml_version`
(the `v` prefix is ignored by `_parse_version`). Renaming an asset breaks
automatic TFT updates for already-flashed panels, so a rename needs a migration
story first.

## Versioning and tag policy

Semantic Versioning. `custom_components/nspanel_haui/manifest.json` is the
source of truth; `haui/version.py` reads it at runtime. Four places must agree:

1. `custom_components/nspanel_haui/manifest.json` — source of truth.
2. `pyproject.toml` — packaging mirror.
3. `esphome/nspanel_haui/version.yaml` — firmware compatibility version.
4. `nextion/nspanel_haui.HMI` — global `system.tftVersion`, checked by the
   release gate against `manifest.json`.

Plus the `CHANGELOG.md` heading and the release date.

**Tags:** use `vX.Y.Z`. The release workflow only triggers on `v*`, while the
older history is tagged without the prefix (`0.3.2`, `0.3.1`). Those older tags
therefore never ran the automated workflow; `v0.4.0` is the first tag that does.
Do not "fix" old tags — the device-side lookup tolerates both forms.

## Branches and cadence

- `master` — release branch; every tag is cut from a green commit here.
- `dev` — integration branch for the next version.
- Feature branches — merged into `dev`, then `dev` into `master` for a release.

No fixed calendar. Ship when user-visible changes accumulate or a fix cannot
wait. Patch releases (`0.4.1`) for regressions; minor releases (`0.5.0`) for
features and breaking changes. **Any breaking change must ship with a
`docs/upgrading.md` entry and a CHANGELOG "Breaking changes" section** — no
alias is kept as a fallback, so the upgrade guide is the only migration path.

## CI gates

| Workflow | Triggers | Runs |
|----------|----------|------|
| `tests.yml` | pushes/PRs to `master`, `dev` | `mkdocs build --strict`, `pytest`, `ruff`, `mypy`, frontend tests |
| `docs.yml` | docs/mkdocs changes | `mkdocs build --strict`, Pages deploy from `master` |
| `validate.yml` | pushes/PRs, nightly | hassfest, HACS validation |
| `release.yml` | `v*` tags, manual dispatch | Nextion gate, ESPHome config + compile, asset upload |

**Gap to keep in mind:** a tag push does **not** re-run `tests.yml` — only
`release.yml` runs. The tag build therefore trusts that the tagged commit was
already green on a branch. Cut tags only from a passing `master` commit, and
re-check `git status` for uncommitted work first.

## Release runbook

### 1. Pre-flight (a few days before)

- Confirm `master` is green (tests, frontend, docs, hassfest/HACS).
- Confirm the device-test list in the
  [Roadmap's release checklist](https://github.com/happydasch/nspanel_haui/blob/master/ROADMAP.md#release-checklist)
  passed on real EU and US hardware.
- Freeze features; only fixes land from here.
- Decide the version number and check for pending breaking changes.

### 2. Version bump

- Set the version in the four places above (manifest, pyproject, ESPHome
  `version.yaml`, HMI `system.tftVersion`).
- Add or update the `CHANGELOG.md` section and its date.
- Re-save the HMI and recompile both TFTs (see next step) — the gate fails on a
  stale `tftVersion` or a stale TFT.

### 3. Nextion assets (human, GUI-only)

1. Open `nextion/nspanel_haui.HMI` in Nextion Editor; set `system.tftVersion`.
2. Make or verify the release's display changes; compile
   `File → TFT file output` → `nextion/nspanel_haui.tft`.
3. Re-run `python scripts/gen_portrait/gen_portrait.py` so the portrait HMI
   picks up landscape edits, then compile
   `nextion/nspanel_haui_portrait.tft`.
4. Run the gates locally:

   ```bash
   python scripts/verify_nextion/verify_nextion.py --require-portrait
   python scripts/gen_portrait/gen_portrait.py --check
   python scripts/gen_preview/gen_preview.py --check-missing
   ```

### 4. Docs and firmware

- Update user-facing docs for behaviour changes (install, services, display
  models).
- Breaking changes: write the `docs/upgrading.md` entry and the CHANGELOG
  "Breaking changes" section before tagging.
- Verify the universal firmware still validates:
  `esphome config esphome/nspanel_haui_universal.yaml`.
- The universal binary now serves **any number of panels**: the MAC suffix gives
  each device a unique name and access point, so no per-device build is needed.
  The baked API/OTA/web credentials remain shared — keep that caveat documented.

### 5. Tag and publish

```bash
git tag -a vX.Y.Z -m "NSPanel HAUI X.Y.Z"
git push origin vX.Y.Z
```

The tag push starts `release.yml`, which runs the Nextion gate, validates and
compiles the universal firmware, and attaches all three assets to the GitHub
release. Watch the run; do not announce before it is green.

### 6. Post-release

- Verify the release page carries all three assets with the expected names.
- Flash one panel from the published `.bin` and confirm TFT auto-update, as a
  smoke test of the exact published artifacts.
- Announce; link the changelog and the update warning.
- Merge `master` back into `dev`, then open the next `CHANGELOG.md` section.

### 7. Rollback

If the published assets are broken: mark the GitHub release as a draft (or
delete it) and publish a patch release. The update controller only installs the
TFT for the firmware's `yaml_version`, so a corrected tag is enough; never
re-point an existing tag at different bytes.

## Known complexity and risks

| # | Complexity | Impact |
|---|------------|--------|
| 1 | Nextion Editor is GUI-only | Version bump and TFT compile cannot be scripted; the release gate can only verify the result |
| 2 | Four version places, no bump script | Drift between manifest/pyproject/YAML/HMI is the most likely release failure |
| 3 | Portrait TFT derives from the landscape HMI | Every landscape edit needs a regeneration step; forgetting it fails the gate or ships a stale portrait |
| 4 | Frozen asset names | A rename silently breaks TFT auto-update for flashed panels |
| 5 | Tag pushes skip the test workflow | A tag on a stale commit can ship without a fresh test run |
| 6 | GitHub release body only points at `CHANGELOG.md` + the upgrade guide | Release notes live in `CHANGELOG.md`; the workflow body does not duplicate them |
| 7 | ~120 MB of Nextion binaries in git | HACS downloads include them; repo and zip size grow with every TFT rebuild |
| 8 | Shared baked credentials in the universal binary | Multi-panel naming is solved; credential isolation is not |
| 9 | ESPHome minimum version | `base.yaml` defines the minimum supported ESPHome version; the release workflow installs the current package and validates against that floor |

Planned improvements to this setup are tracked in the
[Roadmap](https://github.com/happydasch/nspanel_haui/blob/master/ROADMAP.md#release-tooling).
