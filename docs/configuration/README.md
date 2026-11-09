---
title: Configuration Overview
description: How to configure NSPanel HAUI through the Home Assistant UI editor
---

# Configuration Overview

NSPanel HAUI is configured entirely through the **Home Assistant UI** — no YAML editing required. The configuration is organised into three areas:

1. **[Device Configuration](device.md)** — Device-level settings: name, locale, hardware buttons, timeouts, sounds, relays, and color overrides.
2. **[Panel Configuration](panels.md)** — How panels are configured: type, title, key, navigation, panel pin, and type-specific options.
3. **[Item Configuration](items.md)** — How items relate to HA entities: entity picker, state/name/value/icon/color overrides, internal items, and popup overrides.

## Finding the Editor

1. Open **NSPanel HAUI** in the Home Assistant sidebar (`/nspanel-haui`). The entry is visible to administrators only.
2. Select your device in the toolbar.
3. The panel list shows that device's panels. Here you can add (**Add Panel**), reorder, and delete panels.

### If the editor stays on its loading screen

The editor renders Home Assistant's own dialog and card elements (`<ha-dialog>`,
`<ha-dialog-footer>`, `<ha-card>`, `<ha-alert>`). Home Assistant loads those lazily — it
imports them together with its more-info dialog *after* its own first render — so right
after a page reload the editor can be ready before them. Rendering an undefined
`<ha-dialog>` would show its content inline without a modal, so the editor waits until the
elements are defined. This normally takes a second or two.

If the wait exceeds 10 seconds, the loading screen names the elements that are still
missing and offers two actions:

| Action | Effect |
|--------|--------|
| **Reload page** | Reloads the page so Home Assistant runs its startup sequence again. Try this first — it clears a slow or interrupted frontend start. |
| **Continue anyway** | Renders the editor with whatever elements exist. Dialogs then appear inline instead of as modals: enough to inspect or revert configuration, but not a normal working state. |

A message that never clears means the running Home Assistant frontend does not define one
of the listed elements. Use **Continue anyway** to reach your configuration, and report the
Home Assistant version in a GitHub issue.

## The Panel List

