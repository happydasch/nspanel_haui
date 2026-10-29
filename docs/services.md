---
title: Services
description: Home Assistant services provided by NSPanel HAUI for display control and device management
---

# Services

NSPanel HAUI registers Home Assistant services for controlling the display,
updating a selected TFT, and managing devices from automations, scripts, or the
Developer Tools panel in the HA UI.

ESPHome also exposes lower-level TFT upload actions for a configured TFT URL or
an arbitrary URL.

## Display Updates

### `nspanel_haui.update_tft`

Install the TFT release matching the selected panel's firmware (`yaml_version`),
another GitHub release (`version`, older ones included), or the TFT file at
`url`. The device is required, so this action cannot
accidentally start a TFT upload on every panel in the hub. The service uses
HAUI's update controller and reports failures in the update state shown in
Device Info, Device Manager and the panel's **HAUI Display** update entity.

| Field | Required | Description |
|-------|----------|-------------|
| `device` | yes | NSPanel device whose display is updated |
| `version` | no | GitHub release to install instead of the one the firmware needs, e.g. `0.4.1`; not combined with `url` |
| `url` | no | http(s) URL of a `.tft` file to install instead of the GitHub release the firmware needs; not combined with `version` |

**Example automation action:**

```yaml
action: nspanel_haui.update_tft
data:
  device: "abc123..."
```

**Install an older release:**

```yaml
action: nspanel_haui.update_tft
data:
  device: "abc123..."
  version: "0.4.1"
```

**Install a custom or development build:**

```yaml
action: nspanel_haui.update_tft
data:
  device: "abc123..."
  url: "http://homeassistant.local:8123/local/nspanel/nspanel_haui.tft"
```

Choose the device in the service's **Device** selector (or pass its device
registry ID as `device` in YAML). A URL install carries no version the hub can
check: it counts as done once the device reboots after the upload and the
display reports its version.

A TFT installed with `version` or `url` stays on the display: the automatic
check does not replace it with the TFT the firmware needs, and the display does
not ask, until the firmware's version changes. The hold lives in memory, so a
Home Assistant restart lifts it and the automatic check then installs the TFT
the firmware needs again (or the display asks first when `auto_install` is
off). Installing without `version` and `url` lifts it too. A TFT that does not
match the firmware may lack pages or components the firmware uses.

### HAUI Firmware update entity

