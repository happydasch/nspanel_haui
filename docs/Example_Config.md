# Example Configurations

[README](../README.md) | [Documentation](README.md) | [Installation](Install.md) | [Configuration](Config.md) | [Panels](panels/README.md) | [FAQ](FAQ.md)

- [Example Configurations](#example-configurations)
  - [Simple config](#simple-config)
  - [Single page](#single-page)
  - [Multiple navigation pages](#multiple-navigation-pages)
  - [Multiple pages with subpages](#multiple-pages-with-subpages)

## Simple config

```yaml
nspanel-haui:
  module: haui
  class: NSPanelHAUI

  # panel config
  config:

    # device config
    device:
      device_name: nspanel_haui
      locale: en_US
      log_commands: false

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
nspanel-haui:
  module: haui
  class: NSPanelHAUI

  # panel config
  config:

    # device config
    device:
      device_name: nspanel_haui
      locale: en_US
      log_commands: false

    # panels
    panels:

      - type: grid
        title: Single Page
        home_panel: true
        entity: light.example_item
```

## Multiple navigation pages

```yaml
nspanel-haui:
  module: haui
  class: NSPanelHAUI

  # panel config
  config:

    # device config
    device:
      device_name: nspanel_haui
      locale: en_US
      log_commands: false

    # panels
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
nspanel-haui:
  module: haui
  class: NSPanelHAUI

  # panel config
  config:

    # device config
    device:
      device_name: nspanel_haui
      locale: en_US
      log_commands: false

    # panels
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
