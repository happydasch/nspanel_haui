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

The display brightness is managed by the ESPHome firmware: `on` at full brightness, `dim` after `timeout_dimming` seconds of inactivity (when `use_auto_dimming` is enabled), and `off` (brightness zero) after `timeout_display_off` seconds (when `use_auto_display_off` is enabled). Every touch resets the firmware's brightness timer and the hub's separate page-activity clock; a hardware button press counts as an interaction when `reset_interaction_on_button` is enabled (the default). These interactions restore full brightness. Changing either timeout recalculates the display state against the existing interaction timer; changing a timeout does not count as an interaction. The dimmed/off state is purely a brightness behavior — it never switches pages and needs no panel configured.

The firmware decides brightness from the live **Use Auto-Dimming** and **Use Auto Display-Off** switch states. HAUI does not reapply those states on startup, reconnect, page changes, or unrelated settings saves, so Home Assistant automations can own their timing. Saving a changed toggle in device settings applies that value once; subsequent automation changes remain in control. Day/Night profiles may change timeouts and brightness, but never rewrite either toggle.

After its configured dimming timeout, a disconnected device transitions to dim regardless of the auto-dimming switch. It stays awake and never automatically transitions to off while disconnected; both auto switches remain untouched. On reconnect, normal timeout behavior resumes using the current live switch states.

The **Day/Night Profiles** select different brightness, dim/page/display-off timeouts, and idle-page destinations by a fixed local window or sunrise/sunset schedule. For fixed windows, Night starts at the configured start time and ends immediately before the configured end time. Profile changes do not alter the live auto-dimming or auto-display-off switches.

Separate from the brightness is **automatic page switching**: when `use_auto_page` is enabled, the hub opens the configured idle page (`idle_panel`) after `timeout_page` seconds of inactivity, without dimming or turning the display off. It re-reads both settings and the activity clock once per second, so a changed timeout applies on the next tick. If a page holds automatic switching after the deadline has passed, the idle page opens on the next check after the hold ends, unless an interaction has since reset the clock. A hub reconnect (for example after a Home Assistant restart) does not count as an interaction: the restored page is displayed first and the page timeout then starts again from the reconnect.

### Idle Page

When `use_auto_page` is enabled and an `idle_panel` is configured, the hub opens that panel after the page timeout as a screensaver-style idle page. The idle page is a navigation target only — the display can be off (`use_auto_display_off`), dimmed, or fully on while it is shown, and none of those require it. With no idle page configured, automatic page switching simply stays on the current panel.

Day and Night idle destinations are independent. An empty `night_idle_panel`
disables the idle page at night; it never inherits the Day `idle_panel`. If
automatic page switching is enabled for the active profile and its idle key is
empty while the other profile has one configured, the hub logs a warning.

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
- `snapshot_max_age_seconds` is bigger than `0` and more than that many seconds have passed, or
- `auto_navigate_home_timeout` passed while the idle page was shown.

The default (`-1`) always restores the previous panel. See
[Device Configuration](configuration/device.md) for the setting.

### Hardware Buttons

The device can either control the internal relays or toggle an entity. Use `use_relay_left` / `use_relay_right` to control whether the left/right button toggles its internal relay (default `true`) or a configured entity.

When `reset_interaction_on_button` is enabled (the default), a hardware button press resets the interaction timer and wakes the display; it also exits the idle page. When disabled, the button still toggles its configured relay or entity, but it does not reset the timer, wake the display, or exit the idle page.

The ESPHome firmware toggles an internal relay on button **press**. When a button is assigned to a Home Assistant entity instead, the hub toggles that entity on release, so holding the button does not repeat the toggle.

See `switch.nspanel_haui_use_button_interaction` in HA to switch on / off the button interaction.

### Sounds

The device can play sounds on different occasions. Both are off by default; enable them in the device settings.

- `sound_on_startup`
- `sound_on_notification`

