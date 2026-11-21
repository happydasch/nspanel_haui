---
title: Editor architecture
description: The sidebar editor's constraints, data flow, layers, screens, visual foundations, component inventory and tests
---

# Editor architecture

The editor is the static Lit custom panel where devices, panels, themes and updates are configured, and the only surface most users touch. This page names the layer a change belongs to and the contracts it must honour; the preview stage, the panel cards and the browser Nextion simulator are described in [Live preview and cards](preview.md).

## Constraints

- **No build step, no bundler.** The integration is installed by copying `custom_components/nspanel_haui/` into Home Assistant, so `frontend/` holds plain ES modules the browser loads at runtime.
- **Static and unauthenticated.** `web/editor.py` registers the `nspanel-haui-editor` panel element and serves `frontend/` under a content-hashed URL (`<integration version>-<digest>`). No Python file belongs in `frontend/`.
- **Vendored Lit only.** `frontend/vendor/lit/index.js` supplies `html`, `css` and `LitElement`, re-exported by `lit-import.js`. No framework, no bundler, no second Lit copy.
- **No runtime dependency.** `typescript` and `happy-dom` are dev dependencies: they type-check the modules marked `// @ts-check` and run the tests, and never ship with the integration.
- **Restart Home Assistant, then reload the browser** after editing `frontend/`. `haui-editor.js` reloads the page when Home Assistant imports it into a tab that still holds an editor, instead of defining every element a second time.

## How the editor boots

1. `haui-editor.js`, the registered entry, imports `app/shell.js` and re-exports `NSPanelEditor`; the shell element is the editor.
2. The shell receives `hass` and creates one API client (`api/client.js`, over `hass.fetchWithAuth` and the WebSocket) and one store (`store/store.js`). `store/controller.js` is the Lit controller that re-renders the shell on every commit.
3. The store loads the hub entry, panel store, panel types, notifications and the initial device status. It owns the single 5 s status poll: Fleet and a multi-device rail read the aggregate response, which carries rollout progress, while a lone Device screen polls that device. The poll skips a tick while a request is pending or the tab is hidden, and stops when the editor detaches.
4. `app/router.js` parses and serializes the hash and binds back/forward to the store. `fleet-screen.js` and `device-screen.js` turn the route into the screen composition out of `views/` and `ui/`; views pass prepared data and callbacks down and never read the store or the API.
5. `ui/popover.js` is the only anchored popover: one open at a time, placed against the trigger that carries `data-overlay-anchor="<kind>[:<subject>]"`, closed by Escape or an outside click with focus returned to that trigger.
6. A sidebar is one entry of `SIDEBAR_OVERLAY_KINDS` (`store/store.js`: `device-settings`, `panel-catalog`, `panel-editor`, `backups`, `updates`, `theme`, `logs`). `dialogs/confirm.js` and `dialogs/quick-start.js` are the only dialogs.
7. The workspace element (`views/workspace.js`) owns the preview session of the Device screen; [Live preview and cards](preview.md) covers the sessions, the panel renders and the simulator.

## Screens

Two screens and one overlay layer. The hash selects the screen; sidebars, menus, popovers and dialogs overlay it instead of becoming more routes.

### Page structure and navigation

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

The titlebar is sticky and the page scrolls under it, so content that pins to the viewport starts below it at `--haui-header-height` (`styles/tokens.js`). Fleet lays out `minmax(0, 1.65fr)` / `minmax(280px, .85fr)` (`styles/fleet-styles.js`) and Device `minmax(0, 1.65fr)` / `minmax(280px, .9fr)` with the grid areas `workspace side` (`styles/device-layout-styles.js`). Content fills the width with 28px gutters, 14px on narrow screens.

### Shared shell

| Region | Holds | Contract |
|---|---|---|
| Titlebar | HAUI title, current screen or device, notification button and count, Home Assistant's narrow-sidebar toggle | Sticky; no hub or hub configured; no notifications or a nonzero count; narrow mode |
| Global editor footer | `renderFooter()` (`toolbar.js`): integration version, `Dev` badge for prereleases only, GitHub, Documentation | `INTEGRATION_VERSION` is parsed from the hashed asset URL and `docsUrl()` targets `/dev/` on a prerelease, the stable docs root otherwise; the footer stays after the content on loading, error and empty states, and the links never move into a menu |

### Fleet screen regions

