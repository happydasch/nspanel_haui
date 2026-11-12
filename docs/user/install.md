---
title: Installation Guide
description: Step-by-step installation guide for NSPanel HAUI
---

# Installation Guide

A new panel is set up in four steps:

1. [Flash the panel](#flash-the-panel) and connect it to your Wi-Fi.
2. Add it to Home Assistant's ESPHome integration.
3. [Install the integration](#install-the-integration).
4. [Add the panel in the editor](#configure-panels) and create your first panels.

You do not need to build firmware, edit YAML or install the ESPHome add-on.

## Requirements

- Home Assistant 2026.11 or later (it includes the Marketplace)
- A Sonoff NSPanel
- A USB-UART adapter for the first flash

## Flash the panel

### Universal image (no YAML)

Every release includes one firmware file, `nspanel_haui.bin`. It works for EU and US panels.

1. Download `nspanel_haui.bin` from the [latest release](https://github.com/happydasch/nspanel_haui/releases/latest).
2. Open the panel and connect the USB-UART adapter. Connect GND to IO0 to enter flashing mode. The [NSPanel teardown guide](https://blakadder.com/nspanel-teardown/) shows how to open and wire the panel.
3. Flash the file with the [ESP Web Flasher](https://web.esphome.io/).
4. Join the panel's Wi-Fi access point, for example `nspanel-haui-a1b2c3`. Enter your Wi-Fi name and password on the page that opens. The panel restarts and joins your network. It keeps these settings across firmware updates.
5. In Home Assistant, add the panel to the **ESPHome** integration. If Home Assistant asks for an encryption key, enter:

    ```
    TlNwYW5lbC1IQVVJLXVuaXZlcnNhbC1rZXktMDAwMDE=
    ```

Repeat steps 2–5 for every panel. Each panel gets its own name: the last six characters of its MAC address are added to the hostname and to the access point name.

!!! warning "The universal image uses a public key"
    Everyone can read the key above, and it also allows wireless firmware installs. If you want private credentials or the ESPHome web server, build your own firmware: see the [ESPHome development instructions](../develop/esphome.md#installation).

## Install the integration

NSPanel HAUI is installed through the [Home Assistant Marketplace](https://www.home-assistant.io/integrations/marketplace/). It is not in the catalog, so you add it as a custom repository.

[Open the NSPanel HAUI repository in Home Assistant](https://my.home-assistant.io/redirect/marketplace_repository/?owner=happydasch&repository=nspanel_haui&category=integration), or follow these steps:

1. Go to **Settings → Marketplace**. Accept the community-content warning if it appears.
2. Select **Add from link**, enter `happydasch/nspanel_haui`, then select **Add**. Connect GitHub if prompted.
3. Open **NSPanel HAUI**, select **Install**, then restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration** and add **NSPanel HAUI**.

??? note "Manual install"
    Copy the `custom_components/nspanel_haui/` folder into the `custom_components/` folder of your Home Assistant configuration, then restart Home Assistant. A manual copy does not receive update notifications.

??? note "Coming from HACS"
    Home Assistant 2026.11 replaces HACS with the Marketplace and migrates existing installations on first startup. NSPanel HAUI stays installed and keeps receiving updates.

    To receive development releases, enable the repository's **Pre-release** switch on the NSPanel HAUI device page under **Settings → Devices & Services → Marketplace**. The update entity is disabled by default.

## Configure panels

Everything is configured in the editor. You do not need to edit `configuration.yaml`.

1. Open **NSPanel HAUI** in the Home Assistant sidebar. The entry is visible to administrators only.
2. Under **Discovered Devices**, select **Add** for your panel, then open it.
3. Switch to **Panels**, select **Add panel** and choose a panel type.
4. Fill in the fields and select **Save**. The display updates right away.

If your panel is not listed, add it to Home Assistant's ESPHome integration first, then select **Scan for devices** or reload the editor.

Next: the [Configuration overview](configuration/README.md) explains the editor, and the [FAQ](faq.md) answers common questions.

## TFT and firmware updates

The display needs its own file, the TFT. You do not install it yourself: about a minute after the panel connects, the hub checks the display and installs the matching TFT when it is missing or outdated. The display is busy for a few minutes while the file is transferred.

Later updates work the same way:

- Update the firmware with the panel's **HAUI Firmware** update entity. The matching TFT follows after the panel reconnects.
- A panel that runs firmware older than 0.4.3 has to be flashed by hand once, with the ESP Web Flasher, the ESPHome dashboard, or **Install firmware → From URL**.

See [Updating](update.md) for the full update steps and [Nextion Display](../develop/nextion.md) for installing a TFT by hand.