### Quiet Hours

The device supports a do-not-disturb (DND) mode that silences sounds during configurable quiet
hours. When `use_do_not_disturb` is enabled, no sounds are played within the
`quiet_hours_start`–`quiet_hours_end` time window; notifications are still queued and shown,
but a notification does not wake the display. A persistent notification's repeating sound
stays silent during quiet hours and resumes when they end.
The window supports overnight ranges (e.g., 22:00–07:00). This is configured in the Device
Settings dialog under the **Notifications** section.

## Panels

The device supports multiple different panels which are displayed on the display. Each panel can be configured and a complex navigation hierarchy is possible. To get an overview of all available panels, see [Panels overview](panels/README.md).

For entity-based panels, an available entity name takes precedence over the configured panel title. Without an entity name, the configured title is used; if that is empty, the translated panel-type title is shown. See [Panel Configuration](configuration/panels.md#standard-fields) for the title field and its fallbacks.

### Notifications

The device can receive notifications and display them. Notifications normally
stay in the queue until dismissed on the display. The `nspanel_haui.send_notification`
service also supports an optional `timeout` that removes a notification after a
number of seconds; its countdown starts when the notification is queued, so it
can expire while waiting to be shown. Omitting `timeout` or setting it to `0`
keeps the notification until dismissed. Queued notifications play through: when
a notification popup is dismissed or its notification is removed while more
notifications are queued, the next one opens in its place, so none is shown only
once and skipped.

New notifications make the notification indicator blink (the bell on the Clock, Clock Two and Weather panels, or the notifications header button otherwise). The notifications header button prefers a right-side slot (secondary, or primary in a single-nav layout); when a panel claims both right slots — e.g. a grid/row with pagination — the button moves to the idle button's slot on the home panel instead, so unread notifications stay reachable even though the idle/sleep button is displaced. Tapping it opens the notification popup, or a list when several are queued; opening them stops the blinking. Each notification popup has a **Dismiss** button that removes the notification from the queue. Closing the popup without dismissing keeps it queued. If notifications are opened over the idle page, closing the popup/list returns to the idle page; a touch then exits idle as usual.

A notification popup that opens on its own — a force-shown notification, or a persistent notification re-opening its popup — wakes the display, except during [quiet hours](#quiet-hours). While a notification popup is open the automatic page switch waits, so the popup stays on screen until it is dismissed or closed, but the display still dims and turns off on its normal timers; the next touch wakes it with the popup still showing.

Notifications support an optional icon; when none is supplied, the popup shows none and the message uses the full text area. The severity (`info`, `warning` or `critical`) colours the icon when one is set. When `persistent` is set to true the notification sound loops every `persistent_sound_interval` seconds (default 5) and its popup re-opens about every 60 seconds until the notification is dismissed or its timeout expires — useful for alerts that require user attention. Notifications of type `critical` play the `alert` sound instead of the `notification` sound. While the idle page is shown, only a `critical` persistent notification re-opens its popup over it; other severities wait until the user returns to a real panel. The queue holds up to 50 notifications; when it is full, the oldest one is dropped. Sending a repeat of a queued notification replaces the queued copy: its sound plays again and the new copy goes to the end of the queue.

The HA service can set the optional timeout. The standard `notify` entities and ESPHome `send_notification` action do not expose it. The HA service and notify entities force-show persistent notifications immediately; the ESPHome action does not force-show them, but its popup opens about a second after the action (unless a notification popup or list is already open) and re-opens every 60 seconds until dismissed. See [Services](services.md#nspanel_hauisend_notification) for fields and defaults.

See [Popup Notify](panels/popup_notify.md) for full details and usage examples.

The HAUI editor also has a **Notifications** inbox in its header. It shows the notifications currently queued across the hub's devices, updates as notifications arrive or are dismissed, and lets you dismiss an item from the editor; dismissing it removes it from the same queue used by the panel.
