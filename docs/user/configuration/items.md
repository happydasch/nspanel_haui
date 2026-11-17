---
title: Item Configuration
description: Item configuration — entities, state, name, value, icon, color, internal items, and popup overrides
---

# Item Configuration

An **item** is one thing a panel shows or acts on: a tile on a grid, a row on a row panel, the light of a light panel. You edit items in the panel editor.

There are two kinds of items:

- **Entity items** show a Home Assistant entity, for example `light.kitchen`.
- **Internal items** do something without an entity: show a text, open a panel or call a service. See [Internal items](#internal-items).

## Fields

Pick the entity in the **entity picker**. **Name**, **Icon** and **Color** follow it; the other fields are in the **Advanced** section. Leave them empty to use the entity's own values.

| Field | What it changes | Default |
|-------|-----------------|---------|
| `item` | The entity, or the type of an internal item | |
| `name` | The name shown | The entity's name |
| `value` | The value shown | The entity's state |
| `icon` | The icon | The entity's icon |
| `color` | The color of the icon | A color for the entity's type and state |
| `state` | Which attribute counts as the state | The entity's state |
| `popup_key` | The panel that opens when the item is tapped | The popup for the entity's type |

### Values that depend on the state

`name`, `value`, `icon` and `color` accept more than a fixed value:

- **A fixed value**, for example `Kitchen` or `mdi:lightbulb`.
- **One value per state**, for example *Lights On* while the light is `on` and *Lights Off* while it is `off`.
- **A template**, written in Home Assistant's template syntax:

    ```jinja
    {{ states('sensor.temperature') }} °C
    ```

    The editor shows the result of a template as a preview. `mdi:` icon names inside a template are shown as icons on the display. The older `template:` prefix still works.

For an entity item, each of these fields has a switch beside its label: **One value** or **Per state**. **Per state** turns the field into a list with one row per state:

- **State**: the state the row is for. The field suggests the entity's current state, the states of its kind (`on` and `off` for a light, `home` and `not_home` for a person, the options of a select), and `unavailable`.
- **The value** for that state, in the field's own control: a text or template for the name and value, the icon picker, the color field.
- **+ Add state** adds a row; the bin icon removes one.

A state without a row, or a row without a value, uses the default: the entity's own name, icon, color or state. The first row of a state counts; a second row of the same state is marked and not used. Switching back to **One value** keeps the value of the entity's current state.

When the item's [state](#item-state) is an attribute, a row matches the attribute's value. Only a text value can match: an attribute that holds a number or a list never does.

The editor stores the rows as a JSON object, for example `{"on": "Lights On", "off": "Lights Off"}`. Typing such an object into a field opens it as rows.

### Item name

The name shown for the item. Plain text, one name per state, or a template.

### Item value

The value shown for the item. A number (`42`, `3.14`), a text, one value per state, or a template. A person, for example, can show *At home* for the state `home` and *Away* for `not_home`.

### Item icon

Pick an icon in the icon picker, or one icon per state, for example `mdi:lightbulb` for `on` and `mdi:lightbulb-outline` for `off`.

The [Icons Cheatsheet](../../cheatsheet.html) shows all icons.

### Item color

Click the swatch at the start of the field to open the color picker, choose a recent or preset color with the palette button next to it, or type the color:

| Format | Example |
|--------|---------|
| Hex | `#ff6600` |
| RGB | `[255, 102, 0]` |
| RGB565 number | `63488` |
| One color per state | **Per state**, see [Values that depend on the state](#values-that-depend-on-the-state) |
| Template | `{{ ... }}` |

A typed RGB list or RGB565 number is stored when you leave the field, and the field then shows it as its hex color.

### Item state

By default the entity's state is used. To use an attribute instead, enter:

- **The attribute's name**, for example `brightness`.
- **A path** as a JSON array, for a value inside an attribute: `["forecast", 0, "condition"]` is the condition of the first entry of a `forecast` attribute.

## Internal items

An internal item has no entity. Choose its type in the item's type selector, then enter its value.

| Type | What it does | Value |
|------|--------------|-------|
| `skip` | Leaves the place empty | |
| `text` | Shows a text | The text |
| `navigate` | Opens another panel when tapped | The key of the panel |
| `action` | Calls a Home Assistant service when tapped | The service, for example `light.toggle` |

An `action` can pass data to the service. Enter it as a JSON object in the **Service data** field:

```json
{"brightness": 255, "transition": 2}
```

When the service is a script, the keys of this object are available as variables in the script.

## Override a default popup

Tapping an item opens the popup for its entity type:

| Entity type | Popup |
|-------------|-------|
| `light` | `popup_light` |
| `media_player` | `popup_media_player` |
| `vacuum` | `popup_vacuum` |
| `cover` | `popup_cover` |
| `climate` | `popup_climate` |
| `alarm_control_panel` | `popup_alarm` |

Items of other types run their normal action when tapped: toggle, press, and so on.

To open something else, enter a panel key in `popup_key`:

- **Another popup**, for example `popup_timer`. This works for every item, also for entity types without a popup of their own.
- **One of your own panels**, for example a cover panel that is not in the navigation. It opens for the item's entity, on top of the current panel. See [Stacked Panels and Popups](panels.md#stacked-panels-and-popups).

To change the popup for *all* items of a type, change the popup itself. See [System Panel Overrides](panels.md#system-panel-overrides).
