---
title: Popup Notify
description: Notify popup — ad-hoc notifications with action buttons
---

# Popup Notify

## About

The notification popup is used for one-shot, ad-hoc popups — for example to notify the user about errors or to prompt a yes/no decision. It is opened programmatically via the `nspanel_haui.send_notification` service and supports optional buttons and an optional icon.

## How to configure

In the **panel editor**, set:

- **Icon** (optional) — When provided, the text is shown in a narrower column beside the icon. When omitted, the text fills the full width.
- **Close Timeout** (number) — Automatically close the notification after this many seconds. 0 = no auto-close.
- **Close on Button** (toggle) — When a button is visible and pressed, the panel closes. Set to off to keep it open after a button press. Default: On.

## Using the service

Notifications are triggered from automations or scripts using the `nspanel_haui.send_notification` service. See [Services](../services.md) for full details.

## For developers

If you are writing a custom integration or extension that needs to open a notification programmatically with callbacks, see [Hub](../hub.md) for the internal API.
