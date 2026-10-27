# Upgrading to the first stable release

!!! note "Only relevant if you run 0.3.x or earlier"

    This guide covers the breaking changes of the **first stable release**.
    If you are setting up NSPanel HAUI for the first time, follow
    [Installation](install.md) and [Quick Start](get-started.md) instead —
    everything in this guide is already the default for new installations.

The first stable release removes the backward-compatibility layer: saved
settings, service names, ESPHome actions/events and config keys that 0.3.x and
earlier used are **not migrated and not aliased**. The old names appear only in
this guide. The release also stops overloading the word "sleep": the display
idle state (brightness `on` / `dim` / `off`), the Nextion *hardware* sleep, and
the automatic idle page are now named and configured independently.

## 1. Who must read this

You are affected if any of the following applies to you:

- You have saved panel/device settings from **0.3.x or earlier** in the editor.
- Your automations or scripts call the `nspanel_haui.sleep` service.
- Your custom ESPHome YAML uses the actions `display_sleep`,
  `display_wakeup`, or any of the four `send_notification*` actions
  (`send_notification`, `send_notification_with_timeout`,
  `send_notification_persistent`, `send_notification_persistent_with_timeout`).
- Your ESPHome YAML, Node-RED flow or AppDaemon app listens for the events
  `esphome.sleep`, `esphome.wakeup`, or the `esphome.timeout` payload `"sleep"`.
- A dashboard or automation references the entities
  `switch.<device>_use_auto_sleeping` or `number.<device>_timeout_sleep`.

## 2. Before you start

- Back up your HA configuration storage: copy `.storage/nspanel_haui*` (and
  your `configuration.yaml`, if you imported device YAML) somewhere safe.
- Note down any entity ids you reference in dashboards or automations
  (`switch.*_use_auto_sleeping`, `number.*_timeout_sleep` are renamed below).
- Keep the integration, the ESPHome firmware and the Nextion TFT at matching
  versions — update order matters, see below.

## 3. Update order

1. Update the **integration** first (HACS or zip) and restart Home Assistant.
2. Then flash the matching firmware **and** TFT together, as released.

The firmware and the hub exchange event names, so a mismatched pair (new
integration + old firmware, or vice versa) publishes events the other side no
longer understands. After updating the integration, the display installs the
matching TFT automatically on first connect (or asks, depending on
`auto_install`), but the firmware binary itself must be flashed for this first
upgrade. After that the device's `HAUI Firmware` update entity can install later
firmware releases through Home Assistant.

## 4. What changed

### HA services

| Old | New |
|-----|-----|
| `nspanel_haui.sleep` | `nspanel_haui.idle` |

`nspanel_haui.wakeup` is unchanged. The `idle` service does the same thing the
`sleep` service did: open the configured idle page immediately. It is a pure
page switch — it never turns the display off.

### Device config keys and entities

Saved device settings from 0.3.x or earlier are **migrated automatically** the
first time the updated integration starts: the store loader renames the legacy
config keys below in place, saving the migrated values back to the store. A
value you already set under the new key wins; legacy keys are dropped either
way. The migration only covers the keys in the table — anything else you
changed in the editor stays as-is.

| Old key | New key | Old entity | New entity |
|---------|---------|------------|------------|
| `sleep_panel` | `idle_panel` | — | — |
| `sleep_panel_extra` | `idle_panel_extra` | — | — |
| `show_sleep_button` | `show_idle_button` | — | — |
| `use_auto_sleeping` | `use_auto_display_off` | `switch.<device>_use_auto_sleeping` | `switch.<device>_use_auto_display_off` |
| `timeout_sleep` | `timeout_display_off` | `number.<device>_timeout_sleep` | `number.<device>_timeout_display_off` |

The editor labels are **Auto display off** / **Display-off timeout (seconds)**;
the firmware entities are named *Use Auto Display-Off* / *Timeout Display-Off*.
`use_auto_dimming`, `timeout_dimming`, `use_auto_page`, `timeout_page` are
unchanged. The display-off schedule keeps the keys `use_sleep_schedule` /
`sleep_schedule_start` / `sleep_schedule_end` (and the "Sleep schedule" editor
label).

