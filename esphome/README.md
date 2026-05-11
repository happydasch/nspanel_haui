# ESPHome Device Configuration

This directory contains the ESPHome configuration for the NSPanel HAUI device firmware.

## Quick Start

1. Copy `secrets.yaml` and fill in your WiFi credentials, passwords, and API keys.
2. Copy `install.yaml` and set the substitution values for your device.
3. Compile and flash with ESPHome Dashboard or CLI:

   ```bash
   esphome run install.yaml
   ```

## Main Config vs Dev Config

| File | Purpose |
|------|---------|
| `nspanel_haui.yaml` | Production config. Uses `$variable` placeholders filled by `install.yaml`. Includes patched Nextion component. |
| `nspanel_haui_dev.yaml` | Development config. Hardcoded substitutions (no secrets needed). Points TFT update URL at `homeassistant.local:8123`. No patched component - uses bundled ESPHome Nextion. |

## Script Organization

The monolithic `script.yaml` has been split into 5 category files for maintainability:

| File | Scripts | Purpose |
|------|---------|---------|
| `scripts_event.yaml` | 6 scripts | Publish events to HA via the ESPHome native API |
| `scripts_connection.yaml` | 3 scripts | Hub connection lifecycle (connect, disconnect, heartbeat) |
| `scripts_display.yaml` | 6 scripts | Display control (brightness, page navigation, sleep/wake) |
| `scripts_interaction.yaml` | 4 scripts | Touch handling, gesture recognition, page timeouts |
| `scripts_notification.yaml` | 6 scripts | Sound playback, notifications, component queries |

Script IDs are globally scoped in ESPHome - cross-file `id(script).execute()` references work seamlessly.

For nextion display assets (TFT file, HMI source, fonts, images), see the [`nextion/`](../nextion/README.md) directory.