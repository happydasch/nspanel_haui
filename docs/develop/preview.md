---
title: Live preview and cards
description: The virtual panel app, Simulated and Live previews, panel cards and the dashboard card's read-only transport
---

# Live preview and cards

Neither the editor's preview nor the dashboard card builds a screen from a panel config in the browser: a Simulated preview and a panel card run the hub's own code on a per-device virtual app, Live mode streams the device's own app, and the card reads either over WebSocket. Start here when you change anything under `web/preview/`, `web/card.py` or `frontend/virtual/`.

## Simulated and Live

| Mode | Source | What a touch does |
|------|--------|-------------------|
| Simulated | The device's virtual app (`web/preview/virtual_panel.py`), with entity states from a sandbox | Simulated service calls: no real entity changes |
| Live | The device's own running `NSPanelHAUI` app (`web/preview/live_panel.py`) | Checked events go to that app, whose normal service calls act on real entities |

Both modes are drawn by the same browser Nextion simulator and show the panel's own state and hardware buttons; the user-facing tour is in [The live preview](../user/editor/README.md#the-live-preview).

## The virtual app

One second `NSPanelHAUI` per device, built from the device's stored config the way setup builds it. Only the transport and the entity layer differ, so every page, controller and lifecycle hook is the real one. It starts on first use, follows saves that affect its config, and stops after `IDLE_STOP_SECONDS` (600 s in `web/websocket.py`) without a viewer or a card render, or when the hub entry unloads.

| Part | File | Role |
|------|------|------|
| `VirtualNSPanelHAUI` | `web/preview/virtual_panel.py` | Reads states through the sandbox, routes service calls, suppresses HA bus events, uses an inert update controller |
| `VirtualESPHomeProxy` | `web/preview/virtual_panel.py` | Stands in for `ESPHomeProxy` and the firmware: answers the connection handshake, sends heartbeats, forwards display commands, page changes, brightness and sounds to the browser; refuses TFT and firmware uploads |
| `VirtualPanelHost` | `web/preview/virtual_panel.py` | Owns a device's virtual app: fans its display output out to every Simulated viewer (a late viewer gets a replay without redrawing the panel), drops the simulated states when the last viewer leaves, renders panel cards, keeps the home stream |
| `Sandbox` | `web/preview/sandbox.py` | Simulated entity states over the real ones; simulates the common services |
| Sample data | `web/preview/sample_data.py` | Representative entities shared by the editor previews and the card gallery |
| `ButtonEntities` | `web/preview/button_entities.py` | The entities behind the frame's two hardware buttons, shared by the Simulated and Live previews and the dashboard card |
| `LivePanel` | `web/preview/live_panel.py` | One Live viewer of the device's own app |
| `HomeStream` | `web/preview/home_stream.py` | The device's home panel kept running on the virtual app for the [dashboard card](../user/dashboard-card.md), with real states only |

A sandbox lays simulated states over Home Assistant's real ones: a read returns the simulated state when there is one, and a simulated service call changes only the simulated state. It simulates the common services (on/off, light brightness and colour, cover position, climate setpoints and modes, media playback, locks, alarm panels, vacuums, number/select/text values, timers); any other service leaves the state untouched and reports that to the caller.

The simulated states live exactly as long as a Simulated preview: the last viewer of that app leaving (`VirtualPanelHost.detach`) drops them, so switching to Live, another device, the **Panels** view or Fleet, and closing the tab all leave nothing behind — a card render reads the same app and would otherwise draw a simulated state as the panel's own. **Reset sandbox** in the Diagnostics card sends `/reset_sandbox`, which drops them while the preview stays open.

In Simulated mode every non-query service call of the virtual app is simulated; queries with `return_response` (such as `weather.get_forecasts`) always reach Home Assistant. The virtual app also performs the relay switch action that ESPHome performs when a hardware button is pressed in relay mode.

The browser can inject only the events a person causes on a panel: component touches, raw touches, gestures, hardware buttons and the read responses a slider answers with. Slider values come back the way the firmware returns them: the hub's `req_val`/`req_txt` go to the browser, which answers with `esphome.read_response`.

Once a Simulated preview has opened, the virtual app mirrors the device's notification queue: the device's app reports every change of its queue (`publish_preview_state`), and `VirtualPanelHost` copies it into the virtual queue, read-only.

Simulated mode renders its own page content (including camera frames and media covers) using the same hub code but sandbox entity state. Service draws have no page renderer, so the virtual host additionally mirrors their confirmed fills while both apps show the same configured panel key. Matching the HMI page id alone is not enough: several configured panels may use the same template. The sandbox firmware answers a draw slice with the same fence the panel sends (`esphome.res_draw`, after the time those fills would take) instead of confirming it as it records, so a preview shows the busy display and the refused slice the panel has.

