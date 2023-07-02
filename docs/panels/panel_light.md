# Panel Light

[< All Panels](README.md) | [Configuration](../Config.md) | [FAQ](../FAQ.md)

- [Panel Light](#panel-light)
  - [Visualization](#visualization)
  - [About](#about)
  - [Popup](#popup)
  - [Config](#config)

## Visualization

![Subpanel Light](../assets/subpanel_light.png)

![Panel Light](../assets/panel_light.png)

Light entity is off:

![Panel Light Off](../assets/panel_light_off.png)

Light entity is on / color temperature:

![Panel Light Temp](../assets/panel_light_temp.png)

Light entity is on / color:

![Panel Light Color](../assets/panel_light_color.png)

Light entity is on / effect is active:

![Panel Light Effect](../assets/panel_light_effect.png)

Popup:

![Popup Light](../assets/popup_light.png)

## About

`type: light`

The light entity panel allows to control a single light entity.

The functions available depend on the light entity being used. Only buttons for supported functions will appear.

## Popup

`type: popup_light`

`key: popup_light_key`

The light entity detail panel allows to control a single light entity.

The functions available depend on the light entity being used. Only buttons for supported functions will appear.

**If the entity is not available then the popup will close automatically.**

## Config

```yaml
panels:
  - type: light
    entity: light.example_light
```