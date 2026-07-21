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

Items are configured entirely through the panel editor's **item editor** in the Home Assistant UI
— there is no YAML configuration for items. Each entry uses the `item` key for the entity ID
(or an internal keyword), plus optional override fields in the editor's collapsible **Advanced** section:

| Field       | Description |
|-------------|-------------|
| `item`      | The HA entity ID (e.g. `sensor.temperature`) or internal keyword. The entity picker shows available entities; for keywords, choose from the type selector. |
| `name`      | Display name override; defaults to the entity's `friendly_name`. Accepts plain text, a JSON object (state-keyed mapping), or a template. |
| `value`     | Display value override; defaults to the entity's state. Typed field — accepts integers, floats, JSON objects (state-keyed mapping), JSON arrays, or a template. |
| `icon`      | Icon override; defaults to the entity's icon. Uses an icon picker with `mdi:` names, a JSON object (state-keyed mapping), or a template. |
| `color`     | Color override; defaults to a type-based color. Text input with a native color picker — accepts hex (`#rrggbb`), RGB triplet (`[r,g,b]`), RGB565 integer (0–65535), a JSON object (state-keyed mapping), or a template. |
| `state`     | State override; defaults to the entity's `state`. Typed field — an attribute name (string) or a JSON array for nested attribute access. |
| `popup_key` | The key of a popup panel configuration that opens when this item is tapped. Leave empty to use the default popup behaviour. |

### Item state

By default the entity's `state` attribute is used. To override:

- **String** — the entity attribute with that name will be used (e.g. `"brightness"`).
- **Array (JSON)** — the array values are used as keys to drill into nested attributes.
  Entered as a JSON array: `["attributes", "rgb_color"]`.

### Item name

Overrides the display name. Supported formats:

- **Plain text** — a fixed name string.
- **JSON object** (state-keyed) — a mapping from entity state values to names:
  ```json
  {"on": "Lights On", "off": "Lights Off"}
  ```
- **Template** — a Home Assistant template prefixed with `template:` or enclosed in `{{ ... }}`.

### Item value

Overrides the displayed value. This is a **typed field** in the editor — values are parsed through `parseFieldValue`:

- **Integer or float** — typed directly (e.g. `42`, `3.14`).
- **JSON object** (state-keyed) — a mapping from entity state values to display values:
  ```json
  {"home": "At home", "not_home": "Away"}
  ```
- **JSON array** — a list of values.
- **String** — used as-is.
- **Template** — a Home Assistant template prefixed with `template:` or enclosed in `{{ ... }}`.

### Item icon

Overrides the entity icon. The editor provides an icon picker with a searchable dropdown and live preview, or a text input for JSON object (state-keyed) values.

- **Icon name** — an `mdi:` icon string (e.g. `mdi:lightbulb`). The icon picker shows a searchable list of available icons.
- **JSON object** (state-keyed) — a mapping from entity state values to icon names:
  ```json
  {"on": "mdi:lightbulb", "off": "mdi:lightbulb-outline"}
  ```
  The JSON string is shown in the text input field; the icon preview falls back to the puzzle icon.
- **Template** — a Home Assistant template enclosed in `{{ ... }}`.

[Icons Cheatsheet](https://htmlpreview.github.io/?https://raw.githubusercontent.com/happydasch/nspanel_haui/master/docs/cheatsheet.html)

### Item color

Overrides the entity colour. Accepted formats:

| Format | Example |
|--------|---------|
| CSS hex | `#ff6600` |
| RGB triplet | `[255, 102, 0]` |
| RGB565 integer | `63488` |
| JSON object (state-keyed) | `{"on": "#00ff00", "off": "#ff0000"}` |
| Template | `template:{{ ... }}` or `{{ ... }}` |

The editor renders a text input with a native `<input type="color">` picker button.
Picking a colour in the picker updates the text value, preserving the original format
(hex stays hex, RGB565 stays numeric, etc.). Colour swatches for common NSPanel colours
are shown below the input for quick selection.

### Template support

name, value, icon and colour support Home Assistant templates. Template values use the
`{{ ... }}` enclosure syntax:

- **`{{ ... }}`** — rendered as a live preview in the editor when a Home Assistant
  instance is connected. Both `template:` prefix and `{{ ... }}` syntax are treated
  identically by the Python backend, but only `{{ ... }}` triggers editor-side preview.

Templates that contain `mdi:` icons will have those icons replaced with their unicode
representations on the display.

### Internal items

Internal items have no backing HA entity — they are handled directly by the panel logic.
The **item** field uses the type selector to pick an internal type, then provides a text input
for the value/key/service name.

#### skip

The item is skipped — no display slot or action. Equivalent to not configuring the item at all.

#### text

Displays custom text instead of an entity value. The entered text is used as the item value.

#### navigate

Navigates to another panel when tapped. The entered value is the **panel key** to navigate to.

#### action

Executes a Home Assistant service call when tapped. The entered value is the service name
(e.g. `light.toggle`). Additional parameters are passed as `service_data` — a JSON object
entered in the **Service data** textarea:

```json
{"brightness": 255, "transition": 2}
```

`service_data` supports template variables — keys are available as template variables in
scripts.

### Override a default popup

`popup_key` — a string containing the panel key of a popup configuration. When the item is
tapped, the specified popup panel opens instead of the default popup for the item's entity type.