A Camera card is a static render of the picture the hub plans for it. It shows the fills the followed device's camera page holds while that device shows this very panel for this camera; otherwise it fetches a snapshot of the camera itself and plans one whole paint of the picture area at the panel's own quality (`plan_still_frame`), so a card of a camera no device is showing still previews the picture. Without a current picture — no camera configured, or one that does not answer — it keeps the page's placeholder. A panel that names one of the sample world's cameras stands for the camera a *new* panel will be pointed at, so it previews one of the instance's own cameras while it has any (`_real_camera`: available before unavailable, then by entity id) instead of the drawing; the generated picture (`sample_snapshot` in `sample_data.py`) is what an instance with no camera at all shows, which is also what keeps the committed screenshots the same on every machine. A camera card's render is not kept in the browser (`previews/previewer.js`): a picture is stale by the next mount and far too large for the kept-render list. Live does not use that card snapshot: it seeds the page from the same ordered replay as any other page — minus the picture area, which it takes from `NSPanelHAUI.camera_page_frame()` — and asks the stream for a whole paint when the replay can no longer describe that area (its oldest fills were dropped for room), so a viewer gets the picture instead of a composite with holes in it.

### Virtual panel commands

All admin only, like the editor itself.

| Command | Does |
|---------|------|
| `nspanel_haui/virtual_panel/subscribe` | Attaches a Simulated viewer to the device's app and streams its display output until the subscription closes; the first message is `{"type": "started", ...}`, and the last subscription closing drops the simulated states |
| `nspanel_haui/virtual_panel/event` | Injects a touch, swipe or hardware button |
| `nspanel_haui/virtual_panel/home` | Starts the sandbox over: drops the simulated states, leaves the idle page, restarts the inactivity clock and opens the home panel |
| `nspanel_haui/virtual_panel/open` | Opens one of the device's panels by key, as its idle page when `idle` is set (the Current page tile) |
| `nspanel_haui/virtual_panel/idle` | Toggles the idle page: opens it, or wakes back to the panel it covered (or home) |
| `nspanel_haui/virtual_panel/reset_sandbox` | Drops the simulated entity states |
| `nspanel_haui/virtual_panel/render` | Renders one panel as its card shows it, without touching what a viewer sees |

The **Current page** tile of the Connection card sends `/open` with the device status's `current_panel` (`VirtualPanelHost.async_show_panel`): the virtual app opens that panel by key, a popup with the sample context of its card, or as its idle page (`open_idle_panel(key=…)`) while the device's `idle_page` state is `active`. Live mode already shows the device's page, so the tile acts in Simulated mode only.

## Panel cards

Panel cards (`/render`, `VirtualPanelHost.async_render`) run one panel's page through its real lifecycle (`prepare_page_load`, `start_panel`, `render_panel`, stop) on the shared app, isolated from the live display: the page sees a view of the app whose ESPHome controller records the display output, whose navigation ignores every action and which makes only service calls that return data (such as `weather.get_forecasts`). A card never moves what a viewer sees.

The result is `{"page", "before", "commands"}`: `before` is what the hub sends before switching to the page (the theme colours and its picture background), and the editor replays the whole thing in the Nextion simulator. A user card renders the editor's config, unsaved edits included; a system card renders the device's configured panel by `key`.

A card's render key (`previews/previewer.js`) covers everything the hub draws with: the device, its saved settings and panels, the device info its pages show, and the theme definition the device draws in. That theme is read from the store's `hub.themes` — the library `api/editor.themes` returns, which `editor-data.js` commits on every load — so a palette the sidebar saved reaches the cards without a page reload.

Popups open with the sample context `preview_kwargs()` defines (`web/preview/virtual_panel.py`: an example notification, sample choices, a panel to unlock) or, for an entity popup — recognised by its system key, so an edited one too — an entity of its `item` option's domain while its config names none: the first one that is on, else the first one that is off. A card rendered with its own `kwargs` — the panel editor's entity popup, which picks a random entity of the domain once per editing session — wins over the sample.

## Live mode

Live mode does not use the virtual app. Each Live viewer (`web.preview.live_panel.LivePanel`) subscribes to the device's own running app: the commands that app sends through `HAUIESPHomeController.send_cmd` are streamed to the browser's Nextion simulator, so page changes and stateful controls show the app's own render output.

Browser input is checked — an event a person can cause, a component of the current page, coordinates on the display, the device connected — and passed to that app's event handler, so its normal service calls act on real Home Assistant entities. In relay mode a hardware button also switches the real relay, as the firmware does for the real button.

