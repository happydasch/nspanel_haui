# Development scripts

Helper scripts for the display assets, hub data, previews, translations and
releases. They are development tools only: the integration never runs them at
runtime.

Directories name their subject (`hmi_layout`, `font_tools`, `backgrounds`); the
`gen_*` prefix stays on the executable scripts that generate assets.

Run every command from the repository root — most scripts resolve paths
relative to it. Use the project virtual environment (Python 3.14) and install
the development dependencies once:

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Run Python tools as modules from the repository root, not by their file paths.
Replace each path separator with a dot and omit .py; for example,
`python -m scripts.hmi_layout.gen_layout --check` runs
`scripts/hmi_layout/gen_layout.py`. This works without installing the repository
as a package or setting PYTHONPATH.

Some tools have extra requirements:

- Node 22+ for the preview renders and `node --test`.
- Chrome or Chromium for the PNG/README image capture (pass `--chrome PATH` if
  it is not found automatically).
- Windows PowerShell with `ZiLib.dll` for the Nextion font generator.

## Overview

| Script | Purpose |
|--------|---------|
| `bump_version.py` | Bump the integration/firmware/TFT version everywhere it is stored |
| `bump_tft_version.py` | Set `system.tftVersion` in both HMI files and re-stamp the pages |
| `check_preview_coverage.py` | Verify every panel type resolves to a physical page in both layouts |
| `dev_release.py` | Write a local OTA image and firmware manifest for testing hub updates |
| `_ha_stubs.py` | Shared helper: installs `homeassistant.*` import stubs for the generators |

### Layout and HMI

| Script | Purpose |
|--------|---------|
| `hmi_layout/gen_layout.py` | Apply or verify widget geometry specs against the HMI files |
| `hmi_layout/gen_virtual_layout.py` | Regenerate the editor's virtual layouts, pictures, icon map, font metrics and theme code |
| `hmi_layout/portrait_layout.py`, `hmi_layout/landscape_layout.py`, `hmi_layout/theme.py` | Spec and attribute data — imported by the tools above, not run directly |
| `nextion2text/Nextion2Text.py` | Dump an `.HMI` project to readable text (widgets, attributes, event code) |
| `verify_nextion/verify_nextion.py` | Release gate for the HMI/TFT files |
| `verify_nextion/check_hmi_bump.py` | Fail when an HMI changed without a TFT version bump |

### Display images

| Script | Purpose |
|--------|---------|
| `backgrounds/gen_backgrounds.py` | Render the dimmed, cover-cropped background tiles per orientation |
| `design_grid/gen_grid.py` | Render the design-aid grid images used as Nextion Editor backgrounds |
| `spinner/gen_spinner.py` | Render the spinner sprite sheets over the system background |
| `rgb565_image/image_convert.py` | Print a PNG as a Nextion `pixelData~…` string |
| `rgb565_image/palette_generate.py` | Render the 256 × 256 RGB565 palette image |

### Fonts and characters

| Script | Purpose |
|--------|---------|
| `charset/gen_char.py` | Build the display character set (`charout.txt`) for font generation |
| `font_tools/Generate-HASP-Fonts.ps1` | Generate the Nextion ZI v5 text/icon fonts (Windows, ZiLib) |
| `font_tools/extract_chr_from_scss.py` | Extract Material Design icon codepoints into `font_tools/icons_mapping.py`/`.json` |
| `font_tools/extract_svg_from_mdi.py` | Extract the MDI SVG paths into `icons_data.json` |
| `font_tools/extract_weather.py` | Print the weather icon codepoints needed by the PowerShell font script |
| `font_tools/gen_cheatsheet.py` | Write `docs/cheatsheet.html` from `icons_data.json` |

### Colour tools

| Script | Purpose |
|--------|---------|
| `color_wheel/gen_color_wheel.py` | Render a 200 × 200 HSV colour wheel (`output.png`) |
| `color_palette/gen_color_palette.ipynb` | Notebook for colour-palette experiments |
| `rgb_conversion/rgb_conv.ipynb` | Notebook for colour conversion experiments |

