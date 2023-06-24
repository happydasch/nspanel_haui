# ESPHome Component

[README](../README.md) | [Documentation](README.md) | [Installation](Install.md) | [Configuration](Config.md) | [Panels](panels/README.md) | [FAQ](FAQ.md)

The NSPanel is operating on a ESP32. To provide access to the NSPanel via HomeAssistant, ESPHome is being used.

- Provides Scripts and Services for Communication with display
- Responsible for handling the device functionality

See `esphome/nspanel-haui.yaml` for the configuration file for your device.

The communication between ESPHome is done mostly via MQTT.

- [ESPHome Component](#esphome-component)
  - [Config](#config)
  - [Installation](#installation)
  - [Custom Component](#custom-component)
  - [Getting Data](#getting-data)
  - [Communication](#communication)
  - [Requests](#requests)
  - [Responses](#responses)
  - [Commands](#commands)
  - [Events](#events)
  - [Scripts](#scripts)
  - [Page](#page)
  - [Interaction](#interaction)
    - [Interaction Sensors](#interaction-sensors)
  - [Brightness and Dimming](#brightness-and-dimming)
    - [Brightness Sensors](#brightness-sensors)
  - [Temperature](#temperature)
  - [Buttons](#buttons)
  - [Diagnostics](#diagnostics)
  - [Resources](#resources)

## Config

An overview of all config variables defined in the ESPHome yaml file.

- `yaml_version` (0.0.0)
- `required_tft_version` (0.0.0)
- `device_name` (nspanel-haui)
- `friendly_name` (NSPanel HAUI)
- `heartbeat_interval` (5)
- `topic_prefix` (nspanel_haui/nspanel_haui)
- `topic_cmd` ($topic_prefix/cmd)  # used for sending events
- `topic_recv` ($topic_prefix/recv)  # used to recieve events
- `ota_password` (!secret ota_password)
- `encryption_key` (!secret encryption_key)
- `web_username` (!secret web_username)
- `web_password` (!secret web_password)
- `wifi_ssid` (!secret wifi_ssid)
- `wifi_password` (!secret wifi_password)
- `mqtt_ip` (!secret mqtt_ip)
- `mqtt_username` (!secret mqtt_username)
- `mqtt_password` (!secret mqtt_password)
- `tft_update_url` ([http://homeassistant.local:8123/local/nspanel/nspanel.tft](http://homeassistant.local:8123/local/nspanel/nspanel.tft))

## Installation

1. Copy custom component to server
2. esp code update using yaml file

## Custom Component

A custom esphome component `nspanel_haui` is being used. The component is based on the nextion component but supports a different kind of accessing data.

The name of the configuration for this functionality is `esphome/dev/1_nspanel_haui_component.yaml`

Following functionality is provided by the component:

- some of the serial processing functionality from nextion, parsing data:

  - 0x00 - 0x24: status
  - 0x66: page
  - 0x65, 0x67, 0x68: touch
  - 0x70, 0x71: vars
  - 0x86,0x87: wakeup, sleep
  - 0x88: startup

- component callback methods:

  - on_component (press and release events)
  - on_touch (through using sendxy)
  - on_page (through using sendme)

- communication methods:

  - send_command
  - set_component_int
  - set_component_txt
  - get_int_value
  - get_txt_value
  - get_component_txt
  - get_component_int

- all processing needs to be manually, all value requests needs to be done manually

## Getting Data

There are different methods to get data from the display. The requests are published with MQTT. The response will be returned after. See [Requests](#requests) for different methods.

## Communication

The name of the configuration for this functionality is `esphome/dev/2_nspanel_connection.yaml`

A description of events being used for communication between ESP and AppDaemon.

- `heartbeat` Heartbeat Event:

  Will be published every 5 seconds (can be changed in config)
  Value: string (alive)

  The client will get an heartbeat timeout after heartbeat_interval * 2 (can be changed in the config) and will reset to system page.

- `req_connection` Connection Request
- `res_connection` Connection Response
- `ad_heartbeat` Server Heartbeat Response
- `ad_connection_initialized` Server Response
- `ad_connection_closed` Server Response

## Requests

These events will get a response.

- `req_device_info` Device Info Request
- `req_device_state` Device State Request
- `req_reconnect` Reconnect Request
- `req_int_value` Number Value Request
- `req_txt_value` Text Value Request
- `req_component_int` Component Number Value Request
- `req_component_txt` Component Text Value Request

## Responses

These responses will be sent after a request.

- `res_device_state` Device State Event:

  Will be published after sending request `req_device_state`
  Value: json encoded string

- `res_device_info` Device Info Event:

  Will be published after sending request `req_device_info`
  Value: json encoded string

- `res_int_value` Number Value Response
- `res_txt_value` Text Value Response
- `res_component_int` Component Number Value Response
- `res_component_txt` Component Text Value Response

## Commands

These are commands that are being executed on the ESP.

- `send_command` Sends a command to the nextion display
- `send_commands`Sends multiple commands to the nextion display
- `set_component_text` Sets a component text on the nextion display
- `set_component_value` Sets a component value on the nextion display
- `goto_page` Sets the active page on display

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

## Scripts

This scripts below are defined on the ESP. Most of the device functionality is defined here.

- `send_command` Service to send a command

  This will send a command to the nextion display

- `upload_tft` Service to update a TFT file

  This will update the nextion display with the tft file

- `upload_tft_url` Service to update a TFT file from URL

- `set_component_text` Service to set the text of a component

- `set_component_value` Service to set the value of a component

- `set_brightness` Service to change the brightness of the display

- `goto_page` Service to change the page of the display

- `play_rtttl` Service to play a song for RTTTL strings

  RTTTL Strings

  ```text
  startup:4:d=4,o=5,b=200:8c7,8g7,8d7,8g7
  tone:4:d=8,o=6,b=200:16e6
  tone_up:4:d=16,o=5,b=160:16e6,16g6
  tone_down:4:d=16,o=5,b=160:16g6,16d6
  notification:4:d=8,o=6,b=200:16e,16c6,16g6,8c6,8g6
  alert_fast:4:d=8,o=6,b=200:16c7,16d7,16c7,16d7,16c7,16d7,16c7,16d7,16e7
  alert:4:d=16,o=6,b=400:16c7,16d7,16c7,16d7,16c7,16d7,16c7,16d7,16e7
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

- `play_sound` Service to play a named sound

- `publish_event` Service to publish an event

- `reset_last_interaction` Service to reset the last interaction value

  This will update the last interaction value to now

- `reset_last_interaction_offset` Service to reset the last interaction value adding an offset

## Page

These events will be sent out when the device have some page related events.

- `page` (0 - 255)
  The page that is being displayed

  The nextion variable dp is being used to set the page_id

- `timeout_page` (0 - 3600)

  Page switch timeout, will be restored on reboot

  Value > 0 activates the timeout

- After Page Timeout: page goes to sleep_page (default if not set)

## Interaction

The name of the configuration for this functionality is `esphome/dev/2_nspanel_interaction.yaml`

When tracking the last interaction with the device, two input methods are possible: Touchscreen and Buttons. It's possible to disable button as an interaction source by switching off `use_button_interaction`.

### Interaction Sensors

The ESP provides some interaction related events. See below for a overview of all sensors. Some sensors are set to internal to not pollute HA.

- `touch` (button)

  Touch State, the state is being set based on the `touch_x` and `touch_y` values

- `touch_x` (0 - 480=display width)

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

The name of the configuration for this functionality is `esphome/dev/4_nspanel_dimming.yaml`

The whole brightness and dimming functionality is implemented on the ESPHome device.

The brightness change process is processed this way:

- **Within Dimming Timeout:** full brightness is being used

- **After Dimming Timeout:** dimmed brightness is being used, duration is defined by dimming duration

- **After Sleep Timeout:** brightness goes to 0, sleep mode is activated,
  duration is defined by dimming duration

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

- WIFI Info: Different values from wifi
- Uptime: Device uptime

## Resources

- https://esphome.io
- https://nextion.tech/instruction-set/
- https://github.com/masto/NSPanel-Demo-Files
- https://github.com/Blackymas/NSPanel_HA_Blueprint
- https://github.com/marcfager/nspanel-mf
- https://github.com/joBr99/nspanel-lovelace-ui
- https://github.com/Blackymas/NSPanel_HA_Blueprint
- https://github.com/krizkontrolz/Home-Assistant-nextion_handler
