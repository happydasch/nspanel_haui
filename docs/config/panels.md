---
title: Panel Configuration
description: Panel configuration — type, key, title, show_in_navigation, unlock_code, and device-level panel assignments
---

# Panel Configuration

Panels are configured through the **panel editor** in the Home Assistant UI. Each panel has a set of standard fields plus type-specific options declared by the panel's descriptor.

The editor is opened by clicking a panel in the panel list, or by selecting a panel type from the **Add Panel** dialog.

### Standard Fields

Every panel has these fields in the editor:

| Field | Description |
|-------|-------------|
| `type` | The panel type (e.g. `clock`, `grid`, `light`, `climate`). Selectable from a dropdown when adding a new panel. Set for the lifetime of the panel — to change type, delete and re-add. |
| `title` | Display name shown on the panel header. Falls back to `unnamed` if left empty. |
| `key` | A unique identifier used to reference this panel in navigation actions, gestures, and popup overrides. Must be unique across all panels on the device. |
| `show_in_navigation` | Boolean toggle (default **on**). When enabled, the panel appears in the navigation bar. When disabled, the panel is hidden from navigation — use this for subpanels, detail views, and popups. |
| `unlock_code` | A numeric PIN code. When set, the panel requires this code before it can be accessed. The input is masked as a password field. |

### Type-Specific Options

Each panel type declares its own options (e.g. number of grid slots, default brightness, units). These appear in a **Configuration** collapsible section in the editor, generated from the panel's `PageDescriptor` options.

See [Panels Overview](../panels/README.md) for the full list of panel types and their options.

### Popup Overlays

Panels can be displayed as popup overlays on top of the current panel. This is controlled by the **can_show_popup** flag on the panel type descriptor:

- **Single-entity panels** (light, climate, media, cover, vacuum, timer) — support popup overlay display.
- **Multi-entity panels** (grid, row, clock, weather) — do not support popup overlay. When `show_in_navigation` is `false`, they display as full-page subpanels instead.

To use a panel as a popup, set `show_in_navigation` to off and reference it via `popup_key` in an item's advanced configuration.

### Panel Access and Navigation

To reference a panel from actions or gestures, define its `key`. Then use `navigate:key` as the item value to navigate to that panel.

### Auto-Close

`close_timeout` — a number of seconds (backend-only, not yet rendered in the frontend editor). When set to a value greater than 0, the panel will automatically close after that many seconds. This can be set via YAML or API for now.

### Device-Level Panel Assignments

The following settings are **not per-panel** — they are configured in the **Device Config** dialog (accessible from the editor toolbar) under the **Panel Assignments** section:

| Field | Description |
|-------|-------------|
| `home_panel` | The panel shown when the user navigates home or after dim/sleep returns. If not set, the first configured navigation panel is used. |
| `sleep_panel` | The panel shown when the display enters sleep mode (after the page timeout). |
| `wakeup_panel` | The panel shown briefly when the display wakes from sleep. If not set, the display returns to the home panel (or the last active panel if no sleep occurred). |

Each of these is a dropdown that lists all user-defined panels on the device. Only one panel can be assigned to each role.

### Navigation Behaviour

- Panels with `show_in_navigation` enabled appear in the navigation bar and can be cycled through.
- Panels with `show_in_navigation` disabled are hidden from navigation but can still be navigated to via `navigate:key` actions, gestures, or popup references.
- Special system panels (Entry Details, Popups, Settings, About, Notifications, Select, Row, Blank) always have `show_in_navigation` set to `false` and do not appear in navigation.