### Previews and documentation images

| Script | Purpose |
|--------|---------|
| `preview_gallery/gen_preview_gallery.py` | Render every panel card with sample data; serve, screenshot or export the docs overview |
| `preview_gallery/sample_world.py` | Sample entities and render loop shared with the tests |
| `preview_gallery/gallery.html`, `preview_gallery/gallery.js` | The browser gallery |
| `preview_gallery/capture.mjs` | Headless Chrome capture used by `--png`/`--docs` |
| `readme_images/gen_readme_images.py` | Capture the README hero and step images into `docs/assets/readme/` |

### Translations, versions and tooling

| Script | Purpose |
|--------|---------|
| `translations/extract_translations.py` | Extract `t()`/`translate()`/`_()` strings and sync `haui/locale/*.json` |
| `translations/merge_translations.py` | Merge a completed `translate.json` batch back into the locale files |
| `release/dev_version.py` | CI helper: derive and write the dev firmware version |
| `release/generate_firmware_manifest.py` | CI helper: build `firmware-manifest.json` from the release artifacts |
| `git_hooks/install.sh` | Install the repository's git hooks (`core.hooksPath`) |
| `git_hooks/pre-commit` | Regenerate virtual-layout assets and run the layout check before a commit |
| `nextion_vnc/nextion_vnc.sh` | Serve the Nextion Editor VM through noVNC in a browser |

## Layout and HMI

### `hmi_layout/`

The HMI files are the source of truth for widgets, event code, fonts and
pictures. The Python specs describe reproducible geometry and selected
attributes. See [hmi_layout/README.md](hmi_layout/README.md) for the full
workflow; close the Nextion Editor project before patching an HMI, because the
editor rewrites the file when it closes an open project.

```bash
python -m scripts.hmi_layout.gen_layout --check                   # landscape (default)
python -m scripts.hmi_layout.gen_layout --spec portrait --check   # portrait
python -m scripts.hmi_layout.gen_layout                           # write landscape HMI
python -m scripts.hmi_layout.gen_layout --spec portrait           # write portrait HMI
```

`hmi_layout/gen_virtual_layout.py` reads both HMIs and writes the derived
assets the editor previews and cards use. Run it after every HMI change:

```bash
python -m scripts.hmi_layout.gen_virtual_layout
python -m scripts.hmi_layout.gen_virtual_layout --check
python -m scripts.hmi_layout.gen_virtual_layout --theme-code [PAGE ...]
```

Outputs: `frontend/virtual/layout_<orientation>.json`, `icon_map.json`,
`pictures/<orientation>/*.webp` and `haui/mapping/font_metrics.json`.
`--theme-code` prints the Preinitialize theme code to paste into a solid-colour
page in both HMIs.

### `verify_nextion/`

`verify_nextion/verify_nextion.py` is the release gate: it checks that
`clock.tTime` reports touches, that `system.tftVersion` matches
`esphome/nspanel_haui/version.yaml` in both HMIs, and — with
`--require-portrait` — that the portrait HMI/TFT exist and report the same touch
settings as the landscape one.

```bash
python -m scripts.verify_nextion.verify_nextion --require-portrait
```

`verify_nextion/check_hmi_bump.py` is the CI guard that fails a change which
modifies an HMI without advancing the TFT version:

```bash
python -m scripts.verify_nextion.check_hmi_bump --base origin/dev
```

### `nextion2text/`

Dump an `.HMI` into readable per-page text files. Use `-p visual` to include
geometry and colours, and `-s` to write a stats summary. See
[nextion2text/README.md](nextion2text/README.md).

```bash
python -m scripts.nextion2text.Nextion2Text \
    -i nextion/nspanel_haui.HMI -o ref_src/nextion-out-visual -d -s -p visual
```

`--help` lists every flag (event output, JSON output, unknown attributes, …).

## Display images

Each image type has its own directory; the scripts never write into another
one's output folder.

