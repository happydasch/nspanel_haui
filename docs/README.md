# NSPanel HomeAssistant UI Docs

## End User

For details about installation and configuration see the following pages.

- [Installation](Install.md)
  A step-by-step guide for installation

- [Configuration](Config.md)
  Details about the App Configuration

- [Panels](panels/README.md)
  Overview of available panels

- [FAQ](panels/FAQ.md)
  Frequently asked questions

## Development

The device handling responsibility is assigned to ESPHome. The communication with the nextion display is done using a custom ESPHome component `nspanel_haui`.

The backend and global logic of the system is under the management of AppDaemon, which handles all the behind-the-scenes operations.
The display operations with minimal logic are assigned to Nextion, which works in collaboration with ESPHome to show informations on the panel.

- [Communication Overview](Communication.md)
  A description about the communication process of the components.

- [ESPHome Component](ESPHome.md)
-
  The ESP processes the serial communication and creates events which are being sent via MQTT.
  Only the ESP communicates directly with the display.

- [Nextion Component](Nextion.md)

  Most logic is implemented in the AppDaemon App. The display is responsible for showing the panels, doing time critical processing like animations, preparing components on pages before they being shown.

- [AppDaemon Component](AppDaemon.md)
-
  This app controls the Nextion display running on the ESP32. It updates the display based on the latest data from Home Assistant entities.
