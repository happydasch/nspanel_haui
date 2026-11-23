---
title: Components
description: The editor's primitives and composites with their variants, states and accessibility contracts, and the surface-to-component map
---

# Components

Components are Lit template renderers in `frontend/ui/` unless a row names another file. They receive prepared data and callbacks and never read the store or call an API; `views/` composes them, which keeps the markup reusable and every data effect testable at the store and API layer. The custom elements are the exception: `nspanel-haui-editor` (the shell), `nspanel-preview-workspace`, `nspanel-simulator-frame`, `nspanel-panel-editor`, `nspanel-device-settings`, `nspanel-backup-sidebar`, `nspanel-updates-sidebar`, `nspanel-theme-sidebar`, `nspanel-logs-sidebar`, `nspanel-dialog-confirm` and `nspanel-dialog-quick-start`.

Add a component to the inventory below before implementing it when a screen needs a visual element that is not listed. Do not make a component per one-off wrapper; split when the markup or state repeats or the accessibility contract differs.

## Form fields

Shared form renderers in `form-fields.js` (`renderField`, `renderToggleField`) keep labels, controls, hints and toggle rows on one markup contract across the surfaces; `renderField` takes a `className` for surface-specific layout and `extra` content for a validation message. The low-level controls live in `form-field-controls.js`, which the item renderers import directly to avoid an import cycle, and `form-fields.js` re-exports them. `renderColorField` is the one colour control of the panel and item editors: a text field with a swatch that opens the browser's colour picker and a palette toggle (`aria-expanded`) for recent and preset colours, storing a differently shown value (an RGB565 number, an RGB list) on `change` so a keystroke never rewrites the text being typed.

A field's hint floats under the field while the pointer rests on it or focus is in it, so it never moves the layout, and touch screens keep every hint visible; add `is-persistent` to a status line that must always show (`styles/form-common-styles.js`).

## Primitives

| Component | Variants and states | Contract |
|---|---|---|
| `icon` | default, small, large, semantic tone | Home Assistant `<ha-icon>`; decorative icons are `aria-hidden` and an icon-only control carries its label on the button |
| `button`, `iconButton`, `backButton`, `addButton` | primary, outline, quiet, active, icon-only, back arrow, add row; hover, pressed, focus-visible, disabled, busy | Native button, `aria-label` when icon-only, `aria-busy` when busy, `describedBy` for a destructive note; a menu trigger passes `hasPopup: 'menu'` and names its menu only while open |
| `badge`, `countBadge`, `statusDot` | neutral, primary, success, warning, danger; online, offline, stale; a hidden empty count | Colour is never the only cue, and a dot has adjacent text or a label |
| `surface`, `sectionHeading` | plain, flush or table, gradient summary, live-tinted | Sequential heading levels; actions stay named controls |
| `segmented` | two or more choices, an optional count, a disabled choice | `role=group` with `aria-pressed` and keyboard activation |
| `choiceList` (`ui/choice-list.js`) | checkbox rows under an eyebrow heading with an optional count and group action; picked, disabled, empty | `role=group` named by the heading; the whole row is the label; the ring goes around the row |
| `sortHandle` | compact (row), overlay (card); grabbed, dragging, drop target | The only reorder affordance; it needs a pointer, so it is `aria-hidden` and keeps its label as a tooltip |
| `emptyState` | fleet, panels, group, notifications, events; with or without action | A static message and a native button; no live-region spam |
| `popover`, `menuItem` | menu, info panel, notification panel; open, focused, disabled, destructive | Trigger `aria-expanded` and `aria-controls`, menu keyboard navigation, focus restored on close |
| `HauiDialog` (`dialogs/haui-dialog.js`) | the base of both dialogs: heading, close, scrollable body, optional footer | Dialog role labelled by the title, focus contained and restored, one Escape policy |
| `showToast` (`toast.js`) | info, success, warning, error | `role=status` polite, assertive only for an actionable failure, and it never steals focus |
| `searchField` (`ui/search-field.js`) | the one pill search field of the panel list, the catalog and the logs | Its placeholder is its label, so it carries no visible one |
| `trapTab` (`ui/focus-trap.js`) | focus containment for a sidebar, dialog or popover | Tab cycles inside the layer, focus enters on open and returns to the trigger on close |
| `renderFooter` (`toolbar.js`) | stable, prerelease; version missing | The existing `.editor-footer` markup, `target` and `rel` attributes and translated titles; the links stay focusable |
| `format.js` | no DOM: timestamp, version, RSSI and connection formatters | Missing data renders explicit unknown text, never a false value |

## Composites

