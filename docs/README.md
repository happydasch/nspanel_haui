---
title: NSPanel HAUI Documentation
description: HomeAssistant UI for the Sonoff NSPanel — documentation index
---

# NSPanel HomeAssistant UI Docs

Welcome to the documentation for **NSPanel HAUI**, a Home Assistant custom integration
that replaces the stock Sonoff NSPanel firmware with a flexible, configurable display
system built on ESPHome.

---

## End User

These guides help you install, configure, and use NSPanel HAUI on your Sonoff NSPanel device.

- **[Installation](Install.md)** — Step-by-step guide for installing the integration and flashing the device.
- **[Custom Integration](Custom_Integration.md)** — How to install and set up the integration in Home Assistant.
- **[Configuration](Config.md)** — Overview of configuring your panels and device.
  - [Device Configuration](config/device.md) — Device-level settings (sounds, screensaver, buttons, etc.).
  - [Panel Configuration](config/panels.md) — How to create and arrange panels on the display.
  - [Item Configuration](config/items.md) — Configuring entities, icons, colors, and internal items.
- **[Device Description](Device.md)** — How the device works: gestures, display states, hardware buttons, sounds, notifications.
- **[Available Panels](panels/README.md)** — Overview of all panel types with links to each.
- **[Examples](Example_Config.md)** — Example configurations to get started quickly.
- **[FAQ](FAQ.md)** — Frequently asked questions and solutions to common issues.
- **[Troubleshooting](troubleshooting.md)** — Diagnosing and resolving problems.

---

## Development

For developers extending or maintaining the integration.

The system has three main components:

- **ESPHome** — Handles serial communication with the display and relays touch events to the Hub.
- **Hub App** — Runs inside Home Assistant, processes entity states, and controls what the display shows.
- **Nextion Display** — Renders the panels and manages widget state.

- **[Design Guidelines](Design.md)** — Styling, theming, and panel design principles.
- **[Communication Overview](Communication.md)** — How the components communicate.
- **[ESPHome Component](ESPHome.md)** — ESP32 firmware that drives the display and reports events.
- **[Hub Component](Hub.md)** — The core logic: entity state management, panel lifecycle, navigation.
- **[Nextion Component](Nextion.md)** — Display-level operations and widget management.

---

## Versioning

Version information is maintained for:

- **Hub App** — tracked in `custom_components/nspanel_haui/haui/version.py` and synced to `manifest.json` and `pyproject.toml`
- **ESPHome YAML** — the ESPHome device config tracks its own compatibility version
- **TFT Display File** — matches the Hub App release version

Every release should include the compiled TFT file as a release asset.
