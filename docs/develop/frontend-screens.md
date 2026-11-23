---
title: Screens
description: The Fleet and Device routes, the shared shell, and every region of both screens with its data and states
---

# Screens

Two screens and one overlay layer. The hash route is the single source of truth for the screen; sidebars, menus, popovers and dialogs overlay it instead of becoming more routes ([Sidebars and overlays](frontend-overlays.md)). The layers a change belongs to are on [Editor architecture](frontend.md).

## Page structure and navigation

| Hash | Screen | Main regions | Opens initially |
|---|---|---|---|
| `#/` | Fleet | Device carousel; fleet summary; device inventory; latest events | None |
| `#/device/<device-name>` | Device | Device rail; panel workspace; Preview with the contextual side stack | Preview + device details |
| `#/device/<device-name>/panels` | Device | Same regions | Panel list + panel manager |
| `#/device/<device-name>/panel/<panel-key>` | Device | Same regions | Panel editor sidebar for the addressed panel |

Name and key segments are URI-encoded. An unknown device resolves to Fleet and an unknown panel key to the device's Panels view, each with an error toast. User navigation between Fleet and Device pushes a history entry, while switching the panel view or normalizing an invalid route replaces the current one. Open sidebars and unsaved drafts stay out of the URL.

```text
┌─ Titlebar (56px): brand · Dashboard/device breadcrumb · notification bell ────────────────────┐
│ Fleet screen                                                                              │
│  Device carousel (280–320px cards; horizontal snap)                                       │
│  ┌─────────────────────────────────────────┐  ┌───────────────────────────────────────┐ │
│  │ Fleet summary                           │  │ Latest events                         │ │
│  ├─────────────────────────────────────────┤  ├───────────────────────────────────────┤ │
│  │ Device inventory                        │  │                                       │ │
│  └─────────────────────────────────────────┘  └───────────────────────────────────────┘ │
│ Device screen                                                                             │
│  Device rail (horizontal chips)                                                          │
│  ┌─────────────────────────────────────────┐  ┌───────────────────────────────────────┐ │
│  │ Panel workspace                         │  │ Lead card: the view's next actions    │ │
│  │ Preview OR panel groups                 │  ├───────────────────────────────────────┤ │
│  │                                         │  │ Side stack                            │ │
│  │                                         │  │ Device details OR panel manager       │ │
│  └─────────────────────────────────────────┘  └───────────────────────────────────────┘ │
├─ Overlay layer: menu/popover · notification centre · sidebar + scrim · dialogs · toast ────┤
└─ Global footer: version · Dev badge (prerelease only) · GitHub · Documentation ────────────┘
```

