---
title: Troubleshooting
description: Common issues, error messages, and solutions for NSPanel HAUI
---

# Troubleshooting

## Device Discovery Issues

### NSPanel devices not discovered

If you're running Home Assistant in Docker with **bridge networking** (the default), mDNS auto-discovery may not work. This means the integration won't automatically find your NSPanel devices configured via ESPHome.

**Solution:** Ensure you have manually added your ESPHome devices in Home Assistant's ESPHome integration first. Once the ESPHome entries exist, the HAUI integration will detect them:

1. Go to **Settings → Devices & services → ESPHome**.
2. Click **Add entry** and add each of your NSPanel devices by IP or hostname.
3. After adding them, the HAUI hub will automatically pick up the devices within a few seconds.

**Alternative:** Use `--network=host` for your Home Assistant Docker container — this enables mDNS and ESPHome's native discovery.

## TFT Upload Failures

### Firmware updates work, TFT installs stay "installing" and then time out

The ESPHome log shows `HTTP_CLIENT: Out of buffer` and `HTTP failed` right after
`TFT upload requested`. GitHub redirects release TFTs to a signed URL of about
870 characters, which does not fit the display component's default 512-byte
HTTP TX buffer, so the upload fails before the first byte and the device never
reboots. Update the ESPHome firmware (the **HAUI Firmware** entity, or
**Device Manager → Install firmware**): it sets `tft_upload_http_buffer_size_tx:
2048`. The TFT install follows after the reboot.

### "Reading from UART timed out at byte 0!" or "Upgrade response is 0"

If you are getting errors like these, the easiest way to fix this is using the Nextion Editor and a display connected to 5V, GND, TF-TX, TF-RX to upload a new display file.

**Connection reference:** See [blakadder's NSPanel teardown guide](https://blakadder.com/nspanel-teardown/) for connection details.

This will most likely fix the issue. After a successful upload via the Nextion Editor, subsequent OTA updates via the Hub should work normally.

## Display-Off Errors

### "[nextion:536] ERROR: Received numeric return but the queue is empty" on display-off

You may see log entries like:

```log
[I] [haui:602] Display off
[E] [nextion:536] ERROR: Received numeric return but the queue is empty
```

Line numbers in the log may differ between versions.

**Cause:** This is a timing issue where the Nextion display sends a response during the transition into *hardware* sleep (which only happens without a hub connection) that the ESPHome nextion component's queue is not expecting. It is a cosmetic issue in the ESPHome nextion component.

**Impact:** None. This error does not affect functionality and can be safely ignored. With a hub connected the display is never hardware-slept, so this message does not appear in normal hub operation.

## Editor Loading Problems

### The editor stays on "Waiting for Home Assistant to load …"

The configuration editor renders Home Assistant's own dialog and card elements
(`<ha-dialog>`, `<ha-dialog-footer>`, `<ha-card>`, `<ha-alert>`). Home Assistant loads
those lazily, so the editor waits up to **10 seconds** for them and then lists the ones
that are still missing. The loading screen offers two actions:

- **Reload page** — reloads the editor so Home Assistant runs its startup sequence again.
  Try this first; the wait normally clears on its own within a second or two.
- **Continue anyway** — renders the editor with the elements that do exist. Dialogs then
  appear inline rather than as modals. This is an escape hatch for inspecting or reverting
  configuration when a Home Assistant version does not define one of the listed elements —
  it is not a supported working mode.

If neither helps, include your Home Assistant version and the list of missing elements when
you open an issue on the [GitHub issue tracker](https://github.com/happydasch/nspanel_haui/issues).

## Connection Problems

### ESPHome Native API disconnect

If the device disconnects unexpectedly:

1. Check WiFi signal strength at the NSPanel location.
2. Verify the ESPHome device is powered stably (the NSPanel needs adequate 5V supply).
3. Check the ESPHome logs for stack traces or OOM errors.

### Changes in the editor

Saving in the editor applies device settings and panels at once; no restart is needed. Restart Home Assistant only after updating the integration itself.

### Still stuck?

If you continue having issues after trying these solutions:

- Check the [FAQ](faq.md) for additional common questions.
- Open an issue on the [GitHub issue tracker](https://github.com/happydasch/nspanel_haui/issues) with:
  - Your HA version and HAUI version
  - Relevant log entries (from both HA and the ESPHome device)
  - Your configuration (with sensitive info redacted)
