---
title: NSPanel HAUI Documentation
description: HomeAssistant UI (HAUI) for the Sonoff NSPanel — documentation index
---

# NSPanel HAUI Docs

Welcome to the documentation for **NSPanel HAUI**, a Home Assistant custom integration
that replaces the stock Sonoff NSPanel firmware with a flexible, configurable display
system built on ESPHome.

---

## Architecture Overview

NSPanel HAUI uses a three-layer communication architecture:

<p align="center">
  <img src="assets/diagrams/architecture.svg" alt="Architecture Diagram" width="80%">
</p>

| Layer | Component | Role |
|-------|-----------|------|
| **Hub App** | `NSPanelHAUI` (runs in HA) | Reads entity states, renders display commands, manages navigation |
| **ESP32** | ESPHome firmware | Serial bridge between HA and the display, relays touch events |
| **Nextion** | Touchscreen display | Renders panels, manages widget state, handles touch input |

Data flows both ways: panel configs and entity states flow **down** to the display, while touch events and button presses flow **up** to Home Assistant.

---

## End User

These guides help you install, configure, and use NSPanel HAUI on your Sonoff NSPanel device.

- **[Installation](install.md)** — Step-by-step guide for installing the integration and flashing the device.
- **[Custom Integration](custom_integration.md)** — How to install and set up the integration in Home Assistant.
- **[Configuration](config.md)** — Overview of configuring your panels and device.
  - [Device Configuration](config/device.md) — Device-level settings (sounds, screensaver, buttons, etc.).
  - [Panel Configuration](config/panels.md) — How to create and arrange panels on the display.
  - [Item Configuration](config/items.md) — Configuring entities, icons, colors, and internal items.
- **[Device Description](device.md)** — How the device works: gestures, display states, hardware buttons, sounds, notifications.
- **[Available Panels](panels/README.md)** — Overview of all panel types with links to each.
- **[Examples](example_config.md)** — Example configurations to get started quickly.
- **[FAQ](faq.md)** — Frequently asked questions and solutions to common issues.
- **[Troubleshooting](troubleshooting.md)** — Diagnosing and resolving problems.

---

## Development

For developers extending or maintaining the integration.

The system has three main components:

- **ESPHome** — Handles serial communication with the display and relays touch events to the Hub.
- **Hub App** — Runs inside Home Assistant, processes entity states, and controls what the display shows.
- **Nextion Display** — Renders the panels and manages widget state.

- **[Design Guidelines](design.md)** — Styling, theming, and panel design principles.
- **[Communication Overview](communication.md)** — How the components communicate.
- **[ESPHome Component](esphome.md)** — ESP32 firmware that drives the display and reports events.
- **[Hub Component](hub.md)** — The core logic: entity state management, panel lifecycle, navigation.
- **[Nextion Component](nextion.md)** — Display-level operations and widget management.

---

## Versioning

Version information is maintained for:

- **Hub App** — tracked in `custom_components/nspanel_haui/haui/version.py` and synced to `manifest.json` and `pyproject.toml`
- **ESPHome YAML** — the ESPHome device config tracks its own compatibility version
- **TFT Display File** — matches the Hub App release version

Every release should include the compiled TFT file as a release asset.
