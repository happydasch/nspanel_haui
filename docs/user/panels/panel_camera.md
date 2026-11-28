---
title: Panel Camera
description: Camera panel — one camera's picture, refreshed on the display
---

# Panel Camera

<img src="../../assets/screens/landscape/camera.png" alt="camera panel, landscape" width="300" height="213"> <img src="../../assets/screens/portrait/camera.png" alt="camera panel, portrait" width="142" height="213">

## About

The camera panel shows one camera's picture and keeps it current: the hub fetches a snapshot a few times a second and paints only what changed on the display, so a still scene costs nothing and a person walking through the frame costs a handful of small rectangles per update.

It is a picture, not a video. The display has no image buffer and no video path, so the panel can afford a couple of snapshots a second on a camera that is mostly still. A camera that pans or a scene that moves everywhere will look like a slow slideshow — for those, a page background picture or [`nspanel_haui.show_image`](../actions.md#images-on-the-panel) is the better fit.

The panel uses the display's **info page** and paints its big text area: the picture goes exactly where that page's text widget sits (12 px in from the left, below the header, above the row of mode buttons), cropped to fill it. A camera's 16:9 frame is zoomed to the centre rather than shown with bands above and below, so the area the panel reserves for text all goes to the picture.

## How to configure

| Option | Default | Description |
|--------|---------|-------------|
| **Camera** | | The camera entity whose picture the panel shows. Required. |
| **Picture quality** | Medium | How fine the picture is drawn and how often a frame arrives — see below. |

The quality is the whole of the panel's tuning, because on this display the detail
of the picture and the number of frames it can show are the same budget:

| Quality | Picture is drawn in | Full-detail limit | Target frames a second |
|---------|---------------------|-------------------|------------------------|
| **High** | 2-pixel cells | up to 12 000 rectangles | 1 |
| **Medium** | 3-pixel cells | up to 6 000 rectangles | 2 |
| **Low** | 6-pixel cells | up to 3 000 rectangles | 4 |

*High* is the finest the panel gets: a face is a face, and a large plate or a
sign is readable. It costs the most to paint, so it aims at one frame a second.
*Low* is a coarse mosaic that keeps moving scenes honest at four frames a second.
Whatever you pick, an update only ever pays for the cells that actually changed.

## How it behaves

- **The picture starts after the page is up.** Until the first snapshot arrives the panel shows *Waiting for the camera*; a panel without a camera entity shows *No camera selected* and never fetches one.
- **The first snapshot sharpens in stages.** One fill sets the background, large blocks show the scene quickly, then smaller blocks paint over it until the selected quality is reached. How long that takes depends on the camera, the scene and the display.
- **Only what changed is painted.** The hub compares each snapshot with what the display is showing; a scene that has not changed sends no display commands at all.
- **Each update takes as long as it takes.** A frame that arrives while the display is still painting the previous one is dropped rather than queued, so the panel always shows the newest picture it could paint instead of falling behind.
- **A busy scene is painted coarser rather than slower.** When an update would cost more rectangles than its share of the frame budget — a scene in motion, a very detailed picture — the hub uses larger cells for it, so the frames keep coming. The picture returns to the quality you picked as soon as the scene calms down.
- **A sleeping display pauses the picture, it does not end it.** The stream stops asking for snapshots while the panel is dark and paints the whole area again as soon as it wakes, so the picture is never a stale one from hours ago and nothing keeps running into a dark display.
- **A camera that stops answering keeps its last picture.** The stream retries, slows down to an attempt every thirty seconds once it has missed a handful in a row, and carries on by itself when the camera comes back — you do not have to leave the page and return.
- **Leaving the page ends the stream.** So does a TFT install — before the display refuses the next frame. Nothing keeps running in the background.
- **The page returns to the idle page** like any other panel, which ends the stream.
- **A card or thumbnail of this page shows the picture the panel last painted.** It replays the fills the panel received; once the stream has run long enough for its oldest fills to be dropped, it asks the stream for a fresh whole picture, so the card catches up within a render or two instead of sitting on *Waiting for the camera*.
- **A render repaints widgets, not the page.** A plain refresh (from the editor, a
  notification, a reconnect) leaves the picture alone, and the stream keeps running
  across it. The stream is asked for when the panel starts, not when it renders, so a
  refresh starts nothing either. Its detail is decided once, too: no periodic full
  repaint, because a cell that moves further than the dead band from what the panel
  shows is repainted on its own.
- **A page that is drawn again gets its picture back.** When the page itself is
  redrawn — a reload, a theme change, a second panel on the same page, a saved
  panel — the stream keeps running and paints the picture whole again, and so does a
  frame the panel did not take whole or a `show_image` over the picture area. Only
  what changed is painted between two of those, never on top of a picture the
  display no longer has.
- **A preview and a card show the picture.** The frame is part of the page's own
  commands for the render that finds no picture on the display, so the editor's
  preview, a panel card and the docs screenshots replay it instead of an empty area.
  A panel card reads the picture from the device it follows, so it shows one only
  while that device has this camera panel on its screen.
- **A Live preview follows the picture.** Live mirrors the panel's own display
  output, so a camera page keeps moving there too: a viewer that attaches while the
  stream runs is given the picture the panel is holding and then every change. After
  a long stream the panel may no longer be able to describe that picture from what
  it recorded, and the stream then paints it whole for the viewer instead.

The picture is drawn over the page, so the stream ends the moment any other panel opens on top of it — a notification popup included — and it starts again when the camera page is shown again. Closing a popup therefore brings the picture back with a full frame.
