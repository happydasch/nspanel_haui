---
title: Device Description
description: Device behavior, gestures, display states, hardware buttons, and sounds
---

# Device Description
## Device

The device is responsible for gestures, display state and its hardware buttons. The communication between server and client is described in [communication.md](communication.md).

### Gestures

The device supports touch gestures: `swipe_left`, `swipe_right`, `swipe_up`
and `swipe_down`. A single swipe navigates (left/right through the navigation
panels, up to About, down to Settings). Gesture sequences — several swipes in
order within a time limit — open a panel of your choice; configure them per
device under Device Settings → Gestures (see
[Device Configuration](configuration/device.md#gestures)).

### Display State Dimmed, Off and On

The display brightness is managed by the ESPHome firmware: `on` at full brightness, `dimmed` after `timeout_dimming` seconds of inactivity (when `use_auto_dimming` is enabled), and `off` (brightness zero) after `timeout_display_off` seconds (when `use_auto_display_off` is enabled). Every touch or hardware button press resets the interaction timer and the brightness returns to full. The dimmed/off state is purely a brightness behavior — it never switches pages and needs no panel configured.

When a **display-off schedule** is configured (`use_sleep_schedule` plus `sleep_schedule_start`/`sleep_schedule_end`, see [Device Configuration](configuration/device.md#display-dimming-off)), the off-after-`timeout_display_off` behavior only applies inside the configured window (e.g. at night). Outside the window the display never turns off automatically — it only dims, so the idle page stays visible around the clock. The hub drives `switch.<device>_use_auto_display_off` by the clock and re-applies it on start, reconnect, setting changes and at every window boundary, so no automation is needed to keep the switch in the right state.

Separate from the brightness is **automatic page switching**: when `use_auto_page` is enabled, the hub opens the configured idle page (`idle_panel`) after `timeout_page` seconds of inactivity, without dimming or turning the display off.

### Idle Page

When `use_auto_page` is enabled and an `idle_panel` is configured, the hub opens that panel after the page timeout as a screensaver-style idle page. The idle page is a navigation target only — the display can be off (`use_auto_display_off`), dimmed, or fully on while it is shown, and none of those require it. With no idle page configured, automatic page switching simply stays on the current panel.

### Waking up

Waking the device works from any state and **never requires an idle page to be configured**:

- With the **idle page shown**, a touch exits it and restores the panel you were on (or the home panel, see below). When the display is on or dimmed, a single touch is enough (the user can see the screen); when the display is off, the first touch only wakes the display and a second touch exits.
- With **no idle page shown**, the first touch just wakes the display (brightness back to full) — there is nothing to exit.
- A hardware button press always wakes the display and exits the idle page in a single press (when `reset_interaction_on_button` is enabled). A button cannot hit anything on the screen, so it does not need the two-touch protection.

Off with idle page shown:
    - touch: first touch wakes, second touch exits to home / previous panel
    - button: wakes and exits to home / previous panel

Dimmed or on with idle page shown:
    - touch: exits to home / previous panel in a single touch
    - button: wakes and exits to home / previous panel

### Return Panel after Wakeup

When the idle page is exited, the display returns to the panel that was open before it. It goes to the home panel instead when:

- `snapshot_max_age_seconds` is `0` (never restore), or
- `snapshot_max_age_seconds` is bigger than `0` and more than that many seconds have passed.

The default (`-1`) always restores the previous panel. See
[Device Configuration](configuration/device.md) for the setting.

### Hardware Buttons

The device can either control the internal relays or toggle an entity.
Use `use_relay_left` / `use_relay_right` to control whether the left/right
button toggles its internal relay (default `true`) or a configured entity.

It is also possible to completely disable the hardware buttons to be used for checking interactions and change the display state and / or to prevent the display from waking up.

When `reset_interaction_on_button` is enabled (the default), the display wakes immediately on button **press** — there is no need to hold the button until release. The internal relay toggles on press (in the ESPHome firmware); a configured entity toggles on release, so a held button does not spam toggles.

See `switch.nspanel_haui_use_button_interaction` in HA to switch on / off the button interaction.

### Sounds

The device can play sounds on different occasions. Both are off by default; enable them in the device settings.

- `sound_on_startup`
- `sound_on_notification`

### Quiet Hours

The device supports a do-not-disturb (DND) mode that silences sounds during configurable quiet
hours. When `use_do_not_disturb` is enabled, no sounds are played within the
`quiet_hours_start`–`quiet_hours_end` time window; notifications are still queued and shown.
The window supports overnight ranges (e.g., 22:00–07:00). This is configured in the Device
Settings dialog under the **Notifications** section.

## Panels

The device supports multiple different panels which are displayed on the display. Each panel can be configured and a complex navigation hierarchy is possible. To get an overview of all available panels, see [Panels overview](panels/README.md).

### Notifications

The device can receive notifications and display them. Notifications stay in the
queue until dismissed by the user on the display — there is no automatic
dismissal. Queued notifications play through: when a notification popup is
dismissed (or its notification is removed) while more notifications are queued,
the next one opens in its place, so none is shown only once and skipped.

New notifications make the notification indicator blink (the bell on the Clock, Clock Two and Weather panels, or the notifications header button otherwise). The notifications header button prefers a right-side slot (secondary, or primary in a single-nav layout); when a panel claims both right slots — e.g. a grid/row with pagination in navigation — the button moves to the idle button's slot on the home panel instead, so unread notifications stay reachable even though the idle/sleep button is displaced. Tapping it opens the notification popup, or a list when several are queued; opening them stops the blinking. Each notification popup has a **Dismiss** button that removes the notification from the queue. Closing the popup without dismissing keeps it queued.

Notifications support an optional icon; when none is supplied, the severity selects a default one (`info`, `warning` or `critical`). When `persistent` is set to true the notification sound loops every `persistent_sound_interval` seconds (default 5) and its popup re-opens about every 60 seconds until the notification is dismissed - useful for alerts that require user attention. Notifications of type `critical` play the `alert` sound instead of the `notification` sound. While the idle page is shown, only a `critical` persistent notification re-opens its popup over it; other severities wait until the user returns to a real panel. The queue holds up to 50 notifications; when it is full, the oldest one is dropped. Sending a repeat of a queued notification replaces the queued copy: its sound plays again and the new copy goes to the end of the queue.

The HA service and notify entities force-show persistent notifications immediately; the ESPHome actions do not force-show them, but their popup opens about a second after the action (unless a notification popup or list is already open) and re-opens every 60 seconds until dismissed. See [Services](services.md#nspanel_hauisend_notification) for fields and defaults.

See [Popup Notify](panels/popup_notify.md) for full details and usage examples.
