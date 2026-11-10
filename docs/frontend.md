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
  files with a content-hash URL. Keep Python out of `frontend/`, and reload the
  browser after edits.
- **Vendored Lit.** `frontend/vendor/lit/` provides `html`, `css` and
  `LitElement`; `lit-import.js` re-exports them. No framework or bundler is
  added.
- **No new runtime dependencies.** Node tooling is development-only: it
  type-checks modules that opt in with `// @ts-check` and runs the frontend
  tests.

## Current flow

1. `web/editor.py` registers the sidebar panel and serves
   `frontend/haui-editor.js`, which re-exports `NSPanelEditor` from
   `app/shell.js`.
2. The shell receives `hass` from Home Assistant. It creates one API client
   (`api/client.js`) over `hass.fetchWithAuth` and the websocket connection, and
   one store (`store/store.js`).
3. The store loads the hub entry: the panel store, panel types, the status of
   every device and the notification queue. It owns the selected device and its
   5 s status poller; the Device Manager starts and stops the all-device poller
   while it is open.
4. The shell mirrors store state into the Lit properties the existing render
   modules read (`_panels`, `_selectedDevice`, `_deviceStatus`, …). Those
   modules keep their current DOM and CSS; they are adapted, not rewritten.
5. Panel cards ask the hub for a render over the websocket
   (`nspanel_haui/virtual_panel/render`). The browser replays the commands on the
   real layout; there is no renderer in the browser.

## Target v0.5 dashboard

From `design/dashboard-prototype.html`:

- **Shell:** titlebar, device carousel with status dots and update badges,
  content area, a right-hand settings sidebar, popovers and a toast.
- **All devices:** fleet summary, device inventory table and recent activity.
- **Selected device:** a panel workspace (preview or panel list) and a side
  stack with device details or the panel manager.
- **Panel editor:** name, type and key; navigation/home/idle; content. Later a
  split view next to the live preview.
- **Device settings:** device, display and updates first; gestures, language and
  profiles later.
- **Notification center:** a bell, the queue and history, and dismissal in
  place.

The prototype ignores service-call wiring: the existing dialogs' logic is the
source of truth for what each action must do.

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

- **Phase 0 (v0.4.7):** store, API client, shell move, one vertical slice
  (panels/devices/status/notifications), this document. No visible change.
- **Phase 1:** shell with the device carousel, fleet summary, device inventory
  and recent activity.
- **Phase 2:** panel workspace and panel editor split view.
- **Phase 3:** device settings in the sidebar.
- **Phase 4:** notification center.
- **Phase 5:** responsive and accessibility polish, container-query breakpoints.

## Migration rules

- Phase 0 changes no visible behaviour: the DOM, CSS and translations stay as
  they are.
- One view per change. Keep the serving contract and the no-build rule.
- Migrated modules use `api/client.js`; no raw `fetchWithAuth`, `callWS` or
  `subscribeMessage` outside `api/`.
- Shared state is written through store actions. Preserve the save-in-flight
  guard, the selected-device status reset and the stale-status drop.
- New `store/`, `api/` and `views/` modules carry `// @ts-check`; run
  `npm ci` once, then `make typecheck-frontend`.
- Keep the existing frontend tests green. A migrated module may use the
  store-backed fake host in `tests/frontend/fake-host.mjs`, but its behavioural
  assertions stay.

## Trade-offs

One store and one client are easier to reason about than per-domain modules:
the editor is a single page that loads one hub entry, and the pollers,
notifications and saves all touch the same device map. Split a file when it
stops having one reason to change, not when it grows; the store actions are
already grouped by domain and the API client is namespaced by route.
