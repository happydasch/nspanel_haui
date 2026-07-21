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

1. Install the NSPanel HAUI custom integration via HACS or by copying to `custom_components/nspanel_haui/`
2. Add the integration via **Settings → Devices & Services → Add Integration → NSPanel HAUI** (config flow)
3. Restart Home Assistant

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

The configuration is taken from the Hub app config. This class allows to process the config values and gives access to panels and entities.

### Device

`haui.device.HAUIDevice`

This class represents the whole device.

The lifetime of a device is:

- start
- stop

### Page

`haui.abstract.haui_page.HAUIPage`

This class represents a single page on the display.

The lifetime of a page is:

- start_page
- stop_page

### Panel

`haui.abstract.haui_panel.HAUIPanel`

The panel represents a configured page. The panel contains the configuration and entities to use. The configuration values are taken from the config.

The lifetime of a panel is:

- **create_panel**(panel)

page start ..

- **prepare()** (optional) — set instance attribute defaults, called during `__init__()`
- **start_panel**(panel)
- **config_panel**(panel)
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

    Page->>Panel: create_panel(panel)
    Note over Panel: panel config loaded

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

    CONNECTED --> DISCONNECTED: heartbeat timeout<br/>or hub_connection_closed
    CONNECTED --> CONNECTED: bidirectional heartbeats<br/>(every heartbeat_interval)

    DISCONNECTED --> DISCONNECTED: livesign detection<br/>(re-initiate handshake)
```

### Bidirectional Heartbeats

Once connected, both sides independently monitor liveness:

- **Hub→Device**: Periodic `hub_heartbeat` action at the device-declared `heartbeat_interval` (default 5s). First heartbeat fires immediately ("now+0"), then every interval.
- **Device→Hub**: `esphome.heartbeat` events update `_last_time` in the controller. Timeout = `interval × overdue_factor` (default 10s).

### Timeout Monitoring

The `_check_timeout()` method runs on a periodic timer (same interval as heartbeats):
- Only active in CONNECTED state
- If `time.monotonic() > _last_time + max(interval × factor, 10.0)`, transitions to DISCONNECTED
- Extended-disconnect warnings log every 60s when state stays DISCONNECTED

### Reconnection (Livesign Detection)

Any event received while in DISCONNECTED (except `res_connection` and `res_device_state`) triggers immediate handshake re-initiation:
1. Sets state → HANDSHAKING
2. Sends `hub_connection_response` with hub version
3. Returns early (the same event is NOT processed further)
4. Subsequent `res_connection` → `res_device_state` complete the handshake

### Connection State Callbacks

On state transitions:
- **CONNECTED**: Sends `hub_connection_initialized`, `reset_last_interaction`, starts timers, invokes `callback_connection(True)`
- **DISCONNECTED** (from CONNECTED): Sends `hub_connection_closed`, stops timers, invokes `callback_connection(False)`

The callback propagates to `HAUIDevice.set_connected()`, which handles navigation (open sys_system on first connect, restore panel on reconnect).

## Navigation

The navigation is kept simple. There are navigateable panels and non-navigateable panels. Panels that are not navigateable will be kept in a stack when opened so that it is possible to return to the last navigateable item.

All navigation related functionality can be found in `haui.controller.HAUINavigationController`.

## Gestures

Supported gestures: swipe_left, swipe_right, swipe_up, swipe_down

There is also support for gesture sequences.

All gesture functionality can be found in `haui.controller.HAUIGestureController`

## Updates

All update functionality can be found in `haui.controller.HAUIUpdateController`

## Events

All events are wrapped in the `haui.abstract.haui_event.HAUIEvent` class. This class provides basic access to events received via ESPHome.

## Communication

Most of the communication happens by publishing to ESPHome. There are two commands to change the display `send_cmd` and `send_cmds`. It is possible to record all calls to send_cmd of `haui.abstract.haui_page.HAUIPage` and to use them together with send_cmds:

```python
# batch multiple commands using the rec_cmd context manager
with self.rec_cmd:
    self.set_component_text(self.components.title, "Hello")
    self.set_component_value(self.components.t_info, 42)
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

The linking is handled in `_link_esphome_device()` in `__init__.py` and runs both during initial setup and when a device appears later (race condition handling via the device registry listener).

## Available Panels

Panels are configured representations of a page. A page can have multiple panels, like the alarm page, which is used for alarm activation and the unlock popup. There can be multiple panels using the same page. All panels can have a custom key defined, which is used for navigation. See [Panels Overview](panels/README.md) for more details about the different panels.
