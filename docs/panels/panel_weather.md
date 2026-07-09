---
title: Panel Weather
description: Weather panel configuration and options
---

# Panel Weather
## About

`type: weather`

The weather panel can be used as a "screensaver". It will show weather details and other configured information.

## Config

### Info Items

Additional sensor entities can be shown as info panels below the main weather data using `info_items`. Max 2 items.



### Entity Buttons

Quick-action buttons can be placed below the weather display using `entity_buttons`. Max 6 items.



### Background

The weather panel can have different background images. To set a background use the `background` param.

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

### Show forecast

To get weather forecasts on the panel set `forecast_type` to `daily` or `hourly`.

### Show weather

The main weather icon can be hidden by setting `show_weather` to `False`.

### Show temperature

The main temperature text can be hidden by setting `show_temp` to `False`.
To add the home temperature `show_temp` and `show_home_temp` needs to be `True`.

### Show Notifications

The notifications icon can be hidden by setting `show_notifications` to `False`.
