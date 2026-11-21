---
title: Installation Guide
description: Step-by-step installation guide for NSPanel HAUI
---

# Installation Guide

A new panel takes four steps: flash it, add it to ESPHome, install the integration and set up its panels. No firmware build, YAML or ESPHome add-on is needed.

## Requirements

- Home Assistant 2026.11 or later (it includes the Marketplace)
- A Sonoff NSPanel
- A USB-UART adapter for the first flash

## Flash the panel

!!! warning "Back up the stock firmware first"
    Flashing replaces the Sonoff firmware and erases the panel's unique eWeLink credentials. If you may
    want to return the panel to its original state, save a backup before the first flash; see
    [Back up the stock firmware](backup.md).

### Universal image (no YAML)

Every release includes one firmware file, `nspanel_haui.bin`. It works for EU and US panels.

1. Download `nspanel_haui.bin` from the [latest release](https://github.com/happydasch/nspanel_haui/releases/latest).
2. Open the panel and connect the USB-UART adapter with GND to IO0; the [teardown guide](https://blakadder.com/nspanel-teardown/) shows how.
3. Flash the file with the [ESP Web Flasher](https://web.esphome.io/).
4. Join the panel's Wi-Fi access point, for example `nspanel-haui-a1b2c3`, and enter your Wi-Fi details. The panel restarts on your network and keeps these settings across firmware updates.
5. Add the panel to Home Assistant's **ESPHome** integration. If it asks for an encryption key, enter:

    ```
    TlNwYW5lbC1IQVVJLXVuaXZlcnNhbC1rZXktMDAwMDE=
    ```

Repeat steps 2–5 for every panel; its hostname and access point get the last six MAC characters.

!!! warning "The universal image uses a public key"
    Everyone can read the key, and it allows wireless firmware installs. For private credentials or the web server, [build your own firmware](../develop/esphome.md#installation).

## Install the integration

NSPanel HAUI is not in the [Marketplace](https://www.home-assistant.io/integrations/marketplace/) catalog, so add it as a custom repository:

[Open the NSPanel HAUI repository in Home Assistant](https://my.home-assistant.io/redirect/marketplace_repository/?owner=happydasch&repository=nspanel_haui&category=integration), or:

1. Go to **Settings → Marketplace**. Accept the community-content warning if it appears.
2. Select **Add from link**, enter `happydasch/nspanel_haui`, then select **Add**. Connect GitHub if prompted.
3. Open **NSPanel HAUI**, select **Install**, then restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration** and add **NSPanel HAUI**.

??? note "Manual install"
    Copy `custom_components/nspanel_haui/` into your Home Assistant `custom_components/` folder and restart. Manual copies get no update notifications.

??? note "Coming from HACS"
    Home Assistant 2026.11 migrates HACS automatically; updates continue. For development releases, enable **Pre-release** under **Settings → Devices & services → Marketplace**.

## Configure panels

Everything else is configured in the editor; `configuration.yaml` stays untouched.

1. Open **NSPanel HAUI** in the Home Assistant sidebar (administrators only).
2. Under **Discovered Devices**, select **Add** for your panel, then open it.
3. On **Panels**, select **Set up this device** for a ready-made configuration, or **Add panel** to build a page yourself.
4. Change whatever the page needs and select **Save**. The display updates right away.

If your panel is not listed, add it to Home Assistant's ESPHome integration first, then select **Scan for devices** or reload the editor.

Next: the [Editor overview](editor/README.md) explains the editor, and the [FAQ](faq.md) answers common questions.

## TFT and firmware updates

The display also needs its TFT file. You do not install it: about a minute after the panel connects, the hub installs the matching TFT if it is missing or outdated. The transfer takes several minutes.

- Update the firmware with the panel's **HAUI Firmware** update entity. The matching TFT follows after the panel reconnects.
- **Firmware 0.4.3 or older** must be updated once by hand before the hub can update it. See [Other ways to update](update.md#other-ways-to-update).

See [Updating](update.md) for the full update flow and manual TFT installs.
