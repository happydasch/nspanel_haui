---
title: Dashboard Card
description: Show an NSPanel's screen on a Home Assistant dashboard, as its home panel or live
---

# Dashboard Card

The **NSPanel HAUI** card shows one panel's screen on a Home Assistant dashboard. It draws what the hub sends to the display, so the card looks exactly like the panel.

The card is for watching: it shows the screen, and taps on it do nothing. To change panels or try them out, use the [editor](configuration/README.md) and its live preview.

## Add the card

1. Open a dashboard, select **Edit dashboard**, then **Add card**.
2. Search for **NSPanel HAUI** and pick it.
3. Choose the **Device** and what to **Show**, then save.

The card is installed with the integration; there is no extra resource to add.

## What it shows

| Show | The card shows |
|------|----------------|
| **Home panel** | The device's home panel: the **Home panel** setting, or the first panel when none is set. It follows entity changes and the clock as they happen, even while the real panel is idle, on a popup or off. |
| **Live screen** | What the real panel shows right now, page changes and popups included. A dark panel shows a dark screen; while the panel is offline, the card keeps its last screen, dimmed, under **Disconnected**. |

The home panel shows real entity states only, never the simulated states of the editor's preview.

## YAML

```yaml
type: custom:nspanel-haui-card
device: Kitchen   # the device's name in NSPanel HAUI
mode: home        # home (default) or live
```

## Who can see it

Every signed-in Home Assistant user, admin or not, can see the card. It only reads: nobody can change the panel, its settings or its entities through it. The NSPanel HAUI editor stays admin-only.

## When it shows a message

| Message | Why |
|---------|-----|
| Choose a device in the card settings | The card has no `device` yet. |
| Device not found: *name* | No running NSPanel HAUI device has that name: it is disabled, removed or renamed, or Home Assistant is still starting. The card tries again every 30 seconds. |

After a Home Assistant restart, an integration reload or a saved change in the editor, the card connects again on its own and keeps its last screen meanwhile.
