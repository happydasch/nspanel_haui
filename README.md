# NSPanel HAUI (HomeAssistant UI)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/happydasch/nspanel_haui)
[![GitHub release](https://img.shields.io/github/v/release/happydasch/nspanel_haui?style=for-the-badge)](https://github.com/happydasch/nspanel_haui/releases)
[![HA Community](https://img.shields.io/badge/HA%20Community-Thread-03a87c?style=for-the-badge)](https://community.home-assistant.io/t/sonoff-nspanel-haui-homeassistant-ui/578570)
[![License](https://img.shields.io/github/license/happydasch/nspanel_haui?style=for-the-badge)](LICENSE)

A Home Assistant custom integration that replaces the stock Sonoff NSPanel firmware with a flexible, configurable touchscreen display system built on ESPHome. Configure everything from the HA interface — panels, entities, gestures, and dimming — without editing YAML.

[Documentation](docs/README.md) &middot; [Panels Overview](docs/panels/README.md) &middot; [Installation Guide](docs/Install.md) &middot; [Configuration](docs/Config.md) &middot; [FAQ](docs/FAQ.md) &middot; [Example Configs](docs/Example_Config.md) &middot; [HA Community Thread](https://community.home-assistant.io/t/sonoff-nspanel-haui-homeassistant-ui/578570)

---

## Features

| | |
|---|---|
| **Configurable panels** | Grid, row, light, climate, cover, media, vacuum, timer, alarm, QR code, weather, clock, and more |
| **In-UI editor** | Add, remove, and configure panels directly from the Home Assistant interface — no YAML editing required |
| **Touch gestures** | Swipe left/right for navigation, gesture sequences for advanced controls |
| **Live state updates** | Display refreshes instantly when an entity state changes |
| **Display dimming** | Auto-dim brightness after a configurable timeout |
| **Sleep/wake panels** | Switch to a designated page after inactivity; fully configurable sleep and wakeup panels |
| **Panel locking** | Lock any panel with a PIN code; unlock via on-screen keypad |
| **Physical buttons** | Coupled or uncoupled relay modes — use hardware buttons as software inputs |
| **Notifications** | Receive and display notifications with optional looping sounds |
| **Auto-update** | Firmware and TFT updates delivered through the Hub app after initial flash |

---

## Installation

### Prerequisites

- A **Sonoff NSPanel** (original or Pro) connected to your network
- **Home Assistant** 2024.x or newer with **ESPHome** add-on installed
- An **ESPHome dashboard** to manage device firmware

### Step 1: Install via HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=happydasch&repository=nspanel_haui&category=integration)

If the button above does not work:

1. Open **HACS** in your Home Assistant sidebar
2. Go to **Integrations**
3. Click the three-dot menu and select **Custom repositories**
4. Add `https://github.com/happydasch/nspanel_haui` with category **Integration**
5. Click **Install** on the **NSPanel HAUI** entry
6. **Restart Home Assistant**

### Step 2: Flash ESPHome firmware

<details>
<summary>Expand for ESPHome flashing steps</summary>

1. In the ESPHome dashboard, create a new device using the provided [install.yaml](esphome/install.yaml) as a starting point
2. Configure your Wi-Fi credentials and device name
3. Flash the firmware to your NSPanel via USB or OTA
4. After flashing, the TFT display firmware is updated automatically by the Hub app

See the [ESPHome guide](docs/ESPHome.md) and [Nextion guide](docs/Nextion.md) for details.
</details>

### Step 3: Add the integration in Home Assistant

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **NSPanel HAUI** and select it
3. The integration will auto-discover your NSPanel on the network
4. Follow the config flow to set up your device name and ESPHome API credentials

### Step 4: Configure panels

Once the integration is running, each NSPanel appears as a device in Home Assistant. Open the device page to:

- Add, remove, and reorder panels
- Assign entities to each panel
- Configure panel-specific options (display mode, colors, icons, etc.)
- Set up navigation, gestures, dimming, and sleep/wake behaviour

See the [Configuration guide](docs/Config.md) for detailed instructions.

---

### Manual Installation

If you do not use HACS, copy the `custom_components/nspanel_haui/` directory into your Home Assistant `custom_components/` folder and restart. Then follow steps 2-4 above.

---

## Available Panels

| Type | Page | Description |
|------|------|-------------|
| `grid` | [Panel Grid](docs/panels/panel_grid.md) | Up to 6 entities arranged in a grid |
| `row` | [Panel Row](docs/panels/panel_row.md) | Up to 5 entities in a horizontal row |
| `light` | [Panel Light](docs/panels/panel_light.md) | Full light control (brightness, color temp, RGB) |
| `climate` | [Panel Climate](docs/panels/panel_climate.md) | Thermostat / HVAC control panel |
| `cover` | [Panel Cover](docs/panels/panel_cover.md) | Cover / blind position control |
| `media` | [Panel Media](docs/panels/panel_media.md) | Media player controls and queue |
| `vacuum` | [Panel Vacuum](docs/panels/panel_vacuum.md) | Vacuum cleaner controls |
| `timer` | [Panel Timer](docs/panels/panel_timer.md) | Countdown timer with start/stop |
| `alarm` | [Panel Alarm](docs/panels/panel_alarm.md) | Alarm control panel (arm/disarm) |
| `qr` | [Panel QR Code](docs/panels/panel_qr.md) | QR code display (Wi-Fi details, URLs) |
| `weather` | [Panel Weather](docs/panels/panel_weather.md) | Weather forecast + time/date (screensaver) |
| `clock` | [Panel Clock](docs/panels/panel_clock.md) | Time/date + weather (screensaver) |
| `clocktwo` | [Panel ClockTwo](docs/panels/panel_clocktwo.md) | Time as written text (screensaver) |

System panels (blank, settings, about, loading) and popups (unlock, notify, select) are built-in and require no configuration.

---

## Configuration

All device settings — panels, entities, gestures, dimming, sleep, and colours — are managed through the Home Assistant interface. See the [Configuration guide](docs/Config.md) for all available options and the [Device description](docs/Device.md) for a full feature overview.

---

## Documentation

### End User

| Document | Description |
|----------|-------------|
| [Installation Guide](docs/Install.md) | Step-by-step installation instructions |
| [Configuration](docs/Config.md) | Panel and device configuration reference |
| [Panels Overview](docs/panels/README.md) | All available panel types and their options |
| [Device Description](docs/Device.md) | Device behaviour, gestures, dimming, and features |
| [FAQ](docs/FAQ.md) | Frequently asked questions and troubleshooting |
| [Example Configs](docs/Example_Config.md) | Example panel configurations |
| [Icons Cheatsheet](https://htmlpreview.github.io/?https://raw.githubusercontent.com/happydasch/nspanel_haui/master/docs/cheatsheet.html) | Available icon codes |

### Development

| Document | Description |
|----------|-------------|
| [Design Guidelines](docs/Design.md) | Styling and panel design principles |
| [Communication Overview](docs/Communication.md) | How Hub, ESPHome, and Nextion communicate |
| [ESPHome Component](docs/ESPHome.md) | ESP32 firmware details and serial protocol |
| [Hub Component](docs/Hub.md) | The core integration logic |
| [Nextion Component](docs/Nextion.md) | Display firmware and TFT details |

---

## Resources

This project builds on the ideas of:

- [NSPanel Lovelace UI](https://github.com/joBr99/nspanel-lovelace-ui) by joBr99
- [NSPanel HA Blueprint](https://github.com/Blackymas/NSPanel_HA_Blueprint) by Blackymas

### Links

- [ESPHome](https://esphome.io)
- [Nextion Instruction Set](https://nextion.tech/instruction-set/)
- [NSPanel Docs (pky.eu)](https://docs.nspanel.pky.eu/)
- [Generate-HASP-Fonts](https://github.com/joBr99/Generate-HASP-Fonts)
- [NSPanel Demo Files](https://github.com/masto/NSPanel-Demo-Files)
- [nspanel-mf](https://github.com/marcfager/nspanel-mf)
- [HA nextion_handler](https://github.com/krizkontrolz/Home-Assistant-nextion_handler)
