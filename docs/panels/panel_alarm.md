---
title: Panel Alarm
description: Alarm panel — security system keypad with arm/disarm controls
---

# Panel Alarm

![](../assets/previews/panel-alarm.svg)

## About

The alarm panel provides a numeric keypad (0-9, CLR, DEL) for entering an alarm code, and up to 4 action buttons for arming/disarming the security system. It is intended for use with `alarm_control_panel` entities.

## Display

- **Title** — Shows the current alarm state label (e.g., "Disarmed", "Armed Home", "Triggered"). While entering a code on the keypad, the title shows password dots instead.
- **Header indicator** — A shield icon in the top-right header reflects the armed state: red (armed), green (disarmed), amber (arming/pending).
- **Keypad** — 12 buttons: digits 0-9, CLR (clear all), DEL (delete last digit).
- **Action buttons** — 4 bottom buttons whose content depends on the alarm state:
  - **Armed / arming / pending / triggered** — A single "Disarm" button.
  - **Disarmed** — Up to 4 arm mode buttons, filtered by the entity's supported features. Modes (in priority order): Home, Away, Night, Vacation, Custom Bypass.

## Code Handling

- If the alarm entity has a `code_format` attribute, the code is required before calling any arm/disarm service.
- If a code is required but none has been entered, the action is silently ignored (the keypad entry is preserved).
- The entered code is passed as the `code` parameter to the alarm service call.
- After a successful action (or on alarm state change), the entered code is cleared.

## How to configure

In the **panel editor**, set:

- **Item** (entity picker) — An `alarm_control_panel` entity to control. Required.
