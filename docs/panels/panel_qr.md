---
title: Panel QR Code
description: QR Code panel — display Wi-Fi QR codes, URLs, or custom text
---

# Panel QR-Code

![](../assets/previews/panel-qr.svg)

## About

The QR code panel displays a QR code, for example for Wi-Fi network access. It can show two different sizes: a large QR code when no entities are configured, or a smaller QR code with entity information on the other half.

- Tapping the QR code toggles between big and small sizes.
- When the big QR code is displayed, the display will not turn off.
- Entity values longer than 15 characters are split across two lines.

## How to configure

In the **panel editor**, set:

### ESSID and Password

Enter the Wi-Fi network name (SSID) and password as text fields. The integration automatically builds the QR code in the standard Wi-Fi format:

```
WIFI:S:<SSID>;T:WPA;P:<PASSWORD>;;
```

### Start with Big QR (toggle)

When enabled, the panel starts with the QR code displayed large. Default: Off.

### Show Text (toggle)

When enabled and no entities are configured, the SSID and password are shown as plain text labels alongside the QR code. The zoom toggle controls visibility — big QR hides the text, small QR reveals it. Default: On.

### Entities

You can add entities to display alongside the QR code. When entities are configured, the QR code appears smaller on one side with entity information on the other.
