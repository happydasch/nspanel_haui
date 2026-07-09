---
title: Item Configuration
description: Item configuration — entities, state, name, value, icon, color, internal items, and popup overrides
---

# Item Configuration
An **item** is the basic building block that a panel displays or acts on. Each item can be one of two kinds:

- **External item** — wraps a real Home Assistant entity (e.g. `light.kitchen`).
  The entity's state, attributes, and services are tracked automatically.
- **Internal item** — does *not* correspond to any HA entity. Recognised keywords are
  `skip`, `text`, `navigate`, and `action`.

Items are configured through the panel editor's item editor in the Home Assistant UI. Each item entry uses the `entity` key for the entity ID (or an internal keyword), plus optional override keys:

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

The state of the item. By default, the entity state is used. It is possible to
override the state by defining a `state` in the editor. If a string is set, the
entity attribute with that name will be used. If a list is provided, the list
values are used as keys to get the state value from attributes.

### Item Name

The name of the item. The name to be returned can be configured in different ways.
By default it will return a value based on the entity - either `name` or
`friendly_name` will be returned.

If a string is provided, this will be used as the name.

If a dict is provided and the entity state matches the dict key, then this name
will be returned.

Accepts:

- `dict`:

  state → name mapping based on current entity state

- `str`:

  name to use

### Item Value

The value to display for the item. The value to be returned can be configured in
different ways. By default it will return a value based on entity state and type.

It is possible to override the value in the config of the item.

If a string is provided, this will be used as a value.

If a dict is provided and the entity state matches the dict key, then this value
will be returned.

Accepts:

- `dict`:

  state → value mapping based on current entity state

- `str`:

  value to use

### Item Icon

[Icons Cheatsheet](https://htmlpreview.github.io/?https://raw.githubusercontent.com/happydasch/nspanel_haui/master/docs/cheatsheet.html)

#### Templating using HomeAssistant

name, value, icon and color can also be templated. The value needs to start with `template:`

- `template:` home assistant template

#### Icon value type

- `dict`:

  state → icon mapping based on current entity state

- `str`:

  icon to use

### Item Color

Selected values can be entered in different formats:

- `dict`:

  state → color mapping based on current entity state

  **Note:** Use quotes for `on` and `off` to prevent YAML interpreting them as booleans.

- `list`, `tuple`:

  color to use as list with RGB values

- `str`, `int`:

  color to use as RGB565 number

### Internal Items

Internal items begin with a keyword followed by `:` or just the keyword.
These items have no backing HA entity — they are handled directly.

#### Item: skip

- `skip`

  The item should be skipped. This is the same as setting no entity.

#### Item: text

- `text`

  Use the text instead of an entity. The text is available as the item value.
  `text:Text to use`

#### Item: navigate

- `navigate`

  Navigate to the panel with the key `navigate:key`

#### Item: action

- `action`

  Action to execute.

  Pass parameters using `action_data`

### Override a default popup

`popup_key` string

A different than the default popup can be opened when executing by
setting `popup_key` to the panel key to open.