# NSPanel HAUI (HomeAssistant UI)

[![GitHub release](https://img.shields.io/github/v/release/happydasch/nspanel_haui?style=for-the-badge)](https://github.com/happydasch/nspanel_haui/releases)
[![HA Community](https://img.shields.io/badge/HA%20Community-Thread-03a87c?style=for-the-badge)](https://community.home-assistant.io/t/sonoff-nspanel-haui-homeassistant-ui/578570)
[![License](https://img.shields.io/github/license/happydasch/nspanel_haui?style=for-the-badge)](https://github.com/happydasch/nspanel_haui/blob/dev/LICENSE)

<img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/readme/hero.png" alt="NSPanel HAUI on the Sonoff NSPanel, US and EU models" width="100%">

A flexible touchscreen UI for the Sonoff NSPanel, built on ESPHome. Everything is configured in a
visual editor inside Home Assistant, with no YAML to write.

Requires Home Assistant 2026.11 or later.

**[Documentation](https://happydasch.github.io/nspanel_haui/dev/)** ·
[Installation](https://happydasch.github.io/nspanel_haui/dev/user/install.html) ·
[Panels](https://happydasch.github.io/nspanel_haui/dev/user/panels/index.html) ·
[Screens](https://happydasch.github.io/nspanel_haui/dev/screens.html) ·
[FAQ](https://happydasch.github.io/nspanel_haui/dev/user/faq.html) ·
[Changelog](https://github.com/happydasch/nspanel_haui/blob/dev/CHANGELOG.md)

[![Open NSPanel HAUI in the Home Assistant Marketplace](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=happydasch&repository=nspanel_haui&category=integration)

## Features

**On the panel**

- **Landscape and portrait**: one layout for the EU panel, one for the upright US panel
- **Multiple panel types**: clocks, weather, grid, row, light, media, climate, cover, vacuum,
  timer, alarm and QR code, plus built-in popups
- **Touch and gestures**: tap, slide and swipe, configurable gesture sequences, long press to go back
- **Idle page and dimming**: clock, weather or word clock as idle page, auto-dimming and a schedule
  for brightness, sound and display-off
- **Notifications and PINs**: a queue with severities, persistent alerts, silent times and protected
  panels
- **Hardware buttons**: switch the built-in relays or toggle any entity
- **Themes and pictures**: theme colours, per-item colour and icon overrides, background pictures
- **Updates**: firmware and display updates as Home Assistant update entities, stable or dev channel
- **Local and multilingual**: ESPHome native API, no cloud; English, German, Dutch, Polish, French
  and Slovak

**In the editor**

- **Compose panels visually**: choose from the panel catalog, add Home Assistant entities, text items
  or actions, then customise titles, icons and colours
- **Arrange the display**: drag panels between navigation, hidden and popup groups, and reorder them
  for each device
- **Preview as you work**: inspect panel thumbnails and the interactive virtual display, or switch to
  the live view of a connected panel
- **Tune each device**: set themes, language and regional formats, gestures, schedules, idle
  behaviour, dimming, hardware buttons and notifications
- **Manage a fleet**: see device connection and firmware details, recent events and available updates;
  back up or restore a device from its workspace

## Quick start

<img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/readme/quick-start.png" alt="Flash the firmware, connect it to ESPHome, install NSPanel HAUI, configure panels" width="100%">

1. **Flash the panel**: download `nspanel_haui.bin` from the
   [latest release](https://github.com/happydasch/nspanel_haui/releases), flash it and connect to Wi-Fi.
   ([Install guide](https://happydasch.github.io/nspanel_haui/dev/user/install.html#flash-the-panel))
2. **Add it to ESPHome**: use Home Assistant's ESPHome integration. Enter the API key if asked.
3. **Install NSPanel HAUI**: in **Settings → Marketplace**, choose **Add from link** and enter
   `happydasch/nspanel_haui`, then restart Home Assistant. Existing HACS installs migrate automatically.
4. **Set it up**: add **NSPanel HAUI** from **Settings → Devices & Services → Add Integration**, then
   open the sidebar editor to add panels.
   ([Configuration guide](https://happydasch.github.io/nspanel_haui/dev/user/configuration/index.html))

<img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/readme/editor.png" alt="Editor workflow: open the Home Assistant editor, select a device, edit panels and use the live preview" width="100%">

Open **NSPanel HAUI** in the Home Assistant sidebar (administrators only) to build and manage your
interface—no YAML required. Panel design, preview and device management are all in one editor.

## Editor

<table>
  <tr>
    <td align="center" valign="top" width="50%">
      <img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/readme/editor-fleet.png" alt="NSPanel HAUI fleet dashboard with device cards, connection summary, inventory and recent events" width="100%"><br>
      <b>Fleet overview</b><br>
      <sub>See device status, firmware, updates and recent events across the fleet.</sub>
    </td>
    <td align="center" valign="top" width="50%">
      <img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/readme/editor-device-preview.png" alt="Living Room device workspace showing the simulated panel preview beside connection, update, diagnostics and backup details" width="100%"><br>
      <b>Device overview and preview</b><br>
      <sub>Preview the selected device's panel alongside connection health, updates, diagnostics and backup actions.</sub>
    </td>
  </tr>
  <tr>
    <td align="center" valign="top" width="50%">
      <img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/readme/editor-panels.png" alt="Editor workspace showing navigation, hidden and popup panel groups, plus device settings" width="100%"><br>
      <b>Organise panels per device</b><br>
      <sub>Reorder panels and manage navigation, hidden panels and popups alongside device settings.</sub>
    </td>
    <td align="center" valign="top" width="50%">
      <img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/readme/editor-edit-panel.png" alt="Grid panel editor with a panel preview, title and editable item list" width="100%"><br>
      <b>Edit a panel and its items</b><br>
      <sub>Preview the layout while setting a panel title and configuring its items.</sub>
    </td>
  </tr>
  <tr>
    <td align="center" valign="top" width="50%">
      <img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/readme/editor-settings.png" alt="Device settings editor with language, theme, display, navigation, buttons and notification sections" width="100%"><br>
      <b>Configure device behaviour</b><br>
      <sub>Adjust language, theme, display, navigation, buttons, notifications and idle behaviour in one place.</sub>
    </td>
    <td align="center" valign="top" width="50%">
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/configuration/index.html"><b>Explore the editor guide →</b></a><br>
      <sub>See the full configuration walkthrough, including preview and device management.</sub>
    </td>
  </tr>
</table>

## Panels

A panel is one screen on the display. Add as many as you like and swipe between them. There are
13 panel types and a set of built-in popups. Select one to see what it shows and how to set it up.

<table>
  <tr>
    <td align="center" valign="top" width="25%">
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_clock.html"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/clock.png" alt="Clock on the display" width="180"></a><br>
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_clock.html"><b>Clock</b></a><br>
      <sub>Time, date and weather, with quick buttons</sub>
    </td>
    <td align="center" valign="top" width="25%">
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_clocktwo.html"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/clocktwo.png" alt="ClockTwo on the display" width="180"></a><br>
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_clocktwo.html"><b>ClockTwo</b></a><br>
      <sub>The time in words</sub>
    </td>
    <td align="center" valign="top" width="25%">
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_weather.html"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/weather.png" alt="Weather on the display" width="180"></a><br>
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_weather.html"><b>Weather</b></a><br>
      <sub>Current weather and forecast</sub>
    </td>
    <td align="center" valign="top" width="25%">
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_grid.html"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/grid.png" alt="Grid on the display" width="180"></a><br>
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_grid.html"><b>Grid</b></a><br>
      <sub>Six entities as tiles</sub>
    </td>
  </tr>
  <tr>
    <td align="center" valign="top" width="25%">
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_row.html"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/row.png" alt="Row on the display" width="180"></a><br>
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_row.html"><b>Row</b></a><br>
      <sub>Five entities as rows with toggles and sliders</sub>
    </td>
    <td align="center" valign="top" width="25%">
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_light.html"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/light.png" alt="Light on the display" width="180"></a><br>
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_light.html"><b>Light</b></a><br>
      <sub>Brightness, color temperature, color, effects</sub>
    </td>
    <td align="center" valign="top" width="25%">
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_media.html"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/media.png" alt="Media on the display" width="180"></a><br>
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_media.html"><b>Media</b></a><br>
      <sub>Playback, volume, sources, speaker groups</sub>
    </td>
    <td align="center" valign="top" width="25%">
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_climate.html"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/climate.png" alt="Climate on the display" width="180"></a><br>
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_climate.html"><b>Climate</b></a><br>
      <sub>Target temperature, modes, fan, presets</sub>
    </td>
  </tr>
  <tr>
    <td align="center" valign="top" width="25%">
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_cover.html"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/cover.png" alt="Cover on the display" width="180"></a><br>
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_cover.html"><b>Cover</b></a><br>
      <sub>Open, stop, close and position</sub>
    </td>
    <td align="center" valign="top" width="25%">
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_vacuum.html"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/vacuum.png" alt="Vacuum on the display" width="180"></a><br>
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_vacuum.html"><b>Vacuum</b></a><br>
      <sub>Start, dock, fan speed, locate</sub>
    </td>
    <td align="center" valign="top" width="25%">
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_timer.html"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/timer.png" alt="Timer on the display" width="180"></a><br>
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_timer.html"><b>Timer</b></a><br>
      <sub>Countdown timer and stopwatch</sub>
    </td>
    <td align="center" valign="top" width="25%">
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_alarm.html"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/alarm.png" alt="Alarm on the display" width="180"></a><br>
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_alarm.html"><b>Alarm</b></a><br>
      <sub>Keypad to arm and disarm</sub>
    </td>
  </tr>
  <tr>
    <td align="center" valign="top" width="25%">
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_qr.html"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/qr.png" alt="QR Code on the display" width="180"></a><br>
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/panel_qr.html"><b>QR Code</b></a><br>
      <sub>Guest Wi-Fi as a QR code</sub>
    </td>
    <td align="center" valign="top" width="25%">
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/popup_notify.html"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/popup_notify.png" alt="Notification on the display" width="180"></a><br>
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/popup_notify.html"><b>Notification</b></a><br>
      <sub>Popup for messages from Home Assistant</sub>
    </td>
    <td align="center" valign="top" width="25%">
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/popup_select.html"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/popup_select.png" alt="Select on the display" width="180"></a><br>
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/popup_select.html"><b>Select</b></a><br>
      <sub>Popup to choose from a list</sub>
    </td>
    <td align="center" valign="top" width="25%">
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/popup_unlock.html"><img src="https://raw.githubusercontent.com/happydasch/nspanel_haui/dev/docs/assets/screens/landscape/popup_unlock.png" alt="Unlock on the display" width="180"></a><br>
      <a href="https://happydasch.github.io/nspanel_haui/dev/user/panels/popup_unlock.html"><b>Unlock</b></a><br>
      <sub>PIN popup for protected panels</sub>
    </td>
  </tr>
</table>

- **Tap to control**: tap a light, media player, climate, cover, vacuum or alarm entity on a grid or
  row, and its full controls open as a popup.
- **Both layouts**: every panel exists for the landscape and the portrait display.
- **Protect a panel**: give any panel a PIN.

Browse [all panel types](https://happydasch.github.io/nspanel_haui/dev/user/panels/index.html), see
[every screen in both layouts](https://happydasch.github.io/nspanel_haui/dev/screens.html), or copy an
[example layout](https://happydasch.github.io/nspanel_haui/dev/user/examples.html) for a room.

## How it works

The hub runs inside Home Assistant: it reads entity states, renders the display commands and sends
them over the ESPHome native API. The ESP32 relays them to the Nextion display over serial and
reports touches and button presses back. See
[Communication](https://happydasch.github.io/nspanel_haui/dev/develop/communication.html).

## Documentation

The full documentation is at **[happydasch.github.io/nspanel_haui](https://happydasch.github.io/nspanel_haui/dev/)**.

- **Start**: [Installation](https://happydasch.github.io/nspanel_haui/dev/user/install.html) · [Quick start](https://happydasch.github.io/nspanel_haui/dev/user/get-started.html) · [Updating](https://happydasch.github.io/nspanel_haui/dev/user/update.html) · [FAQ](https://happydasch.github.io/nspanel_haui/dev/user/faq.html) · [Troubleshooting](https://happydasch.github.io/nspanel_haui/dev/user/troubleshooting.html)
- **Configure**: [Overview](https://happydasch.github.io/nspanel_haui/dev/user/configuration/index.html) · [Device](https://happydasch.github.io/nspanel_haui/dev/user/configuration/device.html) · [Display models](https://happydasch.github.io/nspanel_haui/dev/user/configuration/display-models.html) · [Panels](https://happydasch.github.io/nspanel_haui/dev/user/configuration/panels.html) · [Items](https://happydasch.github.io/nspanel_haui/dev/user/configuration/items.html) · [Examples](https://happydasch.github.io/nspanel_haui/dev/user/examples.html)
- **Use**: [Gestures and display states](https://happydasch.github.io/nspanel_haui/dev/user/device.html) · [Services](https://happydasch.github.io/nspanel_haui/dev/user/services.html) · [Icons](https://happydasch.github.io/nspanel_haui/dev/cheatsheet.html) · [Screens](https://happydasch.github.io/nspanel_haui/dev/screens.html)
- **Develop**: [Development](https://happydasch.github.io/nspanel_haui/dev/develop/development.html) · [Design](https://happydasch.github.io/nspanel_haui/dev/develop/design.html) · [Communication](https://happydasch.github.io/nspanel_haui/dev/develop/communication.html) · [ESPHome](https://happydasch.github.io/nspanel_haui/dev/develop/esphome.html) · [Hub](https://happydasch.github.io/nspanel_haui/dev/develop/hub.html) · [Nextion](https://happydasch.github.io/nspanel_haui/dev/develop/nextion.html)

For custom firmware builds, see the
[ESPHome development instructions](https://happydasch.github.io/nspanel_haui/dev/develop/esphome.html#installation).

> **Upgrading from 0.3.x or earlier?** Read the [upgrade guide](https://happydasch.github.io/nspanel_haui/dev/user/update.html)
> first. Saved panels do not migrate, and settings stored in config entries by 0.3.2 or earlier are not
> carried over. See [device configuration](https://happydasch.github.io/nspanel_haui/dev/user/configuration/device.html#how-settings-are-saved).

## Credits

Inspired by [NSPanel Lovelace UI](https://github.com/joBr99/nspanel-lovelace-ui) by joBr99 and
[NSPanel HA Blueprint](https://github.com/Blackymas/NSPanel_HA_Blueprint) by Blackymas.

See the [GitHub contributors](https://github.com/happydasch/nspanel_haui/graphs/contributors)
for everyone who contributed. Special thanks to @jameshiscott, who contributed the
[live preview and the Nextion simulator](docs/user/configuration/README.md#the-live-preview).
