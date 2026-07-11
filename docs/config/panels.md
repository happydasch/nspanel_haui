---
title: Panel Configuration
description: Panel configuration — modes, navigation, home/sleep/wakeup, and locking
---

# Panel Configuration

Panels are configured through the panel editor in the Home Assistant UI. Each panel has the following configurable options:

See [Panels Overview](../panels/README.md) for more details about the different panels and configuration.

### Panel Modes

A panel supports different modes:

- `panel` Panel, that shows up in navigation (Default)
- `subpanel` Subpanel, will not show up in navigation
- `popup` Popup, will not show up in navigation

By default a panel will be used as a navigation panel.

Each panel configured will by default be included in the navigateable panels list. To not include a panel in the navigation, set `mode` to `subpanel`. When navigating to an panel that is not navigateable then this panel will be added to a stack, so that it is always possible to return to the last item navigated.

Entry Details, Popups, Settings, About and other special pages will not appear in navigation.

### Accessing a panel

To be able to access a panel from within the configuration, the panel needs to have a `key` defined. By this key the panel can be accessed now for navigation by using `navigation.key` as an entity.

### Closing a panel automatically

To automatically close a panel after some amount of time, set `close_timeout` to a value bigger than 0.

### Using a Panel as a Home Panel

`home_panel` bool

If not defined the first configured panel will be used. If defined, then the defined home panel will be used.

**Only one panel can be a home panel**

### Using a Panel as a Sleep Panel

`sleep_panel` bool

After page_timeout the sleep panel will be activated.

**Only one panel can be a sleep panel**

### Using Panel as a Wakeup Panel

`wakeup_panel` bool

When the display changes into dimmed state and a sleep panel is set or changes into sleep state and wakes up, then if no wakeup panel is defined, it will return to the home panel. If defined, it will return to the defined panel.

If no sleep occured but page was changed, it will return to the last active panel.

**Only one panel can be a wakeup panel**

### Locking a Panel with a Code

`unlock_code` string

Panels can be locked with a code. If an unlock_code is set, the panel will be only accessible after entering the unlock code.