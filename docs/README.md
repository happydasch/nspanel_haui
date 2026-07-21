---
title: NSPanel HAUI Documentation
description: HomeAssistant UI (HAUI) for the Sonoff NSPanel — documentation index
---

# NSPanel HAUI Docs

Welcome! **NSPanel HAUI** turns your Sonoff NSPanel into a smart touchscreen
dashboard for Home Assistant — all configured through a visual editor in the HA UI.

Whether you just got your panel or want to fine-tune it, this guide will get you there.

> **New to NSPanel HAUI?** → Start with the [Quick Start Guide](get-started.md).

---

## Getting Started

If you're setting up a new NSPanel, follow these steps in order:

1. **Install the integration** — Add NSPanel HAUI to Home Assistant via HACS.
   → [Installation guide](install.md)

2. **Flash your device** — Load ESPHome firmware onto the NSPanel.
   → [ESPHome setup](esphome.md)

3. **Connect it** — Add the device in Home Assistant (Settings → Devices & Services).
   → [Integration setup](custom_integration.md)

4. **Configure your panels** — Open the web frontend and start building your dashboard.
   → [Configuration overview](configuration/README.md)
   - [Device settings](configuration/device.md) — brightness, sounds, screensaver, buttons
   - [Panel layout](configuration/panels.md) — add, remove, reorder panels
   - [Items & entities](configuration/items.md) — pick entities, set icons, colors

5. **Browse panel types** — See what kinds of panels you can add.
   → [All panel types](panels/README.md)

---

## Guides

Hands-on help for common tasks.

### Setting up

- **[Quick Start](get-started.md)** — Get up and running in 5 minutes
- **[Installation](install.md)** — Step-by-step: HACS, flashing, first setup
- **[Configuration](configuration/README.md)** — Device settings, panel layout, item editing
- **[Examples](examples.md)** — Real-world configs to copy and adapt

### Using your panel

- **[Panel Overview](panels/README.md)** — All panel types with descriptions and docs
- **[Device Description](device.md)** — Gestures, buttons, notifications, sleep modes

### Need help?

- **[FAQ](faq.md)** — Answers to common questions
- **[Troubleshooting](troubleshooting.md)** — Fixing connection issues, display problems, and more

---

## Development

Want to understand the internals, extend the integration, or contribute?

[Development docs](development.md) — architecture, component design, versioning
