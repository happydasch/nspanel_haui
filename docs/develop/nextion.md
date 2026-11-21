---
title: Nextion component
description: "The display component in the firmware: config options, rendering, refresh and its scripts"
---

# Nextion component

The firmware drives the Nextion display and the hub renders panels through it. Read this page when you change the display configuration or the render cycle, or when you need to know which HMI script writes what.

## The component in the firmware

The firmware uses the stock ESPHome `nextion` display component (ESPHome 2026.11 or later) over a hardware UART, with the temporary vendored patch in `esphome/nextion_patch/`. The hub never sees the UART: it calls the device actions listed in [ESPHome component](esphome.md), and the firmware writes the Nextion commands.

## Display configuration

### Dimensions and non-visible area

| Area | Landscape | Portrait |
|------|-----------|----------|
| Display and touch resolution | 480 × 320 px | 320 × 480 px |
| Visible area | 450 × 320 px | 320 × 480 px |
| Hidden by the bezel | 30 px on the right (x 450..479) | none |

Touch coordinates in the hidden band are valid; no pixels are visible there. Edge gestures depend on it: `esphome/nspanel_haui/scripts_interaction.yaml` takes `visible_width` (450 in landscape, 320 in portrait) for its right-border check with a 40 px `border_margin`, so in landscape a swipe starting at x > 410 counts as a right-edge start and touches in the hidden band count too.

### Display options

These live in `esphome/nspanel_haui/display.yaml`:

