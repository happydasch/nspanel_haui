# FAQ

[README](../README.md) | [Documentation](README.md) | [Installation](Install.md) | [Configuration](Config.md) | [Panels](panels/README.md) | [FAQ](FAQ.md)

- [FAQ](#faq)
  - [I don't know how to start](#i-dont-know-how-to-start)
  - [How to upload a TFT file](#how-to-upload-a-tft-file)
  - [Update is not possible](#update-is-not-possible)
  - [Weather forecast does not work](#weather-forecast-does-not-work)
  - [Error on sleep](#error-on-sleep)
  - [The display should change its brightness and sleep state over the day](#the-display-should-change-its-brightness-and-sleep-state-over-the-day)

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

## Weather forecast does not work

Due to limitations of AppDaemon it is not possible to get responses from service calls. As a workaround a sensor can be created in home assistant that provides weather forecasts.

See [https://github.com/joBr99/nspanel-lovelace-ui/issues/1001](https://github.com/joBr99/nspanel-lovelace-ui/issues/1001) and [https://docs.nspanel.pky.eu/stable/prepare_ha/#workaround-for-homeassistant-202404](https://docs.nspanel.pky.eu/stable/prepare_ha/#workaround-for-homeassistant-202404) for details about the workaround.

hourly weather forecasts:

```yaml
template:
  - trigger:
      - platform: homeassistant
        event: start
      - platform: time_pattern
        hours: /1
    action:
      - service: weather.get_forecasts
        data:
          type: hourly
        target:
          entity_id: weather.home
        response_variable: hourly
    sensor:
      - name: Weather Forecast Hourly
        unique_id: weather_forecast_hourly
        state: "{{ now().isoformat() }}"
        attributes:
          forecast: "{{ hourly['weather.home'].forecast }}"
```

daily weather forecasts:

```yaml
template:
  - trigger:
      - platform: homeassistant
        event: start
      - platform: time_pattern
        hours: /1
    action:
      - service: weather.get_forecasts
        data:
          type: daily
        target:
          entity_id: weather.home
        response_variable: daily
    sensor:
      - name: Weather Forecast Daily
        unique_id: weather_forecast_daily
        state: "{{ now().isoformat() }}"
        attributes:
          forecast: "{{ daily['weather.home'].forecast }}"
```

## Error on sleep

You may see log entries as below. This cannot be changed and does not any harm.

```log
[I] [haui:602] Display is going to sleep
[E] [nextion:536] ERROR: Received numeric return but the queue is empty
```

## The display should change its brightness and sleep state over the day

Add a automation in home assistant. NSPanel HAUI does not support to change this but home assistant is way more flexible so it's very simple to change anything dynamically using home assistant automations.

Here is an example automation:

Day (from sunrise)
Dimmed to 55%, no sleep

```yaml
alias: NSPanel HAUI Day
description: ""
trigger:
  - platform: sun
    event: sunrise
condition: []
action:
  - action: switch.turn_off
    metadata: {}
    data: {}
    target:
      entity_id:
        - switch.nspanel_haui_use_auto_sleeping
  - action: number.set_value
    metadata: {}
    data:
      value: "55"
    target:
      entity_id:
        - number.nspanel_haui_brightness_dimmed
mode: single
```

Evening (from sunset)
Dimmed to 20%, no sleep

```yaml
alias: NSPanel HAUI Evening
description: ""
trigger:
  - platform: sun
    event: sunset
condition: []
action:
  - action: switch.turn_off
    metadata: {}
    data: {}
    target:
      entity_id:
        - switch.nspanel_haui_use_auto_sleeping
  - action: number.set_value
    metadata: {}
    data:
      value: "20"
    target:
      entity_id:
        - number.nspanel_haui__brightness_dimmed
mode: single
```

Night (4,5h after sunset)
Display can go to sleep (the dimmed brightness will remain 20%)

```yaml
alias: NSPanel HAUI Night
description: ""
trigger:
  - platform: sun
    event: sunset
    offset: "04:30:00"
condition: []
action:
  - action: switch.turn_on
    metadata: {}
    data: {}
    target:
      entity_id:
        - switch.nspanel_haui_use_auto_sleeping
mode: single
```
