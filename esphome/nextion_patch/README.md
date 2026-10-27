# Vendored `nextion` component patch

Temporary vendored copy of the ESPHome `nextion` display component, used to
close a regression between released ESPHome versions.

## Why this exists

The numeric-response delivery fix for the stock `nextion` component
([esphome/esphome#17744], commit `fbe4699ad4`, "Properly deliver numeric
responses") was merged two days **after** the 2026.10.0 release tag was cut
(2026-10-20 vs 2026-10-22), so *no released ESPHome contains it*.  Without the
fix the display's numeric replies (`0x71`) are matched against whatever command
sits at the front of the UART queue, so every read response logs
`Numeric return but '…' invalid type 0` and is thrown away: `page`/`dim`
errors after every user interaction and lost `res_val`/`res_txt`/TFT-version
reads.

The fix commit itself does not compile against the 2026.10.0 core because it
sits on top of then-unreleased codegen refactors (`cg.add_optional`,
`display.add_writer`), so pinning `external_components` to it or to `dev` is
not possible.

## What this directory contains

The `nextion/` subdirectory is exactly the stock component at the
`2026.10.0` tag **plus** [esphome/esphome#17744] cherry-picked on top —
nothing else.  `nextion.cpp`/`nextion.h` carry the fix (`deliver_queue_response_`,
`is_raw_get_command`, `RAW_GET_NAME`); every other file is byte-identical to
the released tag, so the component stays API-compatible with the ESPHome
version pinned in `requirements-esphome.txt`.

Upstream license: ESPHome is MIT/GPL-3.0 dual-licensed (see upstream
`LICENSE`); keep the upstream copyright and license notices intact when
modifying these files.

## Removal condition

Delete this directory **and** the `external_components` blocks that reference
it the moment a released ESPHome contains #17744 (2026.11.0).  Then bump
`min_version` in `esphome/nspanel_haui/base.yaml` and the pin in
`requirements-esphome.txt` to that release in the same change.

[esphome/esphome#17744]: https://github.com/esphome/esphome/pull/17744
