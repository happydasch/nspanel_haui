---
title: Popup Select
description: Select popup — value selection list with multiple modes
---

# Popup Select

## About

The select popup allows choosing a value from a list. It is used internally by entity panels (e.g., for fan speed, HVAC mode, or preset selection) and can also be triggered programmatically.

If the selection list has more items than fit on one page, a function button in the header opens the next page.

Tapping an entry selects it. In single-selection mode, tapping the already selected entry keeps it selected and applies it again. With **Multiple** enabled, tapping an entry toggles it.

## How to configure

This popup is opened by the integration and cannot be configured in the panel editor. Parameters when opening it programmatically:

- `items` — The entries (`{value, name}` dicts or plain strings). At least one is required.
- `selected` — The currently selected value (a list with `multiple`).
- `select_mode` — Display style:
  - `default` — 3×4 button grid
  - `full` — Full-width list (4 buttons per page)
- `multiple` — Allow selecting multiple items. Default: false.
- `multiple_delay` — Delay in seconds before the selection is applied when `multiple` is enabled. Default: 1.5.
- `close_on_select` — Close the popup after a selection is made. Default: true.
- `close_timeout` — Automatically close after this many seconds. 0 = no auto-close.
- `selection_callback_fnc`, `close_callback_fnc` — Callbacks.

## For developers

If you are writing a custom integration or extension that needs to open a selection popup programmatically with callbacks, see [Hub](../hub.md) for the internal API.
