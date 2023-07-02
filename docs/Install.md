# Installation Guide

[README](../README.md) | [Documentation](README.md) | [Installation](Install.md) | [Configuration](Config.md) | [Panels](panels/README.md) | [FAQ](FAQ.md)

- [Installation Guide](#installation-guide)
  - [1. Step: Preparations](#1-step-preparations)
  - [2. Step: Install ESPHome](#2-step-install-esphome)
  - [3. Step: Install Nextion Display](#3-step-install-nextion-display)
  - [4. Step: Install AppDaemon App](#4-step-install-appdaemon-app)
  - [5. Step: Configuration](#5-step-configuration)

## 1. Step: Preparations

- Prepare Panel

  It is neccessary to flash the panel once with ESPHome.
  To be able to flash the panel the first time the device needs to be opened and connected via a USB-UART-Adapter.

  Unscrew the backside of the panel
  ![Unscrew Panel](assets/serial_conn_unscrew.jpg)

  Release the display cable holder
  ![Release Display Cable](assets/serial_conn_release.jpg)

  Panel overview, connect cables
  ![Panel Overview](assets/serial_conn_overview.jpg)

  Connected cables, GND to IO0, flashing mode
  ![Panel Connect](assets/serial_conn_connect.jpg)

- Flash via Web [https://web.esphome.io/](https://web.esphome.io/)

  Open firmware file `nspanel_haui.bin` and click on Install

  Wait until finshed
  ![ESPHome Web Installing](assets/esphome_web_installing.jpg)

  Successfully flashed, disconnect and put everything back together again.
  ![ESPHome Web Finished](assets/esphome_web_finished.jpg)

## 2. Step: Install ESPHome

- Install custom component on server
- Install ESPHome on ESP

## 3. Step: Install Nextion Display

- Install TFT Display File

  Either service `upload_tft` or Button `Update Display`

## 4. Step: Install AppDaemon App

- Install AppDaemon on server

  Copy `nspanel_haui` to `appdaemon/apps/` or use HACS.

## 5. Step: Configuration

- Add configuration for panel

  Open and edit the file `appdaemon/apps/apps.yaml` for more details about the configuration file and available options see [Configuration Details](Config.md).