| Region | Holds | Data and states |
|---|---|---|
| Device carousel | Scroll-snap row of real device cards between 280px and 320px wide (280px once the row scrolls), arrows, edge fades, swipe anywhere on a card | online/offline, selected, update; the spare width is filled by `deviceSlots` |
| Device card | The panel's home render as the card's whole top (a portrait screen keeps its shape, centred), the strip with status dot and name, update badge and drag grip floating on the render | loading/error cover, selected, dragging |
| Fleet summary | Top of the Device inventory card: health icon, heading, online/total and a sentence, updates-pending and integration-version facts, **Install updates** while any are installable; the card's footer closes with one segment per device in its connection tone (`fleetBar`, `ui/fleet-summary.js`) and never collapses | loading, empty, healthy, warning/error |
| Device inventory | Table of the same devices: device with its connection icon, IP, firmware (`yaml_version`), TFT, actions; rows drag-sort; firmware that differs from the integration version carries a danger **Mismatch** badge | online/offline, stale, update, dragging; the IP column hides at 1120px, TFT at 560px |
| Update rollout | `rolloutCard` (`ui/rollout-card.js`) above the inventory: state sentence, one row per device with kind, state badge, progress and error, cancel per device and **Cancel remaining** | running, done, stopped, cancelled |
| Latest events | The last 24 hours of warnings and errors as a timeline: a level dot on a rail, the message's first line, the device name, relative time and a repeat count; **Reset** restarts the window, **Last 24 hours** restores it | empty, populated, long text; info and debug lines stay in Logs |

Every figure on Fleet has a real source: connection duration from `device_info.connection_uptime` / `last_connection`, IP and versions from status. The bar's segments are each device's current connection tone, not a history.

**Install updates** installs what each connected device is offered, firmware first, and the shell reads `state.hub.rollout` when Fleet polling starts and on every poll while it runs. The carousel measures the real cards and the spare width itself (`views/fleet.js:carouselSlots` and `deviceSlotCount`) and adds enough dashed outlines to cover it, so the last one may be clipped.

The shell scans for unmanaged HAUI devices once the hub is loaded and Fleet lists them under Discovered Devices; the inventory row menu enables, disables and removes a device (`device-events.js`).

Selecting a device is separate from the route: a click on a row outside its own controls, Enter or Space, or the strip under a card's cover selects it, and selecting it again clears it. The selection scopes the log surfaces — **Latest events** names and lists that device only, and **Logs** opens on it — and it comes back when the user returns to Fleet. **Reset** on the timeline is kept in `haui_fleetEventsSince` (`editor-preferences.js`), so a reload keeps the shortened window.

### Device screen regions

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

The lead card heads the side column (`.haui-device-side` is sticky) and moves above the workspace in one column; keyboard focus keeps following the markup, so it runs lead card, side stack, workspace. The Diagnostics card's status icon counts the open findings and opens them in a popover, and expanded it shows two tiles and the hub internals with Copy report.

### Sidebars and overlays

Every sidebar opens 380px wide (`ui/sidebar.js`) and its inner edge resizes it: drag it, or focus it and use the arrow keys, with Home and End at the limits and a double click back to 380px. The width, between 320px and the window less 120px, is shared by all sidebars and kept in `haui_sidebarWidth`; at 600px or less a sidebar becomes a full-screen page without resize edge or scrim.

