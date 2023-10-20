# Panel Media

[< All Panels](README.md) | [Configuration](../Config.md) | [FAQ](../FAQ.md)

- [Panel Media](#panel-media)
  - [About](#about)
  - [Popup](#popup)
  - [Config](#config)
  - [Grouping / Ungrouping](#grouping--ungrouping)
  - [Media](#media)
  - [Screens](#screens)

## About

`type: media`

The media entity panel allows to control a media entity. It displays the currently playing song and allows to control the media player. It allows to group / ungroup configured media players and allows to select media to play from a list of defined entries.

## Popup

`type: popup_media_player`

`key: popup_media_player_key`

## Config

```yaml
panels:
  - type: media
    entity: media_player.example_media_player
    sonos_favorites: sensor.sonos_favorites
    sonos_favorites_in_source: false
    media_favorites: []
    group_entities: []
```

## Grouping / Ungrouping

It is possible to group/ungroup media_player entities. The available group members will be generated from `entities[1:]`, `group_entities`, `group_members` of entity.

```yaml
panels:
  - type: media_player
    entity: media_player.media_player_to_control
    group_entities:
      media_player.group_member_1
      media_player.group_member_2
      media_player.group_member_3

or

panels:
  - type: media_player
    entity: media_player.media_player_to_control
    entities:
      - entity: media_player.group_member_1
      - entity: media_player.group_member_2
      - entity: media_player.group_member_3

or

panels:
  - type: media_player
    entities:
      - entity: media_player.media_player_to_control
      - entity: media_player.group_member_1
      - entity: media_player.group_member_2
      - entity: media_player.group_member_3
```

## Media

`sonos_favorites` allows to use sonos favorites as the source for media items. This entity needs to be enabled in home assistant. If `sonos_favorites_in_source` is True then the favorites will show up in the source popup.

- `media_favorites` allows to use any content defined.

```yaml
sonos_favorites: sensor.sonos_favorites
sonos_favorites_in_source: false
media_favorites:
  - name: Media Name
    content_id: content_id of media to play
    content_type: content_type (music, ), # Default: music, https://github.com/home-assistant/core/blob/dev/homeassistant/components/media_player/const.py#L103C1-L103C26
  - name: Another Media Name
    content_id: ""
```

## Screens

![Subpanel Media](../assets/subpanel_media.png)

![Panel Media](../assets/panel_media.png)
