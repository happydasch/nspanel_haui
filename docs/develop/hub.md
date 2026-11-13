---
title: Hub Component
description: NSPanelHAUI hub app architecture, structure, and internal components
---

# Hub Component

The hub app (`NSPanelHAUI`, `hub/app.py`) runs inside Home Assistant, one
instance per enabled device: it reads entity states, renders display commands
and publishes them to the panel through the ESPHome native API. Installing the
integration is covered in [Installation](../user/install.md); running a
checkout in a test instance in [Development](development.md#local-development-deployment).

## Structure

### Base classes

- `haui.abstract.haui_base.HAUIBase` — base of every runtime object: config
  access, logging, command batching (`rec_cmd`), ESPHome send helpers and the
  `start`/`stop` lifecycle.
- `haui.abstract.haui_config_access.HAUIConfigAccess` — the lighter sibling for
  data and config wrappers that need no display transport or lifecycle.
- `haui.abstract.haui_page.HAUIPage` — a page on the display; its touch input,
  function buttons, component callbacks and paging come from the mixins in
  `haui/abstract/mixins/`.
- `haui.abstract.display_interface.DisplayInterface` — the display commands
  pages send (`send_cmd`, `set_component_text`, `set_component_value`), through
  the `DisplayTransport` protocol to the ESPHome controller.

### Home Assistant adapter and threading

`HAAdapter` (`hub/adapter.py`) bridges Home Assistant's async API to the
synchronous `haui/` core, which imports nothing from `homeassistant`:
`ItemProxy` wraps one entity's state, attributes and services, `ESPHomeProxy`
sends actions to the device and listens for its events.

Every call from Home Assistant into an app (device events, state changes,
timers, reloads, services, notify) runs on that app's single worker thread, in
order: use `app.dispatch()` (fire-and-forget) or `await app.async_run_on_worker()`.
Blocking work (HTTP, disk) never runs on the worker: `app.run_off_worker()`
waits for the result, `app.submit_off_worker(..., on_done=…)` applies it back on
the worker later; the callable must not touch app state. Only liveness traffic
bypasses the worker: `run_every(..., on_loop=True)` runs on the event loop and
`publish_detached()` sends without waiting, which the hub→device heartbeat uses
so a busy worker never delays it.

### App

`NSPanelHAUI`

The lifetime of the application is:

- **`initialize()`** — sets up config, device, controllers, then calls `start()` internally
- **`stop()`** — cancels timers, stops device and controllers

### Config

`haui.abstract.haui_config.HAUIConfig`

The configuration is built from the device's settings and panels in the panel store, over the `DEVICE_CONFIG` defaults. This class allows to process the config values and gives access to panels and entities.

### Device

`haui.device.HAUIDevice`

This class represents the whole device: its reported state and versions, the
physical buttons, gestures, sounds and the firmware auto switches. It is started
and stopped with the app.

### Page

`haui.abstract.haui_page.HAUIPage`

This class represents a single page on the display.

A page lives as long as the panel it shows: navigation creates a new page
instance each time a panel opens and stops it when the panel closes. The panel
hooks below run on that instance.

### Panel

`haui.abstract.haui_panel.HAUIPanel`

The panel represents a configured page. The panel contains the configuration and entities to use. The configuration values are taken from the config.

The lifetime of a panel is:

- **page_load_commands**(panel) — what the display reads while it loads the page (the theme colours, a picture background); `prepare_page_load()` sends it right before the page switch
- **prepare()** (optional) — set the page's per-panel attribute defaults; runs during `__init__()` and again before every `start_panel`, so nothing one panel set carries over to the next panel on the same page
- **start_panel**(panel) — once the page is loaded: register callbacks, create items, read panel options (`self.option(panel, key)`, which takes an option's default from the page's descriptor)
- **config_panel**(panel) — gives the header buttons `start_panel` registered without a function their default one (navigation, home or idle, unlock or notifications)
- **before_render_panel**(panel) — return `False` to skip rendering
- **render_panel**(panel) — send the display commands
- **after_render_panel**(panel, rendered)
- **stop_panel**(panel) — clears listeners and callbacks, then calls the page's `_stop_panel(panel)`

`start_panel`, `config_panel` and `render_panel` are sent as one command batch.

```mermaid
sequenceDiagram
    participant Page as Page Instance
    participant Panel as HAUIPanel

    Page->>Panel: page_load_commands(panel)
    Note over Page: sent before the page switch

    Page->>Page: prepare()
    Note over Page: per-panel attribute defaults set

    Page->>Panel: start_panel(panel)
    Page->>Panel: config_panel(panel)

    Page->>Panel: before_render_panel(panel)
    alt returns True
        Page->>Panel: render_panel(panel)
        Page->>Panel: after_render_panel(panel, rendered=True)
    else returns False
        Page->>Panel: after_render_panel(panel, rendered=False)
    end

    Note over Panel: panel is active<br/>(the page refreshes on entity updates)

    Page->>Panel: refresh_panel()
    Page->>Panel: render_panel(panel)

    Page->>Panel: stop_panel(panel)
    Note over Panel: panel cleaned up
```

While a panel is active, it can be refreshed using:

- **refresh_panel()** — re-renders the currently set panel by calling `render_panel` in one batch. Pages call it from their state listeners and timers; navigation calls it after buffer overflow recovery and a restored idle snapshot, the notification controller when the open list changes.

The ESPHome controller keeps what the shown page was sent since it loaded (`page_commands()`: the last write to each target, an attribute or a widget's `vis`/`tsw`, in the order of those writes; a page switch starts it over). Replayed on a freshly loaded page after the page's `load_commands` (what `prepare_page_load` sent), it ends on the screen the panel shows: a new Live viewer gets the page this way, whichever hook drew each widget, and the panel draws nothing again.

A saved config shows the current panel again on the loaded page (`start_panel` and `render_panel` run again on the same page instance) as long as `is_loaded_for(panel)` holds, that is, the page would read the same `page_load_commands`; otherwise navigation loads the page again.

### Item

`haui.abstract.haui_item.HAUIItem`

An item represents a configured entry in a panel. It can wrap a real HA entity
(``HAUIEntity``) or be an internal item (``skip``, ``text``, ``navigate``, ``action``).
Configuration values (name, value, icon, color, state overrides) are taken from the
config and resolved through ``HAUIItem``.

## Connection

`haui.controller.HAUIConnectionController` runs the device connection: a
`DISCONNECTED → HANDSHAKING → CONNECTED` state machine with a three-step
handshake, bidirectional heartbeats, a 15 s handshake timeout and livesign
detection (any non-handshake event while disconnected restarts the handshake).
The protocol, timings and failure cases are in
[Communication Overview](communication.md).

On a transition to CONNECTED, and whenever it leaves CONNECTED (to DISCONNECTED, or
to HANDSHAKING when the device reboots), the controller
calls `callback_connection(bool)`, which `HAUIDevice.on_connection_changed()`
handles: it opens the System panel on the first connect and restores the panel on
a reconnect. `health()` reports the drops and late heartbeats of the last
24 hours for the editor's diagnostics (see below).

## Device Status and Details

The editor refreshes status by polling the authenticated
`/api/nspanel_haui/status/{entry_id}` endpoint every five seconds: the editor
store polls the selected device while the editor is open, and every device
while the Fleet screen shows them. This is separate from the
`HAUIConnectionController`: that controller owns the device handshake and
heartbeats, not editor data refresh, and the integration does not use Home
Assistant's `DataUpdateCoordinator` for this status view.
The editor writes each store concern independently: `PUT /api/nspanel_haui/devices/{entry_id}/{device}` replaces one device's settings (and its `GET` reads current settings); `PUT /api/nspanel_haui/panels/{entry_id}/{device}` replaces only that device's panels; `PUT /api/nspanel_haui/device_order/{entry_id}` stores the editor's order; and `POST /api/nspanel_haui/themes/{entry_id}` manages shared themes. The whole-store panels route is read-only, so these writes never replace another device's data.

### REST API

`api/__init__.py` registers these views (`VIEWS`), all under `/api/nspanel_haui/`.
Every view needs an authenticated Home Assistant user, and all but the editor
lookups require an admin. The editor calls them through `frontend/api/client.js`.

| Module | Routes |
|--------|--------|
| `api/editor.py` | `GET translations/{language}`, `panel_types`, `color_defaults`, `icons` |
| `api/config.py` | `GET panels/{entry_id}` (the whole store, read-only); `GET`/`POST`/`DELETE devices/{entry_id}` (list, add, remove); `GET`/`PUT devices/{entry_id}/{device}` (settings); `PUT panels/{entry_id}/{device}`; `PUT device_order/{entry_id}`; `GET`/`POST yaml/{entry_id}` (export, import one device) |
| `api/themes.py` | `GET`/`POST themes/{entry_id}` |
| `api/status.py` | `GET status/{entry_id}`; `GET`/`DELETE notifications/{entry_id}`; `POST refresh_display/{entry_id}` |
| `api/updates.py` | `POST update_tft/{entry_id}`, `update_firmware/{entry_id}`, `check_update/{entry_id}`; `GET tft_releases/{entry_id}`, `firmware_releases/{entry_id}`; `POST update_upload/{entry_id}/{kind}` (a local file, served to the device once through `GET update_artifact/{token}`, which needs no login) |

For an enabled device, the API gathers mutable runtime details (connection, current page,
listeners and timers) on that device app's worker. It reads Wi-Fi readings from the linked
ESPHome entities on Home Assistant's event loop and combines them into the response. Disabled
devices have no running app, so the API returns a minimal status using only available HA entity
readings. **Diagnostics → Hub details** shows the display state (`on`, `dim` or `off`) apart from the
idle page, which is a hub-side page switch: shown, paused by an overlay opened from it, held off by
the current page, due in a given time, or off (`HAUINavigationController.idle_status()`). It counts
the drops of the last 24 hours (`HAUIConnectionController.health()`): every time an established
connection ended, by heartbeat timeout or because the device asked for a new connection (it
rebooted or gave up on the hub's heartbeats); a failed handshake is not a drop. It also counts the
device heartbeats that arrived more than 1.5 intervals after the previous one, with the longest gap.
The history is kept in memory and starts empty when the hub starts; three or more drops in 24 hours
show as an issue on the card. It lists the entities the current page listens to with their live
state from Home Assistant, flagging unavailable and missing ones; the raw listener and timer lists
go into **Copy report**.

### Status fields

The fields of the status response that the editor's **Connection & device** and
**Diagnostics** cards show:

| Field | Meaning |
|-------|---------|
| `integration_version` | Version of the installed NSPanel HAUI integration |
| `integration_version_mismatch` | `true` when the integration version differs from the device's ESPHome firmware `yaml_version`; `null` until both are reported |
| `connection_uptime` | Seconds since the ESPHome connection was last (re)established |
| `display_state` | Display brightness state reported by the firmware: `on`, `dim` or `off` |
| `idle_page` | Where the idle page stands: `state` is `active` (shown), `suspended` (an overlay was opened from it), `offline` (the device is disconnected, so the idle page waits for it), `held` (the current page holds it off), `pending` (it opens after `idle_in` more seconds without an interaction) or `off` |
| `connection_health` | Disconnects and late device heartbeats of the last 24 hours, kept in memory since the hub started: `drops_24h`, `recent_drops` (newest first, with `time` and `reason`), `late_heartbeats_24h` (a heartbeat more than 1.5 intervals after the previous one), `longest_heartbeat_gap` and `heartbeat_interval` |
| `last_disconnect_reason` | Why the connection dropped last (e.g. `heartbeat timeout`), if known |
| `disconnected_since` | When the device went offline that last time |
| `yaml_version` | ESPHome firmware version reported by the panel |
| `tft_version` / `tft_required_version` | Display TFT version installed vs the version required by firmware |
| `update` | TFT update state while an install runs: `checking`, `installing`, `done`, or `error` (with `version`, `started_at`, `last_error`) |

HAUI and firmware versions are expected to match; a known mismatch is an issue
on the **Diagnostics** card, while missing version data is not treated as a
mismatch. A display whose TFT is older than `tft_required_version` is flagged
**update pending**; if the firmware has not reported `tft_required_version`, none
is inferred from `yaml_version` and the display is not flagged. Firmware update
availability compares a release with `yaml_version`; the display check compares
`tft_version` with `tft_required_version`.

The status is only as fresh as the last poll: while a device is offline, the
editor keeps showing the last snapshot it received. The display gives no
byte-level progress during a TFT install, so `update` only moves through
`checking → installing → done` (or `error`).

In Live mode, **Reset interaction** on the Diagnostics card resets the
firmware's dim/off inactivity timer for the selected panel without changing the
current page or resetting the hub's separate idle-page timer.

## Navigation

`haui.controller.HAUINavigationController` owns navigation. There are navigable
panels (`show_in_navigation`) and non-navigable panels; panels that are not
navigable are kept in a stack when opened, so `close_panel()` / `go_back()`
return to the last navigable one. It opens panels (`open_panel`,
`open_home_panel`), waits for the display's page ack before rendering (see
[Nextion Component](nextion.md#panel-rendering-and-refresh)), locks panels with
an unlock code behind the unlock popup, and runs the idle page:
`open_idle_panel()` / `exit_idle_to_prev_or_home()` and the once-per-second
inactivity check that opens it. The idle page is a page switch only; display
dimming and off belong to the firmware.

## Gestures

Supported gestures: swipe_left, swipe_right, swipe_up, swipe_down

All swipes go to `haui.controller.HAUIGestureController`. It runs the action of the gesture a swipe completes: a `GestureAction` (next or previous panel) or the key of a panel to open. Gestures are the `gestures` device setting (the editor's Gestures sidebar; see [Device Configuration](../user/configuration/device.md#gestures)), read on every swipe so a saved config applies without a restart. The controller keeps the latest swipes, as many as the longest gesture has; a swipe runs at most one action (the completed gesture with the most swipes, then the first in the list), and a gesture of several swipes that ran clears them. A slider drag also reports a swipe, so the controller ignores swipes while the page suppresses gestures. `hub/storage.py` (`migrate_gesture_settings`) converts the older `swipe_actions` and `gesture_sequences` settings.

## Updates

`haui.controller.HAUIUpdateController` checks for and installs firmware and TFT
updates and backs the **HAUI Firmware** and **HAUI Display** update entities;
`haui/controller/release_source.py` fetches manifests and release lists off the
worker and caches GitHub releases hub-wide. The whole cycle is in
[Update Process](update-process.md).

## Events

All events are wrapped in the `haui.abstract.haui_event.HAUIEvent` class. This class provides basic access to events received via ESPHome.

## Communication

Pages change the display with `send_cmd` / `send_cmds` and the
`set_component_*` helpers, never through the ESPHome controller directly. The
`rec_cmd` context manager batches them into one `send_commands` action:

```python
with self.rec_cmd:
    self.set_component_text(self.COMPONENTS.title, "Hello")
    self.set_component_value(self.COMPONENTS.t_info, 42)
```

Commands recorded inside the block are deduplicated — only the last write to
each target is sent — and the batch is sent when the block exits;
`start_rec_cmd()` / `stop_rec_cmd()` are the lower-level form. The panel
lifecycle is already batched (see [Panel](#panel)), so `with self.rec_cmd:` is
for callbacks from state listeners, timers and touches.

## Pages and panels

The page classes live in `haui/page/`, one module per page type. A panel is a
configured instance of a page: a page can serve several panels (the alarm page
serves alarm panels and the unlock popup), and every panel can have its own key
for navigation. `PANEL_MAPPING`, `SYS_PANEL_MAPPING` and `POPUP_PANEL_MAPPING`
in `haui/mapping/panel.py` map the keys to pages. The panel types are described
in the [Panels Overview](../user/panels/README.md).

### Popup parameters

`popup_notify` and `popup_select` take these parameters when they are opened from
code (`navigation.open_panel(PopupPanelKey.…, **kwargs)`). The user pages are
[Popup Notify](../user/panels/popup_notify.md) and
[Popup Select](../user/panels/popup_select.md).

**`popup_notify`**

- `notification`, `title` — Message text and title. Line breaks in the message (`\n`) render as line breaks on the display.
- `icon` (optional) — Shown only when set, beside the text (above it in portrait). When omitted, no icon is displayed and the text uses the icon's area too: the full width in landscape, the full height in portrait, so more text fits on each page. `icon_color` colours it.
- `btn_left`, `btn_right` (optional) — Button labels; a button is shown only when set. Colors via `btn_left_color`, `btn_left_back_color` and the `btn_right_*` equivalents.
- `icon_color` (optional) — Icon colour in any `parse_color_value` format (`#rrggbb`, RGB565 int, `[r, g, b]`, integer string). Leave it empty (or unset) for the theme's text colour.
- `text_size` — `auto` (default: the largest font that fits the message on one page) or a font size 1-3, paged at that size when the message does not fit. The per-notification `text_size` field on the service/actions overrides this panel value.
- `close_on_button` — Close when a button is pressed. Default: true.
- `button_callback_fnc`, `close_callback_fnc` — Callbacks.

A queued notification's popup never takes `close_timeout`: the notification
controller owns its lifetime (see [Notification Process](notifications.md)). A
popup opened directly with `open_panel` can use `close_timeout` to close itself
after a number of seconds.

**`popup_select`**

- `items` — The entries (`{value, name}` dicts or plain strings). At least one is required.
- `selected` — The currently selected value (a list with `multiple`).
- `select_mode` — Display style:
    - `default` — 3×4 button grid
    - `full` — Full-width list (4 buttons per page)
- `multiple` — Allow selecting multiple items. Default: false.
- `multiple_delay` — Delay in seconds before the selection is applied when `multiple` is enabled. Default: 1.5.
- `close_on_select` — Close the popup after a selection is made. Default: true.
- `close_timeout` — Automatically close after this many seconds. 0 = no auto-close.
- `selection_callback_fnc`, `close_callback_fnc` — Callbacks.

In single-selection mode, tapping the already selected entry keeps it selected
and applies it again.

## Device Linking

Each configured NSPanel HAUI device is linked to its underlying **ESPHome device** in the Home Assistant device registry. Instead of creating a separate `nspanel_haui` device entry, the hub adds an `nspanel_haui` identifier and attaches its config entry to the existing ESPHome device entry.

This means:

- The device shows up in the **nspanel_haui hub page** — you can see all claimed ESPHome devices under the integration
- **Clicking the device** in the hub page navigates to the ESPHome device page (the ESPHome config entry remains its primary one)
- The **service device picker** (`integration: nspanel_haui`) only shows ESPHome devices that have HAUI firmware — plain ESPHome devices are excluded
- When the integration is unloaded, the config entry is cleanly removed from the device
- **Deleting the device** in the hub page removes it from the hub like **Remove** in the editor (`async_remove_config_entry_device` in `__init__.py`); its settings and panels are deleted

The linking is handled in `_link_esphome_device()` in `__init__.py` and runs both during initial setup and when a device appears later (race condition handling via the device registry listener).

### Accessing sensor entities

An ESPHome YAML `id:` is a firmware-side component reference, not a Home
Assistant entity ID. Components marked `internal: true` are available to ESPHome
automations but are not exposed as HA entities. If both the firmware and HAUI
need a sensor value, keep its ESPHome `id:` and expose the sensor (do not mark
it internal). If HAUI needs a value that should not be exposed as an entity,
send it through the existing ESPHome ↔ hub event/device-state protocol instead.

For sensors explicitly selected in HAUI configuration, use the configured
entity ID. For a built-in ESPHome entity, resolve it through
`HAAdapter.find_entity_id()` using its HA domain and ESPHome-authored original
name, then read it through the adapter:

```python
entity_id = self.app.find_entity_id("sensor", "Temperature")
if entity_id is not None:
    state = self.app.get_item(entity_id).get_state()
```

The same registry lookup pattern is used for the built-in temperature sensor,
firmware-backed settings and the editor's IP/SSID/RSSI diagnostics. Resolve
against the linked HA device and skip an operation when no unique enabled
entity matches; do not substitute an ID guessed from another device. The
adapter marshals its entity-registry read onto Home Assistant's event loop.

Do not derive an HA entity ID from the ESPHome `id:` or the HAUI device slug:
HA may assign area-prefixed IDs, and entity IDs can differ after device renames.
If the registry has no unique enabled match on the linked device, treat the
entity as unavailable: do not read or write a guessed ID. HAUI's built-in
inside-temperature display shows its unavailable value in that case.

## Virtual Panel (Live Preview)

The editor's [live preview](../user/configuration/README.md#the-live-preview) in Simulated mode and its panel cards run on one second `NSPanelHAUI` app per device, built from the device's stored config the same way setup builds it. Only the transport and the entity layer differ, so every page, controller and lifecycle hook is the real one. The app starts on first use, follows every save (`api.config.push_panels`) and stops after ten minutes without a viewer or a card render, or when the hub entry unloads.

| Part | File | Role |
|------|------|------|
| `VirtualNSPanelHAUI` | `web/preview/virtual_panel.py` | Reads states through the sandbox, routes service calls, suppresses HA bus events, uses an inert update controller |
| `VirtualESPHomeProxy` | `web/preview/virtual_panel.py` | Stands in for `ESPHomeProxy` and the firmware: answers the connection handshake, sends heartbeats, forwards display commands, page changes, brightness and sounds to the browser; refuses TFT and firmware uploads |
| `Sandbox` | `web/preview/sandbox.py` | Simulated entity states over the real ones; simulates the common services (on/off, light, cover, climate, media, lock, alarm, vacuum, number/select/text, button, timer) |
| Sample data | `web/preview/sample_data.py` | Representative entities shared by the editor previews and the card gallery |
| Button lights | `web/preview/button_lights.py` | The preview frame's hardware button lights, shared by the Simulated and Live previews |
| `VirtualPanelHost` | `web/preview/virtual_panel.py` | Owns a device's virtual app: fans its display output out to every Simulated viewer (a late viewer gets the current panel redrawn) and renders panel cards |
| WebSocket commands | `web/websocket.py` | `nspanel_haui/virtual_panel/subscribe`, `/event`, `/home`, `/open`, `/idle`, `/reset_sandbox` and `/render` (admin only) |
| `LivePanel` | `web/preview/live_panel.py` | One Live viewer of the device's own app; its WebSocket commands are `nspanel_haui/live_panel/subscribe`, `/event`, `/slider` and `/action` (admin only) |

**Panel cards** (`/render`, `VirtualPanelHost.async_render`) run one panel's page through its real lifecycle (`prepare_page_load`, `start_panel`, `render_panel`, stop) on the shared app, isolated from the live display: the page sees a view of the app whose ESPHome controller records the display output, whose navigation ignores every action and which makes only service calls that return data (such as `weather.get_forecasts`). The result is `{"page", "before", "commands"}` — `before` is what the hub sends before switching to the page (the theme colours and its picture background) — and the editor replays it in the Nextion simulator. A user card renders the editor's config (unsaved edits included), a system card the device's configured panel by `key`. Popups open with the sample context the preview code defines (`web/preview/virtual_panel.py`: an example notification, sample choices, a panel to unlock) or, for entity popups (recognised by their system key, so an edited one too), an entity of their `item` option's domain while their config names none (an empty `{"item": null}` counts as none): the first one that is on, else the first one that is off. The panel editor passes its own `kwargs` for an entity popup it shows — a random entity of the domain, picked once per editing session — and the hub's sample gives way to them.

The browser end lives in `frontend/virtual/`: `nextion-script.js` runs the HMI's event code and the hub's display commands, `nextion-display.js` holds the display state, `nextion-view.js` renders it, `touch-input.js` turns pointer input into the firmware's `esphome.component`, `touch_start`/`touch_end` and `gesture` events, `qr-encode.js` draws QR widgets, `assets.js` loads the layouts, icon map and pictures, and `panel-session.js` connects it all to the WebSocket; `virtual-panel-session.js` (Simulated) and `live-panel-session.js` (Live) add their mode's commands and messages. Slider values come back the way the firmware returns them: the hub's `req_val`/`req_txt` go to the browser, which answers with `esphome.read_response`.

The **Current page** tile of the Connection & device card sends `/open` with the device status's `current_panel` (`VirtualPanelHost.async_show_panel`): the virtual app opens that panel by key, a popup with the sample context of its card, or as its idle page (`open_idle_panel(key=…)`) while the device's `idle_page` state is `active`. Live mode already shows the device's page, so the tile acts in Simulated mode only.

Once a Simulated preview has opened, the virtual app mirrors the device's notification queue: the device's app reports every change of its queue (`publish_preview_state`), and `VirtualPanelHost` copies it into the virtual queue, read-only.

In Simulated mode every non-query service call of the virtual app is simulated; queries with `return_response` (such as `weather.get_forecasts`) always reach Home Assistant. The virtual app also performs the relay switch action that ESPHome performs when a hardware button is pressed in relay mode. The browser can inject only the events a person causes on a panel: component touches, raw touches, gestures and hardware buttons.

Live mode does not use the virtual app. Each Live viewer (`web.preview.live_panel.LivePanel`) subscribes to the device's own running app: the commands that app sends through `HAUIESPHomeController.send_cmd` are streamed to the browser's Nextion simulator, so page changes and stateful controls show the app's own render output. Browser input is checked (an event a person can cause, a component of the current page, coordinates on the display, the device connected) and passed to that app's event handler, so its normal service calls act on real Home Assistant entities; in relay mode a hardware button also switches the real relay, as the firmware does for the real button. **Idle** and **Reset interaction** are explicit live actions: **Idle** toggles the idle page (opening it, or waking the panel back to the panel it covered or home, and restarting its interaction timer), and **Reset interaction** only restarts the inactivity clock. A new viewer gets the current page as the panel shows it: the page's `load_commands`, then the ESPHome controller's `page_commands()`, replayed in the browser; the panel itself draws nothing again. After a save, the viewers follow the reloaded app's button settings for the button lights. The page, display-state and connection snapshots are used only for the live controls and status. Live viewers are independent of each other and of the Simulated previews: a preview switching to Live first sends `/reset_sandbox` when the sandbox has simulated states; opening a Simulated preview and switching back to it from Live take nothing from the device and send `/home`, so the virtual app starts over: it drops the simulated states, leaves its idle page, restarts its inactivity clock (it got no touches while Live was shown) and opens its home panel.

The page layouts are exported from both HMI files by `scripts/hmi_layout/gen_virtual_layout.py` (see [Scripts for display](nextion.md#scripts-for-display)).
