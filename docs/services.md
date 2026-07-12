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

These four services are registered under the `nspanel_haui` domain and
**require a `device_id`** to target which panel device to control.  The
device picker in the HA UI automatically filters to NSPanel HAUI devices.

### `nspanel_haui.open_panel`

Navigate the display to a specific panel by its **panel key** (the identifier
shown in the panel editor).  The panel opens through the navigation controller,
so the full render pipeline runs (goto_page, page ack, settle, set_panel).
Navigation history, popups, and lock state are honored.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device_id` | yes | — | Target NSPanel device |
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
| `device_id` | yes | — | Target NSPanel device |

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
| `device_id` | yes | — | Target NSPanel device |

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
| `device_id` | yes | — | Target NSPanel device |

**Example automation action:**

```yaml
action: nspanel_haui.sleep
target:
  device_id: "abc123..."
```

---

## TFT Display Upload

These are **ESPHome device actions** — they appear under the `esphome` domain
in HA (e.g. `esphome.<device_name>_upload_tft`).  Use them to update the
Nextion display firmware (the `.tft` file) without a USB cable.

### `esphome.<device>_upload_tft`

Upload the TFT file from the URL configured on the ESPHome device.  The URL
is set in the ESPHome YAML (`tft_url`).

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