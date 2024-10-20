# Panel ClockTwo

[< All Panels](README.md) | [Configuration](../Config.md) | [FAQ](../FAQ.md)

- [Panel ClockTwo](#panel-clocktwo)
  - [About](#about)
  - [Config](#config)
    - [Background](#background)
    - [Change language](#change-language)
    - [Custom colors](#custom-colors)
    - [Show Notifications](#show-notifications)
  - [Screens](#screens)

## About

`type: clocktwo`

The clocktwo panel shows the current time by using written text on the display.

## Config

```yaml
panels:

  # clocktwo panel
  - type: clocktwo

  # clocktwo panel with a different background
  - type: clocktwo
    background: dog_1

  # clocktwo panel with a background and with custom colors
  - type: clocktwo
    clock_language: en
    background: dog_1
    off_color:
    letter_color:
    special_color:
```

### Background

The clocktwo panel can have different background images. To set a background use the `background` param.

Possible values:

- default
- spring
- summer
- autumn
- winter
- dog_1
- dog_2
- cat

Dynamic background values are possible using HomeAssistant templates.

`background: template:{...}`

The return value should match a background name.

### Change language

The clocktwo panel supports multiple languages. Set the language by using `clock_language`.

### Custom colors

The colors of the clocktwo can be changed:

Supported colors:

- `off_color`
- `letter_color`
- `special_color`

### Show Notifications

The notifications icon can be hidden by setting `show_notifications` to `False`

## Screens

![Panel ClockTwo](../assets/panel_clocktwo.png)

![Panel ClockTwo Simple](../assets/panel_clocktwo_simple.png)

![Panel ClockTwo Background](../assets/panel_clocktwo_background.png)
