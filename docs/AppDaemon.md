# AppDaemon Component Details

NSPanelHAUI is the backend that allows to manage home automation devices using the NSPanel.

- [AppDaemon Component Details](#appdaemon-component-details)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Structure](#structure)
    - [Base Component](#base-component)
    - [App](#app)
    - [Config](#config)
    - [Device](#device)
    - [Page](#page)
    - [Panel](#panel)
    - [Entity](#entity)
  - [Connection](#connection)
  - [Navigation](#navigation)
  - [Gestures](#gestures)
  - [Updates](#updates)
  - [Events](#events)
  - [Communication](#communication)
  - [Available Pages](#available-pages)
  - [Available Panels](#available-panels)
  - [Resources](#resources)

## Requirements

MQTT configured, see `appdaemon/appdaemon.yaml` for an example config.
pip requirements: babel, pillow

## Installation

1. Install AppDaemon
2. Edit AppDaemon config
3. Copy HAUI app to server
4. Edit HAUI config
5. Restart AppDaemon

## Structure

The classes are structured as described below.

### Base Component

All parts of haui are based on the `haui.base.HAUIBase` class. This class provides some basic functionality. There are more specialized classes, which extend from `HAUIBase`:

- `haui.base.HAUIBaseVars`
  Base class with vars support

- `haui.base.HAUIPage`
  Page representation, this class is used when interacting with the page on the device

- `haui.base.HAUIPart`
  Part with start/stop methods

### App

`NSPanelHAUI`

The lifetime of a page is:

- initialize
- start
- terminate
- stop

### Config

`haui.config.HAUIConfig`

The configuration is taken from the appdaemon app config. This class allows to process the config values and gives access to panels and entities.

### Device

`haui.device.HAUIDevice`

This class represents the whole device.

The lifetime of a page is:

- start
- stop

### Page

`haui.page.HAUIPage`

This class represents a single page on the display.

The lifetime of a page is:

- start_page
- stop_page

### Panel

`haui.config.HAUIConfigPanel`

The panel represents a configured page. The panel contains the configuration and entities to use. The configuration values are taken from the config.

The lifetime of a panel is:

- **start_panel**(panel)
- **config_panel**(panel)
- **before_render_panel**(panel)
  -> if True, panel can be rendered
  -> if False, panel will not be rendered
  - **render_panel**(panel)
- **after_render_panel**(panel, rendered)
- **stop_panel**(panel)

While a panel is active, it can be refreshed using:

- **refresh_panel**()

  re-renders the currently set panel by calling render_panel. This will not be triggered automatically.

### Entity

haui.config.HAUIConfigEntity

The entity represents a configured entity. The configuration values are taken from the config.

## Connection

The connection is being kept alive by sending heartbeats after connection process. The app will tell the device to reconnect or disconnect if needed.

All connection related functionality can be found in `haui.controller.HAUIConnectionController`.

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

All events are wrapped in the `haui.base.HAUIEvent` class. This class provides basic access to events received via MQTT.

## Communication

Most of the communication happens by publishing to MQTT. There are two commands to change the display `send_command` and `send_commands`. It is possible to record all calls to send_cmd of `haui.page.HAUIPage` and to use them together with send_commands:

```python
# start recording of commands to be sent
self.start_rec_cmd()
...

# call render request for page
self.render_panel(panel)

Execute some commands ...

...
# stop recording of commands to be sent
commands = self.stop_rec_cmd(send_commands=False)
self.send_mqtt_json('send_commands', {'commands': commands})
```

every command that ist sent between `start_rec_cmd` and `stop_rec_cmd` will be stored and returned when `stop_rec_cmd` is being called. By default `stop_rec_cmd` will automatically send the recorded commands.

## Available Pages

The pages represent pages on the nextion displays. The pages interact with the ESP and are the main place where to add code for interaction with the device. All pages are defined in `haui.page.*`. See `haui.page.HAUIPage` for functionality.

## Available Panels

Panels are configured representations of a page. A page can have multiple panels, like the alarm page, which is used for alarm activation and the unlock popup. There can be multiple panels using the same page. All panels can have a custom key defined, which is used for navigation. See [Panels Overview](panels/README.md) for more details about the different panels.

## Resources

- https://github.com/joBr99/nspanel-lovelace-ui
- https://github.com/joBr99/Generate-HASP-Fonts
- https://docs.nspanel.pky.eu/
