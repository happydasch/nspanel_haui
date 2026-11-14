---
title: Services
description: Home Assistant services provided by NSPanel HAUI for display control and device management
---

# Services

NSPanel HAUI adds services (actions) to Home Assistant, so automations and scripts can control the panel. You can try them under **Developer Tools → Actions**.

| Service | What it does |
|---------|--------------|
| [`nspanel_haui.send_notification`](#nspanel_hauisend_notification) | Show a notification |
| [`nspanel_haui.open_panel`](#nspanel_hauiopen_panel) | Open a panel |
| [`nspanel_haui.close_panel`](#nspanel_hauiclose_panel) | Close the current panel |
| [`nspanel_haui.wakeup`](#nspanel_hauiwakeup) | Wake the display |
| [`nspanel_haui.idle`](#nspanel_hauiidle) | Open the idle page |
| [`nspanel_haui.reset_last_interaction`](#nspanel_hauireset_last_interaction) | Keep the display awake |
| [`nspanel_haui.update_tft`](#nspanel_hauiupdate_tft) | Install a display file (TFT) |
| [`nspanel_haui.update_firmware`](#nspanel_hauiupdate_firmware) | Install firmware |

The integration also provides [notify entities](#notify-platform-standard-notifysend_message), [update entities](#haui-firmware-update-entity) and [events](#ha-events-automation-triggers).

**The `device` field**

- For navigation and notifications, `device` is optional. Without it, the service acts on all panels.
- For `update_tft` and `update_firmware`, `device` is required, so an install never starts on every panel by accident.
- Choose the panel in the service's **Device** selector. In YAML, `device` is the device ID of the panel's NSPanel HAUI device or of its ESPHome device.
- A call with a `device` that is not a running panel fails with an error.

## Navigation & Display Control

### `nspanel_haui.open_panel`

Opens a panel by its **key**, the name shown in the panel editor. A locked panel still asks for its PIN.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device` | no | all devices | The panel to act on |
| `panel` | yes | — | Key of the panel to open, for example `alarm` or `grid_2` |
| `wakeup` | no | `false` | Wake the display before opening the panel |

```yaml
action: nspanel_haui.open_panel
data:
  device: "abc123..."
  panel: alarm
  wakeup: true
```

### `nspanel_haui.close_panel`

Closes the current panel and goes back to the previous one, or to the home panel when there is none.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device` | no | all devices | The panel to act on |

```yaml
action: nspanel_haui.close_panel
data:
  device: "abc123..."
```

### `nspanel_haui.wakeup`

Wakes the display. If the idle page is shown, it is left and the previous panel (or the home panel, see [Return Panel after Wakeup](device.md#return-panel-after-wakeup)) is shown again.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device` | no | all devices | The panel to act on |

```yaml
action: nspanel_haui.wakeup
data:
  device: "abc123..."
```

### `nspanel_haui.idle`

Opens the idle page right away, as if the page timeout had passed. Without an idle panel the call does nothing. It does not turn the display off; that still follows the display-off timeout.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device` | no | all devices | The panel to act on |

```yaml
action: nspanel_haui.idle
data:
  device: "abc123..."
```

### `nspanel_haui.reset_last_interaction`

Restarts the panel's inactivity timer, as if someone had just touched it. Use it to keep the display awake.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device` | no | all devices | The panel to act on |
| `offset` | no | `0` | Extra seconds to stay awake |

```yaml
action: nspanel_haui.reset_last_interaction
data:
  device: "abc123..."
```

## Notifications

### `nspanel_haui.send_notification`

Shows a notification on the panel. [Notifications](device.md#notifications) explains how they are shown and dismissed on the panel.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device` | no | all devices | The panel to act on |
| `title` | yes | — | The headline |
| `message` | no | `""` | The text. `\n` starts a new line. |
| `icon` | no | `""` | An icon, for example `mdi:bell`. Without one, no icon is shown and the text uses the full width. |
| `icon_color` | no | `""` | The icon's colour: `#rrggbb`, an RGB565 number, `[r, g, b]` or an integer string. Empty uses the theme's text colour. |
| `sound` | no | `notification` | `startup`, `tone`, `tone_up`, `tone_down`, `seq_up`, `seq_down`, `notification`, `alert`, `alert_fast`, `elise`, or `none` for silence |
| `persistent` | no | `false` | For alerts that need attention: opens immediately, repeats its sound and opens again about every 60 seconds until dismissed |
| `force_show` | no | `false` | Opens the notification immediately. If another notification is open, it waits until that one is dismissed. |
| `text_size` | no | `auto` | `auto` uses the largest font that fits the message on one page. `1`–`3` sets a font size; text that does not fit is split into pages. |
| `timeout` | no | none | Removes the notification after this many seconds (1–3600), counted from the moment it is sent, even if nobody has seen it. Without a timeout, or with `0`, it stays until dismissed. |

```yaml
action: nspanel_haui.send_notification
data:
  device: "abc123..."
  title: Doorbell
  message: Someone is at the front door
  icon: mdi:bell
  icon_color: "#f69d31"
  sound: alert
```

Good to know:

- **Sounds are off by default.** They only play when the device's `sound_on_notification` setting is on, see [Device settings → Sounds](configuration/device.md#sounds).
- **Persistent** notifications repeat their sound every `persistent_sound_interval` seconds and also open over the idle page. A [schedule](configuration/device.md#schedule) entry with sound off still keeps the display dark. A `timeout` also ends a persistent notification.
- **The queue** holds up to 50 notifications. When it is full, the oldest one is dropped.
- **Sending the same title and message again** replaces the waiting notification: its sound plays again and it moves to the end of the queue.

#### Preset notification script

This script gives you ready-made notification types, so automations can simply say `type: warning`. Create it as a script in Home Assistant, for example with the alias **NSPanel Notify**, and call `script.nspanel_notify`.

| `type` | `icon_color` | `sound` | `persistent` | `force_show` |
|--------|--------------|---------|--------------|--------------|
| `info` | theme text colour | `notification` | no | no |
| `warning` | `#f69d31` | `notification` | no | no |
| `alert` | `#4aa5ee` | `alert` | no | yes |
| `critical` | `#4aa5ee` | `alert` | yes | yes |
| `silent` | theme text colour | `none` | no | no |

??? example "The script"

    ```yaml
    alias: NSPanel Notify
    description: >-
      Show a notification on an NSPanel display. `type` picks the icon colour, the
      sound, and whether the notification is persistent.
    icon: mdi:tablet
    fields:
      device:
        name: Target display
        description: Which NSPanel shows the message.
        required: true
        selector:
          device:
            integration: nspanel_haui
      title:
        name: Title
        description: Short notification title shown on the panel. Keep it to one word where possible; a title wider than the header widget is cut to fit and ends in `..`.
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
            multiline: true
      icon:
        name: Icon
        description: Material Design icon (e.g. mdi:bell). Empty = no icon shown.
        default: ""
        selector:
          icon:
      type:
        name: Type
        description: >-
          info, warning, alert, critical or silent. Sets the icon colour and the
          sound; critical also loops the sound until dismissed.
        default: info
        selector:
          select:
            options: [info, warning, alert, critical, silent]
      timeout:
        name: Auto-dismiss after
        description: >-
          Optional timeout in seconds, counted from when the notification is queued.
          A notification can expire while waiting to be shown. Use 0 to keep it
          until dismissed on the panel.
        default: 0
        selector:
          number:
            min: 0
            max: 3600
            unit_of_measurement: s
            mode: box
      text_size:
        name: Text size
        description: '"auto" or a font size 1-3.'
        default: auto
        selector:
          select:
            options: ["auto", "1", "2", "3"]
    variables:
      presets:
        info:
          icon_color: ""
          sound: notification
          persistent: false
          force_show: false
        warning:
          icon_color: "#f69d31"
          sound: notification
          persistent: false
          force_show: false
        alert:
          icon_color: "#4aa5ee"
          sound: alert
          persistent: false
          force_show: true
        critical:
          icon_color: "#4aa5ee"
          sound: alert
          persistent: true
          force_show: true
        silent:
          icon_color: ""
          sound: none
          persistent: false
          force_show: false
    sequence:
      - variables:
          preset: "{{ presets.get(type | default('info', true) | lower, presets.info) }}"
      - action: nspanel_haui.send_notification
        data:
          device: "{{ device }}"
          title: "{{ title }}"
          message: "{{ message | default('') }}"
          icon: "{{ icon | default('') }}"
          icon_color: "{{ preset.icon_color }}"
          sound: "{{ preset.sound }}"
          persistent: "{{ preset.persistent }}"
          force_show: "{{ preset.force_show }}"
          timeout: "{{ timeout | default(0) | int(0) }}"
          text_size: "{{ text_size | default('auto') }}"
    mode: single
    ```

The two colours are the accent colors of the built-in dark theme. With a custom theme, call `nspanel_haui.send_notification` directly and pass your own `icon_color`.

### Notify Platform (standard `notify.send_message`)

Every panel also has two notify entities. Use them with Home Assistant's standard `notify.send_message` action, for example in automations that already use notify entities.

| Entity | Behaviour |
|--------|-----------|
| `notify.<device_name>` | A normal notification. It waits until the notification indicator is tapped. |
| `notify.<device_name>_persistent_notification` | A persistent notification. It opens immediately and repeats its sound until dismissed. |

```yaml
action: notify.send_message
data:
  title: Motion detected
  message: Front porch
target:
  entity_id: notify.nspanel_kitchen
```

These entities only take a title and a message. Without a title, "Home Assistant" is used. For an icon, a colour, a sound, `force_show` or a timeout, use `nspanel_haui.send_notification`.

### Sending notifications from Assist / voice assistants (LLM)

A voice assistant can show messages on a panel when you give it a script to call. The script below wraps the [preset notification script](#preset-notification-script) and lets the assistant choose the panel by a simple name.

1. Create the preset notification script above.
2. Create the script below. Replace the names and device IDs under `nspanel_devices` and in the `device` field with your panels.
3. Expose the script to your conversation agent. The assistant reads the descriptions of the script and its fields to decide how to call it.

??? example "The script"

    ```yaml
    alias: NSPanel Notify Voice
    description: >-
      Show a short title and optional message on the NSPanel display as a popup
      notification. Use when the user asks to show a message, text or notification
      on the display. The device field selects the panel.
    icon: mdi:tablet
    fields:
      title:
        name: Title
        description: Short notification title shown on the panel. Keep it to one word where possible; a title wider than the header widget is cut to fit and ends in `..`.
        example: Dishwasher
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
        name: Type
        description: >-
          info (default), warning, alert, critical or silent. Sets the icon colour
          and sound; critical loops the sound until dismissed.
        default: info
        selector:
          select:
            options: [info, warning, alert, critical, silent]
      icon:
        name: Icon
        description: Material Design icon (e.g. mdi:bell). Empty = no icon shown.
        default: ""
        selector:
          icon:
      timeout:
        name: Auto-dismiss after
        description: >-
          Optional timeout in seconds, counted from when the notification is queued.
          A notification can expire while waiting to be shown. Use 0 to keep it
          until dismissed on the panel.
        default: 0
        selector:
          number:
            min: 0
            max: 3600
            unit_of_measurement: s
            mode: box
      text_size:
        name: Text size
        description: "\"auto\" or a font size 1-3."
        default: auto
        selector:
          select:
            options: ["auto", "1", "2", "3"]
    variables:
      nspanel_devices:
        salon: "0123abcd..."   # device-registry ID of the panel (HAUI or ESPHome device)
        bedroom: "4567efgh..."
    sequence:
      - action: script.nspanel_notify
        data:
          title: "{{ title }}"
          message: "{{ message | default('') }}"
          device: >-
            {{ nspanel_devices.get(device | default('salon', true) | lower,
            nspanel_devices.salon) }}
          type: "{{ type | default('info') }}"
          icon: "{{ icon | default('') }}"
          timeout: "{{ timeout | default(0) | int(0) }}"
          text_size: "{{ text_size | default('auto') }}"
    mode: single
    ```

## Display Updates

Updates normally run on their own, see [Updating](update.md). These services and entities are for automations and for installing a specific version.

### `nspanel_haui.update_tft`

Installs a display file (TFT) on one panel: the one the firmware needs, or the file at `url`.

| Field | Required | Description |
|-------|----------|-------------|
| `device` | yes | The panel whose display is updated |
| `version` | no | The TFT version the firmware needs. Cannot be combined with `url`. |
| `url` | no | The http(s) address of a `.tft` file to install instead, for example your own build. Cannot be combined with `version`. |

```yaml
action: nspanel_haui.update_tft
data:
  device: "abc123..."
```

Install your own file:

```yaml
action: nspanel_haui.update_tft
data:
  device: "abc123..."
  url: "http://homeassistant.local:8123/local/nspanel/nspanel_haui.tft"
```

Good to know:

- **Progress.** The display reports no percentage. The state goes from *checking* to *installing* to *done*, or to *error* with the reason. You see it in the **Updates** sidebar, in the device's **Diagnostics** and on the **HAUI Display** entity.
- **A file from a URL stays.** The hub does not replace it with the release TFT until the firmware version changes or Home Assistant restarts. Calling the service without `version` and `url` also installs the release TFT again.
- **A file from a URL has no version the hub can check.** The install counts as done when the panel restarts after the upload. An upload without a restart is reported as failed, see [Troubleshooting](troubleshooting.md#tft-install-fails-with-the-panel-did-not-reboot-after-the-upload).
- A TFT that does not match the firmware may lack pages the firmware uses.

### `nspanel_haui.update_firmware`

Installs firmware on one panel: the offered update, another release, or the file at `url`.

| Field | Required | Description |
|-------|----------|-------------|
| `device` | yes | The panel whose firmware is installed |
| `version` | no | A release to install instead of the offered update, for example `0.4.2`. Older releases work too. Cannot be combined with `url`. |
| `url` | no | The http(s) address of a firmware OTA file (`firmware.ota.bin` or `nspanel_haui_ota.bin`). Cannot be combined with `version`. |

```yaml
action: nspanel_haui.update_firmware
data:
  device: "abc123..."
  version: "0.4.2"
```

Good to know:

- **Without `version` and `url`** the offered update is installed, like **Install** on the **HAUI Firmware** entity.
- **Releases** can be installed from v0.4.2 on. Older releases must be flashed with the ESPHome dashboard or a cable.
- **A file from a URL** is checked first: a factory image or a file that is too large is refused. The panel must be able to reach the address too.
- **The panel needs firmware 0.4.3 or later** to install firmware this way. Flash an older panel once through ESPHome, see [Updating](update.md).
- **Automatic firmware updates pause** after you install a release or a file from a URL, so the hub does not put the latest release back. The pause ends when Home Assistant restarts or you install the offered update.
- **Custom firmware stays custom.** A panel with firmware built from your own YAML is never offered the universal release firmware. Install your own builds with `url`. See [Device Configuration → Updates](configuration/device.md#updates).
- **Going back a release?** The display file is not downgraded on its own. Install the matching TFT with `nspanel_haui.update_tft` and `version`.

### HAUI Firmware update entity

Every panel has an `update.<device>_haui_firmware` entity.

- **Installed version:** the firmware on the panel.
- **Latest version:** the firmware of the latest release, or of the [manifest you configured](configuration/device.md#updates).
- **Install** does the same as `nspanel_haui.update_firmware`: the panel downloads the firmware, installs it and restarts. The entity shows *installing* until the panel is back.
- An install that does not finish within ten minutes, or that ends on the old version, is shown as an error in the **Updates** sidebar and on the entity.

The ESPHome integration may add its own **Firmware** update entity to the device (disabled by default). It belongs to the ESPHome dashboard and has nothing to do with the updates described here.

### HAUI Display update entity

Every panel has an `update.<device>_haui_display` entity, on the same device page.

- **Installed version:** the TFT the display reports. While the display has not reported it yet, the state is unknown; use `nspanel_haui.update_tft` to install anyway.
- **Latest version:** the TFT the firmware needs.
- **Install** does the same as `nspanel_haui.update_tft`. The entity shows *installing* until the display reports the new version.

```yaml
action: update.install
target:
  entity_id: update.nspanel_kitchen_haui_display
```

### TFT Display Upload

Always install a TFT through the integration: with the **HAUI Display** entity, with `nspanel_haui.update_tft`, or in the editor by pressing **Install** beside **Display (TFT)** in the **Updates** sidebar. All three follow the install and report failures.

The firmware has an ESPHome action `esphome.<device>_upload_tft_url`. The hub uses it to pass the file's address to the panel. Do not call it yourself: the hub would not know about the install. Use `nspanel_haui.update_tft` with `url` instead.

The former `esphome.<device>_upload_tft` action and the **Update Display** button no longer exist, see [Upgrading](../develop/update-process.md#10-tft-install-actions-moved-to-the-integration).

## Current Page Sensor

The firmware has two sensors for the page that is shown, both disabled by default:

- `sensor.<device_name>_current_page`
- `sensor.<device_name>_current_page_number`

See [ESPHome → Page](../develop/esphome.md#page). To react to the *panel* that is shown (its key, type and title), use the [`nspanel_haui.page_changed`](#ha-events-automation-triggers) event instead.

## HA Events (automation triggers)

The integration fires events on the Home Assistant event bus, so automations can react to what happens on the panel. Every event has the panel's name in `device`.

| Event | When | Data |
|-------|------|------|
| `nspanel_haui.page_changed` | A panel is opened or closed | `device`, `action` (`opened` / `closed`), `panel` (key), `type`, `title`, `page` |
| `nspanel_haui.notification` | A notification is added or removed | `device`, `id`, `state` (`added` / `removed`), `title`, `message`, `icon`, `icon_color`, `sound`, `persistent`, `force_show`, `timeout` |
| `nspanel_haui.connection_changed` | The panel connects or disconnects; a reboot fires `connected: false` and then `true` | `device`, `connected` |
| `nspanel_haui.display_update_changed` | The display version or the state of a display update changes | `device`, `connected`, `enabled`, `installed_version`, `latest_version`, `state` (`idle` / `checking` / `installing` / `done` / `error`), `update_reason`, `last_error` |
| `nspanel_haui.firmware_update_changed` | The firmware version or the state of a firmware update changes | `device`, `connected`, `enabled`, `installed_version`, `latest_version`, `installing`, `reason`, `last_error` |

Notes on the data:

- `nspanel_haui.notification`: a notification is *removed* when it is dismissed, expires, is replaced, is cleared or drops out of a full queue. A notification that replaces a waiting one gets a new `id`. `icon_color` is `null` for the theme's text colour, `sound` is `""` when silent, `timeout` is in seconds or `null`. `force_show` is `true` for every persistent notification.
- `latest_version` of a firmware update is `null` when no firmware can be offered; `reason` and `update_reason` say why nothing is offered.

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

Ideas: forward persistent notifications to your phone, log doorbell rings, or start an automation when a certain panel is opened.
