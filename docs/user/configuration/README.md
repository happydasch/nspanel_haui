---
title: Configuration Overview
description: How to configure NSPanel HAUI through the Home Assistant UI editor
---

# Configuration Overview

NSPanel HAUI is configured in an editor inside Home Assistant. You do not edit YAML. There are three things to configure:

1. **[Device](device.md)** — settings of the panel itself: language, brightness and timeouts, buttons and sounds.
2. **[Panels](panels.md)** — the screens the panel shows: type, title, key, navigation, PIN.
3. **[Items](items.md)** — what a panel shows: the entities and how they look.

## Finding the Editor

1. Open **NSPanel HAUI** in the Home Assistant sidebar. Only administrators see this entry.
2. The dashboard lists your devices. Select a device to open it. The round back button returns to the dashboard.
3. A device opens on its **Preview**. Switch to **Panels** to see and edit its panels.

Each view starts with a highlighted card of the next actions. On **Preview**, **Add panel** opens its sidebar; the cog beside the card's title opens **Settings**. **Theme**, **Schedule** and **Gestures** sit in one row of buttons in **Manage this device**, each opening its editor in a sidebar. While an update is offered, the Preview's card also offers **Install update**. The **Panels** view uses the full width for the panel list; configure the home and idle pages in **Device Settings → Home & idle**.

