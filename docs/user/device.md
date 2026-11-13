---
title: Device Description
description: Device behavior, gestures, display states, hardware buttons, and sounds
---

# Device Description

This page explains how the panel behaves: gestures, the display going dim or off, the idle page, the hardware buttons, sounds and notifications. The settings named here are described in [Device Configuration](configuration/device.md).

## Device

### Gestures

Swipe from a screen edge to navigate. Unless you change it, a swipe does this:

| Swipe | Opens |
|-------|-------|
| Left / right | The next / previous panel |
| Up | About |
| Down | Settings |

You can change what a swipe does, turn it off, or add gestures of several swipes in a row using the **Gestures** option in **Manage this device** on the device's **Preview** view. See [Device Configuration → Gestures](configuration/device.md#gestures).

### Display State Dimmed, Off and On

The display has three brightness states:

| State | When |
|-------|------|
| **On** | Full brightness. Every touch brings the display back to this state. |
| **Dimmed** | After `timeout_dimming` seconds without interaction, when `use_auto_dimming` is on. |
| **Off** | After `timeout_display_off` seconds without interaction, when `use_auto_display_off` is on. |

Good to know:

- Dimming and switching off only change the brightness. They never change the panel that is shown.
- A hardware button press counts as an interaction when `reset_interaction_on_button` is on (the default).
- Changing a timeout does not count as an interaction.
- **Automations may control the switches.** The firmware has the switches **Use Auto-Dimming** and **Use Auto Display-Off**. The integration sets them only when you change the setting in the editor. It does not reset them on startup, on reconnect or on a page change, so an automation can switch them on a schedule.
- **Without a connection to Home Assistant** the display dims after the dimming timeout, even when auto-dimming is off. It never turns off while disconnected.
- **A schedule** can change the brightness, the dimming and the display-off at set times, for example at night. While it has entries, the integration sets the **Use Auto Display-Off** switch itself. See [Schedule](configuration/device.md#schedule).

### Idle Page

The idle page is a panel that opens on its own after a time without interaction, like a screensaver. This is called **automatic page switching**:

- It is active when `use_auto_page` is on and at least one idle panel is assigned (`idle_panel` or `idle_panel_extra`).
- The idle page opens after `timeout_page` seconds without interaction, showing the next panel in the assigned list. The list cycles on each automatic page switch.
- It only changes the panel. The display can be on, dimmed or off while the idle page is shown.
- Without any assigned idle panels, the current panel simply stays.
- A reconnect to Home Assistant, for example after a restart, does not count as an interaction. The panel shows the previous page again, and the timeout starts over.

### Waking up

A touch or a button press wakes the panel. What happens depends on the state:

| State | Touch | Hardware button |
|-------|-------|-----------------|
| Display off, idle page shown | First touch wakes the display, second touch leaves the idle page | Wakes the display and leaves the idle page |
| Display on or dimmed, idle page shown | Leaves the idle page | Leaves the idle page |
| No idle page shown | Wakes the display | Wakes the display |

A hardware button only wakes the panel when `reset_interaction_on_button` is on.

### Return Panel after Wakeup

When you leave the idle page, the display returns to the panel that was open before. It goes to the home panel instead when:

- `snapshot_max_age_seconds` is `0` (never restore), or
- `snapshot_max_age_seconds` is greater than `0` and more than that many seconds have passed, or
- `auto_navigate_home_timeout` passed while the idle page was shown.

The default (`-1`) always returns to the previous panel. See [Idle & Wake Behavior](configuration/device.md#idle-wake-behavior).

### Hardware Buttons

Each of the two buttons either switches its built-in relay or toggles a Home Assistant entity:

- `use_relay_left` / `use_relay_right` on (default): the button switches the relay.
- Off: the button toggles the entity set in `button_left_entity` / `button_right_entity`. The entity is toggled when you release the button, so holding it does not toggle again.

The relays keep their state across a restart, a firmware update and a power loss, so connected loads do not switch off during an update.

With `reset_interaction_on_button` on (the default), a button press also wakes the display and leaves the idle page. With it off, the button only switches its relay or entity. In Home Assistant this is the panel's **Use Button Interaction** switch.

### Sounds

The panel can play a sound on two occasions. Both are off by default:

- `sound_on_startup` — when the panel starts
- `sound_on_notification` — when a notification arrives

### Silent times

A [schedule](configuration/device.md#schedule) entry with sound off makes the panel silent during its time window:

- No sounds are played. The repeating sound of a persistent notification pauses and continues when the entry ends.
- Notifications are still collected and shown, but they do not wake the display.
- The time window can cross midnight, for example 22:00–07:00, and can start or end at sunrise or sunset.

You set this in the **Schedule** option in **Manage this device** on the device's **Preview** view.

## Panels

A panel is one screen on the display. You can add as many as you like and move between them. See the [Panels overview](panels/README.md) for all panel types.

On a panel that controls a single entity, the header shows the entity's name. Otherwise it shows the panel's title, or the name of the panel type when the title is empty. See [Panel Configuration](configuration/panels.md#standard-fields).

### Notifications

The panel can show notifications sent from Home Assistant. See [Services](services.md#nspanel_hauisend_notification) for how to send one and [Popup Notify](panels/popup_notify.md) for how the popup looks.

**Arriving**

- A new notification goes into a queue. The notification indicator starts to blink: the bell on the Clock, ClockTwo and Weather panels, or the notifications button in the header of other panels.
- A notification sent with `force_show` or `persistent` opens right away and wakes the display, except during [silent times](#silent-times).
- The queue holds up to 50 notifications. When it is full, the oldest one is dropped.
- A notification with the same title and message as a queued one replaces it. Its sound plays again and it moves to the end of the queue.

**Reading**

- Tap the indicator to open the notification, or a list when several are waiting. Opening them stops the blinking.
- **Dismiss** removes the notification from the queue. Closing the popup without dismissing keeps it.
- After a dismiss, the next waiting notification opens in its place.
- While a notification is open, the idle page waits. The display still dims and turns off on its normal timers; the next touch wakes it with the notification still showing.
- If you opened the notifications over the idle page, closing them returns to the idle page.

**Options**

- **Icon and colour** — a notification can have an icon and an icon colour. Without an icon the message uses the whole text area.
- **Sound** — `notification` by default, another sound, or `none`. Sounds only play when `sound_on_notification` is on.
- **Persistent** — the notification opens immediately, repeats its sound every `persistent_sound_interval` seconds (default 5) and opens its popup again about every 60 seconds until it is dismissed. It also opens over the idle page. Silent times still keep the display dark.
- **Timeout** — removes the notification after a number of seconds, counted from the moment it is sent. It can expire before anyone has seen it. Without a timeout it stays until dismissed.

The [preset notification script](services.md#preset-notification-script) has ready-made `info`, `warning`, `alert`, `critical` and `silent` notifications.

**Where the notifications button sits**

The button is drawn in the accent colour while notifications are waiting. It uses a free slot on the right of the header. On a panel that needs both right slots, such as a grid or row with several pages, it takes the place of the idle button on the home panel, so waiting notifications stay reachable.

**Ways to send**

| Way | Options |
|-----|---------|
| `nspanel_haui.send_notification` service | All options |
| `notify.<device>` entities | Title and message only |
| ESPHome `send_notification` action | No `force_show` and no timeout; a notification that is not persistent only shows when the indicator is tapped |

**In the editor**

The editor has a **Notifications** inbox in its header. It lists the notifications waiting on all your panels and updates as they arrive. Dismissing one there removes it from the panel too.
