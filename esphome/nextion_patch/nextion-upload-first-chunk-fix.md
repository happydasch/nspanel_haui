# Nextion TFT upload retry fix (`upload_first_chunk_sent_`) — plan

Status 2026-11-06: patch applied in the vendored component, uncommitted (the user
commits). Tests, lint and the docs build pass, and the firmware compiles (ESP-IDF).
Not tested on hardware yet. Nothing filed upstream yet.

The first version of this fix (earlier on 2026-11-06) disappeared from the working tree
along with the other unstaged changes; this is a re-application of the same change.

## The bug

`Nextion::upload_first_chunk_sent_` is `false` at boot, set to `true` after the first
4096-byte chunk and never reset. A successful upload reboots the ESP, so only a failed
upload leaves it set. The next `upload_tft()` in the same boot then requests the whole
file as its first range. If the display answers the first 4 KB with `0x08` and offset 0
(no skip), the code jumps past the end and stops after 4 KB with
`Invalid range end: <size-1>, size: 0`. With a non-zero skip offset the retry still
completes (it continues from the offset), so the bug only shows with offset 0.

- **Reproduced 2026-11-06** by compiling the real `nextion_upload_esp32.cpp` (HEAD and
  patched) against stubs with a simulated range-capable server and display (harness in
  the session scratchpad, not kept). Unpatched, offset 0: the retry logs
  `Range: bytes=0-12787`, `Recv: [08.00.00.00.00]`, `Invalid range end: 12787, size: 0`,
  on every retry until a fresh boot. Patched: the retry sends `bytes=0-4095` and
  completes. Unpatched, offset 8192: the retry completes.

- **Origin:** upstream, #6576 (ESP-IDF) and #6582 (Arduino), 2024, when the flag started
  choosing the first range. Not introduced by this repo; our hub's TFT installs are what
  retry in the same boot.
- **Upstream state (checked 2026-11-06):** ESPHome `dev` at `6bb7850ed5` still has the
  bug in both files. No issue or PR covers it.

## Done

- `esphome/nextion_patch/nextion/nextion_upload_esp32.cpp`,
  `esphome/nextion_patch/nextion/nextion_upload_arduino.cpp`: `upload_tft()` sets
  `this->upload_first_chunk_sent_ = false;` right after `is_updating_ = true`.
- `tests/test_esphome_yaml.py`: `test_every_tft_upload_starts_with_the_4k_first_chunk`
  (source-level: the reset must come before the first `upload_by_chunks_()` call in
  both files). It failed before the patch and passes now.
- `esphome/nextion_patch/README.md`: third patch listed; removal condition now needs a
  released ESPHome with #17744, #21435 **and** this fix.
- The removal condition elsewhere points to the README's list instead of naming
  #17744 + #21435: `esphome/nspanel_haui/base.yaml`, `esphome/nspanel_haui.yaml`,
  `requirements-esphome.txt`, `AGENTS.md` (`esphome/` row), `docs/develop/esphome.md` (which
  also gained the missing #21435).
- `CHANGELOG.md` (0.4.5, Fixed): one line.
- Checks: `pytest tests/` (1247 passed), `ruff check`, `zensical build --strict`,
  `esphome compile nspanel_haui_universal.yaml` (ESPHome 2026.10.0, local
  `nextion_patch`). The Arduino file is not compiled by any of our configs (ESP-IDF
  only). `nspanel_haui_dev.yaml` stops at config validation on this machine: the
  local `secrets.yaml` has an `ap_password` shorter than 8 characters.

## Next steps

1. **Hardware retest** on a test panel (steps below). Fill in the PR's test environment.
2. **File the upstream issue** (bug report draft written 2026-11-06, follows ESPHome's
   issue form; it needs the log from step 5 of the retest).
3. **Open the upstream PR** below and link the issue.
4. **After upstream merges:** name the PR in `esphome/nextion_patch/README.md`. The
   patch directory goes once a released ESPHome has all three fixes. If 2026.11.0
   ships #17744 and #21435 without this fix, keep the patch: rebase it on 2026.11.0
   with only this fix, or accept the bug and delete it.

## Hardware retest

On a panel running firmware built from this checkout, with `nextion.upload` logging at
VERBOSE (the range header is a VERBOSE line):

1. Serve the TFT from a server without `Range` support:
   `python3 -m http.server 8000` in `nextion/`.
2. Call the ESPHome action `upload_tft_url` with
   `http://<host>:8000/nspanel_haui.tft`. Expected failure:
   `Server does not support range requests (got 200 at offset 4096)`.
3. Turn the panel's **Screen Power** switch off and on (the entity is disabled by
   default) to take the display out of upload mode. Do not reboot the ESP.
