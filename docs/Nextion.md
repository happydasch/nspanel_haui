# Nextion Component Details

- [Nextion Component Details](#nextion-component-details)
  - [How to upload a TFT file](#how-to-upload-a-tft-file)
  - [How to edit the HMI file](#how-to-edit-the-hmi-file)
  - [What information is being provided](#what-information-is-being-provided)
  - [Design Guidelines](#design-guidelines)

The HMI file of this project is only used to display the panels. Most logic is implemented in the AppDaemon App. The display is responsible for showing the panels, doing time critical processing like animations, preparing components on pages before they being shown.

The ESP processes the serial communication and creates events which are being sent via MQTT.
Only the ESP communicates directly with the display.

## How to upload a TFT file

- using button:
  - Button: `Update Display`

- using custom url:
  - Service: `nspanel_haui_upload_tft`
  - Service: `nspanel_haui_upload_tft_url`

## How to edit the HMI file

To edit the HMI file, no special care is needed. Following are some helpful infos. The HMI is used mostly to design the interface but does not need any special code. Only on a page based lifetime of events should be done on the display. If possible, the logic should be placed in the AppDaemon App.

Prepare the page in the `Preinitialize` event because the AppDaemon App cannot control the display at this stage. Only after a page is shown, it is possible to change anything or interact with it.

If you want to process any click events, you need to enable `Send Component ID` on the event to be used.

If you want to interact with any component on the display, the component id and objectname is required. They are being used and are defined in the AppDaemon App.

When changing order of components on a page, be aware, that the id of the components will change.

## What information is being provided

Following informations are extracted from the display and is available on the ESP:

- Page
- Brightness
- Touch Events (touch coordinates and touch state)
- Component Events (press and release)

## Design Guidelines

- Default Color: **6339** (Default background color)

  **RGB888:** #1b1b1b / 0x1b1b1b

  **RGB565:** #18C3 / 0x18C3

- Active Color: **12678** (Color when something is pressed)

  **RGB888:** #313131 / 0x313131

  **RGB565:** #3186 / 0x3186

- Text Color: **57083**

  **RGB888:** #dcdbdb / 0xdcdbdb

  **RGB565:** #DEDB / 0xDEDB

- Inactive Color: **29582** (For inactive or less important infos)

  Disabled Text

  **RGB888:** #717171 / 0x717171

  **RGB565:** #738E / 0x738E

- Highlight Color: **19773** (Highlight color)

  Button Text Action

  **RGB888:** #4ba6ee / 0x4ba6ee

  **RGB565:** #4D3D / 0x4D3D

- Accent Color: **62694** (Accent color)

  **RGB888:** #f09d37 / 0xf09d37

  **RGB565:** #F4E6 / 0xF4E6

- Active color slider: #4BA6EE
- Inactive color slider: #DCDBDB
- 4c4c4c
- 999999
