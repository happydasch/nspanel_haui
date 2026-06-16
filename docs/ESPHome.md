# ESPHome Component

[README](../README.md) | [Documentation](README.md) | [Installation](Install.md) | [Configuration](Config.md) | [Panels](panels/README.md) | [FAQ](FAQ.md)

The NSPanel is operating on a ESP32. To provide access to the NSPanel via HomeAssistant, ESPHome is being used.

- Uses the ESPHome and the nextion display component
- Provides scripts and actions for communication with the display
- Responsible for handling the device functionality

For the communication between the device and the server ESPHome native API events are used.

- [ESPHome Component](#esphome-component)
  - [Installation](#installation)
  - [Config](#config)
  - [Communication](#communication)
    - [Connection Globals](#connection-globals)
    - [Connection Scripts](#connection-scripts)
    - [Events](#events)
    - [Actions](#actions)
  - [Requests](#requests)
  - [Responses](#responses)
  - [Commands](#commands)
  - [Events](#events-1)
  - [Actions](#actions-1)
  - [Page](#page)
  - [Interaction](#interaction)
    - [Interaction Sensors](#interaction-sensors)
  - [Brightness and Dimming](#brightness-and-dimming)
    - [Brightness Sensors](#brightness-sensors)
  - [Temperature](#temperature)
  - [Buttons](#buttons)
  - [Diagnostics](#diagnostics)
  - [Other](#other)

## Installation

See `esphome/install.yaml` for the installation configuration. This file is going to be installed on the device.
See `esphome/nspanel_haui.yaml` for the esphome configuration file. This file contains all ESPHome functionality.

Copy the secrets from `esphome/secrets.yaml` and add them in ESPHome by pressing the `Secrets` Link in the right corner. This step is not neccessary if you add the secrets directly in the config file.

To install ESPHome on the device use the config from `esphome/install.yaml`. Edit the substitution values and install the device.

If the device shows up in Home Assistant you can manually install the TFT file by pressing the `Upload Display` button. The TFT file will automatically be installed when the device connects to the Hub app.

See [Nextion](Nextion.md) for more details about the display.

## Config

An overview of all configuration variables defined in the ESPHome yaml file.

- `heartbeat_interval` (5)
- `name` (nspanel-haui)
- `ota_password` (!secret ota_password)
- `api_encryption_key` (!secret api_encryption_key)
- `web_username` (!secret web_username)
- `web_password` (!secret web_password)
- `wifi_ssid` (!secret wifi_ssid)
- `wifi_password` (!secret wifi_password)
- `tft_update_url` (URL to the ``nspanel_haui.tft`` file, e.g. ``http://homeassistant.local:8123/local/nspanel/nspanel_haui.tft``)

## Communication

All communication between the ESPHome device and the Hub app uses ESPHome Native API events. The configuration for events is in `esphome/nspanel_haui/scripts_event.yaml`. The connection scripts are in `esphome/nspanel_haui/scripts_connection.yaml`.

See [docs/Communication.md](Communication.md) for the full protocol description.

### Connection Globals

The device maintains four globals for connection state (defined in `esphome/nspanel_haui/globals.yaml`):

- `hub_availability` (bool) - Whether the ESPHome Native API is connected to Home Assistant. Set by `on_client_connected` / `on_client_disconnected`.
- `hub_heartbeat` (int) - Last timestamp (epoch seconds) when a hub heartbeat was received. Set by the `hub_heartbeat` action; used by `check_hub_connection` for timeout detection.
- `hub_connection` (bool) - Whether the connection handshake with the Hub app has completed. Set by `set_hub_connected` script.
- `haui_init` (bool) - Whether the device has been initialized by the Hub app.

### Connection Scripts

Defined in `esphome/nspanel_haui/scripts_connection.yaml`:

- `set_hub_connected(connected: int)` - Updates `hub_connection`, anchors/resets `hub_heartbeat`, shows system page on disconnect, writes `system.firstRun.txt="0"` on connect, publishes `client_status` sensor.
- `check_hub_connection` - Runs every 100ms. Detects timeout (hub heartbeat not received within `heartbeat_interval × 2`) or hub unavailability.
- `check_connection` - Runs every 100ms. Sends `req_connection` when disconnected but hub is available, with 10s cooldown between attempts.

### Events

The primary events used for connection management:

- **`esphome.heartbeat`** - Device→Hub heartbeat. Published every `heartbeat_interval` seconds (5s by default) when `hub_connection = true`. Value: `"alive"`.
- **`esphome.req_connection`** - Device→Hub connection request. Published when disconnected and hub is available. Value: JSON with device info (name, MAC, IP, TFT version, etc.).
- **`esphome.res_connection`** - Device→Hub connection response. Published after receiving `hub_connection_response`. Value: JSON with `heartbeat_interval`.
- **`esphome.res_device_state`** - Device→Hub state response. Published after receiving `req_device_state`. Value: JSON with device state (page, brightness, display_state, etc.).

### Actions

Actions that the Hub app can call on the device (via ESPHome Native API service calls):

- **`hub_heartbeat`** - Hub→Device heartbeat. Resets `hub_heartbeat` timestamp on the device.
- **`hub_connection_response`** - Hub acknowledges connection request. Device transitions to sending `res_connection`.
- **`hub_connection_initialized`** - Handshake complete. Sets `hub_connection = true` on the device.
- **`hub_connection_closed`** - Hub disconnects the device. Sets `hub_connection = false`.
- **`req_device_state`** - Hub requests device state. Device responds with `res_device_state` event.
- **`req_device_info`** - Hub requests device info. Device responds with `res_device_info` event.
- **`req_reconnect`** - Hub requests device to reconnect. Calls `set_hub_connected(false)`.
- **`reset_last_interaction`** - Resets the device's display inactivity timer (dim/sleep).

## Requests

These events will get a response.

- `req_device_info` Device Info Request
- `req_device_state` Device State Request
- `req_reconnect` Reconnect Request
- `req_val` Number Request
- `req_txt` Text Request

## Responses

These responses will be sent after a request.

- `res_device_state` Device State Event:

  Will be published after sending request `req_device_state`
  Value: json encoded string

- `res_device_info` Device Info Event:

  Will be published after sending request `req_device_info`
  Value: json encoded string

- `read_response` Component Read Response

  Unified response for component reads (number or text).  Published after
  sending `req_val` or `req_txt`.  Value: JSON encoded string with the
  keys `name` (component name), `type` (`"number"` or `"text"`), and
  `value` (the read value).

## Commands

These are commands that are being executed on the ESP.

- `send_command` Sends a command to the nextion display
- `send_commands`Sends multiple commands to the nextion display
- `goto_page` Sets the active page on display
- `send_notification` Sends a notification to the display

  Parameters: `title` (string), `message` (string), `icon` (string, optional - pass `""` to omit), `timeout` (int, seconds), `persistent` (bool - when true the notification sound loops until dismissed)

## Events

Different ESP device events.

- `connected` Connected Event:

  Will be sent after connection was established

- `sleep` Sleep Event:

  Display went to sleep

- `wakeup` Wakeup Event:

  Display woke up

- `page` Page Change Event:

  A new page was opened
  Value: page_id

- `brightness` Brightness Change Event:

  The brightness was changed
  Value: brightness

- `component` Component Press Event:

  The component was pressed

- `touch_start` Touch Pressed Event:

  The touch screen was pressed
  Value: -

- `touch` Touch Event:

  The touch screen is active
  Value: touch_x,touch_y

- `touch_end` Touch Released Event:

  The touch screen was released
  Value: start_x,start_y,end_x,end_y

- `gesture` Touch Gesture Event:

  The gesture was recognized on the screen
  Value: gesture_str

- `button_left` Left Physical Button Pressed Event:

  The left physical button was pressed
  Value: state (1 or 0)

- `button_right` Right Physical Button Pressed Event:

  The right physical button was pressed
  Value: state (1 or 0)

- `relay_left` Relay Switched Event:

  The left relay was switched
  Value: state (1 or 0)

- `relay_right` Relay Switched Event:

  The right relay was switched
  Value: state (1 or 0)

- `timeout` Timeout Event:

  An internal timeout happened (dim, page, sleep)
  Value: timeout type (string)

- `display_state` Display State Event:

  Current display state (on, off, dim)
  Value: state type (string)

## Actions

This actions below are defined on the ESP. The communication between the Hub server and the ESP is using these.

- `send_command` Action to send a command

  This will send a command to the nextion display

- `upload_tft` Action to update a TFT file

  This will update the nextion display with the tft file

- `upload_tft_url` Action to update a TFT file from URL

- `set_brightness` Action to change the brightness of the display

- `goto_page` Action to change the page of the display

- `play_rtttl` Action to play a song for RTTTL strings

  RTTTL Strings

  ```text
  startup:4:d=4,o=5,b=200:8c7,8g7,8d7,8g7
  tone:4:d=8,o=6,b=200:16e6
  tone_up:4:d=16,o=5,b=160:16e6,16g6
  tone_down:4:d=16,o=5,b=160:16g6,16d6
  notification:4:d=8,o=6,b=200:16e,16c6,16g6,8c6,8g6
  alert_fast:4:d=8,o=6,b=200:16c7,16d7,16c7,16d7,16c7,16d7,16c7,16d7,16e7
  alert:4:d=16,o=6,b=400:16c7,16d7,16c7,16d7,16c7,16d7,16c7,16d7,16e7
  seq_up:4:d=16,o=5,b=160:16e6,16g6
  seq_down:4:d=16,o=5,b=160:16g6,16d6
  elise:d=8,o=5,b=125:32p,e6,d#6,e6,d#6,e6,b,d6,c6,4a.,32p,c,e,a,4b.,32p,e,g#,b,4c.6,32p,e,e6,d#6,e6,d#6,e6,b,d6,c6,4a.,32p,c,e,a,4b.,32p,d,c6,b,2a
  ```

  Other sounds from different sources:

  ```text
  startup_long:d=16,o=5,b=180:c,e,g,c6,8p,c,16p,e,c
  startup:d=16,o=5,b=180:c,e,g,c6
  two short:d=4,o=5,b=100:16e6,16e6
  short:d=4,o=5,b=100:16e6
  scale_up:d=32,o=5,b=100:c,c#,d#,e,f#,g#,a#,b
  chirp6:d=4,o=5,b=400:c6
  doodle-dah:d=8,o=5,b=250:d#6,a5#,d#6
  doodle-duh:d=8,o=5,b=250:d#6,a5#,d#5
  ```

- `play_sound` Action to play a named sound

- `publish_event` Action to publish an event

- `reset_last_interaction` Action to reset the last interaction value

  This will update the last interaction value to now

- `reset_last_interaction_offset` Action to reset the last interaction value adding an offset

- `send_notification` Action to send a notification to a display

  Parameters: `title`, `message`, `icon` (optional), `timeout`, `persistent`

## Page

These events will be sent out when the device have some page related events.

- `page` (0 - 255)
  The page that is being displayed

- `timeout_page` (0 - 3600)

  Page switch timeout, will be restored on reboot

  Value > 0 activates the timeout

- After Page Timeout: page goes to sleep_page (default if not set)

## Interaction

The configuration for this functionality is in `esphome/nspanel_haui/scripts_interaction.yaml`

When tracking the last interaction with the device, two input methods are possible: Touchscreen and Buttons. It's possible to disable button as an interaction source by switching off `use_button_interaction`.

### Interaction Sensors

The ESP provides some interaction related events. See below for a overview of all sensors. Some sensors are set to internal to not pollute HA.

- `touch` (button)

  Touch State, the state is being set based on the `touch_x` and `touch_y` values

- `touch_x` (0 - 480=display width, only 0..450 is visible; the rightmost 30px are behind the bezel)

  Current touch x coordinates (0 when released)

- `touch_y` (0 - 320=display height)

  Current touch y coordinates (0 when released)

- `button_left` (physical button left)

  Physical button left state

- `button_right` (physical button right)

  Physical button right state

- `use_button_interaction` (switch)

  Should buttons be used for updating last interaction time.

- `use_auto_dimming` (switch)

  Should display be automatically dimmed.

- `use_auto_page` (switch)

  Should page be automatically switched.

- `use_auto_sleeping` (switch)

  Should display be automatically go to sleep.

- `relay_left` (relay switch)

- `relay_right` (relay switch)

- `use_relay_left` (switch)

  Defines if the physical button left should use the internal relay

- `use_relay_right` (switch)

  Defines if the physical button right should use the internal relay

- `last_interaction` (millis()/1000)

  Last time when a interaction happened with the display

## Brightness and Dimming

The configuration for this functionality is in `esphome/nspanel_haui/scripts_display.yaml`

The display has 3 states: on, off and dimmed

The whole brightness and dimming functionality is implemented on the ESPHome device.

The brightness change process is processed this way:

- **Within Dimming Timeout:** full brightness is being used (State on)

- **After Dimming Timeout:** dimmed brightness is being used, duration is defined by dimming duration (State dimmed)

- **After Sleep Timeout:** brightness goes to 0 if sleep mode is activated,
  duration is defined by dimming duration (State off)

### Brightness Sensors

Brightness related sensors.

- `brightness` (0 - 100)

  Current brightness, taken from nextion var

- `brightness_full` (1 - 100)

  Full brightness, will be restored on reboot

- `brightness_dim` (0 - 100)

  Dimmed brightness, will be restored on reboot

- `duration_dim` (0.0 - 10.0)

  Dimming duration, will be restored on reboot

- `timeout_dim` (0 - 3600)

  Dimming timeout after last interaction, will be restored on reboot
  Value > 0 activates the timeout

- `timeout_sleep` (0 - 3600)

  Sleeping mode timeout, will be restored on reboot
  Value > 0 activates the timeout

## Temperature

Temperature related sensor.

- `temperature` (in celsius)

  Temperature sensor reading

- `temperature_correction` (-10.0 - 10.0)

  Correction for sensor reading

## Buttons

Buttons provided by the ESP.

- `upload_tft`

  This button uploads the tft from a configured url to nextion

- `restart`

  Restarts the device

- `restart_display`

  Restarts the display

- `factory_reset`

  Resets the device

## Diagnostics

Diagnostics related sensors.

- YAML-Version: `display_yaml_version` Version of YAML files
- TFT-Version: `display_tft_version` Version of TFT File
- WIFI Info: Different values from wifi
- Uptime: Device uptime

## Other

For number and text retrieval the internal sensors `req_txt_component`,
`req_val_component`, `res_txt`, and `res_val` are used.  These feed the
unified `esphome.read_response` event and make it possible to get values
from the display without adding a sensor for every single value to retrieve.