A new viewer gets the current page’s load commands, the page switch, and the ESPHome controller’s ordered page replay. The app’s worker seeds the viewer and subscribes to updates together; the panel itself draws nothing again. Still images and camera updates enter the same replay and Live feed when the firmware acknowledges each slice. An unconfirmed slice is not presented as drawn. A page that paints its area from a picture replays it separately, from what the panel confirmed for that area (`camera_page_frame()`), and the replay skips those fills so nothing is sent twice. A page acknowledgement is not another page load: only the outgoing page switch resets the browser drawing. After a save, the viewers follow the reloaded app's button settings for the button lights. The page, display-state and connection snapshots are used only for the live controls and status.

**Idle** and **Reset interaction** are explicit live actions. **Idle** toggles the idle page: it opens it, or wakes the panel back to the panel it covered or home, and restarts its interaction timer. **Reset interaction** only restarts the inactivity clock of the firmware's dim/off timer, without changing the current page or resetting the hub's separate idle-page timer.

Live viewers are independent of each other and of the Simulated previews. A preview switching to Live first sends `/reset_sandbox` when the sandbox has simulated states, and the sandbox viewer it leaves behind drops them as the last one leaving.

Live lasts exactly as long as the editor keeps showing that preview. Switching device, opening the **Panels** view, going back to Fleet, or opening any sidebar — the panel editor, the catalog, device settings, the theme library, Updates, Logs, Backups — ends it as the change lands, so an edit never runs against the panel on screen. Every commit is checked against the route and sidebars Live started on (`settleLive()` in `store/store.js`, so no caller has to remember), and `views/workspace.js` never starts a live session for a device it was not already showing. Coming back to the preview therefore shows the sandbox again: Live is not resumed on its own.

Opening a Simulated preview and switching back to it from Live take nothing from the device and send `/home`, so the virtual app starts over: it drops the simulated states, leaves its idle page, restarts its inactivity clock (it got no touches while Live was shown) and opens its home panel.

### Live panel commands

All admin only.

| Command | Does |
|---------|------|
| `nspanel_haui/live_panel/subscribe` | Attaches to the device's app and streams its display output, its status and the entity each widget shows (for the editor's entity hover) until the subscription closes |
| `nspanel_haui/live_panel/event` | Passes a touch, swipe or hardware button |
| `nspanel_haui/live_panel/slider` | Passes a slider's value back to the app |
| `nspanel_haui/live_panel/action` | Toggles the idle page or resets the inactivity timer |

## The dashboard card

The [dashboard card](../user/dashboard-card.md) (`frontend/card/`) is the one surface outside the editor. Its commands (`web/card.py`) are the only ones without `require_admin`: they only read, and none of them leads to an input path.

| Command | Does |
|---------|------|
| `nspanel_haui/card/devices` | Lists every device the hub has, each with its Home Assistant `device_id` and its `enabled` setting |
| `nspanel_haui/card/home/subscribe` | Attaches the card to the host's `HomeStream` |
| `nspanel_haui/card/live/subscribe` | Attaches a `LivePanel` to the device's app |

A subscription names its device by `device_id` — which the card editor stores, and which a rename keeps — or by the hub `entry_id` and the device's name; both resolutions go through `_card_device`, so the two subscribe commands refuse an unknown device alike.

A device that runs no app is answered `disabled` when the panel store disables it and `not_found` while its app has not started, so a card says which; it asks again either way. A subscription the hub ends (entry unload, device removed) gets `{"type": "ended"}` as its last message, and the card subscribes again.

A disabled device stays in `card/devices`: the hub still renders its panels from the panel store, so its card keeps its screen and only lacks the panel's own state.

`card/live/subscribe` attaches its `LivePanel` to the device's app but outside the live preview's session registry, so `live_panel/event`, `/slider` and `/action` never find it: the card has no input path. The subscription needs the running app, so a disabled device is refused `disabled`.

`card/home/subscribe` attaches the card to the host's `HomeStream`: the first card starts the home panel (`HAUINavigationController.home_panel`, as Home resolves it on the device) as a panel-card render that is never stopped (`_PanelRender(..., stream=True)`), and the last card stops it.

A device that runs no app is still served when the panel store disables it: the host builds the virtual app from the store (`_home_target`), so the screen is drawn and only `async_follow_device`/`async_follow_panel` are skipped, which is why such a card reports no state.

The home panel's view (`_StreamApp`) reads Home Assistant's real states through a sandbox of its own, which never holds a simulated state, and lets queries that return data (weather forecasts) through, so the page keeps drawing as entities, the clock and forecasts change.

Every output goes to every card; a late card gets `started`, the commands sent before the page, the page and the last write per target (`command_target`, as `page_commands()` does for Live). A save restarts the stream and draws it for every card again.

