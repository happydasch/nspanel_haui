# Configuration

[README](../README.md) | [Documentation](README.md) | [Installation](Install.md) | [Configuration](Config.md) | [Panels](panels/README.md) | [FAQ](FAQ.md)

- [Configuration](#configuration)
  - [Example Configuration](#example-configuration)
  - [Common Configuration](#common-configuration)
  - [Device Configuration](#device-configuration)
  - [Navigation Configuration](#navigation-configuration)
  - [Notification Configuration](#notification-configuration)
  - [Update Controller](#update-controller)
  - [Connection Controller](#connection-controller)
  - [Gesture Controller](#gesture-controller)
  - [Panels](#panels)
    - [Panel Modes](#panel-modes)
    - [Accessing a panel](#accessing-a-panel)
    - [Closing a panel automatically](#closing-a-panel-automatically)
    - [Using a Panel as a Home Panel](#using-a-panel-as-a-home-panel)
    - [Using a Panel as a Sleep Panel](#using-a-panel-as-a-sleep-panel)
    - [Using Panel as a Wakeup Panel](#using-panel-as-a-wakeup-panel)
    - [Locking a Panel with a Code](#locking-a-panel-with-a-code)
  - [Items](#items)
    - [How items relate to HA entities](#how-items-relate-to-ha-entities)
    - [Item State](#item-state)
    - [Item Name](#item-name)
    - [Item Value](#item-value)
    - [Item Icon](#item-icon)
      - [Templating using HomeAssistant](#templating-using-homeassistant)
      - [Icon value type](#icon-value-type)
    - [Item Color](#item-color)
    - [Internal Items](#internal-items)
      - [Item: skip](#item-skip)
      - [Item: text](#item-text)
      - [Item: navigate](#item-navigate)
      - [Item: action](#item-action)
    - [Override a default popup](#override-a-default-popup)

## Example Configuration

To get an idea of the configuration, take also a look into [example configurations](Example_Config.md).

## Common Configuration

For time and date formats see:

CLDR Locale Data (see `haui/utils/locale_data.py` for supported format keys)

Python Documentation [https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes)

- `time_format` string

  Time format

- `date_format` string

  Date format

- `date_format_locale` string

  CLDR locale format key (e.g. `full`, `long`, `medium`, `short`).
  Deprecated alias: `date_format_babel` (still supported for backward compatibility).

```yaml
time_format: "%H:%M"
date_format: "%A, %d. %B %Y"
date_format_locale: "full"
```

## Device Configuration

`device` dict

- `name` string

  The name of the panel device

- `locale` string

  The locale of the device

- `panels` list

  Per-device panel list.  Each panel is at minimum ``{\"type\": \"<type_key>\"}``.
  Default ``[{\"type\": \"clock\"}]``.

- `esphome_device_id` string

  The ESPHome device ID this config entry is linked to.  Set automatically
  during discovery.  Default empty.

- `enabled` bool

  Whether the device is active at runtime.  Disabled devices are skipped
  without deleting their config.  Default ``True``.

- `home_panel` string

  Panel key of the home panel.  Empty means no home panel set.

- `sleep_panel` string

  Panel key of the panel shown when the display goes to sleep.  Empty means
  no sleep panel is set.

- `wakeup_panel` string

  Panel key of the panel shown when the display wakes up.  Empty means no
  wakeup panel is set.

- `show_notifications_button` bool

  Whether the notifications button is visible on supported panels.
  Default ``True``.

- `button_left_entity` string

  The entity (entity ID) for the left hardware button. Default empty.

- `button_right_entity` string

  The entity (entity ID) for the right hardware button. Default empty.

- `use_relay_left` bool

  Whether the left hardware button should toggle the internal relay. Default True.

- `use_relay_right` bool

  Whether the right hardware button should toggle the internal relay. Default True.

- `show_home_button` bool

  Should the panels show a home button. Default False.

- `show_sleep_button` bool

  Should the panels show a sleep button when on home panel. Default False.

- `log_items` bool

  Should display items/commands be logged. Default False.

- `home_on_wakeup` bool

  Should the display exit the sleep/wakeup panel and return home directly after wakeup. Default False.

- `home_on_first_touch` bool

  Should the display exit the sleep/wakeup panel and return home on first iteraction event or wait
  until touched again. Default True.

- `home_only_when_on` bool

  Should the display exit the sleep/wakeup panel and return home only when the display state is on. Default False.

- `home_on_button_toggle` bool

  Should the display exit the sleep/wakeup panel and return home when a button is toggled. Default False.

- `always_return_to_home` bool

  Should the display always return to the home panel or should it restore the previous panel. Default False.

- `sound_on_startup` bool

  Should a sound be played when the display is connected after startup. Default True.

- `sound_on_notification` bool

  Should a sound be played when the display receives a non-persistent notification. Default True.

- `return_to_home_after_seconds` int

  Number of seconds of inactivity on the home panel before auto-navigating
  back to the home panel.  Default ``0`` (disabled).

- `debug_level` int

  Debug verbosity level (0-3). Higher values produce more log output. Default ``0``.

```yaml
device:
  name: ""
  locale: "en_US"
  panels: [{"type": "clock"}]
  esphome_device_id: ""
  enabled: true
  button_left_entity: ""
  button_right_entity: ""
  home_panel: ""
  sleep_panel: ""
  wakeup_panel: ""
  show_home_button: false
  show_sleep_button: false
  show_notifications_button: true
  log_items: false
  debug_level: 0
  home_on_wakeup: false
  home_on_first_touch: true
  home_only_when_on: false
  home_on_button_toggle: false
  return_to_home_after_seconds: 0
  always_return_to_home: false
  use_relay_left: true
  use_relay_right: true
  sound_on_startup: true
  sound_on_notification: true
```

## Navigation Configuration

`navigation` dict

```yaml
navigation:
  page_timeout: 2.0
```

## Notification Configuration

`notification` dict

```yaml
notification: {}
```

## Update Controller

The update controller is responsible for checking version informations and notify about any issues.

To enable update checks set an interval > 0 and/or set check_on_connect to true.

`update` dict

```yaml:
update:
  auto_install: True  # Install tft file automatically if no or a unknown tft file is installed
  auto_update: false  # Update automatically on new releases
  tft_filename: nspanel_haui.tft  # The asset filename to load
  check_on_connect: false  # Should be checked for updates when connected
  on_connect_delay: 60  # Delay between connect and check
  update_interval: 0  # Set to 86400 for daily checks
```

- `auto_install` bool
- `auto_update` bool
- `tft_filename` string
- `update_interval` int
- `check_on_connect` bool
- `on_connect_delay` int

## Connection Controller

`connection` dict

```yaml
connection:
  heartbeat_interval: null
  overdue_factor: 2.0
```

- `heartbeat_interval` int
- `overdue_factor` float

## Gesture Controller

`gesture` dict

```yaml
gesture: {}
```

## Panels

`panels` list

```yaml
panels:
  - type: panel_type
    ...
```

Config values:

```yaml
# panel type (required)
type: panel_type  # for ex. weather, grid, etc.
# panel mode (Default: panel)
mode: panel  # string, panel, subpanel or popup
# internal identifier for panel
key: identifier  # string, can be used for navigation with navigate:
# title of panel
title: Panel Title
# is panel the home panel
home_panel: false
# is panel the sleep panel
sleep_panel: false
# is panel the wakeup panel
wakeup_panel: false
# show home button (Default: device config value `show_home_button`)
show_home_button: null
# single item (maps to a HA entity or internal keyword)
entity: None
# multiple items (list of entity entries)
entities: []
# unlock code for panel
unlock_code: null
# close panel after amount of time
close_timeout: null
```

See [Panels Overview](panels/README.md) for more details about the different panels and configuration.

### Panel Modes

A panel supports different modes:

- `panel` Panel, that shows up in navigation (Default)
- `subpanel` Subpanel, will not show up in navigation
- `popup` Popup, will not show up in navigation

By default a panel will be used as a navigation panel.

Each panel configured will by default be included in the navigateable panels list. To not include a panel in the navigation, set `mode` to `subpanel`. When navigating to an panel that is not navigateable then this panel will be added to a stack, so that it is always possible to return to the last item navigated.

Entry Details, Popups, Settings, About and other special pages will not appear in navigation.

```yaml
mode: panel
```

### Accessing a panel

To be able to access a panel from within the configuration, the panel needs to have a `key` defined. By this key the panel can be accessed now for navigation by using `navigation.key` as an entity.

```yaml
key: identifier
```

### Closing a panel automatically

To automatically close a panel after some amount of time, set `close_timeout` to a value bigger than 0.

```yaml
close_timeout: 2.0
```

### Using a Panel as a Home Panel

`home_panel` bool

If not defined the first configured panel will be used. If defined, then the defined home panel will be used.

**Only one panel can be a home panel**

```yaml
home_panel: true
```

### Using a Panel as a Sleep Panel

`sleep_panel` bool

After page_timeout the sleep panel will be activated.

**Only one panel can be a sleep panel**

```yaml
sleep_panel: true
```

### Using Panel as a Wakeup Panel

`wakeup_panel` bool

```yaml
wakeup_panel: true
```

When the display changes into dimmed state and a sleep panel is set or changes into sleep state and wakes up, then if no wakeup panel is defined, it will return to the home panel. If defined, it will return to the defined panel.

If no sleep occured but page was changed, it will return to the last active panel.

**Only one panel can be a wakeup panel**

```yaml
wakeup_panel: true
```

### Locking a Panel with a Code

`unlock_code` string

```yaml
unlock_code: "1234"
```

Panels can be locked with a code. If a unlock_code is set, the panel will be only accessible after entering the unlock code.

## Items

An **item** is the basic building block that a panel displays or acts on.  Each item is
represented at runtime by the ``HAUIItem`` class.  An item can be one of two kinds:

- **External item** - wraps a real Home Assistant entity (e.g. ``light.kitchen``).
  Internally delegates to ``HAUIEntity`` for entity state, attributes, and services.
- **Internal item** - does *not* correspond to any HA entity.  Recognised keywords are
  ``skip``, ``text``, ``navigate``, and ``action``.

### How items relate to HA entities

``HAUIItem`` (in ``abstract/item.py``) is the class you interact with in page code.
It extends ``HAUIBase``, so it has config access, template rendering, and logging.
For external items it holds a reference to an ``HAUIEntity`` instance.

``HAUIEntity`` (in ``abstract/entity.py``) is a **lightweight, internal bridge**.
It does *not* extend ``HAUIBase`` - it only wraps an entity ID and provides
synchronous access to state, attributes, and service calls through the ``HAAdapter`` bridge.
You never create an ``HAUIEntity`` directly in config; you create an ``HAUIItem``
that uses one internally.

In your YAML config each item entry uses the ``entity`` key for the entity ID
(or an internal keyword), plus optional override keys:

- ``entity`` - the HA entity id (e.g. ``sensor.temperature``) or internal keyword
- ``name`` - name override; defaults to the entity's friendly name
- ``value`` - value override; defaults to the entity's state or derived value
- ``icon`` - icon override; defaults to the entity's icon
- ``color`` - color override; defaults to a type-based color
- ``state`` - state override; by default the entity's ``state`` is used

name, value, icon and color can also contain Home Assistant template code.
These values may contain ``mdi:`` icons which will be replaced by their
unicode representations.

### Item State

``haui_item.get_item_state()``

The state of the item. By default, the entity state is used. It is possible to
override the state by defining a ``state`` in config. If a string is set, the
entity attribute with that name will be used. If a list is provided, the list
values are used as keys to get the state value from attributes.

```yaml
# use attribute forecast condition as state of a weather entity
  - entity: weather.home
    state: ["forecast", 1, "condition"]

# use attribute temperature as state
  - entity: weather.home
    state: "temperature"
```

### Item Name

``haui_item.get_name()``

The name of the item. The name to be returned can be configured in different ways.
By default it will return a value based on the entity - either ``name`` or
``friendly_name`` will be returned.

If a string is provided, this will be used as the name.

If a dict is provided and the entity state matches the dict key, then this name
will be returned.

Accepts:

- ``dict``:

  state → name mapping based on current entity state

  ```yaml
  - entity: switch.example_entity
    name:
      on: "name x"
      off: "name y"
  ```

- ``str``:

  name to use

  ```yaml
  name: Name
  ```

### Item Value

``haui_item.get_value()``

The value to display for the item. The value to be returned can be configured in
different ways. By default it will return a value based on entity state and type.

It is possible to override the value in the config of the item.

If a string is provided, this will be used as a value.

If a dict is provided and the entity state matches the dict key, then this value
will be returned.

Accepts:

- ``dict``:

  state → value mapping based on current entity state

  ```yaml
  value:
    on: value x
    off: value y
  ```

- ``str``:

  value to use

  ```yaml
  value: Text
  ```

### Item Icon

[Icons Cheatsheet](https://htmlpreview.github.io/?https://raw.githubusercontent.com/happydasch/nspanel_haui/master/docs/cheatsheet.html)

``haui_item.get_icon()``

#### Templating using HomeAssistant

name, value, icon and color can also be templated. The value needs to start with ``template:``

- ``template:`` home assistant template

#### Icon value type

- ``dict``:

  state → icon mapping based on current entity state

  ```yaml
  icon:
    on: "icon_name_x"
    off: "icon_name_y"
  ```

- ``str``:

  icon to use

  ```yaml
  icon: "icon_name"
  ```

### Item Color

``haui_item.get_color()``

- ``dict``:

  state → color mapping based on current entity state

  **Note:** Use quotes for ``on`` and ``off`` to prevent YAML interpreting them as booleans.

  ```yaml
  color:
    "on": [255, 255, 255]
    "off": "6339"
  ```

- ``list``, ``tuple``:

  color to use as list with RGB values

  ```yaml
  color: [255, 255, 255]
  ```

- ``str``, ``int``:

  color to use as RGB565 number

  ```yaml
  color: "6339"
  color: 6339
  ```

### Internal Items

Internal items begin with a keyword followed by ``:`` or just the keyword.
These items do **not** wrap an ``HAUIEntity`` - ``HAUIItem`` handles them directly.

```yaml
  - entity: skip
  - entity: text:Text to use as value
...
  - entity: navigate:key
```

#### Item: skip

- ``skip``

  The item should be skipped. This is the same as ``entity: null``.

  ```yaml
  - entity: "skip"
  - entity: skip
  ...
  - entity: null
  ```

#### Item: text

- ``text``

  Use the text instead of an entity. The text is available as the item value.
  ``text:Text to use``

  ```yaml
  - entity: "text:Text to use"
  ```

#### Item: navigate

- ``navigate``

  Navigate to the panel with the key ``navigate:key``

  ```yaml
  - entity: "navigate:key"
  ```

#### Item: action

- ``action``

  Action to execute.

  Pass parameters using ``action_data``

  ```yaml
  - entity: "action:action_to_call"
    action_data:
      val: x
  ```

### Override a default popup

``popup_key`` string

```yaml
popup_key: popup_media_player
```

A different than the default popup can be opened when executing by
setting ``popup_key`` to the panel key to open.
