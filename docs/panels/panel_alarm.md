---
title: Panel Alarm
description: Alarm panel configuration and options
---

# Panel Alarm
## About

`type: alarm`

`key: item` (alarm_control_panel entity)

The alarm panel provides a numeric keypad (0-9, CLR, DEL) for entering an alarm code, and up to 4 action buttons for arming/disarming the security system. It is used as the base for the unlock popup and is intended for use with `alarm_control_panel` entities.

## Display

- **Title** — Shows the current alarm state label (e.g., "Disarmed", "Armed Home", "Triggered"). While entering a code on the keypad, the title shows password dots instead.
- **Header indicator** — A shield icon in the top-right header reflects the armed state: red (armed), green (disarmed), amber (arming/pending).
- **Keypad** — 12 buttons: digits 0-9, CLR (clear all), DEL (delete last digit).
- **Action buttons** — 4 bottom buttons whose content depends on the alarm state:
  - **Armed / arming / pending / triggered** — A single "Disarm" button.
  - **Disarmed** — Up to 4 arm mode buttons, filtered by the entity's `supported_features`. Modes (in priority order): Home, Away, Night, Vacation, Custom Bypass.

## Code Handling

- If the alarm entity has a `code_format` attribute, the code is required before calling any arm/disarm service.
- If a code is required but none has been entered, the action is silently ignored (the keypad entry is preserved).
- The entered code is passed as the `code` parameter to the alarm service call.
- After a successful action (or on alarm state change), the entered code is cleared.

## Popup

`type: popup_unlock`

`key: popup_unlock`

The unlock popup is used internally when a locked panel requires unlocking. It extends `AlarmPage` with a simplified layout: a single "UNLOCK" action button and dimmed keypad labels.

## Config

Panel options are configured through the NSPanel HAUI editor in Home Assistant.
