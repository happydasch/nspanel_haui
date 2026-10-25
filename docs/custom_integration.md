---
title: Custom Integration
description: Install and add the NSPanel HAUI integration
---

# Custom Integration

## Overview

NSPanel HAUI runs as a native Home Assistant custom integration. No external addon required.

## Requirements

- Home Assistant 2026.5+
- ESPHome device flashed and connected (see [Installation Guide](install.md) steps 1-2)

## Installation

For most users, the **recommended installation method** is via HACS, adding the integration through the Home Assistant UI's config flow workflow:

1. Install via HACS or copy the `custom_components/nspanel_haui/` folder into your HA config directory:
   ```
   <ha_config>/custom_components/nspanel_haui/
   ```
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration → NSPanel HAUI** to set up via the config flow.

## Configuration

**The primary configuration method is the HA UI panel editor.** After adding the integration, open **NSPanel HAUI** in the Home Assistant sidebar (admin only), select your device and add, remove and configure panels there.

For full config options see [Configuration Details](configuration/README.md).
