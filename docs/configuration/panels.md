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
| `title` | Display name shown on the panel header. Falls back to the panel type's label (e.g. `Grid`) if left empty. |
| `key` | A unique identifier used to reference this panel in navigation actions and popup overrides. Must be unique across all panels on the device. |
| `show_in_navigation` | Boolean toggle (default **on**). When enabled, the panel appears in the navigation bar. When disabled, the panel is hidden from navigation and opens stacked on top of the current panel — use this for subpanels and detail views (see [Stacked Panels and Popups](#stacked-panels-and-popups)). |
| `long_press_back` | **Long press to go back** (default **off**), offered only for panel types without header buttons (Clock, ClockTwo, Weather), which can otherwise only be left by swiping. When enabled, holding anywhere for about a second goes back: to the panel this one was opened from, or to the home panel. A long press rather than a tap or double tap because the firmware polls touches every 200 ms, too slowly to catch quick taps reliably. |
| `unlock_code` | **Panel pin** in the editor. A numeric PIN code. When set, the panel requires this code before it can be accessed. The input is masked as a password field. |

### Type-Specific Options

Each panel type declares its own options (e.g. number of grid slots, default brightness, units). These appear in a **Configuration** collapsible section in the editor, generated from the panel's `PageDescriptor` options.

See [Panels Overview](../panels/README.md) for the full list of panel types and their options.

### Stacked Panels and Popups

A panel with `show_in_navigation` off is opened on top of the current panel
(*stacked*) — by a `navigate:key` action, a gesture, or an item's `popup_key` —
and closing it goes back to where it was opened from. Every panel you add
yourself is a **stacked panel** when it is out of navigation, whatever its type:
a cover or light panel behaves exactly like a grid. Only the built-in system
popups are **popups**: the entity popups (`popup_light`, `popup_media_player`,
`popup_vacuum`, `popup_climate`, `popup_cover`, `popup_timer`, `popup_alarm`),
`popup_notify`, `popup_select`, `popup_unlock`, and Settings and About. They are
recognised by their key, so an edited entity popup (see below) stays a popup.

The only difference is the header buttons the hub fills in automatically:

| Panel | Left | Second left | Right |
|-------|------|-------------|-------|
| Navigation panel | previous panel | home | next panel |
| Stacked panel | up | home | close |
| Popup | home | — | close |

- **Up** and **close** both go back to the panel the stacked panel or popup was opened from.
- **Home** appears only when the home button is enabled (`show_home_button` on the device or the panel), and never on the home panel itself. The home panel shows the idle button there instead when `show_idle_button` is on. A popup without a home button shows **up** in its place; Settings and About are configured that way.
- The right-hand secondary slot shows the unlock button on a locked panel, otherwise the notifications button.
- The **unlock popup** (`popup_unlock`) opens on top of the locked panel and its header follows that panel: guarding a navigation panel it shows the navigation header (previous, home, next), so you can move on without unlocking, with the lock in the right-hand secondary slot; guarding any other panel it shows the popup header.

### System Panel Overrides

The editor lists the fixed built-in panels in the **System Panels** section and
the editable popups (`popup_*`) in the **Popups** section. Only the popups can
be edited: **Edit** saves a panel under the popup's key
that replaces the built-in one on this device; it is marked **Edited**, and
**Reset to default** deletes it and brings the built-in popup back. **System**,
**Blank**, **Settings** and **About** are fixed and shown read-only; the hub
refuses a panel saved under their key, and a stored edit of one (saved by an
earlier development build) is removed when the integration loads, with a
warning in the log.

- An entity popup (`popup_light`, `popup_climate`, `popup_media_player`,
  `popup_cover`, `popup_vacuum`, `popup_timer`, `popup_alarm`) is edited with
  the form of its panel type (e.g. Cover for `popup_cover`) and saved as that
  type. The entity still comes from the item that opens the popup.
- **Notify**, **Select** and **Unlock** keep their own type and offer the
  generic fields.
- An edited popup keeps every default of the built-in one it does not set.
- Its key and **Show in navigation** are fixed: it stays a system popup and
  never joins navigation.

The hub drives **Notify**, **Select** and **Unlock** itself, so these offer
only the title: a **Panel pin** or **Close automatically after** would get in
the way (a PIN on Unlock would ask for a PIN before every unlock, auto-close
would close queued notifications). The hub ignores both fields on these popups
and logs a warning if a stored configuration still has them.

### Panel Access and Navigation

To reference a panel from actions, define its `key`. Then use `navigate:key` as the item value to navigate to that panel.

### Auto-Close

`close_timeout` — **Close automatically after (seconds)** in the panel's general settings. When set to a value greater than 0, the panel closes and navigation goes back after that many seconds. `0` (default) keeps it open. Queued-notification popups do not use it: they stay open until the notification is dismissed.

### Device-Level Panel Assignments

The following settings are **not per-panel** — they are configured in the **Device Config** dialog (accessible from the editor toolbar) under the **Panel Assignments** section:

| Field | Description |
|-------|-------------|
| `home_panel` | The panel shown when the user navigates home, or when the idle page is exited without a snapshot to restore. If not set, the first configured navigation panel is used. |
| `idle_panel` | The **idle page** — the panel opened by automatic page switching (`use_auto_page`) after the page timeout. It is a navigation target only; turning the display off is a separate behavior (`use_auto_display_off`) that never requires a page switch. |

Each of these is a dropdown that lists all user-defined panels on the device. Only one panel can be assigned to each role. `idle_panel_extra` additionally accepts a comma-separated carousel of panel keys that cycle on repeated entries.

### Navigation Behaviour

- Panels with `show_in_navigation` enabled appear in the navigation bar and can be cycled through.
- Panels with `show_in_navigation` disabled are hidden from navigation but can still be navigated to via `navigate:key` actions or popup references.
- Special system panels (Settings, About, Notifications, Select, Unlock, Blank and the other system pages) always have `show_in_navigation` set to `false` and do not appear in navigation.