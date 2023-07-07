
# NSPanel HAUI (HomeAssistant UI)

`nspanel-haui` is a versatile display system for HomeAssistant based smart homes.

- [NSPanel HAUI (HomeAssistant UI)](#nspanel-haui-homeassistant-ui)
  - [About](#about)
  - [Features](#features)
  - [Resources](#resources)
  - [Installation](#installation)
  - [Development](#development)
    - [Roadmap](#roadmap)
  - [Additional Information](#additional-information)

## About

For details about the configuration see [Configuration](docs/Config.md). Also look at [Panels](docs/panels/README.md) to get an overview of available panels.

## Features

- **A variety of different panels**

  Select from different [Panels](docs/panels/README.md) that can be displayed on the panel.

- **Touch gestures and sequences**

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

  All panels can be locked by a pin code. The panel can be accessed after entering the pin code.

- **Device settings in HomeAssistant**

  The whole device configuration can be done in HomeAssistant.

- **Device display configuration in a single yaml file**

  The whole configuration is located in the `apps.yaml` file. The configuration is done per device.

- **Optimized custom ESPHome component**

  For the communication between the esp32 and the nextion display a custom component `nspanel_haui` is used. It provides basic functionality like `send_command`, `get_int_value`, `get_txt_value`, etc. and also generates events for button presses and other changes on the display.

## Resources

- [Documentation](docs/README.md)
- [Icons Cheatsheet](https://htmlpreview.github.io/?https://raw.githubusercontent.com/happydasch/nspanel_haui/master/docs/cheatsheet.html)
- [Thread in HomeAssistant Community](https://community.home-assistant.io/t/sonoff-nspanel-haui-homeassistant-ui/578570)

## Installation

In order to install NSPanel HAUI it is neccessary to flash the Panel with ESPHome.

The simplified process is as followed:

1. Flash Panel with [ESPHome](docs/ESPHome.md)
2. Update [Display TFT](docs/Nextion.md)
3. Install [AppDaemon App](docs/AppDaemon.md)
4. Add [Configuration](docs/Config.md)

Take also a look at the more detailed [Installation Guide](docs/Install.md). Have also a look at the [FAQ](docs/FAQ.md).

## Development

For details about how the parts of the whole system communicate together see [NSPanel HomeAssistant UI Docs](docs/README.md).

- [Design Guidelines](docs/Design.md)
- [Communication Description](docs/Communication.md)
- [ESPHome Component](docs/ESPHome.md)
- [AppDaemon Component](docs/AppDaemon.md)
- [Nextion Component](docs/Nextion.md)

### Roadmap

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
- [x] Add style and design for panels
- [ ] Implement design in hmi file
- [x] Add light panel
- [ ] Add cover panel
- [ ] Add media panel
- [ ] Add thermo panel
- [ ] Support for timebased value overrides
- [ ] Add updater

First release

- [ ] Add new panels
- [ ] Add a light theme?

## Additional Information

The project is based on the ideas of [NSPanel Lovelace UI](https://github.com/joBr99/nspanel-lovelace-ui) and [NSPanel Custom with HA Blueprint](https://github.com/Blackymas/NSPanel_HA_Blueprint).
