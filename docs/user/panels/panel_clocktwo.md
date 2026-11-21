---
title: Panel ClockTwo
description: ClockTwo panel — minimalist clock with written text display
---

# Panel ClockTwo

<img src="../../assets/screens/landscape/clocktwo.png" alt="clocktwo panel, landscape" width="300" height="213"> <img src="../../assets/screens/portrait/clocktwo.png" alt="clocktwo panel, portrait" width="142" height="213">

## About

The ClockTwo panel is a word clock. It shows a grid of letters and lights up the words that spell the time, for example "IT IS HALF PAST TWELVE". The time is rounded to 5 minutes; four dots show the extra minutes.

## How to configure

| Option | Default | Description |
|--------|---------|-------------|
| **Background** | Dark Color | The picture the panel is drawn on, see [Background](#background). |
| **Clock language** | English | English, German or Polish. |
| **Show AM/PM** | Off | Show AM or PM. English only. |
| **Show intro text** | On | Always show the intro words ("IT IS"). |
| **Show intro text on full hour** | Off | Show the intro words on full hours. |
| **Off-letter color**, **Active letter color**, **Special letter color** | empty | Your own colors for the letters. Empty: the colors of the background or the selected theme. |
| **Show notifications** | On | Show the notification bell. |

### Background

Choose **Dark Color** (the default), **Light Color** or a decorative picture. The letters and dots always use the colors that are readable on the picture the panel is drawn on, unless you set your own letter colors: the lit words take its text color, and the unlit letters sit a fixed small step off the page as a soft watermark — nowhere near the time. The step is a contrast ratio (1.4:1 on a light picture, the card tone on a dark one), so every theme gets the same quiet backdrop.

For a background that changes, for example at night, choose **Template…**. See [Background pages](../editor/themes.md#background-pages) for all backgrounds and an example.

### Leaving the Panel

This panel has no header buttons. To leave it:

- Swipe left or right from a screen edge to change the panel.
- Or turn on **Long press to go back** in the *Advanced* section. Then holding a finger anywhere for about a second goes back to the previous panel, or to the home panel. See [Standard Fields](../editor/panels.md#standard-fields).
