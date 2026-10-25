# Nextion Display Assets

This directory contains display-related assets for the NSPanel HAUI device:

| File / Directory | Purpose |
|------------------|---------|
| `nspanel_haui.tft` | Compiled Nextion display firmware — the UI file installed on the panel's display |
| `nspanel_haui.HMI` | Nextion Editor source project (for customization) |
| `nspanel_haui_portrait.HMI` | Nextion Editor source project of the portrait layout, patched from `nspanel_haui.HMI` with `scripts/gen_portrait/gen_portrait.py` |
| `nspanel_haui_portrait.tft` | **US-model portrait layout** — compiled from `nspanel_haui_portrait.HMI` (see [Display Models](../docs/configuration/display-models.md)) |
| `fonts/` | `.zi` fonts for the Nextion Editor's font list, generated with `scripts/gen_fonts/`; the HMI projects embed Roboto-Regular (20, 24, 32, 48, 72, 164) and Roboto-Light (72, 96, 128, 164) |
| `images/` | Image assets used by the display; `bkg/landscape/` (480 × 320) and `bkg/portrait/` (320 × 480) hold the generated background tiles; `grid_landscape.png` / `grid_portrait.png` are the editor design-aid grids from `scripts/gen_grid/gen_grid.py`; `spinner_<orientation>_1.png` / `_2.png` are the system page's spinner sheets from `scripts/gen_spinner/gen_spinner.py` |
| `src_images/` | Source pictures the image assets are made from: Pixelmator (`.pxd`) page and logo designs, and `bkg/` with the background sources, rendered with `scripts/gen_backgrounds/gen_backgrounds.py` |

The TFT file is installed automatically by the Hub app when the device connects with an outdated TFT. To install it by hand, use **Device Manager → Install TFT** in the editor or press the device's **Update Display** button in Home Assistant.

## Display model variants

`nspanel_haui.tft` is the landscape layout used by the EU NSPanel and by a US
panel mounted horizontally.  The **US panel mounted vertically** (portrait,
buttons below the screen) needs `nspanel_haui_portrait.tft`. Its project,
`nspanel_haui_portrait.HMI`, holds the same widgets as `nspanel_haui.HMI` with
the 320 × 480 layout applied by `scripts/gen_portrait/gen_portrait.py`; the
release workflow attaches both TFTs to every GitHub release (see
[Display Models](../docs/configuration/display-models.md) and the
[Nextion Editor human guide](../docs/nextion-editor.md) for the portrait-TFT
workflow).
The Hub app selects the asset per device via the device's `display_model`
setting.

## ESPHome Configuration

All ESPHome device configuration files (YAML scripts, packages, and build configs) have moved to the [`esphome/`](../esphome/README.md) directory.

For documentation about the ESPHome device configuration see:

- [ESPHome Configuration](../docs/esphome.md)
- [`esphome/README.md`](../esphome/README.md)
