
# NSPanel HAUI (HomeAssistant UI)

`nspanel-haui` is a robust display system for HomeAssistant based smart homes.

For details about the configuration see [Configuration](docs/Config.md), also look at [Panels](docs/panels/README.md) to get an overview of available panels.

- [NSPanel HAUI (HomeAssistant UI)](#nspanel-haui-homeassistant-ui)
  - [Features](#features)
  - [Installation](#installation)
  - [Development](#development)
  - [Roadmap](#roadmap)
  - [Additional](#additional)

## Features

- **Touch Gestures and sequences**

  Different touch gestures as swipe left or right are supported. There is also support for gesture sequences.

- **Live state updates**

  The display will update when a entity state changes. All entities being displayed will notify about changes and the display will update.

- **Button and relay states, coupled and uncoupled relays**

  The buttons can be used in a couped state, so that by button presses, the relay will get activated. It is also possible to disable the relay and use the physical buttons as software buttonms.

- **Dimming of the display after a timeout**

  The display will automatically dim its brightness after a timeout.

- **Sleep display change after a timeout**

  The display can switch to a page after a timeout. There are sleep and wakeup panels possible.

- **Locking/Unlocking mechanism for panels**

  All panels can be locked by a pin. The panel can be accessed after entering the pin code.

- **Device settings in HomeAssistant**

  The whole device configuration can be done in HomeAssistant.

- **Device display configuration in a single yaml file**

  The whole configuration is located in the `apps.yaml` file. The configuration is done per device.

- **Optimized custom ESPHome component**

  For the communication between the esp32 and the nextion display a custom component `nspanel_haui` is used. It provides basic functionality like `send_command`, `get_int_value`, `get_txt_value`, etc. and also generates events for button presses and other changes on the display.

## Installation

In order to install NSPanel HAUI it is neccessary to flash the Panel with ESPHome.

The simplified process is as follows:

1. Flash Panel with [ESPHome](docs/ESPHome.md)
2. Update [Display TFT](docs/Nextion.md)
3. Install [AppDaemon App](docs/AppDaemon.md)
4. Add [Configuration](docs/Config.md)

Take also a look at the more detailed [Installation Guide](docs/Install.md). Have also a look at the [FAQ](docs/FAQ.md).

## Development

For details about how the parts of the whole system communicate together see [docs](docs/README.md)

- [Communication Description](docs/Communication.md)

  - Overview of the communication process

- [AppDaemon Component](docs/AppDaemon.md)

  - Server Application running on AppDaemon

- [ESPHome Component](docs/ESPHome.md)

  - Device and Sensors Implementation
  - Provides Scripts and Services for Communication with display
  - Responsible for handling the device functionality

- [Nextion Component](docs/Nextion.md)

  - Responsible for display, as little logic as possible

## Roadmap

Basic functionality

- [x] Basic app structure to be able to interact with display
- [x] Load panels and entities from config
- [x] Trigger entities (internal/external)
- [x] Add translation functionality
- [x] Add default panels (list,grid, ...)
- [x] Add detail panels and popups
- [x] Add basic interaction functionality between panels
- [x] Add missing panel functionality (all panels should work)

Improvements / Additional

- [x] Create new font using Roboto font
- [ ] Improve / Change design
- [ ] Support for timebased value overrides
- [ ] Add updater
- [ ] Add new panels
- [ ] Add a light theme

## Additional

The project is based on the ideas of [NSPanel Lovelace UI](https://github.com/joBr99/nspanel-lovelace-ui) and [NSPanel Custom with HA Blueprint](https://github.com/Blackymas/NSPanel_HA_Blueprint). Many frontend parts are based on `NSPanel Lovelace UI` as the configuration, functionality and design. The backend part is a completely different implementation.
