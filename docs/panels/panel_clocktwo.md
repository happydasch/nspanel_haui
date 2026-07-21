---
title: Panel ClockTwo
description: ClockTwo panel — minimalist clock with written text display
---

# Panel ClockTwo

![](../assets/previews/panel-clocktwo.svg)

## About

The clocktwo panel shows the current time by using written text on the display (e.g. "twelve thirty-four"). It supports multiple languages and customizable colors.

## How to configure

In the **panel editor**, set:

### Background

The clocktwo panel can have different background images. Select from the dropdown in the editor:

- Dark, Modern, Spring, Summer, Autumn, Winter, Dog 1, Dog 2, Cat

For dynamic backgrounds, use a Home Assistant template in the background field: `template:{{ ... }}`. The return value should match a background name.

### Language

Set the display language from the dropdown. Supported languages:

- English, German, Polish

### Custom Colors

Customize the text colors in the panel editor:

- **Off Color** — Color for inactive/dim text segments
- **Letter Color** — Color for active letter text
- **Special Color** — Color for special text elements

### Show AM/PM

Toggle to enable AM/PM display.

### Show Intro Text

- **Show Intro Text** — Show intro text always (Default: On)
- **Show Intro Text Full Hour** — Show intro text on full hours (Default: On)

### Show Notifications

Toggle the notifications icon on/off.
