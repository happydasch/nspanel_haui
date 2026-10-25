
# NSPanel HAUI (HomeAssistant UI)

NSPanel HAUI is a Home Assistant custom integration for Sonoff NSPanel devices.
It replaces the stock firmware with a configurable display system built on ESPHome.

## Features

- Multiple configurable panel types (light, climate, cover, media, etc.)
- Touch gestures and sequences
- Live state updates via ESPHome native API
- Configurable dimming, sleep, and wake behavior
- Pin-code locking
- Full device configuration through the HA UI

## Installation

1. Flash the NSPanel with the ESPHome firmware (the prebuilt `nspanel_haui.bin` from the release)
2. Install this integration via HACS
3. Add the integration through Home Assistant UI
4. Add the panel in the NSPanel HAUI editor; the display TFT installs automatically

See the [README](https://github.com/happydasch/nspanel_haui/blob/master/README.md) for full documentation.