The titlebar is sticky and the page scrolls under it, so content that pins to the viewport starts below it at `--haui-header-height` (`styles/tokens.js`). Fleet lays out `minmax(0, 1.65fr)` / `minmax(280px, .85fr)` (`styles/fleet-styles.js`); Device lays out `minmax(0, 1.65fr)` / `minmax(280px, .9fr)` with the grid areas `workspace side` (`styles/device-layout-styles.js`). Content fills the width with 28px gutters, 14px on narrow screens. The breakpoints that change this are on [Visual foundations](frontend-visuals.md#breakpoints).

## Shared shell

| Region | Holds | Contract |
|---|---|---|
| Titlebar | HAUI title, current screen or device, notification button and count, Home Assistant's narrow-sidebar toggle | Sticky; no hub or hub configured; no notifications or a nonzero count; narrow mode |
| Global editor footer | `renderFooter()` (`toolbar.js`): integration version, `Dev` badge for prereleases only, GitHub, Documentation | `INTEGRATION_VERSION` is parsed from the hashed asset URL and `docsUrl()` targets `/dev/` on a prerelease, the stable docs root otherwise; the footer stays after the content on loading, error and empty states, and the links never move into a menu |

## Fleet screen regions

| Region | Holds | Data and states |
|---|---|---|
| Device carousel | Scroll-snap row of real device cards between 280px and 320px wide (280px once the row scrolls), arrows, edge fades, swipe anywhere on a card | online/offline, selected, update; the spare width is filled by `deviceSlots` |
| Device card | The panel's home render as the card's whole top (a portrait screen keeps its shape, centred), the strip with status dot and name, update badge and drag grip floating on the render | loading/error cover, selected, dragging |
| Fleet summary | Top of the Device inventory card: health icon, heading, online/total and a sentence, updates-pending and integration-version figures with a tone-tinted glyph in the diagnostics tiles' type, **Install updates** while any are installable; the card's footer closes with one segment per device in its connection tone (`fleetBar`, `ui/fleet-summary.js`), each opening `fleetBarTip` with its device and state on hover or focus, and never collapses | loading, empty, healthy, warning/error |
| Device inventory | Table of the same devices: device with its connection icon, IP, firmware (`yaml_version`), TFT, actions; rows drag-sort; firmware that differs from the integration version carries a danger **Mismatch** badge | online/offline, stale, update, dragging; the IP column hides at 1120px, TFT at 560px |
| Update rollout | `rolloutCard` (`ui/rollout-card.js`) above the inventory: state sentence, one row per device with kind, state badge, progress and error, cancel per device and **Cancel remaining** | running, done, stopped, cancelled |
| Latest events | The last 24 hours of warnings and errors as a timeline: a level dot on a rail, the message's first line, the device name, relative time and a repeat count; **Reset** restarts the window, **Last 24 hours** restores it | empty, populated, long text; info and debug lines stay in Logs |

Every figure on Fleet has a real source: connection duration from `device_info.connection_uptime` / `last_connection`, IP and versions from status. The bar's segments are each device's current connection tone, not a history.

**Install updates** installs what each connected device is offered, firmware first, and the shell reads `state.hub.rollout` when Fleet polling starts and on every poll while it runs. The carousel measures the real cards and the spare width itself (`views/fleet.js:carouselSlots` and `deviceSlotCount`) and adds enough dashed outlines to cover it, so the last one may be clipped.

The shell scans for unmanaged HAUI devices once the hub is loaded and Fleet lists them under Discovered Devices; the inventory row menu enables, disables and removes a device (`device-events.js`).

Selecting a device is separate from the route: a click on a row outside its own controls, Enter or Space, or the strip under a card's cover selects it, and selecting it again clears it. The selection scopes the log surfaces — **Latest events** names and lists that device only, and **Logs** opens on it — and it comes back when the user returns to Fleet. **Reset** on the timeline is kept in `haui_fleetEventsSince` (`editor-preferences.js`), so a reload keeps the shortened window.

## Device screen regions

| Region | Holds | Data and states |
|---|---|---|
| Device rail | Compact device chips: status dot, short name, update mark; collapses into a dropdown while the chips do not fit beside the title (`ui/device-rail.js:railOverflows`) | `devices.order` and statuses; selecting navigates; narrow, overflow |
| Workspace header | Segmented `Preview` / `Panels (count)`, Live and Idle controls, the panel list's search field | no panels disables Preview; icons only at 600px or less |
| Panel workspace | The preview stage, or the panel groups (`views/workspace.js`, `views/panel-list.js`) | loading, no panel, error |
| Panel groups | Navigation, Hidden and Popups (extended popups only; fixed system panels are not listed), built by `panel-utils.js:groupPanels`; rows carry a hub-rendered thumb, Home/Idle markers, an item count and one anchored menu | panel order; drag reorder; a drop across Navigation and Hidden flips `show_in_navigation` in one save (`crud.js:movePanelToGroup`) |
| Lead card | The view's next actions (`ui/action-card.js`), primary-tinted and never collapsed: Panels has the counts, Add panel and Settings; Preview has Settings, Add panel, Install update while one is offered, then Theme and Gestures as plain buttons | sticky beside the workspace; moves above it in one column |
| Side stack | `surface` cards: Connection, Diagnostics, then one full-width button per sidebar (Themes, Updates, Backups) | one card expanded at a time, remembered in `haui_deviceDetailsExpanded` / `haui_diagnosticsExpanded`; facts marked stale while offline |
| Panel manager | Counts, the Home and Idle selectors, and the selected panel's card (`panel-models.js:panelSideModel`): its render, facts, role toggles and Edit, Duplicate, Delete — a popup override gets Edit and Reset to default | no panels, unassigned roles; the render folds per browser (`haui_panelPreviewFolded`) |

A device with no panels shows one device-wide setup state instead of three empty groups (`setup` in `views/panel-list.js` renders an `emptyState` whose action opens the quick start).

Panel rows show an explicit drag handle, a thumb (landscape 72×51, portrait 40×60), title, key, item count, role markers and one overflow menu; only user panels drag, and fixed system rows show a disabled grip so the rows line up. The idle markers follow the device's carousel — the first idle panel solid, every further one dimmed and numbered — and the Home marker follows the hub's fallback to the first navigation panel. A row the list just gained carries a New badge for `NEW_PANEL_MARK_MS` (10 s, `app/shell.js`).

A search field in the workspace header (`ui/search-field.js`, rendered by `views/device.js`) narrows the groups to matching rows and switches reordering off while it is active; the row menu duplicates a panel (`crud.js:duplicatePanel`), and menus move with the arrow, Home and End keys. Panel rows and inventory rows end in the same two quiet buttons (`haui-row-action`): Edit for a panel, Settings for a device, then More.

`frontend/panel-roles.js` owns the device's Home and Idle roles: the stored key lists (`home_panel`, `idle_panel` + `idle_panel_extra`) and one shared resolution against the panels the device has (`resolvePanelRoles`). A key whose panel is gone is no set panel for either role, as the hub treats it, and is shown as an unknown key. **Home panel** writes `home_panel` and **Idle panel** appends to the idle sequence or removes it, both through `crud.js:togglePanelRole` in one device-settings save; a popup override takes no role.

The lead card heads the side column (`.haui-device-side` is sticky) and moves above the workspace in one column; keyboard focus keeps following the markup, so it runs lead card, side stack, workspace. The Diagnostics card's status icon counts the open findings and opens them in a popover, and expanded it shows two tiles and the hub internals with Copy report. Only one side-stack card is expanded at a time: opening a collapsed one closes the current one, and a click anywhere on a heading outside its controls, or on its chevron, collapses it.

The workspace element (`views/workspace.js`) owns the preview session of the Device screen; [Live preview and cards](preview.md) covers the sessions, the panel renders and the simulator.
