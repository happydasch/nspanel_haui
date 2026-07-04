---
title: Custom Integration Development
description: Guide for developing custom integrations with NSPanel HAUI
---

# Custom Integration

[README](../README.md) | [Documentation](README.md) | [Installation](Install.md) | [Configuration](Config.md) | [Panels](panels/README.md) | [FAQ](FAQ.md)

- [Custom Integration](#custom-integration)
  - [Overview](#overview)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Multiple Devices](#multiple-devices)

## Overview

NSPanel HAUI can run as a native Home Assistant custom integration. No external addon required. The config format is identical to the Hub setup - only the file location changes.

## Requirements

- Home Assistant 2026.4+
- ESPHome device flashed and connected (see [Installation Guide](Install.md) steps 1–2)

## Installation

1. Copy the `custom_components/nspanel_haui/` folder into your HA config directory:

   ```
   <ha_config>/custom_components/nspanel_haui/
   ```

   HACS or manual copy both work.

2. Restart Home Assistant.

## Configuration

Add to `configuration.yaml`. The `config:` block contains panels and entities:

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


