---
title: Configuration Overview
description: How to configure NSPanel HAUI through the Home Assistant UI editor
---

# Configuration Overview

NSPanel HAUI is configured entirely through the **Home Assistant UI** — no YAML editing required. The configuration is organised into three areas:

1. **[Device Configuration](device.md)** — Device-level settings: name, locale, hardware buttons, timeouts, sounds, relays, and color overrides.
2. **[Panel Configuration](panels.md)** — How panels are configured: type, title, key, navigation, panel pin, and type-specific options.
3. **[Item Configuration](items.md)** — How items relate to HA entities: entity picker, state/name/value/icon/color overrides, internal items, and popup overrides.

## Finding the Editor

1. Open **NSPanel HAUI** in the Home Assistant sidebar (`/nspanel-haui`). The entry is visible to administrators only.
2. Select your device in the toolbar.
3. The panel list shows that device's panels. Here you can add (**Add Panel**), reorder, and delete panels.

### If the editor stays on its loading screen

The editor renders Home Assistant's own dialog and card elements (`<ha-dialog>`,
`<ha-dialog-footer>`, `<ha-card>`, `<ha-alert>`). Home Assistant loads those lazily — it
imports them together with its more-info dialog *after* its own first render — so right
after a page reload the editor can be ready before them. Rendering an undefined
`<ha-dialog>` would show its content inline without a modal, so the editor waits until the
elements are defined. This normally takes a second or two.

If the wait exceeds 10 seconds, the loading screen names the elements that are still
missing and offers two actions:

| Action | Effect |
|--------|--------|
| **Reload page** | Reloads the page so Home Assistant runs its startup sequence again. Try this first — it clears a slow or interrupted frontend start. |
| **Continue anyway** | Renders the editor with whatever elements exist. Dialogs then appear inline instead of as modals: enough to inspect or revert configuration, but not a normal working state. |

A message that never clears means the running Home Assistant frontend does not define one
of the listed elements. Use **Continue anyway** to reach your configuration, and report the
Home Assistant version in a GitHub issue.

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
| **Title** | Display name shown on the panel header. Falls back to the panel type's label (e.g. "Grid") if empty. |
| **Key** | A unique identifier used to reference this panel in navigation and popups. |
| **Show in navigation** | Toggle to show/hide this panel in the navigation bar. |
| **Panel pin** | A numeric PIN — when set, the panel requires this code before access. |

Below the standard fields, each panel type shows its **type-specific options** in a collapsible **Configuration** section.

## The Item Editor

Each entity item in a panel has its own editor with:

- **Entity picker** — Search and select a Home Assistant entity
- **Advanced** section (collapsible) — Override the entity's name, value, icon, color, state, and popup behavior

See [Item Configuration](items.md) for full details on all override options.

## The Device Settings Dialog

Opened from the device toolbar. Fields are grouped into collapsible sections:

- **General Settings** — Locale, display model, auto dimming / auto page / auto display-off with their timeouts, debug level, item logging, stale-data indicator
- **Hardware Buttons** — Relay control, button entities, interaction reset
- **Display Buttons** — Home button, idle button, notifications button visibility
- **Gestures** — Named gesture sequences
- **Notifications** — Startup sound, notification sound, do not disturb, quiet hours
- **Idle & Wake Behavior** — Snapshot restore behavior, auto-navigate home, hub idle-page fallback
- **Time & Date** — Time and date formats
- **Panel Assignments** — Home panel, idle panel (carousel)

See [Device Configuration](device.md) for full details.

## The Color Overrides Dialog

Opened from its own button (separate from Device Settings). Lets you override individual entries of the built-in color palette per device.

## See Also

- [Panels Overview](../panels/README.md) — All panel types with descriptions
- [Examples](../examples.md) — Real-world configuration patterns
- [FAQ](../faq.md) — Common questions
