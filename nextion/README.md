# Nextion Display Assets

This directory contains display-related assets for the NSPanel HAUI device:

| File / Directory | Purpose |
|------------------|---------|
| `nspanel_haui.tft` | Compiled Nextion display firmware — the UI file installed on the panel's display |
| `nspanel_haui.HMI` | Nextion Editor source project (for customization) |
| `fonts/` | Custom font files used by the display |
| `images/` | Image assets used by the display |

The TFT file is uploaded to the device automatically by the Hub app on first connection, or manually via the ESPHome dashboard's "Upload Display" button.

## ESPHome Configuration

All ESPHome device configuration files (YAML scripts, packages, and build configs) have moved to the [`esphome/`](../esphome/README.md) directory.

For documentation about the ESPHome device configuration see:

- [ESPHome Configuration](../docs/ESPHome.md)
- [`esphome/README.md`](../esphome/README.md)
