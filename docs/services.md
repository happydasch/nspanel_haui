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
device picker (filtered to ESPHome devices running HAUI firmware).

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
  panel: alarm
  wakeup: true
target:
  device_id: "abc123..."
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
target:
  device_id: "abc123..."
```

### `nspanel_haui.wakeup`

Wake the display and navigate to the configured wakeup panel (or home panel
if no wakeup panel is set).  Equivalent to touching the display when it is
in dimmed or sleep state.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device` | no | all devices | Target NSPanel device |

**Example automation action:**

```yaml
action: nspanel_haui.wakeup
target:
  device_id: "abc123..."
```

### `nspanel_haui.sleep`

Send the display to sleep immediately by opening the configured sleep panel.
The device's dim/sleep timer is unaffected — this is a one-shot command.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device` | no | all devices | Target NSPanel device |

**Example automation action:**

```yaml
action: nspanel_haui.sleep
target:
  device_id: "abc123..."
```

### `nspanel_haui.send_notification`

Show a notification on the panel with a title, message, severity level, and
icon.  Supports auto-dismiss (timeout), persistent alerts that loop until
dismissed on the panel, and force-show to interrupt whatever is displayed.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device` | no | all devices | Target NSPanel device |
| `title` | yes | — | Notification headline |
| `message` | no | `""` | Body text (can be empty for a title-only alert) |
| `icon` | no | `""` | Material Design Icon (e.g. `"mdi:bell"`) |
| `type` | no | `"info"` | Severity level — `"info"`, `"warning"`, or `"critical"` (affects colour and sound) |
| `timeout` | no | `0` | Seconds until auto-dismiss. `0` = stays until dismissed |
| `persistent` | no | `false` | When `true`, notification sound loops until dismissed on the panel |
| `force_show` | no | `false` | When `true`, immediately opens the notification panel even if another panel is displayed |

**Example automation action:**

```yaml
action: nspanel_haui.send_notification
data:
  title: Doorbell
  message: Someone is at the front door
  icon: mdi:bell
  type: warning
  timeout: 30
target:
  device_id: "abc123..."
```

### `nspanel_haui.reset_last_interaction`

Reset the panel's idle timer as if the user just touched it — keeps the
display awake or delays sleep.  Optionally add an offset to the reset
point.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device` | no | all devices | Target NSPanel device |
| `offset` | no | `0` | Additional seconds of wake time before the display returns to idle |

**Example automation action:**

```yaml
action: nspanel_haui.reset_last_interaction
target:
  device_id: "abc123..."
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
| `notify.<device_name>` | Standard notification (auto-dismisses on timeout) |
| `notify.<device_name>_persistent` | Persistent notification (sound loops until dismissed on the panel) |

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

## TFT Display Upload

These are **ESPHome device actions** — they appear under the `esphome` domain
in HA (e.g. `esphome.<device_name>_upload_tft`).  Use them to update the
Nextion display firmware (the `.tft` file) without a USB cable.

### `esphome.<device>_upload_tft`

Upload the TFT file from the URL configured on the ESPHome device.  The URL
is set in the ESPHome YAML (`tft_update_url`).

**Example:**

```yaml
action: esphome.nspanel_kitchen_upload_tft
```

### `esphome.<device>_upload_tft_url`

Upload a TFT file from an arbitrary URL provided directly in the service call.
Overrides the device's configured `tft_url` for this upload only.

**Example:**

```yaml
action: esphome.nspanel_kitchen_upload_tft_url
data:
  url: "https://example.com/nspanel_haui_v2.tft"
```