---
title: Panel Climate
description: Climate panel — HVAC control with temperature setpoint and mode selection
---

# Panel Climate

![](../assets/previews/panel-climate.svg)

## About

The climate panel controls a single climate/HVAC entity — temperature setpoint adjustment, HVAC mode selection, fan modes, swing modes, and presets. All available HVAC modes are shown as icons at the bottom of the panel.

## Popup Variant

The popup variant (`popup_climate`) mirrors the main panel layout. It is used automatically when a climate entity is assigned as an item on another panel.

## Controls

| Widget | Description |
|--------|-------------|
| **Temperature display** | Large current temperature reading with unit (°C). |
| **Temperature up/down** | Buttons to increase/decrease the target temperature setpoint. |
| **Title** | Displays the entity's friendly name and current target temperature. |
| **Power toggle** | Header button to turn the climate entity on/off. |
| **HVAC mode row** | Bottom row of mode icons (heat, cool, auto, dry, fan_only, etc.). Shows modes available on the entity. |
| **Fan mode button** | Opens a popup to select fan mode. Visible when entity supports fan modes. |
| **Swing mode button** | Opens a popup to select swing mode. Visible when entity supports swing modes. |
| **Preset button** | Opens a popup to select a preset. Visible when entity supports presets. |

## How to configure

In the **panel editor**, set:

- **Item** (entity picker) — A climate/HVAC entity to control. Required.
- **HVAC modes** (multi-select list) — Override the set of HVAC modes shown on the panel. Available choices: Off, Heat, Cool, Heat/Cool, Auto, Dry, Fan Only. If not set, the panel auto-detects supported modes from the entity.

## Display Behavior

- The **title** shows the entity's friendly name and the current target temperature.
- The large center display shows the current temperature from the entity.
- HVAC mode buttons auto-hide/show based on supported modes (or the override).
- When the target temperature is adjusted, the new setpoint is sent via the `set_temperature` service.
- Fan mode, swing mode, and preset each open a selection popup when tapped.
