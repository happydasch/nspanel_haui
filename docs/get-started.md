---
title: Quick Start Guide
description: Get your NSPanel up and running in 5 minutes
---

# Quick Start Guide

Get your NSPanel connected to Home Assistant and showing your first panel. This guide covers the bare minimum — for full details, see the [Installation Guide](install.md).

## What you need

- A Home Assistant instance with **HACS** installed
- The **ESPHome** add-on installed and running
- A USB-UART adapter (for first-time flashing)
- A Sonoff NSPanel device

## 1. Flash the device

Open the NSPanel and connect the USB-UART adapter (connect GND to IO0 for flashing mode). In the ESPHome dashboard, create a new device using `esphome/install.yaml` from this repository. Set your Wi-Fi credentials and install.

See [Installation Guide](install.md) for full flashing instructions.

## 2. Install the integration

Install NSPanel HAUI via HACS (**HACS → Integrations → + → NSPanel HAUI**) or copy `custom_components/nspanel_haui/` into your Home Assistant `custom_components/` directory. Restart Home Assistant.

## 3. Add the device

Go to **Settings → Devices & Services → Add Integration → NSPanel HAUI**. If your device was discovered via ESPHome, it appears automatically. Otherwise, add it manually.

## 4. Open the panel editor

On the device page, click the device name. The **Panels** tab shows your panel list. Click **Add Panel** to add your first panel.

## 5. Add your first panel

Choose a panel type (e.g., **Clock** for a screensaver or **Grid** for entity tiles). Fill in the required fields and click **Save**. The display updates automatically.

## That's it!

Your NSPanel is now running. Next steps:

- Browse all [panel types](panels/README.md) to see what's available
- Read [example configurations](examples.md) for setup ideas
- Check the [FAQ](faq.md) if something isn't working
