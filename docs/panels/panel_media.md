# Panel Media

[< All Panels](README.md) | [Configuration](../Config.md) | [FAQ](../FAQ.md)

- [Panel Media](#panel-media)
  - [About](#about)
  - [Popup](#popup)
  - [Config](#config)
  - [Screens](#screens)

## About

`type: media`

The media entity panel allows to control a media entity. It displays the currently playing song and allows to control the media player.

## Popup

`type: popup_media`

`key: popup_media_key`

## Config

```yaml
panels:
  - type: media
    entity: media_player.example_media_player
```

## Screens

![Subpanel Media](../assets/subpanel_media.png)

![Panel Media](../assets/panel_media.png)
