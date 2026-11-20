# Vendored `nextion` component patch

Temporary vendored copy of the ESPHome `nextion` display component. It carries one fix that is not upstream yet.

## Why this exists

`Nextion::upload_first_chunk_sent_` is set after the first 4096-byte chunk and
never reset, but a successful upload reboots the ESP. A failed upload therefore
leaves it set, and the next `upload_tft()` in the same boot requests the whole
file as its first range. When the display answers the first 4 KB with `0x08` and
offset 0 (no skip), the code jumps past the end and stops after 4 KB with
`Invalid range end`; a non-zero resume offset hides the bug. `upload_tft()` now
clears the flag when an upload starts.

ESPHome 2026.11.0 already ships the two fixes this directory used to carry, so
they are no longer patched: numeric-response delivery ([esphome/esphome#17744])
and the TFT upload TX buffer option ([esphome/esphome#21435]) that
`display.yaml` uses (`tft_upload_http_buffer_size_tx: 2048`).

## What this directory contains

The `nextion/` subdirectory is exactly the stock component at the `2026.11.0` tag **plus** the TFT upload retry fix — nothing else. Both `nextion_upload_esp32.cpp` and `nextion_upload_arduino.cpp` clear `upload_first_chunk_sent_` when `upload_tft()` starts.

Every other file is byte-identical to the released tag, so the component stays
API-compatible with the ESPHome version pinned in `requirements-esphome.txt`.

Upstream license: ESPHome is MIT/GPL-3.0 dual-licensed (see upstream
`LICENSE`); keep the upstream copyright and license notices intact when
modifying these files.

## Removal condition

Delete this directory **and** the `external_components` blocks that reference it
the moment a released ESPHome contains the retry fix. **Status 2026-11-20:** the
fix is not upstream yet (both the 2026.11.0 tag and current `dev` still never
reset `upload_first_chunk_sent_`), so it has to be filed and merged first. Then
bump `min_version` in `esphome/nspanel_haui/base.yaml` and the pin in
`requirements-esphome.txt` to that release in the same change.

[esphome/esphome#17744]: https://github.com/esphome/esphome/pull/17744
[esphome/esphome#21435]: https://github.com/esphome/esphome/pull/21435
