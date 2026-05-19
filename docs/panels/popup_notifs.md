# Popup Notifs

[< All Panels](README.md) | [Configuration](../Config.md) | [FAQ](../FAQ.md)

- [Popup Notifs](#popup-notifs)
  - [About](#about)
  - [Sending notifications](#sending-notifications)
  - [Persistent notifications](#persistent-notifications)
  - [Device config](#device-config)

> For the simple one-shot popup used internally, see [Popup Notify](popup_notify.md).

## About

`type: popup_notifs`

`key: popup_notifs`

The notification panel shows all queued notifications. It opens automatically when the notification bell icon is tapped on a panel that has `show_notifications: true` (e.g. clock, weather).

Notifications are kept in the queue until explicitly dismissed by the user. The panel supports navigating between multiple notifications with prev/next buttons and dismissing them one at a time.

## Sending notifications

Notifications are sent from an ESPHome script or from Python/Hub.

**ESPHome script:**

```yaml
- service: esphome.<device_name>_send_notification
  data:
    title: "Alert"
    message: "Motion detected in hallway"
    icon: "mdi:motion-sensor"   # optional - pass empty string "" to omit
    timeout: 0                  # seconds before auto-dismiss; 0 = no timeout
    persistent: false           # true = sound loops until dismissed (see below)
```

**Python / Hub:**

```python
# via device shorthand
self.app.device.notify(
    title="Alert",
    message="Motion detected in hallway",
    icon="mdi:motion-sensor",   # optional
    timeout=0,
    persistent=False,
)

# or via the notification controller directly
self.app.controller["notification"].send_notification(
    title="Alert",
    message="Motion detected in hallway",
    icon="mdi:motion-sensor",
    timeout=0,
    persistent=False,
)
```

**Icon** is optional. Pass an empty string `""` (or omit when calling from Python) to display the message in full-width without an icon.

## Persistent notifications

When `persistent: true` the notification sound loops at a regular interval until the notification is dismissed by the user. The dismiss button is highlighted in accent color to make persistent notifications visually distinct.

- Sound starts playing immediately when the notification is received.
- Sound repeats every `persistent_sound_interval` seconds (default `5`).
- Sound stops as soon as the notification is dismissed or all persistent notifications are cleared.

Persistent notifications are intended for alerts that require user attention - for example alarms, door sensors, or smoke detectors.

## Device config

The following device-level config keys affect notification behaviour:

```yaml
device:
  sound_on_notification: true       # play sound for normal (non-persistent) notifications
  persistent_sound_interval: 5      # seconds between repeated sounds for persistent notifications
```
