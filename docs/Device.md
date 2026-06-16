# Device Description

- [Device Description](#device-description)
  - [Device](#device)
    - [Gestures](#gestures)
    - [Display State Sleep, Dimmed and On](#display-state-sleep-dimmed-and-on)
    - [Sleep Panel](#sleep-panel)
    - [Waking up](#waking-up)
    - [Return Panel after Wakeup](#return-panel-after-wakeup)
    - [Hardware Buttons](#hardware-buttons)
    - [Sounds](#sounds)
  - [Panels](#panels)
    - [Notifications](#notifications)

## Device

The device is responsible for gestures, display state and its hardware buttons. The device functionality is implemented in `haui/device.py`. Per-device configuration constants (field names, defaults) live in `haui/device_config.py`. The communication between server and client is described in [Communication.md](Communication.md).

### Gestures

The device supports touch gestures.

### Display State Sleep, Dimmed and On

When running the device will be in different states. The timeouts for each state are configurable in HA. The dimmed and sleep state can be enbled or disabled.

If a user interacts with the device, the display state is `on`.

If a user did not interact for some time, then the device will go into a `dimmed` display state. After another period of time the display will then switch to the `sleep` state.

### Sleep Panel

The device will open a sleep panel after a set amount of time. This will only happen if a sleep panel is set.

The sleep panel will be started after a timeout.

### Waking up

The wakeup of the display can happen from different states: dimmed or sleep.

When the user touches the display **anywhere** the display wakes and the sleep/wake
panel is exited immediately — restoring the home or previously viewed panel in a
single touch. The same applies to hardware button presses.

Dimmed:
    - touch: exits to home / previous panel
    - button: sets display state to on and exits

Sleep:
    - touch: wakes and exits to home / previous panel
    - button: wakes and exits to home / previous panel

### Return Panel after Wakeup

The display will return to:

Dimmed:
    - previously open panel
    - if `snapshot_max_age_seconds` is bigger than 0 then
      the display will return to home panel if more than the given
      seconds passed

Sleep:
    - home panel

The opening of the previous panel can be disabled. Set `snapshot_max_age_seconds` to `0` to always go to the home panel.

### Hardware Buttons

The device can either control the internal relays or toggle an entity.
Use `use_relay_left` / `use_relay_right` to control whether the left/right
button toggles its internal relay (default `true`) or a configured entity.

It is also possible to completely disable the hardware buttons to be used for checking interactions and change the display state and / or to prevent the display from waking up.

When `reset_interaction_on_button` is enabled (the default), the display wakes immediately on button **press** — there is no need to hold the button until release. The relay/entity toggle still happens on release so a held button does not spam toggles.

See `switch.nspanel_haui_use_button_interaction` in HA to switch on / off the button interaction.

### Sounds

The device will play sounds on different occasions. The sounds can be disabled.

- `sound_on_startup`
- `sound_on_notification`

## Panels

The device supports multiple different panels which are displayed on the display. Each panel can be configured and a complex navigation hierachy is possible. To get an overview of all available panels, see [Panels overview](panels/README.md).

### Notifications

The device can receive notifications and display them. Notifications remain in the queue until dismissed by the user on the display.

Notifications support an optional icon and an optional `persistent` flag. When `persistent` is set to true the notification sound loops at a regular interval until the notification is explicitly dismissed - useful for alerts that require user attention.

See [Popup Notification](panels/popup_notifs.md) for full details and usage examples.