| Surface | Contents |
|---|---|
| Device settings (`views/device-settings.js`) | Two levels: a landing grid of `settingsTile`s, one per group of `SETTINGS_SECTIONS` (`device-settings-sections.js`: general, home, hardware, buttons, screen, sounds, gestures, advanced), then the open group's page; the footer **Device Enabled** / Cancel / Save is the same on both levels |
| Panel editor (`views/panel-editor.js`) | Panel identity, behaviour and roles, descriptor options grouped by `PageOption.section` with item counts in the headings, inline item editing; `option-rules.js` marks a broken rule as an error that blocks Save, an entity Home Assistant does not know as a warning, and a hub refusal (`serverErrors`) marks the field it names |
| Panel catalog (`views/panel-catalog.js`) | Shared search, a Large/Compact preview toggle (`haui_panelCatalogCompact`), one card per descriptor, popup and copy |
| Backups (`dialogs/backup.js`) | **Backup file** with Export and Import as one pair, then **Copy to other devices** with a `choiceList` per direction |
| Updates (`dialogs/updates.js`) | Status, a scheduled install with **Install now**, **In 1 hour**, **In 1 day** and **Skip this version**, `updateProgress`, the firmware and display rows, **Check for updates** |
| Theme (`dialogs/theme.js`) | Draft palette preview, one theme picker, the icon colours of the palette the background picks, New/Export/Import and Duplicate/Rename/Delete |
| Logs (`dialogs/logs.js`) | The hub's recent lines newest first and grouped by day, a device selector, the shared search field, Copy |
| Notification centre (`views/notifications.js`) | The queued notifications with per-item dismiss; the count is the queue length |
| Panel preview popover | An enlarged thumb with the panel's name and key, opened on hover, focus or tap |
| Toast (`toast.js`) | One transient success, error or info message, `role="status"`, no focus steal |
| Confirmation dialog (`dialogs/confirm.js`) | Destructive confirmation on `HauiDialog`, opened by the action it guards |
| Quick start (`dialogs/quick-start.js`) | The preset chooser of a device without panels (`quick-start-flow.js`, presets in `presets.js`, entity slots resolved from the user's own areas by `preset-entities.js`); a slot the area has no entity for is left out of an item list, so it never blocks the setup |

The settings, editor and catalog sidebars render no header of their own: the sidebar strip carries the title and the close control, and a settings group adds a back control before the title. A sidebar's body scrolls while its footer stays put. Only one side-stack card is expanded at a time: opening a collapsed one closes the current one, and a click anywhere on a heading outside its controls, or on its chevron, collapses it.

The panel editor asks the hub to render the unsaved form (`crud.js:buildPanelConfig`), at once on the first change and then 400 ms after typing pauses; `panelKeyError` validates the key in place and Save stays disabled while a field is marked.

Only one anchored popover is open at a time, and a sidebar may hold one topmost menu. Escape closes the topmost layer first, then the sidebar, and returns from Device to Fleet only when no overlay is open; an outside click closes only the active popover. Closing restores focus to the trigger, opening a sidebar moves focus into it and traps Tab, and focus is never lost on render or save. Use native buttons, links, inputs and `<details>/<summary>`, keep visible focus rings and give every control a meaningful accessible name.

### Where features live

| Feature | Where |
|---|---|
| Add, scan, select, enable and remove devices | Fleet: scan on load and on request, Discovered Devices, the inventory row menu |
| Display, idle, update, gesture, schedule and button settings | The Device settings sidebar, as one draft, opened from the lead card's cog or a Panels-side link |
| Add, edit, remove, reorder, show and hide panels, home and idle roles | Panel groups, row menu, catalog, panel manager, editor sidebar |
| Popup overrides | The Popups group lists extended popups only; the catalog's *Extend a popup* section offers the rest |
| Panel options, items and overrides | The descriptor-driven panel editor with inline item editing (`item-renderers.js`) |
| Themes | **General**'s theme field names the device's theme; the **Themes** button below the side stack opens its colors and icon palettes |
| Updates | The Updates sidebar; **Install updates** on Fleet starts the hub's one-at-a-time rollout |
| YAML import and export | The Backups sidebar, through the server YAML endpoint, never a client parser |
| Notifications | The bell and the notification centre, fed by the store's WebSocket subscription |
| Logs and diagnostics | Device details: the Connection card, the Diagnostics card (`ui/device-diagnostics.js`), the Logs sidebar |
| Confirm remove, reset and install | The confirmation dialog |
| The diagnostics report | **Copy report** at the end of the Diagnostics card's hub internals |
| Option rules | `option-rules.js`, which mirrors `haui/option_rules.py` (`tests/fixtures/option_rules_cases.json` runs through both) |
| A device without panels | The quick start dialog, opened from its device card or the Panels view's setup state |
| Version, docs and GitHub | The global editor footer |

## Visual foundations

The editor draws with Home Assistant's live theme variables and their legacy aliases, never with copied colour ramps or `prefers-color-scheme` overrides. `styles/tokens.js` is the single home of the `--haui-*` aliases and the measured scale; `styles.js` composes the fragments of `styles/`, and an element-local style is reserved for layout specific to that element.

| Token group | Rule |
|---|---|
| Color | HA primary, text, secondary, disabled, surface, divider, error, warning and success tokens, plus a small `--haui-*` alias layer for the meanings HA lacks, each with a fallback. Tonal text uses `--haui-good-text`, `-warn-text`, `-bad-text` and `-accent-text`: the tone mixed with `--primary-text-color` as far as 4.5:1 allows (65% good, 50% warn, 70% bad, 55% accent). An icon in a tone is a graphic and keeps more of it, for 3:1: `--haui-good-icon` at 94%, `--haui-warn-icon` at 71%, `--haui-bad-icon` plain |
| Typography | HA body font, which `styles.js` also gives native buttons and inputs; `--haui-mono` for node, key, IP and versions. The sizes are the 11/13/14/16/18/20/24px scale, each following HA's font size setting, and which one a text takes is its role in [Text sizes](#text-sizes). Weights are 400 for text, 500 for headings, names, labels, values and `strong` (`styles.js` replaces the browser's 700), and 600 only for 11–13px uppercase labels and count bubbles, which track `.05em`. Line heights: `--haui-line-height-tight`, `--haui-line-height-copy` and `--haui-line-height` |
| Spacing | 4/8/12/16/20/24/28/32/40px through `--haui-space-1` to `--haui-space-8` and `--haui-space-10`, mapped onto HA's spacing variables where they exist |
| Radius | `--haui-radius-control` for 8px controls and thumbs, `--haui-card-radius` for 12px cards, `--haui-radius-pill` for pills, `--haui-radius-round` for dots |
| Elevation | `--haui-shadow-card` for cards and `--haui-shadow-overlay` for popovers and sidebars; the preview bezel and the Device screen's cards sit flat on their borders |
| Icon | Home Assistant `<ha-icon>` with MDI names, 18px by default and 14–16px compact, the HAUI brand icon for the mark. Never build SVG `<use>` sprites, which cannot cross shadow roots |
| Motion | 120–150ms hover and colour transitions; the scrim and sidebar entrance keep their 140/180ms timing; every animation is paired with `prefers-reduced-motion` |
| Focus | `--haui-focus-ring` and `--haui-focus-offset`: a visible 2px primary outline with a 2px offset, never suppressed |
| Hover | An item whose border turns `--primary-color` on hover also takes `color-mix(in srgb, var(--primary-color) 8%, var(--card-background-color))`, 10% on small pill controls, never the border alone; a preview filled by a render and a text field keep their own background |