```bash
# Background tiles -> nextion/images/bkg/<orientation>/
python -m scripts.backgrounds.gen_backgrounds [--only NAME ...]

# Spinner sheets -> nextion/images/spinner_<orientation>_{1,2}.png
python -m scripts.spinner.gen_spinner [landscape|portrait ...]

# Design grids -> nextion/images/grid_<orientation>.png
python -m scripts.design_grid.gen_grid [landscape|portrait ...]
```

The design grids are editor-only aids. Regenerate them after a layout rule
(margins, header, bars) or a theme colour changes.

The RGB565 tools are small, ad-hoc utilities with hardcoded input/output
names, meant to be run from their own folder and edited for the task at hand:
`image_convert.py` prints `image.png` as a Nextion `pixelData~…` string, and
`palette_generate.py` renders `rgb565.png`.

## Fonts and characters

`charset/gen_char.py` writes the display character set to
`scripts/charset/charout.txt` (the selected Unicode ranges plus the Chinese
characters used by the UI). Regenerate it when the character set changes; it is
the character list used when building the display fonts.

`font_tools/` is a self-contained font toolchain; see
[font_tools/README.md](font_tools/README.md). The PowerShell script needs
Windows and `ZiLib.dll`; the Python helpers only extract codepoints and icon
data:

```bash
python -m scripts.font_tools.extract_chr_from_scss   # icons_mapping.py + .json
python -m scripts.font_tools.extract_weather         # print weather codepoints
python -m scripts.font_tools.extract_svg_from_mdi    # icons_data.json
python -m scripts.font_tools.gen_cheatsheet          # docs/cheatsheet.html
```

## Colour tools

The two Jupyter notebooks are exploratory: `color_palette/` is for palette
experiments and `rgb_conversion/` for RGB conversion experiments.
`color_wheel/gen_color_wheel.py` renders an HSV colour wheel to `output.png`
in the current directory.

## Previews and documentation images

`preview_gallery` renders a card of every panel type with the sample world and
replays the hub's own commands in the editor's simulator. See
[preview_gallery/README.md](preview_gallery/README.md).

```bash
python -m scripts.preview_gallery.gen_preview_gallery           # render only
python -m scripts.preview_gallery.gen_preview_gallery --serve   # browse the gallery
python -m scripts.preview_gallery.gen_preview_gallery --png     # one PNG per card
python -m scripts.preview_gallery.gen_preview_gallery --docs    # docs/assets/screens/ + docs/screens.html
```

Outputs go to the git-ignored `scripts/preview_gallery/out/`. The `Screens`
workflow runs `--docs` after each dev firmware build and commits the result;
do not edit those generated images by hand.

`check_preview_coverage.py` verifies every exposed panel (user, system and popup
alias) maps to a physical page present in both generated layouts:

```bash
python -m scripts.check_preview_coverage
```

`readme_images/gen_readme_images.py` captures the hero and step strips from
`readme_images/src/` with headless Chrome and writes them to
`docs/assets/readme/`:

```bash
python -m scripts.readme_images.gen_readme_images [--chrome PATH]
```

## Translations

Extraction is the routine step. It scans Python `self.translate("…")` calls,
descriptor `_("…")` markers and frontend `t("…")` calls, then adds new keys to
`haui/locale/*.json` (English text in `en.json`, empty placeholders elsewhere)
and removes keys no longer referenced:

```bash
python -m scripts.translations.extract_translations
```

Fill in the empty non-English values afterwards.
`translations/merge_translations.py` merges a completed
`scripts/translations/translate.json` batch back into the locale files without
clobbering existing translations; it is for external translation-service round
trips, not routine development.

## Versions and releases

`bump_version.py` keeps every version source in sync:

```bash
python -m scripts.bump_version 0.5.0                        # firmware release
python -m scripts.bump_version 0.5.0 --tft-update           # release with a TFT update
python -m scripts.bump_version 0.5.0 --check --tft-update   # dry run
python -m scripts.bump_version 0.5.0.dev3                   # dev firmware bump
```

