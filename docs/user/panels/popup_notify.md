---
title: Popup Notify
description: Notify popup — ad-hoc notifications with action buttons
---

# Popup Notify

## About

The notify popup shows a notification: a title, a message, an optional icon and a **Dismiss** button.

It opens:

- right away for a notification sent with `force_show` or `persistent`, or
- when you tap the notification indicator.

See [Notifications](../device.md#notifications) for how notifications behave on the panel, and [Services](../services.md#nspanel_hauisend_notification) for how to send one.

## What it shows

| Part | Description |
|------|-------------|
| **Title** | The notification's title. A title that is too long is cut and ends in `..`. |
| **Icon** | Shown only when the notification has one, beside the text (above it in portrait). Its color is the notification's `icon_color`, or the theme's text color. |
| **Message** | Without an icon the message uses the whole area, so more text fits. `\n` in the message starts a new line. |
| **Dismiss** | Removes the notification. Closing the popup in another way keeps it waiting. |

## Long messages

- **Text size.** The popup picks the largest of three font sizes at which the whole message fits on one page. Set `text_size` (1–3) on the notification to choose the size yourself.
- **Pages.** A message that does not fit even in the small font is split into pages. The title then shows a counter such as `(1/3)`, and a button in the header opens the next page. Pages never change on their own, and the last page stays on screen.

## How to configure

You do not add this popup; the integration opens it. To change its title or default icon color for a device, use **Add panel → Extend a popup**, see [System Panel Overrides](../configuration/panels.md#system-panel-overrides).

## For developers

The popup can also be opened from code with buttons and callbacks. See [Hub → Popup parameters](../../develop/hub.md#popup-parameters) and [Notification Process](../../develop/notifications.md#sending-from-your-own-code).