| Option | Value | Effect |
|--------|-------|--------|
| `uart_id` | `haui_uart` | the UART bus the display is on |
| `wake_up_page` | `0` | page shown after *hardware* sleep. The display state machine never hardware-sleeps: it keeps System page 0 visible and dims the backlight, so this only matters if hardware sleep is requested explicitly |
| `tft_url` | `$tft_update_url` | compile-time default TFT URL, overridable per device YAML; the hub always passes the URL of the TFT it installs. The component's validation also requires it next to `tft_upload_http_buffer_size_tx` |
| `tft_upload_http_buffer_size_tx` | `2048` | HTTP TX buffer for the TFT download: GitHub redirects release TFTs to a signed URL of about 870 characters, and the ESP-IDF default of 512 fails with `HTTP_CLIENT: Out of buffer` |
| `max_queue_size` | `800` | caps the command queue so a Nextion buffer overflow cannot strand entries and fragment the heap; 800 absorbs a full panel render plus concurrent state updates |
| `max_commands_per_loop` | `50` | commands processed per loop iteration, spreading allocation and deallocation; with pacing active the pacer limits output further |
| `command_spacing` | `2ms` | enables the command pacer globally. The ESP32 loop timestamp is constant within an iteration, so at most one queued command leaves per loop, which spreads large renders and keeps bursts out of the Nextion's 1 KB RX buffer |
| `on_setup`, `on_page`, `on_touch` | — | triggers after the firmware connects to the display, on a page change, and on a touch |
| `on_buffer_overflow` | — | logs the warning and publishes a `buffer_overflow` event, which starts [buffer overflow recovery](#buffer-overflow-recovery) |

## Panel rendering and refresh

The HA layer batches commands to keep the native API payload small, ESPHome queues them and the `command_spacing` pacer writes them to the UART. The pacer, not HA batching, is what protects the Nextion's 1 KB RX buffer.

A panel render has two paths:

- **Full render** (`display_panel`): initial display, panel switches and the page-load path. Resets the command-dedup cache, so the first batch is never dropped as a duplicate of the previous page.
- **Refresh** (`refresh_panel`): re-runs `render_panel` on the active panel for entity state changes, clock ticks and overflow recovery, with no page transition.

```mermaid
flowchart TD
    Event{What triggered<br/>the render?}

    Event -->|Page switch /<br/>initial display| Full[Full Render - display_panel]
    Event -->|Entity state change /<br/>clock tick| Refresh[Refresh - refresh_panel]

    Full --> Cache[Reset command-dedup cache]
    Cache --> Goto[Send goto_page command]
    Goto --> Ack{0x66 ack<br/>received?}
    Ack -->|Yes| Settle[Wait page_settle_delay]
    Ack -->|Timeout 10s| Fallback[Force-resend page command<br/>and render anyway]
    Settle --> Render[render_panel - full display commands]
    Fallback --> Render

    Refresh --> RenderDirect[render_panel - incremental<br/>display commands]

    RenderDirect --> Batch[Batch and send via send_commands]
    Render --> Batch
    Batch --> Done[Done]

    style Full fill:#4ba6ee,color:#fff
    style Refresh fill:#f09d37,color:#fff
```

### Page acknowledge and settle delay

The Nextion answers a page change with a 0x66 ack once the new page is active, and the hub waits for it before rendering: commands that arrive earlier are rejected with "Invalid variable name" (0x1A) because the page's components are not initialised yet. After the ack the hub waits `page_settle_delay` (default `0.1` s) and then calls `display_panel`. If no ack arrives within 10 s (`PAGE_ACK_TIMEOUT`), it force-resends the page command and renders anyway.

### Buffer overflow recovery

A Nextion buffer overflow (0x24) loses every instruction that was in flight, so the display shows a mix of stale and updated widgets. The hub debounces a `refresh_panel()` after `OVERFLOW_RECOVERY_DELAY` (0.5 s), doubling the delay for each consecutive overflow and pausing recovery after `OVERFLOW_RECOVERY_MAX_ATTEMPTS` (5) until the display has been overflow-free for `OVERFLOW_RECOVERY_RESET` (30 s). Recovery re-renders the active panel instead of switching pages, so its batch is smaller than the one that overflowed. The constants and the handler are in `haui/controller/navigation.py`.

## Editing the HMI

The HMI holds the interface design and only the page-scoped logic that must run on the display; everything else belongs to the hub. The rules that keep both HMIs in step are in [Nextion Editor](nextion-editor.md#the-hmipython-contract).

- Every page sends `sendme` in `Preinitialize`: it is how a page change becomes an `esphome.page` event, and a page without it is never rendered.
- Prepare the page in `Preinitialize`, because the hub cannot touch the display before the page is shown. What the page needs at load time arrives in the globals the hub sets before the switch: the theme colours in `Program.s` for solid-colour pages, and the picture background of the clock and weather pages.
- Enable `Send Component ID` on any widget whose touch the hub must receive.
- The hub addresses a widget by id and object name from the page's `COMPONENTS` registry, so reordering components changes their ids.

The walkthrough for the editor itself — widgets, pages, fonts, images, the portrait project — is [Nextion Editor](nextion-editor.md).

## Scripts for display

The display tools live in `scripts/` (index in `scripts/README.md`) and run as modules from the repository root.

| Script | Writes | Run it | Guards it |
|--------|--------|--------|-----------|
| `python -m scripts.hmi_layout.gen_layout`, `--spec portrait` | the spec's geometry and attributes into the HMI, and the sibling's `sendkey` values | after a change to `landscape_layout.py` or `portrait_layout.py` | `--check` compares spec and HMI, including widget coverage across both |
| `python -m scripts.hmi_layout.gen_virtual_layout` | `frontend/virtual/layout_<orientation>.json`, `icon_map.json`, the preview pictures (WebP) and `haui/mapping/font_metrics.json` | after every HMI change | `--check` (in the suite) fails while any of them is stale; it also verifies every solid page's theme code |
| `python -m scripts.hmi_layout.gen_virtual_layout --theme-code <page>` | the `Preinitialize` theme code of one page | when a page's theme code must be pasted or refreshed | same `--check` |
| `python -m scripts.check_preview_coverage` | — | after adding a panel type | `tests/test_preview_coverage.py` |
| `python -m scripts.nextion2text.Nextion2Text -i <hmi> -o <dir> -d -s -p visual` | a text dump per page: widgets with ids and names, event code and visual properties | when you map widgets to `COMPONENTS` | — (read-only; `build/` is git-ignored) |
| `python -m scripts.bump_tft_version` | `system.tftVersion` in both HMIs | with a release that ships new TFTs | `tests/test_bump_version.py` and the release manifest |
| `python -m scripts.design_grid.gen_grid` | `nextion/images/grid_landscape.png`, `grid_portrait.png`, the editor-only design grid | after a layout rule or theme colour changes | import them into both projects by hand |
| `python -m scripts.backgrounds.gen_backgrounds` | `nextion/images/bkg/landscape/`, `bkg/portrait/` | after a source picture in `nextion/src_images/bkg/` changes | import them by hand |
| `python -m scripts.spinner.gen_spinner` | `spinner_<orientation>_1.png`, `_2.png` (pictures 11 and 12) | after the `system` tile changes or `hSpinner` moves | `gen_virtual_layout --check` fails while the timer's `xpic` ids point elsewhere |
| `python -m scripts.charset.gen_char`, `scripts/font_tools/` | `charout.txt`, the `.zi` fonts, `docs/cheatsheet.html` | when the icon set or a font size changes | `make generated-check` fails while the cheatsheet is stale |
| `python -m scripts.rgb565_image.image_convert`, `python -m scripts.color_wheel.gen_color_wheel` | a `pixelData~` string, an HSV colour wheel picture | for ad-hoc assets | — |

`make hmi-check` runs the layout, generated-asset and preview-coverage guards in one go; `make screens-check` compares the docs screen images with a fresh render.

