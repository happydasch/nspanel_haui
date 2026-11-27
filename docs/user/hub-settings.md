---
title: Hub settings
description: Rename the hub and set the time and date formats every panel inherits
---

# Hub settings

Two kinds of settings exist: those that belong to the hub and those that belong to a panel.
Everything about a panel — its pages, theme, brightness, buttons, gestures and its own formats — lives in the
[NSPanel HAUI editor](editor/README.md). The hub's own settings live in Home Assistant, on the integration's card.

## Open the settings

1. Go to **Settings → Devices & services**.
2. Find **NSPanel HAUI** and select **Configure**.
3. Change what you need and select **Submit**.

The form shows the values every panel inherits today, so an untouched hub displays what its panels use now.

## Hub name

**Hub name** is the name Home Assistant shows for this integration: on its card, in the repair that warns about a
hub without enabled devices, and in the log lines about the hub.

It does not rename anything else. Panels keep their own names, their device and entity ids keep the name they were
created with, and the notify and update entities keep working across a rename.

## Display defaults

The three formats below are the defaults a panel inherits while its own **Time format**, **Date format** or
**Locale-aware date layout** is left at **Default** in the editor:

| Setting | Example | Notes |
|---------|---------|-------|
| **Default time format** | `%H:%M` | A strftime pattern; `%H:%M` is 14:30, `%I:%M %p` is 2:30 PM |
| **Default date format** | `%A, %d. %B %Y` | A strftime pattern with at least one `%` directive |
| **Default locale-aware date layout** | `full` | Used when a panel's date format is **Default**; the layout follows the panel's language |

The rules are short:

- **A panel's own value wins.** A panel with a format of its own is not affected by the hub defaults.
- **Empty means the built-in default.** Clearing a field keeps the default the integration ships with rather than
  blanking the panels.
- **The layout and the format are not the same thing.** Set **Default date format** for the exact pattern every panel
  should show, or leave it empty and pick a layout — `full`, `long`, `medium`, `short`, `E` or `EEEE` —
  which the panel fills in with its own language.

## Saving restarts the panels

Saving reloads the integration, so every panel restarts with the new defaults: the display keeps showing its last
page and is redrawn after a few seconds. No setting is lost, and the editor needs no reload.

## What is not here

Per-panel settings, the theme library and the device order are not part of this form; they need the editor's live
preview and are changed there. Connection timings are not exposed either: a wrong heartbeat setting disconnects
every panel, and a panel already reports its own through the handshake.
