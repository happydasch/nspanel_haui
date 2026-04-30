# Custom Integration (No AppDaemon)

[README](../README.md) | [Documentation](README.md) | [Installation](Install.md) | [Configuration](Config.md) | [Panels](panels/README.md) | [FAQ](FAQ.md)

- [Custom Integration (No AppDaemon)](#custom-integration-no-appdaemon)
  - [Overview](#overview)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Multiple Devices](#multiple-devices)
  - [Migration from AppDaemon](#migration-from-appdaemon)

## Overview

NSPanel HAUI can run as a native Home Assistant custom integration. No AppDaemon addon required. The config format is identical to the AppDaemon setup — only the file location changes.

## Requirements

- Home Assistant 2023.1+
- MQTT integration enabled in HA
- ESPHome device flashed and connected (see [Installation Guide](Install.md) steps 1–2)

## Installation

1. Copy the `custom_components/nspanel_haui/` folder into your HA config directory:

   ```
   <ha_config>/custom_components/nspanel_haui/
   ```

   HACS or manual copy both work.

2. Restart Home Assistant.

## Configuration

Add to `configuration.yaml`. The `config:` block is identical to the existing `apps.yaml` config — copy it as-is:

```yaml
nspanel_haui:
  - name: nspanel_haui          # must match ESPHome device name (used for MQTT topics)
    config:

      device:
        name: nspanel_haui      # ESPHome device name (used for service calls)
        locale: en_US

      connection:
        heartbeat_interval: null
        overdue_factor: 2.0

      navigation:
        page_timeout: 2.0

      update:
        auto_install: true
        auto_update: false
        tft_filename: nspanel_haui.tft

      sys_panels:
        - type: blank
          mode: subpanel
          key: sys_blank
        - type: system
          mode: subpanel
          key: sys_system
        - type: system_settings
          mode: popup
          key: sys_settings
        - type: system_about
          mode: popup
          key: sys_about
        - type: popup_unlock
          mode: popup
          key: popup_unlock
        - type: popup_notify
          mode: popup
          key: popup_notify
        - type: popup_select
          mode: popup
          key: popup_select
        - type: popup_timer
          mode: popup
          key: popup_timer
        - type: popup_light
          mode: popup
          key: popup_light
        - type: popup_media_player
          mode: popup
          key: popup_media_player
        - type: popup_vacuum
          mode: popup
          key: popup_vacuum
        - type: popup_climate
          mode: popup
          key: popup_climate
        - type: popup_cover
          mode: popup
          key: popup_cover

      panels:
        - type: clock
          mode: subpanel
          entity: weather.home
          key: clock
        - type: grid
          title: Home
          home_panel: true
          entities:
            - entity: light.living_room
            - entity: switch.fan
```

The `name:` field at the top level sets the MQTT topic prefix (`nspanel_haui/{name}/cmd` and `/recv`). It must match the `topic_prefix` configured in the ESPHome device YAML.

For full config options see [Configuration Details](Config.md) and [Config Examples](Example_Config.md).

## Multiple Devices

Add one list entry per device:

```yaml
nspanel_haui:
  - name: living_room
    config:
      device:
        name: living_room
      panels:
        - type: clock
          ...

  - name: bedroom
    config:
      device:
        name: bedroom
      panels:
        - type: clock
          ...
```

## Migration from AppDaemon

1. Copy `custom_components/nspanel_haui/` to `<ha_config>/custom_components/`.
2. In `configuration.yaml`, add the `nspanel_haui:` block and copy the `config:` section from your existing `appdaemon/apps.yaml`.
3. Add `name:` at the top of each entry — use the same value as the AppDaemon instance key (the YAML key above `module:` in apps.yaml).
4. Restart HA. AppDaemon app can be disabled or removed.

**Before (apps.yaml):**
```yaml
nspanel_haui:            # ← this becomes name:
  module: nspanel_haui
  class: NSPanelHAUI
  config:
    device:
      name: nspanel_haui
    panels:
      - type: clock
        ...
```

**After (configuration.yaml):**
```yaml
nspanel_haui:
  - name: nspanel_haui   # ← was the apps.yaml key
    config:
      device:
        name: nspanel_haui
      panels:
        - type: clock
          ...
```
