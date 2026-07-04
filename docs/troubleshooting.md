---
title: Troubleshooting
description: Common issues, error messages, and solutions for NSPanel HAUI
---

# Troubleshooting

[README](../README.md) | [Documentation](README.md) | [Installation](Install.md) | [Configuration](Config.md) | [Panels](panels/README.md) | [FAQ](FAQ.md)

- [Troubleshooting](#troubleshooting)
  - [Device Discovery Issues](#device-discovery-issues)
  - [TFT Upload Failures](#tft-upload-failures)
  - [Sleep Errors](#sleep-errors)
  - [Connection Problems](#connection-problems)

## Device Discovery Issues

### NSPanel devices not discovered

If you're running Home Assistant in Docker with **bridge networking** (the default), mDNS auto-discovery may not work. This means the integration won't automatically find your NSPanel devices configured via ESPHome.

**Solution:** Ensure you have manually added your ESPHome devices in Home Assistant's ESPHome integration first. Once the ESPHome entries exist, the HAUI integration will detect them:

1. Go to **Settings → Devices & services → ESPHome**.
2. Click **Add entry** and add each of your NSPanel devices by IP or hostname.
3. After adding them, the HAUI hub will automatically pick up the devices within a few seconds.

**Alternative:** Use `--network=host` for your Home Assistant Docker container — this enables mDNS and ESPHome's native discovery.

**Manual trigger:** Use the "Scan for new devices" button in the HAUI Editor's Device Manager to manually trigger discovery.

## TFT Upload Failures

### "Reading from UART timed out at byte 0!" or "Upgrade response is 0"

If you are getting errors like these, the easiest way to fix this is using the Nextion Editor and a display connected to 5V, GND, TF-TX, TF-RX to upload a new display file.

**Connection reference:** See [blakadder's NSPanel teardown guide](https://blakadder.com/nspanel-teardown/) for connection details.

This will most likely fix the issue. After a successful upload via the Nextion Editor, subsequent OTA updates via the Hub should work normally.

## Sleep Errors

### "[nextion:536] ERROR: Received numeric return but the queue is empty" on sleep

You may see log entries like:

```log
[I] [haui:602] Display is going to sleep
[E] [nextion:536] ERROR: Received numeric return but the queue is empty
```

**Cause:** This is a timing issue where the Nextion display sends a response during sleep transition that the ESPHome nextion component's queue is not expecting. It is a cosmetic issue in the ESPHome nextion component.

**Impact:** None. This error does not affect functionality and can be safely ignored.

## Connection Problems

### ESPHome Native API disconnect

If the device disconnects unexpectedly:

1. Check WiFi signal strength at the NSPanel location.
2. Verify the ESPHome device is powered stably (the NSPanel needs adequate 5V supply).
3. Check the ESPHome logs for stack traces or OOM errors.
4. Try reducing the `update_interval` in the `update` controller config if you have frequent updates triggered.

### HA restart after device configuration

After changing device configuration or adding new panels, a full Home Assistant restart is recommended to ensure all entities and services are properly registered.

### Still stuck?

If you continue having issues after trying these solutions:

- Check the [FAQ](FAQ.md) for additional common questions.
- Open an issue on the [GitHub issue tracker](https://github.com/happydasch/nspanel_haui/issues) with:
  - Your HA version and HAUI version
  - Relevant log entries (from both HA and the ESPHome device)
  - Your configuration (with sensitive info redacted)