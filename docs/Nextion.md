# Nextion Overview

![Overview](assets/style_overview.png)

- [Nextion Overview](#nextion-overview)
  - [Style](#style)
  - [Fonts for text](#fonts-for-text)
  - [Fonts for time / weather](#fonts-for-time--weather)
  - [Colors](#colors)
  - [How to edit the HMI file](#how-to-edit-the-hmi-file)

## Style


The display is splitted into two areas, a top area and a main area.

The top area is used for navigation and a header.

The main area is used for content.

![Font & Color](assets/style_text.png)

![Components](assets/style_color.png)

![Components](assets/style_components.png)

The font [Roboto](https://github.com/googlefonts/roboto) and [MaterialDesign-Webfont](https://github.com/Templarian/MaterialDesign-Webfont) is being used.

- [Cheatsheet](https://htmlpreview.github.io/?https://raw.githubusercontent.com/happydasch/nspanel_haui/master/docs/cheatsheet.html) for a icon overview

- [Pictogrammers](https://pictogrammers.com/library/mdi/) if you need the char of the source font

## Fonts for text

- **Size 24** - All icons / Text
- **Size 32** - All icons / Text
- **Size 48** - All icons / Text

## Fonts for time / weather

- **Size 96** - Only Limited Icons / Limited Text
- **Size 128** - Only Limited Icons / Limited Text

## Colors

- Background Color: **6339**

  **RGB888:** #1b1b1b / 0x1b1b1b
  **RGB565:** #18C3 / 0x18C3

- Text: **57083**

  **RGB888:** #dcdbdb / 0xdcdbdb
  **RGB565:** #DEDB / 0xDEDB

- Text Inactive: **29582**

  **RGB888:** #717171 / 0x717171
  **RGB565:** #738E / 0x738E

- Text Disabled: **12678**

  **RGB888:** #313131 / 0x313131
  **RGB565:** #3186 / 0x3186

- Component: **65535**

- Component Active: **19773**

  Button Text Action, Active Slider

  **RGB888:** #4ba6ee / 0x4ba6ee
  **RGB565:** #4D3D / 0x4D3D

- Component Accent: **62694**

  **RGB888:** #f09d37 / 0xf09d37
  **RGB565:** #F4E6 / 0xF4E6

- Component Background: **38066**

  **RGB888:** #4c4c4c / 0x4c4c4c
  **RGB565:** #94B2 / 0x94B2

## How to edit the HMI file

![Grid](../nextion/images/grid.png)

To edit the HMI file, no special care is needed. Following are some helpful infos. The HMI is used mostly to design the interface but does not need any special code. Only on a page based lifetime of events should be done on the display. If possible, the logic should be placed in the AppDaemon App.

All pages need to send a `sendme` in `Preinitialize`. This is needed to know of a page change event.

Prepare the page in the `Preinitialize` event because the AppDaemon App cannot control the display at this stage. Only after a page is shown, it is possible to change anything or interact with it.

If you want to process any click events, you need to enable `Send Component ID` on the event to be used.

If you want to interact with any component on the display, the component id and objectname is required. They are being used and are defined in the AppDaemon App.

When changing order of components on a page, be aware, that the id of the components will change.
