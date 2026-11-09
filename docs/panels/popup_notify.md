---
title: Popup Notify
description: Notify popup — ad-hoc notifications with action buttons
---

# Popup Notify

## About

The notification popup is used for one-shot, ad-hoc popups — for example to notify the user about errors or to prompt a yes/no decision. It supports optional buttons and an optional icon colour.

It shows the notifications queued by the `nspanel_haui.send_notification` service and the notify entities: either right away with `force_show` or `persistent`, or when the user taps the notification indicator. `force_show` never takes the place of a notification popup or list that is already open — the new notification waits in the queue and opens when the current one is dismissed. For these, the popup's right button is **Dismiss**, which removes the notification from the queue. Persistent notifications also re-open their popup over the idle page and repeat their sound every `persistent_sound_interval` seconds (default 5) when the device's `sound_on_notification` setting is on (off by default), until dismissed; quiet hours still keep the display dark. A popup that opens on its own wakes the display (except during quiet hours); while it is open the display still dims and turns off on its normal timers — see [Notifications](../device.md#notifications). The queue holds up to 50 notifications; when it is full, the oldest one is dropped. The icon is coloured by the notification's `icon_color`; without one it uses the theme's text colour. A notification sent without an icon shows none.

The text size is the largest font — large, medium or small — at which the whole message fits on one page of the popup's text area, measured with the display fonts' real character widths, so lines break between words exactly where the display shows them. A message that does not fit even at the small font is split into static pages; the title shows a `(page/total)` counter and the header's inner-right button advances to the next page. Paging is manual — nothing advances on its own — and the button disappears on the final page, which stays visible, so long messages are readable page by page instead of being truncated. The `text_size` field on `nspanel_haui.send_notification` and the `send_notification` ESPHome action overrides the automatic choice per notification with a fixed font size (1-3).

Long notification titles and queue-list labels are shortened with `..` to fit their widgets. The detail-popup message is paged rather than shortened.

## How to configure

This popup is opened by the integration. In the editor's **Popups** section its title and default icon colour can be changed (see [System Panel Overrides](../configuration/panels.md#system-panel-overrides)). Parameters when opening it programmatically:

- `notification`, `title` — Message text and title. Line breaks in the message (`\n`) render as line breaks on the display.
- `icon` (optional) — Shown only when set, beside the text (above it in portrait). When omitted, no icon is displayed and the text uses the icon's area too: the full width in landscape, the full height in portrait, so more text fits on each page. `icon_color` colours it.
- `btn_left`, `btn_right` (optional) — Button labels; a button is shown only when set. Colors via `btn_left_color`, `btn_left_back_color` and the `btn_right_*` equivalents.
- `icon_color` (optional) — Icon colour in any `parse_color_value` format (`#rrggbb`, RGB565 int, `[r, g, b]`, integer string). Leave it empty (or unset) for the theme's text colour.
- `text_size` — `auto` (default: the largest font that fits the message on one page) or a font size 1-3, paged at that size when the message does not fit. The per-notification `text_size` field on the service/actions overrides this panel value.
- `close_on_button` — Close when a button is pressed. Default: true.
- `button_callback_fnc`, `close_callback_fnc` — Callbacks.

Queued-notification popups do not use the popup's generic `close_timeout`.
Navigating away from a popup does not dismiss its notification; it stays queued
until dismissed or until its optional `timeout` expires. The notification
timeout countdown begins when the item is queued, not when its popup opens, and
expiry removes it from the queue (opening the next queued notification when
appropriate). A programmatic `open_panel` popup that is not a queued notification
can still use `close_timeout` to close itself after a number of seconds.

## Using the service

Notifications are triggered from automations or scripts using the `nspanel_haui.send_notification` service. See [Services](../services.md) for full details.

## For developers

If you are writing a custom integration or extension that needs to open a notification programmatically with callbacks, see [Hub](../hub.md) for the internal API.
