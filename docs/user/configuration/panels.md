---
title: Panel Configuration
description: Panel configuration — type, key, title, show_in_navigation, unlock_code, and device-level panel assignments
---

# Panel Configuration

A panel is one screen on the display. You add and edit panels in the **Panels** view of a device: select **Add panel** for a new one, or select a panel in the list to edit it.

Selecting a panel in the list shows it in the side column, under the **Panels** card: how the display draws it, its type, key, group and item count, whether it is the home or idle panel, and its **Edit**, **Duplicate** and **Delete** actions. Select the preview to fold it to a thumbnail; the editor remembers that choice. Close the card or select the row again to clear the selection; the card then explains the groups and names the configured **Home panel** and **Idle panel** instead.

Every panel has the standard fields below. Each panel type adds its own options, shown in the **Configuration** section of the editor and described on the type's page in the [Panels Overview](../panels/README.md).

## Standard Fields

| Field | Key | Description |
|-------|-----|-------------|
| **Type** | `type` | The panel type, for example `clock`, `grid` or `light`. You choose it when you add the panel. It cannot be changed later: delete the panel and add a new one instead. |
| **Title** | `title` | The name in the panel's header. A title that is too long for the header is cut and ends in `..`. |
| **Color theme** | `theme_id` | Colours for this panel only; the default follows the device theme. |
| **Key** | `key` | A unique name for the panel on this device. You use it to open the panel from items, gestures and automations. |
| **Show in navigation** | `show_in_navigation` | On (default): you reach the panel by swiping and with the header buttons. Off: the panel is hidden and only opens when something opens it, see [Stacked Panels and Popups](#stacked-panels-and-popups). |
| **Panel pin** | `unlock_code` | A numeric PIN. When set, the panel asks for it before it opens. |
| **Close automatically after (seconds)** | `close_timeout` | Closes the panel after this many seconds and goes back. `0` (default) keeps it open. |
| **Long press to go back** | `long_press_back` | Only for Clock, ClockTwo and Weather, which have no header buttons. When on, holding a finger anywhere for about a second goes back to the previous panel, or to the home panel. Default: off. |

**Which title is shown?** A panel that controls a single entity, such as a light or cover panel, shows the entity's name. Other panels show the title. When the title is empty, the name of the panel type is shown, for example *Grid*.

## Opening a Panel

A panel in the navigation is reached by swiping. Any panel, hidden or not, can be opened by its key:

- from an item of type `navigate` with the panel's key, see [Internal items](items.md#internal-items)
- from an item's `popup_key`, see [Override a default popup](items.md#override-a-default-popup)
- with a gesture, see [Gestures](device.md#gestures)
- from an automation with the [`nspanel_haui.open_panel`](../services.md#nspanel_hauiopen_panel) service

## Stacked Panels and Popups

A panel with **Show in navigation** off opens *on top of* the current panel. Closing it goes back to where you came from. This is called a **stacked panel**. Any panel type can be used this way; it is the right choice for detail views and sub-pages.

**Popups** are the built-in panels that open the same way:

- the entity popups: `popup_light`, `popup_media_player`, `popup_vacuum`, `popup_climate`, `popup_cover`, `popup_timer`, `popup_alarm`
- `popup_notify`, `popup_select` and `popup_unlock`
- Settings and About

### Header buttons

The header buttons are set automatically:

| Panel | Left | Second left | Right |
|-------|------|-------------|-------|
| Navigation panel | Previous panel | Home | Next panel |
| Stacked panel or popup | Up | Home | Close |

- **Up** and **Close** both go back to the panel you came from.
- **Home** is only shown when the home button is turned on (`show_home_button`), and never on the home panel itself. With `show_idle_button` on, the home panel shows the idle button in its place. Settings and About never show it.
- **The second button on the right** shows the next-page button on a grid or row with several pages, the unlock button on a locked panel, and otherwise the notifications button.

### Locked panels

A panel with a **Panel pin** opens the unlock popup first. The popup has the header of the panel it protects, so you can move on without unlocking:

- In front of a navigation panel it shows previous, home and next.
- In front of a stacked panel it shows up, home and close.

Closing the unlock popup never opens the locked panel. In front of a locked navigation panel, closing goes to the home panel.

## System Panel Overrides

You can change the built-in **popups**, but not the other built-in panels.

**To change a popup:** select **Add panel → Extend a popup** and choose the popup. Saving stores your version for this device. It is then listed in the **Popups** group of the panel list.

**To undo it:** select **Reset to default** in the row's menu. Your version is deleted and the built-in popup is used again.

What you can change:

| Popup | What you can edit |
|-------|-------------------|
| Entity popups (`popup_light`, `popup_climate`, `popup_media_player`, `popup_cover`, `popup_vacuum`, `popup_timer`, `popup_alarm`) | Everything the panel type offers, for example the Cover options for `popup_cover`. The entity still comes from the item that opens the popup. |
| **Notify**, **Select**, **Unlock** | The title and **Color theme**. A panel pin or an auto-close time would get in the way of these popups, so they are not offered. |

Good to know:

- A changed popup keeps the built-in value for everything you do not set.
- Its key and **Show in navigation** cannot be changed. It stays a popup.
- **System**, **Blank**, **Settings** and **About** cannot be changed and are not listed in the editor.

## Home and Idle Panels

Which panel is the home panel and which panels appear while idle are device settings, not settings of individual panels. Configure them in the **Home & idle** section of **Device Settings** (open the device's Preview and select its Settings cog). The **Panels** view no longer has a side area; it uses the full width for panel management.

| Setting | Key | Description |
|---------|-----|-------------|
| Home panel | `home_panel` | The panel shown when you navigate home. If unset, the first navigation panel is used. |
| Idle panels | `idle_panel`, `idle_panel_extra` | One ordered list of panels shown after the automatic page-switch timeout. Each switch shows the next panel, cycling through the list. The first entry is stored in `idle_panel`; the remaining entries are stored in `idle_panel_extra`. An empty list means nothing opens automatically. Add panels from the dropdown; remove them with **×**. |

See [Home and Idle Panels](#home-and-idle-panels) for the settings and their behavior.
