---
title: Configuration Overview
description: Overview of the NSPanel HAUI configuration system
---

# Configuration

[README](../README.md) | [Documentation](README.md) | [Installation](Install.md) | [Configuration](Config.md) | [Panels](panels/README.md) | [FAQ](FAQ.md)

- [Configuration](#configuration)
  - [Example Configuration](#example-configuration)
  - [Common Configuration](#common-configuration)
  - [Device Config](config/device.md)
  - [Panel Config](config/panels.md)
  - [Item Config](config/items.md)

The NSPanel HAUI configuration is organised into three areas:

1. **[Device Configuration](config/device.md)** — device-level settings including the `device` dict (name, locale, hardware buttons, timeouts, relays, sound, colour overrides), plus the `navigation`, `notification`, `update`, `connection`, and `gesture` controllers.
2. **[Panel Configuration](config/panels.md)** — how panels are defined in the `panels` list: modes (panel/subpanel/popup), keys, navigation, home/sleep/wakeup panels, auto-close timeouts, and code locking.
3. **[Item Configuration](config/items.md)** — how items relate to HA entities, overriding state/name/value/icon/color, internal items (skip, text, navigate, action), templating, and popup overrides.

## Example Configuration

To get an idea of the configuration, see [example configurations](Example_Config.md).

## Common Configuration

For time and date formats see:

CLDR Locale Data (see `haui/utils/locale_data.py` for supported format keys)

Python Documentation <https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes>

- `time_format` string

  Time format

- `date_format` string

  Date format

- `date_format_locale` string

  CLDR locale format key (e.g. `full`, `long`, `medium`, `short`).
  Deprecated alias: `date_format_babel` (still supported for backward compatibility).

```yaml
time_format: "%H:%M"
date_format: "%A, %d. %B %Y"
date_format_locale: "full"
```
