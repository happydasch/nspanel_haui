# FAQ

- [FAQ](#faq)
  - [How to upload a TFT file](#how-to-upload-a-tft-file)
  - [Getting errors while updating, update is not possible](#getting-errors-while-updating-update-is-not-possible)

## How to upload a TFT file

- Using a button:
  - Button: `Update Display`

- Using a service:
  - Service: `nspanel_haui_upload_tft`
  - Service: `nspanel_haui_upload_tft_url`

## Getting errors while updating, update is not possible

If you are getting errors like `Reading from UART timed out at byte 0!` or `Upgrade response is   0` the easiest way to fix this is using the Nextion Editor and a display connected to 5V, GND, TF-TX, TF-RX (See [https://blakadder.com/nspanel-teardown/](https://blakadder.com/nspanel-teardown/) for connection details) to upload a new display file.
This will most likely fix the issue.
