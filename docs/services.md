---
title: Services
description: Home Assistant services provided by NSPanel HAUI for display control and device management
---

# Services

NSPanel HAUI registers Home Assistant services for controlling the display
and managing the device from automations, scripts, or the Developer Tools
panel in the HA UI.

Services are also available for uploading TFT firmware to the display — these
run at the ESPHome device level.

---

## Navigation & Display Control

These six services are registered under the `nspanel_haui` domain.  The
`device` field is **optional** — when omitted, the service applies to **all**
HAUI-connected devices.  When provided, it targets a single device via the
device picker (filtered to ESPHome devices running HAUI firmware).  Pass the
device ID in `data` as `device`; these services do not accept a `target:`.

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
icon.  Notifications stay in the queue until they are dismissed on the panel
(or replaced/cleared) — there is no automatic dismissal.  `persistent` loops
the alert sound until dismissed, and `force_show` interrupts whatever is
displayed to open the popup.
When no icon is supplied, the severity selects a default one (`info` →
`mdi:information-outline`, `warning` → `mdi:alert-outline`, `critical` →
`mdi:alert-octagon-outline`).
See [Notifications](device.md#notifications) for how notifications are
viewed and dismissed on the panel.  The ESPHome firmware also exposes
`send_notification` action (title/message/icon + optional persistent/text_size), but this service is
the recommended path because it also carries severity and force-show.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device` | no | all devices | Target NSPanel device |
| `title` | yes | — | Notification headline |
| `message` | no | `""` | Body text (can be empty for a title-only alert) |
| `icon` | no | severity default | Material Design Icon (e.g. `"mdi:bell"`). When omitted, the `type` selects the default icon |
| `type` | no | `"info"` | Severity level — `"info"`, `"warning"`, or `"critical"`. Sets the icon colour in the popup; `critical` also plays the `alert` sound instead of `notification` |
| `persistent` | no | `false` | When `true`, notification sound loops until dismissed on the panel, and the notification opens immediately |
| `force_show` | no | `false` | When `true`, immediately opens the notification panel even if another panel is displayed |
| `require_ack` | no | `false` | When `true`, the notification re-opens its popup periodically until someone presses **Acknowledge** on the panel. Implies `persistent` (looping alert sound). Use for alarms and other notifications that must not be missed |
| `text_size` | no | `"auto"` | Popup body text size — `"auto"` (chosen from the message length) or a font size `1`-`3` |

Sending a notification with the same title and message as one that is still
queued replaces it: the sound plays again and the notification moves to the
front of the queue.

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
  require_ack:
    name: Require acknowledgement
    description: >-
      Keep reopening the popup until Acknowledge is pressed. Implies persistent.
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
      require_ack: "{{ require_ack | default(false) | bool }}"
      force_show: "{{ force_show | default(true) | bool }}"
mode: single
```

The service accepts `type`, `icon`, `persistent`, `require_ack` and
`force_show`, so one script covers the full range of behaviour: an info
popup (the defaults), a warning with a custom icon, or a critical alert
that loops the sound and requires acknowledgement. Expose the script to the
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

The Device Manager shows the same versions inline per device; a display whose
TFT is older than the firmware version is flagged **update pending**.

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
re-install the TFT immediately, the **Device Manager → Install TFT** action
triggers it for the selected panel (or all at once in the dialog footer's
*Refresh all displays* menu).  While an install runs, the health section and
the Device Manager row show the matching state and version; failures surface
the reason via the update state's `last_error`.

The display gives no byte-level progress, so the state only moves through
`checking → installing → done` (or `error`) — there is no percentage bar.

---

## TFT Display Upload

These are **ESPHome device actions** — they appear under the `esphome` domain
in HA (e.g. `esphome.<device_name>_upload_tft`).  Use them to update the
Nextion display firmware (the `.tft` file) without a USB cable.

### `esphome.<device>_upload_tft`

Upload the TFT file from the URL configured on the ESPHome device.  The URL
is set in the ESPHome YAML (`tft_update_url`, used as the display's `tft_url`).

**Example:**

```yaml
action: esphome.nspanel_kitchen_upload_tft
```

### `esphome.<device>_upload_tft_url`

Upload a TFT file from an arbitrary URL provided directly in the service call.
Sets the display's TFT URL to the given value and uploads it; the override lasts
until the device restarts.

**Example:**

```yaml
action: esphome.nspanel_kitchen_upload_tft_url
data:
  url: "https://example.com/nspanel_haui_v2.tft"
```
## HA Events (automation triggers)

Besides the services above, the integration fires **events on the Home
Assistant event bus** so automations can react to what happens on the panel.

| Event | Payload | When |
|-------|---------|------|
| `nspanel_haui.page_changed` | `device`, `action` (`opened`/`closed`), `panel` (key), `type`, `title`, `page` (Nextion page name) | Whenever a panel is opened through the render pipeline or closed |
| `nspanel_haui.notification` | `device`, `state` (`added`/`removed`), `title`, `message`, `icon`, `notif_type`, `persistent`, `require_ack` | Whenever a notification is queued or dismissed |
| `nspanel_haui.connection_changed` | `device`, `connected` (bool) | Whenever the hub's connection to the panel device changes |

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

Useful patterns: forward `critical` / `require_ack` notifications to your
phone or a messaging service, log doorbell rings, or reset a "someone is
home" flag from a panel button.
