---
title: Panel Timer
description: Timer panel configuration and options
---

# Panel Timer
## About

The timer panel allows to run a (for now local) timer. If a time bigger than 0 is set, the timer will run backwards, if a time of 0 is set, the timer will run forward.

`type: timer`

## Popup

`type: popup_timer`

`key: popup_timer`

## Config

Panel options are configured through the NSPanel HAUI editor in Home Assistant.



## Notification on timer end

When the timer finishes, a sound will be played. Additionally, a notification can be shown by setting `show_notification` to true.
