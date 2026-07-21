---
title: Panel Media
description: Media panel — media player controls with grouping and favorites
---

# Panel Media

![](../assets/previews/panel-media.svg)

## About

The media panel controls a media player entity — TV, speaker, or receiver. It displays the currently playing song/album art, and provides play/pause, volume, track navigation, and grouping controls. The album art, title, and artist info span the full panel width for a cleaner look. A vertical volume slider on the right replaces the previous bottom progress bar.

## Popup Variant

The popup variant (`popup_media_player`) mirrors the main panel layout. It is used automatically when a media player entity is assigned as an item on another panel.

## How to configure

In the **panel editor**, set:

- **Item** (entity picker) — A media player entity to control. Required.

### Media Favorites

You can add media favorites as quick-select items. The editor shows one editable row per favorite:

- **Sonos Favorites** — Enable to use Sonos favorites as the source for media items. This requires the Sonos integration to be configured in Home Assistant. If **Sonos favorites in source** is enabled, favorites appear in the source selection popup.
- **Media Favorites** — Add individual media content items. Each entry has a name and content ID.

## Grouping / Ungrouping

If the media player supports grouping (e.g., Sonos speakers), you can group and ungroup devices. Available group members are determined automatically from the entity's `group_members` attribute.

## Display Behavior

- Album art, title, and artist span the full panel width.
- The vertical volume slider is on the right side.
- When nothing is playing, the panel shows the media player's current source or idle state.
