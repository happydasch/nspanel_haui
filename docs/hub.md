---
title: Hub Component
description: NSPanelHAUI hub app architecture, structure, and internal components
---

# Hub Component

NSPanelHAUI is the backend that allows to manage home automation devices using the NSPanel.

## Requirements

- Home Assistant with ESPHome integration
- Dependencies are auto-installed by Home Assistant (see `manifest.json`)

## Installation

1. Install the NSPanel HAUI custom integration from the Home Assistant Marketplace or by copying to `custom_components/nspanel_haui/`
2. Restart Home Assistant
3. Add the integration via **Settings → Devices & Services → Add Integration → NSPanel HAUI** (config flow)

## Structure

The classes are structured as described below.

### Base Component

All parts of haui are based on the `haui.abstract.haui_base.HAUIBase` class. This class provides some basic functionality. There are more specialized classes, which extend from `HAUIBase`:

- `haui.abstract.haui_base.HAUIBase`
  Base class with common functionality

- `haui.abstract.haui_page.HAUIPage`
  Page representation, this class is used when interacting with the page on the device

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

This class represents the whole device.

The lifetime of a device is:

- start
- stop

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

- **prepare()** (optional) — set instance attribute defaults, called during `__init__()`
- **page_load_commands**(panel) — what the display reads while it loads the page (the theme colours, a picture background); `prepare_page_load()` sends it right before the page switch

page loaded ..

- **start_panel**(panel)
- **config_panel**(panel) — gives the header buttons `start_panel` registered without a function their default one (navigation, home or idle, unlock or notifications)
- **before_render_panel**(panel)
  -> if True, panel can be rendered
  -> if False, panel will not be rendered
  - **render_panel**(panel)
- **after_render_panel**(panel, rendered)
- **stop_panel**(panel)
```mermaid
sequenceDiagram
    participant Page as Page Instance
    participant Panel as HAUIPanel

    Page->>Page: prepare()
    Note over Page: instance attributes set

    Page->>Panel: page_load_commands(panel)
    Note over Page: sent before the page switch

    Page->>Panel: start_panel(panel)
    Page->>Panel: config_panel(panel)

    Page->>Panel: before_render_panel(panel)
    alt returns True
        Page->>Panel: render_panel(panel)
        Page->>Panel: after_render_panel(panel, rendered=True)
    else returns False
        Page->>Panel: after_render_panel(panel, rendered=False)
    end

    Note over Panel: panel is active<br/>(entity updates trigger refresh)

    Page->>Panel: refresh_panel()
    Page->>Panel: render_panel(panel)

    Page->>Panel: stop_panel(panel)
    Note over Panel: panel cleaned up
```

While a panel is active, it can be refreshed using:

- **refresh_panel()** — re-renders the currently set panel by calling render_panel. This will not be triggered automatically.

A saved config shows the current panel again on the loaded page (`start_panel` and `render_panel` run again on the same page instance) as long as `is_loaded_for(panel)` holds, that is, the page would read the same `page_load_commands`; otherwise navigation loads the page again.

### Item

`haui.abstract.haui_item.HAUIItem`

An item represents a configured entry in a panel. It can wrap a real HA entity
(``HAUIEntity``) or be an internal item (``skip``, ``text``, ``navigate``, ``action``).
Configuration values (name, value, icon, color, state overrides) are taken from the
config and resolved through ``HAUIItem``.

## Connection

The connection between the Hub app and the device is managed by `haui.controller.HAUIConnectionController` using a 3-state machine: `DISCONNECTED → HANDSHAKING → CONNECTED`.

### State Machine

```mermaid
stateDiagram-v2
    state DISCONNECTED
    state HANDSHAKING
    state CONNECTED

    [*] --> DISCONNECTED

    DISCONNECTED --> HANDSHAKING: req_connection<br/>received from device

    HANDSHAKING --> HANDSHAKING: res_connection received<br/>(sends req_device_state)
    HANDSHAKING --> CONNECTED: res_device_state received<br/>(sends hub_connection_initialized)

    HANDSHAKING --> DISCONNECTED: handshake not completed<br/>within 15s
    CONNECTED --> DISCONNECTED: heartbeat timeout<br/>or hub_connection_closed
    CONNECTED --> CONNECTED: bidirectional heartbeats<br/>(every heartbeat_interval)

    DISCONNECTED --> DISCONNECTED: livesign detection<br/>(re-initiate handshake)
```

