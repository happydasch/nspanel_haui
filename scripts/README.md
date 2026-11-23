# Development scripts

Development-only tools for display assets, hub data, previews, translations and
releases. The integration never runs them at runtime. Each script's docstring or
sub-README holds the detail; this page is the index and the common workflow.

Run every command from the repository root, as a module:

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt        # once per clone

python -m scripts.hmi_layout.gen_layout --check
```

Extra requirements: Node 22+ for the preview renders and `node --test`; Chrome
or Chromium for PNG captures (`--chrome PATH` if not found); Windows PowerShell
with `ZiLib.dll` for the Nextion font generator.

## Index

### Layout and HMI

| Script | Purpose |
|--------|---------|
| `hmi_layout/gen_layout.py` | Apply or verify widget geometry in an HMI (`--spec portrait` for the portrait HMI) |
| `hmi_layout/gen_virtual_layout.py` | Regenerate the editor's layouts, pictures, icon map, font metrics and theme code from both HMIs |
| `hmi_layout/landscape_layout.py`, `hmi_layout/portrait_layout.py`, `hmi_layout/theme.py` | Geometry and attribute specs imported by the tools above |
| `nextion2text/Nextion2Text.py` | Dump an `.HMI` project to readable text |
| `verify_nextion/check_hmi_bump.py` | Fail when an HMI or TFT changed without a TFT version bump |
| `verify_firmware/check_size.py` | Fail when the compiled firmware uses too much of its app partition |

### Display images, fonts and colours

| Script | Purpose |
|--------|---------|
| `backgrounds/gen_backgrounds.py` | Render the dimmed background tiles per orientation |
| `design_grid/gen_grid.py` | Render the editor-only design-grid images |
| `spinner/gen_spinner.py` | Render the spinner sprite sheets |
| `rgb565_image/image_convert.py` | Print a PNG as a Nextion `pixelData~…` string |
| `rgb565_image/palette_generate.py` | Render the RGB565 palette image |
| `color_wheel/gen_color_wheel.py` | Render an HSV colour wheel |
| `color_palette/gen_color_palette.ipynb`, `rgb_conversion/rgb_conv.ipynb` | Colour experiments |
| `charset/gen_char.py` | Build the display character set (`charout.txt`) |
| `font_tools/Generate-HASP-Fonts.ps1` | Generate the Nextion ZI fonts (Windows, ZiLib) |
| `font_tools/extract_chr_from_scss.py`, `extract_svg_from_mdi.py`, `extract_weather.py` | Extract icon codepoints and SVG data |
| `font_tools/gen_cheatsheet.py` | Write `docs/cheatsheet.html` |

### Previews, docs and checks

| Script | Purpose |
|--------|---------|
| `preview_gallery/gen_preview_gallery.py` | Render every panel card with sample data; serve, screenshot or export the docs overview |
| `preview_gallery/sample_world.py` | Sample entities and render loop shared with the tests |
| `preview_gallery/gallery.html`, `gallery.js`, `capture.mjs`, `docs_overview.py` | Gallery page, headless capture and docs comparison |
| `check_preview_coverage.py` | Verify every panel type maps to a page in both layouts |
| `check_frontend_styles.py` | Check the frontend CSS against the design tokens and scale |
| `readme_images/gen_readme_images.py` | Capture the README hero and step images from `readme_images/src/` |
| `readme_images/gen_editor_screenshots.py`, `capture_editor.mjs` | Capture the README editor and dashboard card screenshots from a throwaway Home Assistant |

### Translations, versions and releases

| Script | Purpose |
|--------|---------|
| `translations/extract_translations.py` | Extract `t()`/`translate()`/`_()` strings and sync `haui/locale/*.json` |
| `translations/merge_translations.py` | Merge a completed `translate.json` batch back into the locales |
| `bump_version.py` | Bump the integration, firmware and TFT versions everywhere |
| `bump_tft_version.py` | Set `system.tftVersion` in both HMIs and re-stamp the pages |
| `dev_release.py` | Write a local OTA image and firmware manifest for testing hub updates |
| `release/dev_version.py` | CI helper: derive and write the dev firmware and TFT versions |
| `release/compile_firmware.sh` | CI helper: compile the universal firmware and copy both images |
| `release/generate_firmware_manifest.py` | CI helper: build the release firmware manifest |
| `release/dev_release_notes.py` | CI helper: write the development prerelease notes |
| `release/preflight.py` | Report what a stable release still needs, without changing anything |
| `release/publish_stable.py` | Preview the next stable tag, or push it with `--push` |
| `release/sync_branches.py` | After a stable release: merge it into `dev`, open the next changelog section and merge `dev` into `master` (preview unless `--apply`) |

### Tooling

| Script | Purpose |
|--------|---------|
| `git_hooks/install.sh`, `git_hooks/pre-commit` | Install the hooks and regenerate layouts before a commit |
| `docs/dev_site.sh` | Point `mkdocs.yml` at the dev docs site |
| `nextion_vnc/nextion_vnc.sh` | Serve the Nextion Editor VM through noVNC |
| `_ha_stubs.py` | Install `homeassistant.*` import stubs for generators; import it before `haui` |

## Common workflows

**HMI change.** Close the Nextion Editor project before a script writes the HMI.
Change both HMIs, then run `gen_layout --check` and `gen_layout --spec portrait
--check`; compile both TFTs and advance `tft_version` if either TFT changed.
`gen_virtual_layout` regenerates the editor assets. Guide:
[docs/develop/nextion-editor.md](../docs/develop/nextion-editor.md).

**Preview screenshots.** `gen_preview_gallery --docs` writes
`docs/assets/screens/` and `docs/screens.html`; the dev-firmware workflow commits
them, so never edit those images by hand. Details:
[preview_gallery/README.md](preview_gallery/README.md).

**Translations.** Run `extract_translations` after any string change and fill in
the empty non-English values. `merge_translations` is only for an external
translation round trip.

**Release.** Follow the runbook in
[docs/develop/release.md](../docs/develop/release.md). `release/preflight` reports
what a stable release still needs; it never builds, tags or publishes.

**Before committing.** Run `make -j4 check`; shortcuts and local setup are in
[docs/develop/development.md](../docs/develop/development.md).

When adding or removing a script, update this index and put the detail in the
script's docstring or sub-README rather than growing this page. Name directories
by subject and keep the `gen_*` prefix on scripts that generate assets.
