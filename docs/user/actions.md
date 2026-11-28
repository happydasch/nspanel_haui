---
title: Actions
description: Home Assistant actions provided by NSPanel HAUI for display control and device management
---

# Actions

NSPanel HAUI adds actions to Home Assistant, so automations and scripts can control the panel. You can try them under **Developer Tools → Actions**. Older Home Assistant versions call them services.

| Action | What it does |
|--------|--------------|
| [`nspanel_haui.send_notification`](#nspanel_hauisend_notification) | Show a notification |
| [`nspanel_haui.open_panel`](#nspanel_hauiopen_panel) | Open a panel |
| [`nspanel_haui.close_panel`](#nspanel_hauiclose_panel) | Close the current panel |
| [`nspanel_haui.wakeup`](#nspanel_hauiwakeup) | Wake the display |
| [`nspanel_haui.idle`](#nspanel_hauiidle) | Open the idle page |
| [`nspanel_haui.reset_last_interaction`](#nspanel_hauireset_last_interaction) | Keep the display awake |
| [`nspanel_haui.show_image`](#nspanel_hauishow_image) | Draw an image on the panel |
| [`nspanel_haui.clear_image`](#nspanel_hauiclear_image) | Paint an image's rectangle away |
| [`nspanel_haui.update_tft`](#nspanel_hauiupdate_tft) | Install a display file (TFT) |
| [`nspanel_haui.update_firmware`](#nspanel_hauiupdate_firmware) | Install firmware |

The integration also provides [notify entities](#notify-platform-standard-notifysend_message), [update entities](#haui-firmware-update-entity) and [events](#ha-events-automation-triggers).

**The `device` field**

- For navigation and notifications, `device` is optional. Without it, the action applies to all panels.
- For `update_tft` and `update_firmware`, `device` is required, so an install never starts on every panel by accident.
- Choose the panel in the action's **Device** selector. In YAML, `device` is the device ID of the panel's NSPanel HAUI device or of its ESPHome device.
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

Wakes the display. If the idle page is shown, it is left and the previous panel (or the home panel, see [Return Panel after Wakeup](editor/device.md#return-after-the-idle-page)) is shown again.

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

## Images on the panel

The panel can show an image that is not part of a panel: a logo, a QR code, a
weather radar, a small photo. The image is drawn **over the page that is
currently shown** — it is not a panel of its own, and it is not stored on the
panel.

Two actions do this:

| Action | What it does |
|--------|--------------|
| `nspanel_haui.show_image` | Draws an image from a URL or from a file into a rectangle |
| `nspanel_haui.clear_image` | Paints that rectangle back to the page's background colour |

### `nspanel_haui.show_image`

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device` | no | all devices | The panel to draw on |
| `url` | one of the two | — | The http(s) address of the image: PNG, JPEG, GIF, BMP or WebP, up to 4 MiB |
| `path` | one of the two | — | The image as a file in the `www` folder of your configuration, for example `logo.png` for `www/logo.png` |
| `x` | yes | — | Left edge of the rectangle, in display pixels |
| `y` | yes | — | Top edge of the rectangle, in display pixels |
| `w` | yes | — | Width of the rectangle, in display pixels |
| `h` | yes | — | Height of the rectangle, in display pixels |
| `progressive` | no | `true` | Draw a coarse version first, so the image appears at once and then sharpens |
| `quality` | no | `300` | How many rectangles the whole draw may use, 60–12000; more is sharper and slower; a small rectangle reaches one rectangle per display pixel. |

```yaml
action: nspanel_haui.show_image
data:
  device: "abc123..."
  url: "https://example.com/logo.png"
  x: 20
  y: 60
  w: 120
  h: 120
```

```yaml
action: nspanel_haui.show_image
data:
  device: "abc123..."
  path: "logo.png"    # the file www/logo.png in your configuration
  x: 20
  y: 60
  w: 120
  h: 120
```

Give exactly one of `url` and `path`. `path` needs no web server: put the file
in the `www` folder of your configuration folder (create it if it is not there)
and name it relative to that folder — the same file Home Assistant already
publishes at `/local/logo.png`. A `www/` prefix is accepted, and anything that
points outside the folder is refused.

### `nspanel_haui.clear_image`

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device` | no | all devices | The panel to clear |
| `x` | yes | — | Left edge of the rectangle, in display pixels |
| `y` | yes | — | Top edge of the rectangle, in display pixels |
| `w` | yes | — | Width of the rectangle, in display pixels |
| `h` | yes | — | Height of the rectangle, in display pixels |

```yaml
action: nspanel_haui.clear_image
data:
  device: "abc123..."
  x: 20
  y: 60
  w: 120
  h: 120
```

### What the image looks like

- **The rectangle is painted entirely.** One rectangle covers the whole area in
  the picture's own most common colour, and only the blocks that differ from it
  follow — so whatever was there, an older image, a widget or a picture
  background, cannot show through, while a large flat area of the picture costs a
  single instruction instead of thousands. The area the picture does not fill is
  painted in that colour too, which is why a fitted image looks like one card
  instead of a picture floating on a black box.
- **It is rebuilt from rectangles, not pixels.** The display link is fast enough
  for a few hundred rectangles, not for a photograph's pixels, so the image is
  drawn as blocks in the display's own 65 536 colours — gradients stay gradients.
  A logo, an icon, a QR code or a chart comes out crisp; a photo comes out as a
  coarse mosaic.
- **It is fast, and the count is the time.** `quality` is the total number of
  rectangles the whole draw may use — the coarse pass is part of it, not extra.
  Every rectangle is one instruction the panel draws in turn, so it trades time
  for detail: the hub plans for 2 ms per rectangle — `60` is about 0.12 s, `300`
  about 0.6 s, and the top of its range, `12000`, about 24 s — and the panel
  streams a draw at the rate its display acknowledges the rectangles, which is
  several times faster, so a draw usually finishes in a fraction of that plan.
  The Home Assistant log prints what it actually took. The grid never gets finer
  than one display pixel. A page with large flat areas merges down to a few
  thousand rectangles and is drawn at that resolution even at `4000`, while a
  photograph needs one rectangle per pixel — 153 600 for a whole 480x320 page —
  so the cell size is whatever the budget allows, which is what a page background
  picture is for.
- **A long image arrives in bands.** The hub sends the rectangles in slices the
  panel can hold in memory and sends the next one as each finishes, so a big,
  detailed image starts drawing at once and fills in rather than waiting. A page
  change in the middle stops it: the band already on its way finishes, the page
  loads and nothing else is painted.
- **Thin gaps or stray colour strips mean the panel's firmware is old.** A
  detailed image is thousands of one-pixel-high rectangles, which a display draws
  slower than the old firmware streams them, so its receive buffer overruns and
  single rectangles are lost or corrupted. The hub re-sends the image once when
  the panel reports a failure and warns in the log; installing the current
  firmware draws it cleanly.
- **The rectangle decides the detail.** The block never gets finer than one
  display pixel, so a rectangle of a few hundred pixels is drawn at the screen's
  own resolution, while the same budget over the whole page gives a coarse mosaic
  (that is what a panel with a picture background is for). If the image comes out
  blocky, Home Assistant logs a warning with the block size it reached.
- **The image keeps its aspect ratio.** It is fitted into the rectangle, and the
  margins are painted in the picture's own canvas colour.
- **It disappears on the next page change** — opening a panel, going to the idle
  page, a notification. A re-render of the same page only repaints the widgets it
  touches, so the image stays everywhere else. Call the action again if the image
  should stay.
- **`clear_image` only paints a flat colour.** On a page whose background is a
  picture (clock, clock two, weather) the rectangle stays a visible block; change
  the page instead.
- **It needs firmware 0.5.9 or later:** the panel's firmware draws the program the
  hub prepares. On older firmware the action fails with the version it needs
  instead of silently drawing nothing.
- **It is not drawn during a display update.** While a TFT install is running the
  action is refused; the panel is rebooting its display anyway.


## A camera on the panel

A camera can keep its picture on the panel: `nspanel_haui.start_camera_stream`
takes a snapshot a few times a second, works out which parts of the picture
changed, and draws only those. It is a **slow, soft picture**, not video — the
display has no framebuffer and no refresh control, so every frame is rectangles
painted straight onto the page (see the developer guide). What it is good at is
the two things a wall panel actually needs: a still scene costs *nothing* (no
rectangles are sent at all), and one person walking across a room costs a handful
of rectangles per frame.

| Action | What it does |
|--------|--------------|
| `nspanel_haui.start_camera_stream` | Draws a camera into a rectangle, and keeps it current |
| `nspanel_haui.stop_camera_stream` | Stops it; the last frame stays on the screen |

### `nspanel_haui.start_camera_stream`

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device` | no | all devices | The panel to draw on |
| `camera` | yes | — | The camera entity to draw |
| `x`, `y` | no | `0` | Top-left corner of the rectangle, in display pixels |
| `w`, `h` | yes | — | Size of the rectangle, in display pixels |
| `fps` | no | `2` | How often to try for a new frame, 0.1–10 |
| `cell` | no | `8` | Size of one rectangle in pixels, 2–24 (smaller is sharper, slower) |
| `band` | no | `24` | How far a colour must move before it is repainted, per channel |
| `max_runs` | no | `400` | The most rectangles one frame may cost, 40–2400 |

```yaml
action: nspanel_haui.start_camera_stream
data:
  device: "abc123..."
  camera: camera.front_door
  x: 0
  y: 40
  w: 240
  h: 160
  fps: 2
```

```yaml
action: nspanel_haui.stop_camera_stream
data:
  device: "abc123..."
```

### What to expect

- **A frame the panel is still drawing is skipped, never queued.** Ask for more
  frames per second than the panel can paint and it simply skips more; it never
  falls behind. `stop_camera_stream` ends the stream, and so does the panel on its
  own: a page change, the display going to sleep, a TFT install, or a camera that
  stops answering (five failures in a row).
- **Only what changed is painted.** The hub keeps a model of what the panel is
  showing and repaints a rectangle only when the picture has really moved away
  from it — by more than `band` per colour channel. That threshold is what makes a
  camera usable at all: without it, sensor noise and a flickering lamp would
  repaint the whole picture every frame. Raise `band` on a noisy camera that
  repaints too much; lower it if a slow gradient looks patchy.
- **A still scene is free.** With nothing moving, no rectangles are sent — the
  panel and the camera keep running for nothing. A full repaint comes round every
  60 frames anyway, so a slow drift (a wall darkening through the evening) cannot
  stay wrong.
- **A camera that moves is expensive.** Pan, tilt or zoom moves every part of the
  picture, so a full-page rectangle at `cell: 8` costs about two thousand
  rectangles a frame — near a second per frame. Fit a fixed camera; if the picture
  must move, coarsen `cell` and lower `fps` until the log is quiet.
- **It is soft.** The picture is a grid of `cell`-pixel rectangles, so it looks
  like a mosaic of the size you pick. A 240x160 rectangle at `cell: 8` is 30x20
  blocks — recognisable people and shapes, not a photograph.
- **The stream coarsens itself.** A frame that would cost more than `max_runs` is
  drawn with bigger rectangles instead of taking longer, and the cell size stays
  there while the scene stays busy, so `cell` is a starting point.
- **It draws over the page you are on, and stops when you leave.** The rectangle
  covers whatever the page had there; the widgets of other panels are untouched.
  Surviving a page change would mean repainting a page the stream was never meant
  for, so it stops — start it again from the new page, or from an automation
  triggered by `nspanel_haui.page_changed`.
- **It needs firmware 0.5.9 or later,** the same `draw_runs` action `show_image`
  uses.
- **One stream per panel.** Starting a second stream on the same panel replaces the
  first.

Example: draw the doorbell while the doorbell rings, and stop it a minute later.

```yaml
automation:
  - alias: Show the doorbell on the panel
    triggers:
      - trigger: state
        entity_id: binary_sensor.doorbell
        to: "on"
    actions:
      - action: nspanel_haui.start_camera_stream
        data:
          device: "abc123..."
          camera: camera.front_door
          x: 0
          y: 40
          w: 240
          h: 160
          fps: 2
      - delay: "00:01:00"
      - action: nspanel_haui.stop_camera_stream
        data:
          device: "abc123..."
```

## Notifications

| Way | Options |
|-----|---------|
| `nspanel_haui.send_notification` action | All options |
| `notify.<device>` entities | Title and message only |
| ESPHome `send_notification` action | No `force_show` and no timeout; a notification that is not persistent only shows when the indicator is tapped |

### `nspanel_haui.send_notification`

Shows a notification on the panel. See [On the panel](#on-the-panel) for the queue, the indicator and dismissal.

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

#### On the panel

**Arriving**

- A new notification goes into a queue. The notification indicator starts to blink: the bell on the Clock, ClockTwo and Weather panels, or the notifications button in the header of other panels.
- A notification sent with `force_show` or `persistent` opens right away and wakes the display, except during a [schedule](editor/device.md#silent-times) entry with sound off.
- The queue holds up to 50 notifications. When it is full, the oldest one is dropped.
- A notification with the same title and message as a queued one replaces it. Its sound plays again and it moves to the end of the queue.

**Reading**

- Tap the indicator to open the notification, or a list when several are waiting. Opening them stops the blinking.
- **Dismiss** removes the notification from the queue. Closing the popup without dismissing keeps it.
- After a dismiss, the next waiting notification opens in its place.
- While a notification is open, the idle page waits. The display still dims and turns off on its normal timers; the next touch wakes it with the notification still showing.
- If you opened the notifications over the idle page, closing them returns to the idle page.

**Sound and timing**

- **Sounds are off by default.** They only play when the device's **Sound on notification** setting is on, see [Device settings → Sounds](editor/device.md#sounds).
- **Persistent** notifications repeat their sound every **Persistent sound interval** seconds and also open over the idle page. A [schedule](editor/device.md#schedule) entry with sound off still keeps the display dark. A `timeout` also ends a persistent notification.
- The [preset notification script](#preset-notification-script) has ready-made `info`, `warning`, `alert`, `critical` and `silent` notifications.

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

Updates normally run on their own, see [Updating](update.md). These actions and entities are for automations and for installing a specific version.

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

- **It answers.** The action returns the update state — `started` until the panel answers, then `installing`, `error`, … — so an automation can branch on it with `response_variable: result`.
- **A refusal fails the call.** Nothing matches the device, updates are off, an install is already running, or the panel cannot be reached: the action raises with the hub's reason instead of returning as if it started. Automations that relied on the old silent success need to handle the error.
- **The URL is checked first.** A non-http(s) address, an answer of `404`/`5xx`, a file larger than the display can hold, or a server that ignores range requests is refused with the reason before the panel is asked to download. If Home Assistant itself cannot reach the address, the install still starts — the panel's network may differ.
- **Progress.** The display reports no percentage. The state goes from *checking* to *installing* to *done*, or to *error* with the reason. You see it in the **Updates** sidebar, in the device's **Diagnostics** and on the **HAUI Display** entity.
- **The panel reports a failed upload itself.** Firmware from this release on sends the reason it could not install (no network, the server's answer, a refused display) as soon as the upload ends, so a failure shows in seconds instead of after the 20-minute timeout. Older firmware keeps the timeout-only reporting.
- **A file from a URL stays.** The hub does not replace it with the release TFT until the firmware version changes or Home Assistant restarts. Calling the action without `version` and `url` also installs the release TFT again.
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
- **Custom firmware stays custom.** A panel with firmware built from your own YAML is never offered the universal release firmware. Install your own builds with `url`. See [Other ways to update](update.md#other-ways-to-update).
- **Going back a release?** The display file is not downgraded on its own. Install the matching TFT with `nspanel_haui.update_tft` and `version`.

### HAUI Firmware update entity

Every panel has an `update.<device>_haui_firmware` entity.

- **Installed version:** the firmware on the panel.
- **Latest version:** the firmware of the latest release, or of the [manifest you configured](update.md#update-settings).
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

The firmware has an ESPHome action `esphome.<device>_upload_tft_url`. The hub uses it to pass the file's address to the panel. Prefer `nspanel_haui.update_tft` with `url`: the hub checks the address first, tracks the install and reports the panel's failure. Called directly, the action still uploads, but only the ESPHome log shows how it ended.

**From local file** in the **Updates** sidebar takes the same path: Home Assistant stages the file, hands the panel its temporary address and follows the install like a URL install, so it reports the same failures.

The former `esphome.<device>_upload_tft` action and the **Update Display** button no longer exist, see [Upgrading](../develop/upgrading.md#045).

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
