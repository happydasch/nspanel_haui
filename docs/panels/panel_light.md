---
title: Panel Light
description: Light panel configuration and options
---

# Panel Light
## About

`type: light`

The light entity panel allows to control a single light entity.

The functions available depend on the light entity being used. Only buttons for supported functions will appear.

## Popup

`type: popup_light`

`key: popup_light_key`

## Config

```yaml
panels:
  - type: light
    entity: light.example_light
    show_kelvin: false  # false = Mireds (default), true = Kelvin for color temperature display
```
