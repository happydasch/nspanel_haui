# Nextion Display Assets

Display firmware and source assets for the NSPanel.

| File | What it is |
|------|------------|
| `nspanel_haui.tft` | Landscape display firmware (EU panel, or US panel mounted horizontally) |
| `nspanel_haui.HMI` | Nextion Editor source for the landscape layout |
| `nspanel_haui_portrait.tft` | Portrait display firmware (US panel mounted vertically) |
| `nspanel_haui_portrait.HMI` | Nextion Editor source for the portrait layout, generated from the landscape project with `scripts/hmi_layout/gen_layout.py --spec portrait` |

`fonts/` holds the `.zi` fonts for the Nextion Editor, `images/` the pictures used
on the display (backgrounds, spinner frames, design grids) and `src_images/` the
Pixelmator sources they are rendered from.

The hub installs TFTs itself: use the **HAUI Display** update entity or **Display
(TFT)** in the editor's **Updates** sidebar. To install your own build, pass its URL
to the [TFT update action](../docs/user/actions.md).

Both TFTs are attached to every GitHub release. The hub picks the one for a device
from its `display_model` setting — see
[Display Models](../docs/user/editor/display-models.md) and the
[Nextion Editor guide](../docs/develop/nextion-editor.md).

Everything here is a build input, not runtime data: `.gitattributes` marks
`nextion/` `export-ignore`, so GitHub's source archives (the zip HACS installs)
leave it out while `raw.githubusercontent.com` and the release assets keep serving
the TFTs. Never put a file the integration reads at runtime in this directory.

ESPHome device configuration lives in [`esphome/`](../esphome/README.md).
