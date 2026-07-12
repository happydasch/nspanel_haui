---
title: NSPanel HAUI Documentation
description: HomeAssistant UI (HAUI) for the Sonoff NSPanel — documentation index
---

# NSPanel HAUI Docs

Welcome! **NSPanel HAUI** turns your Sonoff NSPanel into a smart touchscreen
dashboard for Home Assistant — all configured through a visual editor in the HA UI.

Whether you just got your panel or want to fine-tune it, this guide will get you there.

---

## 🚀 Getting Started

If you're setting up a new NSPanel, follow these steps in order:

1. **Install the integration** — Add NSPanel HAUI to Home Assistant via HACS.
   → [Installation guide](install.md)

2. **Flash your device** — Load ESPHome firmware onto the NSPanel.
   → [ESPHome setup](esphome.md)

3. **Connect it** — Add the device in Home Assistant (Settings → Devices & Services).
   → [Integration setup](custom_integration.md)

4. **Configure your panels** — Open the web frontend and start building your dashboard.
   → [Configuration overview](config.md)
   - [Device settings](config/device.md) — brightness, sounds, screensaver, buttons
   - [Panel layout](config/panels.md) — add, remove, reorder panels
   - [Items & entities](config/items.md) — pick entities, set icons, colors

5. **Browse panel types** — See what kinds of panels you can add.
   → [All panel types](panels/README.md)

---

## 📖 Guides

Hands-on help for common tasks.

| Guide | What you'll learn |
|-------|-------------------|
| [Installation](install.md) | Step-by-step: HACS, flashing, first setup |
| [Configuration](config.md) | Device settings, panel layout, item editing |
| [Panel Overview](panels/README.md) | All panel types with descriptions and docs |
| [Examples](example_config.md) | Real-world configs to copy and adapt |
| [Device Description](device.md) | Gestures, buttons, notifications, sleep modes |
| [FAQ](faq.md) | Answers to common questions |
| [Troubleshooting](troubleshooting.md) | Fixing connection issues, display problems, and more |

---

<details>
<summary><b>🔧 Developer Docs</b> — architecture, component design, extending the integration</summary>

The system has three layers:

<p align="center">
  <img src="assets/diagrams/architecture.svg" alt="Architecture Diagram" width="80%">
</p>

| Layer | Component | Role |
|-------|-----------|------|
| **Hub App** | `NSPanelHAUI` (runs in HA) | Reads entity states, renders display commands, manages navigation |
| **ESP32** | ESPHome firmware | Serial bridge between HA and the display, relays touch events |
| **Nextion** | Touchscreen display | Renders panels, manages widget state, handles touch input |

- **[Design Guidelines](design.md)** — Styling, theming, and panel design principles
- **[Communication Overview](communication.md)** — How the layers talk to each other
- **[ESPHome Component](esphome.md)** — ESP32 firmware details
- **[Hub Component](hub.md)** — Core logic: state management, panel lifecycle, navigation
- **[Nextion Component](nextion.md)** — Display-level operations and widget management

</details>

<details>
<summary><b>📦 Versioning</b> — release structure and version tracking</summary>

Version information is maintained for:

- **Hub App** — tracked in `custom_components/nspanel_haui/haui/version.py` and synced to `manifest.json` and `pyproject.toml`
- **ESPHome YAML** — the ESPHome device config tracks its own compatibility version
- **TFT Display File** — matches the Hub App release version

Every release should include the compiled TFT file as a release asset.

</details>
