# Nextion Display Assets

Display firmware and source assets for the NSPanel.

| File | What it is |
|------|------------|
| `nspanel_haui.tft` | Landscape display firmware (EU panel, or US panel mounted horizontally) |
| `nspanel_haui.HMI` | Nextion Editor source for the landscape layout |
| `nspanel_haui_portrait.tft` | Portrait display firmware (US panel mounted vertically) |
| `nspanel_haui_portrait.HMI` | Nextion Editor source for the portrait layout, generated from the landscape project with `scripts/hmi_layout/gen_layout.py --spec portrait` |
| `nspanel_haui_repair.HMI` | Landscape repair project — one page drawing "Repair" and carrying `system.tftVersion`, per [the repair TFTs](../docs/develop/nextion-editor.md#the-repair-tfts) |
| `nspanel_haui_repair.tft` | Compiled from it; the file the hub installs first on a landscape (`eu`) display whose own TFT cannot be installed |
| `nspanel_haui_repair_portrait.HMI` | Portrait repair project, the same single page at 320 × 480 |
| `nspanel_haui_repair_portrait.tft` | Compiled from it; the portrait (`us`) repair file |

The repair pair is not a second set of release builds: one page instead of thirteen, no pictures, and
two subset fonts (`repair_body.zi` 12,906 bytes and `repair_title.zi` 57,137) instead of the full Roboto
faces, so each file is 465 KB against the release TFT's 11.5 MB — small enough that a display which is
half-written or running at another baud can always take it. A release publishes them — with the
`repair` block of `firmware-manifest.json` that the hub's **Repair display** action reads — only while
both files are committed here and pass `python -m scripts.verify_nextion.check_repair_tft`.
That check's `[OK]` does not prove the version it looks for, because `REPAIR_VERSION` is `"1"`; read
`system.tftVersion` back out of the two projects as the guide shows.

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