If a dashboard or automation toggled `switch.*_use_auto_sleeping`, point it at
the renamed switch instead — or use the schedule feature the same way as before.

### ESPHome actions

| Old | New |
|-----|-----|
| `display_sleep` | `display_off` |
| `display_wakeup` | `display_on` (new, the off-direction was previously one-way) |

The four notification actions are **one action** now:

| Old | Use instead |
|-----|-------------|
| `send_notification` | `send_notification` (with optional variables, see below) |
| `send_notification_with_timeout` | `send_notification` (timeouts no longer exist — notifications stay until dismissed) |
| `send_notification_persistent` | `send_notification` with `persistent: true` |
| `send_notification_persistent_with_timeout` | `send_notification` with `persistent: true` (timeouts no longer exist) |

Optional variables on `send_notification`: `persistent` (bool; loops the
alert sound until dismissed), `text_size` (`"auto"` or a font size 1-3).

**Notification `timeout` was removed.** Notifications no longer auto-dismiss:
an entry stays in the queue until it is dismissed on the panel, replaced by an
identical title+message, or cleared. The `timeout` field on
`nspanel_haui.send_notification`, the `send_notification` action and the
`nspanel_haui.notification` event is gone — remove it from automations and
scripts. For alerts that must not be missed, use `persistent: true` instead
(it loops the alert sound and re-opens the popup periodically until the
notification is dismissed).

### ESP events

| Old | New |
|-----|-----|
| `esphome.sleep` | `esphome.display_off` |
| `esphome.wakeup` | `esphome.display_on` |
| `esphome.timeout` payload `"sleep"` | payload `"off"` |

`esphome.timeout` payloads `"dim"` and `"page"` and the
`esphome.display_state` payloads `on` / `dim` / `off` are unchanged.

### Removed automatic migrations and shims

- **Saved panels are not migrated.** 0.3.x's automatic `show_forecast` →
  `forecast_type` and `mode` → `show_in_navigation` renames no longer happen on
  load. After updating, verify each weather panel's forecast type and each
  panel's **Show in navigation** setting in the editor; settings that were
  previously auto-fixed may now differ silently.
- **No pydantic fallback.** Pydantic is a hard requirement (it already was,
  via `manifest.json`); validation always runs.
- **YAML import requires a bare `config:` / `panels:` mapping.** Importing a
  YAML file wrapped under the device name is rejected with a 400 error.
- **`[r, g, b]` color strings are no longer accepted** in color values. Use
  `#rrggbb` or an integer.
- **`template:` prefixes are no longer a template marker.** Strings are
  rendered as templates only when they contain bare `{{ ... }}` / `{% ... %}`.
- **`touch_events` argument removed** from `update_function_component`.
- **Vacuum fallback removed.** The vacuum panel no longer reads the deprecated
  `battery_level` / `battery_icon` entity attributes; the battery icon needs a
  configured battery sensor.
- **Log-only `on_sleep` / `on_wake` handlers removed** from the firmware
  display config; the Nextion hardware sleep is still used on the no-hub path
  where it was before.

## 5. How to update

1. **Update the integration** (HACS → reinstall/download the release, or copy
   the folder) and restart Home Assistant.
2. **Re-enter saved settings** in the editor (Device Manager → device): per
   weather panel set the forecast type back, verify **Show in navigation** per
   panel, and re-check colors and notification settings.
3. **Update automations/scripts**: replace `nspanel_haui.sleep` with
   `nspanel_haui.idle` (device targeting is unchanged). Update any references
   to the renamed switches/numbers.
4. **Update custom ESPHome YAML**: `display_sleep` → `display_off` (add
   `display_on` where the wake action is needed), consolidate the notification
   actions into `send_notification` with optional variables, and update event
   listeners (`esphome.display_off` / `esphome.display_on` /
   `esphome.timeout` → `off`).