Every linked panel has an `update.<device>_haui_firmware` entity. Its installed
version is the firmware's `yaml_version`, its latest version the one the
firmware manifest names: by default the `firmware-manifest.json` of the latest
GitHub release, or the device's
[`firmware_manifest_url`](configuration/device.md#updates). The hub reads the
manifest on startup, when the URL changes and on every release check.
**Install** runs the same install as `nspanel_haui.update_firmware` without
`version` and `url`: the panel downloads the image, flashes it and reboots,
and the entity shows *installing* until it reconnects. It stays available
while the install keeps the device offline. An install that does not end in a
reboot within ten minutes, or a reboot into the old version, is reported as an
error in the Device Manager. The entity supports a specific version, the same
as `nspanel_haui.update_firmware` with `version`.

When the ESPHome dashboard is set up, the ESPHome integration adds its own
**Firmware** update entity to the device (disabled by default). It recompiles
your device YAML in the dashboard and is independent of the hub's firmware
updates.

### HAUI Display update entity

Every linked panel has an `update.<device>_haui_display` entity next to the
**HAUI Firmware** entity on the same device page. Its installed
version is the TFT the display reports, its latest version the TFT the firmware
needs. **Install** runs the same TFT update as `nspanel_haui.update_tft`
without a URL, and the entity shows *installing* until the display reports the
new version. It stays available while an install keeps the device offline (the
upload blocks the ESP32 and ends in a reboot). When the display has not
reported its version yet, the entity state is unknown; use
`nspanel_haui.update_tft` to force an install. The entity supports a specific
version, so `update.install` installs another release, the same as
`nspanel_haui.update_tft` with `version`:

```yaml
action: update.install
target:
  entity_id: update.nspanel_kitchen_haui_display
data:
  version: "0.4.1"
```

### `nspanel_haui.update_firmware`

Install the firmware update the panel's **HAUI Firmware** entity offers,
another GitHub release (`version`, older ones included), or the firmware OTA
image at `url`. The device is required.

| Field | Required | Description |
|-------|----------|-------------|
| `device` | yes | NSPanel device whose firmware is installed |
| `version` | no | GitHub release to install instead of the offered update, e.g. `0.4.2`; not combined with `url` |
| `url` | no | http(s) URL of a firmware OTA image (`firmware.ota.bin` / `nspanel_haui_ota.bin`); not combined with `version` |

```yaml
action: nspanel_haui.update_firmware
data:
  device: "abc123..."
  version: "0.4.2"
```

Without `version` and `url` the action re-reads the firmware manifest and
installs the offered update, like the entity's own **Install**. Every install
runs the firmware's `install_firmware_url` action, which downloads and flashes
the image itself:

- **Releases:** only releases that ship `nspanel_haui_ota.bin` and
  `firmware-manifest.json` (v0.4.2 and later) install over the air; the hub
  reads the image's md5 from the manifest. A `version` equal to the one the
  manifest offers installs from the manifest, so a test release works too. Older releases ship only the
  factory image (`nspanel_haui.bin`), which an over-the-air update must not
  write — flash those with the ESPHome dashboard or a cable.
- **URLs:** the Home Assistant host downloads the file first to compute the md5
  the flash needs, and refuses a factory image or a file larger than the app
  partition. The panel must reach the URL too.
- **The panel's current firmware needs the `install_firmware_url` action**
  (0.4.3 and later). Flash newer firmware once through ESPHome on a panel that
  runs 0.4.2 or older (see [Upgrading](upgrading.md)).
- **Automatic firmware updates pause** after a release or URL install, so
  `firmware_auto_update` does not reinstall the latest release on the next
  check. The pause lives in memory: a Home Assistant restart or installing the
  offered update ends it.- **Automatic firmware updates pause** after a release or URL install, so
  `firmware_auto_update` does not reinstall the latest release on the next
  check. The pause lives in memory: a Home Assistant restart or installing the
  offered update ends it.
- **Build variants are never crossed.** Only releases whose manifest
  `variant` matches the panel's reported one are offered, listed in the
  editor's firmware picker, or installed by `version`. A panel built from
  `esphome/install.yaml` (variant `custom`) is therefore refused the public
  universal release image; flash custom builds with `url` (see
  [Firmware build variants in the device Updates section](configuration/device.md#updates)).

Installing older firmware leaves the TFT alone: the automatic TFT check treats
a newer TFT as up to date. Install the matching TFT with
`nspanel_haui.update_tft` and `version` when you go back a release.

---

## Navigation & Display Control

These six services are registered under the `nspanel_haui` domain. The
`device` field is optional for these navigation and notification services; when
it is omitted, they apply to all HAUI-connected devices. `update_tft` and
`update_firmware` are separate and require selecting one device, so an install
cannot accidentally start on every panel. The selector is filtered to NSPanel HAUI
devices.

### `nspanel_haui.open_panel`

Navigate the display to a specific panel by its **panel key** (the identifier
shown in the panel editor).  The panel opens through the navigation controller,
so the full render pipeline runs (goto_page, page ack, settle, set_panel).
Navigation history, popups, and lock state are honored.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device` | no | all devices | Target NSPanel device (from device registry) |
| `panel` | yes | — | Panel key to open (e.g. `"alarm"`, `"grid_2"`, `"climate_living"`) |
| `wakeup` | no | `false` | If `true`, wakes the display before opening the panel |

**Example automation action:**

```yaml
action: nspanel_haui.open_panel
data:
  device: "abc123..."
  panel: alarm
  wakeup: true
```

### `nspanel_haui.close_panel`

Close the current panel and return to the previous panel in the navigation
stack.  Falls back to the home panel if there is no history.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device` | no | all devices | Target NSPanel device |

**Example automation action:**

```yaml
action: nspanel_haui.close_panel
data:
  device: "abc123..."
```

### `nspanel_haui.wakeup`

Wake the display (reset the firmware interaction timer) and exit the idle
page if one is shown, returning to the panel you were on (or the home panel
per `snapshot_max_age_seconds`).  Waking never depends on a configured panel:
with no idle page shown the call only wakes the display.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device` | no | all devices | Target NSPanel device |

**Example automation action:**

```yaml
action: nspanel_haui.wakeup
data:
  device: "abc123..."
```

### `nspanel_haui.idle`

Enter the idle state immediately by opening the configured idle page (`idle_panel`),
as if the page timeout had fired.  Repeated calls keep the original pre-idle
snapshot, so waking still returns to the panel you were on.  If no idle page is
configured, the call does nothing (the current panel stays).  The display-off
behavior is separate — it is governed by `use_auto_display_off` and happens over time.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device` | no | all devices | Target NSPanel device |

**Example automation action:**

```yaml
action: nspanel_haui.idle
data:
  device: "abc123..."
```

### `nspanel_haui.send_notification`

Show a notification on the panel with a title, message, severity level, and
icon.  Notifications stay in the queue until they are dismissed on the panel,
replaced, or cleared — unless a `timeout` is given, which auto-dismisses the
notification after that many seconds.  `persistent` loops
the alert sound and re-opens the popup about every 60 seconds until dismissed;
it opens immediately and `timeout` still applies to it.  `force_show` also opens
the popup immediately, but never
takes the place of a notification popup or list that is already on screen: the
new notification waits in the queue and opens when the current one is
dismissed.  The queue holds up to 50 notifications; when it is full, the oldest
one is dropped.  While the idle page is shown, only a `critical` persistent
notification forces its popup over it; other severities stay queued and appear
as soon as the user returns to a real panel.
Notification sounds play only when the device's `sound_on_notification`
setting is on; it is off by default
([Device settings → Notifications](configuration/device.md#notifications)).
When no icon is supplied, the severity selects a default one (`info` →
`mdi:information-outline`, `warning` → `mdi:alert-outline`, `critical` →
`mdi:alert-octagon-outline`).
See [Notifications](device.md#notifications) for how notifications are
viewed and dismissed on the panel.  The ESPHome firmware also exposes
`send_notification` action (title/message/icon + optional persistent/text_size, no severity/force-show/timeout), but this service is
the recommended path because it also carries severity and force-show.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device` | no | all devices | Target NSPanel device |
| `title` | yes | — | Notification headline |
| `message` | no | `""` | Body text (can be empty for a title-only alert). Line breaks (`\n`) render as line breaks on the display |
| `icon` | no | severity default | Material Design Icon (e.g. `"mdi:bell"`). When omitted, the `type` selects the default icon |
| `type` | no | `"info"` | Severity level — `"info"`, `"warning"`, or `"critical"`. Sets the icon colour in the popup; `critical` also plays the `alert` sound instead of `notification` |
| `persistent` | no | `false` | When `true`, the notification opens immediately, its sound loops every `persistent_sound_interval` seconds and its popup re-opens about every 60 seconds until dismissed on the panel. While the idle page is shown, only a `critical` persistent notification interrupts it. A `timeout` still ends it |
| `force_show` | no | `false` | When `true`, opens the notification panel immediately, unless a notification popup or list is already open — then it waits in the queue |
| `text_size` | no | `"auto"` | Popup body text size — `"auto"` (chosen from the message length) or a font size `1`-`3` |
| `timeout` | no | — (none) | Seconds until the notification auto-dismisses. Left out (or `0`) it stays queued until dismissed on the panel |

Sending a notification with the same title and message as one that is still
queued replaces it: the queued copy is removed (firing a `removed` event), the
sound plays again, and the new copy is queued at the end — after the
notifications already waiting in front of it.

**Example automation action:**

```yaml
action: nspanel_haui.send_notification
data:
  device: "abc123..."
  title: Doorbell
  message: Someone is at the front door
  icon: mdi:bell
  type: warning
```

### `nspanel_haui.reset_last_interaction`

Reset the panel's idle timer as if the user just touched it — keeps the
display awake or delays the display-off.  Optionally add an offset to the reset
point.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device` | no | all devices | Target NSPanel device |
| `offset` | no | `0` | Additional seconds of wake time before the display returns to idle |

**Example automation action:**

```yaml
action: nspanel_haui.reset_last_interaction
data:
  device: "abc123..."
```

---

## Notify Platform (standard `notify.send_message`)

Each device also exposes a **NotifyEntity** (`notify.<device_name>`) that
you can use with the standard Home Assistant `notify.send_message` service.
This is an alternative to `nspanel_haui.send_notification` that works with
any automation or script that already uses the `notify` platform.

Two entities are created per device:

| Entity ID | Behaviour |
|-----------|-----------|
| `notify.<device_name>` | Standard notification (queued; view it by tapping the notification indicator) |
| `notify.<device_name>_persistent_notification` | Persistent notification (sound loops until dismissed on the panel; opens immediately) |

`notify.send_message` only takes a title and a message, so these entities
cannot set a severity, or force-show — use
`nspanel_haui.send_notification` for those. When no title is given, "Home Assistant"
is used. The entities are only created once the device is linked to its ESPHome
device.

**Example:**

```yaml
action: notify.send_message
data:
  title: Motion detected
  message: Front porch
target:
  entity_id: notify.nspanel_kitchen
```

---

## Sending notifications from Assist / voice assistants (LLM)

Voice assistants and LLM integrations call a **script** that wraps
`nspanel_haui.send_notification`. Expose the script to the conversation agent
so the assistant can show messages on a chosen panel. The script maps friendly
panel keys to the ESPHome device-registry IDs the service expects and exposes
the notification options as script fields:

```yaml
alias: NSPanel Notify
description: >-
  Show a short title and optional message on the NSPanel display as a popup
  notification. Use when the user asks to show a message, text or notification
  on the display. The device field selects the panel.
icon: mdi:tablet
fields:
  title:
    name: Title
    description: Short notification title shown on the panel.
    example: Dishwasher finished
    required: true
    selector:
      text:
        type: text
  message:
    name: Message
    description: Optional body below the title. Empty = title only.
    default: ""
    selector:
      text:
        type: text
  device:
    name: Target display
    description: Which NSPanel shows the message.
    default: salon
    selector:
      select:
        options:
          - value: salon
            label: Living room
          - value: bedroom
            label: Bedroom
  type:
    name: Severity
    description: >-
      info (default), warning or critical. Sets the icon and colour;
      critical plays the alert sound.
    default: info
    selector:
      select:
        options: [info, warning, critical]
  icon:
    name: Icon
    description: Material Design icon (e.g. mdi:bell). Empty = severity default icon.
    default: ""
    selector:
      icon:
  persistent:
    name: Loop sound
    description: Loop the alert sound until dismissed.
    default: false
    selector:
      boolean:
  force_show:
    name: Force show
    description: >-
      Open the popup immediately instead of waiting for the notification
      indicator.
    default: true
    selector:
      boolean:
variables:
  nspanel_devices:
    salon: "0123abcd..."   # ESPHome device-registry ID of the panel
    bedroom: "4567efgh..."
sequence:
  - action: nspanel_haui.send_notification
    data:
      title: "{{ title }}"
      message: "{{ message | default('') }}"
      device: >-
        {{ nspanel_devices.get(device | default('salon', true) | lower,
        nspanel_devices.salon) }}
      type: "{{ type | default('info') }}"
      icon: "{{ icon | default('') }}"
      persistent: "{{ persistent | default(false) | bool }}"
      force_show: "{{ force_show | default(true) | bool }}"
mode: single
```

The service accepts `type`, `icon`, `persistent` and `force_show`, so one
script covers the full range of behaviour: an info popup (the defaults), a
warning with a custom icon, or a critical alert that loops the sound and
re-opens the popup periodically until dismissed. Expose the script to the
conversation agent; the LLM reads its description and field descriptions when
deciding how to call it.

---

## Current Page Sensor

Each device exposes a **`sensor.<device_name>_current_page`** diagnostic
sensor whose value is the Nextion page name currently shown on the display
(e.g. `grid`, `weather`, `popup_light`, `clock`).  It is updated by the hub's
`nspanel_haui.page_changed` events, so no polling is needed; when the panel
device goes offline the sensor becomes unavailable and returns when the
connection is restored.

Attributes carry the panel context for automation templates:

| Attribute | Meaning |
|-----------|---------|
| `panel` | Panel key of the shown panel (empty for system popups) |
| `type` | Panel type (e.g. `grid`) |
| `title` | Panel display title |

**Example automation trigger (page changed):**

```yaml
trigger:
  - platform: state
    entity_id: sensor.nspanel_kitchen_current_page
```

The entity is only created once the device is linked to its ESPHome device.

---

## Device health (Panel Doctor)

The editor's **Device Info** dialog shows live health readings for the
connected panel, polled every few seconds from the device status API:

| Field | Meaning |
|-------|---------|
| `integration_version` | Version of the running NSPanel HAUI integration |
| `connection_uptime` | Seconds since the ESPHome connection was last (re)established |
| `idle_page_active` | `true` when the idle page is shown — the editor shows **Idle page** / **Active** |
| `last_disconnect_reason` | Why the connection dropped last (e.g. `heartbeat timeout`), if known |
| `disconnected_since` | When the device went offline that last time |
| `tft_version` / `yaml_version` | Display TFT version installed vs the version the firmware needs |
| `update` | TFT update state while an install runs: `checking`, `installing`, `done`, or `error` (with `version`, `started_at`, `last_error`) |

The Device Manager shows the same versions inline per device, using **Unknown**
when firmware or display version has not been reported. A display whose TFT is
older than the firmware version is flagged **update pending**.

The status payload is only as fresh as the last poll.  When a panel has been
disconnected too long for the poll to succeed, the dialog keeps showing the
last received snapshot — treat readings shown there as potentially stale if the
connection indicator shows the device offline.

For per-item freshness on the display itself, set `stale_data_seconds` in the
device settings ([General Settings](configuration/device.md#general-settings)):
**Row** page values that have not updated within that window render dimmed with
a `…` suffix instead of showing an old value as current.

### TFT update state

TFT installs are automatic on connect (or after confirmation on the display,
depending on `auto_install`) and normally need no action.  When you want to
re-install the TFT immediately, use the **Device Manager → Install TFT** action
or the `nspanel_haui.update_tft` service and select the panel (or press
**Install** on its **HAUI Display** update entity). The HA service is also
convenient from automations and Developer Tools, and uses HAUI's
firmware-matched TFT release unless a `url` is given. The Device Manager also supports *Refresh all
displays* from its dialog footer. While an install runs, the health section and
the Device Manager row show the matching state and version; failures surface
the reason via the update state's `last_error`.

The display gives no byte-level progress, so the state only moves through
`checking → installing → done` (or `error`) — there is no percentage bar.

---

## TFT Display Upload

Install the Nextion display file (the `.tft`) through the integration: the
panel's **HAUI Display** update entity, the `nspanel_haui.update_tft` action
(with an optional `url`), or **Device Manager → Install TFT**. All three track
the install and report failures.

The firmware still exposes one ESPHome action, `esphome.<device>_upload_tft_url`
(`url`): it is the transport the hub uses to hand the TFT URL to the device,
because the ESP32 has to download the file and stream it to the display. Calling
it directly bypasses the hub's install tracking — use `nspanel_haui.update_tft`
with `url` instead. The former `esphome.<device>_upload_tft` action and the
**Update Display** button are gone (see [Upgrading](upgrading.md#10-tft-install-actions-moved-to-the-integration)).

GitHub serves release TFTs through a redirect to a signed URL of about 870
characters. The firmware's display component reserves a 2048-byte HTTP TX
buffer (`tft_upload_http_buffer_size_tx`) for that request line; firmware
without it fails every release install with `HTTP_CLIENT: Out of buffer`
before the first byte, so update the firmware before the TFT.
## HA Events (automation triggers)

Besides the services above, the integration fires **events on the Home
Assistant event bus** so automations can react to what happens on the panel.

| Event | Payload | When |
|-------|---------|------|
| `nspanel_haui.page_changed` | `device`, `action` (`opened`/`closed`), `panel` (key), `type`, `title`, `page` (Nextion page name) | Whenever a panel is opened through the render pipeline or closed |
| `nspanel_haui.notification` | `device`, `state` (`added`/`removed`), `title`, `message`, `icon`, `notif_type`, `persistent` | Whenever a notification is queued or dismissed |
| `nspanel_haui.connection_changed` | `device`, `connected` (bool) | Whenever the hub's connection to the panel device changes |
| `nspanel_haui.display_update_changed` | `device`, `connected`, `installed_version` (TFT), `latest_version` (TFT the firmware needs), `state` (`idle`/`checking`/`installing`/`done`/`error`), `last_error` | Whenever the display's TFT version or the TFT update state changes (drives the **HAUI Display** update entity) |

All events carry the device name in `event.data.device`, so a single
automation can react to every panel of the hub.

**Example automation trigger:**

```yaml
trigger:
  - platform: event
    event_type: nspanel_haui.notification
    event_data:
      state: added
    variables:
      notif_title: "{{ trigger.event.data.title }}"
      notif_device: "{{ trigger.event.data.device }}"
```

Useful patterns: forward `critical` notifications to your phone or a
messaging service, log doorbell rings, or reset a "someone is home" flag
from a panel button.
