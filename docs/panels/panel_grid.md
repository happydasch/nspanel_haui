# Panel Grid

[< All Panels](README.md) | [Configuration](../Config.md) | [FAQ](../FAQ.md)

- [Panel Grid](#panel-grid)
  - [About](#about)
  - [Config](#config)
    - [Per-Item Color Overrides](#per-item-color-overrides)
    - [Initial Page `initial_page`](#initial-page-initial_page)
  - [Screens](#screens)

## About

`type: grid`

The entities grid panel provides a panel with 6 big buttons. If more than 6 entities are provided, the entities can be scrolled.

This panel can be also used to organize panels and subpanels. Colors can be set for the individual tiles.

## Config

```yaml
# Default config
panels:
  - type: grid
    initial_page: 0
    entities:
      - entity: light.example_light
        text_color: null
        power_color: null
        back_color: null
        back_color_pressed: null
        color_pressed: null
        show_power_button: null
```

Example config with 7 entities:

```yaml
panels:
  - type: grid
    entities:
      - entity: light.example_light
      - entity: light.example_light1
      - entity: light.example_light2
      - entity: light.example_light3
      - entity: light.example_light4
      - entity: light.example_light5
      - entity: light.example_light6
```

### Per-Item Color Overrides

Each entity in the grid can have optional color and appearance overrides.
Set any of these on individual entities to override the default theme colors:

- `text_color` — Text and icon color for the tile
- `back_color` — Background color of the tile
- `color_pressed` — Text/icon color when pressed
- `back_color_pressed` — Background color when pressed
- `power_color` — Color for the power toggle button
- `show_power_button` — Set to `true` to show a power on/off toggle button

```yaml
panels:
  - type: grid
    entities:
      - entity: light.example_light
        text_color: 6339
        back_color: 12678
        show_power_button: true
      - entity: light.example_light1
```

### Initial Page `initial_page`

The page to start the üanel with can be set with  `initial_page`.

```yaml
# grid panel with 7 entities and a inital page
panels:
  - type: grid
    initial_page: 1
    entities:
      - entity: light.example_light
      - entity: light.example_light1
      - entity: light.example_light2
      - entity: light.example_light3
      - entity: light.example_light4
      - entity: light.example_light5
      - entity: light.example_light6
```

## Screens

![Subpanel Grid](../assets/subpanel_grid.png)

![Panel Grid](../assets/panel_grid.png)

Simple grid (no background, no power button):

![Panel Grid Simple](../assets/panel_grid_simple.png)
