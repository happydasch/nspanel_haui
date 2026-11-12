---
title: Panel Overview
description: Overview of all available panel types for NSPanel HAUI
---

# Panel Overview

A panel is one screen on the display. There are **13 panel types** you can add, plus built-in popups and system panels. The **Add panel** catalog lists them under four categories: **Backgrounds**, **Entities**, **Grouping** and **Tools**. Select a panel below to read what it shows and which options it has.

You add panels in the editor, see the [Configuration Overview](../configuration/README.md). The [Screens overview](../../screens.html) shows every panel in the landscape and the portrait layout.

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

## Tools

Panels for special tasks.

| Preview | Panel | Type | Shows |
|---------|-------|------|-------|
| <a href="panel_timer.md"><img src="../../assets/screens/landscape/timer.png" alt="timer panel" width="120" height="85"></a> | [Timer](panel_timer.md) | `timer` | A countdown timer or stopwatch. Needs no entity. |
| <a href="panel_qr.md"><img src="../../assets/screens/landscape/qr.png" alt="qr panel" width="120" height="85"></a> | [QR Code](panel_qr.md) | `qr` | A QR code for your Wi-Fi |
| <a href="panel_alarm.md"><img src="../../assets/screens/landscape/alarm.png" alt="alarm panel" width="120" height="85"></a> | [Alarm](panel_alarm.md) | `alarm` | A keypad to arm and disarm an alarm system |

## Popups

Popups open on top of the current panel and close again. They are built in; you do not add them.

| Popup | Key | Opens when |
|-------|-----|------------|
| [Notify](popup_notify.md) | `popup_notify` | A notification is shown |
| [Select](popup_select.md) | `popup_select` | You choose from a list, for example a fan speed or a preset |
| [Unlock](popup_unlock.md) | `popup_unlock` | You open a panel that has a PIN |
| Entity popups | `popup_light`, `popup_media_player`, `popup_vacuum`, `popup_climate`, `popup_cover`, `popup_alarm`, `popup_timer` | You tap an entity on a grid, row or other panel. They look like the panel of the same type. |

You can change a popup for a device with **Add panel → Extend a popup**, see [System Panel Overrides](../configuration/panels.md#system-panel-overrides). To open one of your own panels on top of another panel, see [Stacked Panels and Popups](../configuration/panels.md#stacked-panels-and-popups).

## System Panels

Always there. They need no configuration and cannot be changed.

| Panel | Key | Shows |
|-------|-----|-------|
| [Blank](panel_blank.md) | `sys_blank` | Nothing. Use it as the idle panel for an empty screen. |
| [System](panel_system.md) | `sys_system` | A message while the panel connects or has lost its connection |
| [Settings](panel_settings.md) | `sys_settings` | Brightness sliders. Swipe down to open it. |
| [About](panel_about.md) | `sys_about` | Versions and the IP address. Swipe up to open it. |
