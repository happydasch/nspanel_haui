---
title: Dashboard Card
description: Show an NSPanel's screen on a Home Assistant dashboard, as its home panel or live
---

# Dashboard Card

The **NSPanel HAUI** card puts one panel on a Home Assistant dashboard: its screen in the panel's
frame, with the two hardware buttons' lights and one row about the panel itself — whether it is
reachable, awake or dark, how many notifications are waiting, and which firmware and display
version it runs. It draws what the hub sends to the display, so the card looks like the panel.

There is one card and one shape: the screen, its frame, the buttons and the row. Nothing in the
settings turns part of it off. **Show** picks *what* the card shows — the home panel, the screen
as it is right now, or only the row (a status tile).

The card is for watching: it shows the screen and the button lights, and taps on it do nothing. To
change panels or try them out, use the [editor](configuration/README.md) and its live preview.

## Add the card

1. Open a dashboard, select **Edit dashboard**, then **Add card**.
2. Search for **NSPanel HAUI** and pick it.
3. Choose the **Device** and what it should **Show**, then save.

The card is installed with the integration; there is no extra resource to add. It is available to
every signed-in user, and a device switched off with **Device Enabled** in the editor is still
offered here, marked *(disabled)*, so a dashboard does not have to be edited when a panel returns.

## What it shows

| Show | The card shows |
|------|----------------|
| **Home panel** | The device's home panel: the **Home panel** setting, or the first panel when none is set. It follows entity changes and the clock as they happen, even while the real panel is idle, on a popup or off. The card dims and marks **Disconnected** while the panel is offline, but keeps showing the panel. |
| **Live screen** | What the real panel shows right now, page changes and popups included. A dark panel shows a dark screen; while the panel is offline, the card keeps its last screen, dimmed, under **Disconnected**. |
| **Status tile** | Only the row: the panel, without its screen. For a dashboard that shows the screen elsewhere or wants a compact tile per panel. |

The screens show real entity states only, never the simulated states of the editor's preview.
The frame's button lights show the panel's real relays and button entities.

The row under the screen says what the hub reports and nothing else: **Connected** or **Offline**,
**On**, **Dimmed** or **Off**, how many notifications are waiting, and the firmware and TFT versions.
A value the panel has not reported yet reads **Unknown**.

## Options

| Option | Default | Meaning |
|--------|---------|---------|
| `device` | | The device's name in NSPanel HAUI. The card editor stores it together with `device_id`. |
| `device_id` | | The panel's Home Assistant device. Preferred over `device`: renaming the device in the editor keeps the card working. |
| `mode` | `home` | `home` (the home panel), `live` (what the screen shows now) or `tile` (the row only). |
| `title` | | A heading above the card. |
| `scale` | `100` | The screen's size, in percent of the space the card gives it (20–100). Use it for a smaller preview on a wide dashboard; the frame and the row under it keep its width. |

## YAML

```yaml
type: custom:nspanel-haui-card
device: Kitchen      # the device's name in NSPanel HAUI
device_id: 4f2a…     # its Home Assistant device; the card editor writes this
mode: home           # home (default), live, or tile
title: Kitchen       # optional heading
scale: 100           # the screen's size in percent (20-100)
```

## A smaller preview

The screen normally fills the card. On a wide dashboard, `scale` draws it smaller and centers it,
with the frame and the row under it:

```yaml
type: custom:nspanel-haui-card
device_id: 4f2a…
scale: 50            # half the size the card would use
```

## A status tile

`mode: tile` keeps the row and leaves out the screen, for a dashboard that shows the screen
elsewhere or wants a compact tile per panel:

```yaml
type: custom:nspanel-haui-card
device_id: 4f2a…
mode: tile
```

## Who can see it

Every signed-in Home Assistant user, admin or not, can see the card. It only reads: nobody can
change the panel, its settings or its entities through it. The NSPanel HAUI editor stays admin-only.

## When it shows a message

| Message | Why |
|---------|-----|
| Choose a device in the card settings | The card has no device yet. A newly added card starts here. |
| The device is disabled in NSPanel HAUI | Its **Device Enabled** setting is off. The card tries again every 30 seconds, so it comes back when the device is enabled. |
| Device not found: *name* | No NSPanel HAUI device has that name or id: it was removed, or Home Assistant is still starting. The card tries again every 30 seconds. |
| This device has no home panel | The hub has no panel to run for **Home panel** mode. |
| The preview could not be started / shown | The hub could not run the panel this time; it tries again every 30 seconds. |

After a Home Assistant restart, an integration reload or a saved change in the editor, the card
connects again on its own and keeps its last screen meanwhile.

