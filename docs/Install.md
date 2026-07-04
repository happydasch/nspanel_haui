---
title: Installation Guide
description: Step-by-step installation guide for NSPanel HAUI
---

# Installation Guide

[README](../README.md) | [Documentation](README.md) | [Installation](Install.md) | [Configuration](Config.md) | [Panels](panels/README.md) | [FAQ](FAQ.md)

- [Installation Guide](#installation-guide)
  - [Requirements](#requirements)
  - [1. Step: Preparations](#1-step-preparations)
  - [2. Step: Install ESPHome](#2-step-install-esphome)
  - [3. Step: Install Hub App](#3-step-install-hub-app)
  - [4. Step: Configuration for Hub](#4-step-configuration-for-hub)
  - [5. Step: Install TFT File](#5-step-install-tft-file)
  - [Finished](#finished)

## Requirements

HomeAssistant needs to provide following applications:

- ESPHome
- Hub (nspanel_haui custom integration)

Please install all requirements before continuing.

## 1. Step: Preparations

It is neccessary to flash the panel once with ESPHome.

To be able to flash the panel the first time the device needs to be opened and connected via a USB-UART-Adapter.

- Unscrew the backside of the panel
  ![Unscrew Panel](assets/serial_conn_unscrew.jpg)

- Release the display cable holder
  ![Release Display Cable](assets/serial_conn_release.jpg)

- Panel overview, connect cables
  ![Panel Overview](assets/serial_conn_overview.jpg)

- Connected cables, GND to IO0, flashing mode**
  ![Panel Connect](assets/serial_conn_connect.jpg)

## 2. Step: Install ESPHome

With the prepared and connected device it is now possible to install ESPHome on it.

- Get config for ESPHome

  The configuration can be found in `esphome/install.yaml`

  copy the content of this file into esphome and adjust the values accordingly. See below for an more detailed explaination of the configuration values.

- Create new device

  Create a new device in ESPHome. Set the device name to the hostname of the device. If you want to access. By default the config is using nspanel-haui which can be accessed at <http://nspanel-haui.local>

  ![Device Name](assets/esphome_create_config.png)
  ![Encryption Key](assets/esphome_encyption_key.png)

- Replace configuration

  Store the ota password and encryption key and replace the existing config with the config from `esphome/install.yaml`. See `esphome/README.md` for the full directory layout.

  ![Device Name](assets/esphome_created_config.png)

- Edit configuration

  Only substitutions needs to be edited.
  Either use a secrets.yaml file or set the configuration values directly in this file.

  The name of the device can be set with `name`.

  - name: host- and device name

  Some credentials needs to be provided:

  - Wifi SSID and Password for autoconnect `wifi_ssid`, `wifi_password`
  - Web Access Login Details `web_username`, `web_password`
  - OTA Password and API Encryption Key `ota_password`, `api_encryption_key`

  ![Device Name](assets/esphome_replaced_config.png)

- Install configuration

  When the configuration is done, install the configuration on the device.

  Select Plug into this computer if the device is connected and your broswer supports it or select Manual download to get the binary file `nspanel_haui.bin`.

- Optional: Flash via Web [https://web.esphome.io/](https://web.esphome.io/)

  Open firmware file `nspanel_haui.bin` and click on Install

  Wait until finshed
  ![ESPHome Web Installing](assets/esphome_web_installing.jpg)

  Successfully flashed, disconnect and put everything back together again.
  ![ESPHome Web Finished](assets/esphome_web_finished.jpg)

## 3. Step: Install Hub App

Now that the device is prepared, the Hub app can be activated. Install manually by copying the `custom_components/nspanel_haui` folder from this repository into your Home Assistant `custom_components/` directory, or install via HACS.

- Install Hub on Server

  Copy the folder `nspanel_haui` to `custom_components/nspanel_haui/`.

- Install Hub using HACS

This needs to be done only once.

## 4. Step: Configuration for Hub

Edit `configuration.yaml` and create the config for Hub.

- Add configuration for panel

  Open and edit the file `configuration.yaml` for more details about the configuration file and available options see [Configuration Details](Config.md).

  See [Config Examples](Example_Config.md) for some sample configurations.

## 5. Step: Install TFT File

The display needs a custom interface which is provided in a TFT file. The file will automatically be installed on the display when the Device connects to the Hub App.

The installation process can also be executed manually. See [Nextion Display](Nextion.md) for details.

## Finished

To install more devices just use unique names. The process remains the same for multiple devices.

See [Documentation](README.md) for more details.