A stable version updates `manifest.json`, `pyproject.toml`, the firmware
`yaml_version`, and — with `--tft-update` — `tft_version` plus both HMI
`system.tftVersion` values. A dev version is firmware-only. `CHANGELOG.md` is
not edited. `--text-only` is a legacy alias for a firmware-only release. A TFT
version change must keep the same string length; use the Nextion Editor for a
length-changing bump. A dev bump is also how a minor development cycle starts:
commit `X.Y.0.dev0` (a placeholder suffix) on `dev` after a release; the first
build writes its own run number and keeps the base.

`bump_tft_version.py` edits only `system.tftVersion` in the HMI binaries and
re-stamps the affected pages (useful after editing the HMI in the Nextion
Editor):

```bash
python -m scripts.bump_tft_version --version 0.5.0 [--check] [--hmi PATH]
```

`dev_release.py` turns a local firmware build into a test release that Home
Assistant serves over `/local/`. It verifies the version and variant embedded
in the image, then writes `nspanel_haui_ota.bin` and `firmware-manifest.json`:

```bash
python -m scripts.dev_release \
    --image esphome/.esphome/build/nspanel-test/build/firmware.ota.bin \
    --version 0.4.4-dev1 \
    --base-url http://homeassistant.local:8123/local/nspanel \
    --out /path/to/config/www/nspanel
```

Each test release needs a newer version than the panel currently runs, or the
hub keeps re-offering it.

`release/` holds CI helpers, not day-to-day tools:

- `dev_version.py RUN_NUMBER` derives the PEP 440 dev version from
  `manifest.json` and writes it to `manifest.json`, the firmware `yaml_version`
  and the GitHub environment (`DEV_VERSION`, `DEV_SHA`). It requires
  `GITHUB_ENV` and `GITHUB_SHA` and is run by the dev-firmware workflow.
- `release/generate_firmware_manifest.py` builds the stable release manifest
  from `nspanel_haui_ota.bin` and both TFT assets. It requires
  `GITHUB_REPOSITORY` and `GITHUB_REF_NAME` and is run by the release workflow
  for `v*` tags.

See [docs/release.md](../docs/release.md) for the full branch and release
process.

## Developer tooling

`git_hooks/install.sh` points `core.hooksPath` at `scripts/git_hooks`:

```bash
scripts/git_hooks/install.sh
```

The pre-commit hook runs `hmi_layout/gen_virtual_layout.py`, stages the
regenerated layout/picture/icon files, then checks both specs with
`hmi_layout/gen_layout.py --check` (landscape) and
`hmi_layout/gen_layout.py --spec portrait --check`. It never rewrites either
HMI. Install the development dependencies first so both generators can run.

`nextion_vnc/nextion_vnc.sh` starts websockify and noVNC and prints the URL of
the Nextion Editor VM. The first run installs websockify and clones noVNC into
the git-ignored `build/novnc/`:

```bash
scripts/nextion_vnc/nextion_vnc.sh
```

Environment overrides: `NEXTION_VNC_HOST` (default `192.168.65.2`),
`NEXTION_VNC_PORT` (default `5900`), `NOVNC_PORT` (default `6080`). The bridge
listens on `127.0.0.1` only.

## Shared helper

`_ha_stubs.py` installs a meta-path finder that stubs `homeassistant.*`
imports, so generators can import the `haui` package without Home Assistant.
Import it **before** importing `haui` modules:

```python
import _ha_stubs  # noqa: F401  (installs the stubs)
```

## Checks before committing

Run from the repository root:

```bash
pytest tests/
node --test 'tests/frontend/*.test.mjs'
ruff check custom_components/ scripts/
mypy
zensical build --strict
python -m scripts.verify_nextion.verify_nextion --require-portrait
python -m scripts.hmi_layout.gen_virtual_layout --check
python -m scripts.hmi_layout.gen_layout --check
python -m scripts.hmi_layout.gen_layout --spec portrait --check
```

When adding or removing a script, update this file (and the script's own
docstring or README) so the index stays complete.
