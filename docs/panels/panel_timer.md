---
title: Panel Timer
description: Timer panel configuration and options
---

# Panel Timer

![](../assets/previews/panel-timer.svg)

## About

`type: timer`

The timer panel provides a local countdown timer with start, pause, and stop controls. The timer runs entirely on the display — it does not use a Home Assistant `timer` entity. If a duration greater than 0 is set, the timer counts down from that value; if 0 is set, it counts up (stopwatch mode).

<!-- TODO: Add screenshot at ../assets/screenshots/panel-timer.png once screenshot generation script is implemented -->

## Popup

`type: popup_timer`

`key: popup_timer`

## Controls

| Widget | Description |
|--------|-------------|
| **Time display** | Shows `MM:SS` format. Large digits in the center of the panel. |
| **Up/Down buttons** | 4 sets of up/down arrows for setting digits (M1 M2 : S1 S2) before starting. |
| **Start button** | Begins the countdown. Enabled when duration > 0 and timer is not running. |
| **Stop button** | Stops/resets the timer. Enabled while timer is running. |

## Config

### Show Notification

`key: show_notification` | `kind: bool` | `default: True`

When the timer finishes (reaches 00:00 in countdown mode), a sound is played. If this option is enabled, a notification popup is also shown on the display.

## Display Behavior

- **Before starting:** The up/down arrow buttons allow setting the initial duration.
- **Running:** The time display updates every 0.5 seconds. Start button becomes a pause/resume button.
- **Finished (countdown):** A sound plays; if `show_notification` is enabled, a popup notification appears.
- **Stopwatch mode:** When initial duration is 00:00, the timer counts up from 0.
- The timer state is local to the display — it does not persist across device restarts.