4. Call `upload_tft_url` with a URL that supports `Range` (the GitHub release TFT, or
   the file under Home Assistant's `/local/`).
5. **Expected with the patch:** the first request logs `Range: bytes=0-4095` and the
   upload completes and reboots the panel. **Without the patch** (control): the first
   request logs `Range: bytes=0-<size-1>` and the upload stops after 4 KB with
   `Invalid range end` and `TFT upload error`. Keep this log for the issue. The control
   only shows the bug when the display answers `Recv: [08.00.00.00.00]`; if it logs
   `New range: …` (a non-zero skip offset), the unpatched retry completes and the run
   proves nothing.

## Draft upstream PR (not filed)

**Title:** `[nextion] Reset first-chunk flag at the start of every TFT upload`

### What does this implement/fix?

`Nextion::upload_first_chunk_sent_` starts as `false`. `upload_by_chunks_()` sets it to
`true` after the first 4096-byte chunk (ESP32 and ESP8266) and nothing ever resets it.
After a successful upload the ESP reboots, so the bug only shows after a **failed**
upload. Every later `upload_tft()` in the same boot then sees the flag still set:

1. The first range request is `bytes=0-<tft_size-1>` instead of `bytes=0-4095`.
2. If the display answers the first 4096 bytes with `0x08` and offset 0 (no skip), the
   code sets `range_start = range_end + 1`, which is the file size.
3. The next `upload_by_chunks_()` call fails with `Invalid range end: <size-1>, size: 0`
   and the upload ends after 4 KB with `TFT upload error` (`Upload error` on ESP8266).
   The display is left in upload mode until it is power-cycled, and every further retry
   fails the same way until the ESP reboots, as long as the display answers offset 0.

With a non-zero skip offset the retry still works: the code jumps to the offset, so the
only cost is a first request for the whole file that is closed after 4 KB.

This PR clears the flag in `upload_tft()` when an upload starts, in both
`nextion_upload_esp32.cpp` and `nextion_upload_arduino.cpp`.

### Steps to reproduce

1. Start a TFT upload that fails after the first chunk. For example, serve the file
   from a server that ignores `Range`: the ESP32 variant logs
   `Server does not support range requests (got 200 at offset 4096)`.
2. Power-cycle the display (not the ESP), fix the cause and call `upload_tft()` again.
3. The upload stops after 4 KB with `Invalid range end` (with VERBOSE logs on, the
   range header shows `bytes=0-<size-1>`). A reboot of the ESP clears it.

*Hardware log: add the control run from the retest (step 5). No device log of the
failure exists yet.*

### Types of changes

- [x] Bugfix (non-breaking change which fixes an issue)

### Test environment

- [ ] ESP32 — *fill in after the hardware retest*
- [ ] ESP8266 — not tested (same one-line change)

### Diff (both files)

```cpp
   this->connection_state_.is_updating_ = true;
+  // Every upload starts with the 4096-byte chunk the display answers with its resume offset.
+  // A failed upload leaves the flag set; a retry in the same boot would then request the
+  // whole file as its first chunk and stop after 4 KB.
+  this->upload_first_chunk_sent_ = false;
```

## Related upstream bugs seen in passing (not fixed)

- Latent, not reachable today: `upload_tft()` returns `false` when
  `set_protocol_reparse_mode(false)` fails, but `is_updating_` is already `true`, so
  every later call would log `Upload in progress` until the ESP reboots.
  `set_protocol_reparse_mode()` sets `ignore_is_setup_` before sending, so
  `send_command_()` cannot fail and it always returns `true`. Not worth an issue on its
  own.
- ESP32: the `status_code != 200 && != 206` path returns without
  `esp_http_client_cleanup()` and leaks the HTTP client on every attempt (reachable: a
  TFT URL that answers 404). The `Set GET failed` path has the same leak but is
  practically unreachable.