A card showing only a device's state (`CardInfoSession` in the browser) takes the live subscription and ignores the display output: the panel's own state is all it shows, and the hub renders nothing for it.

### The panel's own state

The card also shows the panel itself, never from its own guesses. `VirtualPanelHost.async_follow_panel` subscribes **once** per device to the running app's `subscribe_preview_state` (`get_preview_state()`: the current page, the display state, the connection and the versions the panel runs), copies the queue onto the virtual app, and streams that state with its queued notification count to every home card (`HomeStream.set_panel`, `{"type": "physical"}` / `{"type": "notifications"}`) — the same two messages the editor's Live preview gets, from the same state.

The hardware buttons are `ButtonEntities` (`web/preview/button_entities.py`, the tracker the Live preview uses too) fed by Home Assistant's real entity states, so a preview's simulated states never reach a card. `ButtonEntities` owns the whole view of a hardware button in one message: each of the panel's two buttons switches its own relay, or runs an entity of any domain with its domain's default action when relay mode is off, and `{"type": "buttons"}` reports per side the `relay` and `entity` it involves, the light's `state` (the entity it switches, else its relay) and the relay's own `relay_state` (the dot beside the light). There is no separate relay or "lights" message: the entities and their states travel together.

A late card is replayed the panel's state, its notification count and its buttons before the page.

## The browser simulator

`frontend/virtual/` is the display end of both previews and of the card.

| File | Role |
|------|------|
| `nextion-script.js` | Runs the HMI's event code and the hub's display commands |
| `nextion-display.js` | Holds the display state |
| `nextion-view.js` | Renders that state |
| `touch-input.js` | Turns pointer input into the firmware's `esphome.component`, `touch_start`/`touch_end` and `gesture` events |
| `qr-encode.js` | Draws QR widgets |
| `assets.js` | Loads the layouts, icon map and pictures |
| `panel-session.js` | Connects the display to the WebSocket; applies the panel's own state, its queued notifications and the button lights |
| `virtual-panel-session.js` | The Simulated mode's commands and messages |
| `live-panel-session.js` | The Live mode's commands and messages |
| `card-sessions.js` | The card's three sessions (Home, Live, Info), view-only |

The page layouts are exported from both HMI files by `scripts/hmi_layout/gen_virtual_layout.py`: per orientation it writes `frontend/virtual/layout_<orientation>.json` (every page by the hub's id, with its widgets, fonts and globals), the page pictures and the icon map, plus the fonts' glyph widths and the solid pages' theme code (see [Scripts for display](nextion.md#scripts-for-display)).

A draw program's `fill` runs are painted into a `<canvas>`, not into one element each: a picture is thousands of adjacent rectangles and a stream repaints it several times a second, so a run of fills becomes a single canvas sized to the runs' own bounding box and scaled by the same transform as the widgets (`virtual/picture-layer.js`). One node and one texture instead of thousands of SVGs, whose per-rect nodes made the browser spend 71 % of a drawing preview's time in Paint / display-list building (measured on a 6 000-run picture; the same picture is now 14 DOM nodes). A canvas also has no subpixel edges, so adjacent runs share their boundary exactly where scaled CSS boxes left a hairline; and a render paints only the fills it added to the display's log - a stream's frame is a few hundred rectangles on a picture of thousands - so the rest of the picture stays on the canvas. The canvas is kept per run across renders and never rebuilt per frame; a log that was rewritten rather than appended to (a widget repainted over the picture split its fills, a page change dropped them) is signalled by the display's `fillsRevision`, and only then is the run painted again from its start. A fill that reaches over every fill of the log replaces it - a picture sent again is the picture, not a layer on top of the previous one. A run below `MIN_CANVAS_FILLS` stays plain boxes, since a canvas each would cost more than the boxes it paints. `tests/frontend/support/canvas.mjs` gives the test DOM the 2D context happy-dom lacks and records what was painted, which is what `tests/frontend/virtual-view.test.mjs` asserts.

Raw hub commands are not cached as reusable HMI scripts. The display also periodically drops fills whose exact rectangle a newer fill repainted, so a long camera session does not retain every colour a region has shown. A log rewrite invalidates the canvas cache, including when removing a shape joins two previously separate runs.

## Saving a panel store edit

Panel-store edits (`api/panel_edits.py`) hold Home Assistant's entry setup lock from loading the snapshot through saving and applying it. This also orders edits with setup-time storage migrations, device removal and initial preview startup.

An in-place save updates the affected physical apps before refreshing previews; home cards then read button entities from the updated apps. A full entry reload reacquires the lock and loads the current store, so a save must release the lock before awaiting it. This ordering does not merge two editors' drafts that both replace the same settings or panel list.
