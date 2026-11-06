---
title: Popup Unlock
description: Unlock popup — PIN-protected panel unlocking
---

# Popup Unlock

## About

The unlock popup is used internally to provide a PIN unlocking mechanism for panels. To use this feature, set a **Panel pin** on any panel in the editor.

The panel pin (`unlock_code`) is a numeric PIN entered as a string field in the panel editor's standard fields.

The popup shows the locked panel's title (or **Unlock** when it has none), a keypad and an **Unlock** button that becomes active once the PIN matches. It opens on top of the locked panel and has that panel's header, so you can move on without unlocking: guarding a navigation panel it shows previous, home and next; guarding a stacked panel it shows up, home and close, back to the panel the locked one was opened from. The lock sits in the right-hand secondary slot (see [Stacked Panels and Popups](../configuration/panels.md#stacked-panels-and-popups)). Closing the popup of a locked navigation panel with the `close_panel` service goes to the home panel.

## How to configure

In the **panel editor**, set the **Panel pin** field on any panel. When set, the panel requires this code before it can be accessed. The input is masked as a password field in the editor.