The panel list shows all panels configured for this device. It defaults to a
grid of cards, each with a preview of the panel's real display page — drawn by
the shared Nextion simulator in the device's orientation on top of the panel's
type, title, and key. Cards show the configured entities with their current
states (for example the clock and weather panels' weather icon and temperatures,
and the weather panel's forecast row, as their settings allow) and the selected
device's own details on the About
card (name, IP address, TFT and firmware versions). A compact **list** view is
available from the toolbar.
From this list you can:

- **Add** a new panel — choose a type from the dropdown
- **Edit** a panel — click the panel name to open the panel editor
- **Reorder** — drag panels to change their order
- **Delete** — remove a panel

## The Panel Editor

Clicking a panel opens the panel editor with these standard fields:

| Field | Description |
|-------|-------------|
| **Type** | The panel type (e.g. Clock, Grid, Light, Climate). Set when adding — cannot be changed. |
| **Title** | Display name shown in the panel header. On entity-based panel types, an available entity name takes precedence; otherwise the configured title is used, falling back to the translated panel-type default when empty. See [Panel Configuration](panels.md#standard-fields) for details. |
| **Key** | A unique identifier used to reference this panel in navigation and popups. |
| **Show in navigation** | Toggle to show/hide this panel in the navigation bar. |
| **Panel pin** | A numeric PIN — when set, the panel requires this code before access. |

Below the standard fields, each panel type shows its **type-specific options** in a collapsible **Configuration** section.

## The Item Editor

Each entity item in a panel has its own editor with:

- **Entity picker** — Search and select a Home Assistant entity
- **Advanced** section (collapsible) — Override the entity's name, value, icon, color, state, and popup behavior

See [Item Configuration](items.md) for full details on all override options.

## The Device Settings Dialog

Opened from the device toolbar. Fields are grouped into collapsible sections:

- **General Settings** — Locale, display model, auto dimming / auto page / auto display-off with their timeouts, debug level, item logging, stale-data indicator
- **Hardware Buttons** — Relay control, button entities, interaction reset
- **Display Buttons** — Home button, idle button, notifications button visibility
- **Gestures** — Named gesture sequences
- **Notifications** — Startup sound, notification sound, do not disturb, quiet hours
- **Idle & Wake Behavior** — Snapshot restore behavior and max age; auto-navigate home timeout
- **Time & Date** — Time and date formats
- **Panel Assignments** — Home panel, idle panel (carousel)

See [Device Configuration](device.md) for full details.

## The Colors Dialog

Opened from its own button (separate from Device Settings). Choose a built-in scheme (**Dark Color**, **Light Color**, **White** or **Black**) or a custom scheme, then **Apply scheme**. Built-in schemes are read-only; use **Save as** to create a custom scheme, and **Import**/**Export** to share the custom library. See [Color schemes](device.md#color-schemes).

## The Live Preview

Opened with the **Live preview** button (TV with a play symbol) in the device toolbar, or **Live preview** in the device actions menu. The preview has two separate sessions: **Simulated** runs a virtual copy of the device on the real hub code with its saved panels and settings and simulated entity states; **Live** mirrors the selected device's already-running hub app by following its display commands and status. Both use the display model's matching layout (landscape or portrait).

The bar above the screen switches the preview between **Simulated** (sandbox mode) and **Live**; a note above the bar says what the current mode does. The switch and that note turn orange in Live mode. The bar's **More tools** button (sliders icon) shows **Show entities**, which is hidden by default, and **Reset sandbox**; hiding the tools again switches **Show entities** off. The reset is disabled in Live mode. The **Idle timeout** button (zzz icon) sits in the bar.

- **Touch** — in Simulated mode, click or tap a widget, drag sliders and swipe from the screen edges with the mouse or a finger. The preview applies the panel's display scripts locally and sends resulting input to the virtual app.
- **Live mode** — supported component presses, swipes, hardware buttons and the **Idle** control are sent to the connected physical app. The simulator displays the commands that app emits through its normal ESPHome command path; it does not open a second copy of the physical page or simulate button effects. Slider thumbs track the pointer locally; slider handlers run on release. The physical app performs its normal Home Assistant service calls, so controls (including device settings) affect the real entities. Timed idle and home-page navigation follow the physical app, and page-change events keep the simulator on its current page. In relay mode, simulated hardware-button presses switch the panel's real ESPHome **Relay Left** / **Relay Right** switches. The **Reset interaction timer** action resets only the panel's inactivity timer (it is not a reboot or configuration reset). Switching Live mode on drops simulated states. Physical interactions are accepted only while the device is connected.
- **Show entities** — with this switch on, hovering the mouse over a tile, button or item shows the entity it is linked to (friendly name and entity id); on single-entity panels (light, cover, climate, …) the rest of the screen shows the panel's entity. The switch is available at every preview width.
- **Reset interaction timer** — in Live mode, resets the connected panel's inactivity timer to zero without changing its page, display configuration or firmware. Available only while the panel is connected.
- **Reset sandbox** — clears all simulated entity states so the preview shows the real Home Assistant states again. Available only in Simulated mode.
- **Hardware buttons** — the two buttons in the frame below the screen (**Left button**, **Right button**) send press/release input to the physical app in Live mode. In Simulated mode, a press toggles the configured relay or button entity in the sandbox. The light on each button shows its relay in blue; on a button that switches an entity instead, it shows that entity's state in yellow.
- **Idle timeout** (zzz icon) — in Live mode, opens the idle page on the physical device; in Simulated mode, switches the virtual app to the idle page. The button stays highlighted while the idle page is shown and returns to normal once a touch or button press leaves it.
- **Sandbox mode** (default) — every action changes only a simulated state, shown on the preview; your lights and switches are not touched. Use **Reset sandbox** in **More tools** to restore the real states without switching modes.


In Simulated mode the preview never fires `nspanel_haui.*` events, so automations reacting to the real panel do not see it, and it never checks for or installs firmware or TFT updates. It also mirrors the panel's notification queue read-only: queued notifications appear in the preview (a force-show one opens there too), and dismissing one in the preview leaves the panel's queue unchanged. A device has one virtual copy: Simulated previews opened in several browser tabs show the same screen and share its simulated states. Each tab has its own mode, so one tab can stay Simulated while another is Live. The preview uses the saved configuration and follows every save right away. Simulated and Live are independent: switching to Live drops the simulated states and always shows the device's actual current panel and display output; switching back to Simulated opens the virtual copy's home panel (leaving its idle page if it was shown) with the real entity states. Because the virtual copy is shared, other Simulated tabs of the device lose their simulated states and go home too.

The panel cards in the editor are drawn by the same virtual copy: each card shows its panel the way the hub draws it on the device — entity values, translations, templates, the clock, the weather forecast — including edits that are not saved yet. A popup's card shows it opened for a sample: an entity of its domain (one that is on, if there is one), an example notification or selection. Rendering a card never changes what an open preview shows.

The live preview and the Nextion simulator were created by
[@jameshiscott](https://github.com/jameshiscott).

## See Also

- [Panels Overview](../panels/README.md) — All panel types with descriptions
- [Examples](../examples.md) — Real-world configuration patterns
- [FAQ](../faq.md) — Common questions
