---
title: Panel Configuration
description: Panel configuration — modes, navigation, home/sleep/wakeup, and locking
---

# Panel Configuration

[README](../../README.md) | [Documentation](../README.md) | [Installation](../Install.md) | [Configuration](../Config.md) | [Panels](../panels/README.md) | [FAQ](../FAQ.md)

[< Configuration](../Config.md)

- [Panel Configuration](#panel-configuration)
  - [Panel Modes](#panel-modes)
  - [Accessing a panel](#accessing-a-panel)
  - [Closing a panel automatically](#closing-a-panel-automatically)
  - [Using a Panel as a Home Panel](#using-a-panel-as-a-home-panel)
  - [Using a Panel as a Sleep Panel](#using-a-panel-as-a-sleep-panel)
  - [Using Panel as a Wakeup Panel](#using-panel-as-a-wakeup-panel)
  - [Locking a Panel with a Code](#locking-a-panel-with-a-code)

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

See [Panels Overview](../panels/README.md) for more details about the different panels and configuration.

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