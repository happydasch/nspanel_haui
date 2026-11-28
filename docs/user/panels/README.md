---
title: Panel Types
description: All panel types available for NSPanel HAUI
---

# Panel Types

A panel is one screen on the display. There are **14 panel types** you can add, plus built-in popups and system panels. The **Add panel** catalog groups the types under **Backgrounds**, **Entities**, **Grouping** and **Tools**, and also lists **Extend a popup** and **Copy an existing panel**. Select a panel below to read what it shows and which options it has.

You add panels in the editor, see the [Editor overview](../editor/README.md). The [Screens overview](../screens.md) shows every panel in the landscape and the portrait layout.

## Backgrounds

Full-screen panels without header buttons. They work well as the home panel or as the idle panel.

| Preview | Panel | Type | Shows |
|---------|-------|------|-------|
| <a href="panel_weather.md"><img src="../../assets/screens/landscape/weather.png" alt="weather panel" width="120" height="85"></a> | [Weather](panel_weather.md) | `weather` | Current weather, a forecast, the time and up to two extra values |
| <a href="panel_clock.md"><img src="../../assets/screens/landscape/clock.png" alt="clock panel" width="120" height="85"></a> | [Clock](panel_clock.md) | `clock` | A large time and date, optional weather and up to six buttons |
| <a href="panel_clocktwo.md"><img src="../../assets/screens/landscape/clocktwo.png" alt="clocktwo panel" width="120" height="85"></a> | [ClockTwo](panel_clocktwo.md) | `clocktwo` | The time in words, for example "IT IS HALF PAST TWELVE" |

## Grouping

Panels that show and control several entities at once.

| Preview | Panel | Type | Shows |
|---------|-------|------|-------|
| <a href="panel_grid.md"><img src="../../assets/screens/landscape/grid.png" alt="grid panel" width="120" height="85"></a> | [Grid](panel_grid.md) | `grid` | Six tiles per page, each with an icon and a name |
| <a href="panel_row.md"><img src="../../assets/screens/landscape/row.png" alt="row panel" width="120" height="85"></a> | [Row](panel_row.md) | `row` | Five rows per page, each with a control that fits the entity: toggle, slider, buttons or a value |

## Entities

Panels that control a single entity in full.

| Preview | Panel | Type | Controls |
|---------|-------|------|----------|
| <a href="panel_light.md"><img src="../../assets/screens/landscape/light.png" alt="light panel" width="120" height="85"></a> | [Light](panel_light.md) | `light` | Brightness, color temperature, color and effects |
| <a href="panel_media.md"><img src="../../assets/screens/landscape/media.png" alt="media panel" width="120" height="85"></a> | [Media](panel_media.md) | `media` | Playback, volume, sources and speaker groups of a media player |
| <a href="panel_vacuum.md"><img src="../../assets/screens/landscape/vacuum.png" alt="vacuum panel" width="120" height="85"></a> | [Vacuum](panel_vacuum.md) | `vacuum` | Start, stop, return to dock, fan speed and locate |
| <a href="panel_cover.md"><img src="../../assets/screens/landscape/cover.png" alt="cover panel" width="120" height="85"></a> | [Cover](panel_cover.md) | `cover` | Open, stop, close and a position slider |
| <a href="panel_climate.md"><img src="../../assets/screens/landscape/climate.png" alt="climate panel" width="120" height="85"></a> | [Climate](panel_climate.md) | `climate` | Target temperature, modes, fan, swing and presets |
| <a href="panel_camera.md"><img src="../../assets/screens/landscape/camera.png" alt="camera panel" width="120" height="85"></a> | [Camera](panel_camera.md) | `camera` | One camera's picture, refreshed on the display |

## Tools

Panels for special tasks.

| Preview | Panel | Type | Shows |
|---------|-------|------|-------|
| <a href="panel_timer.md"><img src="../../assets/screens/landscape/timer.png" alt="timer panel" width="120" height="85"></a> | [Timer](panel_timer.md) | `timer` | A countdown timer or stopwatch. Needs no entity. |
| <a href="panel_qr.md"><img src="../../assets/screens/landscape/qr.png" alt="qr panel" width="120" height="85"></a> | [QR Code](panel_qr.md) | `qr` | A QR code for your Wi-Fi |
| <a href="panel_alarm.md"><img src="../../assets/screens/landscape/alarm.png" alt="alarm panel" width="120" height="85"></a> | [Alarm](panel_alarm.md) | `alarm` | A keypad to arm and disarm an alarm system |

