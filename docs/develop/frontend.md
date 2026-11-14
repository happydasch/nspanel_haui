---
title: Frontend Architecture
description: How the sidebar editor is structured, how its state flows, its screens, visual foundations, component inventory and tests
---

# Frontend architecture

The sidebar editor is a static custom panel served by Home Assistant. This page
records how it is put together: the constraints, the state flow, the screens and
overlays, the visual foundations and component inventory, the module boundaries
and how it is tested.

## Constraints

- **No build step.** The integration is installed by copying a folder into Home
  Assistant. The editor is plain ES modules loaded at runtime.
- **Static and unauthenticated.** `web/editor.py` serves `frontend/` as static
  files with a content-hash URL, computed at startup and cached by the browser.
  Keep Python out of `frontend/`, and restart Home Assistant, then reload the
  browser, after edits.
- **Vendored Lit.** `frontend/vendor/lit/` provides `html`, `css` and
  `LitElement`; `lit-import.js` re-exports them. No framework or bundler is
  added.
- **No new runtime dependencies.** Node tooling is development-only: it
  type-checks modules that opt in with `// @ts-check` and runs the frontend
  tests.

## Current flow

1. `web/editor.py` registers the sidebar panel and serves
   `frontend/haui-editor.js`, which imports `app/shell.js` and re-exports
   `NSPanelEditor`. The asset URL carries a digest of the frontend files, so
   after a restart that changed them Home Assistant imports the entry again into
   a page that already holds the old editor; the entry then reloads the page
   rather than defining every element a second time.
2. The shell receives `hass` from Home Assistant. It creates one API client
   (`api/client.js`) over `hass.fetchWithAuth` and the websocket connection, and
   one store (`store/store.js`).
3. The store loads the hub entry: the panel store, panel types, the status of
   every device and the notification queue. It owns the selected device and its
   5 s status poller; the all-device poller (also 5 s) runs on the Fleet screen
   and, for the device chips, on the Device screen of a hub with several devices. It also owns the route, the ordered overlay stack and the
   preview intent (`ui.preview`).
4. `app/router.js` binds the hash route to the store. The shell renders one of
   two screens from it: Fleet (`views/fleet.js`) or Device
   (`views/device.js`). Both are Lit templates built from the `ui/` components;
   views receive prepared data and callbacks and never read the store directly.
5. Panel thumbnails and the interactive stage replay the hub's own render: the
   websocket commands of `nspanel_haui/virtual_panel/render` (cards, thumbs) or
   the `virtual_panel`/`live_panel` sessions (`views/workspace.js`). The browser
   has no renderer of its own; it keeps each card's last render
   (`previews/previewer.js`, `localStorage`) and shows it until the new one
   arrives.
6. `views/workspace.js` owns the preview session and reports what the session is
   doing through a `preview-state` event; the Device header owns the Live and
   Idle controls and drives the workspace through its public methods. The
   preview's tools are in the expanded Diagnostics card
   (`ui/device-diagnostics.js`): the entity switch, the reset (the workspace's
   `resetSession`: the sandbox in Simulated, the interaction timer in Live) and,
   in Live, the redraw, which the shell asks of the hub.
7. `ui/popover.js` is the only anchored-popover implementation: one open at a
   time, positioned against the trigger that carries
   data-overlay-anchor="<kind>[:<subject>]", closed by the shell on Escape or an
   outside click, with focus returned to that trigger.
8. Device settings, the schedule and gesture editors, the panel catalog and
   editor, the updates, the theme and the logs open in the modal sidebar
   (`SIDEBAR_OVERLAY_KINDS` in `store/store.js`); the Panels view's side card
   summarizes the selected panel or the list overview. The confirmation dialog
   (`dialogs/confirm.js`) is the only dialog.

## Screens

### Page structure and navigation

There are two screens and one overlay layer. A screen is selected by the hash; sidebars, menus,
popovers, and dialogs overlay the screen rather than becoming more routes.

| Hash | Screen | Main regions | Opens initially |
|---|---|---|---|
| `#/` | Fleet | Device carousel; fleet summary; device inventory; latest events | None |
| `#/device/<device-name>` | Device | Device rail; full-width panel workspace or Preview + contextual side stack | Preview + device details |
| `#/device/<device-name>/panels` | Device | Same regions | Panel list + panel manager |
| `#/device/<device-name>/panel/<panel-key>` | Device | Same regions | Panel editor sidebar for the addressed panel |

The name/key path segments are URI-encoded. Unknown devices resolve to Fleet with an error toast;
unknown panel keys resolve to the device's Panels view with an error toast. The route is reflected in
the hash and is the single source of truth. User navigation between Fleet and Device creates a
browser history entry; changing the selected panel view or normalizing an invalid route replaces the
current entry (no history spam while dragging/toggling). The router handles `hashchange` and
back/forward. The panel segmented control is shareable (`/panels`); open/closed sidebar state and
unsaved drafts are transient and are not encoded in the URL.

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

The titlebar and overlay layer are shared by both screens. Fleet uses a two-column grid of
`minmax(0, 1.65fr)` / `minmax(280px, .85fr)`; Device uses
`minmax(0, 1.65fr)` / `minmax(280px, .9fr)`. The main content is centered and max-width 1440px; the
sidebar has its own scrollable body.

### Shared shell regions

