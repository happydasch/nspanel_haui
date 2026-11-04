---
title: Popup Unlock
description: Unlock popup — PIN-protected panel unlocking
---

# Popup Unlock

## About

The unlock popup is used internally to provide a PIN unlocking mechanism for panels. To use this feature, set a **Panel pin** on any panel in the editor.

The panel pin (`unlock_code`) is a numeric PIN entered as a string field in the panel editor's standard fields.

The popup shows the locked panel's title (or **Unlock Panel** when it has none), a keypad and an **Unlock** button that becomes active once the PIN matches. It opens on top of the locked panel, and its header follows that panel: guarding a navigation panel, it shows the previous, home and next buttons, so you can move on without unlocking (see [Stacked Panels and Popups](../configuration/panels.md#stacked-panels-and-popups)).

## How to configure

In the **panel editor**, set the **Panel pin** field on any panel. When set, the panel requires this code before it can be accessed. The input is masked as a password field in the editor.
