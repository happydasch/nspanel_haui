# Layout generation tools

This directory contains the scripts that generate or maintain the NSPanel screen layouts. The HMI files remain the source of truth for widget names, IDs, event code, fonts, and pictures; the Python specs describe reproducible geometry and selected attributes.

## Tools

### `gen_layout.py` — patch and verify HMI layouts

Applies a layout spec to a Nextion `.HMI` project in place without changing record sizes or offsets. It also refreshes the editor's per-page content stamp. The default `landscape` spec applies the partial 480 × 320 refinements to `nspanel_haui.HMI`; `--spec portrait` applies the complete 320 × 480 geometry to `nspanel_haui_portrait.HMI`.

```bash
python -m scripts.hmi_layout.gen_layout --check                 # landscape (default)
python -m scripts.hmi_layout.gen_layout                           # patch landscape (default)
python -m scripts.hmi_layout.gen_layout --spec portrait --check
python -m scripts.hmi_layout.gen_layout --spec portrait
```

The specs are `landscape_layout.py` (the default) and `portrait_layout.py` (`--spec portrait`); `theme.py` provides shared theme-colour attributes. Keep widget coverage and sibling-HMI parity intact. Close the project in Nextion Editor before patching: the editor can overwrite an externally modified HMI when it closes an open project.

### `gen_virtual_layout.py` — export virtual-panel assets

Reads both HMIs and writes the editor's virtual display layouts, preview pictures, icon map, and hub font metrics. Its `--check` mode verifies that the generated files are current and checks theme code and other preview asset constraints.

```bash
python -m scripts.hmi_layout.gen_virtual_layout
python -m scripts.hmi_layout.gen_virtual_layout --check
python -m scripts.hmi_layout.gen_virtual_layout --theme-code [PAGE ...]
```

Run this after HMI changes and after compiling/reviewing the HMIs in Nextion Editor. The generated files live under `custom_components/nspanel_haui/frontend/virtual/` and `custom_components/nspanel_haui/haui/mapping/font_metrics.json`.

## Typical HMI workflow

1. Edit and compile the HMI in Nextion Editor. Close the project before running scripts that patch an HMI.
2. Run `gen_layout.py --check` for the landscape HMI (the default), and `gen_layout.py --spec portrait --check` for the portrait HMI. Run either without `--check` to write its spec into the HMI.
3. Re-open and inspect both HMI projects in Nextion Editor; compile both TFTs when either HMI changed.
4. Run `gen_virtual_layout.py` to regenerate editor assets, then run it with `--check` as a validation gate.
5. Run `python -m scripts.verify_nextion.verify_nextion --require-portrait` and the repository test suite before committing.

The scripts have distinct roles: the HMI patcher writes source projects and the virtual-layout exporter reads them to produce derived assets. Do not use the exporter as a substitute for HMI compilation or visual inspection.
