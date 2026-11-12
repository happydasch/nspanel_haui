---
title: Themes
description: Choose and customize display colors and state-icon palettes for NSPanel HAUI devices
---

# Themes

A theme defines the display's semantic page colors and the weather, alarm and climate icon palettes. The four predefined themes are **Dark**, **Light**, **White** and **Black**. Custom themes are shared by all devices under the same hub entry.

On a device's **Preview**, select **Choose theme** below **Add panel** to open the Theme sidebar. The color swatches at the top show the current draft as you select and edit themes. Select a theme and press **Apply** to use it on that device; **Cancel** discards the draft.

The same selector is in the device settings sidebar: **Settings** on the device Preview opens **Device settings**, whose **Theme** section selects the device's theme and offers **New theme**, **Export all** and **Import**. A theme picked there is saved with the rest of the device settings; editing a theme's colors stays in the Theme sidebar.

## Predefined and custom themes

One **Color theme** dropdown lists every theme: the predefined ones under **Predefined themes** and your own under **Custom themes**. The swatches below it show the selected theme's colors. Editing a built-in theme's colors creates a custom copy automatically; use **New theme** to copy the current selection explicitly, or use **Duplicate** on a custom theme. A custom theme can be renamed, deleted, exported individually, or imported from a JSON file. **Export all** downloads the custom theme library.

A custom theme includes the semantic page colors and both dark- and light-background palettes for weather, alarm and climate icons. Editing a built-in theme never changes it; it creates a custom theme instead.

## Icon variant

**Default icon color variant** chooses which icon palette to use when the background is dark or light. It is a per-device setting, separate from the selected theme. Pages with a fixed picture background choose the matching palette for that background. **Edit icon colors for** selects which palette you are editing in a custom theme.

## Color editing

The **Theme colors** section edits the selected theme's semantic colors. Custom themes are shared by every device that selects them; changing a built-in theme's color creates a custom copy. The **Reset colors** button restores the selected theme's draft palette. Panel and item color settings remain explicit and can still take precedence; use the reset option in the sidebar if you want to clear those settings when applying the theme.

When panel and item colors exist, the **Reset existing panel and item color overrides when applying this theme** checkbox clears them along with the theme application. Panel and item color settings are separate from semantic theme colors.

The **Use color scheme** background option on Clock, ClockTwo and Weather panels uses a solid dark or light background chosen to match the theme. It does not add picture backgrounds to themes. See the [device configuration](device.md#background-pages) and the [panel guides](../panels/README.md).
