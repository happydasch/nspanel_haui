---
title: Upgrading
description: Breaking changes per released version, the manual flash old firmware needs, and how to roll back
---

# Upgrading

Every released version that broke an existing installation is listed below with the keys, entities, actions and versions to change. Read the section for the version you come from before installing a newer one; the regular steps are in [Updating](../user/update.md). Keep the integration, the firmware and the TFT at matching versions: the firmware and the hub exchange event names, so a mismatched pair publishes events the other side does not understand. [Rollback](#rollback) applies whenever an upgrade has to be undone.

| You come from | Read |
|---------------|------|
| 0.3.x or earlier | 0.3.x → 0.4.0, then every later section, plus Older firmware |
| 0.4.0 – 0.4.4 | 0.4.5, then 0.5.0, 0.5.2 and 0.5.3, plus Older firmware |
| 0.4.5 | 0.5.0, then 0.5.2 and 0.5.3 |
| 0.5.0 – 0.5.1 | 0.5.2, then 0.5.3 |
| 0.5.2 | 0.5.3 |

## Breaking changes by version

### 0.3.x → 0.4.0

The first stable release removes the backward-compatibility layer: settings, action names, ESPHome actions and events from 0.3.x and earlier are not migrated and not aliased, except the five device keys below. It also stops overloading "sleep": the display idle state, the Nextion *hardware* sleep and the automatic idle page are named and configured separately.

Before you start:

- Back up `.storage/nspanel_haui*` (and your `configuration.yaml`, if you imported device YAML).
- Note the entity ids your dashboards and automations use: two are renamed.
- Keep the integration, the firmware and the TFT at matching versions.

| Changed | What to do |
|---------|------------|
| Action `nspanel_haui.sleep` is `nspanel_haui.idle`, which opens the configured idle page immediately and never turns the display off; `nspanel_haui.wakeup` is unchanged. | Rename the action in automations and scripts. |
| Device keys `sleep_panel`, `sleep_panel_extra`, `show_sleep_button`, `use_auto_sleeping`, `timeout_sleep` become `idle_panel`, `idle_panel_extra`, `show_idle_button`, `use_auto_display_off`, `timeout_display_off`. The store loader renames them in place on the first start; a value already under the new key wins and the legacy key is dropped. | Nothing; only these keys are migrated. Other editor settings stay as they are. |
| Entities `switch.<device>_use_auto_sleeping` and `number.<device>_timeout_sleep` become `switch.<device>_use_auto_display_off` and `number.<device>_timeout_display_off`; editor labels are **Auto display off** / **Display-off timeout (seconds)**, firmware entities *Use Auto Display-Off* / *Timeout Display-Off*. `use_auto_dimming` and `timeout_dimming` are unchanged. | Point dashboards and automations at the new entity ids. |
| Automatic page switching: `use_auto_page` and `timeout_page` stay device settings. The firmware's *Use Auto-Page* switch and *Timeout Page* number go with 0.4.5, when the hub takes automatic page switching over. | Nothing here; the 0.4.5 rows cover the entity cleanup. |
| ESPHome actions `display_sleep` and `display_wakeup` become `display_off` and `display_on` (waking used to be one-way). | Rename them in your device YAML and add `display_on`. |
| The four notification actions `send_notification`, `send_notification_with_timeout`, `send_notification_persistent` and `send_notification_persistent_with_timeout` are one `send_notification` with optional `persistent` (loops the alert sound) and `text_size` (`"auto"` or 1–3). Auto-dismiss is the action's `timeout` (1–3600 seconds, counted from queueing); `notify` entities and the ESPHome action take no timeout, and the `nspanel_haui.notification` event carries `timeout` (seconds or `null`). | Call `send_notification`, with `persistent: true` for the persistent variants; use the action when it needs a timeout, see [Actions](../user/actions.md#nspanel_hauisend_notification). |
| ESP events `esphome.sleep` and `esphome.wakeup` become `esphome.display_off` and `esphome.display_on`, and the `esphome.timeout` payload `"sleep"` becomes `"off"`. The `"dim"` / `"page"` payloads and the `esphome.display_state` payloads `on` / `dim` / `off` are unchanged. | Update the event listeners in your YAML. |
| Saved panels are not migrated: the 0.3.x renames `show_forecast` → `forecast_type` and `mode` → `show_in_navigation` no longer happen. | Verify both settings per panel in the editor. |
| Validation always runs (no pydantic fallback). YAML import needs a bare `config:` / `panels:` mapping and rejects a file wrapped under the device name; `[r, g, b]` colors are rejected (use `#rrggbb` or an integer); only bare `{{ ... }}` / `{% ... %}` render (`template:` is not a marker). | Fix the imported file and its colors, then re-import. |
| `touch_events` is removed from `update_function_component`; the log-only `on_sleep` / `on_wake` handlers are removed (the Nextion hardware sleep still serves the no-hub path); the vacuum fallback is removed, so the battery icon needs a configured battery sensor and `battery_level` / `battery_icon` are ignored. | Drop those keys from your YAML and configure the battery sensor. |

Update in this order:

1. Update the **integration** (Marketplace or zip) and restart Home Assistant.
2. Flash the matching firmware **and** TFT together, as released. This first upgrade needs the firmware binary by hand; later releases come from **HAUI Firmware**.
3. Re-enter the saved settings (forecast type per weather panel, **Show in navigation**, colors, notifications), rename the action and entities, and update your ESPHome YAML.
4. Verify: `nspanel_haui.idle` opens the idle page and `nspanel_haui.wakeup` still wakes; automatic page switching opens the idle page without turning the display off, and display-off happens after its own timeout without a page switch; touch and button wake work with and without an idle page; the no-hub path still sleeps and wakes with `esphome.display_off` / `esphome.display_on`; saving a device or a panel applies without an error, and YAML import rejects a `config:`/`panels:`-less root.

A fresh installation follows [Installation](../user/install.md) and [Quick Start](../user/get-started.md); everything above is already its default.

### 0.4.5

| Changed | What to do |
|---------|------------|
| An empty `tft_version` means **unknown**, not `0.0.0` (which re-installed the TFT on every reboot). The hub requests a fresh device state and acts only on a known version; no answer, no install. | Nothing. Read `tft_version` only from the device-state event. |
| An install the display never confirms is an error and is not retried automatically. | Retry with **Install** beside **Display (TFT)** in the **Updates** sidebar. |
| `installing` survives the reboot: it stays until the device reconnects with the new version (`done`) or the verification window times out (`error`). | Nothing. |
| A failed install raises a toast, and the REST API answers HTTP 502 instead of a silent success. | Check the response in a script that calls the API. |
| A playing buzzer tune stops before a TFT upload, a firmware update or a reboot. | Nothing. |
| Firmware installs come first and the matching TFT follows after the reboot; a running TFT upload is never interrupted. Automatic firmware installs are off by default, while manual installs from the **Updates** sidebar work either way. | Nothing; firmware 0.4.3 needs one manual flash first, see [Older firmware](#older-firmware). |
| The shipped firmware no longer runs the ESPHome **web server**: the web UI on port 80 and Home Assistant's **Visit** link disappear. The hub, the editor and the TFT install path all use the native API. | Add the component to *your own* device YAML before flashing (below); `esphome/nspanel_haui_dev.yaml` keeps it for local development. See [ESPHome Component → Web server](esphome.md#web-server-optional). |
| TFT installs belong to the integration: **HAUI Display** (`update.<device>_haui_display`) and `nspanel_haui.update_tft` (optional `url`). | Install the TFT from that entity or action. |
| The action `esphome.<device>_upload_tft` and the **Update Display** button (`button.<device>_update_display`) are gone. The substitution `tft_update_url_portrait` is ignored (delete it), and `tft_update_url` stays for local TFT builds. | Use `nspanel_haui.update_tft`. `esphome.<device>_upload_tft_url` still exists for the hub to hand the URL to the device, so calling it directly bypasses the hub's install tracking. |
| TFT installs from GitHub releases failed with `HTTP_CLIENT: Out of buffer` before this firmware. | Install the firmware first; the TFT follows after the reboot. See [Troubleshooting](../user/troubleshooting.md#firmware-updates-work-tft-installs-stay-installing-and-then-time-out). |
| **HAUI Firmware** belongs to the integration, next to **HAUI Display**; the firmware declares none, leaving only the stock **Firmware** entity for the ESPHome dashboard. The hub installs through the firmware's `install_firmware_url` action from `firmware-manifest.json`. | 0.4.4 and later: nothing. 0.4.3: flash **once** by hand — it reports no build variant, so the hub withholds the image — through the ESPHome dashboard, or **Install** beside **Firmware** → **From URL** with a release `nspanel_haui_ota.bin`. 0.4.2: the hub cannot install firmware; press **Install** once on the firmware's own `update.<device>_haui_firmware`, or flash through ESPHome. 0.4.1 and older: flash through ESPHome. |
| Build variants are never crossed: the manifest names its own (`"variant": "universal"`), the device reports the one it runs (`firmware_variant`: `custom` for `install.yaml` and dev builds), and two unknown variants count as incompatible so a custom build is never flashed the public image. | Custom builds update through **Install** beside **Firmware** → **From URL**. |
| While a panel still runs firmware with its own **HAUI Firmware** entity, that entity holds `update.<device>_haui_firmware` and the hub's is registered as `update.<device>_haui_firmware_2`; ESPHome removes its entity after the reboot and the next Home Assistant restart renames the hub's back. | Nothing; automations keep working. |
| A panel following a local test release (a manifest written by `scripts/dev_release.py`) through the `firmware_manifest_url` substitution got its manifest from there; the hub now reads the channel. | Set the same **Custom manifest URL** in the device editor before you update the integration (or **Install firmware updates automatically** off), or the hub installs a newer release over the test build. |
| The TFT is part of the firmware's update path: every manifest carries a `tft` block (version and per display model asset), read by **HAUI Display**, the automatic TFT check and the picker. | Nothing; the manifest is the single TFT source. |
| The picker lists only the manifest's TFT plus **From URL** and **From local file**, so another release's TFT cannot be installed by version, and a manifest without a `tft` block needs no display update. | Dev prereleases name their TFTs like a stable release; a local test release names none, so **HAUI Display** reports the installed TFT and offers nothing. |
| Version comparison follows Home Assistant: `0.4.5` is offered over `0.4.5.dev3`, an unparseable version (an old `dev-<run>-<sha>` tag) is withheld as unknown, and a `+g<sha>` segment sorts above the final release and later dev builds. | Rebuild a panel whose version does not parse; install a newer build once by hand (the **Updates** sidebar, or **Install another version** in the Marketplace) when a `+g<sha>` build is stuck, then updates resume. |
| New device setting `firmware_update_channel` (`stable` / `dev`) picks the manifest when the URL is empty. | Choose the channel; an explicit **Custom manifest URL** still overrides it. |
| Native OTA is encrypted with the API key instead of protected by a password: the `ota_password` substitution and secret are gone, and a `password:` on `ota: platform: esphome` in your own YAML fails validation. | Panels on 0.4 firmware need nothing. Older firmware needs one wireless install with a migration block, see [ESPHome Component → Encrypted native OTA](esphome.md#encrypted-native-ota). |
| The **Current Page** sensor comes from the firmware as the Nextion page name (`grid`, `weather`, `light`, …); it no longer turns unavailable while the hub is disconnected, and the `panel`, `type` and `title` attributes are gone. | Delete the old integration sensor under **Settings → Devices & services → Entities** so the firmware's entity can take `sensor.<device>_current_page` (if the firmware connected first, rename its `..._current_page_2` back). |
| The firmware's **Current Page** and the new **Current Page Number** are disabled by default, and its page changes come as the `nspanel_haui.page_changed` event. | Enable the entity on the panel's ESPHome device page and read the event instead of the attributes (see [Actions → HA Events](../user/actions.md#ha-events-automation-triggers)). |
| **Home Assistant 2026.11** is the minimum, declared in the Marketplace metadata; the built-in [Marketplace](https://www.home-assistant.io/integrations/marketplace/) replaces HACS, and the HACS beta toggle is the repository's **Pre-release** switch (disabled by default). | Update Home Assistant first: on 2026.10 or older this release is not offered, and the Marketplace does not downgrade. |
| An installation that came through HACS keeps working. | Nothing: Home Assistant migrates it on the first 2026.11 start as a custom repository, with the entity's name, area and labels kept. Fresh install: add `happydasch/nspanel_haui` under **Settings → Marketplace → Add from link** (needs a GitHub connection, see [Installation](../user/install.md#install-the-integration)). |
| The firmware drops the actions and events the hub never used: `esphome.<device>_haui_discover` and its `esphome.haui_discover` event, `esphome.<device>_req_device_info` and its `esphome.res_device_info` event, `esphome.<device>_req_reconnect`, and the events `use_relay_left` / `use_relay_right` (`esphome.nspanel_event`). | Panels work as before; automations that used them directly switch to `esphome.<device>_req_device_state` (its `res_device_state` also carries `yaml_version`, `tft_required_version` and `firmware_variant`), `esphome.<device>_hub_connection_closed`, or a state trigger on `switch.<device>_use_relay_left` / `switch.<device>_use_relay_right`. Discovery comes from the ESPHome device registry. |
| Clock and weather panels show only the time in their big time area until more cycle cards are enabled, so a clock panel that never changed the options stops cycling the date and the outside temperature. | Turn on **Show date** and **Show outside temperature** under **Cycle cards**; a panel that already set them keeps them, and weather panels behave as before (see [Weather panel](../user/panels/panel_weather.md#cycle-cards)). |
| The `nspanel_haui` actions raise an error when their `device` matches no running panel, where they logged a warning and did nothing. | An automation that names a disabled panel, a removed panel or another integration's device stops at that step. Select the panel's **NSPanel HAUI** or ESPHome device (see [Actions](../user/actions.md#navigation-display-control)), and set `continue_on_error: true` for a step that may target a disabled panel. |
| Automatic page switching belongs to the hub: it checks `use_auto_page` and `timeout_page` once per second against its interaction clock. A timeout that passes while a page holds automatic switching opens the idle page on the next check after the hold ends, unless an interaction has since reset the clock; a reconnect starts the timeout again after the restored page is displayed. `hub_idle_timeout` is removed and there is no fallback timer. | Update the integration first, then install the matching firmware from **HAUI Firmware** (the TFT follows after the reboot); mixed hub and firmware releases are unsupported. |
| The firmware's **Use Auto-Page** switch, **Timeout Page** number and `esphome.timeout` event with the `page` payload are gone, with no firmware replacement. | Delete the orphaned entities and update automations that listened for that event. |
| Notification `type` (`info`, `warning`, `critical`) is replaced by `icon_color` and `sound`: `type: info` is `icon_color: ""` (the theme's text colour) with `sound: notification`, `type: warning` is `icon_color: "#f69d31"` with `sound: notification`, and `type: critical` is `icon_color: "#4aa5ee"` with `sound: alert`. | Pass `icon_color: ""` and `sound: "notification"` in custom YAML that calls the action to keep the old `info` behaviour, or `sound: "alert"` for the old `critical` sound. |
| `icon_color` takes `#rrggbb`, an RGB565 number, `[r, g, b]` or an integer string. `sound` is any `play_sound` name (`startup`, `tone`, `tone_up`, `tone_down`, `seq_up`, `seq_down`, `notification`, `alert`, `alert_fast`, `elise`) or `none`, and defaults to `notification`. | Any of them works; the mapping on the row above only recreates the old presets. |
| The `nspanel_haui.notification` event carries `icon_color` and `sound` instead of `notif_type`, and the ESPHome `send_notification` action requires both variables. A panel still running a build without them sends the old payload, which the hub accepts with the theme's text colour and `notification`. | Update the event listeners and the custom YAML that calls the action. |
| A persistent notification forces its popup open on every path, including the ESPHome action, and re-opens over the idle page; a schedule entry with sound off still keeps the display dark, and the `critical`-only idle guard is gone. | Nothing; the [preset notification script](../user/actions.md#preset-notification-script) recreates the old `info`/`warning`/`alert`/`critical`/`silent` combinations for existing automations. |

To keep the ESPHome web server, add this to the device YAML that includes `nspanel_haui.yaml` as a package before flashing:

```yaml
web_server:
  port: 80
  auth:
    username: admin
    password: !secret web_password
```

### 0.5.0

| Changed | What to do |
|---------|------------|
| `schedule` replaces the Day/Night profiles and the quiet hours: a list of entries, each with a window (`start` and `end`: `HH:MM`, or `sunrise` / `sunset` shifted by `start_offset` / `end_offset` minutes) and the settings `sound`, `brightness`, `display_off` and `timeout_display_off`. Outside every entry the device's normal settings apply. | Add the entries again in the device settings; see [Schedule](../user/editor/device.md#schedule). |
| The stored `day_night_*`, `day_*`, `night_*`, `use_do_not_disturb` and `quiet_hours_*` settings are ignored, and nothing is converted. | Set **Brightness** under **Screen** and recreate the windows as schedule entries. |
| `brightness` is a new device setting (default empty): the full brightness outside the schedule. Empty leaves the panel's **Brightness Full** number alone, and a schedule requires a value; with a value the hub writes the number on every sync, so a change made on the panel's Settings page lasts until the next connect or schedule boundary. | Set it whenever you use a schedule. |
| The Night profile's dimming timeout, dim ramp, dimmed brightness, automatic page switching, page timeout and idle panel are gone, and so are the Day profile's adopted brightness values. | Dimming and the idle page always follow the device settings. |
| While `schedule` has entries the hub owns the **Use Auto Display-Off** switch: it writes the active entry's `display_off`, or `use_auto_display_off` outside every entry, on every sync. Without entries the switch belongs to its live state, and the save that removes the last entry writes `use_auto_display_off` to it once. | Nothing. |
| Sun boundaries use Home Assistant's sunrise and sunset of the current day plus the boundary's offset, read when the hub evaluates the schedule; the hub arms one timer for the next boundary instead of listening for sun events. | Nothing. |
| The firmware clamps the dim target to the full brightness, so an entry whose brightness is below **Brightness Dimmed** does not brighten the display when it dims. | Install the matching firmware from the panel's **HAUI Firmware** entity. |
| Custom themes live in one library shared by every device of the hub; a device selects its theme with `theme_id`, and panels can select a library theme of their own. A YAML export carries the selected custom theme as `theme_definition`. | Add the custom palette to the theme library and select it; see [Themes](../user/editor/themes.md). |
| Per-device `color_overrides` and `theme_overrides` are no longer read, and hand-written config must use `theme_id`. | Nothing is converted: recreate the palette as a library theme. |
| The **Device Colors** sidebar is the **Theme** sidebar (the **Theme** button of **Manage this device** on the device's Preview), and the Appearance section is gone from device settings. | Use the Theme sidebar; panel and item colour settings are separate and unchanged. |

### 0.5.2

| Changed | What to do |
|---------|------------|
| A schedule entry may set `brightness_dim`, but 0.5.0 accepted that while the device's `brightness_dim` was empty, so the hub had no value to write when the entry ended and the panel kept the entry's dimmed brightness. `validate_device_config` refuses an entry with `brightness_dim` while the device's is empty, as it refuses a schedule without `brightness`. | Set `brightness_dim` on the device: `PanelStorage.load` sets it to 20 once (the firmware's initial **Brightness Dimmed**) and logs a warning, and the **Schedule** group saves the panel's **Brightness Dimmed** reading (20 when there is none) with the schedule. |
| `Theme.variant` follows the theme's own page background (`background_variant()` in `haui/mapping/color.py`): the light-background icon colors for **Light**, **White**, **Sky** and any custom theme with a light page, the dark-background ones for the rest. `ThemeLibrary` takes no variant, and a page with a fixed picture background still passes its own variant. `theme_variant` is gone from `DEVICE_CONFIG`, the device-config model and the editor's defaults (`PanelStorage.load` drops the stored key once, and the editor and the Theme sidebar send `theme_id` only); the **Theme variant** switch is gone with it. | Nothing. The Theme sidebar's **Icon colors** section edits the palette the theme draws (`themeIconVariant()` in `frontend/theme-library.js`, mirroring the hub's rule) and has no palette picker; a custom theme still stores both palettes, because a page with a fixed picture background uses the other one. |

### 0.5.3

| Changed | What to do |
|---------|------------|
| Clock, ClockTwo and Weather: `background` names a picture compiled into the display — `dark`, `light`, `modern`, `spring`, `summer`, `autumn`, `winter`, `dog_1`, `dog_2` or `cat` — instead of a color scheme. `scheme` is no longer a choice, because those pages could never draw the theme's background: `background_choice()` in `haui/page/clock_common.py` falls back to the theme's fill (`theme.background_variant()`) and logs a warning for a value that is not a picture. | Pick **Background** in the panel editor: **Dark Color** (the default), **Light Color** or a decorative picture ([Background pages](../user/update.md#background-pages-draw-a-picture)). |
| Dashboard card: `mode` is `fleet` or `device` and `display_mode` is `big`, `small` or `status`. A saved `overview`, `home`, `live` or `tile` card keeps the view it named, `devices` is dropped, and `focus_mode` is deleted from the card config. | Nothing for a saved card. A new card sets `mode` and `display_mode` ([Dashboard Card](../user/dashboard-card.md)). |
| REST: `/api/nspanel_haui/panel_templates` is gone with the editor's **Start from a template** list, which was its only caller. | Nothing unless a script called it; a panel starts from its type, a built-in popup or a copy of an existing panel ([The Panel List](../user/editor/panels.md#panel-list)). |
| `req_connection` and `res_device_state` carry `hub_api_version` (`1.0` in `esphome/nspanel_haui/version.yaml`, mirrored by `HUB_API_VERSION` in `haui/version.py`). The hub compares the major part, logs a `WARNING` on a mismatch and reports `hub_api_compatible` in the device status; firmware that does not report the field stays compatible. | Nothing. Install the panel's firmware from its **Updates** sidebar when the log warns ([Version compatibility](../user/version-compatibility.md#firmware-contract-version)). |
| Grid tiles: an item that is on takes its background and its power-button color from the selected theme on every render. A quick start used to write those colors into the panel, which pinned the tiles to the theme the setup was created in — after a theme change an on tile stayed a dark tint under a light page's dark text. The store loader clears a stored `back_color`/`power_color` that is one of the built-in themes' values and keeps a color you picked yourself. | Nothing; the tiles follow the theme ([Panel Grid](../user/panels/panel_grid.md#colors)). |

## Older firmware

Panels below 0.4.4 need one manual flash before the hub can update them:

| Panel firmware | What to do |
|----------------|------------|
| 0.4.3 | It can install firmware but reports no build variant, so the hub offers it nothing. Flash it once with **From URL** (a release's `nspanel_haui_ota.bin` for the universal image, your own build for a custom one), or through ESPHome. |
| 0.4.2 and older | It cannot install firmware from the hub. Flash the current firmware once through ESPHome. |

After that one manual flash the hub updates a universal panel itself, and a custom panel continues as in [Custom firmware](update-process.md#custom-firmware).

## Rollback

1. Restore a Home Assistant backup from before the update; the Marketplace does not downgrade. Copying the previous integration folder back works too.
2. Restore the storage backup you took before upgrading (`.storage/nspanel_haui*`, and your `configuration.yaml` if you imported device YAML).
3. Restore the matching firmware and TFT before you reconnect the device: the old firmware and TFT must match the old integration.
