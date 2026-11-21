---
title: Editor architecture
description: The editor's constraints, boot sequence, layer boundaries and feature map, plus a link to each page of this section
---

# Editor architecture

The editor is the static Lit custom panel where devices, panels, themes and updates are configured, and the only surface most users touch. This page holds what is true of the editor as a whole; each part that grew too large for one page has its own:

| Page | Covers |
|---|---|
| [Screens](frontend-screens.md) | The routes, the shared shell, Fleet and the Device screen |
| [Sidebars and overlays](frontend-overlays.md) | The seven sidebars, menus, popovers, dialogs, focus and Escape |
| [Visual foundations](frontend-visuals.md) | Colour, type, spacing, radius, motion, breakpoints and text sizes |
| [Components](frontend-components.md) | Every primitive and composite, and which surface uses which |
| [Tests](frontend-testing.md) | Conventions, local checks and assertion boundaries |

The preview stage, the panel cards and the browser Nextion simulator are described in [Live preview and cards](preview.md).

## Constraints

- **No build step, no bundler.** The integration is installed by copying `custom_components/nspanel_haui/` into Home Assistant, so `frontend/` holds plain ES modules the browser loads at runtime.
- **Static and unauthenticated.** `web/editor.py` registers the `nspanel-haui-editor` panel element and serves `frontend/` under a content-hashed URL (`<integration version>-<digest>`). No Python file belongs in `frontend/`.
- **Vendored Lit only.** `frontend/vendor/lit/index.js` supplies `html`, `css` and `LitElement`, re-exported by `lit-import.js`. No framework, no bundler, no second Lit copy.
- **No runtime dependency.** `typescript` and `happy-dom` are dev dependencies: they type-check the modules marked `// @ts-check` and run the tests, and never ship with the integration.
- **Restart Home Assistant, then reload the browser** after editing `frontend/`. `haui-editor.js` reloads the page when Home Assistant imports it into a tab that still holds an editor, instead of defining every element a second time.

## How the editor boots

1. `haui-editor.js` is the registered entry: it imports `app/shell.js` and re-exports `NSPanelEditor`, the shell element that is the editor.
2. The shell receives `hass` and creates one API client (`api/client.js`, over `hass.fetchWithAuth` and the WebSocket) and one store (`store/store.js`). `store/controller.js` is the Lit controller that re-renders the shell on every commit.
3. The store loads the hub entry, panel store, panel types, notifications and the initial device status. It owns the single 5 s status poll: Fleet and a multi-device rail read the aggregate response, which carries rollout progress, while a lone Device screen polls that device. The poll skips a tick while a request is pending or the tab is hidden, and stops when the editor detaches.
4. `app/router.js` parses and serializes the hash and binds back/forward to the store. `fleet-screen.js` and `device-screen.js` turn the route into the screen composition out of `views/` and `ui/`; views receive prepared data and callbacks and never read the store or the API.

The overlay layer is wired alongside it — [Sidebars and overlays](frontend-overlays.md#how-overlays-are-wired) lists the one popover, the sidebar kinds and the two dialogs.

## Where features live

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
