# NSPanel HAUI (HomeAssistant UI)

[![GitHub release](https://img.shields.io/github/v/release/happydasch/nspanel_haui?style=for-the-badge)](https://github.com/happydasch/nspanel_haui/releases)
[![HA Community](https://img.shields.io/badge/HA%20Community-Thread-03a87c?style=for-the-badge)](https://community.home-assistant.io/t/sonoff-nspanel-haui-homeassistant-ui/578570)
[![License](https://img.shields.io/github/license/happydasch/nspanel_haui?style=for-the-badge)](https://github.com/happydasch/nspanel_haui/blob/dev/LICENSE)

<img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/readme/hero.png" alt="NSPanel HAUI on the Sonoff NSPanel, US and EU models" width="100%">

A flexible touchscreen UI for the Sonoff NSPanel, built on ESPHome. Everything is configured in a
visual editor inside Home Assistant, with no YAML to write.

**[Documentation](https://happydasch.github.io/nspanel_haui/)** ·
[Installation](https://happydasch.github.io/nspanel_haui/install.html) ·
[Panels](https://happydasch.github.io/nspanel_haui/panels/index.html) ·
[Screens](https://happydasch.github.io/nspanel_haui/screens.html) ·
[FAQ](https://happydasch.github.io/nspanel_haui/faq.html) ·
[Changelog](https://github.com/happydasch/nspanel_haui/blob/dev/CHANGELOG.md)

[![Open NSPanel HAUI in the Home Assistant Marketplace](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=happydasch&repository=nspanel_haui&category=integration)

## Panels

Choose from 13 panel types for entity controls and room displays, including clocks, weather, and QR
codes. Each entity panel has a matching popup; notification, selection, and PIN popups are also
included. Browse [all panel types](https://happydasch.github.io/nspanel_haui/panels/index.html) or
see rendered examples in the [Screens overview](https://happydasch.github.io/nspanel_haui/screens.html)
for both layouts.

## Features

- **Landscape and portrait**: the EU panel and the upright US panel each get their own display layout
- **Touch and gestures**: tap, slide, swipe through panels, named gesture sequences, long press to go back
- **Idle page and dimming**: clock, weather or word clock as idle page (also as a carousel), auto-dimming, display-off schedule, day/night profiles
- **Notifications**: a queue with severities, persistent alerts that keep sounding until dismissed, quiet hours
- **Panel PINs**: lock sensitive panels behind a code
- **Hardware buttons**: switch the built-in relays or any entity
- **Colours and icons**: theme colours, per-item colour and icon overrides, background pictures
- **Updates**: firmware and display updates as Home Assistant update entities, stable or dev channel
- **Local push**: ESPHome native API, no cloud; English, German, Dutch, Polish and French

## Editor

Open **NSPanel HAUI** in the Home Assistant sidebar (administrators only) to manage panels, items,
device settings, colours and devices. It is there as soon as the integration is added.

<img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/readme/editor.png" alt="Open the editor, select a device, edit panels, check the live preview" width="100%">

See [Configuration](https://happydasch.github.io/nspanel_haui/configuration/index.html) for the
live preview, the panel cards and the device manager.

## Quick start

Requires Home Assistant 2026.11 or later.

<img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/readme/quick-start.png" alt="Flash the firmware, connect it to ESPHome, install NSPanel HAUI, configure panels" width="100%">

1. **Flash**: load the prebuilt `nspanel_haui.bin` from the
   [latest release](https://github.com/happydasch/nspanel_haui/releases) and enter your Wi-Fi at
   first boot. ([Install guide](https://happydasch.github.io/nspanel_haui/install.html#flash-the-panel))
2. **Connect**: add the panel to Home Assistant's ESPHome integration. Use the key in the
   [install guide](https://happydasch.github.io/nspanel_haui/install.html#flash-the-panel) if prompted.
3. **Install**: add `happydasch/nspanel_haui` from **Settings → Marketplace → Add from link**,
   install NSPanel HAUI, then restart Home Assistant. HACS installs migrate automatically.
   ([Install guide](https://happydasch.github.io/nspanel_haui/install.html))
4. **Configure**: add **NSPanel HAUI** from **Settings → Devices & Services → Add Integration**, then
   open the editor and add panels.
   ([Integration](https://happydasch.github.io/nspanel_haui/custom_integration.html) ·
   [Configuration](https://happydasch.github.io/nspanel_haui/configuration/index.html))

For custom firmware builds, see the
[ESPHome development instructions](https://happydasch.github.io/nspanel_haui/esphome.html#installation).

> **Upgrading from 0.3.x or earlier?** Read the [upgrade guide](https://happydasch.github.io/nspanel_haui/update.html)
> first: services, ESPHome actions/events and two config entities were renamed. The panel store
> migrates the legacy sleep/display-off setting names and color scheme, but settings stored in config
> entries by 0.3.2 or earlier are not carried over. Saved panels do not migrate, so check each panel
> after upgrading; see [device configuration](https://happydasch.github.io/nspanel_haui/configuration/device.html#how-settings-are-saved).

## How it works

The hub runs inside Home Assistant: it reads entity states, renders the display commands and sends
them over the ESPHome native API. The ESP32 relays them to the Nextion display over serial and
reports touches and button presses back. See
[Communication](https://happydasch.github.io/nspanel_haui/communication.html).

## Documentation

The full documentation is at **[happydasch.github.io/nspanel_haui](https://happydasch.github.io/nspanel_haui/)**.

- **Start**: [Installation](https://happydasch.github.io/nspanel_haui/install.html) · [Quick start](https://happydasch.github.io/nspanel_haui/get-started.html) · [Updating](https://happydasch.github.io/nspanel_haui/update.html) · [FAQ](https://happydasch.github.io/nspanel_haui/faq.html) · [Troubleshooting](https://happydasch.github.io/nspanel_haui/troubleshooting.html)
- **Configure**: [Overview](https://happydasch.github.io/nspanel_haui/configuration/index.html) · [Device](https://happydasch.github.io/nspanel_haui/configuration/device.html) · [Display models](https://happydasch.github.io/nspanel_haui/configuration/display-models.html) · [Panels](https://happydasch.github.io/nspanel_haui/configuration/panels.html) · [Items](https://happydasch.github.io/nspanel_haui/configuration/items.html) · [Examples](https://happydasch.github.io/nspanel_haui/examples.html)
- **Use**: [Gestures and display states](https://happydasch.github.io/nspanel_haui/device.html) · [Services](https://happydasch.github.io/nspanel_haui/services.html) · [Icons](https://happydasch.github.io/nspanel_haui/cheatsheet.html) · [Screens](https://happydasch.github.io/nspanel_haui/screens.html)
- **Develop**: [Development](https://happydasch.github.io/nspanel_haui/development.html) · [Design](https://happydasch.github.io/nspanel_haui/design.html) · [Communication](https://happydasch.github.io/nspanel_haui/communication.html) · [ESPHome](https://happydasch.github.io/nspanel_haui/esphome.html) · [Hub](https://happydasch.github.io/nspanel_haui/hub.html) · [Nextion](https://happydasch.github.io/nspanel_haui/nextion.html)

## Credits

Inspired by [NSPanel Lovelace UI](https://github.com/joBr99/nspanel-lovelace-ui) by joBr99 and
[NSPanel HA Blueprint](https://github.com/Blackymas/NSPanel_HA_Blueprint) by Blackymas.

See the [GitHub contributors](https://github.com/happydasch/nspanel_haui/graphs/contributors)
for everyone who contributed.
Special thanks to @jameshiscott who contributed the [the live preview and the Nextion simulator](docs/configuration/README.md#the-live-preview).
