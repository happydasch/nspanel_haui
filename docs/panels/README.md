---
title: Panel Overview
description: Overview of all available panel types for NSPanel HAUI
---

# Panel Overview

All panels are configured through the visual editor in Home Assistant. See the [Configuration Overview](../configuration/README.md) for how to use the editor.

NSPanel HAUI supports **13 panel types** plus **system panels** and **popups**. The [Screens overview](../screens.html) shows every one of them in the landscape and portrait layout. Panels are categorized by purpose:

- **Entity Controls** — Control a single Home Assistant entity (light, climate, cover, etc.)
- **Multi-Entity** — Display and control multiple entities at once
- **Screensavers** — Full-screen displays for idle/sleep mode
- **Utility** — Special-purpose panels (timer, QR, alarm)
- **System** — Always-available built-in panels (no configuration needed)

---

## Screensaver Panels

Panels that can be used as screensavers / idle display. These panels do not show navigation by default.

| Preview | Panel | Type | Description |
|---------|-------|------|-------------|
| <a href="panel_weather.md"><img src="../assets/screens/landscape/weather.png" alt="weather panel" width="120" height="85"></a> | [Weather](panel_weather.md) | `weather` | Weather forecast, time/date, optional background images. Supports up to two info items. |
| <a href="panel_clock.md"><img src="../assets/screens/landscape/clock.png" alt="clock panel" width="120" height="85"></a> | [Clock](panel_clock.md) | `clock` | Large time/date display with optional weather, background, and entity buttons. |
| <a href="panel_clocktwo.md"><img src="../assets/screens/landscape/clocktwo.png" alt="clocktwo panel" width="120" height="85"></a> | [ClockTwo](panel_clocktwo.md) | `clocktwo` | Word clock showing the time by highlighting letters (e.g., "IT IS HALF PAST TWELVE"). |

---

## Multi-Entity Panels

Panels that show multiple entities in a navigation-enabled layout.

| Preview | Panel | Type | Description |
|---------|-------|------|-------------|
| <a href="panel_grid.md"><img src="../assets/screens/landscape/grid.png" alt="grid panel" width="120" height="85"></a> | [Grid](panel_grid.md) | `grid` | Up to 6 entities arranged in a scrollable grid. Color overrides, power buttons. |
| <a href="panel_row.md"><img src="../assets/screens/landscape/row.png" alt="row panel" width="120" height="85"></a> | [Row](panel_row.md) | `row` | Up to 5 entities as stacked rows, each with an icon, name and a control suited to the entity type. |

---

## Entity Control Panels

Single-entity control panels with full feature support.

| Preview | Panel | Type | Description |
|---------|-------|------|-------------|
| <a href="panel_light.md"><img src="../assets/screens/landscape/light.png" alt="light panel" width="120" height="85"></a> | [Light](panel_light.md) | `light` | Full light control: brightness, color temperature, RGB color wheel, effects. |
| <a href="panel_media.md"><img src="../assets/screens/landscape/media.png" alt="media panel" width="120" height="85"></a> | [Media](panel_media.md) | `media` | Media player controls: play/pause, volume, queue. Supports TV, speakers, receivers. |
| <a href="panel_vacuum.md"><img src="../assets/screens/landscape/vacuum.png" alt="vacuum panel" width="120" height="85"></a> | [Vacuum](panel_vacuum.md) | `vacuum` | Robot vacuum controls: start/stop, return home, fan speed, locate. Up to 6 secondary items. |
| <a href="panel_cover.md"><img src="../assets/screens/landscape/cover.png" alt="cover panel" width="120" height="85"></a> | [Cover](panel_cover.md) | `cover` | Cover/blind control: open, stop, close, vertical position slider. |
| <a href="panel_climate.md"><img src="../assets/screens/landscape/climate.png" alt="climate panel" width="120" height="85"></a> | [Climate](panel_climate.md) | `climate` | HVAC control: temperature setpoint, modes (heat/cool/auto), fan speed, swing, presets. |

---

## Utility Panels

Special-purpose panels for non-entity functions.

| Preview | Panel | Type | Description |
|---------|-------|------|-------------|
| <a href="panel_timer.md"><img src="../assets/screens/landscape/timer.png" alt="timer panel" width="120" height="85"></a> | [Timer](panel_timer.md) | `timer` | Local countdown timer with start/pause/stop. Display-local time, no HA entity needed. |
| <a href="panel_qr.md"><img src="../assets/screens/landscape/qr.png" alt="qr panel" width="120" height="85"></a> | [QR Code](panel_qr.md) | `qr` | Display QR codes for Wi-Fi details, URLs, or custom text. |
| <a href="panel_alarm.md"><img src="../assets/screens/landscape/alarm.png" alt="alarm panel" width="120" height="85"></a> | [Alarm](panel_alarm.md) | `alarm` | Numeric keypad for alarm code entry. Arm/disarm with mode buttons. |

---

## Popups

Overlay panels used for temporary interactions.

| Popup | Type | Description |
|-------|------|-------------|
| [Unlock](popup_unlock.md) | `popup_unlock` | PIN-protected unlock for locked panels. Built on `AlarmPage`. |
| [Notify](popup_notify.md) | `popup_notify` | Ad-hoc notification popup with optional action buttons. |
| [Select](popup_select.md) | `popup_select` | Selection list popup for choosing values (fan speeds, presets, etc.). |

Popup variants of entity panels (`popup_light`, `popup_media_player`, `popup_vacuum`, `popup_climate`, `popup_timer`, `popup_cover`, `popup_alarm`) mirror their main panel layout. They and the other popups (Notify, Select, Unlock) can be edited in the editor's **Popups** section (see [System Panel Overrides](../configuration/panels.md#system-panel-overrides)). A panel you add yourself is never a popup: out of navigation it is a stacked panel, whatever its type. Both open on top of the current panel with up, home and close in the header (see [Stacked Panels and Popups](../configuration/panels.md#stacked-panels-and-popups)).

---

## System Panels

Always available, no configuration needed. Unlike the popups above they cannot be edited.

| Panel | Type | Description |
|-------|------|-------------|
| [Blank](panel_blank.md) | `sys_blank` | Blank/empty panel you can use as the idle page. |
| [System](panel_system.md) | `sys_system` | Loading/error panel. Automatically shown when the device loses connection. |
| [Settings](panel_settings.md) | `sys_settings` | Device settings panel (brightness, dimming, sounds, etc.). |
| [About](panel_about.md) | `sys_about` | Device and version information panel. |
