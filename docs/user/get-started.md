---
title: Quick Start Guide
description: Get your NSPanel up and running in a few steps
---

# Quick Start Guide

This is the short version. The [Installation Guide](install.md) has every step in detail.

## What you need

- Home Assistant **2026.11** or later
- A Sonoff NSPanel
- A USB-UART adapter (only for the first flash)
- `nspanel_haui.bin` from the [latest release](https://github.com/happydasch/nspanel_haui/releases/latest)

## 1. Flash the panel

1. Open the panel, connect the USB-UART adapter and connect GND to IO0.
2. Flash `nspanel_haui.bin` with the [ESP Web Flasher](https://web.esphome.io/).
3. Join the panel's Wi-Fi access point (for example `nspanel-haui-a1b2c3`) and enter your Wi-Fi details.
4. Add the panel to Home Assistant's **ESPHome** integration. If it asks for an encryption key, use the one in the [Installation Guide](install.md#flash-the-panel).

## 2. Install the integration

1. Open **Settings → Marketplace** and select **Add from link**.
2. Enter `happydasch/nspanel_haui`, then select **Add**.
3. Install **NSPanel HAUI** and restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration** and add **NSPanel HAUI**.

## 3. Add your first panel

1. Open **NSPanel HAUI** in the Home Assistant sidebar (administrators only).
2. Add your panel under **Discovered Devices** and open it. If it is missing, see the [FAQ](faq.md#my-nspanel-devices-are-not-discovered).
3. Switch to **Panels** and select **Add panel**.
4. Choose a panel type, fill in the fields and select **Save**. The display updates right away.

Two good panels to start with:

<div style="display: flex; flex-wrap: wrap; gap: 1rem;">
  <figure style="flex: 1 1 18rem; margin: 0;">
    <img src="../assets/screens/landscape/clock.png" alt="Clock panel with the time, date, and status icons" width="450" height="320" style="display: block; width: 100%; height: auto;">
    <figcaption><strong>Clock</strong> shows the time and date. It works well as a screensaver.</figcaption>
  </figure>
  <figure style="flex: 1 1 18rem; margin: 0;">
    <img src="../assets/screens/landscape/grid.png" alt="Grid panel titled Rooms with six sample tiles for Lamp, Fan, Blind, Living, TV, and Movie" width="450" height="320" style="display: block; width: 100%; height: auto;">
    <figcaption><strong>Grid</strong> shows the entities you pick as tiles.</figcaption>
  </figure>
</div>

The [Screens overview](../screens.html) shows every panel type, also in the portrait layout.

## Next steps

- Browse all [panel types](panels/README.md)
- Copy ideas from the [example configurations](examples.md)
- Set a home panel and a screensaver in **Device Settings → Special pages**
- Check the [FAQ](faq.md) if something is not working
