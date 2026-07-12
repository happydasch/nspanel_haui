---
title: Development
description: Architecture, component design, and information for extending NSPanel HAUI
---

# Development

Everything you need to understand the internals of NSPanel HAUI, extend the
integration, or contribute to the project.

---

## Architecture

The system has three layers:

<p align="center">
  <img src="assets/diagrams/architecture.svg" alt="Architecture Diagram" width="80%">
</p>

| Layer | Component | Role |
|-------|-----------|------|
| **Hub App** | `NSPanelHAUI` (runs in HA) | Reads entity states, renders display commands, manages navigation |
| **ESP32** | ESPHome firmware | Serial bridge between HA and the display, relays touch events |
| **Nextion** | Touchscreen display | Renders panels, manages widget state, handles touch input |

---

## Developer Docs

- **[Design Guidelines](design.md)** — Styling, theming, and panel design principles
- **[Communication Overview](communication.md)** — How the layers talk to each other
- **[ESPHome Component](esphome.md)** — ESP32 firmware details
- **[Hub Component](hub.md)** — Core logic: state management, panel lifecycle, navigation
- **[Nextion Component](nextion.md)** — Display-level operations and widget management
- **[Services Reference](services.md)** — Home Assistant services for display control and TFT upload

---

## Versioning

Version information is maintained for:

- **Hub App** — tracked in `custom_components/nspanel_haui/haui/version.py` and synced to `manifest.json` and `pyproject.toml`
- **ESPHome YAML** — the ESPHome device config tracks its own compatibility version
- **TFT Display File** — matches the Hub App release version

Every release should include the compiled TFT file as a release asset.
