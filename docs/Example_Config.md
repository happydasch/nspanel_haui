---
title: Example Configurations
description: Sample YAML configurations for NSPanel HAUI panels
---

# Example Configurations

[README](../README.md) | [Documentation](README.md) | [Installation](Install.md) | [Configuration](Config.md) | [Panels](panels/README.md) | [FAQ](FAQ.md)

- [Example Configurations](#example-configurations)
  - [Simple config](#simple-config)
  - [Single page](#single-page)
  - [Multiple navigation pages](#multiple-navigation-pages)
  - [Multiple pages with subpages](#multiple-pages-with-subpages)

## Simple config

Import via the HA UI: **NSPanel HAUI → YAML Import** (enter your device name).

```yaml
# device settings
config:
  locale: en_US

# panels
panels:
  # clock panel
  - type: clock
    sleep_panel: true
    home_panel: true
    entity: weather.home
```

## Single page

```yaml
config:
  locale: en_US

panels:
  - type: grid
    title: Single Page
    home_panel: true
    entity: light.example_item
```

## Multiple navigation pages

```yaml
config:
  locale: en_US

panels:
  # weather panel
  - type: weather
    mode: subpanel  # it will not show up in navigation
    entity: weather.home
    sleep_panel: true
    key: weather

  # home panel
  - type: grid
    title: Multi Nav Pages
    home_panel: true
    entities:
      - entity: light.example_item
      - entity: switch.example_item

  # qr code
  - type: qr
    title: QR Code
    qr_code: WIFI:S:wifi_ssid;T:WPA;P:wifi_pw;;
    entities:
      - entity: "text:wifi_ssid"
        name: Wifi SSID
        icon: mdi:wifi
      - entity: "text:wifi_pw"
        name: Wifi Key
        icon: mdi:key
```

## Multiple pages with subpages

```yaml
config:
  locale: en_US

panels:
  # weather panel
  - type: weather
    mode: subpanel  # it will not show up in navigation
    entity: weather.home
    sleep_panel: true
    key: weather

  # home panel
  - type: grid
    title: Example
    home_panel: true

    entities:
      - entity: navigate:panel_key
      - entity: light.example_item
      - entity: switch.example_item

  # subpanel
  - type: grid
    title: Subpanel Open
    mode: subpanel
    key: panel_key
    entities:
      - entity: light.example_item
      - entity: switch.example_item
      - entity: null
      - entity: button.example_item
      - entity: cover.example_item

  # qr code
  - type: qr
    title: Small QR Code
    qr_code: WIFI:S:wifi_ssid;T:WPA;P:wifi_pw;;
    entities:
      - entity: "text:wifi_ssid"
        name: Wifi SSID
        icon: mdi:wifi
      - entity: "text:wifi_pw"
        name: Wifi Key
        icon: mdi:key
```
