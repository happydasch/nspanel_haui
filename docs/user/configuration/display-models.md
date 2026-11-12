---
title: Display Models
description: EU vs US NSPanel hardware, TFT layout selection, and updating
---

# Display Models

The NSPanel exists in an EU and a US version. What matters for NSPanel HAUI is how the panel is mounted, because the display needs a layout for that direction.

## Which model do I have?

| Setting | Mounting | Layout |
|---------|----------|--------|
| **European (standard)** — the default | Landscape: the EU panel (buttons below the screen) and a US panel mounted horizontally (buttons on the right) | Landscape, 480 × 320 |
| **US (portrait)** | A US panel mounted vertically (buttons below the screen) | Portrait, 320 × 480 |

A US panel mounted in landscape works exactly like an EU panel, so it uses the default setting.

## Selecting the model

1. Open the device's **Settings**.
2. Under **General Settings**, set **Display Model**.
3. Select **Save**. The editor asks whether to install the matching display file (TFT) now.

If you answer no, the display keeps its current layout until you install the TFT yourself with **Install** beside **Display** in the **Updates** sidebar. The display cannot report which layout it has, so the hub does not notice a wrong one on its own.

What follows the setting:

- **The editor** shows every panel picture and the live preview in the layout of the selected model.
- **Updates** install the landscape or the portrait TFT, whichever matches.
- **Gestures** use the screen edges of the selected model.

!!! note
    The firmware is the same for all models. Only the display file (TFT) differs, and every release includes both.

## For maintainers

The hub requests `nspanel_haui.tft` for `eu` and `nspanel_haui_portrait.tft` for `us`. How the portrait file is built is described in the [Nextion Editor guide](../../develop/nextion-editor.md#7-creating-the-us-portrait-tft).
