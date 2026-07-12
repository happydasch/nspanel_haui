---
title: Panel Vacuum
description: Vacuum panel configuration and options
---

# Panel Vacuum
## About

`type: vacuum`

The vacuum panel controls a vacuum/mop robot entity with start/stop, return-to-base, fan speed selection, and locate commands. Up to 6 secondary entities can be displayed as quick-action buttons below the main controls.

<!-- TODO: Add screenshot at ../assets/screenshots/panel-vacuum.png once screenshot generation script is implemented -->

## Popup

`type: popup_vacuum`

`key: popup_vacuum_key`

The popup variant mirrors the main panel layout and is used when a vacuum is assigned as an item on another panel.

## Controls

| Widget | Description |
|--------|-------------|
| **Action button** | Start cleaning (docked/idle) or pause (cleaning/returning). Icon changes dynamically. |
| **Home button** | Return to charging dock. Visible when the entity supports `return_home`. Disabled when already docked. |
| **Fan button** | Opens a fan speed selection popup. Visible when the entity supports `fan_speed`. |
| **Locate button** | Triggers the locate/sound alarm on the vacuum. Visible when the entity supports `locate`. |
| **Status text** | Shows the current state label (e.g., "Cleaning", "Docked", "Returning", "Idle") |
| **Battery indicator** | Header icon shows battery level. Visible when the entity supports `battery`. |
| **Secondary items** | Up to 6 additional entity buttons below the main controls, configured via `items`. |

## Config

### Item

`key: item` | `kind: item` | `domain: vacuum`

The vacuum entity to control. Required.

### Secondary Items

`key: items` | `kind: item_list` | `max_items: 6`

Additional entities to display as quick-action tiles below the vacuum controls. Useful for sensors (e.g., filter status, mop state) or toggles.

### Fan Speed

If the vacuum entity supports fan speeds, tapping the fan button opens a selection popup listing the available speed settings. Selecting a speed calls `set_fan_speed`.

## Display Behavior

- The **title** defaults to the entity's friendly name.
- Buttons are shown or hidden based on the entity's `supported_features` attribute.
- Start/pause/stop icon changes dynamically based on the vacuum state.
- The battery icon is shown in the header when the entity reports battery level.
