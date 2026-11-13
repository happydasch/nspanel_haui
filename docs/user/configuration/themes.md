---
title: Themes
description: Choose and customize display colors and state-icon palettes for NSPanel HAUI devices
---

# Themes

A theme defines the display's semantic page colors and the weather, alarm and climate icon palettes. The four predefined themes are **Dark**, **Light**, **White** and **Black**. Custom themes are shared by all devices under the same hub entry.

In the device's **Preview** view, the **Manage this device** card has three buttons in one row: **Theme**, **Schedule** and **Gestures**. Each opens its editor in a sidebar: **Theme** the Theme sidebar, **Schedule** and **Gestures** their own, which keep their explicit **Save** action. In the Theme sidebar the **Color theme** picker selects the device's theme (saved immediately) and shows the selected palette's colors in the field; it shows the current draft as you edit, and **Apply** saves the sidebar changes while **Cancel** discards them.

Choose **Theme** to select a device's theme and to edit the shared theme library and icon palettes.

## Predefined and custom themes

One **Color theme** picker lists every theme: the predefined ones under **Predefined themes** and your own under **Custom themes**. Its palette chip shows the selected theme's colors, and the row of actions under it holds **New**, **Export** and **Import**, plus **Duplicate**, **Rename** and **Delete** icons when a custom theme is selected. Editing a built-in theme's colors creates a custom copy automatically; use **New** to copy the current selection explicitly, or use **Duplicate** on a custom theme. A custom theme can be renamed or deleted. **Export** downloads the currently selected theme, including predefined themes and the current edited colors and icon palettes; **Import** adds themes from a JSON file.

A custom theme includes the semantic page colors and both dark- and light-background palettes for weather, alarm and climate icons. Editing a built-in theme never changes it; it creates a custom theme instead.


## Per-panel theme

A panel can select its own **Color theme** in the editor's **Advanced** section. By default, it follows the device theme. This applies to user panels and editable popups; a popup uses its own theme when opened over another panel. The panel's theme controls its page, items and icons. Item and panel color fields remain explicit overrides and take precedence. The device's **Default icon color variant** remains in effect for every panel.
## Icon variant

**Default icon color variant** chooses which icon palette to use when the background is dark or light. It is a per-device setting, separate from the selected theme. Pages with a fixed picture background choose the matching palette for that background. **Edit icon colors for** selects which palette you are editing in a custom theme.

## Color editing

The **Theme colors** section edits the selected theme's semantic colors. Custom themes are shared by every device that selects them; changing a built-in theme's color creates a custom copy. **Reset theme** restores the selected theme's complete saved palette, including semantic and icon colors. A changed color row has its own **Revert to theme color** action, which restores only that value. Applying a theme leaves panel and item color settings untouched; those overrides can still take precedence over theme colors.

The **Use color scheme** background option on Clock, ClockTwo and Weather panels uses a solid dark or light background chosen to match the theme. It does not add picture backgrounds to themes. See the [device configuration](device.md#background-pages) and the [panel guides](../panels/README.md).
