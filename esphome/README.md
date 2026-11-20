# ESPHome Device Configuration

This directory contains the ESPHome configuration for the NSPanel HAUI device firmware.
Most users flash the prebuilt `nspanel_haui.bin` from the release instead of building it
(see the [Installation Guide](../docs/user/install.md)); the steps below build your own
and need ESPHome 2026.11 or later.

## Quick Start

1. Copy `secrets.yaml.example` to `secrets.yaml` (git-ignored) and fill in your WiFi credentials, passwords, and API keys.
2. Copy `install.yaml` and set the substitution values for your device.
3. Compile and flash with ESPHome Dashboard or CLI:

   ```bash
   esphome run install.yaml
   ```

## Main Config vs Dev Config

| File | Purpose |
|------|---------|
| `nspanel_haui.yaml` | Production config. Uses `$variable` placeholders filled by `install.yaml`. Overrides the stock Nextion component with the vendored `nextion_patch/` (git source) — see below. |
| `nspanel_haui_dev.yaml` | Development config. Hardcoded substitutions, but still reads `!secret` values from `secrets.yaml`. Defaults to the TFT on GitHub; hub-managed installs send their own URL. Uses the local `nextion_patch/` override. |
| `nspanel_haui_universal.yaml` | Universal prebuilt image. Baked documented credentials (no `secrets.yaml`), `name_add_mac_suffix: true` for unique device names/APs, and no fixed Wi-Fi — provisioned over its open access point. Uses the local `nextion_patch/` override. Compiled by `release.yml` into the `nspanel_haui.bin` release asset. |

All three entry points share the component list in `nspanel_haui/packages.yaml`.
Keep the vendored Nextion override until the TFT upload retry fix is in a
released ESPHome: the patch is 2026.11.0 plus only that fix, because 2026.11.0
already ships the numeric-response delivery and TFT upload TX buffer fixes. See
the [removal checklist](nextion_patch/README.md).

The ESPHome web server is **optional and disabled by default**: `base.yaml`
leaves `web_server` out so the HTTP OTA path has flash and RAM headroom. The dev
config enables it for diagnostics; to get the web UI in your own build, add a
top-level `web_server:` block to your device YAML (see `docs/develop/esphome.md`).


## Script Organization

Scripts are split into five category files in `nspanel_haui/`:

| File | Scripts | Purpose |
|------|---------|---------|
| `scripts_event.yaml` | 5 scripts | Publish events to HA via the ESPHome native API |
| `scripts_connection.yaml` | 3 scripts | Hub connection lifecycle (connect, disconnect, heartbeat) |
| `scripts_display.yaml` | 5 scripts | Display control (brightness, page navigation, display off/on) |
| `scripts_interaction.yaml` | 3 scripts | Touch handling, gesture recognition |
| `scripts_common.yaml` | 7 scripts | Sound playback, notifications, component queries, activity suspension and TFT upload |

Script IDs are globally scoped in ESPHome - cross-file `id(script).execute()` references work seamlessly.

For nextion display assets (TFT file, HMI source, fonts, images), see the [`nextion/`](../nextion/README.md) directory.