| Component | Variants and states | Contract |
|---|---|---|
| `deviceCard` | landscape, portrait; fleet, compact rail; online or offline, selected, update, loading or error cover, dragging | Selection is its own button, separate from the grip and the menu, and the carousel names the device |
| `deviceSlots` (`ui/device-slot.js`) | dashed outlines covering the row's spare width | Inert and hidden from assistive technology: no cover, status, scrolling or snapping |
| `deviceRow` | desktop table, compact; online or offline, stale, update, dragging | Table semantics where practical, labelled row actions, no nested control inside one button |
| `deviceRail` | full, narrow; active, offline, pending, overflow | A named group, each chip exposing its device and connection state |
| `fleetSummary`, `fleetBar`, `fleetBarTip` | normal, degraded, all offline; loading, empty; a segment hovered or focused | Counts are text, each figure keeps the diagnostics tiles' 13 px name above a 14 px/500 value, its tone repeats what the value says, and health is readable without colour or animation; every segment names its device and state, and its tip repeats it |
| `eventList` | info, warning, error; empty, populated, long text | An ordered list; the level is hidden text before the message; `<time datetime>` carries the timestamp; a repeat reads "Repeated N times" |
| `panelRow` | navigation, hidden, popup, fixed system; empty items, role set, invalid, dragging | A row is not one giant button, and a fixed entry says why it cannot be edited |
| `panelThumb` | landscape 72×51, portrait 40×60; loading, rendered, error | `alt` names the page, and hover or focus enlarges the same render |
| `panelRoleMarker` (`ui/panel-role.js`) | home, idle (numbered), navigation, hidden | `role=img` with the role's name; the icon is decorative and an unknown role draws nothing |
| `deviceDetails`, `deviceDiagnostics` | online, offline, no status; simple, expanded | Facts as a definition list with the stale ones marked; the Diagnostics card holds the tiles and the hub internals, ending with Copy report |
| `panelSideCard` (`ui/panel-info.js`) | the selected panel, or the list overview | The role toggles carry `pressed`, and the facts follow the type's own rules |
| `nspanel-device-settings` (`views/device-settings.js`) | the eight groups; landing, group open, dirty, saving, validation failure | Every field labelled and described; only the open group is in the DOM, so nothing of another group can be tabbed into |
| `settingsTile` (`ui/settings-tile.js`) | one `SETTINGS_SECTIONS` group; hover, focus | One button per tile; a missing value is named, never invented |
| `nspanel-panel-editor` (`views/panel-editor.js`) | new or copied panel, popup override, system popup; dirty, saving, duplicate key, option error | Key, title and type labelled; a disabled field says why; a fixed system key stays non-editable |
| `panelCatalog` (`views/panel-catalog.js`) | large or compact previews; loading, empty search, unsupported | Search labelled, the layout control a labelled segmented group, each card a button with title and description |
| `panelActions` (`ui/panel-manager.js`) | the Panels lead card: the panel counts, Add panel and Settings | The same module's `themeLabel` and `updatesSummary` name a theme and an update setting the way the editor and its sidebars do, so a choice and its editor say the same |
| `entryList`, `scheduleSection`, `gestureSection` | schedule, gestures; folded, open, just added | Native `details` and `summary` folding, with the remove button separate so it does not fold the card |
| `updateProgress` (`ui/update-progress.js`) | firmware, display; starting, transferring, done, failed | `role=progressbar` with a text value, the current step `aria-current="step"`, and the bar below 100 while the rest is an estimate |
| `rolloutCard` (`ui/rollout-card.js`) | running, done, stopped, cancelled; queued, installing, failed | An ordered list, state as badge text, a polite `status` summary, and cancel buttons named by device |
| `notificationItem` | ordinary, persistent, critical; queued, dismissing | Severity is text or icon plus colour, and dismiss names its notification |
| `modalSidebar`, `sidebarFrame` (`ui/sidebar.js`) | the seven sidebar kinds; opening, dirty, saving or error | Modal semantics, a labelled heading, focus moved, trapped and restored, Escape closing the topmost layer |
| `stateValues` (`ui/state-values.js`) | text, icon and colour rows per state; empty, duplicate state | A labelled list; a duplicate state is `aria-invalid` and described by its warning |
| Item renderers (`item-renderers.js`) | entity, skip, text, navigate, action; single or list item | Inline errors labelled, the entity picker's combobox contract kept, reorder announced |
| `renderOptionField`, `renderEntityPicker`, `renderIconPicker`, `renderColorField`, `scheduleTemplateRender` | the descriptor-driven form controls | The control matches the option kind, labels and descriptions are linked, constraints are conveyed |

## Surface-to-component map

| Surface | Components used |
|---|---|
| Shared titlebar | `icon`, `button`, `badge`, `popover` |
| Fleet | `deviceCard`, `deviceSlots`, `sortHandle`, `fleetSummary`, `surface`, `deviceRow`, `eventList`, `emptyState`, `badge` |
| Device rail | `deviceRail`, `statusDot` |
| Workspace header and preview | `segmented`, `button`, `previewStage`, `emptyState`, `popover` |
| Panel groups | `surface`, `panelRow`, `panelThumb`, `sortHandle`, `badge`, `emptyState` |
| Device details and panel manager | `deviceDetails`, `deviceDiagnostics`, `panelActions`, `panelSideCard`, the four sidebar elements, `surface`, `button`, `badge`, `choiceList` |
| Settings, panel editor and catalog sidebars | `modalSidebar`, `nspanel-device-settings`, `settingsTile`, `scheduleSection`, `gestureSection`, `nspanel-panel-editor`, `panelCatalog`, the form renderers, the item renderers, `panelThumb` |
| Notification centre | `notificationsView`, `popover`, `notificationItem`, `emptyState`, `button` |
| Confirmation dialog | `HauiDialog`, `nspanel-dialog-confirm`, `button`, `showToast` |
| Quick start dialog | `HauiDialog`, `nspanel-dialog-quick-start`, `button`, `emptyState`, `panelRoleMarker`, the form renderers, `ha-alert`, `nspanel-simulator-frame` |
