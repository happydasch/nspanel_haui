---
title: Frontend Architecture
description: How the sidebar editor is structured, how its state flows, and the agreed plan for the v0.5 dashboard
---

# Frontend architecture

The sidebar editor is a static custom panel served by Home Assistant. This page
records how it is put together today, the boundaries new code must respect, and
the information architecture the v0.5 dashboard is built from.

The visual target is the static prototype in `design/dashboard-prototype.html`
(open it from a checkout; it is a repository artifact, not a docs page). It
uses mock data and is the reference for layout and interaction, not for
service-call wiring.

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
8. Device settings and option editors, panel editing and logs use the modal sidebar; the
   Panels view's side card summarizes the selected panel or the list overview. The
   former Device Manager and Device Info dialogs are gone. Confirmation and other
   specialized overlays remain separate UI elements.

## Target v0.5 dashboard

`design/dashboard-prototype.html` is the **visual reference**, not production markup or behavior. It
is a 3,134-line, standalone mockup: inline CSS, SVG sprite, hard-coded device data, and template-string
renders. It makes no API calls. The target keeps its layout and visual hierarchy while using the real
store, HA APIs, translation system, panel descriptors, and simulator. Do not port its mock data,
`innerHTML` rendering, client-side YAML parser, or fake preview behavior.

The existing editor remains the feature/behavior source of truth during migration. The target must
retain device management, panel types and options, popup overrides, all item kinds, device settings,
colors, firmware/TFT flows, notifications, logs, YAML import/export, live/simulated preview, and
system-panel rules. This section fixes the information architecture and reusable visual inventory
before implementation begins.

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
│  Device carousel (264px cards; 196px covers; horizontal snap)                             │
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
`minmax(0, 1.65fr)` / `minmax(300px, .85fr)`; Device uses
`minmax(0, 1.65fr)` / `minmax(280px, .9fr)`. The main content is centered and max-width 1440px; the
sidebar has its own scrollable body. The existing editor footer remains at the bottom of the page,
after the screen content, using the existing `renderFooter()` and `.editor-footer` styling on Fleet
and Device screens and on loading/error states. Do not replace it with a titlebar menu or change its
integration version, Dev badge, GitHub, or Documentation links.

### Shared shell regions

