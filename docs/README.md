# NSPanel HomeAssistant UI Docs

[README](../README.md) | [Documentation](README.md) | [Installation](Install.md) | [Configuration](Config.md) | [Panels](panels/README.md) | [FAQ](FAQ.md)

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

The backend and global logic of the system is under the management of AppDaemon, which handles all the behind-the-scenes operations.

The display operations with minimal logic are assigned to Nextion, which works in collaboration with ESPHome to show informations on the panel.

- [Design Guidelines](Design.md)

  A description about designing styling panels.

- [Communication Overview](Communication.md)

  A description about the communication process of the components.

- [ESPHome Component](ESPHome.md)

  The ESP processes the serial communication and creates events which are being sent via MQTT.
  Only the ESP communicates directly with the display.

- [AppDaemon Component](AppDaemon.md)

  Most logic is implemented in the AppDaemon App. This app controls the Nextion display running on the ESP32. It updates the display based on the latest data from Home Assistant entities.

- [Nextion Component](Nextion.md)

  The display is responsible for showing the panels, preparing components on pages before they being shown (setting an initial state).

## Versioning

There are version informations for:

- AppDaemon App
- YAML-File for ESPHome
- TFT-Display File (Matches Release Version)

Every release should contain the tft files as assets. The version for the tft files should match the release version.
