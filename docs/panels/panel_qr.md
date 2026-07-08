---
title: Panel QR Code
description: QR Code panel configuration and options
---

# Panel QR-Code
## About

`type: qr`

The QR-Code panel can be used to display a qr code containing provided informations for example wifi access.

The panel can show 2 different qr code sizes. It will display a big qr code if there are no entities configured. If there are entities then a smaller qr code will be shown on one half and entity informations on the other.

If the smaller qr code is available, by touching the qr code the big qr code will be displayed and vice versa.

If the big qr code is activated, then the display will not turn off.

The entity values will be split on two lines if value is longer than 15 characters.

The panel can be started with a big QR by setting `big_qr` to True.

There is also a **text display** option: when no entities are configured and `show_text` is `true`, the SSID and password are shown as plain text labels alongside the QR code. The zoom toggle works normally — big QR hides the text, small QR shows it with the text.

## Config

```yaml
panels:

  # big qr code
  - type: qr
    essid: MySSID
    password: MyPassW0rd
    big_qr: true

  # small qr code
  - type: qr
    essid: MySSID
    password: MyPassW0rd
    big_qr: false
    entities:
      - entity: "text:Test 1"
        name: Title 1
        icon: mdi:key
      - entity: "text:Test 2"
        name: Title 2
        icon: mdi:wifi
```

### ESSID + Password

The wifi credentials are entered as two separate text fields: `essid` (WiFi network name) and `password` (WiFi password). The integration automatically builds the QR code string in the standard WiFi format:

```
WIFI:S:<SSID>;T:WPA;P:<PASSWORD>;;
```

Source: [https://en.wikipedia.org/wiki/QR_code#Joining_a_Wi%E2%80%91Fi_network](https://en.wikipedia.org/wiki/QR_code#Joining_a_Wi%E2%80%91Fi_network)

### Start with big QR

```yaml
- type: qr
  ...
  big_qr: true
```

### Text display

When `show_text` is `true` and no entities are configured, the SSID and password are shown as plain text labels alongside the QR code. The zoom toggle controls visibility — big QR hides the text, small QR reveals it.

```yaml
- type: qr
  essid: MySSID
  password: MyPassW0rd
  show_text: true
```
