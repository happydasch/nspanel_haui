---
title: Panel Media
description: Media panel configuration and options
---

# Panel Media
## About

`type: media`

The media entity panel allows to control a media entity. It displays the currently playing song and allows to control the media player. It allows to group / ungroup configured media players and allows to select media to play from a list of defined entries.

The album art, title, and artist info span the full panel width for a cleaner look. A vertical volume slider on the right replaces the previous bottom progress bar.

## Popup

`type: popup_media_player`

`key: popup_media_player_key`

## Config

Panel options are configured through the NSPanel HAUI editor in Home Assistant.



## Grouping / Ungrouping

It is possible to group/ungroup media_player entities. The available group members will be generated from `entities[1:]`, `group_items`, `group_members` of entity.



## Media

`sonos_favorites` allows to use sonos favorites as the source for media items. This entity needs to be enabled in home assistant. If `sonos_favorites_in_source` is True then the favorites will show up in the source popup.

- `media_favorites` allows to use media content IDs. The editor shows one editable row
  per favorite.
