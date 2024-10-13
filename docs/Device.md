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

The device is responsible for gestures, display state and its hardware buttons. The device functionality is implemented in `haui/device.py`. The communication between server and client is described in [Communication.md](Communication.md).

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

The sleep panel will be exited if:

Dimmed:
    - touch: first touch exits panel
    - button: sets display state to on

Sleep:
    - touch: first touch wakes up, second touch exits panel
    - button: wakes up and sets display state to on

The exact behaviour is configurable.

### Return Panel after Wakeup

The display will return to:

Dimmed:
    - previously open panel

Sleep:
    - home panel

The opening of the previous panel can be disabled. See the config value `always_return_to_home` to configure this.

### Hardware Buttons

The device can either control the internal relays or toggle a entity.

It is also possible to completely disable the hardware buttons to be used for checking interactions and change the display state and / or to prevent the display from waking up.

See `switch.nspanel_haui_use_button_interaction` in HA to switch on / off the button interaction.

See the config value `home_on_button_toggle` to go to the home panel after button was pressed.

### Sounds

The device will play sounds on different occasions. The sounds can be disabled.

- `sound_on_startup`
- `sound_on_notification`

## Panels

The device supports multiple different panels which are displayed on the display. Each panel can be configured and a complex navigation hierachy is possible. To get an overview of all available panels, see [Panels overview](panels/README.md).

### Notifications

The device can receive notifications and display them. The notifications are available until they are discarded on the display.
