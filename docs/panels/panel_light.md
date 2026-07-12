---
title: Panel Light
description: Light panel configuration and options
---

# Panel Light
## About

`type: light`

The light panel provides full control for a single light entity — brightness, color temperature, RGB color, effects, and power. Only controls for features the entity supports are shown.

<!-- TODO: Add screenshot at ../assets/screenshots/panel-light.png once screenshot generation script is implemented -->

## Popup

`type: popup_light`

`key: popup_light_key`

The popup variant mirrors the main panel layout and is used when a light is assigned as an item on another panel (e.g., grid tile → tap → light popup).

## Controls

| Widget | Description |
|--------|-------------|
| **Power** | On/off toggle button. Shown when the entity supports `turn_on`/`turn_off`. |
| **Brightness Slider** | Adjustable slider (0–100%). Shown when the entity supports `brightness`. |
| **Color Temp Slider** | Adjusts white color temperature. Shown when the entity supports `color_temp`. |
| **Color Wheel** | Tap-and-drag rectangular color picker. Shown when the entity supports `rgb_color` or `xy_color`. |
| **Function Buttons** | Up to 4 context-sensitive buttons below the main controls: effects, color mode, scene cycling, etc. |

## Config

### Item

`key: item` | `kind: item` | `domain: light`

The light entity to control. Required.

### Show Kelvin

`key: show_kelvin` | `kind: bool` | `default: False`

When enabled, color temperature is displayed in Kelvin (e.g., 3500K) instead of Mireds (e.g., 286 mired). Mired is the default Home Assistant unit.

### Per-Item Options

When a light panel is used as a popup from another panel, the parent entity can configure:

- `icon` — Override the light icon
- `name` — Custom display name
- `back_color` — Background color override for the tile

## Display Behavior

- The **title** defaults to the entity's friendly name, configurable via the panel's title setting.
- Controls automatically hide or show based on the light entity's `supported_color_modes` and `supported_features` attributes.
- When the light is off, sliders are disabled and the power button reflects the state.
- The color wheel always appears when RGB/XY color is supported, regardless of other features.