| Region | Anatomy and content | Data / interactions | Required states |
|---|---|---|---|
| Titlebar | Existing HAUI title, current screen/device name, notification button/count (plus HA's narrow sidebar toggle) | Current entry, notification queue; opens existing surfaces | No hub / configured hub; no notifications / nonzero count; narrow mode |
| Global editor footer | The current `renderFooter()` output, unchanged: centered integration version label; `Dev` badge for prereleases only; GitHub and Documentation links | `INTEGRATION_VERSION` parsed from the content-hashed asset URL; `docsUrl()` targets `/dev/` on prereleases and the stable docs root otherwise | Version unavailable hides version group; Dev badge only for prerelease; both links always present |

Footer placement and preservation are intentional: it stays after the main screen content on Fleet and
Device, and on loading, error, and empty-entry states. Reuse the current `renderFooter()` and
`.editor-footer`, `.footer-version-group`, `.footer-version`, `.footer-dev-badge`, and `.footer-link`
styles verbatim. Do not move the links/version into a titlebar menu or About popover. The sidebars'
Cancel/Save footer is a separate local control, not a replacement for this global footer.

### Fleet screen regions

| Region | Anatomy and content | Live data / interactions | Required states |
|---|---|---|---|
| Device carousel | Scroll-snap horizontal row; 264px device cards with 196px screen covers; left/right arrows appear on hover/focus; a swipe anywhere on a card, its cover included, scrolls the row | `devices.order`, device config/status, update state; card opens the device, arrows scroll by one card, drag handle reorders | empty devices; one device (no arrows); online/offline; pending update; loading/failed cover; dragging/drop target |
| Device card | Real home-panel cover in device orientation; selected check; update badge; status dot; name; current page; drag grip (upper left) and update badge (lower right) on the cover | Home panel render via `previews/simulator-frame.js` and `previewRenderKey`; select opens `#/device/<name>` | empty bezel if no home panel; offline status; stale current-page data; active update; render error |
| Fleet summary | The top of the Device inventory card: the health-coloured icon, its heading, then online/total plus a sentence — all connected, N offline, or none connected — followed by small labelled updates-pending and hub-version facts on the right; **Install updates** appears while any are installable. Below it, a thin segment per device in its connection tone (`fleetBar`); one column on narrow screens | Counts from actual device/status/update data (online, updates available, total) | no devices; all online; partial/offline; pending updates; no hub version; placeholders until the first status arrives |
| Device inventory | Table of same devices (card is the selector, table is the at-a-glance comparison); columns device (with the **Connection & device** card's connection icon in front of the name), IP, firmware (`yaml_version`), TFT, actions; rows drag-sort. The firmware cell shows a danger **Mismatch** badge below the firmware version when it differs from the integration version. At narrower widths, the IP column is hidden while firmware and TFT stay visible. Dense table: 46 px rows, 13 px cells, 10 px uppercase column labels, addresses and versions in the mono face | IP/RSSI/versions and the `integration_version_mismatch` flag from status, update state, device identity/config; row opens device; menu offers supported actions | loading; empty; offline/stale; update; mismatch; dragging; narrow layout |
| Latest events | Up to eight different recent status-log entries from devices as a timeline: a hairline rail through a level dot per entry (the level drives the dot's icon and colour), the message's first line (two lines at most), then the device name, relative time and, for a message the device repeated, its count (×N, the newest time shown); debug lines are left out; the header shows the visible count as a chip | `status.logs` strings formatted `[ISO 8601 timestamp with offset] LEVEL message` (the level's full name, written by `HAAdapter.log`), grouped by device, level and message (`latestEvents`), because the hub writes some warnings, such as a missing entity, on every render; **Logs** opens every device's lines in the Logs sidebar | no events; mixed levels; long/truncated messages; one warning repeated many times |

The prototype's availability percentage, spark bars, static "mostly healthy" line, per-device
activity arrays, firmware/display/node fields, and fixed two-notification count are fabricated or
have no backend source. Do not display them as real facts. The segments under the summary strip are
not a history either: each one is a device's current connection tone. Connection duration comes from
`device_info.connection_uptime` / `last_connection`; IP and versions come from status.

### Device screen regions

| Region | Anatomy and content | Live data / interactions | Required states |
|---|---|---|---|
| Device rail | Horizontal compact device chips: status dot, short name, update indicator; selected chip is active | `devices.order`, statuses; selecting navigates to that device | overflow scroll; selected; offline; pending update; narrow icon-only labels only if the icon still has an accessible name |
| Workspace header | Segmented `Preview` / `Panels (count)` selector; preview-only Live and Idle buttons; the preview's tools are in the Diagnostics card | panel view in route; preview mode and idle state; real virtual/live panel session actions | no panels disables Preview; unsupported Live disabled with reason; active/inactive |
| Preview stage | Dark bezel and screen, orientation-aware real simulator/live display, hardware button affordances | Hub-rendered output or `virtual_panel` / `live_panel` session; button touches forwarded to the session; idle/reset forwarded to existing APIs | loading, render error, no panel, offline/disconnected, live connected, sandbox idle, active update |
| Panel groups | Four groups: Navigation, Hidden, Popups, System. User panels split by `show_in_navigation`; popup and fixed system entries come from `system_panels` (`editable` distinguishes them) | Panel array order; drag reorder/move groups; row opens editor; menu actions; home/idle roles | each empty group/drop target; dragging within/across groups; editable popup vs fixed system; overridden vs default; row with no items |
| Device details | Connection hero; facts (current page, IP, firmware, TFT, last connection/disconnect); update status/action; YAML card | `status`, `device_info`, `update`; links to configure, logs, firmware, YAML | never connected / online / offline; facts stale while offline; no IP/version; update available/error/installing |
| Panel manager | Add-panel action, configured count and Navigation count, Home and Idle selectors | Device config's `home_panel`, `idle_panel`; panel catalog action; save through store | no panels; unassigned roles; duplicate role selection allowed only if runtime semantics permit |

Panel rows show an explicit drag handle, preview thumb (landscape 72×51; portrait 40×60), panel title,
key, item count/empty indicator, Home/Idle role markers, and overflow action. Fixed System/Blank/
Settings/About entries cannot be overridden or deleted. Popup entries are editable under popup keys;
`validate_panels` remains the authority. Preserve custom popup behavior and system reset actions from
the current editor.

### Sidebars and overlays

| Surface | Contents | Entry / exit |
|---|---|---|
| Device settings sidebar (380px) | General/device identity; display model; dimming/off; schedule; automatic page switching; hardware buttons; display buttons; update channel/auto-update; gestures; notifications; idle/wake; time/date (strftime and locale-aware layout); panel assignments; YAML actions | Configure/menu opens from right with scrim; Cancel discards draft; Save persists via panel store |
| Panel editor sidebar (380px) | Preview in the form; once it scrolls away a small copy with the panel's name, type and key pins above the form (an entity popup with no entity of its own shows a random one of its domain); title/type/key; navigation/home/idle/long-press behavior; descriptor options grouped by `PageOption.section`, the section holding the items open with their count in its heading; item rows that open on click, with stacked move arrows and remove | Row/menu opens; `/panel/<key>` deep-link; Cancel/Save; item editing opens existing item editor dialog |
| Panel catalog sidebar (380px) | Sticky search/preview toolbar with a pill search field in Home Assistant's outlined style (labelled by its placeholder, no visible label) and an icon-only Large/Compact toggle of the same height beside it; the shared `config-section-intro` line under the toolbar; shared search across panel types/popups/copies; spacing between toolbar and collapsible panel-category, popup, and copy sections | Add panel; choosing a starting point creates the draft and transitions to editor; close without footer |
| Device/panel/actions menu | Menu items, dividers, destructive item styling; actions only where supported | Anchored to trigger; Escape/outside click closes and restores focus |
| Updates sidebar (380px) | Integration, firmware and display version rows; update state; note; check/install/queue action; release picker and local upload where existing flow supports them | Opens from the update action or ⋯ → Firmware and display updates; API-driven state; close or complete action; no footer |
| Panel preview popover | Larger preview thumbnail with panel name/key | Hover/focus on thumb (hover presentation is not the only way to open it) |
| Notification centre | Current queued notifications and dismiss actions, plus empty state; count is actual queue length | Bell opens; WebSocket notification events update store; close on Escape/outside click |
| Toast | Brief success/error/info message | Live region; auto-dismiss; no focus stealing |
| Theme sidebar (380px) | Draft palette preview; one **Color theme** picker in Home Assistant's filled form style, with the selected theme's palette chip inside the field (`ui/theme-selector.js`); one action row under it (New/Export/Import, then icon-only Duplicate/Rename/Delete for a custom theme); intro notes in the shared `config-section-intro` style; icon variant; shared semantic and state-icon color editor; cancel/apply | The **Theme** button in the Preview view's **Manage this device** card; edits the entry-wide custom library and applies a theme selection to the current device |
| Schedule and Gestures sidebars (380px) | `deviceOptionPanel` (`ui/panel-manager.js`): the option's form scrolling above one action — **Save**, which writes the draft and closes the sidebar | The **Schedule** and **Gestures** buttons in the Preview view's **Manage this device** card; closing one drops its unsaved draft |
| Logs sidebar (380px) | The hub's recent log lines, newest first and grouped by day; level filter (All/Warnings/Errors with counts); search over message and device; level tag and tint on warnings, errors and debug lines; Copy writes the visible lines oldest first with their full timestamps | Device: Diagnostics **Logs** or its log warning count. Fleet: **Logs** beside Latest events (every device, the device name on each line) or ⋯ → Logs (one device); the only sidebar Fleet has, and entering a device closes it. Updates with each status poll; no footer |
| Existing dialogs | Item editing, destructive confirmation | Keep existing `nspanel-dialog-*` elements and behavior until their phase migrates; live preview is a Device workspace component |

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

### Feature placement / parity

| Existing feature | New location |
|---|---|
| Add/scan/select/remove/manage devices and enabled state | Fleet: scan on load and on request, Discovered Devices with Add/Add All, the inventory row menu (Enable/Disable, Remove with confirmation); carousel and inventory provide selection/reorder |
| Per-device display/idle/update/gesture/time/button settings | Device settings sidebar, preserving all config fields and defaults; Theme, Schedule and Gestures are also exposed as quick-access buttons in the Preview lead card |
| Add, edit, remove, reorder, show/hide panels, home/idle roles | Panel groups, row menu, catalog, panel manager, editor sidebar |
| Popup overrides | Popups group lists extended popups only; the catalog's *Extend a popup* section offers the rest; fixed system panels are not listed; preserve fixed-key protection and popup-to-user-type mapping |
| All panel types/options, entity/action/text/navigate items and overrides | Descriptor-driven panel editor and existing item editing form/dialog |
| Themes and shared color editing | The **Theme** button on the Preview view's **Manage this device** card opens the sidebar for theme selection and shared color editing |
| Simulated and live preview, touch/slider/button input, idle/reset/entity overlay | Workspace preview stage using existing session classes and APIs |
| TFT/firmware check, release selection, upload, install | Device details/update chip → firmware surface; reuse existing update APIs and ordering semantics |
| YAML import/export | **Backup** card of the Preview side stack, using the server YAML endpoint, not a client parser |
| Notification queue/dismissal | Bell + notification centre, existing store and WebSocket subscription |
| Logs and diagnostics | Device details: facts plus the Diagnostics card (`ui/device-diagnostics.js`: a status line or two tiles and the hub internals with Copy report); logs stay a dialog |
| Confirm remove/reset/install | Existing confirm dialog |
| Editor version, docs, GitHub | Existing global footer at page bottom: version/Dev badge, GitHub, Documentation |

### Visual foundations

The prototype provides visual measurements, not a second Home Assistant theme. In HA, prefer its live
CSS variables and legacy aliases, rather than copying the prototype's full color ramps or
`prefers-color-scheme` overrides.

| Token group | Target |
|---|---|
| Color | HA primary/text/secondary/disabled/surface/divider/error/warning/success tokens. Add a small `--haui-*` alias layer only for missing meanings (good/warn/bad soft fills, soft surface, strong border, screen/bezel gradient, live-preview tint), each with a fallback. Respect HA's active theme. |
| Typography | HA body font; 10/12/13/14/16/20/24px scale; 400/500/600 weights; monospace for node, key, IP and versions. `styles/tokens.js` defines `--haui-text-eyebrow`, `--haui-text-caption`, `--haui-text-label` (13px), `--haui-text-body`, `--haui-text-title`, `--haui-text-display` and `--haui-line-height`. |
| Spacing | 4/8/12/16/20/24/28/32/40px; use measured prototype paddings for card, table, field and sidebar layouts. |
| Radius | `--haui-radius-control` for 8px controls/thumbs, `--haui-card-radius` for 12px cards, `--haui-radius-pill` for pills and `--haui-radius-round` for dots. |
| Elevation | `--haui-shadow-card` for cards; `--haui-shadow-overlay` for popovers/sidebars; device preview shadows remain distinct inside the bezel. |
| Icon | Home Assistant `<ha-icon>` with MDI icon names, 18px default and 14–16px compact; existing HAUI brand icon for mark. Do not use prototype SVG `<use>` sprites across shadow roots. |
| Motion | 120–150ms hover/color transitions; the scrim/sidebar entrance keeps its 140/180ms timing; pair motion with `prefers-reduced-motion`. |
| Focus | `--haui-focus-ring` and `--haui-focus-offset`: visible 2px primary-color outline with 2px offset. Never suppress keyboard focus. |

Typography utility classes in `styles.js` (`.haui-text-caption`, `.haui-text-label`, `.haui-text-body`,
`.haui-text-title`, `.haui-text-display`, `.haui-eyebrow`, `.haui-text-mono`) keep repeated type
choices consistent. `.haui-focusable` and the shared interactive-component rules use the same focus
ring. Spacing aliases (`--haui-space-1` through `--haui-space-8` and `--haui-space-10`) map the
measured spacing ladder onto HA's spacing variables where available.

The `scripts/check_frontend_styles.py` guard checks the scale, raw colors, alias ownership, duplicate
selectors, repeated style adoption, and reduced-motion overrides; `tests/test_frontend_styles.py` covers both valid styles and
intentional violations. Run it directly with `python scripts/check_frontend_styles.py` when changing
frontend CSS.

Keep the existing `:host` container query (`styles.js`) as the responsive root because descendant
container queries cannot reach outside the component's shadow tree. At approximately 1120px simplify
inventory; at 980px collapse the two-column screens; at 720px reduce row/card detail and stack role
controls; at 600px the sidebar becomes a full-screen page. Anchored popovers remain floating overlays
at every width, placed beside their trigger and clamped to the viewport. The notification centre
keeps its top-right placement and adjusts its width to the available viewport. The sidebar keeps the
Home Assistant app's `--safe-area-inset-*` free, so its strip and footer never sit under the
status bar or home indicator.
Exact breakpoints may be tuned to the available custom-panel width, not just viewport width.

## Visual component inventory

Components are Lit template renderers in `frontend/ui/` unless noted. They receive prepared data and
callbacks; they do not read the store or call APIs. `views/` composes them. This keeps component
markup/styles reusable and makes all data effects testable through the store/API layer. Retain custom
elements only for the editor shell, existing dialogs and simulator frame.
Shared form renderers in `form-fields.js` (`renderField` and `renderToggleField`) keep labels, controls,
hints, and toggle rows on the same markup contract across editor surfaces. `renderField` accepts a
`className` for surface-specific layout and `extra` content for validation messages or supplemental copy.

For each component below, the contract names its anatomy, variants, states, inputs, emitted actions,
and accessibility behavior. Components are listed once; each surface above is assembled from these
rows plus its view-level layout. Inventory: 12 primitives and 30 composites. Components that the migration keeps (for example
`dialogFrame` and the descriptor-driven field controls) keep current behavior; their appearance is
changed by the new styles.

### Primitives

| Component | Anatomy | Variants | States | Data in → events out | Accessibility |
|---|---|---|---|---|---|
| `icon` | HA `<ha-icon>` | default, small, large; semantic tone | decorative or labelled | icon name/class → none | Decorative icons `aria-hidden`; icon-only control gets its label on the button, not the glyph |
| `button` / `iconButton` / `backButton` / `addButton` | Native button, optional icon + label | primary, outline, quiet, active, icon-only, back, list add row (a `+ label` row with a dashed full-width outline that turns into the primary outline on hover) | hover, pressed, focus-visible, disabled, busy | label/icon/disabled/callback → click | Native button; `aria-label` for icon-only; disabled truly disabled; busy uses `aria-busy` |
| `badge` / `chip` / `statusDot` | pill or dot; optional count | neutral, primary, success, warning, danger; online/offline/stale | normal, empty count (hidden), pending, stale | text/tone/count or connection state → none | Dot has adjacent text or accessible label; color never sole state cue; count announced as notification count |
| `surface` / `sectionHeading` | card, heading band, optional subtitle/badge/actions, body | plain, flush/table, gradient summary, live-tinted | default, live-tinted | heading/actions/body template → action callbacks | Heading levels are sequential; actions remain named controls |
| `segmented` | labelled group of native buttons + optional count | two-or-more choices | selected, hover, focus, disabled choice | options/value → `select(key)` | `role=group` and `aria-pressed`; keyboard tab order and activation; current choice announced |
| `sortHandle` | visible grip with 32px target | compact (row), overlay (card) | idle, grabbed, dragging, drop target | draggable item ID/kind → start/drop | Grip only: the card, row or group it is dragged onto takes the drop. It is the only reorder affordance — panels and devices carry no Move up/Move down menu entries |
| `emptyState` | icon, title, explanatory line, optional action | fleet, panels, group, notifications, events | action/no-action | title/body/icon/action → action callback | Static message, optional native button; no live-region spam |
| `popover` / `menuItem` | anchored panel, optional arrow; menu rows, separators, danger style | menu, info panel, notification panel | open/closed, focused item, disabled, destructive, loading | anchor key + content/actions → select, close | Trigger `aria-expanded`/`aria-controls`; Escape/outside close; menu keyboard navigation; restore focus; modal overlays manage focus while open |
| `dialogFrame` | Existing `HauiDialog` custom element: labelled heading, close, scrollable body, optional footer | centered dialog, narrow/fullscreen | open/closed, loading, dirty, error | title/open/hass/content → close/confirm/save | Dialog role, labelled by title, modal focus containment/restoration, Escape policy consistent across all dialogs |
| `toast` | transient message with optional icon | info, success, warning, error | visible, dismissed, timeout | message/tone → dismiss | `role=status` polite (assertive only for actionable failure); does not steal focus |
| `editorFooter` | Existing `renderFooter()` version group + GitHub and Documentation links | Stable / prerelease | version missing; prerelease Dev badge; narrow wrapping | embedded asset version + `docsUrl(version)` → external links | Keep existing `.editor-footer` markup/styles, link URLs, `target`/`rel` security attributes, and translated titles; links keyboard-focusable |
| `format` | No DOM; pure timestamp/version/RSSI/connection formatters | localized unit/time variants | invalid/missing data handled explicitly | raw status values → display string | Localized output; missing values render explicit unknown/not-reported text, not a false value |

### Composites

| Component | Anatomy | Variants | States | Data in → events out | Accessibility |
|---|---|---|---|---|---|
| `deviceCard` | Screen cover + overlay update/selected/drag affordance; body status/name/node/chips | landscape, portrait; fleet, compact rail | online/offline, selected, update, loading/error cover, dragging | device/config/status/update/preview → select, menu, reorder | Native button selection separate from drag/menu buttons; descriptive name/status; image has useful alt or is decorative |
| `deviceRow` | Grid identity cell, IP, firmware, TFT, actions | desktop table, compact mobile | online/offline, stale, update, dragging | device/status/update → open, menu, reorder | Use table semantics where practical; row action buttons have labels; do not make nested interactive controls inside one button |
| `deviceRail` | Scrollable device chips with dot, name and update mark | full, narrow | active, offline, pending, overflow | ordered devices/status → select | Named navigation/group; each chip button exposes selected device and connection state |
| `fleetSummary`, `fleetBar` | Health line + updates and hub-version figures; `fleetBar` draws one segment per device | normal, degraded, all offline | loading, empty, healthy, warning/error | device/status/update aggregates → none | Counts are text; health statement is available without color/animation |
| `eventList` | Level/tone marker, event text, device/time metadata | info, warning, error | empty, populated, long text | log lines + device names → optional open-logs | Ordered list; level and device conveyed in text; timestamps use `<time>` |
| `panelRow` | Drag handle, thumb, title/key, item metadata, home/idle markers, menu | navigation, hidden, popup, fixed system | empty items, role, overridden/default, dragging/drop target | panel/system entry/device roles → edit, preview, menu, reorder/group move | Row isn't one giant button; every action separate named button; fixed entries indicate why edit/delete is unavailable |
| `panelThumb` | Cropped/contained real page render with role markers | landscape, portrait | loading, rendered, unavailable/error, hover/focus enlarged | explicit preview context + panel → open preview | `alt` identifies panel/page; markers have text/accessible labels |
| `deviceDetails` | Connection hero, fact tiles, Updates action, diagnostics card | online, offline, no status | stale facts, update available/installing/error | status/deviceInfo/update/config → configure, firmware, logs, YAML actions, menu | Connection state text; facts as definition list; actions labelled; stale data identified |
| `deviceDiagnostics` | Issue badge, status line or tiles (firmware, hub log; the Hub log tile opens the logs; `connectionTiles` supplies the uptime and Wi-Fi tiles of the Connection & device card), hub internals (transport, listeners, timers) ending with Copy report in the Device details side stack | simple, expanded | unavailable data, stale/offline, update available/installing/error | device status/device info → open logs, choose release, upload/install, close | Facts labelled and marked stale when needed; active activity data must be safe to expose; update controls retain confirmation/state announcements |
| `firmwareSurface` | Heading/close, version rows, update state/note, release/upload/action controls | sidebar body | checking, available, queued, installing, done, error, current | update state/releases → check, choose release, upload, install, close | Sidebar strip title and close; progress/state announced; destructive/irreversible install explained |
| `previewStage` | Bezel, simulator/live frame, two hardware button targets | landscape, portrait; simulated, live | loading, no panel, error, idle, online, disconnected | preview context/session state → touch, slider, hardware button, idle, reset | Live state named; hardware controls labelled; simulator inputs keyboard-operable; disconnected live mode disabled with explanation |
| `notificationItem` | Severity icon, title/message, time, dismiss | ordinary, persistent, critical | queued, active, dismissing | notification → dismiss/open | Severity is text/icon plus color; dismiss button has notification-specific label |
| `catalogOption` | Preview, icon, label, description, feature/option hint | user panel type | hover/focus, selected, disabled/unsupported | `PageDescriptor` → add type | One button/card with accessible name and concise description |
| `sidebar` | Fixed right panel (phone at widths of 600px or less: full-screen page), heading/close, scrollable body, sticky footer, desktop scrim; one open from another (for example, a panel editor from the catalog) covers it as a layer | device settings, panel editor, catalog, updates, theme | opening, closing, focused, dirty, saving/error; catalog omits footer | kind/title/body/draft → close, cancel, save, choose item | Modal dialog semantics, labelled heading, focus moved/trapped/restored, Escape closes topmost; Save/Clear labels state |
| `deviceSettings` | Grouped settings sections with shared fields and bottom actions | ordinary / advanced sections | loading, dirty, saving, validation failure | device config + device metadata → field changes, check updates, save/cancel | Each field labelled and described; grouped sections are keyboard-toggleable; preserve all device-config fields |
| `panelEditor` | Panel identity, behavior switches/roles, descriptor options, item counts in the section headings, inline item editing | user panel, popup override, system popup | new/edit, dirty, saving, duplicate key/error, hub-driven restrictions | panel draft + `PageDescriptor` → change fields, edit items, save/cancel | Label key/title/type; disabled fields explain why; errors associated with inputs; fixed system keys remain non-editable |
| `panelCatalog` | Search field + descriptor cards (thumb/icon, title, description, hints), with a top control to switch between large previews and compact side-by-side previews | all supported user panel descriptors | loading, empty search, result, selected/unsupported; large/compact preview layout | descriptors + query + preview layout → search, choose type, change layout, close | Search has label; layout control is a labelled segmented group; cards are buttons with title and description; keyboard selection |
| `panelManager` | The Theme, Schedule and Gestures buttons of the Preview lead card, one row of three, plus the Schedule and Gestures sidebars (`deviceOptionPanel`); Home and idle page assignments live in Device Settings → Special pages | Preview management area, Schedule and Gestures sidebars, Device Settings form | empty, configured, dirty draft, saving | device panels + config + theme library → open the theme sidebar, edit/save schedule and gestures, assign special pages | The buttons name the setting and carry their summary as a tooltip; the sidebars retain labelled controls and explicit saves |
| `entryList` | The list editors of the schedule (`scheduleEditor`) and the gestures (`gestureEditor`): an add row, then one folding card per entry whose head reads Entry N, the summary (what starts the entry: its window, its swipes; it gives way first), the note (what it does) and a remove button | schedule, gestures | folded, open, just added (only `expandedIndex` opens by state), removed (later cards hand their fold state up one) | entries + summary/note/body renderers → add, remove, toggle | Native `details`/`summary` fold control; the remove button is a named icon button and does not toggle the card |
| `notificationCentre` | Heading/count, queued notification list, per-item dismiss, empty message | viewport-clamped popover | empty, queued, persistent/critical, dismissing, error | store notification queue + update events → dismiss, close | `dialog`/popover label, count, list semantics, per-item dismiss name; focus restore |
| `deviceManagerDialog` | Device rows, ESPHome discovery/scan and add controls, enabled/update/status indicators, row action menu | manage, add/scan result | loading, scanning, empty discovery, existing, disabled, error | device entries + statuses → add, select, move, enable, remove, update action | Table/list semantics; each icon action named; scan status announced; confirmation for remove |
| `itemEditor` | Item list rows; add/reorder/remove; inline item fields (entity picker, type, icon, template, options) | entity, skip, text, navigate, action; single or list item | empty, max items, editing, invalid entity/value, saving | item config + `PageOption`/`item_options` + HA states → add/edit/reorder/remove/save/cancel | Entity picker combobox/listbox keyboard contract retained; inline errors labelled; reorder announced |
| `themeSidebar` | Draft palette preview; one predefined/custom theme dropdown; icon variant; shared semantic and state-icon color editor; import/export | built-in/custom theme and device selection | loading, selected, dirty, invalid color, in-use/unsaved confirmation | builtins + saved themes + active device settings → select/edit/create/duplicate/rename/delete/import/export/apply | Sidebar strip title; each color has named label/value; color is not communicated by swatch alone |
| `logsDialog` | Timestamped log lines with severity and device context | device-specific, recent | empty, populated, long lines, loading | status logs → close | Dialog title; log lines in chronological list; preserve readable wrapping and monospace metadata |
| `confirmDialog` | Title, explanatory message, cancel and confirm actions | default, destructive | open, busy, failure | action description + labels → confirm/cancel | Focus starts safely; destructive action explicit; Escape/cancel; result/failure announced |
| `optionField` | Descriptor-driven control renderer and label/description wrapper | bool, int, float, text, color, icon, generic, select, item/list variants | default, templated, validation error, disabled, dirty | `PageOption` + value → typed value change | Correct input for option kind, labels/descriptions linked, constraints/max-items conveyed |
| `entityPicker` | Search input + domain-filtered entity list + selected entity | single entity; domain-filtered; clearable where allowed | loading, no results, selected, unavailable entity, keyboard active option | HA states + allowed domain/current value → select/clear | Combobox/listbox semantics and keyboard navigation; entity name/state exposed to assistive tech |
| `iconPicker` | Searchable icon list + selected icon and preview | compact field, expanded picker | loading, no results, selected, invalid/unknown value | icon names/current value → search/select | Search label; list options named; selected state exposed; preview decorative |
| `colorPicker` | Color swatch, value control, optional preset palette | inline field, theme sidebar | default, dirty, invalid, disabled | color value/presets → change/save | Each swatch has a color-name/value label; contrast and selection not color-only |
| `templatePreview` | Template input + render/preview result | text/action template | idle, rendering, result, render error | template + HA render-template API → edit/render | Button labelled Preview; output/error associated with input and announced without focus steal |



### Surface-to-component map

| Surface | Components used |
|---|---|
| Shared titlebar / overflow | `icon`, `button`, `badge`, `popover` / `menuItem`, `themeSidebar`, `logsDialog` |
| Fleet | `deviceCard`, `sortHandle`, `fleetSummary`, `surface`, `deviceRow`, `eventList`, `emptyState`, `badge` |
| Device rail | `deviceRail`, `statusDot` |
| Workspace header and preview | `segmented`, `button`, `previewStage`, `emptyState`, `popover` |
| Panel groups | `surface`, `panelRow`, `panelThumb`, `sortHandle`, `badge`, `emptyState` |
| Device details / panel manager | `deviceDetails`, `deviceDiagnostics`, `panelManager`, `firmwareSurface`, `surface`, `button`, `badge` |
| Device settings / panel editor / catalog sidebars | `sidebar`, `deviceSettings`, `panelEditor`, `panelCatalog`, `optionField`, `entityPicker`, `iconPicker`, `colorPicker`, `templatePreview`, `panelThumb`, `catalogOption` |
| Notification centre | `notificationCentre`, `popover`, `notificationItem`, `emptyState`, `button` |
| Existing item/device-manager/logs/confirm dialogs | `dialogFrame`, `itemEditor`, `deviceManagerDialog`, `logsDialog`, `confirmDialog`, `button`, `toast` |
| App feedback | `toast`, `emptyState` |

Add a component to the inventory before implementing it if a screen needs a visual element not listed
here. Avoid making a component per one-off wrapper; split when it has repeated markup/state or a
separate accessibility contract.

### Prototype behaviors explicitly not carried over

- Mock fields and fake statistics: availability percentage/history, uptime literals, activity arrays,
  version placeholders, hard-coded notification count.
- Its PNG-only “Live” toggle, toast-only idle/reset/hardware buttons, and no-op “Show entities”. These
  controls must be connected to the existing live/virtual preview sessions and APIs.
- Its client-side YAML subset parser (server YAML API is authoritative), dead compact-switcher rules,
  missing device/panel order persistence, and click/drag conflict on the same row.
- Inline SVG symbols referenced across independent shadow roots; use HA icons.
- Duplicated popover positioning, broken focus restoration, missing focus trap, and content-wide
  `aria-live` region. Use one overlay implementation, proper focus handling, and a polite toast.

### Implemented: Fleet, Device, preview and side stack

The dashboard phases are implemented; the remaining dialog surfaces are listed below.

- `frontend/ui/` holds the render primitives and the data-driven Fleet/Device components. Views receive
  prepared data and callbacks; they never read the store or the API. `panel-utils.js` owns the panel
  grouping, move state and role markers.
- `frontend/styles/tokens.js` is the single home for HA-backed `--haui-*` aliases and the measured
  scale; `styles.js` composes shared tokens, primitives, panel pills, entries, form/dialog content
  and per-screen fragments. `styles/content.js` is one fragment, not an aggregator. Device styles are
  split between `styles/device-layout-styles.js` and `styles/device-panel-styles.js`; shared firmware
  and preview rules live in `styles/firmware-styles.js` and `styles/preview-styles.js`. Logs, theme, and
  panel-editor surfaces keep their focused rules in `styles/logs-styles.js`,
  `styles/theme-sidebar-styles.js`, and `styles/panel-editor-styles.js`. The shell uses `editorStyles`,
  dialogs use `dialogStyles`, and the preview simulator composes the shared tokens and `previewStyles`.
  Element-local styles are reserved for layout specific to that element.
- `frontend/app/router.js` parses/serializes the Fleet and Device hashes and binds history to the store.
- Fleet: scroll-snap carousel of real home-panel covers with arrows that disable at the scroll extents, a
  summary that waits for the first status payload, the inventory (`Firmware`/`TFT` columns), latest events,
  and one anchored device-actions menu shared by cards and rows.
- Device: a head with the back button to Fleet, the device name and the device rail (shown with more
  than one device; its chips collapse into a dropdown while they do not fit beside the title, measured
  by the shell with `ui/device-rail.js:railOverflows`), a workspace header with the Preview/Panels segmented control plus the Live
  and Idle controls, the panel workspace, and the
  context side stack.
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
  instead: one row per group with its count chip, the configured Home panel (or the hub's fallback to
  the first navigation panel) and Idle page (`idlePanelKeys`, summarised as *Clock and 2 more*), then
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
- Device management: there is no device manager dialog and no header menu. The shell scans for
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
  counts, Add panel and Settings (`panelActions`). Preview: Settings, Updates and Add panel, led by Install update
  while an update is offered (`ui/device-actions.js`); below its actions the same card carries the three
  device options as plain buttons in one row — Theme, Schedule and Gestures (`ui/panel-manager.js`), always
  side by side at any card width, dropping their icons before a label truncates. Each one only opens its
  editor: Theme the shared theme sidebar, Schedule and Gestures their own sidebar (`deviceOptionPanel`), so
  the card never grows when an option is opened. A button's tooltip states what its option holds (the
  selected theme, the entry counts). It heads the side column beside the workspace
  (`.haui-device-side`, sticky: it stays in view while a long workspace scrolls);
  once the layout is one column it moves above the workspace (grid areas of `.haui-device-layout`),
  and at 560px or wider its actions sit beside its heading.
- Side stack: a column of `surface` cards. In the Preview view: Connection & device, Diagnostics and
  Backup (YAML import and export). Each collapses as a whole on a click anywhere on the heading outside its controls, or on its chevron
  (the keyboard control), remembered per browser. The Connection &
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
  assigned in Device Settings → Special pages, and panel thumbnails carry
  the Home, Idle and edited-popup markers; the Home marker follows the hub's fallback to the first
  navigation panel while no home panel is configured. The modal sidebar (settings, panel editor,
  catalog) is its own element (`haui-modal-sidebar`) over the page. `ui/sidebar.js` frames the modal
  side stack (labelled strip, close control, 380px body);
  device details report the connection facts, mark them stale while offline, and carry the diagnostics
  card (`ui/device-diagnostics.js`: a status icon before the title that counts the issues, a status line that expands to two tiles and the
  hub internals, Copy report at their end; expanded, it also holds the preview's tools: Show entities, Reset sandbox (only while the sandbox holds a simulated state), and in Live
  Reset interaction and Redraw display), plus the firmware, logs and YAML actions; Device Settings assigns Home/Idle
  pages under Special pages.
- Overlays: `ui/popover.js` is the single anchored-popover implementation (one open at a time, placed
  against its trigger, Escape/outside click close with focus returned). The panel menu,
  device menu, notification centre and firmware surface use it; the notification centre and firmware
  surface keep their own geometry and are marked `staticPlacement`.
- Panel authoring: the searchable catalog seeds the descriptor-driven panel editor in the side stack. Item
  editing stays **inline** in that editor (the `itemEditor` row above describes the form, which the
  editor renders itself) rather than in a widened dialog; the section holding the item list opens with the form and
  shows the item count in its heading.
- Device settings, panel editor and catalog are the only sidebar surfaces; their forms scroll while
  their Cancel/Save footer stays put.
- Retained dialog: the confirmation dialog. The Theme editor and logs are sidebar elements (`dialogs/theme.js`, `dialogs/logs.js`); the firmware surface is the `nspanel-firmware-popover` element (`dialogs/firmware.js`), and diagnostics live in the side stack. The old device-manager and device-info dialogs are gone. These keep their behaviour and are styled through `dialogStyles`.
- The store has route, ordered overlay and preview-intent state plus a persisted `device_order`;
  `PanelStorage` and the panel API normalize that order against the actual devices.
- `frontend/ui/format.js` formats relative timestamps, reported versions and short uptime labels.
- The persistent footer remains on every screen, including error and loading states: version, Dev badge,
  GitHub and documentation links.
- `tests/frontend/ui-primitives-preview.html` renders the shipped primitives and their
  enabled/disabled, open/closed, dirty/error and empty/loading variants for manual review.

## Boundaries

| Directory | Owns | Rule |
|-----------|------|------|
| `app/` | The shell element and its lifecycle | Wires collaborators; no data fetching or formatting |
| `store/` | Shared state and actions | Only the store writes shared state; one poller per scope |
| `api/` | REST and websocket transport | No rendering or state; one namespaced client |
| `views/` (v0.5) | Pure render functions and view elements | Read state and dispatch actions; no transport calls |
| `dialogs/`, forms, `previews/` | Existing UI | Stay until a view migrates; use the client, never raw `fetch` |

Existing modules keep their public shape while they migrate. A view receives
data and callbacks; it does not reach into the shell for new features.

The preview context is explicit: `{ entryId, device, deviceConfig, panels,
deviceInfo, api }`. `previews/previewer.js` and `previews/simulator-frame.js`
depend on that object, not on the editor element.

## Phasing

The information architecture and component inventory above are the P0 contract. P1–P6 are
implemented; P7 (accessibility, states, docs and screenshot refresh) continues as maintenance.

- **P0 — Structure + component specification:** this document; define routes, screens, overlays,
  feature parity, visual foundations and each reusable component's markup, variants, states, data,
  events and accessibility contract.
- **P1 — Foundations (done):** tokens, primitive components, formatting helpers, router/overlay state and
  persistent device ordering; no screen redesign yet.
- **P2 — Shell + Fleet (done):** titlebar, carousel/cards, fleet summary, device inventory and latest events.
- **P3 — Device workspace (done):** device rail, working simulated/live preview, details, panel groups and
  reordering.
- **P4 — Panel authoring (done):** catalog, panel editor, roles and item editing.
- **P5 — Device settings + updates (done):** settings sidebar and firmware/TFT flows.
- **P6 — Secondary surfaces (done):** notification centre, colors and logs; the device manager dialog and the header overflow menu were removed (their functions live on Fleet and in the Device cards).
- **P7 — Polish:** responsive and keyboard/accessibility pass, empty/error/offline states, docs and
  screenshot refresh.

Each implementation phase stays shippable. Run the frontend tests and typecheck plus backend tests,
ruff, mypy and strict docs build when their touched code/docs require them.

## Migration rules

- Initial foundation changes preserved the serving contract and no-build rule. The dashboard phases
  replace the old single-page presentation while retaining the store, API, simulator and device
  transport behavior.
- One view per change. Keep the serving contract and the no-build rule.
- Migrated modules use `api/client.js`; no raw `fetchWithAuth`, `callWS` or
  `subscribeMessage` outside `api/`.
- Shared state is written through store actions. Preserve the save-in-flight
  guard, the selected-device status reset and the stale-status drop.
- New `store/`, `api/` and `views/` modules carry `// @ts-check`; run
  `npm ci` once, then `npm run typecheck:frontend`.
- Keep the existing frontend tests green. A migrated module may use the
  store-backed fake host in `tests/frontend/fake-host.mjs`, but its behavioural
  assertions stay.


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
