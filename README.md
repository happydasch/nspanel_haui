# NSPanel HAUI (HomeAssistant UI)

[![Marketplace](https://img.shields.io/badge/Marketplace-Custom-41BDF5.svg?style=for-the-badge)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=happydasch&repository=nspanel_haui&category=integration)
[![GitHub release](https://img.shields.io/github/v/release/happydasch/nspanel_haui?style=for-the-badge)](https://github.com/happydasch/nspanel_haui/releases)
[![HA Community](https://img.shields.io/badge/HA%20Community-Thread-03a87c?style=for-the-badge)](https://community.home-assistant.io/t/sonoff-nspanel-haui-homeassistant-ui/578570)
[![License](https://img.shields.io/github/license/happydasch/nspanel_haui?style=for-the-badge)](LICENSE)

<p align="center">
  <img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/hero-banner.svg" alt="NSPanel HAUI" width="100%">
</p>

A flexible touchscreen UI for the Sonoff NSPanel, built on ESPHome. Everything is configured in a
visual editor inside Home Assistant, with no YAML to write.

**[Documentation](docs/README.md)** · [Installation](docs/install.md) · [Panels](docs/panels/README.md) ·
[Screens](https://happydasch.github.io/nspanel_haui/screens.html) · [FAQ](docs/faq.md) ·
[Changelog](CHANGELOG.md)

<a href="https://my.home-assistant.io/redirect/marketplace_repository/?owner=happydasch&repository=nspanel_haui&category=integration">
  <img src="https://my.home-assistant.io/badges/marketplace_repository.svg" alt="Open your Home Assistant instance and open NSPanel HAUI in the Marketplace.">
</a>


## Panels

13 panel types, a popup for every entity panel (lights, covers, climate, media, vacuum, alarm,
timers) plus notification, selection and PIN popups. Every screenshot is rendered by the
integration itself; the [Screens overview](https://happydasch.github.io/nspanel_haui/screens.html)
shows every panel, popup and system screen in both layouts.

<table>
<tr>
<td align="center" width="20%"><a href="docs/panels/panel_grid.md"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/grid.png" alt="Grid panel" width="130"></a><br><a href="docs/panels/panel_grid.md">Grid</a></td>
<td align="center" width="20%"><a href="docs/panels/panel_row.md"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/row.png" alt="Row panel" width="130"></a><br><a href="docs/panels/panel_row.md">Row</a></td>
<td align="center" width="20%"><a href="docs/panels/panel_light.md"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/light.png" alt="Light panel" width="130"></a><br><a href="docs/panels/panel_light.md">Light</a></td>
<td align="center" width="20%"><a href="docs/panels/panel_climate.md"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/climate.png" alt="Climate panel" width="130"></a><br><a href="docs/panels/panel_climate.md">Climate</a></td>
<td align="center" width="20%"><a href="docs/panels/panel_cover.md"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/cover.png" alt="Cover panel" width="130"></a><br><a href="docs/panels/panel_cover.md">Cover</a></td>
</tr>
<tr>
<td align="center"><a href="docs/panels/panel_media.md"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/media.png" alt="Media panel" width="130"></a><br><a href="docs/panels/panel_media.md">Media</a></td>
<td align="center"><a href="docs/panels/panel_vacuum.md"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/vacuum.png" alt="Vacuum panel" width="130"></a><br><a href="docs/panels/panel_vacuum.md">Vacuum</a></td>
<td align="center"><a href="docs/panels/panel_alarm.md"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/alarm.png" alt="Alarm panel" width="130"></a><br><a href="docs/panels/panel_alarm.md">Alarm</a></td>
<td align="center"><a href="docs/panels/panel_timer.md"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/timer.png" alt="Timer panel" width="130"></a><br><a href="docs/panels/panel_timer.md">Timer</a></td>
<td align="center"><a href="docs/panels/panel_qr.md"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/qr.png" alt="QR Code panel" width="130"></a><br><a href="docs/panels/panel_qr.md">QR Code</a></td>
</tr>
<tr>
<td align="center"><a href="docs/panels/panel_weather.md"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/weather.png" alt="Weather panel" width="130"></a><br><a href="docs/panels/panel_weather.md">Weather</a></td>
<td align="center"><a href="docs/panels/panel_clock.md"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/clock.png" alt="Clock panel" width="130"></a><br><a href="docs/panels/panel_clock.md">Clock</a></td>
<td align="center"><a href="docs/panels/panel_clocktwo.md"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/clocktwo.png" alt="ClockTwo word clock panel" width="130"></a><br><a href="docs/panels/panel_clocktwo.md">ClockTwo</a></td>
<td align="center"><a href="docs/panels/README.md#popups"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/popup_notify.png" alt="Notification popup" width="130"></a><br><a href="docs/panels/README.md#popups">Popups</a></td>
<td align="center"><a href="docs/configuration/display-models.md"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/portrait/grid.png" alt="Grid panel in portrait" height="92"></a><br><a href="docs/configuration/display-models.md">US portrait</a></td>
</tr>
</table>

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

<p align="center">
  <img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/frontend-preview.svg" alt="NSPanel HAUI editor" width="75%">
</p>

- **Live preview**: a virtual copy of each device running the real hub code. Tap, drag and swipe
  with the mouse; **sandbox mode** leaves your home untouched, **live mode** controls real entities.
- **Exact panel cards**: every card, popups and system panels included, is drawn by the hub, so
  it shows what the display shows, unsaved edits included.
- **Device manager**: find panels on the network, add, enable or remove them, and see connection,
  firmware and display versions.

The live preview and the Nextion simulator were created by
[@jameshiscott](https://github.com/jameshiscott). See [The Live Preview](docs/configuration/README.md#the-live-preview).

## Quick start

Requires Home Assistant 2026.11 or later.

1. **Install**: Settings → Marketplace → Add from link, add `happydasch/nspanel_haui`, install it
   and restart Home Assistant. HACS installs are migrated automatically. ([Install guide](docs/install.md))
2. **Flash**: flash the prebuilt `nspanel_haui.bin` from the
   [latest release](https://github.com/happydasch/nspanel_haui/releases) and enter your Wi-Fi at
   first boot, or build your own from `esphome/install.yaml`. ([Flashing](docs/install.md#2-step-install-esphome))
3. **Add**: Settings → Devices & Services → Add NSPanel HAUI; the device is discovered
   automatically. ([Integration](docs/custom_integration.md))
4. **Configure**: open the editor and add panels. ([Configuration](docs/configuration/README.md))

> **Upgrading from 0.3.x or earlier?** Read the [upgrade guide](docs/upgrading.md) first: services,
> ESPHome actions/events and two config entities were renamed. Device settings migrate
> automatically, saved panels do not, so check each panel after upgrading.

## How it works

The hub runs inside Home Assistant: it reads entity states, renders the display commands and sends
them over the ESPHome native API. The ESP32 relays them to the Nextion display over serial and
reports touches and button presses back. See [Communication](docs/communication.md).

## Documentation

- **Start**: [Installation](docs/install.md) · [Quick start](docs/get-started.md) · [Upgrading](docs/upgrading.md) · [FAQ](docs/faq.md) · [Troubleshooting](docs/troubleshooting.md)
- **Configure**: [Overview](docs/configuration/README.md) · [Device](docs/configuration/device.md) · [Display models](docs/configuration/display-models.md) · [Panels](docs/configuration/panels.md) · [Items](docs/configuration/items.md) · [Examples](docs/examples.md)
- **Use**: [Gestures and display states](docs/device.md) · [Services](docs/services.md) · [Icons](https://happydasch.github.io/nspanel_haui/cheatsheet.html) · [Screens](https://happydasch.github.io/nspanel_haui/screens.html)
- **Develop**: [Development](docs/development.md) · [Design](docs/design.md) · [Communication](docs/communication.md) · [ESPHome](docs/esphome.md) · [Hub](docs/hub.md) · [Nextion](docs/nextion.md)

The full index is [docs/README.md](docs/README.md).

## Credits

Inspired by [NSPanel Lovelace UI](https://github.com/joBr99/nspanel-lovelace-ui) by joBr99 and
[NSPanel HA Blueprint](https://github.com/Blackymas/NSPanel_HA_Blueprint) by Blackymas.