## Popups

Popups open on top of the current panel and close again. They are built in; you do not add them.

| Preview | Popup | Key | Opens when |
|---------|-------|-----|------------|
| <a href="popup_notify.md"><img src="../../assets/screens/landscape/popup_notify.png" alt="notify popup" width="120" height="85"></a> | [Notify](popup_notify.md) | `popup_notify` | A notification is shown |
| <a href="popup_select.md"><img src="../../assets/screens/landscape/popup_select.png" alt="select popup" width="120" height="85"></a> | [Select](popup_select.md) | `popup_select` | You choose from a list, for example a fan speed or a preset |
| <a href="popup_unlock.md"><img src="../../assets/screens/landscape/popup_unlock.png" alt="unlock popup" width="120" height="85"></a> | [Unlock](popup_unlock.md) | `popup_unlock` | You open a panel that has a PIN |

These popups show one item's full controls in the panel of its type. Tapping a light, media player, vacuum, cover, climate or alarm entity on a grid, row or other panel opens its popup; a timer item opens the timer popup.

| Preview | Popup | Key | Controls |
|---------|-------|-----|----------|
| <a href="panel_light.md"><img src="../../assets/screens/landscape/popup_light.png" alt="light popup" width="120" height="85"></a> | Light | `popup_light` | The [Light](panel_light.md) panel |
| <a href="panel_media.md"><img src="../../assets/screens/landscape/popup_media_player.png" alt="media popup" width="120" height="85"></a> | Media player | `popup_media_player` | The [Media](panel_media.md) panel |
| <a href="panel_vacuum.md"><img src="../../assets/screens/landscape/popup_vacuum.png" alt="vacuum popup" width="120" height="85"></a> | Vacuum | `popup_vacuum` | The [Vacuum](panel_vacuum.md) panel |
| <a href="panel_cover.md"><img src="../../assets/screens/landscape/popup_cover.png" alt="cover popup" width="120" height="85"></a> | Cover | `popup_cover` | The [Cover](panel_cover.md) panel |
| <a href="panel_climate.md"><img src="../../assets/screens/landscape/popup_climate.png" alt="climate popup" width="120" height="85"></a> | Climate | `popup_climate` | The [Climate](panel_climate.md) panel |
| <a href="panel_alarm.md"><img src="../../assets/screens/landscape/popup_alarm.png" alt="alarm popup" width="120" height="85"></a> | Alarm | `popup_alarm` | The [Alarm](panel_alarm.md) panel |
| <a href="panel_timer.md"><img src="../../assets/screens/landscape/popup_timer.png" alt="timer popup" width="120" height="85"></a> | Timer | `popup_timer` | The [Timer](panel_timer.md) panel |

You can change a popup for a device with **Add panel → Extend a popup**, see [System Panel Overrides](../editor/panels.md#system-panel-overrides). To open one of your own panels on top of another panel, see [Stacked Panels and Popups](../editor/panels.md#stacked-panels-and-popups).

## System Panels

Always there. They need no configuration and cannot be changed.

| Preview | Panel | Key | Shows |
|---------|-------|-----|-------|
| <a href="panel_blank.md"><img src="../../assets/screens/landscape/sys_blank.png" alt="blank panel" width="120" height="85"></a> | [Blank](panel_blank.md) | `sys_blank` | Nothing. Add it to the idle panels for an empty screen. |
| <a href="panel_system.md"><img src="../../assets/screens/landscape/sys_system.png" alt="system panel" width="120" height="85"></a> | [System](panel_system.md) | `sys_system` | A message while the panel connects or has lost its connection |
| <a href="panel_settings.md"><img src="../../assets/screens/landscape/sys_settings.png" alt="settings panel" width="120" height="85"></a> | [Settings](panel_settings.md) | `sys_settings` | Brightness sliders. Swipe down to open it. |
| <a href="panel_about.md"><img src="../../assets/screens/landscape/sys_about.png" alt="about panel" width="120" height="85"></a> | [About](panel_about.md) | `sys_about` | Versions and the IP address. Swipe up to open it. |
