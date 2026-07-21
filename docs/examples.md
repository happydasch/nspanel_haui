---
title: Example Configurations
description: Example configurations and usage patterns for NSPanel HAUI panels
---

# Example Configurations

While all configuration is done through the Home Assistant UI editor, here are some common usage patterns to help you structure your display layouts.

Configuration is done via the **NSPanel HAUI** device page in **Settings → Devices & Services** → your device → **Panels** tab.

---

## Pattern 1: Clock Screensaver + Entity Grid

A common setup: the display starts on a clock/weather screensaver, swiping navigates to a grid of daily controls.

```
Panel 1:  Clock or Weather   (screensaver)
Panel 2:  Grid               (light, switch, sensor, etc.)
Panel 3:  Light              (main room light with dimming)
Panel 4:  Cover              (window blinds)
```

**Device settings:**
- **Home panel:** `panel_1` (the clock)
- **Auto-dim:** Enabled, with the clock as the idle page
- **Swipe left/right:** Navigate between panels

---

## Pattern 2: Weather Dashboard

Use the weather panel as an information hub.

```
Panel 1:  Weather            (screensaver)
  → Weather entity, daily forecast
  → Info items: indoor temp, humidity, CO2
  → Entity buttons: toggle bedroom light, toggle porch light
```

**Background:** Set to `spring` or `modern` for visual appeal. Use a template for dynamic backgrounds: `background: template:{'dark' if is_state('sun.sun', 'below_horizon') else 'modern'}`

---

## Pattern 3: Living Room Control Hub

For a media-focused room:

```
Panel 1:  Grid               (lights, plugs, scene toggles)
Panel 2:  Light              (main light with brightness + RGB)
Panel 3:  Media              (TV/speaker controls)
Panel 4:  Climate            (AC/heating thermostat)
```

**Color scheme:** Match the room ambiance with warm accent colors (`header_accent: #f69d31`).

---

## Pattern 4: Bedroom Control

Minimalist bedroom setup with night-use consideration:

```
Panel 1:  ClockTwo           (time as text — easier to read at night)
Panel 2:  Light              (bedside lamp, dimmed to warm white)
Panel 3:  Grid               (alarm, do-not-disturb toggle, fan)
```

**Device settings:**
- **Dim level:** Low (10-20%) for nighttime
- **Screensaver timeout:** 15 seconds

---

## Pattern 5: Security & Utility

For a hallway or entrance area:

```
Panel 1:  Clock              (time, temp, weather)
Panel 2:  Alarm              (arm/disarm the alarm system)
Panel 3:  QR                 (Wi-Fi guest network QR code)
Panel 4:  Grid               (outdoor lights, door lock, camera)
```

**Panel locking:** Enable lock on the alarm panel to require PIN for arm/disarm.

---

## Pattern 6: Kitchen Helper

```
Panel 1:  Weather            (morning glance)
Panel 2:  Timer              (cooking timer)
Panel 3:  Grid               (kitchen lights, coffee machine, extractor fan)
Panel 4:  Media              (kitchen speaker / radio)
```

**Timer notification:** Enable `show_notification: true` so the timer alerts visually when cooking is done.

---

## See Also

- [Panel Configuration](configuration/panels.md) — Available panel options
- [Panels Overview](panels/README.md) — Details on each panel type
- [Device Configuration](configuration/device.md) — Gestures, dimming, navigation
