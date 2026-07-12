---
title: Frequently Asked Questions
description: Common issues, troubleshooting, and tips for NSPanel HAUI
---

# FAQ
## I don't know how to start

Take a look at the [Panel Configuration](config/panels.md) reference and the [Panel Overview](panels/README.md) for details.

## How to upload a TFT file

- Using a button:
  - Button: `Update Display`

- Using a service:
  - Service: `esphome.<device>_upload_tft`
  - Service: `esphome.<device>_upload_tft_url`

See the [Services Reference](services.md#tft-display-upload) for full details.

## Update is not possible

If you are getting errors like `Reading from UART timed out at byte 0!` or `Upgrade response is   0` the easiest way to fix this is using the Nextion Editor and a display connected to 5V, GND, TF-TX, TF-RX (See [https://blakadder.com/nspanel-teardown/](https://blakadder.com/nspanel-teardown/) for connection details) to upload a new display file.
This will most likely fix the issue.

## Error on sleep

You may see log entries as below. This cannot be changed and does not cause any harm.

```log
[I] [haui:602] Display is going to sleep
[E] [nextion:536] ERROR: Received numeric return but the queue is empty
```

## The display should change its brightness and sleep state over the day

Add an automation in home assistant. NSPanel HAUI does not support to change this but home assistant is way more flexible so it's very simple to change anything dynamically using home assistant automations.

Here is an example of how to do this:

Day (from sunrise): Dimmed to 55%, no sleep.

Evening (from sunset): Dimmed to 20%, no sleep.

Night (4,5h after sunset): Display can go to sleep (the dimmed brightness will remain 20%).

## My NSPanel devices are not discovered

If you're running Home Assistant in Docker with **bridge networking** (the default), mDNS auto-discovery may not work.  This means the integration won't automatically find your NSPanel devices configured via ESPHome.

To resolve this, ensure you have manually added your ESPHome devices in Home Assistant's ESPHome integration first.  Once the ESPHome entries exist, the HAUI integration will detect them:

1. Go to **Settings → Devices & services → ESPHome**.
2. Click **Add entry** and add each of your NSPanel devices by IP or hostname.
3. After adding them, the HAUI hub will automatically pick up the devices within a few seconds.

If you continue having discovery issues:

- Use `--network=host` for your Home Assistant Docker container — this enables mDNS and ESPHome's native discovery.