5. **Update dashboards/cards** that referenced the two renamed config entities.
6. **Flash the matching firmware + TFT** together, then verify.

## 6. Verification checklist

- `nspanel_haui.idle` opens the idle page; `nspanel_haui.wakeup` still wakes.
- Automatic page switching opens the idle page **without** turning the display
  off, and display-off happens after its own timeout **without** requiring a
  page — the two behaviors are fully independent again.
- Touch/button wake works with and without a configured idle page.
- The no-hub hardware sleep/wake path (device without a hub connection) still
  blanks and wakes the display, and `esphome.display_off` / `esphome.display_on`
  are the events you see.
- Saving a device or panel in the editor applies without a reload error, and
  YAML import rejects a `config:`/`panels:`-less root.

## 7. Rollback

Pin the previous integration version (e.g. in HACS, reinstall 0.3.2) and
restore the storage backup from step 2. The old firmware and TFT must match
the old integration — restore those versions too before reconnecting the
device.

## 8. Update behaviour changes

The automatic update logic changed in this release. Review these points before
upgrading:

- **Empty `tft_version` is treated as unknown.** The hub's boot handshake reads
  the display's version about 1 second after boot, before the display answered.
  An empty value is no longer parsed as `0.0.0` (which caused an automatic
  reinstall after every reboot). Instead, the hub requests a fresh device state
  and only acts on a known version. This is fail-safe: if the device does not
  answer the refresh request, no automatic install starts. Use **Install TFT**
  in the editor to install manually.
- **A recent unconfirmed install is not auto-retried.** When an install cannot
  be confirmed (the device does not report the new version within its timeout),
  the hub reports an error and stops. It will not retry automatically; press
  **Install TFT** in the editor to start a fresh attempt. This prevents a
  display that cannot report its version from being uploaded to forever.
- **`INSTALLING` survives the reboot.** The TFT upload ends in an ESP32 reboot,
  so the disconnect is expected. The state stays `installing` until the device
  reconnects and reports the new version (→ `done`) or the verification window
  times out (→ `error`). A matching version reported on reconnect confirms the
  install; a timeout shows the reason in the editor.
- **Failed installs report why.** The editor shows a toast when the upload
  command could not be sent or when the update state ends in `error`. The REST
  API returns HTTP 502 for a failed install instead of a silent success.
- **The buzzer stops before a TFT upload starts.** A playing tune no longer
  sounds until the reboot. Flash the updated ESPHome firmware to activate this
  fix.
- **Firmware auto-update ships the display and firmware together.** When a newer
  release exists and the device reports an installable firmware update through
  its `HAUI Firmware` entity, the hub triggers the firmware install first. The
  device reboots into the new firmware and then installs the matching TFT on the
  next connect. A TFT upload that is already running is never interrupted: the
  firmware install waits for it to finish. Set `firmware_auto_update: false` to
  keep the previous notice-only behaviour. The first firmware that contains this
  feature must still be flashed manually — the `HAUI Firmware` entity only exists
  in the new firmware, so an older firmware cannot be updated by the hub.

## 9. Web server is no longer enabled by default

The shipped firmware no longer runs the ESPHome **web server**. It costs flash
and RAM that the HTTP OTA path (TLS, JSON, `http_request`) needs to fit next to
the display stack. What changes when you flash the new firmware:

- The device's web UI on port 80 disappears, and Home Assistant's **Visit**
  link for the device disappears with it.
- The web server was never part of the HAUI protocol — the hub, the editor and
  the TFT install path all use the ESPHome native API — so nothing else breaks.

To keep the web UI, add the component to *your own* device YAML (the file that
includes `nspanel_haui.yaml` as a package) before flashing:

```yaml
web_server:
  port: 80
  auth:
    username: admin
    password: !secret web_password
```

`esphome/nspanel_haui_dev.yaml` keeps the web server for local development. See
[ESPHome Component → Web server](esphome.md#web-server-optional).

