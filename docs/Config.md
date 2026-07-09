---
title: Configuration Overview
description: Overview of the NSPanel HAUI configuration system
---

# Configuration
The NSPanel HAUI configuration is organised into three areas:

1. **[Device Configuration](config/device.md)** — device-level settings including the `device` dict (name, locale, hardware buttons, timeouts, relays, sound, colour overrides), plus the `navigation`, `notification`, `update`, `connection`, and `gesture` controllers.
2. **[Panel Configuration](config/panels.md)** — how panels are configured: modes (panel/subpanel/popup), keys, navigation, home/sleep/wakeup panels, auto-close timeouts, and code locking.
3. **[Item Configuration](config/items.md)** — how items relate to HA entities, overriding state/name/value/icon/color, internal items (skip, text, navigate, action), templating, and popup overrides.

## Example Configuration

See the [Panels Overview](panels/README.md) for available panel types and their options.

## Common Configuration

The following device-level settings control time and date formatting. Configuration is done through the Home Assistant UI panel editor.

| Option | Description |
|--------|-------------|
| `time_format` | Time format using Python `strftime` codes (e.g. `%H:%M`). See the [Python datetime docs](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes) for available codes. |
| `date_format` | Date format using Python `strftime` codes (e.g. `%A, %d. %B %Y`). |
| `date_format_locale` | CLDR locale format key (e.g. `full`, `long`, `medium`, `short`). Deprecated alias: `date_format_babel` (still supported for backward compatibility). |
