---
title: Device Configuration
description: Device-level configuration keys for NSPanel HAUI
---

# Device Configuration

[README](../../README.md) | [Documentation](../README.md) | [Installation](../Install.md) | [Configuration](../Config.md) | [Panels](../panels/README.md) | [FAQ](../FAQ.md)

[< Configuration](../Config.md)

- [Device Configuration](#device-configuration)
  - [Navigation Configuration](#navigation-configuration)
  - [Notification Configuration](#notification-configuration)
  - [Update Controller](#update-controller)
  - [Connection Controller](#connection-controller)
  - [Gesture Controller](#gesture-controller)

## Device Configuration

`device` dict

- `name` string

  The name of the panel device

- `locale` string

  The locale of the device

- `panels` list

  Per-device panel list.  Each panel is at minimum `{"type": "<type_key>"}`.
  Default `[{"type": "clock"}]`.

- `esphome_device_id` string

  The ESPHome device ID this config entry is linked to.  Set automatically
  during discovery.  Default empty.

- `enabled` bool

  Whether the device is active at runtime.  Disabled devices are skipped
  without deleting their config.  Default `True`.

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
  Default `True`.

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

- `reset_interaction_on_button` bool

  Whether hardware button presses reset the idle/interaction timer (and wake the
  display). When `False`, button presses only toggle the relay and do not count
  as user interaction. The device-side `use_button_interaction` switch is kept
  in sync with this value. Default `True`.

- `hub_idle_timeout` int

  Hub-side idle timeout in seconds (`0` = disabled). Fallback that triggers
  sleep after this many seconds of inactivity when the device doesn't publish
  `esphome.timeout` events (e.g. when auto-sleeping is off on the device).
  Default `0`.

- `auto_navigate_home_timeout` int

  Auto-navigate-home timeout in seconds (`0` = disabled). When `>0`, after
  this many seconds of inactivity on any non-home panel the hub navigates back
  to the home panel automatically. Should be set shorter than any sleep/dim
  timeout to take effect before the display sleeps. Default `0`.

- `color_overrides` dict

  RGB565 color values overriding the built-in `COLORS` defaults, keyed by
  color name. Unknown keys are ignored (logged) and values are clamped to
  `0`–`65535`. Default `{}` (empty).

- `sound_on_startup` bool

  Should a sound be played when the display is connected after startup. Default True.

- `sound_on_notification` bool

  Should a sound be played when the display receives a non-persistent notification. Default True.

- `snapshot_max_age_seconds` int

  Maximum age in seconds of a navigation snapshot before it's considered stale
  and the display falls back to the home panel instead.
  - `-1` (default): No limit - always restore the snapshot.
  - `0`: Never restore the snapshot - always go to the home panel.
  - `>0`: Only restore if the snapshot is newer than this many seconds.

- `debug_level` int

  Debug verbosity level (0-3). Higher values produce more log output. Default `0`.

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
  reset_interaction_on_button: true
  snapshot_max_age_seconds: -1
  hub_idle_timeout: 0
  auto_navigate_home_timeout: 0
  use_relay_left: true
  use_relay_right: true
  sound_on_startup: true
  sound_on_notification: true
  color_overrides: {}
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