### Bidirectional Heartbeats

Once connected, both sides independently monitor liveness:

- **Hub→Device**: Periodic `hub_heartbeat` action at the device-declared `heartbeat_interval` (default 5s). First heartbeat fires immediately ("now+0"), then every interval. The hub also answers each incoming `esphome.heartbeat` with an immediate `hub_heartbeat`; the timer is a fallback.
- **Device→Hub**: `esphome.heartbeat` events update `_last_time` in the controller. Timeout = `interval × overdue_factor` (default 10s).

### Timeout Monitoring

The `_check_timeout()` method runs on a periodic timer (same interval as heartbeats):
- Only active in CONNECTED state
- If `time.monotonic() > _last_time + max(interval × factor, 10.0)`, transitions to DISCONNECTED
- Extended-disconnect warnings log every 60s when state stays DISCONNECTED

### Handshake Timeout

A handshake that does not complete within 15s (`_HANDSHAKE_TIMEOUT`) logs a warning and returns to DISCONNECTED; the device retries `req_connection` every 10s.

### Reconnection (Livesign Detection)

Any event received while in DISCONNECTED (except `req_connection`, `res_connection` and `res_device_state`) triggers immediate handshake re-initiation:
1. Sets state → HANDSHAKING
2. Sends `hub_connection_response` with hub version
3. Returns early (the same event is NOT processed further)
4. Subsequent `res_connection` → `res_device_state` complete the handshake

### Connection State Callbacks

On state transitions:
- **CONNECTED**: Sends `hub_connection_initialized`, starts timers, invokes `callback_connection(True)`; the firmware's inactivity timer is unchanged
- **DISCONNECTED** (from CONNECTED): Sends `hub_connection_closed`, stops timers, invokes `callback_connection(False)`

The callback propagates to `HAUIDevice.on_connection_changed()`, which handles navigation (open sys_system on first connect, restore panel on reconnect).

## Device Status and Details

The editor's Device Info dialog and device list refresh status by polling the authenticated
`/api/nspanel_haui/status/{entry_id}` endpoint every five seconds while open. This is separate
from the `HAUIConnectionController`: that controller owns the device handshake and heartbeats,
not editor data refresh, and the integration does not use Home Assistant's
`DataUpdateCoordinator` for this status view.

For an enabled device, the API gathers mutable runtime details (connection, current page,
listeners and timers) on that device app's worker. It reads Wi-Fi readings from the linked
ESPHome entities on Home Assistant's event loop and combines them into the response. Disabled
devices have no running app, so the API returns a minimal status using only available HA entity
readings. In Device Info, **Page Mode** means whether the hub is showing the configured idle
page or a regular page; it does not describe display brightness (`on`, `dim` or `off`).

## Navigation

The navigation is kept simple. There are navigateable panels and non-navigateable panels. Panels that are not navigateable will be kept in a stack when opened so that it is possible to return to the last navigateable item.

All navigation related functionality can be found in `haui.controller.HAUINavigationController`.

## Gestures

Supported gestures: swipe_left, swipe_right, swipe_up, swipe_down

