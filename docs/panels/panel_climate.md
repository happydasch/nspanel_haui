---
title: Panel Climate
description: Climate panel configuration and options
---

# Panel Climate
## About

`type: climate`

The climate panel controls a single climate/HVAC entity — temperature setpoint adjustment, HVAC mode selection, fan modes, swing modes, and presets. All available HVAC modes are shown as icons at the bottom of the panel.

<!-- TODO: Add screenshot at ../assets/screenshots/panel-climate.png once screenshot generation script is implemented -->

## Popup

`type: popup_climate`

`key: popup_climate_key`

The popup variant mirrors the main panel and is used when a climate entity is assigned as an item on another panel.

## Controls

| Widget | Description |
|--------|-------------|
| **Temperature display** | Large current temperature reading with unit (°C). |
| **Temperature up/down** | Buttons to increase/decrease the target temperature setpoint. |
| **Title** | Displays the entity's friendly name and current target temperature. |
| **Power toggle** | Header button to turn the climate entity on/off. |
| **HVAC mode row** | Bottom row of mode icons (heat, cool, auto, dry, fan_only, etc.). Shows modes available on the entity. |
| **Fan mode button** | Opens a popup to select fan mode. Visible when entity supports `fan_mode`. |
| **Swing mode button** | Opens a popup to select swing mode. Visible when entity supports `swing_mode`. |
| **Preset button** | Opens a popup to select a preset. Visible when entity supports `preset_mode`. |

## Config

### Item

`key: item` | `kind: item` | `domain: climate`

The climate/HVAC entity to control. Required.

### HVAC modes

`key: hvac_modes` | `kind: list_items` | `default: [] (auto-detect)`

Override the set of HVAC modes shown on the panel. Available choices:

- `off` — Off
- `heat` — Heat
- `cool` — Cool
- `heat_cool` — Heat/Cool
- `auto` — Auto
- `dry` — Dry
- `fan_only` — Fan Only

If not set, the panel auto-detects supported modes from the entity's `hvac_modes` attribute.

## Display Behavior

- The **title** shows the entity's friendly name and the current target temperature.
- The large center display shows the current temperature from the entity's `current_temperature` attribute.
- HVAC mode buttons auto-hide/show based on supported modes (or the `hvac_modes` override).
- When the target temperature is adjusted, the new setpoint is sent via the `set_temperature` service.
- Fan mode, swing mode, and preset each open a selection popup when tapped.
- The panel uses climate-specific color theming defined in `haui/mapping/color.py`.
