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

Pick the entity in the **entity picker**. The other fields are in the **Advanced** section. Leave them empty to use the entity's own values.

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
- **One value per state**, written as a JSON object:

    ```json
    {"on": "Lights On", "off": "Lights Off"}
    ```

- **A template**, written in Home Assistant's template syntax:

    ```jinja
    {{ states('sensor.temperature') }} °C
    ```

    The editor shows the result of a template as a preview. `mdi:` icon names inside a template are shown as icons on the display. The older `template:` prefix still works.

### Item name

The name shown for the item. Plain text, one name per state, or a template.

### Item value

The value shown for the item. A number (`42`, `3.14`), a text, one value per state, or a template:

```json
{"home": "At home", "not_home": "Away"}
```

### Item icon

Pick an icon in the icon picker, or enter one icon per state:

```json
{"on": "mdi:lightbulb", "off": "mdi:lightbulb-outline"}
```

The [Icons Cheatsheet](../../cheatsheet.html) shows all icons.

### Item color

Pick a color with the color picker or one of the swatches below the field, or type it:

| Format | Example |
|--------|---------|
| Hex | `#ff6600` |
| RGB | `[255, 102, 0]` |
| RGB565 number | `63488` |
| One color per state | `{"on": "#00ff00", "off": "#ff0000"}` |
| Template | `{{ ... }}` |

### Item state

By default the entity's state is used. To use an attribute instead, enter:

- **The attribute's name**, for example `brightness`.
- **A path** as a JSON array, for a value inside an attribute: `["attributes", "rgb_color"]`.

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
