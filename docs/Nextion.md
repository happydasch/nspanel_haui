# Nextion Component

[README](../README.md) | [Documentation](README.md) | [Installation](Install.md) | [Configuration](Config.md) | [Panels](panels/README.md) | [FAQ](FAQ.md)

- [Nextion Component](#nextion-component)
  - [Installation](#installation)
  - [How to edit the HMI file](#how-to-edit-the-hmi-file)
  - [Display dimensions and non-visible area](#display-dimensions-and-non-visible-area)
  - [Scripts for display](#scripts-for-display)

## Installation

To install the TFT file on the display, the device needs to be already flashed with ESPHome.

The device will provide a button `Update Display` in the device settings. There are also services
available.

- **Using a button**:

  - Button: `Update Display`
    This will load the TFT file from the URL configured on the ESP.

- **Using a service**:

  - Service: `nspanel_haui_upload_tft`
    This will load the TFT from the configured URL

  - Service: `nspanel_haui_upload_tft_url`
    This will load the TFT from the URL provided to the service.

## Nextion display configuration used in this project

### Display dimensions and non-visible area

The Sonoff NSPanel Nextion display has the following physical touch characteristics:

- **Total display/touch resolution:** 480 × 320 pixels
- **Visible (effective) area:** 450 × 320 pixels
- **Non-visible area:** 30 pixels on the right side (x = 450..479)

The display is 480 pixels wide, but the LCD bezel hides the rightmost 30 pixels. Touch coordinates in that band (x = 450..479) are valid but no pixels are visible there.

This is relevant for edge-based gesture detection — swipe-from-right gestures (swipe left) start in the non-visible zone. The ESPHome gesture logic in `scripts_interaction.yaml` uses the full `screen_w` (480) for its right-border check, which naturally includes the non-visible zone.

This project uses the ESPHome `nextion` display component with a hardware UART and the following key options:

- `uart_id`: references the UART bus used for the Nextion display.
- `wake_up_page`: the page shown when the display wakes up.
- `tft_url`: URL used by `upload_tft` to update the TFT file.
- `on_setup`: triggered after ESPHome connects to the Nextion.
- `on_page`: triggered when the display changes pages.
- `on_touch`: triggered when a touch event happens.
- `on_sleep` / `on_wake`: triggered when the display sleeps or wakes.

The repo also exposes these actions via API:

- `upload_tft`
- `upload_tft_url`
- `send_command`
- `set_brightness`
- `goto_page`

This project also handles Nextion runtime issues such as buffer overflow using the `on_buffer_overflow` automation.
When a buffer overflow is detected, the display logs the warning and publishes a `buffer_overflow` event so the app can react or retry safely.

These match the official ESPHome Nextion component behavior used by the project.

## How to edit the HMI file

To edit the HMI file, no special care is needed. Following are some helpful infos. The HMI is used mostly to design the interface but does not need any special code. Only on a page based lifetime of events should be done on the display. If possible, the logic should be placed in the Hub App.

All pages need to send a `sendme` in `Preinitialize`. This is needed to know of a page change event.

Prepare the page in the `Preinitialize` event because the Hub App cannot control the display at this stage. Only after a page is shown, it is possible to change anything or interact with it.

If you want to process any click events, you need to enable `Send Component ID` on the event to be used.

If you want to interact with any component on the display, the component id and objectname is required. They are being used and are defined in the Hub App.

When changing order of components on a page, be aware, that the id of the components will change.

## Scripts for display

see `scripts` in the root directory for different scripts.

- Font generation
- Image generation
