---
title: Troubleshooting
description: Common issues, error messages, and solutions for NSPanel HAUI
---

# Troubleshooting

## Device Discovery Issues

### NSPanel devices not discovered

The editor finds panels through Home Assistant's ESPHome integration. A panel that is not added there cannot be found.

1. Go to **Settings → Devices & services → ESPHome**.
2. Select **Add entry** and add each panel by its IP address or hostname.
3. Open the NSPanel HAUI editor again. The panels appear under **Discovered Devices** within a few seconds.

**Home Assistant in Docker:** with bridge networking (the default), Home Assistant cannot discover ESPHome devices on its own, so add each panel by IP address as described above. On Linux you can instead run the container with `--network=host`. Docker Desktop on macOS does not support this; keep bridge networking there.

### Panels reachable from one machine but not another

**Symptom:** one machine reaches the panels (for example your Home Assistant or the ESPHome dashboard). Another machine on the same network cannot ping them, does not discover them and cannot add them by IP address, although it reaches other devices.

**Cause:** the Wi-Fi network filters broadcast and multicast traffic to the panels. The second machine then never learns the panel's hardware address, and discovery (mDNS) is blocked as well. On UniFi this is the **Multicast and Broadcast Control** setting of the Wi-Fi network; machines on its exception list keep working.

**Check (macOS):** enter the panel's MAC address by hand (your router's client list shows it), test the ESPHome API port and remove the entry again:

```bash
sudo arp -s 192.168.0.106 <panel-mac> ifscope en0
nc -vz 192.168.0.106 6053
sudo arp -d 192.168.0.106
```

**Fix:** if `nc` only connects with the manual entry, turn the filter off or add the machine to its exceptions. On macOS, first set **Private Wi-Fi address** to **Off** or **Fixed** for that network. Otherwise the exception stops matching when the address changes.

## TFT Upload Failures

### Firmware updates work, TFT installs stay "installing" and then time out

**Symptom:** the ESPHome log shows `HTTP_CLIENT: Out of buffer` and `HTTP failed` right after `TFT upload requested`.

**Cause:** the download address of a release TFT is too long for older firmware, so the upload fails before it starts.

**Fix:** update the firmware first, with the **HAUI Firmware** entity or by pressing **Install** beside **Firmware** in the **Updates** sidebar. The TFT install follows after the restart.

### TFT install fails with "the panel did not reboot after the upload"

**Cause:** the upload stopped partway, usually because of a weak Wi-Fi connection. This happens more often when several panels upload at the same time. The display may be blank or half-drawn until an upload succeeds.

**Fix:** install the TFT again, one panel at a time. The ESPHome log shows the error as `[E][nextion.upload]` lines ending in `Upload failed`.

### The install fails at once and names a reason

Since the firmware that reports upload failures, the hub shows the panel's own reason instead of waiting 20 minutes. The reason is also in the ESPHome log as `TFT upload failed: …`:

| Reason | Cause | Fix |
|--------|-------|-----|
| `the server answered HTTP 404` (or another `4xx`/`5xx`) | The `url` does not serve a file to the panel | Check the address on another device; it must be reachable from the panel, not only from your browser |
| `the server does not support range requests` | The host answers the whole file to every request; the panel downloads a TFT in ranges | Serve the file from Home Assistant's own `www` folder (`/local/…`) or another host that supports ranges |
| `the file size … is out of range` | The download is smaller than 4 KiB or bigger than 128 MiB — usually an HTML error page instead of a `.tft` | Point `url` at the `.tft` file itself |
| `the panel has no network connection` | The panel lost Wi-Fi before the download started | Check the panel's Wi-Fi and try again |
| `the display refused the upload` | The display is in a state where it will not take a file (a half-finished upload) | Power-cycle the panel, then install again |
| `an upload is already running` | A second request arrived while the first transfer was still running | Wait for it to finish; power-cycle the panel if it never does |
| `A TFT install started at … is still running` | The hub refused a second install because one is in flight | Wait, or power-cycle the panel to clear an upload that never finishes |

A `url` that Home Assistant cannot read is **not** one of these: the hub warns and starts the install anyway, because the panel's network can differ from Home Assistant's. The editor and the action refuse a URL only when Home Assistant got a definite answer (a `404`, no range support, too large).

### The action or Install button says it started, but nothing happens

**Cause:** an install was already in flight, or the panel had not handed over to the hub yet. The editor and `nspanel_haui.update_tft` now fail with the reason instead of returning a false success.

**Fix:** read the reason in the **Updates** sidebar or the failure message. If it names an install that is still running, wait for it; if the panel never finishes, power-cycle it and install again. Firmware from this release reports a failed upload within seconds; older firmware only reports through the timeout.

### "Reading from UART timed out at byte 0!" or "Upgrade response is 0"

**Fix:** upload the display file with the Nextion Editor over a cable. Connect the display to 5V, GND, TF-TX and TF-RX; [blakadder's NSPanel teardown guide](https://blakadder.com/nspanel-teardown/) shows the connections. After one successful upload this way, updates through the hub work again.

## Display-Off Errors

### "[nextion:536] ERROR: Received numeric return but the queue is empty" on display-off

You may see log entries like these (the line numbers differ between versions):

```log
[I] [haui:602] Display off
[E] [nextion:536] ERROR: Received numeric return but the queue is empty
```

**You can ignore this.** The display answers at a moment the ESPHome display component does not expect. Nothing is broken, and it does not appear during normal dimming.

## Editor Loading Problems

### The editor stays on "Waiting for Home Assistant to load …"

The editor uses parts of the Home Assistant interface that load a moment after the page. It waits up to **10 seconds** for them. If they are still missing, the loading screen lists them and offers two buttons:

- **Reload page** — try this first. It usually fixes the problem.
- **Continue anyway** — opens the editor without the missing parts. Dialogs then appear inside the page instead of as popups. Use this only to look at or fix your configuration; it is not meant for normal work.

If neither helps, [open an issue](https://github.com/happydasch/nspanel_haui/issues) and include your Home Assistant version and the list of missing parts.

## Connection Problems

### The panel disconnects

1. Check the Wi-Fi signal where the panel is mounted. The device's **Diagnostics** card in the editor shows the signal and how often the connection dropped in the last 24 hours.
2. Check that the panel has a stable power supply.
3. Check the ESPHome logs for errors.

### Changes in the editor do not need a restart

Saving in the editor applies device settings and panels right away. Restart Home Assistant only after updating the integration itself.

## Still stuck?

- Check the [FAQ](faq.md).
- [Open an issue](https://github.com/happydasch/nspanel_haui/issues) and include:
    - your Home Assistant and NSPanel HAUI versions
    - the relevant log entries from Home Assistant and from the ESPHome device
    - your configuration, with private details removed

The device's **Diagnostics** card has a **Copy report** button that collects most of this for you.
