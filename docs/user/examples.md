---
title: Example Configurations
description: Example configurations and usage patterns for NSPanel HAUI panels
---

# Example Configurations

These examples show panel layouts for common rooms. Build them in the **NSPanel HAUI** editor: open your device, switch to **Panels** and add the panels in the order shown.

## Clock screensaver with an entity grid

The display rests on a clock. Swipe to reach the controls you use every day.

| Panel | Type | Shows |
|-------|------|-------|
| 1 | Clock or Weather | Screensaver |
| 2 | Grid | Lights, switches, sensors |
| 3 | Light | The main light, with dimming |
| 4 | Cover | The window blinds |

**Device settings:** set the clock as **Home panel** and as **Idle panel**, and turn on auto dimming and automatic page switching.

## Weather dashboard

One Weather panel as an information hub.

| Panel | Type | Shows |
|-------|------|-------|
| 1 | Weather | Weather entity with the daily forecast, info items for indoor temperature, humidity and CO2 |

**Background:** choose `spring` or `modern`. For a background that follows the time of day, choose **Template…** in the Background field and enter:

```jinja
{{ 'dark' if is_state('sun.sun', 'below_horizon') else 'modern' }}
```

## Living room

For a room with a TV or speakers.

| Panel | Type | Shows |
|-------|------|-------|
| 1 | Grid | Lights, plugs, scenes |
| 2 | Light | The main light with brightness and color |
| 3 | Media | TV or speaker controls |
| 4 | Climate | Heating or air conditioning |

**Colors:** for a warm look, set the `header_accent` tweak to `#f69d31` in the **Theme** sidebar.

## Bedroom

A small setup that is easy on the eyes at night.

| Panel | Type | Shows |
|-------|------|-------|
| 1 | ClockTwo | The time in words |
| 2 | Light | The bedside lamp |
| 3 | Grid | Alarm, do-not-disturb, fan |

**Device settings:**

- Dimmed brightness: 10–20 % (the `number.<device>_brightness_dimmed` entity of the ESPHome device)
- Dimming timeout (`timeout_dimming`): 15 seconds

## Hallway or entrance

| Panel | Type | Shows |
|-------|------|-------|
| 1 | Clock | Time, temperature, weather |
| 2 | Alarm | Arm and disarm the alarm system |
| 3 | QR | QR code for the guest Wi-Fi |
| 4 | Grid | Outdoor lights, door lock, camera |

**Tip:** set a **Panel pin** on the alarm panel, so it asks for a PIN before it opens.

## Kitchen

| Panel | Type | Shows |
|-------|------|-------|
| 1 | Weather | The weather for the day |
| 2 | Timer | Cooking timer |
| 3 | Grid | Kitchen lights, coffee machine, extractor fan |
| 4 | Media | Kitchen speaker or radio |

**Tip:** turn on **Show Notification** on the timer panel to get a popup when the timer ends.

## See also

- [Panels overview](panels/README.md) — every panel type
- [Panel Configuration](configuration/panels.md) — the fields every panel has
- [Device Configuration](configuration/device.md) — home panel, idle panel, dimming, gestures
