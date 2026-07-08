---
title: Custom Integration Development
description: Guide for developing custom integrations with NSPanel HAUI
---

# Custom Integration
## Overview

NSPanel HAUI can run as a native Home Assistant custom integration. No external addon required. The config format is identical to the Hub setup - only the file location changes.

## Requirements

- Home Assistant 2026.4+
- ESPHome device flashed and connected (see [Installation Guide](Install.md) steps 1–2)

## Installation

For most users, the **recommended installation method** is via HACS, adding the integration through the Home Assistant UI's config flow workflow. This avoids manual YAML editing:

1. Install via HACS or copy the `custom_components/nspanel_haui/` folder into your HA config directory:
   ```
   <ha_config>/custom_components/nspanel_haui/
   ```
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration → NSPanel HAUI** to set up via the config flow.

## Configuration

**The primary configuration method is the HA UI panel editor.** After adding the integration, open the NSPanel device page to add, remove, and configure panels.

For advanced setups or bulk import, YAML configuration in `configuration.yaml` is still supported. The `config:` block defines panels and entities:

```yaml
nspanel_haui:
  - name: nspanel_haui          # must match ESPHome device name
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

The `name:` field is the device name and must match the ESPHome device name. Communication uses ESPHome native API event types (`send_commands`, `goto_page`, etc.).

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


