---
title: Panel Weather
description: Weather panel — screensaver with weather, info items, and entity buttons
---

# Panel Weather

![](../assets/previews/panel-weather.svg)

## About

The weather panel can be used as a screensaver. It displays weather details, time/date, and optional background images. Additional info items and entity buttons can be placed below the weather display.

## How to configure

In the **panel editor**, set:

**Item** (entity picker) — A weather entity to display. Required.

### Info Items

Additional sensor entities can be shown as info panels below the main weather data. You can add up to 2 info items. Common uses: indoor temperature, humidity, CO2 level.

### Entity Buttons

Quick-action buttons can be placed below the weather display. You can add up to 6 entity buttons. Each button uses the standard entity picker.

### Background

The weather panel can have different background images. Select from the dropdown in the editor:

- Dark — a clean dark theme
- Modern — modern gradient
- Spring — floral theme
- Summer — warm theme
- Autumn — fall colors
- Winter — cold theme
- Dog 1, Dog 2, Cat — pet-themed backgrounds

For dynamic backgrounds, you can use a Home Assistant template in the background field: `template:{{ 'dark' if is_state('sun.sun', 'below_horizon') else 'modern' }}`. The return value should match a background name listed above.

### Show Forecast

Toggle **Daily** or **Hourly** forecast display in the editor.

### Show Weather

Toggle the main weather icon on/off.

### Show Temperature

Toggle the main temperature text. When **Show Home Temperature** is also enabled, the NSPanel's internal temperature is shown alongside the weather.

### Show Notifications

Toggle the notifications icon on/off.
