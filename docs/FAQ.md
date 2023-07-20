# FAQ

[README](../README.md) | [Documentation](README.md) | [Installation](Install.md) | [Configuration](Config.md) | [Panels](panels/README.md) | [FAQ](FAQ.md)

- [FAQ](#faq)
  - [I don't know how to start](#i-dont-know-how-to-start)
  - [How to upload a TFT file](#how-to-upload-a-tft-file)
  - [Update is not possible](#update-is-not-possible)

## I don't know how to start

Take a look at some [example configurations](Example_Config.md). If you still don't know, how to do anything, please open an issue.

## How to upload a TFT file

- Using a button:
  - Button: `Update Display`

- Using a service:
  - Service: `nspanel_haui_upload_tft`
  - Service: `nspanel_haui_upload_tft_url`

## Update is not possible

If you are getting errors like `Reading from UART timed out at byte 0!` or `Upgrade response is   0` the easiest way to fix this is using the Nextion Editor and a display connected to 5V, GND, TF-TX, TF-RX (See [https://blakadder.com/nspanel-teardown/](https://blakadder.com/nspanel-teardown/) for connection details) to upload a new display file.
This will most likely fix the issue.
