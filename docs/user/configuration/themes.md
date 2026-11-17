---
title: Themes
description: Choose and customize display colors and state-icon palettes for NSPanel HAUI devices
---

# Themes

A theme defines the display's semantic page colors and the weather, alarm and climate icon palettes. The predefined themes are the neutral **Dark**, **Light**, **White** and **Black** plus the colorful **Midnight**, **Ocean**, **Forest**, **Sunset**, **Violet** and **Sky**. All of them but **Sky** are dark-background themes; **Sky** is the light one, with a light blue page and a sky blue header. Custom themes are shared by all devices under the same hub entry.

The device's theme is chosen in **Device Settings → General**: the **Theme** field selects it, and the **Themes** button below the **Connection** and **Diagnostics** cards, which names the selected theme, opens the Theme sidebar, where the colors of the selected theme and the shared library are edited; the preview at the top shows the current draft as you edit and stays in view while you scroll through the colors, and **Apply** saves the sidebar changes while **Cancel** discards them. The theme choice itself is saved with the rest of the settings.

Choose **Themes** below the **Connection** and **Diagnostics** cards to edit the selected theme and its icon palettes.

## Predefined and custom themes

One **Color theme** picker shows every theme as a tile with a miniature panel in its colors: the predefined ones under **Predefined themes** and your own under **Custom themes**. The row of actions under it holds **New**, **Export** and **Import**, plus **Duplicate**, **Rename** and **Delete** icons when a custom theme is selected. Editing a built-in theme's colors creates a custom copy automatically; use **New** to copy the current selection explicitly, or use **Duplicate** on a custom theme. A custom theme can be renamed or deleted. **Export** downloads the currently selected theme, including predefined themes and the current edited colors and icon palettes; **Import** adds themes from a JSON file.

A custom theme includes the semantic page colors and both dark- and light-background palettes for weather, alarm and climate icons. Editing a built-in theme never changes it; it creates a custom theme instead.


## Per-panel theme

A panel can select its own **Color theme** in the editor's **Advanced** section. By default, it follows the device theme. This applies to user panels and editable popups; a popup uses its own theme when opened over another panel. The panel's theme controls its page, items and icons. Item and panel color fields remain explicit overrides and take precedence.

## Icon colors

A theme carries the weather, alarm and climate icon colors for both a dark and a light background. Which of the two the display draws follows the theme itself: a theme with a dark page background uses the dark-background palette, a light theme such as **Light**, **White** or **Sky** the light-background one. There is no separate setting, so a theme's page and its icons always match. Pages with a fixed picture background choose the matching palette for that background instead. The Theme sidebar's **Icon colors** section shows the palette the theme draws, so you edit the colors the display actually uses.

## Color editing

The **Theme colors** section edits the selected theme's semantic colors. Custom themes are shared by every device that selects them; changing a built-in theme's color creates a custom copy. **Reset theme** restores the selected theme's complete saved palette, including semantic and icon colors. A changed color row has its own **Revert to theme color** action, which restores only that value. Applying a theme leaves panel and item color settings untouched; those overrides can still take precedence over theme colors.

The **Use color scheme** background option on Clock, ClockTwo and Weather panels uses a solid dark or light background chosen to match the theme. It does not add picture backgrounds to themes. See the [device configuration](device.md#background-pages) and the [panel guides](../panels/README.md).