| Region | Anatomy and content | Data / interactions | Required states |
|---|---|---|---|
| Titlebar | HAUI title, current screen/device name, notification button/count (plus HA's narrow sidebar toggle) | Current entry, notification queue; opens existing surfaces | No hub / configured hub; no notifications / nonzero count; narrow mode |
| Global editor footer | `renderFooter()` (`toolbar.js`): centered integration version label; `Dev` badge for prereleases only; GitHub and Documentation links | `INTEGRATION_VERSION` parsed from the content-hashed asset URL; `docsUrl()` targets `/dev/` on prereleases and the stable docs root otherwise | Version unavailable hides version group; Dev badge only for prerelease; both links always present |

The footer stays after the main screen content on Fleet and Device, and on loading, error and
empty-entry states, with its `.editor-footer` markup and styles unchanged; never move the links or
the version into a titlebar menu or About popover. The sidebars' Cancel/Save footer is a separate
local control.

### Fleet screen regions

| Region | Anatomy and content | Live data / interactions | Required states |
|---|---|---|---|
| Device carousel | Scroll-snap horizontal row that centres the card it stops on (the first and the last card stay at their edge); device cards between 280px and 320px wide (280px once the row scrolls); with a mouse the left/right arrows appear on hover/focus, on a touch screen they stay shown while they can scroll; an edge with more cards beyond it fades out (a mask over the cards, not the scrollbar), measured on scroll, resize and every render; a swipe anywhere on a card, its cover included, scrolls the row | `devices.order`, device config/status, update state; card opens the device, arrows scroll by 80% of the visible row (at least 240px), drag handle reorders | empty devices; one device (no arrows); online/offline; pending update; loading/failed cover; dragging/drop target |
| Device card | Real home-panel cover in device orientation; selected check; update badge; status dot; name; current page; drag grip (upper left) and update badge (lower right) on the cover | Home panel render via `previews/simulator-frame.js` and `previewRenderKey`; select opens `#/device/<name>` | empty bezel if no home panel; offline status; stale current-page data; active update; render error |
| Fleet summary | The top of the Device inventory card: the health-coloured icon, its heading, then online/total plus a sentence — all connected, N offline, or none connected — followed by small labelled updates-pending and hub-version facts on the right; **Install updates** appears while any are installable and starts the hub's one-at-a-time rollout. Below it, a thin segment per device in its connection tone (`fleetBar`); one column on narrow screens; at 560px and narrower the heading and the health sentence are hidden, leaving online/total | Counts from actual device/status/update data (online, updates available, total) | no devices; all online; partial/offline; pending updates; no hub version; placeholders until the first status arrives |
| Device inventory | Table of same devices (card is the selector, table is the at-a-glance comparison); columns device (with the **Connection & device** card's connection icon in front of the name), IP, firmware (`yaml_version`), TFT, actions; rows drag-sort. The firmware cell shows a danger **Mismatch** badge below the firmware version when it differs from the integration version. At 1120px and narrower the IP column is hidden, at 560px and narrower the TFT column too; firmware stays visible. Dense table: 46 px rows, 13 px cells, 10 px uppercase column labels, addresses and versions in the mono face. The card grows with the device list up to 720px; a longer list scrolls under its sticky column heads | IP/RSSI/versions and the `integration_version_mismatch` flag from status, update state, device identity/config; row opens device; menu offers supported actions | loading; empty; offline/stale; update; mismatch; dragging; narrow layout |
| Update rollout | `rolloutCard` (`ui/rollout-card.js`) above the inventory while a rollout ran: a sentence for its state, then one row per device with its name, firmware or display, a state badge (Queued, Installing, Done, Failed, Cancelled, Not started), the installing device's `updateProgress` and a failed device's error; a cancel icon button per queued device and **Cancel remaining** while it runs | `state.hub.rollout`, read when Fleet polling starts and every poll while it runs (`api.updates.rollout`); the installing device's `firmware_progress` / `tft_progress` from its status; cancel calls `api.updates.cancelRollout` | idle (hidden); running; done; stopped at a failure; cancelled |
| Latest events | Up to eight different recent status-log entries from devices as a timeline: a hairline rail through a level dot per entry (the level drives the dot's icon and colour), the message's first line (two lines at most), then the device name, relative time and, for a message the device repeated, its count (×N, the newest time shown); debug lines are left out; the header shows the visible count as a count badge. Beside the inventory the card takes the inventory's height (at least 320px) and its list scrolls inside; stacked (980px and narrower) the list scrolls after 480px | `status.logs` strings formatted `[ISO 8601 timestamp with offset] LEVEL message` (the level's full name, written by `HAAdapter.log`), grouped by device, level and message (`latestEvents`), because the hub writes some warnings, such as a missing entity, on every render; **Logs** opens every device's lines in the Logs sidebar | no events; mixed levels; long/truncated messages; one warning repeated many times |

Every figure on Fleet has a real source; the segments under the summary strip are not a history:
each one is a device's current connection tone. Connection duration comes from
`device_info.connection_uptime` / `last_connection`; IP and versions come from status.

### Device screen regions

| Region | Anatomy and content | Live data / interactions | Required states |
|---|---|---|---|
| Device rail | Horizontal compact device chips: status dot, short name, update indicator; selected chip is active | `devices.order`, statuses; selecting navigates to that device | overflow scroll; selected; offline; pending update; narrow icon-only labels only if the icon still has an accessible name |
| Workspace header | Segmented `Preview` / `Panels (count)` selector; preview-only Live and Idle buttons; the preview's tools are in the Diagnostics card | panel view in route; preview mode and idle state; real virtual/live panel session actions | no panels disables Preview; unsupported Live disabled with reason; active/inactive |
| Preview stage | Dark bezel and screen, orientation-aware real simulator/live display, hardware button affordances | Hub-rendered output or `virtual_panel` / `live_panel` session; button touches forwarded to the session; idle/reset forwarded to existing APIs | loading, render error, no panel, offline/disconnected, live connected, sandbox idle, active update |
| Panel groups | Three groups: Navigation, Hidden, Popups. User panels split by `show_in_navigation`; the Popups group lists the extended popups from `system_panels` (`editable`); fixed system panels are not listed (`panel-utils.js:groupPanels`) | Panel array order; drag reorder/move groups; row opens editor; menu actions; home/idle roles | each empty group/drop target; dragging within/across groups; editable popup vs fixed system; overridden vs default; row with no items |
| Device details | Connection hero; facts (current page, IP, firmware, TFT, last connection/disconnect); update status/action; YAML card | `status`, `device_info`, `update`; links to configure, logs, firmware, YAML | never connected / online / offline; facts stale while offline; no IP/version; update available/error/installing |
| Panel manager | Add-panel action, configured count and Navigation count, Home and Idle selectors | Device config's `home_panel`, `idle_panel`; panel catalog action; panels save through the per-device panels endpoint | no panels; unassigned roles; duplicate role selection allowed only if runtime semantics permit |

Panel rows show an explicit drag handle, preview thumb (landscape 72×51; portrait 40×60), panel title,
key, item count/empty indicator, Home/Idle role markers, and overflow action. Fixed System/Blank/
Settings/About entries cannot be overridden or deleted. Popup entries are editable under popup keys;
`validate_panels` remains the authority. Popup overrides keep Edit and Reset to default.

### Sidebars and overlays

| Surface | Contents | Entry / exit |
|---|---|---|
| Device settings sidebar (380px) | General/device identity; display model; dimming/off; schedule; automatic page switching; hardware buttons; display buttons; update channel/auto-update; gestures; notifications; idle/wake; time/date (strftime and locale-aware layout); panel assignments; YAML actions | Configure/menu opens from right with scrim; settings load fresh before opening; Cancel discards draft; Save persists only device settings through the settings endpoint |
| Panel editor sidebar (380px) | Preview in the form; once it scrolls away a small copy with the panel's name, type and key pins above the form (an entity popup with no entity of its own shows a random one of its domain); title/type/key; navigation/home/idle/long-press behavior; descriptor options grouped by `PageOption.section`, the section holding the items open with their count in its heading; item rows that open on click, with stacked move arrows and remove | Row/menu opens; `/panel/<key>` deep-link; Cancel/Save; items are edited inline in the form |
| Panel catalog sidebar (380px) | Sticky search/preview toolbar with the shared pill search field (`.haui-search-field`, labelled by its placeholder, no visible label) and an icon-only Large/Compact toggle of the same height beside it; the shared `config-section-intro` line under the toolbar; shared search across panel types/starter templates/popups/copies; spacing between toolbar and collapsible panel-category, *Start from a template*, popup, and copy sections | Add panel; choosing a starting point creates the draft and transitions to editor; close without footer |
| Device/panel/actions menu | Menu items, dividers, destructive item styling; actions only where supported | Anchored to trigger; Escape/outside click closes and restores focus |
| Updates sidebar (380px) | Status; a scheduled automatic firmware install with **Install now**, **In 1 hour**, **In 1 day** and **Skip this version**; the running install's `updateProgress`; the retry line (next attempt, or stopped); integration, firmware and display version rows (a skipped version marked **Skipped**); check/install action; release picker and local upload; **Update settings**: the **Enable updates** switch beside its title, then the three choices an update needs (**Update channel**, **When a new version is found**, **Check for a new version**) and a folded **Advanced** section with the manifest URL, the check on connect, the display auto-install, the wait before an automatic firmware install and the retry limit (the last two only while something installs by itself). | Opens from **Install update** in the lead card while an update is offered, or the **Updates** action of the Connection & device card; API-driven state; every change saves by itself; close or complete action; no footer |
| Panel preview popover | Larger preview thumbnail with panel name/key | Hover/focus on thumb (hover presentation is not the only way to open it) |
| Notification centre | Current queued notifications and dismiss actions, plus empty state; count is actual queue length | Bell opens; WebSocket notification events update store; close on Escape/outside click |
| Toast | Brief success/error/info message | Live region; auto-dismiss; no focus stealing |
| Theme sidebar (380px) | Draft palette preview, pinned to the top of the scrolling body; intro note in the shared `config-section-intro` style; one theme picker without a visible label (its accessible name is *Color theme*): a radio group of tiles, predefined then custom themes, each a miniature panel in the theme's colors with its name (`ui/theme-selector.js`); one action row under it (New/Export/Import, then icon-only Duplicate/Rename/Delete for a custom theme); icon variant; shared semantic and state-icon color editor; cancel/apply | The **Theme** button in the Preview view's **Manage this device** card; edits the entry-wide custom library and applies a theme selection to the current device |
| Schedule and Gestures sidebars (380px) | `deviceOptionPanel` (`ui/panel-manager.js`): the option's form scrolling above one action — **Save**, which writes the draft and closes the sidebar | The **Schedule** and **Gestures** buttons in the Preview view's **Manage this device** card; closing one drops its unsaved draft |
| Logs sidebar (380px) | The hub's recent log lines, newest first and grouped by day; one row with the device selector, the search and Copy: the device selector is a round icon in front of the search with the native select invisible over it (**All devices**, with the device name on each line, or one device, which changes the icon, tints it and names the device in its title), the search covers message and device in the editor's shared search field (`.haui-search-field`, as in the panel list and the panel catalog); level filter below as a full-width `segmented` control (All/Warnings/Errors, the counts toned warning/danger when not zero); level tag and tint on warnings, errors and debug lines; Copy writes the visible lines oldest first with their full timestamps | The same sidebar on both screens; only the device selected when it opens differs. Device: Diagnostics **Logs** or its log warning count (that device). Fleet: **Logs** beside Latest events (all devices) or ⋯ → Logs (that device); Fleet's one sidebar, and entering a device closes it. Updates with each status poll; no footer |
| Confirmation dialog | Destructive confirmation (remove, reset, install) | `nspanel-dialog-confirm` (`dialogs/confirm.js`) on `HauiDialog`; opened by the action it guards |

Every sidebar opens 380px wide. Its inner edge (`ui/sidebar.js`) resizes it: drag it, or focus it and
use the arrow keys (Home and End go to the limits); a double click restores 380px. The width, between
320px and the window less 120px, is shared by every sidebar and kept in the browser
(`haui_sidebarWidth`). At widths of 600px or less the sidebar becomes a page of its own: it fills the window, has no
resize edge or scrim, and the strip's close button is the way back.

Only one anchored popover is open at a time. A sidebar is modal and may have one topmost menu/popover;
Escape closes the topmost layer first, then sidebar, then returns from Device to Fleet only if no
overlay is open. Outside-click closes only the active popover. Closing restores focus to its trigger;
sidebar opening moves focus into its heading/body and traps Tab until closed. Focus must not be lost on
render or save. Hover previews must also be keyboard reachable. Use native buttons, links, inputs,
`<details>/<summary>` where suitable, visible focus rings and meaningful accessible labels.

### Where features live

| Feature | Location |
|---|---|
| Add/scan/select/remove/manage devices and enabled state | Fleet: scan on load and on request, Discovered Devices with Add/Add All, the inventory row menu (Enable/Disable, Remove with confirmation); carousel and inventory provide selection/reorder |
| Per-device display/idle/update/gesture/time/button settings | Device settings sidebar, preserving all config fields and defaults; Theme, Schedule and Gestures are also exposed as quick-access buttons in the Preview lead card |
| Add, edit, remove, reorder, show/hide panels, home/idle roles | Panel groups, row menu, catalog, panel manager, editor sidebar |
| Popup overrides | Popups group lists extended popups only; the catalog's *Extend a popup* section offers the rest; fixed system panels are not listed; preserve fixed-key protection and popup-to-user-type mapping |
| All panel types/options, entity/action/text/navigate items and overrides | Descriptor-driven panel editor with inline item editing (`item-renderers.js`) |
| Themes and shared color editing | The **Theme** button on the Preview view's **Manage this device** card opens the sidebar for theme selection and shared color editing |
| Simulated and live preview, touch/slider/button input, idle/reset/entity overlay | Workspace preview stage (`views/workspace.js` with the `virtual/` session classes) |
| TFT/firmware check, release selection, upload, install | The Updates sidebar (`dialogs/updates.js`), opened from the Device screen |
| Automatic installs, installing every device | Per device: **When a new version is found** in the Updates sidebar, with its waits and retry limit under **Advanced**. **Install updates** on Fleet (the hub's one-at-a-time rollout with its card) |
| Starter templates and option rules | The catalog's *Start from a template* section (`api.editor.panelTemplates`, `Crud.openAddFromTemplate`); field checks in the panel editor from `option-rules.js`, which mirrors `haui/option_rules.py` |
| YAML import/export | **Backup** card of the Preview side stack, using the server YAML endpoint, not a client parser |
| Notification queue/dismissal | Bell + notification centre (`views/notifications.js`), fed by the store's WebSocket subscription |
| Logs and diagnostics | Device details: facts plus the Diagnostics card (`ui/device-diagnostics.js`: a status line or two tiles and the hub internals with Copy report); logs open in the Logs sidebar |
| Confirm remove/reset/install | The confirmation dialog |
| Editor version, docs, GitHub | The global footer at page bottom: version/Dev badge, GitHub, Documentation |

### Visual foundations

The editor uses Home Assistant's theme: its live CSS variables and legacy aliases, never copied
colour ramps or `prefers-color-scheme` overrides. `styles/tokens.js` adds `--haui-*` aliases only for
meanings HA lacks.

| Token group | Rule |
|---|---|
| Color | HA primary/text/secondary/disabled/surface/divider/error/warning/success tokens. Add a small `--haui-*` alias layer only for missing meanings (good/warn/bad soft fills, soft surface, strong border, screen/bezel gradient, live-preview tint), each with a fallback. Respect HA's active theme. |
| Typography | HA body font; 10/12/13/14/16/20/24px scale; 400/500/600 weights; monospace for node, key, IP and versions. `styles/tokens.js` defines `--haui-text-eyebrow`, `--haui-text-caption`, `--haui-text-label` (13px), `--haui-text-body`, `--haui-text-title`, `--haui-text-display` and `--haui-line-height`. |
| Spacing | 4/8/12/16/20/24/28/32/40px (`--haui-space-*`). |
| Radius | `--haui-radius-control` for 8px controls/thumbs, `--haui-card-radius` for 12px cards, `--haui-radius-pill` for pills and `--haui-radius-round` for dots. |
| Elevation | `--haui-shadow-card` for cards; `--haui-shadow-overlay` for popovers/sidebars; device preview shadows remain distinct inside the bezel. |
| Icon | Home Assistant `<ha-icon>` with MDI icon names, 18px default and 14–16px compact; existing HAUI brand icon for mark. Never build SVG `<use>` sprites; they cannot cross shadow roots. |
| Motion | 120–150ms hover/color transitions; the scrim/sidebar entrance keeps its 140/180ms timing; pair motion with `prefers-reduced-motion`. |
| Focus | `--haui-focus-ring` and `--haui-focus-offset`: visible 2px primary-color outline with 2px offset. Never suppress keyboard focus. |

Typography utility classes in `styles.js` (`.haui-text-caption`, `.haui-text-label`, `.haui-text-body`,
`.haui-text-title`, `.haui-text-display`, `.haui-eyebrow`, `.haui-text-mono`) keep repeated type
choices consistent. The shared interactive-component rules use the same focus ring. Spacing aliases (`--haui-space-1` through `--haui-space-8` and `--haui-space-10`) map the
measured spacing ladder onto HA's spacing variables where available.

The `scripts/check_frontend_styles.py` guard checks the scale, raw colors, alias ownership, duplicate
selectors, repeated style adoption, and reduced-motion overrides; `tests/test_frontend_styles.py` covers both valid styles and
intentional violations. Run it directly with `python scripts/check_frontend_styles.py` when changing
frontend CSS. Every selector with a transition or animation needs a `prefers-reduced-motion` override
in its own file, unless `styles.js` composes that file into a sheet together with the universal
reduced-motion rule of `styles/content.js`; a fragment adopted on its own (`preview-styles.js`,
`panel-editor-styles.js`) carries its own overrides.

Keep the existing `:host` container query (`styles.js`) as the responsive root because descendant
container queries cannot reach outside the component's shadow tree. Its `haui-editor` queries use
1120px (simplify the inventory), 980px (collapse the two-column screens), 870px (toolbar spacing),
720px (reduce row/card detail and stack role controls), 600px (the sidebar becomes a full-screen
page) and 560px (compact Fleet facts, no inventory heading or TFT column). Elements that follow their own width declare named containers
(`haui-workspace`, `haui-panel-info`, `haui-action-card`). Anchored popovers remain floating overlays
at every width, placed beside their trigger and clamped to the viewport. The notification centre
keeps its top-right placement and adjusts its width to the available viewport. The sidebar keeps the
Home Assistant app's `--safe-area-inset-*` free, so its strip and footer never sit under the
status bar or home indicator.

## Visual component inventory

Components are Lit template renderers in `frontend/ui/` unless noted. They receive prepared data and
callbacks; they do not read the store or call APIs. `views/` composes them. This keeps component
markup/styles reusable and makes all data effects testable through the store/API layer. The custom
elements are the exception: `nspanel-haui-editor` (shell), `nspanel-preview-workspace`,
`nspanel-simulator-frame`, `nspanel-panel-editor`, `nspanel-device-settings`,
`nspanel-updates-sidebar`, `nspanel-theme-sidebar`, `nspanel-logs-sidebar` and
`nspanel-dialog-confirm`.
Shared form renderers in `form-fields.js` (`renderField` and `renderToggleField`) keep labels, controls,
hints, and toggle rows on the same markup contract across editor surfaces. `renderField` accepts a
`className` for surface-specific layout and `extra` content for validation messages or supplemental copy.
Where the pointer can hover, a field's hint (`.haui-field-hint`, a child of `.haui-field` or
`.haui-checkbox-wrap`) floats under the field only while the pointer rests on it or keyboard focus is in
it, so it never moves the layout; touch screens keep every hint visible. Add `is-persistent` to a status
line or a list description that must always show (`styles/form-common-styles.js`).
`renderColorField` is the one colour control of the panel and item editors: a text field with a swatch
inside it that opens the browser's colour picker, and a palette toggle (`aria-expanded`) that shows the
recent and preset colours below it. A typed value the field shows differently (an RGB565 number or an
RGB list, both shown as hex) is stored on `change`, so a keystroke never rewrites the text being typed.
The caller owns whether the presets are open: the panel editor per panel, the item draft per item.
The low-level controls live in `form-field-controls.js`, which the
item renderers import directly to avoid an import cycle; `form-fields.js` re-exports them.

For each component below, the contract names its anatomy, variants, states, inputs, emitted actions,
and accessibility behavior. Components are listed once; each surface above is assembled from these
rows plus its view-level layout. A row names the exported function or element; it lives in
`frontend/ui/` unless the row names another file.

### Primitives

| Component | Anatomy | Variants | States | Data in → events out | Accessibility |
|---|---|---|---|---|---|
| `icon` | HA `<ha-icon>` | default, small, large; semantic tone | decorative or labelled | icon name/class → none | Decorative icons `aria-hidden`; icon-only control gets its label on the button, not the glyph |
| `button` / `iconButton` / `backButton` / `addButton` | Native button, optional icon + label, optional `detail` (secondary text after the label, part of the accessible name) | primary, outline, quiet, active, icon-only, back (icon-only arrow), list add row (a `+ label` row with a dashed full-width outline that turns into the primary outline on hover) | hover, pressed, focus-visible, disabled, busy | label/icon/detail/disabled/callback → click | Native button; `aria-label` for icon-only; disabled truly disabled; busy uses `aria-busy` |
| `badge` / `countBadge` / `statusDot` | pill, count pill or dot | neutral, primary, success, warning, danger; online/offline/stale; a count is tinted so it shows on a hovered or open row | normal, empty count (hidden), pending, stale | text/tone/count or connection state → none | Dot has adjacent text or accessible label; color never sole state cue; count announced as notification count |
| `surface` / `sectionHeading` | card, heading band, optional subtitle/badge/actions, body | plain, flush/table, gradient summary, live-tinted | default, live-tinted | heading/actions/body template → action callbacks | Heading levels are sequential; actions remain named controls |
| `segmented` | labelled group of native buttons + optional count (in an optional badge tone) | two-or-more choices | selected, hover, focus, disabled choice | options/value → `select(key)` | `role=group` and `aria-pressed`; keyboard tab order and activation; current choice announced |
| `sortHandle` | visible grip with 32px target | compact (row), overlay (card) | idle, grabbed, dragging, drop target | draggable item ID/kind → start/drop | Grip only: the card, row or group it is dragged onto takes the drop. It is the only reorder affordance — panels and devices carry no Move up/Move down menu entries |
| `emptyState` | icon, title, explanatory line, optional action | fleet, panels, group, notifications, events | action/no-action | title/body/icon/action → action callback | Static message, optional native button; no live-region spam |
| `popover` / `menuItem` | anchored panel, optional arrow; menu rows, separators, danger style | menu, info panel, notification panel | open/closed, focused item, disabled, destructive, loading | anchor key + content/actions → select, close | Trigger `aria-expanded`/`aria-controls`; Escape/outside close; menu keyboard navigation; restore focus; modal overlays manage focus while open |
| `HauiDialog` (`dialogs/haui-dialog.js`) | Base class of the confirmation dialog: labelled heading, close, scrollable body, optional footer | centered dialog, narrow/fullscreen | open/closed, loading, dirty, error | title/open/hass/content → close/confirm/save | Dialog role, labelled by title, modal focus containment/restoration, Escape policy consistent across all dialogs |
| `showToast` (`toast.js`) | transient message with optional icon | info, success, warning, error | visible, dismissed, timeout | message/tone → dismiss | `role=status` polite (assertive only for actionable failure); does not steal focus |
| `renderFooter` (`toolbar.js`) | Version group + GitHub and Documentation links | Stable / prerelease | version missing; prerelease Dev badge; narrow wrapping | embedded asset version + `docsUrl(version)` → external links | Keep existing `.editor-footer` markup/styles, link URLs, `target`/`rel` security attributes, and translated titles; links keyboard-focusable |
| `format.js` | No DOM; pure timestamp/version/RSSI/connection formatters | localized unit/time variants | invalid/missing data handled explicitly | raw status values → display string | Localized output; missing values render explicit unknown/not-reported text, not a false value |

### Composites

| Component | Anatomy | Variants | States | Data in → events out | Accessibility |
|---|---|---|---|---|---|
| `deviceCard` | Screen cover + overlay update/selected/drag affordance; body status/name/node/chips | landscape, portrait; fleet, compact rail | online/offline, selected, update, loading/error cover, dragging | device/config/status/update/preview → select, menu, reorder | Native button selection separate from drag/menu buttons; descriptive name/status; image has useful alt or is decorative |
| `deviceRow` | Grid identity cell, IP, firmware, TFT, actions | desktop table, compact mobile | online/offline, stale, update, dragging | device/status/update → open, menu, reorder | Use table semantics where practical; row action buttons have labels; do not make nested interactive controls inside one button |
| `deviceRail` | Scrollable device chips with dot, name and update mark | full, narrow | active, offline, pending, overflow | ordered devices/status → select | Named navigation/group; each chip button exposes selected device and connection state |
| `fleetSummary`, `fleetBar` | Health line + updates and hub-version figures; `fleetBar` draws one segment per device | normal, degraded, all offline | loading, empty, healthy, warning/error | device/status/update aggregates → none | Counts are text; health statement is available without color/animation |
| `eventList` | Level/tone marker, event text, device/time metadata | info, warning, error | empty, populated, long text | log lines + device names → optional open-logs | Ordered list; level and device conveyed in text; timestamps use `<time>` |
| `panelRow` | Drag handle, thumb, title/key, item metadata, home/idle markers, a **Check settings** warning badge for a saved panel that breaks a rule of its type, menu | navigation, hidden, popup, fixed system | empty items, role, overridden/default, invalid, dragging/drop target | panel/system entry/device roles → edit, preview, menu, reorder/group move | Row isn't one giant button; every action separate named button; fixed entries indicate why edit/delete is unavailable |
| `panelThumb` | Cropped/contained real page render with role markers | landscape, portrait | loading, rendered, unavailable/error, hover/focus enlarged | explicit preview context + panel → open preview | `alt` identifies panel/page; markers have text/accessible labels |
| `deviceDetails` | Connection hero, fact tiles, Updates action, diagnostics card | online, offline, no status | stale facts, update available/installing/error | status/deviceInfo/update/config → configure, firmware, logs, YAML actions, menu | Connection state text; facts as definition list; actions labelled; stale data identified |
| `deviceDiagnostics` | Issue badge, status line or tiles (firmware, hub log; the Hub log tile opens the logs; `connectionTiles` supplies the uptime and Wi-Fi tiles of the Connection & device card), hub internals (transport, listeners, timers) ending with Copy report in the Device details side stack | simple, expanded | unavailable data, stale/offline, update available/installing/error | device status/device info → open logs, choose release, upload/install, close | Facts labelled and marked stale when needed; active activity data must be safe to expose; update controls retain confirmation/state announcements |
| `nspanel-updates-sidebar` (`dialogs/updates.js`) | Updates sidebar: heading/close, one compact status/version card, release/upload/action controls and update settings | sidebar body | checking, available, queued, installing, done, error, current | update state/releases → check, choose release, upload, install, close | Sidebar strip title and close; progress/state announced; destructive/irreversible install explained |
| `previewStage` | Bezel, simulator/live frame, two hardware button targets | landscape, portrait; simulated, live | loading, no panel, error, idle, online, disconnected | preview context/session state → touch, slider, hardware button, idle, reset | Live state named; hardware controls labelled; simulator inputs keyboard-operable; disconnected live mode disabled with explanation |
| `updateProgress` (`ui/update-progress.js`) | The install's steps (Starting, Transferring, Restarting and checking, Done) with the current one marked, a bar and the time it ran with about how long is left | firmware, display; in the Updates sidebar and the rollout card | starting, transferring, verifying, done, failed (text, no bar), past the estimate | `firmware_progress` / `tft_progress` → none | `role="progressbar"` labelled by its kind with a text value; current step `aria-current="step"`; the bar stays below 100 until done because it is an estimate |
| `rolloutCard` (`ui/rollout-card.js`) | Fleet's update rollout: state sentence, device rows with kind, state badge, progress and error, cancel controls | running, done, stopped, cancelled | queued, installing, done, failed, cancelled, not started | rollout snapshot + devices → cancel one or the rest | Ordered list; state as badge text; cancel buttons named by device; errors announced |
| `notificationItem` | Severity icon, title/message, time, dismiss | ordinary, persistent, critical | queued, active, dismissing | notification → dismiss/open | Severity is text/icon plus color; dismiss button has notification-specific label |
| `modalSidebar` / `sidebarFrame` | Fixed right panel (phone at widths of 600px or less: full-screen page), heading/close, scrollable body, sticky footer, desktop scrim; one open from another (for example, a panel editor from the catalog) covers it as a layer | device settings, panel editor, catalog, updates, theme | opening, closing, focused, dirty, saving/error; catalog omits footer | kind/title/body/draft → close, cancel, save, choose item | Modal dialog semantics, labelled heading, focus moved/trapped/restored, Escape closes topmost; Save/Clear labels state |
| `nspanel-device-settings` (`views/device-settings.js`) | Grouped settings sections with shared fields and bottom actions | ordinary / advanced sections | loading, dirty, saving, validation failure | device config + device metadata + option summaries (`deviceOptionSummaries`) + the panel's brightness readings (`deviceBrightness`, the empty brightness fields' placeholders) → field changes, open the theme, schedule, gestures or updates sidebar over it (`open-option`), save/cancel | Each field labelled and described; settings are read before opening and saved through the per-device settings endpoint; grouped sections are keyboard-toggleable; preserve all device-config fields; the form follows the stored config and keeps its unsaved edits on top of it, so a save in a sidebar opened from it is not undone |
| `nspanel-panel-editor` (`views/panel-editor.js`) | Panel identity, behavior switches/roles, descriptor options, item counts in the section headings, inline item editing; a rule an option breaks (`option-rules.js`, the hub's own rules) marks its field or list entry with an error that blocks Save, an entity Home Assistant does not know with a warning that does not, and the hub's refusal of a save (`serverErrors`) marks the field it names until the next edit | user panel, popup override, system popup | new/edit, dirty, saving, duplicate key/error, option error/warning, hub-driven restrictions | panel draft + `PageDescriptor` → change fields, edit items, save/cancel | Label key/title/type; disabled fields explain why; errors associated with inputs; fixed system keys remain non-editable |
| `panelCatalog` (`views/panel-catalog.js`) | Search field + one button card per descriptor, starter template, popup and copy (thumb/icon, title, description, hints; a template's thumb is the hub's render of its keyless panel with example entities in its empty slots), with a top control to switch between large previews and compact side-by-side previews | all supported user panel descriptors | loading, empty search, result, selected/unsupported; large/compact preview layout | descriptors + query + preview layout → search, choose type, change layout, close | Search has label; layout control is a labelled segmented group; cards are buttons with title and description; keyboard selection |
| `panelManager` | The Theme, Schedule and Gestures buttons of the Preview lead card, one row of three, plus the Schedule and Gestures sidebars (`deviceOptionPanel`); Home and idle page assignments live in Device Settings → Home & idle | Preview management area, Schedule and Gestures sidebars, Device Settings form | empty, configured, dirty draft, saving | device panels + config + theme library → open the theme sidebar, edit/save schedule and gestures, assign special pages | The buttons name the setting and carry their summary as a tooltip; the sidebars retain labelled controls and explicit saves |
| `entryList` | The list editors of the schedule (`scheduleEditor`) and the gestures (`gestureEditor`): an add row, then one folding card per entry whose head reads Entry N, the summary (what starts the entry: its window, its swipes; it gives way first), the note (what it does) and a remove button | schedule, gestures | folded, open, just added (only `expandedIndex` opens by state), removed (later cards hand their fold state up one) | entries + summary/note/body renderers → add, remove, toggle | Native `details`/`summary` fold control; the remove button is a named icon button and does not toggle the card |
| `notificationsView` (`views/notifications.js`) | Notification centre: heading/count, queued notification list, per-item dismiss, empty message | viewport-clamped popover | empty, queued, persistent/critical, dismissing, error | store notification queue + update events → dismiss, close | `dialog`/popover label, count, list semantics, per-item dismiss name; focus restore |
| Item renderers (`item-renderers.js`) | Item list rows; add/reorder/remove; inline item fields (entity picker, type, icon, template, options) | entity, skip, text, navigate, action; single or list item | empty, max items, editing, invalid entity/value, saving | item config + `PageOption`/`item_options` + HA states → add/edit/reorder/remove/save/cancel | Entity picker combobox/listbox keyboard contract retained; inline errors labelled; reorder announced |
| `nspanel-theme-sidebar` (`dialogs/theme.js`) | Draft palette preview; one predefined/custom theme dropdown; icon variant; shared semantic and state-icon color editor; whole-theme reset + per-color revert; import/export | built-in/custom theme and device selection | loading, selected, dirty, invalid color, in-use/unsaved confirmation | builtins + saved themes + active device settings → select/edit/create/duplicate/rename/delete/import/export/apply; panel/item colors untouched | Sidebar strip title; each color has named label/value; color is not communicated by swatch alone |
| `nspanel-logs-sidebar` (`dialogs/logs.js`) | Device selector, search, level filter, timestamped log lines with severity and device context | one device, every device | empty, populated, long lines, loading | every device's status logs + devices + selected device → select device, copy, close | Sidebar strip title; log lines in chronological list; preserve readable wrapping and monospace metadata |
| `nspanel-dialog-confirm` (`dialogs/confirm.js`) | Title, explanatory message, cancel and confirm actions | default, destructive | open, busy, failure | action description + labels → confirm/cancel | Focus starts safely; destructive action explicit; Escape/cancel; result/failure announced |
| `renderOptionField` (`form-fields.js`) | Descriptor-driven control renderer and label/description wrapper | bool, int, float, text, color, icon, generic, select, item/list variants | default, templated, validation error, disabled, dirty | `PageOption` + value → typed value change | Correct input for option kind, labels/descriptions linked, constraints/max-items conveyed |
| `renderEntityPicker` (`haui-entity.js`) | Search input + domain-filtered entity list + selected entity | single entity; domain-filtered; clearable where allowed | loading, no results, selected, unavailable entity, keyboard active option | HA states + allowed domain/current value → select/clear | Combobox/listbox semantics and keyboard navigation; entity name/state exposed to assistive tech |
| `renderIconPicker` (`form-field-controls.js`) | Searchable icon list + selected icon and preview | compact field, expanded picker | loading, no results, selected, invalid/unknown value | icon names/current value → search/select | Search label; list options named; selected state exposed; preview decorative |
| `renderColorField` (`form-field-controls.js`) | Color swatch, value control, optional preset palette | inline field, theme sidebar | default, dirty, invalid, disabled | color value/presets → change/save | Each swatch has a color-name/value label; contrast and selection not color-only |
| `scheduleTemplateRender` (`form-field-controls.js`) | Template input + render/preview result | text/action template | idle, rendering, result, render error | template + HA render-template API → edit/render | Button labelled Preview; output/error associated with input and announced without focus steal |



### Surface-to-component map

| Surface | Components used |
|---|---|
| Shared titlebar | `icon`, `button`, `badge`, `popover` / `menuItem` |
| Fleet | `deviceCard`, `sortHandle`, `fleetSummary`, `surface`, `deviceRow`, `eventList`, `emptyState`, `badge` |
| Device rail | `deviceRail`, `statusDot` |
| Workspace header and preview | `segmented`, `button`, `previewStage`, `emptyState`, `popover` |
| Panel groups | `surface`, `panelRow`, `panelThumb`, `sortHandle`, `badge`, `emptyState` |
| Device details / panel manager | `deviceDetails`, `deviceDiagnostics`, `panelManager`, `nspanel-updates-sidebar`, `nspanel-theme-sidebar`, `nspanel-logs-sidebar`, `surface`, `button`, `badge` |
| Device settings / panel editor / catalog sidebars | `modalSidebar`, `nspanel-device-settings`, `nspanel-panel-editor`, `panelCatalog`, `renderOptionField`, `renderEntityPicker`, `renderIconPicker`, `renderColorField`, `scheduleTemplateRender`, item renderers, `panelThumb` |
| Notification centre | `notificationsView`, `popover`, `notificationItem`, `emptyState`, `button` |
| Confirmation dialog | `HauiDialog`, `nspanel-dialog-confirm`, `button`, `showToast` |
| App feedback | `toast`, `emptyState` |

Add a component to the inventory before implementing it if a screen needs a visual element not listed
here. Avoid making a component per one-off wrapper; split when it has repeated markup/state or a
separate accessibility contract.

## Screen details

- `frontend/ui/` holds the render primitives and the data-driven Fleet/Device components. Views receive
  prepared data and callbacks; they never read the store or the API. `frontend/panel-utils.js` owns the
  panel grouping, move state and role markers.
- `frontend/styles/tokens.js` is the single home for HA-backed `--haui-*` aliases and the measured
  scale; `styles.js` composes shared tokens, primitives, panel pills, entries, form/dialog content
  and per-screen fragments. `styles/content.js` is one fragment, not an aggregator. Device styles are
  split between `styles/device-layout-styles.js` and `styles/device-panel-styles.js`; shared firmware
  and preview rules live in `styles/updates-styles.js` and `styles/preview-styles.js`. Logs, theme, and
  panel-editor surfaces keep their focused rules in `styles/logs-styles.js`,
  `styles/theme-sidebar-styles.js`, and `styles/panel-editor-styles.js`. The shell uses `editorStyles`,
  dialogs use `dialogStyles`; the preview workspace and the simulator frame, which draw the stage and
  the display, adopt `previewStyles` themselves (the shell does neither). The workspace element is its
  own `haui-workspace` container, so the stage follows the workspace's width, not the editor's.
  Element-local styles are reserved for layout specific to that element.
- `frontend/app/router.js` parses/serializes the Fleet and Device hashes and binds history to the store.
- Fleet: scroll-snap carousel of real home-panel covers with arrows that disable at the scroll extents, a
  summary that waits for the first status payload, the inventory (`Firmware`/`TFT` columns), and a
  scrollable latest-events timeline of dated entries from the previous 24 hours (repeated messages are
  grouped), plus one anchored device-actions menu shared by cards and rows.
- Device: a head with the back button to Fleet, the device name and the device rail (shown with more
  than one device; its chips collapse into a dropdown while they do not fit beside the title, measured
  by the shell with `ui/device-rail.js:railOverflows`), a workspace header with the Preview/Panels segmented control plus the Live
  and Idle controls, the panel workspace, and the
  context side stack. At 600px or less, the segmented control shows icons only while Live and Idle
  show text only.
- Panel list: three groups (Navigation, Hidden, and Popups — extended popups only) with band headers, rows carrying a
  hub-rendered thumbnail, Home/Idle markers, item counts and one anchored actions menu. Hovering a
  thumbnail with the mouse, or tapping or pressing it, enlarges that same render beside it
  (`ui/panel-thumb.js`). A row is dragged
  by its grip; only entries marked `sortable` (user panels) drag, every other row shows its grip
  disabled so the rows line up; a drop on the upper or lower half of a row lands before or after it, and a drop on a
  group's heading or empty area lands at its end (no separate drop zones are drawn).
  A drop within a group reorders it without moving the other group's rows; a drop across Navigation and
  Hidden flips `show_in_navigation` and lands at the drop position in a single save
  (`crud.js:movePanelToGroup`). Fixed system rows explain why they cannot be edited; popup overrides keep
  edit and reset.
- Preview: `views/workspace.js` owns the `virtual_panel`/`live_panel` session (touches, slider drags, both
  hardware buttons, brightness, entity hover, idle and reset) and hands the drawing to
  `ui/preview-stage.js`, which owns the bezel, the live tint and the loading/no-panel/error states. The
  stage fills the workspace card edge to edge on the dark screen gradient; in Live mode the card itself
  takes the live tint. The
  workspace reports `{mode, idle, ready, canInteract, connected}` through a `preview-state` event, so the
  header follows the session instead of keeping a second copy of its state.
- Panel list extras: a search field in the workspace header narrows the groups to matching rows
  (reordering is off while it is active); the row menu duplicates a panel
  (`crud.js:duplicatePanel`); menus move with the arrow, Home and End keys.
- Panel selection: a click on a row outside its own controls (title, actions, grip, menu), Enter or
  Space selects it (`ui/panel-row.js`, `aria-current`), and selecting it again clears the selection.
  The shell keeps the key in `_selectedPanelKey`, drops it when the panel is gone or the device
  changes, and reports it to `views/panel-list.js`; the Panels view's side card describes what is
  selected (`ui/panel-info.js`), and shows the list's overview while nothing is.
- Panel details card: `panelSideCard` renders the selected panel as the hub draws it (the same
  `renderSimulatorPreview` render as the row thumbnail), its type icon, label and description, the
  facts that decide its behaviour (type, key, group, item count, Home/Idle role) and the row menu's
  actions (Edit, Duplicate, Delete; a popup override gets Edit and Reset to default). Its model comes
  from `shell.js:_panelSideModel`, and it sits in the side stack under the view's lead card.
  The render is its own toggle (`panelSideCard` model: `onTogglePreview`): large, it takes the card's
  width with the description under it; folded, it is a thumbnail with the description beside it, and
  the facts and actions stay. The choice is one `localStorage` flag (`haui_panelPreviewFolded`), so it
  holds for every panel of the browser. With nothing selected the same function renders the overview
  instead: one row per group with its count badge, a tile per role — the role's icon beside its
  label with the configured Home panel (or the hub's fallback to the first navigation panel) and
  Idle page (`idlePanelKeys`, summarised as *Clock and 2 more*) under it — then
  two hints (drag to reorder, the row menu's actions).
- Panel editor: a preview at the top of the sidebar asks the hub to render the form's unsaved state
  (`crud.js:buildPanelConfig`, debounced 400 ms); the key and PIN fields validate in place
  (`panelKeyError`) and Save is disabled while one is marked. The catalog shows each panel type with
  the hub's render of a new panel using fixed representative sample data shared with the card-gallery
  generator (preview-only; no Home Assistant entities are required and nothing is saved), and also
  offers a copy of any panel of the hub (`crud.js:openAddFrom`). The catalog's Large/Compact preview
  size is one `localStorage` flag (`haui_panelCatalogCompact`), so it opens the way it was left.
- Bulk updates: Install updates on Fleet installs what each connected device is offered, firmware
  first.
- Device management: the shell scans for
  unmanaged HAUI devices once the hub is loaded (`_scanDevices`) and Fleet lists them under Discovered
  Devices; the inventory row menu enables, disables and removes a device (`device-events.js`), and the
  lead card of the Preview and Panels views opens the settings with the cog beside its title; the
  Connection & device card opens the updates.
- Row actions: panel rows and inventory rows end in the same two quiet buttons (`haui-row-action`):
  Edit (panels) or Settings (devices), then More. Editable popups have both, fixed system rows none.
  On a device card the drag grip sits in the cover's upper left corner and the update badge in its
  lower right.
- Sidebar forms: the device settings, the panel editor and the panel catalog render without a header of
  their own; the sidebar strip carries the title and the close control.
- Lead card: each view's first card is its next actions (`ui/action-card.js`), tinted with the primary
  colour and never collapsed, so it stands apart from the side stack. Panels: the panel and navigation
  counts, Add panel and Settings (`panelActions`). Preview: Settings (the cog beside its title) and Add panel,
  led by Install update while an update is offered (`ui/device-actions.js`); below its actions the same card carries the three
  device options as plain buttons in one row — Theme, Schedule and Gestures (`ui/panel-manager.js`), always
  side by side at any card width, dropping their icons before a label truncates. Each one only opens its
  editor: Theme the shared theme sidebar, Schedule and Gestures their own sidebar (`deviceOptionPanel`), so
  the card never grows when an option is opened. A button's tooltip states what its option holds (the
  selected theme, the entry counts). It heads the side column beside the workspace
  (`.haui-device-side`, sticky: it stays in view while a long workspace scrolls);
  once the layout is one column it moves above the workspace and the side stack below it (grid areas
  of `.haui-device-layout`; keyboard focus still follows the markup: lead card, side stack, then
  workspace), and at 560px or wider its actions sit beside its heading.
- Side stack: a column of `surface` cards. In the Preview view: Connection & device, Diagnostics and
  Backup (YAML import and export). Only one side-area card can be expanded at a time: opening a
  collapsed card closes the currently expanded one; clicking the expanded card collapses it. The
  selection is remembered per browser (`haui_deviceDetailsExpanded`, `haui_diagnosticsExpanded`,
  `haui_panelCardsExpanded`), and older saved preferences with multiple expanded cards are normalized
  to one on load. Each card collapses as a whole on a click anywhere on the heading outside its controls, or on its chevron
  (the keyboard control). The Connection &
  device heading also carries the connection state as one icon (Wi-Fi strength in shape and colour
  while connected, crossed out while not; its dot shows the connection state) whose card opens on hover, focus or tap with the state, uptime or last
  seen, signal, SSID, IP, last connection and the stale note. Collapsed, the card shows its heading
  only; expanded (the default), four tiles (uptime, Wi-Fi, current page, IP) with a label
  and value only, dimmed while stale; hover, focus or a tap opens a card under the tile with the full
  value and the remaining facts (last connection or disconnection, disconnects and the latest drop;
  SSID and IP; last panel update; SSID and signal). The versions stay out of the card: **Diagnostics**
  and the **Updates** sidebar own them. Diagnostics shows a status line and expands to two tiles of
  the same kind (`ui/info-tile.js`; integration, YAML and display versions) and the hub internals, which end with Copy
  report; a tap on the Hub log tile opens the logs instead of its card.
  In the Panels view the side column keeps its usual place: the lead card (Add panel, Settings) on
  top, the selected panel's card under it, and the panel list fills the workspace. Home/Idle are
  assigned in Device Settings → Home & idle, and panel thumbnails carry
  the Home, Idle and edited-popup markers; the Home marker follows the hub's fallback to the first
  navigation panel while no home panel is configured. The modal sidebar is an
  `<aside class="haui-modal-sidebar">` over the page. `ui/sidebar.js` frames the modal
  side stack (labelled strip, close control, 380px body);
  device details report the connection facts, mark them stale while offline, and carry the diagnostics
  card (`ui/device-diagnostics.js`: a status icon before the title that counts the issues, a status line that expands to two tiles and the
  hub internals, Copy report at their end; expanded, it also holds the preview's tools: Show entities, Reset sandbox (only while the sandbox holds a simulated state), and in Live
  Reset interaction and Redraw display), plus the firmware, logs and YAML actions; Device Settings assigns Home/Idle
  pages under Home & idle.
- Overlays: `ui/popover.js` is the single anchored-popover implementation (one open at a time, placed
  against its trigger, Escape/outside click close with focus returned). The panel menu,
  device menu, notification centre and firmware surface use it; the notification centre and firmware
  surface keep their own geometry and are marked `staticPlacement`.
- Panel authoring: the searchable catalog seeds the descriptor-driven panel editor in the side stack. Item
  editing stays **inline** in that editor (the item renderers in `item-renderers.js`); the section holding the item list opens with the form and
  shows the item count in its heading.
- Sidebar forms scroll while their Cancel/Save footer (where they have one) stays put.
- The confirmation dialog is the only dialog; the theme editor and logs are sidebar elements
  (`dialogs/theme.js`, `dialogs/logs.js`), the Updates sidebar is the `nspanel-updates-sidebar` element
  (`dialogs/updates.js`), and diagnostics live in the side stack. All of them are styled through
  `dialogStyles`.
- The store has route, ordered overlay and preview-intent state plus a persisted `device_order`;
  the device-order endpoint normalizes it against the actual devices.
- `frontend/ui/format.js` formats relative timestamps, reported versions and short uptime labels.
- `tests/frontend/ui-primitives-preview.html` renders the shipped primitives and their
  enabled/disabled, open/closed, dirty/error and empty/loading variants for manual review.

## Boundaries

| Directory | Owns | Rule |
|-----------|------|------|
| `app/` | The shell element (`shell.js`) and the router | Wires collaborators; no data fetching or formatting |
| `store/` | Shared state and actions (`store.js`), the Lit controller | Only store actions write shared state; one poller per scope |
| `api/` | REST and WebSocket transport (`client.js`, `types.js`) | No rendering or state; one namespaced client |
| `views/` | One render entry per screen region, plus the `workspace`, `panel-editor` and `device-settings` elements | Prepared data in, callbacks out; no transport, no store |
| `ui/` | Reusable template components (the inventory above) | Data in, callbacks out; no transport, no store |
| `dialogs/`, `previews/`, `virtual/` | Sidebar and dialog elements, the hub-render replay, the Nextion simulator and its sessions | Use the client, never raw `fetch` (the simulator sessions own their subscriptions) |
| `styles/` | Shared `css` fragments composed by `styles.js` | One module per surface |
| top-level modules | Shared helpers: `crud.js`, `panel-utils.js`, `device-*.js`, `form-field*.js`, `item-renderers.js`, `theme-*.js`, `toast.js`, `toolbar.js`, `constants.js`, `localize.js`, `ha-elements.js`, `iconset.js` | No transport outside `api/` |

Every REST and WebSocket call goes through `api/client.js`; no `fetchWithAuth`,
`callWS` or `subscribeMessage` outside `api/`. Shared state is written through
store actions, which keep the save-in-flight guard shared by the per-device
settings and panels writes, the selected-device status reset and the
stale-status drop. New `store/`, `api/` and `views/` modules carry
`// @ts-check` (`npm ci` once, then `npm run typecheck:frontend`).

The preview context is explicit: `{ entryId, device, deviceConfig, panels,
theme, deviceInfo, api }`. `previews/previewer.js` and `previews/simulator-frame.js`
depend on that object, not on the editor element.

## Testing

Frontend tests should protect decisions and observable behavior, not preserve a snapshot of how the
markup or styles happen to be written. The tests use Node's built-in runner and the vendored Lit
bundle; `happy-dom` supplies a real DOM for tests only and is a dev dependency, never shipped with
the integration. Import `tests/frontend/support/browser.mjs` before importing any module that needs
browser globals. Use `support/render.mjs` to render Lit templates or mount custom elements and
`support/queries.mjs` to locate controls by role, accessible name, label, or text. Shared HA and
panel/layout fixtures live in `support/`.

### When to add a test

| Change | Add a test? | Assert |
|---|---|---|
| Pure formatter, mapper, or utility | Yes, one case per branch | Exact return values |
| Store action or selector | Yes | State transition |
| API client method | Yes | Request shape and returned value |
| New UI primitive | Yes | Semantics, accessible name, callback payload |
| View composition | Only for its decision branches | Empty state, disabled action, chosen callback |
| Element lifecycle (dialog, workspace, shell) | Yes for changed lifecycle branches | Mount, interact, observe event/state/result |
| Simulator behavior | Yes | Parsed display state or emitted ESP command |
| Styling, layout, color, or spacing | No | Review in the preview/gallery |
| Copy or translation text | No | Test a translation mapping only when it is the subject |
| Behavior-preserving refactor | No new test | Existing behavior tests pass without markup-driven edits |

### Assertion boundaries

Prefer return values, emitted events, and store state; then real DOM roles, accessible names, text,
control presence, and meaning-carrying attributes (`aria-*`, `disabled`, `href`, `checked`). Use a
functional state class such as `is-*` only when no semantic alternative exists. Do not assert CSS
text, pixel geometry, inline style strings, Lit `TemplateResult.strings`/`values`, private members,
or fabricate an element with `Object.create(prototype)` and assigned internals. Dispatch real DOM
events instead of extracting template callback indices.

A test covers one behavior and one module. Split files around 300 lines or when they cover more than
two modules. Tests must not depend on run order or leave global state patched. Delete assertions whose
subject is presentation, behavior already covered at a lower layer, or implementation detail. When a
rename or refactor only requires changing an assertion because markup or copy moved, remove that
assertion instead. Removed visual pins are reviewed in the editor preview or the card gallery; they
are not replaced with new CSS or geometry tests.

## Trade-offs

One store and one client are easier to reason about than per-domain modules:
the editor is a single page that loads one hub entry, and the pollers,
notifications and saves all touch the same device map. Split a file when it
stops having one reason to change, not when it grows; the store actions are
already grouped by domain and the API client is namespaced by route.
