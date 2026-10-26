---
title: Popup Notify
description: Notify popup — ad-hoc notifications with action buttons
---

# Popup Notify

## About

The notification popup is used for one-shot, ad-hoc popups — for example to notify the user about errors or to prompt a yes/no decision. It supports optional buttons and a severity-coloured icon.

It shows the notifications queued by the `nspanel_haui.send_notification` service and the notify entities: either right away with `force_show`, or when the user taps the notification indicator. `force_show` never takes the place of a notification popup or list that is already open — the new notification waits in the queue and opens when the current one is dismissed. For these, the popup's right button is **Dismiss**, which removes the notification from the queue. Persistent notifications also re-open their popup about every 60 seconds until dismissed, so they stay accessible even if the user navigates away. While the idle/screensaver page is shown, only a `critical` persistent notification forces its popup over it; other severities wait until the user returns to a real panel; their alert sound repeats every `persistent_sound_interval` seconds (default 5). The queue holds up to 50 notifications; when it is full, the oldest one is dropped. The icon is coloured by the notification `type` (`info`, `warning`, `critical`). When a queued notification has no icon, the popup uses the severity default (`info` → `mdi:information-outline`, `warning` → `mdi:alert-outline`, `critical` → `mdi:alert-octagon-outline`).

The text size follows the message length: messages under 50 characters use a large font, messages under 150 characters a medium font, and longer messages a small font. Messages longer than one page render as static pages that auto-advance about every 4 seconds; the title shows a `(page/total)` counter and the final page stays visible, so long messages are readable page by page instead of being truncated. The `text_size` field on `nspanel_haui.send_notification` and the `send_notification` ESPHome action overrides the automatic choice per notification with a fixed font size (1-3).

## How to configure

This popup is opened by the integration and cannot be configured in the panel editor. Parameters when opening it programmatically:

- `notification`, `title` — Message text and title.
- `icon` (optional) — Always shown. When provided, the text is shown in a narrower column beside the icon. When omitted, the severity default icon is used (`info` → `mdi:information-outline`, etc.).
- `btn_left`, `btn_right` (optional) — Button labels; a button is shown only when set. Colors via `btn_left_color`, `btn_left_back_color` and the `btn_right_*` equivalents.
- `notif_type` — `info` (default), `warning` or `critical`; sets the icon color (override with `icon_color`).
- `text_size` — `auto` (default, by message length) or a font size 1-3. The per-notification `text_size` field on the service/actions overrides this panel value.
- `close_timeout` — Automatically close after this many seconds. 0 = no auto-close.
- `close_on_button` — Close when a button is pressed. Default: true.
- `button_callback_fnc`, `close_callback_fnc` — Callbacks.

## Using the service

Notifications are triggered from automations or scripts using the `nspanel_haui.send_notification` service. See [Services](../services.md) for full details.

## For developers

If you are writing a custom integration or extension that needs to open a notification programmatically with callbacks, see [Hub](../hub.md) for the internal API.
