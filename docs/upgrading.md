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

1. Update the **integration** first (Marketplace or zip) and restart Home Assistant.
2. Then flash the matching firmware **and** TFT together, as released.

The firmware and the hub exchange event names, so a mismatched pair (new
integration + old firmware, or vice versa) publishes events the other side no
longer understands. After updating the integration, the display installs the
matching TFT automatically on first connect (or asks, depending on
`auto_install`), but the firmware binary itself must be flashed for this first
upgrade. After that the hub's **HAUI Firmware** update entity installs later
firmware releases (see
[Firmware updates moved to the integration](#11-firmware-updates-moved-to-the-integration)).

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
| `send_notification_with_timeout` | `send_notification` (the ESPHome action no longer accepts a timeout; use the HA service for optional auto-dismiss) |
| `send_notification_persistent` | `send_notification` with `persistent: true` |
| `send_notification_persistent_with_timeout` | `send_notification` with `persistent: true`; use the HA service if it also needs a timeout |

Optional variables on the ESPHome `send_notification` action are `persistent`
(bool; loops the alert sound) and `text_size` (`"auto"` or a font size 1–3).
The integration service `nspanel_haui.send_notification` separately supports an
optional `timeout` from 1–3600 seconds. Its countdown begins when the
notification is queued, including while it waits to be shown; omit the field or
set it to `0` to keep it until dismissed. Standard `notify` entities and the
ESPHome action do not expose a timeout. The `nspanel_haui.notification` event
includes the notification's `timeout` value (seconds, or `null` when unset).
See [Services](services.md#nspanel_hauisend_notification) for details.

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

1. **Update the integration** (Marketplace → install the release, or copy
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

Restore a Home Assistant backup from before the update (the Marketplace does
not downgrade an integration) or copy the previous integration folder back, and
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
- **The buzzer stops before a TFT upload, a firmware update or a reboot.** A
  playing tune no longer keeps one note sounding through the transfer or the
  boot. Flash the updated ESPHome firmware to activate this fix.
- **Firmware auto-update ships the display and firmware together.** The hub
  reads the firmware manifest independently of the TFT version, then installs
  an available firmware update first. The device reboots into the new firmware
  and then installs the matching TFT on the next connect. A TFT upload that is
  already running is never interrupted: the firmware install waits for it to
  finish. Automatic firmware installs are disabled by default; enable **Auto-install
  firmware updates** in the device editor to allow unattended installs. The
  Device Manager's **Install firmware** action remains available either way. The first
  firmware with the `install_firmware_url` action (0.4.3) must still be flashed
  manually — older firmware cannot be updated by the hub.

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

## 10. TFT install actions moved to the integration

Installing the display TFT is now an integration feature:

- Each linked panel gets a **HAUI Display** update entity
  (`update.<device>_haui_display`). It shows the installed TFT and the TFT the
  firmware needs; **Install** installs it.
- `nspanel_haui.update_tft` takes an optional `url` to install a custom or
  development TFT file.

The firmware drops the matching public pieces. After flashing the new firmware:

| Removed | Use instead |
|---------|-------------|
| Action `esphome.<device>_upload_tft` | `nspanel_haui.update_tft` |
| Action `esphome.<device>_upload_tft_url` in automations | `nspanel_haui.update_tft` with `url` |
| Substitution `tft_update_url_portrait` | nothing — the hub picks the portrait TFT by the device's display model |

`esphome.<device>_upload_tft_url` itself still exists: the hub uses it to hand
the TFT URL to the device. Calling it directly works but bypasses the hub's
install tracking. A leftover `tft_update_url_portrait` in your device YAML is
ignored and can be deleted.

The **Update Display** button (`button.<device>_update_display`), removed in
0.4.3, is back in 0.4.5 but disabled by default. It installs the TFT without
the hub's tracking, so prefer **Install** on `update.<device>_haui_display`.

The new firmware also fixes TFT installs from GitHub releases, which failed
with `HTTP_CLIENT: Out of buffer` (see
[Troubleshooting](troubleshooting.md#firmware-updates-work-tft-installs-stay-installing-and-then-time-out)).
Update the firmware first; the TFT follows after the reboot.

## 11. Firmware updates moved to the integration

The **HAUI Firmware** update entity now belongs to the integration, next to
**HAUI Display**. The firmware no longer declares an update entity of its own;
on the ESPHome side only the ESPHome integration's stock **Firmware** entity
(for the ESPHome dashboard) remains.

- The hub reads the release's `firmware-manifest.json` itself and installs a
  newer firmware through the firmware's `install_firmware_url` action —
  automatically with `firmware_auto_update`, or with **Install** on the entity.
- **Build variants are never crossed.** The release manifest names its variant
  (`"variant": "universal"`); the device reports the one it runs
  (`firmware_variant` in the state: `custom` for `install.yaml`/dev builds).
  The hub only offers, lists or installs a release whose variant matches the
  panel's, and treats both unknowns as incompatible, so a custom build is
  never flashed the public universal image. Custom builds update through
  **Install firmware → From URL**.
- The manifest is a device setting: **Firmware manifest URL** in the device
  editor's Updates section (`update.firmware_manifest_url`, see
  [Device settings](configuration/device.md#updates)) replaces the
  `firmware_manifest_url` substitution. A leftover substitution in your device
  YAML is ignored and can be deleted.

What happens depends on the firmware the panel runs when you update the
integration:

| Panel firmware | What to do |
|----------------|------------|
| 0.4.4 and later | Nothing: the hub installs the new firmware through `install_firmware_url`. |
| 0.4.3 | Flash **once** by hand: firmware 0.4.3 does not report its build variant yet, and the hub withholds the release image from panels with an unknown variant (a custom 0.4.3 build must not be silently replaced by the universal one). Use the ESPHome dashboard, or the editor's **Install firmware → From URL** with a release `nspanel_haui_ota.bin`. After the reboot the panel reports its variant and the hub can update it again. |
| 0.4.2 | The hub cannot install firmware on it — 0.4.2 has no `install_firmware_url` action. Press **Install** once on the firmware's own ESPHome entity (`update.<device>_haui_firmware`), or flash the new firmware through ESPHome. |
| 0.4.1 and older | Flash the new firmware through ESPHome, as before. |

**Entity id.** While the panel still runs firmware with its own **HAUI
Firmware** entity, that entity holds `update.<device>_haui_firmware` and Home
Assistant registers the hub's entity as `update.<device>_haui_firmware_2`.
ESPHome removes its entity once the panel reboots into the new firmware; the
next Home Assistant restart renames the hub's entity to
`update.<device>_haui_firmware`, so automations keep working.

**Test panels.** A panel that follows
[local test releases](release.md#test-firmware-updates-with-a-local-release)
through the `firmware_manifest_url` substitution needs its **Firmware
manifest URL** set to the same URL in the device editor before you update the
integration — or turn off **Auto-install firmware updates** for it. Otherwise
the hub reads the GitHub manifest and installs a newer release over the test
build.

## 12. Display TFT updates come from the firmware manifest

The display TFT is now part of the firmware's update path: every release
manifest carries a `tft` block (version + per display model asset), and the
**HAUI Display** entity, the automatic TFT check and **Install TFT** read it
instead of looking up a matching GitHub release.

- **The editor's TFT picker lists only the manifest's TFT** (the one the
  firmware needs) plus **From URL**. Installing another release's TFT by
  version (`nspanel_haui.update_tft` with `version`, or
  `update.install` with `version`) is no longer possible — install a
  different TFT from a URL instead.
- **A manifest without a `tft` block needs no display update.** A local test
  release (`scripts/dev_release.py`) names no TFT: the **HAUI Display** entity
  then reports the installed TFT and offers nothing, instead of erroring with
  "No GitHub release …; TFT not updated"; the display simply keeps the TFT it
  has. Dev prereleases ship their TFTs and name them like a stable release.
- **Version comparisons now match Home Assistant.** The hub compares versions
  with the same rules as Home Assistant's update entities, so the offered
  firmware and the entity agree. A final release is offered over its dev
  builds (`0.4.5` over `0.4.5.dev3`), and a firmware that reports an
  unparseable version (for example an old `dev-<run>-<sha>` local build tag)
  is withheld as unknown instead of being offered as an update on every check.
  Rebuild such a panel with a parseable version (a release tag, or a
  next-patch `X.Y.(Z+1).devN` build). Dev builds published before 2026-11-04
  carry a `+g<sha>` segment that Home Assistant sorts above the final release
  and above later dev builds: install a newer build once by hand (**Install
  firmware** with its version; in the Marketplace, **Install another version**),
  then updates are
  offered normally.
- **New device setting:** `firmware_update_channel` (`stable`/`dev`) in the
  editor's Updates section picks the manifest when the URL is empty — the
  latest stable release, or the newest dev prerelease. An explicit
  **Firmware manifest URL** still overrides it.

## 13. Native OTA is encrypted with the API key

The firmware's native OTA platform (wireless installs from ESPHome) is now
encrypted with the API key instead of protected by a password, so the
`ota_password` substitution and secret are gone. Panels on HAUI 0.4 firmware
need nothing: their firmware already accepts the encrypted upload. Panels on
older firmware need one wireless install with a migration block, and a
`password:` on the `ota: platform: esphome` block of your own YAML now fails
validation. See
[ESPHome Component → Encrypted native OTA](esphome.md#encrypted-native-ota).

## 14. The Current Page sensor moved to the firmware

The firmware now provides the **Current Page** sensor; the integration's
sensor platform is gone. The value is still the Nextion page name the display
shows (`grid`, `weather`, `light`, …), and it no longer turns unavailable while
the hub is disconnected, because it comes from the display.

- The integration's old sensor stays in the entity registry as unavailable.
  Delete it under **Settings → Devices & services → Entities**, so the
  firmware's entity can take `sensor.<device>_current_page`; if the firmware
  connected first, rename its `..._current_page_2` entity back.
- The `panel`, `type` and `title` attributes are gone. Automations that read
  them trigger on the `nspanel_haui.page_changed` event instead, which carries
  the same fields (see [Services → HA Events](services.md#ha-events-automation-triggers)).

## 15. Home Assistant 2026.11 and the Marketplace

NSPanel HAUI now requires **Home Assistant 2026.11** or later (`hacs.json`
declares it). That release replaces HACS with the built-in
[Marketplace](https://www.home-assistant.io/integrations/marketplace/), and the
install docs describe only the Marketplace.

- **Update Home Assistant first.** On 2026.10 or older, the update to this
  release is not offered.
- **Installed through HACS:** nothing to do. Home Assistant migrates HACS on
  the first start of 2026.11; NSPanel HAUI stays installed as a custom
  repository and keeps receiving updates. Its update entity keeps its name,
  area and labels.
- **Development builds:** the HACS beta toggle is now the repository's
  **Pre-release** switch (**Settings → Devices & services → Marketplace**,
  NSPanel HAUI's device page; the entity is disabled by default).
- **Rolling back:** the Marketplace does not downgrade. Restore a backup
  instead of installing an older version.
- **Fresh install:** add `happydasch/nspanel_haui` under **Settings →
  Marketplace → Add from link**; adding a custom repository needs a GitHub
  connection. See [Installation](install.md#3-step-install-hub-app).

## 16. Unused firmware actions and events removed

The firmware drops actions and events that the hub never called or listened
to. Panels work as before; only automations that used them directly need a
change after flashing the new firmware:

| Removed | Use instead |
|---------|-------------|
| Action `esphome.<device>_haui_discover` and its `esphome.haui_discover` event | nothing — the integration finds panels through the ESPHome device registry |
| Action `esphome.<device>_req_device_info` and its `esphome.res_device_info` event | `esphome.<device>_req_device_state`: its `esphome.res_device_state` event also carries `yaml_version`, `tft_required_version` and `firmware_variant` |
| Action `esphome.<device>_req_reconnect` | `esphome.<device>_hub_connection_closed`, which does the same |
| Events `use_relay_left` / `use_relay_right` (`esphome.nspanel_event`) | a state trigger on `switch.<device>_use_relay_left` / `switch.<device>_use_relay_right` |

## 17. Cycle cards are off by default

Clock and weather panels now show only the time in their big time area until
more cycle cards are enabled. Clock panels cycled the date and outside
temperature by default before, so a clock panel that never changed these
options stops cycling after the update.

- To keep the old rotation, open the clock panel in the editor and turn on
  **Show date** and **Show outside temperature** in the **Cycle cards**
  section. A panel that already set them keeps its cards.
- Weather panels behave as before: they show the time and date until you
  enable more cards (see [Weather panel](panels/panel_weather.md#cycle-cards)).
