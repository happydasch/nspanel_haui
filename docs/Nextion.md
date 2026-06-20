# Nextion Component

[README](../README.md) | [Documentation](README.md) | [Installation](Install.md) | [Configuration](Config.md) | [Panels](panels/README.md) | [FAQ](FAQ.md)

- [Nextion Component](#nextion-component)
  - [Installation](#installation)
  - [How to edit the HMI file](#how-to-edit-the-hmi-file)
  - [Display dimensions and non-visible area](#display-dimensions-and-non-visible-area)
  - [Panel rendering and refresh](#panel-rendering-and-refresh)
  - [Advanced queue tuning options](#advanced-queue-tuning-options)
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

### Advanced queue tuning options

These options are set in `esphome/nspanel_haui/display.yaml` and are not needed for normal use.

- `max_queue_size` (default: 800): caps the command queue to prevent heap fragmentation when the Nextion serial buffer overflows and orphans pending entries. 800 entries is enough to absorb a full panel render burst plus concurrent state updates.

- `max_commands_per_loop` (default: 50): limits commands processed per loop iteration to spread out allocation/deallocation. When `command_spacing` is active this cap is redundant (pacer already limits to 1 cmd/loop), so it only matters with spacing disabled.

- `command_spacing` (default: `0`, disabled): minimum gap between commands sent to the Nextion display. When set to a non-zero duration (e.g. `2ms`), the pacer sends at most 1 command per loop iteration, keeping only 1 command in flight on UART at a time and preventing RX buffer overflow on slower Nextion panels. The ESP32 loop runs at ~3–5ms under this workload, giving ~200–330 commands/sec at `2ms` spacing. Leave at `0` for maximum throughput. Enable only if you observe buffer overflows or display glitches under heavy load.

The repo also exposes these actions via API:

- `upload_tft`
- `upload_tft_url`
- `send_command`
- `set_brightness`
- `goto_page`

This project also handles Nextion runtime issues such as buffer overflow using the `on_buffer_overflow` automation.
When a buffer overflow is detected, the display logs the warning and publishes a `buffer_overflow` event so the app can react or retry safely.

These match the official ESPHome Nextion component behavior used by the project.

### Panel rendering and refresh

Commands are batched at the HA layer and sent as a single `send_commands` service call, keeping only one in-flight payload on the UART at a time and preventing the Nextion's 1 KB RX buffer from overflowing. This is the primary protection against display corruption under heavy load.

The rendering cycle has two paths:

- **Full render** (`display_panel`): used for initial page display, panel switches, and overflow recovery. Resets the command-dedup cache so the first batch is never suppressed as a duplicate of the previous page.
- **Refresh** (`refresh_panel`): used for incremental updates (entity state changes, clock ticks, etc.). Re-runs `render_panel` on the already-active panel without a page transition.

#### Page settle delay

After a page-change command the Nextion sends a 0x66 ack once the new page is active. The hub waits for this ack before sending render commands — commands arriving before the ack are rejected with "Invalid variable name" (0x1A) because page components are not yet initialised.

After the ack the hub waits an additional settle delay (default `0.1s`, configurable via `page_settle_delay`) before calling `display_panel`. If the ack never arrives within `page_timeout` (default 10s), the hub force-resends the page command and renders anyway as a fallback.

#### Buffer overflow recovery

If the Nextion reports a buffer overflow (0x24), the hub debounces a full `display_panel` re-render with a 500ms delay to let the ESPHome queue drain any remaining commands before re-sending the complete panel state. This is a safety net — normal operation should not trigger overflows given the HA-layer batching.

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
