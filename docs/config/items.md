---
title: Item Configuration
description: Item configuration — entities, state, name, value, icon, color, internal items, and popup overrides
---

# Item Configuration

[README](https://github.com/happydasch/nspanel_haui) | [Documentation](../README.md) | [Installation](../Install.md) | [Configuration](../Config.md) | [Panels](../panels/README.md) | [FAQ](../FAQ.md)

[< Configuration](../Config.md)

- [Item Configuration](#item-configuration)
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

An **item** is the basic building block that a panel displays or acts on.  Each item is
represented at runtime by the `HAUIItem` class.  An item can be one of two kinds:

- **External item** - wraps a real Home Assistant entity (e.g. `light.kitchen`).
  Internally delegates to `HAUIEntity` for entity state, attributes, and services.
- **Internal item** - does *not* correspond to any HA entity.  Recognised keywords are
  `skip`, `text`, `navigate`, and `action`.

### How items relate to HA entities

`HAUIItem` (in `abstract/item.py`) is the class you interact with in page code.
It extends `HAUIBase`, so it has config access, template rendering, and logging.
For external items it holds a reference to an `HAUIEntity` instance.

`HAUIEntity` (in `abstract/entity.py`) is a **lightweight, internal bridge**.
It does *not* extend `HAUIBase` - it only wraps an entity ID and provides
synchronous access to state, attributes, and service calls through the `HAAdapter` bridge.
You never create an `HAUIEntity` directly in config; you create an `HAUIItem`
that uses one internally.

In your YAML config each item entry uses the `entity` key for the entity ID
(or an internal keyword), plus optional override keys:

- `entity` - the HA entity id (e.g. `sensor.temperature`) or internal keyword
- `name` - name override; defaults to the entity's friendly name
- `value` - value override; defaults to the entity's state or derived value
- `icon` - icon override; defaults to the entity's icon
- `color` - color override; defaults to a type-based color
- `state` - state override; by default the entity's `state` is used

name, value, icon and color can also contain Home Assistant template code.
These values may contain `mdi:` icons which will be replaced by their
unicode representations.

### Item State

`haui_item.get_item_state()`

The state of the item. By default, the entity state is used. It is possible to
override the state by defining a `state` in config. If a string is set, the
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

`haui_item.get_name()`

The name of the item. The name to be returned can be configured in different ways.
By default it will return a value based on the entity - either `name` or
`friendly_name` will be returned.

If a string is provided, this will be used as the name.

If a dict is provided and the entity state matches the dict key, then this name
will be returned.

Accepts:

- `dict`:

  state → name mapping based on current entity state

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

### Item Value

`haui_item.get_value()`

The value to display for the item. The value to be returned can be configured in
different ways. By default it will return a value based on entity state and type.

It is possible to override the value in the config of the item.

If a string is provided, this will be used as a value.

If a dict is provided and the entity state matches the dict key, then this value
will be returned.

Accepts:

- `dict`:

  state → value mapping based on current entity state

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

### Item Icon

[Icons Cheatsheet](https://htmlpreview.github.io/?https://raw.githubusercontent.com/happydasch/nspanel_haui/master/docs/cheatsheet.html)

`haui_item.get_icon()`

#### Templating using HomeAssistant

name, value, icon and color can also be templated. The value needs to start with `template:`

- `template:` home assistant template

#### Icon value type

- `dict`:

  state → icon mapping based on current entity state

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

### Item Color

`haui_item.get_color()`

- `dict`:

  state → color mapping based on current entity state

  **Note:** Use quotes for `on` and `off` to prevent YAML interpreting them as booleans.

  ```yaml
  color:
    "on": [255, 255, 255]
    "off": "6339"
  ```

- `list`, `tuple`:

  color to use as list with RGB values

  ```yaml
  color: [255, 255, 255]
  ```

- `str`, `int`:

  color to use as RGB565 number

  ```yaml
  color: "6339"
  color: 6339
  ```

### Internal Items

Internal items begin with a keyword followed by `:` or just the keyword.
These items do **not** wrap an `HAUIEntity` - `HAUIItem` handles them directly.

```yaml
  - entity: skip
  - entity: text:Text to use as value
...
  - entity: navigate:key
```

#### Item: skip

- `skip`

  The item should be skipped. This is the same as `entity: null`.

  ```yaml
  - entity: "skip"
  - entity: skip
  ...
  - entity: null
  ```

#### Item: text

- `text`

  Use the text instead of an entity. The text is available as the item value.
  `text:Text to use`

  ```yaml
  - entity: "text:Text to use"
  ```

#### Item: navigate

- `navigate`

  Navigate to the panel with the key `navigate:key`

  ```yaml
  - entity: "navigate:key"
  ```

#### Item: action

- `action`

  Action to execute.

  Pass parameters using `action_data`

  ```yaml
  - entity: "action:action_to_call"
    action_data:
      val: x
  ```

### Override a default popup

`popup_key` string

```yaml
popup_key: popup_media_player
```

A different than the default popup can be opened when executing by
setting `popup_key` to the panel key to open.