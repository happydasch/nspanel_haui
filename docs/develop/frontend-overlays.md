---
title: Sidebars and overlays
description: The editor's sidebars, menus, popovers, dialogs and toast — how they are wired, what each holds, and the focus and Escape rules
---

# Sidebars and overlays

Everything that sits above the current screen is one overlay layer: sidebars, the side stack's cards, menus, popovers, dialogs and the toast. None of them is a route, and an open sidebar or an unsaved draft stays out of the URL ([Screens](frontend-screens.md)).

## How overlays are wired

- `ui/popover.js` is the only anchored popover: one open at a time, placed against the trigger that carries `data-overlay-anchor="<kind>[:<subject>]"`, closed by Escape or an outside click with focus returned to that trigger.
- A sidebar is one entry of `SIDEBAR_OVERLAY_KINDS` (`store/store.js`): `device-settings`, `panel-catalog`, `panel-editor`, `backups`, `updates`, `theme`, `logs`.
- `dialogs/confirm.js` and `dialogs/quick-start.js` are the only dialogs.

## Sidebars

Every sidebar opens 380px wide (`ui/sidebar.js`) and its inner edge resizes it: drag it, or focus it and use the arrow keys, with Home and End at the limits and a double click back to 380px. The width, between 320px and the window less 120px, is shared by all sidebars and kept in `haui_sidebarWidth`; at 600px or less a sidebar becomes a full-screen page without resize edge or scrim.

| Sidebar | Contents |
|---|---|
| Device settings (`views/device-settings.js`) | Two levels: a landing grid of `settingsTile`s, one per group of `SETTINGS_SECTIONS` (`device-settings-sections.js`: general, home, hardware, buttons, screen, sounds, gestures, advanced), then the open group's page; the footer **Device Enabled** / Cancel / Save is the same on both levels |
| Panel editor (`views/panel-editor.js`) | Panel identity, behaviour and roles, descriptor options grouped by `PageOption.section` with item counts in the headings, inline item editing; `option-rules.js` marks a broken rule as an error that blocks Save, an entity Home Assistant does not know as a warning, and a hub refusal (`serverErrors`) marks the field it names |
| Panel catalog (`views/panel-catalog.js`) | Shared search, a Large/Compact preview toggle (`haui_panelCatalogCompact`), one card per descriptor, popup and copy |
| Backups (`dialogs/backup.js`) | **Backup file** with Export and Import as one pair, then **Copy to other devices** with a `choiceList` per direction; each card says what it replaces in an `ha-alert` warning banner |
| Updates (`dialogs/updates.js`) | Status, a scheduled install with **Install now**, **In 1 hour**, **In 1 day** and **Skip this version**, `updateProgress`, the firmware and display rows, **Check for updates** |
| Theme (`dialogs/theme.js`) | Draft palette preview, one theme picker, the icon colours of the palette the background picks, New/Export/Import and Duplicate/Rename/Delete |
| Logs (`dialogs/logs.js`) | The hub's recent lines newest first and grouped by day, a device selector, the shared search field, Copy |

The settings, editor and catalog sidebars render no header of their own: the sidebar strip carries the title and the close control, and a settings group adds a back control before the title. A sidebar's body scrolls while its footer stays put.

The panel editor asks the hub to render the unsaved form (`crud.js:buildPanelConfig`), at once on the first change and then 400 ms after typing pauses; `panelKeyError` validates the key in place and Save stays disabled while a field is marked.

## Menus, popovers and dialogs

| Overlay | Contents |
|---|---|
| Notification centre (`views/notifications.js`) | The queued notifications with per-item dismiss; the count is the queue length |
| Panel preview popover | An enlarged thumb with the panel's name and key, opened on hover, focus or tap |
| Toast (`toast.js`) | One transient success, error or info message, `role="status"`, no focus steal |
| Confirmation dialog (`dialogs/confirm.js`) | Destructive confirmation on `HauiDialog`, opened by the action it guards |
| Quick start (`dialogs/quick-start.js`) | The preset chooser of a device without panels (`quick-start-flow.js`, presets in `presets.js`, entity slots resolved from the user's own areas by `preset-entities.js`); a slot the area has no entity for is left out of an item list, so it never blocks the setup |

## Focus and Escape

Only one anchored popover is open at a time, and a sidebar may hold one topmost menu. Escape closes the topmost layer first, then the sidebar, and returns from Device to Fleet only when no overlay is open; an outside click closes only the active popover. Closing restores focus to the trigger, opening a sidebar moves focus into it and traps Tab, and focus is never lost on render or save. Use native buttons, links, inputs and `<details>/<summary>`, keep visible focus rings and give every control a meaningful accessible name.
