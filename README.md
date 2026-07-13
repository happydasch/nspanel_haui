# NSPanel HAUI (HomeAssistant UI)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/happydasch/nspanel_haui)
[![GitHub release](https://img.shields.io/github/v/release/happydasch/nspanel_haui?style=for-the-badge)](https://github.com/happydasch/nspanel_haui/releases)
[![HA Community](https://img.shields.io/badge/HA%20Community-Thread-03a87c?style=for-the-badge)](https://community.home-assistant.io/t/sonoff-nspanel-haui-homeassistant-ui/578570)
[![License](https://img.shields.io/github/license/happydasch/nspanel_haui?style=for-the-badge)](LICENSE)

<p align="center">
  <img src="docs/assets/hero-banner.svg" alt="NSPanel HAUI Hero" width="100%">
</p>

<p align="center">
  <b>A flexible touchscreen display system for the Sonoff NSPanel, built on ESPHome.</b><br>
  All configuration is done through a built-in web frontend — a Lovelace panel<br>
  inside Home Assistant that provides a visual editor for panels, entities,<br>
  gestures, colors, and more.
</p>

---

<p align="center">
  <a href="docs/README.md"><b>Documentation</b></a> ·
  <a href="docs/panels/README.md"><b>Panels Overview</b></a> ·
  <a href="docs/install.md"><b>Installation Guide</b></a> ·
  <a href="docs/config.md"><b>Configuration</b></a> ·
  <a href="docs/faq.md"><b>FAQ</b></a> ·
  <a href="docs/example_config.md"><b>Example Configs</b></a>
</p>


---

## Quick Start

Get NSPanel HAUI up and running with a display dashboard in just 4 steps:

<p align="center">
  <img src="docs/assets/diagrams/install-flow.svg" alt="Installation Flow" width="100%">
</p>


1. **Install via HACS** — Add the custom repository, install the integration, and restart Home Assistant.

   [Install guide →](docs/install.md)

2. **Flash ESPHome** — Use `esphome/install.yaml` as a starting point, configure your Wi-Fi, and flash via USB or OTA.

   [ESPHome guide →](docs/esphome.md)

3. **Add Integration** — Go to Settings → Devices & Services → Add NSPanel HAUI. It auto-discovers your device.

   [Config flow →](docs/custom_integration.md)

4. **Configure Panels** — Open the web frontend, add panels, assign entities, and set colors to your liking.

   [Configuration guide →](docs/config.md)

<a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=happydasch&repository=nspanel_haui&category=integration">
  <img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.">
</a>

---

## Features

<table>
  <tr>
    <td align="center" valign="top" width="16%">
      <img src="https://cdn.jsdelivr.net/npm/@mdi/svg@7/svg/view-grid.svg" width="32" height="32"><br>
      <b>13 Panel Types</b><br>
      <small>Grid, light, climate,<br>cover, media, weather,<br>and more</small>
    </td>
    <td align="center" valign="top" width="16%">
      <img src="https://cdn.jsdelivr.net/npm/@mdi/svg@7/svg/gesture-swipe.svg" width="32" height="32"><br>
      <b>Touch + Gestures</b><br>
      <small>Swipe navigation,<br>gesture sequences,<br>tap interactions</small>
    </td>
    <td align="center" valign="top" width="16%">
      <img src="https://cdn.jsdelivr.net/npm/@mdi/svg@7/svg/palette.svg" width="32" height="32"><br>
      <b>Full Customization</b><br>
      <small>Per-entity colors,<br>icons, backgrounds,<br>themes</small>
    </td>
    <td align="center" valign="top" width="16%">
      <img src="https://cdn.jsdelivr.net/npm/@mdi/svg@7/svg/theme-light-dark.svg" width="32" height="32"><br>
      <b>Auto-Dimming</b><br>
      <small>Smart sleep/wake,<br>ambient light sensor,<br>screensaver</small>
    </td>
    <td align="center" valign="top" width="16%">
      <img src="https://cdn.jsdelivr.net/npm/@mdi/svg@7/svg/tune.svg" width="32" height="32"><br>
      <b>Visual Editor</b><br>
      <small>Built-in Lovelace panel<br>with live previews, drag<br>reorder, color pickers</small>
    </td>
    <td align="center" valign="top" width="16%">
      <img src="https://cdn.jsdelivr.net/npm/@mdi/svg@7/svg/translate.svg" width="32" height="32"><br>
      <b>Multi-Language</b><br>
      <small>English, German,<br>Dutch, Polish,<br>French</small>
    </td>
  </tr>
  <tr>
    <td align="center" valign="top" width="16%">
      <img src="https://cdn.jsdelivr.net/npm/@mdi/svg@7/svg/bell-ring.svg" width="32" height="32"><br>
      <b>Notifications</b><br>
      <small>Sound alerts, toasts,<br>notification queue<br>on display</small>
    </td>
    <td align="center" valign="top" width="16%">
      <img src="https://cdn.jsdelivr.net/npm/@mdi/svg@7/svg/lock.svg" width="32" height="32"><br>
      <b>Panel Locking</b><br>
      <small>PIN-protected unlock<br>for sensitive<br>controls</small>
    </td>
    <td align="center" valign="top" width="16%">
      <img src="https://cdn.jsdelivr.net/npm/@mdi/svg@7/svg/remote.svg" width="32" height="32"><br>
      <b>ESPHome Native API</b><br>
      <small>Fast, reliable<br>communication with<br>the display</small>
    </td>
    <td align="center" valign="top" width="16%">
      <img src="https://cdn.jsdelivr.net/npm/@mdi/svg@7/svg/clock-digital.svg" width="32" height="32"><br>
      <b>Screensaver Modes</b><br>
      <small>Clock, weather,<br>clock-two (text)<br>display modes</small>
    </td>
    <td align="center" valign="top" width="16%">
      <img src="https://cdn.jsdelivr.net/npm/@mdi/svg@7/svg/gesture-tap-hold.svg" width="32" height="32"><br>
      <b>Hardware Buttons</b><br>
      <small>Physical rocker switch<br>support with custom<br>actions</small>
    </td>
    <td align="center" valign="top" width="16%">
      <img src="https://cdn.jsdelivr.net/npm/@mdi/svg@7/svg/qrcode.svg" width="32" height="32"><br>
      <b>QR Code Display</b><br>
      <small>Show Wi-Fi details,<br>URLs, or text as<br>QR codes</small>
    </td>
  </tr>
</table>

---

## Available Panels

See the <a href="docs/panels/README.md">Panels Overview</a> for details.

<table>
  <tr>
    <td width="33%" valign="top">
      <a href="docs/panels/panel_grid.md"><img src="docs/assets/previews/panel-grid.svg" alt="Grid Panel" width="100%"></a><br>
      <b><a href="docs/panels/panel_grid.md">Grid</a></b> <code>grid</code><br>
      <small>Up to 6 entities in a scrollable grid layout. Color overrides, power buttons.</small>
    </td>
    <td width="33%" valign="top">
      <a href="docs/panels/panel_row.md"><img src="docs/assets/previews/panel-row.svg" alt="Row Panel" width="100%"></a><br>
      <b><a href="docs/panels/panel_row.md">Row</a></b> <code>row</code><br>
      <small>Up to 5 entities in a vertical scrollable rows. Compact, text-focused layout.</small>
    </td>
    <td width="33%" valign="top">
      <a href="docs/panels/panel_light.md"><img src="docs/assets/previews/panel-light.svg" alt="Light Panel" width="100%"></a><br>
      <b><a href="docs/panels/panel_light.md">Light</a></b> <code>light</code><br>
      <small>Full light control: brightness, color temp, RGB color wheel, effects.</small>
    </td>
  </tr>
  <tr>
    <td width="33%" valign="top">
      <a href="docs/panels/panel_climate.md"><img src="docs/assets/previews/panel-climate.svg" alt="Climate Panel" width="100%"></a><br>
      <b><a href="docs/panels/panel_climate.md">Climate</a></b> <code>climate</code><br>
      <small>HVAC control: temperature, modes, fan speed, swing, presets.</small>
    </td>
    <td width="33%" valign="top">
      <a href="docs/panels/panel_cover.md"><img src="docs/assets/previews/panel-cover.svg" alt="Cover Panel" width="100%"></a><br>
      <b><a href="docs/panels/panel_cover.md">Cover</a></b> <code>cover</code><br>
      <small>Open/close/stop with vertical position slider. Blinds, garages, curtains.</small>
    </td>
    <td width="33%" valign="top">
      <a href="docs/panels/panel_media.md"><img src="docs/assets/previews/panel-media.svg" alt="Media Panel" width="100%"></a><br>
      <b><a href="docs/panels/panel_media.md">Media</a></b> <code>media</code><br>
      <small>Media player controls, volume, queue. Supports TV, speakers, receivers.</small>
    </td>
  </tr>
  <tr>
    <td width="33%" valign="top">
      <a href="docs/panels/panel_vacuum.md"><img src="docs/assets/previews/panel-vacuum.svg" alt="Vacuum Panel" width="100%"></a><br>
      <b><a href="docs/panels/panel_vacuum.md">Vacuum</a></b> <code>vacuum</code><br>
      <small>Start/stop, return to dock, fan speed, locate. Up to 6 secondary items.</small>
    </td>
    <td width="33%" valign="top">
      <a href="docs/panels/panel_timer.md"><img src="docs/assets/previews/panel-timer.svg" alt="Timer Panel" width="100%"></a><br>
      <b><a href="docs/panels/panel_timer.md">Timer</a></b> <code>timer</code><br>
      <small>Local countdown timer with start/pause/stop. Uses display-local time.</small>
    </td>
    <td width="33%" valign="top">
      <a href="docs/panels/panel_alarm.md"><img src="docs/assets/previews/panel-alarm.svg" alt="Alarm Panel" width="100%"></a><br>
      <b><a href="docs/panels/panel_alarm.md">Alarm</a></b> <code>alarm</code><br>
      <small>Numeric keypad for alarm code entry. Arm/disarm with mode buttons.</small>
    </td>
  </tr>
  <tr>
    <td width="33%" valign="top">
      <a href="docs/panels/panel_qr.md"><img src="docs/assets/previews/panel-qr.svg" alt="QR Panel" width="100%"></a><br>
      <b><a href="docs/panels/panel_qr.md">QR Code</a></b> <code>qr</code><br>
      <small>Display QR codes for Wi-Fi, URLs, or custom text. Great for guest networks.</small>
    </td>
    <td width="33%" valign="top">
      <a href="docs/panels/panel_weather.md"><img src="docs/assets/previews/panel-weather.svg" alt="Weather Panel" width="100%"></a><br>
      <b><a href="docs/panels/panel_weather.md">Weather</a></b> <code>weather</code><br>
      <small>Screensaver-ready weather display. Forecast, backgrounds, info items.</small>
    </td>
    <td width="33%" valign="top">
      <a href="docs/panels/panel_clock.md"><img src="docs/assets/previews/panel-clock.svg" alt="Clock Panel" width="100%"></a><br>
      <b><a href="docs/panels/panel_clock.md">Clock</a></b> <code>clock</code><br>
      <small>Large time/date display. Optional weather, entity buttons, backgrounds.</small>
    </td>
  </tr>
  <tr>
    <td width="33%" valign="top">
      <a href="docs/panels/panel_clocktwo.md"><img src="docs/assets/previews/panel-clocktwo.svg" alt="ClockTwo Panel" width="100%"></a><br>
      <b><a href="docs/panels/panel_clocktwo.md">ClockTwo</a></b> <code>clocktwo</code><br>
      <small>Time displayed as written text. Minimalist screensaver alternative.</small>
    </td>
    <td width="33%" valign="top"></td>
    <td width="33%" valign="top"></td>
  </tr>
</table>

---

## Web Frontend Editor

NSPanel HAUI ships with a **fully integrated web frontend** — a custom Lovelace panel that runs inside Home Assistant and provides a visual, point-and-click interface for configuring everything on your NSPanel.

<p align="center">
  <img src="docs/assets/frontend-preview.svg" alt="Web Frontend Editor Preview" width="100%">
</p>

| Capability | What you can do |
|------------|-----------------|
| **Panel management** | Add, remove and reorder panels. Each panel type (grid, light, climate, etc.) gets a visual **live preview** showing how it will look on the actual display. |
| **Entity assignment** | Pick entities from a searchable HA entity picker. Configure per-entity icons, display names, colors, and overrides. |
| **Color editing** | Full color picker for device-level theme colors and per-item overrides. |
| **Gesture & navigation** | Configure swipe directions, physical button actions, and auto-dimming behavior. |
| **Multi-device** | Manage multiple NSPanels from a single Lovelace panel. Switch between devices, compare configs. |
| **Real-time status** | Live device connection status, uptime, firmware versions, and log viewer — all from the frontend. |

The frontend is **automatically available** once the integration is added — no separate installation step needed. Open it from the Lovelace panel list or via the device page in **Settings → Devices & Services**.

Behind the scenes, the frontend communicates with the HAUI hub app through a REST API (`/api/nspanel_haui/...`) and the Home Assistant custom panel system. The frontend code lives in `custom_components/nspanel_haui/frontend/` and is written in vanilla JavaScript using Lit for components.

---

## Configuration

All device settings — panels, entities, gestures, dimming, sleep, and colours — are managed through the Home Assistant interface.

- **[Configuration Overview](docs/config.md)** — All available options at a glance
- **[Device Configuration](docs/config/device.md)** — Sounds, screensaver, buttons, dimming
- **[Panel Configuration](docs/config/panels.md)** — Creating and arranging panels
- **[Item Configuration](docs/config/items.md)** — Entities, icons, colors, internal items
- **[Device Description](docs/device.md)** — Gestures, display states, hardware buttons, notifications
- **[Example Configs](docs/example_config.md)** — Ready-to-use panel combinations

---

## Architecture

NSPanel HAUI uses a three-layer architecture:

<p align="center">
  <img src="docs/assets/diagrams/architecture.svg" alt="Architecture Diagram" width="100%">
</p>

- **HAUI** (`NSPanelHAUI`, hub that runs in HA) — Reads entity states, renders display commands, manages navigation
- **ESP32** (ESPHome firmware) — Serial bridge between HA and the display, relays touch events
- **Nextion** (Touchscreen display) — Renders panels, manages widget state, handles touch input

Data flows both ways: panel configs and entity states flow **down** to the display, while touch events and button presses flow **up** to Home Assistant.

For detailed architecture information, see the [Communication Overview](docs/communication.md).

---

## Documentation

### End User

- **[Installation Guide](docs/install.md)** — Step-by-step installation instructions
- **[Custom Integration](docs/custom_integration.md)** — How to install and set up the integration
- **[Configuration](docs/config.md)** — Panel and device configuration reference
- **[Panels Overview](docs/panels/README.md)** — All available panel types and their options
- **[Device Description](docs/device.md)** — Device behaviour, gestures, dimming, and features
- **[FAQ](docs/faq.md)** — Frequently asked questions and troubleshooting
- **[Troubleshooting](docs/troubleshooting.md)** — Diagnosing and resolving common problems
- **[Example Configs](docs/example_config.md)** — Example panel configurations
- **[Icons Cheatsheet](https://htmlpreview.github.io/?https://raw.githubusercontent.com/happydasch/nspanel_haui/master/docs/cheatsheet.html)** — Available icon codes for your panels

### Development

- **[Design Guidelines](docs/design.md)** — Styling and panel design principles
- **[Communication Overview](docs/communication.md)** — How Hub, ESPHome, and Nextion communicate
- **[ESPHome Component](docs/esphome.md)** — ESP32 firmware details and serial protocol
- **[Hub Component](docs/hub.md)** — The core integration logic
- **[Nextion Component](docs/nextion.md)** — Display firmware and TFT details

---

## Resources

Inspired by other NSPanel projects:

- [NSPanel Lovelace UI](https://github.com/joBr99/nspanel-lovelace-ui) by joBr99
- [NSPanel HA Blueprint](https://github.com/Blackymas/NSPanel_HA_Blueprint) by Blackymas
