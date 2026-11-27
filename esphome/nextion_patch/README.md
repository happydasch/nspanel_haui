# Vendored `nextion` component patch

Temporary vendored copy of the ESPHome `nextion` display component. It carries two local changes that are not upstream yet.

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

The `nextion/` subdirectory is exactly the stock component at the `2026.11.0` tag **plus** the upload fixes — nothing else:

- `upload_first_chunk_sent_` is cleared when `upload_tft()` starts, in both `nextion_upload_esp32.cpp` and `nextion_upload_arduino.cpp`.
- A failed upload names its cause in `tft_upload_error_` instead of failing silently, and `tft_upload_display_fault()` marks the failures that came from the display's side of the link (a refused upload command, a rejected chunk, a missing acknowledgement). A download, range or heap error is not marked, because another transfer at a lower rate would end the same way — `prepare_tft_upload` in `esphome/nspanel_haui/scripts_common.yaml` retries only the marked ones, once, at 115200 bps.

Every other file is byte-identical to the released tag, so the component stays
API-compatible with the ESPHome version pinned in `requirements-esphome.txt`.

Upstream license: ESPHome is MIT/GPL-3.0 dual-licensed (see upstream
`LICENSE`); keep the upstream copyright and license notices intact when
modifying these files.

## Style

Do not reformat this tree. Upstream's own formatting (import order, wrapped
calls, long message strings such as `NextionName`'s `cv.Invalid` text) differs
from ours, and `[tool.ruff] extend-exclude` in `pyproject.toml` keeps both
`ruff check` and `ruff format` off it, so a diff against the release tag shows
only the patch. A "format on save" editor setting still rewrites the files:
if `git status` shows them modified without a real fix, restore them instead of
committing the churn.

## Removal condition

Delete this directory **and** the `external_components` blocks that reference it
the moment a released ESPHome contains both changes — the retry is worth filing
upstream together with the fault flag, which is what makes a rate change the
caller's decision. **Status 2026-11-20:** the retry is not upstream yet (both the
2026.11.0 tag and current `dev` still never reset `upload_first_chunk_sent_`), so
it has to be filed and merged first; `tft_upload_error_` and
`tft_upload_display_fault()` are this project's, and would have to be filed with
it. Then bump `min_version` in `esphome/nspanel_haui/base.yaml` and the pin in
`requirements-esphome.txt` to that release in the same change.

[esphome/esphome#17744]: https://github.com/esphome/esphome/pull/17744
[esphome/esphome#21435]: https://github.com/esphome/esphome/pull/21435
