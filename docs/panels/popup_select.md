---
title: Popup Select
description: Select popup — value selection list with multiple modes
---

# Popup Select

## About

The select popup allows choosing a value from a list. It is used internally by entity panels (e.g., for fan speed, HVAC mode, or preset selection) and can also be triggered programmatically.

If the selection list has more items than fit on one page, a function button in the header opens the next page.

## How to configure

In the **panel editor**, set:

- **Select Mode** (dropdown) — Display style:
  - **Default** — 3×4 button grid
  - **Full** — Full-width list (4 buttons per page)
- **Multiple** (toggle) — Allow selecting multiple items. Default: Off.
- **Multiple Delay** (number) — Delay in seconds before closing when Multiple is enabled. Default: 1.5s.
- **Close on Select** (toggle) — Close the popup after a selection is made. Default: On.
- **Close Timeout** (number) — Automatically close after this many seconds. 0 = no auto-close.

## For developers

If you are writing a custom integration or extension that needs to open a selection popup programmatically with callbacks, see [Hub](../hub.md) for the internal API.
