---
title: Display Models
description: EU vs US NSPanel hardware, TFT layout selection, and updating
---

# Display Models

The Sonoff NSPanel is sold in regional hardware variants whose displays are
mounted differently.  The integration needs to know which variant a device is
so the correct TFT layout is kept on the display.

## Which model do I have?

| Model | Display mounting | TFT layout |
|-------|------------------|------------|
| **EU (default)** | Landscape — both the EU panel (buttons below) and the US panel mounted horizontally (buttons at the right) | Landscape (`nspanel_haui.tft`) |
| **US (portrait)** | The US panel mounted vertically (buttons below the screen) | Portrait, rotated (`nspanel_haui_portrait.tft`) |

The landscape layout covers every horizontally mounted panel regardless of
regional hardware: a US panel mounted landscape is functionally identical to
the EU default (same TFT, same gesture dimensions) and is configured with the
default `European (standard)` option.  The EU screen has a slightly smaller
visible area (the rightmost ~30 pixels of the TFT are hidden behind the
bezel); the layouts shipped by this project are designed to stay safe there.

## Gestures on every model

Edge-swipe gestures (swipe left/right/up/down from the screen border) use the
touch dimensions of the installed model so the margins match the visible edge
on landscape **and** portrait panels.  The hub syncs the device's
`display_model` to the firmware's `Display Model` number on every connect
(0 = landscape, 1 = portrait); the gesture script reads it at runtime, so no
per-model firmware build is needed.

## Selecting the model

In **Device Settings → General Settings → Display Model** choose the entry that
matches your hardware:

- `European (standard)` — the default landscape layout, for the EU panel and
  for a US panel mounted horizontally (landscape).
- `US (portrait)` — US hardware mounted vertically; requires the rotated
  portrait TFT.

The editor's panel previews follow this setting: with a portrait device
selected, every panel card shows the 320 × 480 layout with the function
buttons at the bottom of the screen, as on the rotated TFT.

Saving a changed model installs the matching TFT right away (the display
cannot report which layout it runs, so the version check alone would keep the
old layout). The firmware's **Update Display** button and its `upload_tft`
action pick the landscape or the portrait file by the same setting, which the
hub mirrors into the device's *Display Model* number on every connect.

## How updates pick the right TFT

The auto-update controller downloads the display firmware (the `.tft` file)
matching the **integration version the firmware needs** from the GitHub
release.  When a device's `display_model` is set, the controller asks the
release for the matching asset:

| `display_model` | Asset requested |
|-----------------|-----------------|
| `eu` (default) | `nspanel_haui.tft` |
| `us` | `nspanel_haui_portrait.tft` |

!!! note
    The ESPHome firmware (`.yaml`/`.bin`) is **identical** for all models —
    only the display layout (`.tft`) differs.  No `rotation` setting is needed;
    the portrait layout is a separate asset compiled from the Nextion project.

## Building the portrait TFT (maintainers)

Every release carries both TFTs. How the portrait project is generated and
compiled is described in the [Nextion Editor guide](../nextion-editor.md#7-creating-the-us-portrait-tft).