If the editor does not get past its loading screen, see [Troubleshooting](../troubleshooting.md#editor-loading-problems).

## The Device Screen

Beside the preview, the Device screen has two cards about the panel's state.

### Connection & device

Four tiles: how long the panel has been online (or that it is offline), the Wi-Fi signal, the current page and the IP address. Hover over a tile or tap it for more, such as the Wi-Fi network, the last disconnect or the last panel update. Below the tiles, **Updates** opens the updates; the firmware and display versions are in **Diagnostics** and in the **Updates** sidebar.

### Diagnostics

The icon in the header is a green check while all is good, or an alert with the number of issues; hover over it to list them. An issue is one of:

- the panel is offline
- the firmware does not match the integration
- a display update is pending or failed
- the Wi-Fi signal is weak
- the connection dropped three or more times in 24 hours
- the hub log has warnings or errors

Expand the card for more:

- **Firmware** and **Hub log** tiles. A tap on **Hub log** opens the logs.
- **Hub details** — the display state (on, dimmed, off), when the idle page opens, the disconnects of the last 24 hours and the entities the current page uses. Select an entity to open it in Home Assistant.
- **Copy report** — copies a text report for a bug report. It contains versions, connection history and the recent log, but no network name, IP address or entity ids.
- The preview's tools, see [The Live Preview](#the-live-preview).

### Logs

The **Logs** sidebar shows the 50 most recent messages of the hub for a device, newest first and grouped by day. Open it with the **Hub log** tile of the Diagnostics card or with **Logs** in the device's **More** menu. Filter them with **All**, **Warnings** and **Errors** or with the search box. The copy button copies the lines shown, for a bug report.

On the dashboard, **Logs** beside **Latest events** shows the messages of all devices.

The logs only contain messages of NSPanel HAUI. They are not a full Home Assistant or ESPHome log, and they are not saved to disk.

## The Panel List

The **Panels** view lists the device's panels in three groups:

| Group | Contains |
|-------|----------|
| **Navigation** | Panels you reach by swiping or with the header buttons |
| **Hidden** | Panels that are only opened from another panel |
| **Popups** | Built-in popups you have changed on this device |

Each row has a picture of the panel as the display shows it, with your entities and their current states. Markers show the home panel and the idle panel. The search field narrows the list by title, key or type. Selecting a row opens its details alongside the list: the panel's type, key, group and item count, Home/Idle role, and **Edit**, **Duplicate** and **Delete** actions. Close the details card or select the row again to clear it and return to the overview.

In this list you can:

- **Add** — **Add panel** opens the catalog: a stack of collapsible groups. The panel types sit under **Backgrounds**, **Entities**, **Grouping** and **Tools**, each with a full-width picture of the panel; below them, **Start from a template** offers ready-made panels (a lights grid, a room overview, a thermostat, a bedside clock, a weather station, guest Wi-Fi and more), **Extend a popup** changes a built-in popup and **Copy an existing panel** starts from a panel of any of your devices. A template opens in the editor with its entities marked: choose one for each, then save. A group opens when you select it, and a search opens the groups it looks into.
- **Edit** — select a panel's name or the pencil.
- **Preview** — hover over the picture or tap it to enlarge it.
- **Duplicate** — in the row's **More** menu.
- **Reorder** — drag a row by its grip, also between Navigation and Hidden.
- **Delete** — remove a panel.

A panel saved before this version whose settings no longer fit its type (for example a light panel bound to a sensor) shows **Check settings** in the list. It keeps working as before; fix it the next time you edit it.

The built-in panels System, Blank, Settings and About cannot be changed and are not listed.

## The Panel Editor

Selecting a panel opens the panel editor in a sidebar. Every panel has these fields:

| Field | Description |
|-------|-------------|
| **Type** | The panel type, for example Clock, Grid or Light. It is set when you add the panel and cannot be changed. |
| **Title** | The name in the panel's header. A panel that controls a single entity shows the entity's name instead. |
| **Key** | A unique name for the panel. You use it to open the panel from other panels and from automations. |
| **Show in navigation** | Whether you reach the panel by swiping. |
| **Panel pin** | A numeric PIN. When set, the panel asks for it before it opens. |

Below these fields, the **Configuration** section has the options of the panel type. All fields are explained in [Panel Configuration](panels.md); the options of each type are on its page in the [Panels overview](../panels/README.md).

How the editor helps:

- **Preview** — the picture at the top shows the panel with your current, unsaved values. It follows every change.
- **Items** — the section with the panel's items is open and shows how many there are. Select an item to edit it and drag it to move it.
- **Errors** — a field that cannot be saved is marked with the reason, and **Save** stays disabled until it is fixed: a key that another panel uses, an entity of the wrong kind (a light panel needs a light), a missing entity the panel needs, a number outside its range, more items than the page shows, a value that is not one of the choices, or a colour the display cannot read. A popup you extend may leave its entity empty: it shows the entity it is opened for.
- **Warnings** — an entity Home Assistant does not know right now is marked too, but you can still save: it may be offline or not created yet.
- **Width** — drag the left edge of a sidebar to make it wider or narrower. A double click on the edge restores the default width.

## The Item Editor

Every item of a panel has its own editor:

- **Entity picker** — search and select a Home Assistant entity.
- **Advanced** — change the name, value, icon, color, state and popup of the item.

See [Item Configuration](items.md) for all options.

## The Device Settings Dialog

**Settings** opens the device settings in a sidebar. You find it as the cog in the action card of the **Preview** and of **Panels** and in the device's row on the dashboard. The settings are grouped into sections:

| Section | Settings |
|---------|----------|
| **General** | Display model, display language, time and date formats; opens the **Theme** |
| **Screen** | Brightness, dimming and display off with their timeouts; opens the **Schedule** |
| **Sounds** | Startup and notification sounds |
| **Home & idle** | Home panel, automatic page switching, idle panels and what the panel shows after waking up |
| **Screen buttons & gestures** | Home, idle and notifications buttons in the header; opens the **Gestures** |
| **Hardware buttons** | Relays or entities for the two buttons |
| **Advanced** | Logging, stale data marking and page settle delay; opens the **Updates** |

See [Device Configuration](device.md) for every setting. The **Schedule**, **Gestures**, and **Theme** buttons are in **Manage this device** in the device's **Preview** view; the rows in the settings open the same sidebars. Set the home and idle panel assignments in **Device Settings → Home & idle**.

## The Theme Sidebar

In **Preview**, open **Manage this device** and choose **Theme** to open the Theme sidebar, where you select the device's theme and edit shared colors or icon palettes. The selection is saved immediately; press **Apply** to save color changes or **Cancel** to discard them. See [Themes](themes.md).

## The Live Preview

The **Preview** view shows your panel in the browser. You can use it like the real panel: tap, drag sliders and swipe from the screen edges. It has two modes.

### Simulated mode

The preview starts in **Simulated** mode. It shows a copy of your panel with your saved panels and settings.

- **Nothing real changes.** Whatever you tap only changes a simulated state. Your lights and switches are not touched, and automations do not see it.
- It starts on the home panel with the real entity states, every time you open it.
- It follows every save right away.
- Notifications waiting on the real panel are shown, but dismissing one here does not dismiss it on the panel.
- It never checks for or installs updates.
- A device has one simulated copy. If you open it in several browser tabs, they show the same screen.

### Live mode

The **Live** button above the screen switches to the real panel and back. While Live is on, the button is highlighted and the workspace has a teal tint.

- The preview shows what the real panel shows.
- **Everything you do is real.** A tap acts on the real panel and switches your real entities. A press on a hardware button switches the real relay.
- Input is only accepted while the panel is connected.

### Controls

| Control | Where | What it does |
|---------|-------|--------------|
| **Live** | Bar above the screen | Switches between Simulated and Live |
| **Idle** (moon icon) | Bar above the screen | Opens the idle page; press it again to leave the idle page |
| **Left button**, **Right button** | Below the screen | The two hardware buttons. The light is blue for a relay and yellow for an entity. |
| **Show entities in the preview** | Diagnostics card | Hover over a tile or button to see the entity behind it |
| **Current page** | Connection & device card, Simulated mode | Click the tile to show the page the real panel is on, as its idle page when the panel is idle. A popup opens with an example |
| **Reset sandbox** | Diagnostics card, Simulated mode | Drops all simulated states and shows the real states again. Shown only once an action in the preview changed a simulated state |
| **Reset interaction** | Diagnostics card, Live mode | Restarts the panel's inactivity timer, as if you had touched it. It does not restart the panel. |
| **Redraw display** | Diagnostics card, Live mode | Draws the current page again, for a display that shows old or broken content |

### Panel pictures

The pictures in the panel list and in the panel editor are drawn the same way as the display: with your entities, translations and templates, including changes you have not saved yet. A popup is shown with an example, such as a sample notification or an entity of its type.

Your browser keeps the last picture of every panel, so the editor shows them at once when you open it and replaces them as soon as Home Assistant has drawn new ones. After an update of the integration the pictures start empty once.

The live preview and the Nextion simulator were created by [@jameshiscott](https://github.com/jameshiscott).

## See Also

- [Panels Overview](../panels/README.md) — all panel types
- [Examples](../examples.md) — panel layouts for common rooms
- [FAQ](../faq.md) — common questions
