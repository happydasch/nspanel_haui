---
title: Panel Cover
description: Cover panel configuration and options
---

# Panel Cover
## About

`type: cover`

The cover entity panel allows to control a single cover entity. Open, stop, and close buttons are shown based on the features supported by the entity. A vertical position slider is shown when the entity supports `set_position`.

## Popup

`type: popup_cover`

`key: popup_cover`

## Config

```yaml
panels:
  - type: cover
    entity: cover.example_cover
```
