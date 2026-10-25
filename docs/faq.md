---
title: Frequently Asked Questions
description: Common issues, troubleshooting, and tips for NSPanel HAUI
---

# FAQ
## I don't know how to start

Take a look at the [Panel Configuration](configuration/panels.md) reference and the [Panel Overview](panels/README.md) for details.

## How to upload a TFT file

The hub installs the TFT the firmware needs automatically when the device connects. To install it by hand:

- In the editor: **Device Manager → Install TFT**
- Using a button: the device's `Update Display` button
- Using a service: `esphome.<device>_upload_tft` or `esphome.<device>_upload_tft_url`

See the [Services Reference](services.md#tft-display-upload) for full details.

## Update is not possible

See [TFT Upload Failures](troubleshooting.md#tft-upload-failures).

## Error on sleep

See [Sleep Errors](troubleshooting.md#display-off-errors). The log entry is harmless.

## The display should change its brightness over the day

Add an automation in Home Assistant that sets the panel's `number.<device>_brightness_full` and `number.<device>_brightness_dimmed` entities, for example dimmed to 55 % from sunrise and to 20 % from sunset.

## The display should turn off completely only at night

Set a **display-off schedule** under Device Settings → Display dimming & off: enable *Sleep schedule* and pick the window (e.g. `22:00`–`07:00`, overnight ranges supported). During the day the display only dims and the idle page stays visible; at night it turns off completely after the display-off timeout and wakes on touch. The hub drives `switch.<device>_use_auto_display_off` by the clock, so automations that toggle that switch (which previously fought the hub's own sync after reconnects and restarts) are no longer needed.

## My NSPanel devices are not discovered

See [Device Discovery Issues](troubleshooting.md#device-discovery-issues).
