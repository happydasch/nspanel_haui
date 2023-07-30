# Configuration Description

[README](../README.md) | [Documentation](README.md) | [Installation](Install.md) | [Configuration](Config.md) | [Panels](panels/README.md) | [FAQ](FAQ.md)

- [Configuration Description](#configuration-description)
  - [Example Configuration](#example-configuration)
  - [Common Configuration](#common-configuration)
  - [Device Configuration](#device-configuration)
  - [Navigation Configuration](#navigation-configuration)
  - [MQTT Controller](#mqtt-controller)
  - [Update Controller](#update-controller)
  - [Connection Controller](#connection-controller)
  - [Panels](#panels)
    - [Panel Modes](#panel-modes)
    - [Accessing a panel](#accessing-a-panel)
    - [Closing a panel automatically](#closing-a-panel-automatically)
    - [Using a Panel as a Home Panel](#using-a-panel-as-a-home-panel)
    - [Using a Panel as a Sleep Panel](#using-a-panel-as-a-sleep-panel)
    - [Using Panel as a Wakeup Panel](#using-panel-as-a-wakeup-panel)
    - [Locking a Panel with a Code](#locking-a-panel-with-a-code)
  - [Entities](#entities)
    - [Entity State](#entity-state)
    - [Entity Name](#entity-name)
    - [Entity Value](#entity-value)
    - [Entity Icon](#entity-icon)
      - [Templating using HomeAssistant](#templating-using-homeassistant)
      - [Icon value type](#icon-value-type)
    - [Entity Color](#entity-color)
    - [Internal Entities](#internal-entities)
      - [Entity: skip](#entity-skip)
      - [Entity: text](#entity-text)
      - [Entity: navigate](#entity-navigate)
      - [Entity: script](#entity-script)

## Example Configuration

To get an idea of the configuration, take also a look into [example configurations](Example_Config.md).

## Common Configuration

For time and date formats see:

Babel Documentation [https://babel.pocoo.org/en/latest/dates.html#date-fields](https://babel.pocoo.org/en/latest/dates.html#date-fields)

Python Documenation [https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes)

- `time_format` string

  Time format

- `date_format` string

  Date format

- `date_format_babel` string

  Babel date format

```yaml
time_format: "%H:%M"
date_format: "%A, %d. %B %Y"
date_format_babel: "full"
```

## Device Configuration

`device` dict

- `device_name` string

  The name of the panel device, defaults to received mqtt_device_name value

- `locale` string

  The locale of the device

- `button_left_entity` string

  The entity to use for button left. Default None.

- `button_right_entity` string

  The entity to use for button right. Default None.

- `show_home_button` bool

  Should the panels show a home button. Default False.

- `log_commands` bool

  Should commands be logged. Default False.

```yaml
device:
  device_name: null
  locale: "en_US"
  button_left_entity: null
  button_right_entity: null
  show_home_button: false
  log_commands: false
```

## Navigation Configuration

`navigation` dict

```yaml
navigation:
  page_timeout: 2.0
```

## MQTT Controller

`mqtt` dict

```yaml
mqtt:
  topic_prefix: nspanel_haui/nspanel_haui
```

- `topic_prefix`

## Update Controller

The update controller is responsible for checking version informations and notify about any issues.

To enable update checks set an interval > 0 and/or set check_on_connect to true.

`update` dict

```yaml:
update:
  auto_update: false  # Update automatically on new releases
  tft_filename: nspanel_haui.tft  # The asset filename to load
  check_on_connect: false  # Should be checked for updates when connected
  on_connect_delay: 60  # Delay between connect and check
  interval: 0  # Set to 86400 for daily checks
```

- `auto_update` bool
- `tft_filename` string
- `interval` int
- `check_on_connect` bool
- `on_connect_delay` int

## Connection Controller

`connection` dict

```yaml
connection:
  interval: null
  overdue_factor: 2.0
```

- `interval` int
- `overdue_factor` float

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
# single entity
entity: None
# multiple entities
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

`home_panel` string

If not defined the first configured panel will be used. If defined, then the defined home panel will be used.

```yaml
home_panel: true
```

### Using a Panel as a Sleep Panel

`sleep_panel` string

After page_timeout the sleep panel will be activated.

```yaml
sleep_panel: true
```

### Using Panel as a Wakeup Panel

`wakeup_panel` string

```yaml
wakeup_panel: true
```

When the display changes into dimmed state and a sleep panel is set or changes into sleep state and wakes up, then if no wakeup panel is defined, it will return to the home panel.

If defined, it will return to the defined panel.

If no sleep occured but page was changed, it will return to the last active panel.

### Locking a Panel with a Code

`unlock_code` string

```yaml
unlock_code: "1234"
```

Panels can be locked with a code. If a unlock_code is set, the panel will be only accessible after entering the unlock code.

## Entities

`HAUIConfigEntity` is used internally to provide access to the entity from the config.

Basic values:

- `entity` the entity id (ex. sensor.temperature)
- `name` name override, a default entity name will be used if not set
- `value` value override, a default entity value will be used if not set
- `icon` icon override, a default entity icon will be used if not set
- `color` color override, a default entity color will be used if not set
- `state` state override, by default state will be used

the name, value, icon and color can also contain homeassistant template code. These values can contain `mdi:` or `hass:` icons which will be replaced by its unicode representations.

### Entity State

`haui_entity.get_state()`

The state of the entity. By default, the state will be used. It is possible to override the state value by defining a state in config. If a string is set, the entity attribute with that name will be used. If a list is provided, the list values are being used as keys to get the state value from attributes.

```yaml
# use attribute forecast condition as state of a weather entity
  - entity: weather.home
    state: ["forecast", 1, "condition"]

# use attribute temperature as state
  - entity: weather.home
    state: "temperature"
```

### Entity Name

`haui_entity.get_name()`

The name of the entity. The name to be returned can be configured in different ways. By default it will return a value based on the entity. Either name or friendly name will be returned.

If a string is provided, this will be used as the name.

If a dict is provided and the entity state matches the dict key, then this name will be returned.

Accepts:

- `dict`:

  state: value assignment based on current entity state

  ```yaml
  - entity: switch.example_entity
    name:
      on: "name x"
      off: "name y"
  ```

- `str`:

  name to use

  ```yaml
  name: Name
  ```

### Entity Value

`haui_entity.get_value()`

The entity value to display. The value to be returned can be configured in different ways. By default it will return a value based on entity state and type.

It is possible to override the value in the config of the entity.

If a string is provided, this will be used as a value.

If a dict is provided and the entity state matches the dict key, then this value will be returned.

Accepts:

- `dict`:

  state: value assignment based on current entity state

  ```yaml
  value:
    on: value x
    off: value y
  ```

- `str`:

  value to use

  ```yaml
  value: Text
  ```

### Entity Icon

[Icons Cheatsheet](https://htmlpreview.github.io/?https://raw.githubusercontent.com/happydasch/nspanel_haui/master/docs/cheatsheet.html)

`haui_entity.get_icon()`

#### Templating using HomeAssistant

name, value, icon and color can also be templated. The value needs to start with `template:`

- `template:` home assistant template

#### Icon value type

- `dict`:

  state: icon assignment based on current entity state

  ```yaml
  icon:
    on: "icon_name_x"
    off: "icon_name_y"
  ```

- `str`:

  icon to use

  ```yaml
  icon: "icon_name"
  ```

### Entity Color

`haui_entity.get_color()`

- `dict`:

  state: color assignment based on current entity state

  ```yaml
  color:
    on: [255, 255, 255]
    off: "6339"
  ```

- `list`, `tuple`:

  color to use as list with rgb values

  ```yaml
  color: [255, 255, 255]
  ```

- `str`, `int`:

  color to use as rgb565 number

  ```yaml
  color: "6339"
  color: 6339
  ```

### Internal Entities

Internal entities begin with a keyword followed by `:` or just the keyword.

```yaml
  - entity: skip
  - entity: text:Text to use as value
...
  - entity: navigate:key
```

#### Entity: skip

- `skip`

  The entity should be skipped. This is the same as `entity: null`

  ```yaml
  - entity: "skip"
  - entity: skip
  ...
  - entity: null
  ```

#### Entity: text

- `text`

  Use the text instead of an entity, the text is available as the entity value
  `text:Text to use`

  ```yaml
  - entity: "text:Text to use"
  ```

#### Entity: navigate

- `navigate`

  Navigate to the panel with the key `navigate:key`

  ```yaml
  - entity: "navigate:key"
  ```

#### Entity: script

- `script`

  Script to execute

  Pass parameters using `script_data`

  ```yaml
  - entity: "script:script_to_call"
    script_data:
      val: x
  ```