`:host` in `styles.js` is the responsive root (`container-name: haui-editor`), because descendant container queries cannot leave a shadow tree. Its breakpoints are 1120px (simplify the inventory), 980px (collapse the two-column screens), 870px (toolbar spacing), 720px (less row and card detail, stacked role controls), 600px (a sidebar becomes a full-screen page) and 560px (compact Fleet facts, no inventory heading or TFT column). Elements that follow their own width declare their own containers (`haui-workspace`, `haui-panel-info`, `haui-action-card`); anchored popovers float at every width, clamped to the viewport. The panel is registered with `handle_safe_area`, so the title header takes the top inset and the editor host the side and bottom insets.

### Text sizes

A text's size comes from what it is, not from how important it feels: pick its role below and use that token. The levels nest, so a heading stays one level above what it heads and a row's name never matches the card title.

| Level | Token | Size and weight | Used for |
|---|---|---|---|
| Title bar, page | `--haui-text-headline` | 20px / 400, page title 500 | The title bar (Home Assistant's own is 20px regular), the device screen's title, dialog titles |
| Sidebar | `--haui-text-title` | 18px / 500 | A sidebar's title in its header strip, above the sections it holds |
| Card, section | `--haui-text-body` | 16px / 500 | Card and section titles, a folding section heading, an Updates status headline, the title bar's context |
| Name, value | `--haui-text-label` | 14px / 500 | Device, panel and item names, tile and fact values, group headings inside a card, form labels |
| Text | `--haui-text-label` | 14px / 400 | Running text, inputs and selects, button labels, a heading's description, menu items |
| Secondary | `--haui-text-caption` | 13px / 400 | Hints, meta lines, badges and chips, a field's error, timestamps, versions in tables |
| Eyebrow | `--haui-text-eyebrow` | 11px / 600 uppercase, `.05em` | Column heads, the small label over a figure, count bubbles |
| Hero figure | `--haui-text-display` | 24px / 500 | Reserved for a single large figure; no screen uses it today |

- **No size between the steps.** Use a token, never a pixel value or an `em`; `scripts/check_frontend_styles.py` refuses anything off the scale.
- **Weight separates text of one size.** A name or value is 14px at 500, the text around it 14px at 400, never 700.
- **Every heading element gets a size.** An `h1` to `h3` or a `summary` without a rule takes the browser's default, which for an `h2` is about 21px, off the scale.
- **Colour, not size, makes a text quieter.** Secondary text that keeps its role takes `--secondary-text-color` at the same size.
- **Visually hidden text** (`.haui-sr-only`) has no visible size and stays out of the table.
- **The simulator is not editor type.** The display preview draws the Nextion fonts at the display's scale; its text never follows these levels.

Typography utility classes in `styles.js` (`.haui-text-caption`, `.haui-text-label`, `.haui-text-body`, `.haui-text-title`, `.haui-text-display`, `.haui-eyebrow`, `.haui-text-mono`) keep repeated type choices consistent. To check a screen, measure the computed `font-size` and `font-weight` of its visible text: each value should sit in its role's level, and no heading should share size and weight with the rows below it.

`scripts/check_frontend_styles.py` guards the scale (the `font` shorthand and raw line heights included), raw colors, alias ownership, duplicate selectors, repeated style adoption and reduced-motion overrides; `tests/test_frontend_styles.py` covers valid styles and intentional violations. A fragment adopted on its own (`preview-styles.js`, `panel-editor-styles.js`) carries its own `prefers-reduced-motion` overrides, while one that `styles.js` composes into a sheet shares the universal rule of `styles/content.js`.

## Component inventory

Components are Lit template renderers in `frontend/ui/` unless a row names another file. They receive prepared data and callbacks and never read the store or call an API; `views/` composes them, which keeps the markup reusable and every data effect testable at the store and API layer. The custom elements are the exception: `nspanel-haui-editor` (the shell), `nspanel-preview-workspace`, `nspanel-simulator-frame`, `nspanel-panel-editor`, `nspanel-device-settings`, `nspanel-backup-sidebar`, `nspanel-updates-sidebar`, `nspanel-theme-sidebar`, `nspanel-logs-sidebar`, `nspanel-dialog-confirm` and `nspanel-dialog-quick-start`.

Shared form renderers in `form-fields.js` (`renderField`, `renderToggleField`) keep labels, controls, hints and toggle rows on one markup contract across the surfaces; `renderField` takes a `className` for surface-specific layout and `extra` content for a validation message. The low-level controls live in `form-field-controls.js`, which the item renderers import directly to avoid an import cycle, and `form-fields.js` re-exports them. `renderColorField` is the one colour control of the panel and item editors: a text field with a swatch that opens the browser's colour picker and a palette toggle (`aria-expanded`) for recent and preset colours, storing a differently shown value (an RGB565 number, an RGB list) on `change` so a keystroke never rewrites the text being typed.

A field's hint floats under the field while the pointer rests on it or focus is in it, so it never moves the layout, and touch screens keep every hint visible; add `is-persistent` to a status line that must always show (`styles/form-common-styles.js`).

### Primitives

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

### Composites

| Component | Variants and states | Contract |
|---|---|---|
| `deviceCard` | landscape, portrait; fleet, compact rail; online or offline, selected, update, loading or error cover, dragging | Selection is its own button, separate from the grip and the menu, and the carousel names the device |
| `deviceSlots` (`ui/device-slot.js`) | dashed outlines covering the row's spare width | Inert and hidden from assistive technology: no cover, status, scrolling or snapping |
| `deviceRow` | desktop table, compact; online or offline, stale, update, dragging | Table semantics where practical, labelled row actions, no nested control inside one button |
| `deviceRail` | full, narrow; active, offline, pending, overflow | A named group, each chip exposing its device and connection state |
| `fleetSummary`, `fleetBar` | normal, degraded, all offline; loading, empty | Counts are text, and health is readable without colour or animation |
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

### Surface-to-component map

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

Add a component to this inventory before implementing it when a screen needs a visual element that is not listed. Do not make a component per one-off wrapper; split when the markup or state repeats or the accessibility contract differs.

## Boundaries

The editor adds no bundler, no framework and no runtime dependency, no Python file lands in `frontend/`, and every fetch stays in `api/`. A change belongs to the layer that owns its job, and the layers stay apart.

| Directory | Owns | Rule |
|---|---|---|
| `app/` | The shell element (`shell.js`), the router, and the screen compositions `fleet-screen.js` and `device-screen.js` | Wires collaborators; no data fetching, no formatting |
| `store/` | Shared state and actions (`store.js`) and the Lit controller (`controller.js`) | Only store actions write shared state, and there is one status scheduler |
| `api/` | REST and WebSocket transport (`client.js`, `types.js`) | No rendering, no state, one namespaced client |
| `views/` | One render entry per screen region, plus the workspace, panel editor and device settings elements | Prepared data in, callbacks out; no transport, no store |
| `ui/` | The reusable template components above | Data in, callbacks out; no transport, no store |
| `dialogs/` | The dialog and sidebar elements: backup, confirm, logs, quick start, theme, updates | Use the client, never raw `fetch` |
| `previews/`, `virtual/`, `card/` | The hub-render replay, the Nextion simulator and its sessions, the dashboard card (`card.js`, `card-editor.js`) and its card sessions | View-only, through the card sessions and `api.card`; see [Live preview and cards](preview.md) |
| `styles/` | Shared `css` fragments composed by `styles.js` | One module per surface, tokens only from `tokens.js` |
| Top-level modules | `crud.js`, `panel-utils.js`, `panel-models.js`, `panel-roles.js`, `device-*`, `form-field*`, `item-renderers.js`, `theme-*`, `toast.js`, `toolbar.js`, `constants.js`, `localize.js`, `ha-elements.js`, `iconset.js` | No transport outside `api/` |
| Shell collaborators | `device-sidebars.js`, `editor-data.js`, `editor-preferences.js` | Take the editor element as their host, like `toolbar.js`; the shell keeps one-line wrappers |

Every REST and WebSocket call goes through `api/client.js`: no `fetch`, `fetchWithAuth`, `callWS` or `subscribeMessage` outside `api/`. Shared state is written only through store actions, which keep the save-in-flight guard shared by the settings and panels writes, the selected-device status reset and the stale-status drop. New `store/`, `api/` and `views/` modules opt into typing with `// @ts-check`: run `npm ci` once, then `npm run typecheck:frontend`.

## Testing

Frontend tests protect decisions and observable behaviour, not how the markup or styles happen to be written. They run on Node's built-in runner with the vendored Lit bundle, and `happy-dom` supplies the DOM for tests only. Import `tests/frontend/support/browser.mjs` before any module that needs browser globals, render through `support/render.mjs`, find controls with `support/queries.mjs` by role, accessible name, label or text, and take Home Assistant and panel fixtures from `support/hass.mjs`, `support/fixtures.mjs` and `tests/frontend/fake-host.mjs`. `tests/frontend/ui-primitives-preview.html` renders the shipped primitives in their enabled, open, dirty and empty variants for manual review.

A new primitive also needs its demo in `tests/frontend/ui-primitives-preview.js` and a semantic assertion in `ui-primitives.test.mjs`.

### Local checks

| Command | Covers |
|---|---|
| `make test-frontend` (`node --test 'tests/frontend/*.test.mjs'`) | Every editor test |
| `make typecheck-frontend` (`npm run typecheck:frontend`) | The modules marked `// @ts-check` |
| `python scripts/check_frontend_styles.py` | The style rules on this page |

### When to add a test

| Change | Add a test? | Assert |
|---|---|---|
| Pure formatter, mapper or utility | Yes, one case per branch | Exact return values |
| Store action or selector | Yes | The state transition |
| API client method | Yes | Request shape and returned value |
| New UI primitive or composite | Yes | Semantics, accessible name, callback payload |
| View composition | Only its decision branches | Empty state, disabled action, chosen callback |
| Element lifecycle (dialog, workspace, shell) | Yes for the changed branches | Mount, interact, observed event, state or result |
| Simulator behaviour | Yes | Parsed display state or emitted ESP command |
| Styling, layout, colour or spacing | No | Review in the editor preview or the gallery |
| Copy or translation text | No | A translation mapping only when it is the subject |
| Behaviour-preserving refactor | No new test | Existing behaviour tests stay green without markup-driven edits |

### Assertion boundaries

Prefer return values, emitted events and store state; then real DOM roles, accessible names, text, control presence and meaning-carrying attributes (`aria-*`, `disabled`, `href`, `checked`). Use a functional state class such as `is-*` only when no semantic alternative exists. Do not assert CSS text, pixel geometry, inline style strings, Lit `TemplateResult.strings` or `values`, or private members, and do not fabricate an element with `Object.create(prototype)`: dispatch real DOM events instead of reaching into template callbacks.

One test covers one behaviour and one module; split a file around 300 lines or when it covers more than two modules. Tests never depend on run order and leave no global state patched. Delete an assertion whose subject is presentation or an implementation detail, and when a rename only needs an assertion changed because markup or copy moved, remove it instead of re-pinning it.

