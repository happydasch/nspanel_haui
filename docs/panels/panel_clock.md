---
title: Panel Clock
description: Clock panel configuration and options
---

# Panel Clock
## About

`type: clock`

The clock panel displays a large digital time with optional date, outside/inside temperature, and weather information. The center display area cycles through up to 4 configurable cards every 5 seconds, and can be tapped to manually advance.

Up to 6 entity buttons can be shown at the bottom for quick action access.

## Config

```yaml
panels:

  # simple clock
  - type: clock
    entity: weather.home

  # clock with a different background, weather icon color, and home temp
  - type: clock
    entity: weather.home
    background: modern
    weather_icons: monochrome
    show_home_temp: True

  # clock with only time and entity buttons, no weather
  - type: clock
    show_weather: False
    show_temp: False
    show_notifications: False
    items:
      - entity: light.living_room
      - entity: switch.coffee_maker
      - entity: fan.ceiling

  # clock with custom cycle cards
  - type: clock
    entity: weather.home
    show_time_date: True
    show_time_outside_temp: True
    show_time_inside_temp: False
    items:
      - entity: light.kitchen
      - entity: sensor.outside_humidity
```

### Background

The clock panel can have different background images. To set a background use the `background` param.

Possible values:

- dark
- modern
- spring
- summer
- autumn
- winter
- dog_1
- dog_2
- cat

Dynamic background values are possible using HomeAssistant templates.

`background: template:{...}`

The return value should match a background name.

### Cycle Cards

The center area cycles through enabled cards every 5 seconds. Tap the time area to advance to the next card immediately.

| Option | Default | Description |
|--------|---------|-------------|
| `show_time_time` | `True` | Show current time (HH:MM) with the date below it |
| `show_time_date` | `True` | Show a separate date card (e.g. "Mon 16") |
| `show_time_outside_temp` | `True` | Show outside temperature from the weather entity |
| `show_time_inside_temp` | `False` | Show NSPanel internal temperature |

The date is always shown below the time when the time card is active, regardless of `show_time_date`. The `show_time_date` option only controls whether a separate dedicated date card is added to the rotation.

If no cards are enabled, the time card is shown as a fallback.

### Weather

To display weather information, set a weather entity using the `entity` option.

| Option | Default | Description |
|--------|---------|-------------|
| `entity` | — | Weather entity (e.g. `weather.home`) |
| `show_weather` | `True` | Show the weather condition icon |
| `show_temp` | `True` | Show temperature and pressure text |
| `show_home_temp` | `False` | Show NSPanel internal temperature alongside the weather |
| `weather_icons` | `color` | Icon style: `color` (condition-based) or `monochrome` |
| `items` | — | Up to 6 entity buttons for quick actions (see below) |

### Item Buttons

Up to 6 quick-action buttons can be placed at the bottom of the clock using the `items` list:

```yaml
items:
  - entity: light.living_room
  - entity: switch.coffee_maker
  - entity: fan.ceiling
```

### Show Notifications

The notifications icon can be hidden by setting `show_notifications` to `False`.
