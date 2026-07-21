---
title: Configuration Overview
description: How to configure NSPanel HAUI through the Home Assistant UI editor
---

# Configuration Overview

NSPanel HAUI is configured entirely through the **Home Assistant UI** — no YAML editing required. The configuration is organised into three areas:

1. **[Device Configuration](device.md)** — Device-level settings: name, locale, hardware buttons, timeouts, sounds, relays, and color overrides.
2. **[Panel Configuration](panels.md)** — How panels are configured: type, title, key, navigation, unlock codes, and type-specific options.
3. **[Item Configuration](items.md)** — How items relate to HA entities: entity picker, state/name/value/icon/color overrides, internal items, and popup overrides.

## Finding the Editor

1. Go to **Settings → Devices & Services**.
2. Find your NSPanel HAUI device.
3. Click the device name to open its page.
4. The **Panels** tab shows your panel list. Here you can add, reorder, and delete panels.

## The Panel List

The panel list shows all panels configured for this device. Each panel shows its type, title, and key. From this list you can:

- **Add** a new panel — choose a type from the dropdown
- **Edit** a panel — click the panel name to open the panel editor
- **Reorder** — drag panels to change their order
- **Delete** — remove a panel

## The Panel Editor

Clicking a panel opens the panel editor with these standard fields:

| Field | Description |
|-------|-------------|
| **Type** | The panel type (e.g. Clock, Grid, Light, Climate). Set when adding — cannot be changed. |
| **Title** | Display name shown on the panel header. Falls back to "unnamed" if empty. |
| **Key** | A unique identifier used to reference this panel in navigation, gestures, and popups. |
| **Show in navigation** | Toggle to show/hide this panel in the navigation bar. |
| **Unlock code** | A numeric PIN — when set, the panel requires this code before access. |

Below the standard fields, each panel type shows its **type-specific options** in a collapsible **Configuration** section.

## The Item Editor

Each entity item in a panel has its own editor with:

- **Entity picker** — Search and select a Home Assistant entity
- **Advanced** section (collapsible) — Override the entity's name, value, icon, color, state, and popup behavior

See [Item Configuration](items.md) for full details on all override options.

## The Device Settings Dialog

Opened from the device toolbar. Fields are grouped into collapsible sections:

- **General Settings** — Locale, debug level, item logging
- **Display Buttons** — Home button, sleep button, notifications button visibility
- **Notifications** — Startup sound, notification sound, do not disturb, quiet hours
- **Panel Assignments** — Home panel, sleep panel, wakeup panel
- **Hardware Buttons** — Relay control, button entities, interaction reset
- **Sleep and Wakeup** — Snapshot restore behavior, idle timeout, auto-navigate home

See [Device Configuration](device.md) for full details.

## The Color Overrides Dialog

Opened from its own button (separate from Device Settings). Lets you override individual entries of the built-in color palette per device.

## Common Settings

The following device-level settings control time and date formatting:

| Option | Description |
|--------|-------------|
| **Time Format** | Time format using Python `strftime` codes (e.g. `%H:%M`). |
| **Date Format** | Date format using Python `strftime` codes (e.g. `%A, %d. %B %Y`). |
| **Date Format Locale** | CLDR locale format key (e.g. `full`, `long`, `medium`, `short`). |

## See Also

- [Panels Overview](../panels/README.md) — All panel types with descriptions
- [Examples](../examples.md) — Real-world configuration patterns
- [FAQ](../faq.md) — Common questions
