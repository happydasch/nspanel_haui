---
title: Back up the stock firmware
description: Save the original Sonoff firmware and its eWeLink credentials before flashing NSPanel HAUI
---

# Back up the stock firmware

This step is optional. It is also the only chance to keep the panel's original Sonoff firmware: the first
flash erases it.

Each panel leaves the factory with its own eWeLink credentials in the ESP32 flash. The eWeLink app uses them
to identify the panel, and they cannot be recreated. Copies of the stock firmware found online carry the
credentials of the panel they came from, so they do not work on a different panel.

Make a backup if you may want to return the panel to stock, test a suspected hardware fault with Sonoff's
software, claim the warranty, or sell the panel.

!!! warning "A backup is only possible before the first flash"
    Once NSPanel HAUI, or any other firmware, has been installed, the original firmware and its credentials
    are gone.

## What a backup covers

- **ESP32:** the firmware, the eWeLink credentials, and usually the Wi-Fi settings. This is what `esptool`
  reads.
- **Nextion display:** the display firmware and its TFT cannot be read back. The original Sonoff TFT is
  proprietary and is not distributed here.

A complete restore therefore also needs the original Sonoff TFT. Without it, the display stays on the NSPanel
HAUI screen even after the ESP32 is restored.

!!! danger "Keep the backup private"
    The file contains the panel's eWeLink credentials and may contain your Wi-Fi name and password. Store it
    safely and never attach it to an issue, a discussion or a chat.

## Create the backup

Use the same USB-UART connection as the first flash, with GND connected to IO0 to put the ESP32 into firmware
transfer mode. The [teardown guide](https://blakadder.com/nspanel-teardown/) shows how to open the panel and
connect the adapter.

1. Install `esptool`:

    ```bash
    pip install esptool
    ```

2. Find the serial port of the adapter, for example `COM3` on Windows or `/dev/ttyUSB0` on Linux.
3. Read the whole 4 MB flash into a file:

    ```bash
    esptool --port <PORT> --baud 115200 read-flash 0 0x400000 nspanel_stock.bin
    ```

4. Verify the backup against the flash:

    ```bash
    esptool --port <PORT> --baud 115200 verify-flash 0 nspanel_stock.bin
    ```

Continue only when verification succeeds. If it fails, read the flash again.

Older versions of `esptool` use `esptool.py` as the command and underscores in the subcommand, for example
`esptool.py read_flash 0 0x400000 ...`.

Close the terminal when the backup is done so the serial port is released, then continue with
[Installation](install.md#flash-the-panel). One backup per panel: a file only works on the panel it was taken
from.

## Restore the stock firmware

1. Connect the panel the same way as for the backup, with IO0 connected to GND.
2. Write the backup to the start of the flash:

    ```bash
    esptool --port <PORT> --baud 115200 write-flash 0 nspanel_stock.bin
    ```

3. Reassemble the panel and power it up.
4. Install the original Sonoff TFT if you have it. Without it, the stock firmware runs but the display keeps
   the NSPanel HAUI interface.

If you restore the stock firmware and later change your mind, flash NSPanel HAUI again. The display TFT is
installed by the hub after the panel reconnects; see [Installation](install.md#flash-the-panel).