Singular gesture handling lives in `haui.device`; `haui.controller.HAUIGestureController` opens a panel when a configured gesture sequence completes within its time limit. Sequences are the `gesture_sequences` device setting (Device Settings → Gestures in the editor; see [Device Configuration](configuration/device.md#gestures)), read on every gesture so a saved config applies without a restart.

## Updates

All update functionality can be found in `haui.controller.HAUIUpdateController`

## Events

All events are wrapped in the `haui.abstract.haui_event.HAUIEvent` class. This class provides basic access to events received via ESPHome.

## Communication

Most of the communication happens by publishing to ESPHome. There are two commands to change the display `send_cmd` and `send_cmds`. It is possible to record all calls to send_cmd of `haui.abstract.haui_page.HAUIPage` and to use them together with send_cmds:

```python
# batch multiple commands using the rec_cmd context manager
with self.rec_cmd:
    self.set_component_text(self.COMPONENTS.title, "Hello")
    self.set_component_value(self.COMPONENTS.t_info, 42)
    self.render_panel(panel)

# commands are deduplicated and sent automatically on exit
```

Commands recorded inside the `with rec_cmd:` block are deduplicated — only the last write to each target is sent — and the batch is sent automatically when the block exits. The lower-level `start_rec_cmd()` / `stop_rec_cmd()` methods are also available for manual use if needed.

## Available Pages

The pages represent pages on the nextion displays. The pages interact with the ESP and are the main place where to add code for interaction with the device. All pages are defined in `haui.page.*`. See `haui.abstract.haui_page.HAUIPage` for functionality.

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

## Available Panels

Panels are configured representations of a page. A page can have multiple panels, like the alarm page, which is used for alarm activation and the unlock popup. There can be multiple panels using the same page. All panels can have a custom key defined, which is used for navigation. See [Panels Overview](panels/README.md) for more details about the different panels.

## Virtual Panel (Live Preview)

The editor's [live preview](configuration/README.md#the-live-preview) and its panel cards run on one second `NSPanelHAUI` app per device, built from the device's stored config the same way setup builds it. Only the transport and the entity layer differ, so every page, controller and lifecycle hook is the real one. The app starts on first use, follows every save (`api.config.push_panels`) and stops after ten minutes without a viewer or a card render, or when the hub entry unloads.

| Part | File | Role |
|------|------|------|
| `VirtualNSPanelHAUI` | `virtual_panel.py` | Reads states through the sandbox, routes service calls, suppresses HA bus events, uses an inert update controller |
| `VirtualESPHomeProxy` | `virtual_panel.py` | Stands in for `ESPHomeProxy` and the firmware: answers the connection handshake, sends heartbeats, forwards display commands, page changes, brightness and sounds to the browser; refuses TFT and firmware uploads |
| `Sandbox` | `sandbox.py` | Simulated entity states over the real ones; simulates the common services (on/off, light, cover, climate, media, lock, alarm, vacuum, number/select/text, button, timer) |
| `VirtualPanelHost` | `virtual_panel.py` | Owns a device's virtual app: fans its display output out to every live-preview viewer (a late viewer gets the current panel redrawn) and renders panel cards |
| WebSocket commands | `websocket_api.py` | `nspanel_haui/virtual_panel/subscribe`, `/event`, `/notifications`, `/idle`, `/reset_sandbox`, `/configure` and `/render` (admin only) |

**Panel cards** (`/render`, `VirtualPanelHost.async_render`) run one panel's page through its real lifecycle (`prepare_page_load`, `start_panel`, `render_panel`, stop) on the shared app, isolated from the live display: the page sees a view of the app whose ESPHome controller records the display output, whose navigation ignores every action and which makes only service calls that return data (such as `weather.get_forecasts`). The result is `{"page", "before", "commands"}` — `before` is what the hub sends before switching to the page (the theme colours and its picture background) — and the editor replays it in the Nextion simulator. A user card renders the editor's config (unsaved edits included), a system card the device's configured panel by `key`. Popups open with `PageDescriptor.preview_kwargs` (an example notification, sample choices, a panel to unlock) or, for entity popups (recognised by their system key, so an edited one too), an entity of their `item` option's domain: the first one that is on, else the first one that is off.

The browser end lives in `frontend/virtual/`: `nextion-script.js` runs the HMI's event code and the hub's display commands, `nextion-display.js` holds the display state, `nextion-view.js` renders it, `touch-input.js` turns pointer input into the firmware's `esphome.component`, `touch_start`/`touch_end` and `gesture` events, `qr-encode.js` draws QR widgets and `virtual-panel-session.js` connects it all to the WebSocket. Slider values come back the way the firmware returns them: the hub's `req_val`/`req_txt` go to the browser, which answers with `esphome.read_response`.

In sandbox mode every non-query service call is simulated; queries with `return_response` (such as `weather.get_forecasts`) always reach Home Assistant. In live mode calls reach Home Assistant, except calls targeting a settings entity of the real device (from the entity registry), which stay simulated; the `Relay Left` / `Relay Right` switches are the exception and switch for real. Calls using area, device, floor or label targets are refused in live mode because they cannot be checked safely against the protected device entities. Because the firmware toggles a relay itself when a hardware button is pressed in relay mode (`sensor.yaml`, `on_press`), the virtual device does the same through the relay's switch entity in `VirtualDevice.process_event`; the preview publishes the relay and button-entity lights to the browser. The browser can inject only the events a person causes on a panel: component touches, raw touches, gestures, hardware buttons, the idle timeout and read responses.

The page layouts are exported from both HMI files by `scripts/hmi_layout/gen_virtual_layout.py` (see [Scripts for display](nextion.md#scripts-for-display)).
