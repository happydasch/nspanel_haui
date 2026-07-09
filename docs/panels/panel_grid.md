---
title: Panel Grid
description: Grid panel configuration and options
---

# Panel Grid
## About

`type: grid`

The entities grid panel provides a panel with 6 big buttons. If more than 6 entities are provided, the entities can be scrolled.

This panel can be also used to organize panels and subpanels. Colors can be set for the individual tiles.

## Config

### Per-Item Color Overrides

Each entity in the grid can have optional color and appearance overrides.
Set any of these on individual entities to override the default theme colors:

- `text_color` — Text and icon color for the tile
- `back_color` — Background color of the tile
- `color_pressed` — Text/icon color when pressed
- `back_color_pressed` — Background color when pressed
- `power_color` — Color for the power toggle button
- `show_power_button` — Set to `true` to show a power on/off toggle button



If more than 6 entities are configured, a next-page button appears. The panel
remembers which page you last viewed and returns to it on revisit — this is
automatic, not configurable.
