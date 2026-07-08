---
title: NSPanel HAUI Documentation
description: HomeAssistant UI for the Sonoff NSPanel — documentation index
---

# NSPanel HomeAssistant UI Docs

## End User

For details about installation and configuration see the following pages.

- [Installation](Install.md)
  A step-by-step guide for installation

- [Configuration](Config.md)
  Details about the App Configuration

- [Device Description](Device.md)
  A description of the device itself, how it is inteded to work and what is supported.

- [Available Panels](panels/README.md)
  Overview of available panels

- [FAQ](FAQ.md)
  Frequently asked questions

## Development

The device handling responsibility is assigned to ESPHome. The communication with the nextion display is done using the ESPHome component `nextion`.

The backend and global logic of the system is under the management of the Hub, which handles all the behind-the-scenes operations.

The display operations with minimal logic are assigned to Nextion, which works in collaboration with ESPHome to show informations on the panel.

- [Design Guidelines](Design.md)

  A description about designing styling panels.

- [Communication Overview](Communication.md)

  A description about the communication process of the components.

- [ESPHome Component](ESPHome.md)

  The ESP processes the serial communication and creates events which are sent via ESPHome native API.
  Only the ESP communicates directly with the display.

- [Hub Component](Hub.md)

  Most logic is implemented in the Hub App. This app controls the Nextion display running on the ESP32. It updates the display based on the latest data from Home Assistant entities.

- [Nextion Component](Nextion.md)

  The display is responsible for showing the panels, preparing components on pages before they being shown (setting an initial state).

## Versioning

Version information is maintained for:

- **Hub App** — tracked in `custom_components/nspanel_haui/haui/version.py` and synced to `manifest.json` and `pyproject.toml`
- **ESPHome YAML** — the ESPHome device config tracks its own compatibility version
- **TFT Display File** — matches the Hub App release version

Every release should include the compiled TFT file as a release asset.
