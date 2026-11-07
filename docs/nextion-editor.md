---
title: Nextion Editor (Human Guide)
description: How to change the Nextion HMI project by hand — widget, page, font, layout and US portrait TFT maintenance
---

# Nextion Editor — Human Guide

The display UI is a **Nextion Editor project** (`nextion/nspanel_haui.HMI`) and
the compiled firmware is the `.tft` files. Most of this repository's tooling
cannot produce those files for you: layout changes, new pages, new widgets and
the portrait variant for the US model are **human work in the Nextion Editor
application**. This document is the instruction sheet for that work and for
keeping the HMI in sync with the Python side of the integration.

It deliberately walks through everything a human has to know. For the
integration-side view (which commands the hub sends and how rendering works) see
[Nextion Component](nextion.md); for the hardware models see
[Display Models](configuration/display-models.md).

## 1. When you need this document

- Moving / resizing / recolouring an existing widget (quick fix).
- Adding a widget or a whole new page to the UI.
- Adding fonts or images (icons, backgrounds, spinners).
- Maintaining **both TFT layouts**: the standard landscape
  (`nspanel_haui.tft`, EU + US mounted landscape) and the rotated portrait
  (`nspanel_haui_portrait.tft`, US mounted portrait).
- Releasing a new version (both assets must ship together).

## 2. Prerequisites & tools

| Tool | Purpose |
|------|---------|
| **Nextion Editor** (official, free; Windows) | Edit `nspanel_haui.HMI`, compile to `.tft` |
| [**Nextion2Text**](https://github.com/joBr99/Nextion2Text) — local copy: `scripts/nextion2text/Nextion2Text.py` (see `scripts/nextion2text/README.md`) | Dump the HMI to readable text to verify IDs/names/coordinates |
| The repo's Python test stack | Verify the Python component registries still match |
| `scripts/nextion_vnc/nextion_vnc.sh` | Reach the editor on a Windows VM from a browser (noVNC) |

When the editor runs in a Windows VM, `scripts/nextion_vnc/nextion_vnc.sh`
bridges the VM's VNC server to a local noVNC page and prints its URL
(`http://127.0.0.1:6080/vnc.html?…`). The first run installs websockify and
noVNC under `build/novnc/`. The VM defaults to `192.168.65.2:5900`; set
`NEXTION_VNC_HOST`, `NEXTION_VNC_PORT` or `NOVNC_PORT` to change the VM or the
local port. The page listens on `127.0.0.1` only, and the VM's VNC password
still applies. Stop the bridge with `Ctrl+C`.

The HMI is a binary project file — open it in the Nextion Editor, never edit it
by hand. Choose the project variant matching the NSPanel's display
(480 × 320 landscape).

**Verification command for a landscape HMI:**

```bash
python scripts/nextion2text/Nextion2Text.py -i nextion/nspanel_haui.HMI \
  -o build/nextion-out/landscape -d -s -p visual
```

Use the matching `-i` for the portrait HMI (see
[§7 Creating the US portrait TFT](#7-creating-the-us-portrait-tft)) and a
different `-o` folder (e.g. `build/nextion-out/portrait`). `build/` is
git-ignored — safe to regenerate.



## 3. The sync contract between HMI and Python

The hub renders the display by name (`tHeader.txt="..."`) and maps touches by
**id + object name**. Every widget the Python side touches must exist in the
HMI with matching coordinates of truth:

| HMI side | Python side |
|----------|-------------|
| Widget **object name** on a page | `Component(id, "name")` entry in that page's `COMPONENTS` (`ComponentRegistry`) in `custom_components/nspanel_haui/haui/page/<page>.py` |
| Widget **id** (page-local, 1-based) | the `Component.id` int — must match exactly |
| Page **id** in the page properties | the page class `DESCRIPTOR.page_id`, mapped via `PAGE_MAPPING` (`haui/mapping/panel.py`) |
| Page **name** | the page class `DESCRIPTOR.page_name` and `PAGE_MAPPING` |

Example: if the HMI page `clock` has widget `tTime` with id `3`, Python has
`t_time=Component(3, "tTime")` and calls `self.set_component_text(self.COMPONENTS.t_time, ...)`.

### Hard rules

- **Every page must send `sendme` in its `Preinitialize` event.** The hub
  waits for the `esphome.page` event (the Nextion `sendme` postulate) before
  rendering; a page without it will never be rendered.
- **Prepare the page in `Preinitialize`** (hide unused widgets, set picture
  backgrounds, clear text). The hub cannot touch the display before the page
  is shown.
- **A solid-colour page paints itself in the theme in `Preinitialize`.** The
  hub sets the theme globals declared in `Program.s` (`thmBg`, `thmHdrBg`,
  `thmHdrTxt`, `thmPressed`, `thmCompBg`, defaults = the `COLORS` palette)
  before every page switch, and the page assigns them to its own `bco` and to
  every widget colour compiled with a theme colour. The code is generated from
  the page's widgets:

  ```bash
  python scripts/gen_virtual_layout/gen_virtual_layout.py --theme-code grid
  ```

  Paste it right after `sendme` in both HMIs, and paste it again whenever a
  widget compiled with a theme colour is added, removed or recoloured:
  `gen_virtual_layout.py --check` (run by the test suite) fails while a page's
  code is missing or stale.
- **Enable `Send Component ID`** on any touch event the hub needs to react
  to (buttons, sliders, keypad keys). Without it the hub receives no
  component event for the widget.
- **Component ids are page-local and change when you reorder widgets.**
  After reordering, re-dump the page and fix every affected `Component(id, …)`
  entry in Python.
- **Keep logic in the Hub App, not in HMI events.** Layout/visuals live in the
  HMI; behaviour (state reads, commands, navigation) lives in
  `haui/page/*.py`. HMI event code beyond `sendme` should be the exception.
- **Respect the visible area.** The landscape panel is 480 × 320 px but the
  bezel hides the rightmost 30 px — keep interactive/important content left of
  x = 450 (see [Nextion Component](nextion.md#nextion-display-configuration-used-in-this-project)).
- **Version text lives in the HMI too.** If a page (e.g. System/About) shows
  a version, keep it in sync with `custom_components/nspanel_haui/manifest.json`
  and `esphome/nspanel_haui/version.yaml` on release.

## 4. Typical workflow: change an existing widget

The most common human task — reposition, resize, recolour, or retitle a widget.
No Python changes are needed unless you also change the object name or id.

1. Open `nextion/nspanel_haui.HMI` in the Nextion Editor.
2. Open the page, select the widget (click on the canvas, or find it in the
   page's component list).
3. Edit its properties (x, y, w, h, font id, colours, `.txt` default, picture).
   - If the hub **writes** the value at runtime (text, font size, colors,
     pictures), the HMI values are only the *initial* look — the hub overrides
     them on every render. Don't be surprised that a changed default is
     overwritten.
   - If the hub sets colors from the HA palette, those come from
     `haui/mapping/color.py` `COLORS`, not from the HMI.
   - Geometry-only changes (position, size, slider cursor) are better kept in
     `scripts/gen_portrait/landscape_layout.py` and applied with
     `gen_portrait.py --spec landscape_layout` (project closed first, see
     [§7](#7-creating-the-us-portrait-tft)): the spec documents the layout
     rules and the same change then goes into `portrait_layout.py`.
4. Run the steps in [§8](#8-after-any-hmi-change-scripts-to-run): layout
   specs, compile, generated assets, an id/name check against Python, and the
   gates.
5. Test on the device: render the page, touch the widget, watch the hub log.

## 5. Add a widget or a whole page

### Adding one widget to an existing page

1. In the editor, add the widget on the page (e.g. a `text` for a new sensor
   readout, a `button` for a new action, a `gauge`/`slider` for a value).
2. Note its **object name** and **id**.
3. In `haui/page/<page>.py`, extend the registry if the page subclasses a base
   that already declares some entries:

   ```python
   class MyPage(SomeBasePage):
       COMPONENTS = SomeBasePage.COMPONENTS.merge(
           t_new_readout=Component(9, "tNewReadout"),
       )
   ```

   If the page's registry is standalone (like `CommonNotifyPage`), add the
   `Component(...)` line to its `ComponentRegistry(...)`.
4. Use the component: `self.set_component_text(self.COMPONENTS.t_new_readout, …)`
   or `self.on_release(self.COMPONENTS.btn_x, self.callback_x)` with a handler
   `def callback_x(self, event, component): …`.
5. If the widget shows user-facing text or a title attribute, run the
   translation extraction (`python scripts/translations/extract_translations.py`)
   after adding the `t()`/`self.translate()` call.
6. Re-dump + run `pytest tests/`, `ruff`, `mypy` (see [§8](#8-after-any-hmi-change-scripts-to-run)).

### Adding a new page

1. In the editor: add a page, give it a **unique page id** and a **page name**
   (e.g. `dehumidifier`).
2. In its `Preinitialize`, send `sendme` and prepare the page state; on a
   solid-colour page, paste its theme code after `sendme` (see the hard rules).
3. Add all widgets; enable `Send Component ID` on the interactive ones.
4. In Python, create `haui/page/dehumidifier.py` with a `HAUIPage` subclass,
   a `COMPONENTS` registry, and a `DESCRIPTOR` (unique `type_key`,
   `page_id`/`page_name` matching the editor, `label`/`description` via `_()`).
5. Register it in `haui/mapping/panel.py` (`_page_classes` list) — the
   registration logic itself is closed for modification.
6. Set `DESCRIPTOR.page_id` to the physical Nextion page — the editor's shared
   Nextion-simulator preview resolves it automatically. Document the panel in
   `docs/panels/panel_<key>.md` and run the checks.

## 6. Fonts and images

- **Icons are font glyphs.** The MDI icon set is baked into custom Nextion
  fonts in `nextion/fonts/` (`Roboto-Regular <size> (UTF_8).zi`, `Roboto-Light <size> (UTF_8).zi`), generated
  by the font scripts in `scripts/gen_fonts/` (see `scripts/gen_fonts/README.md`).
  The hub maps an icon
  name to its code point via `haui/mapping/icons.py` and writes the single
  glyph character into a text widget. You cannot add a new icon to the display
  without (a) generating an updated font `.zi`, (b) importing it into the HMI
  in the Nextion Editor, and (c) adding the name→glyph mapping to
  `haui/mapping/icons.py`.
- **Font sizes must exist per widget.** A text widget references one of the
  embedded fonts by id. When you change a widget's font in the editor, use a
  size that actually exists in the project's font list, and make sure the hub's
  `font=` override (e.g. the notify page's auto-sizing) picks a size the device
  has.
- **Pictures/backgrounds** live in `nextion/images/` (`bkg/`, `grid_landscape.png`,
  `grid_portrait.png`, …).
  Backgrounds are imported as picture resources; the hub sets `.pic`/`.picc`
  from `haui/mapping/`. Some pages (About, Clock, Clock Two, Weather) are
  **entirely picture-background based** — their look is the PNG, not widgets.
  The background tiles are generated: put the source picture in
  `nextion/src_images/bkg/`, named after its key in
  `haui/mapping/background.py` (`system` is the `modern` picture), and run
  `python scripts/gen_backgrounds/gen_backgrounds.py`. It writes the dimmed
  480 × 320 and 320 × 480 tiles to `nextion/images/bkg/landscape/` and
  `nextion/images/bkg/portrait/`. The two `grid_*.png` files are design-aid
  page backgrounds for the editor (margins, column and row guides, placeholder
  sizes, font samples, theme colors as RGB565); regenerate them with
  `python scripts/gen_grid/gen_grid.py`. The system page's spinner is two
  sprite sheets per orientation (`spinner_<orientation>_1.png` / `_2.png`,
  pictures 10 and 11) whose frames are drawn on the `system` tile cropped at
  the spinner's position; `python scripts/gen_spinner/gen_spinner.py`
  re-renders them, so run it after changing that tile or moving `hSpinner`.
- **RGB565 images** for ad-hoc assets can be converted with
  `scripts/gen_rgb565_image` / `scripts/rgb_conv`.

## 7. Creating the US portrait TFT

The **US model mounted portrait** needs a **rotated** layout: the same pages,
object names and ids as the landscape project, different geometry.
`scripts/gen_portrait/` keeps that geometry reproducible —
`portrait_layout.py` holds the 320 × 480 position of every widget and
`gen_portrait.py` writes it into the portrait HMI. The script also re-computes
the per-page content stamp the editor validates (a hand-edited page block
otherwise fails with "Version mismatch" / "Loading Page Failed"). The editor is
still needed to set the display direction, import pictures and compile; ship
the result alongside the landscape TFT on every release.

### 7.1 First creation (or a fresh re-rotation)

1. In the Nextion Editor, open `nextion/nspanel_haui.HMI`.
2. **Save a copy as its own project** before rotating anything:
   `File → Save As…` → `nextion/nspanel_haui_portrait.HMI`. Commit this file —
   it is the versioned source of the portrait asset (same as the landscape HMI
   is for `nspanel_haui.tft`).
3. In the editor's device settings, switch the display orientation of this
   copy to portrait (320 × 480), then apply the geometry from the repo —
   `gen_portrait.py` patches widget geometry only, not the orientation:

   ```bash
   python scripts/gen_portrait/gen_portrait.py --check   # spec vs. HMI widgets
   python scripts/gen_portrait/gen_portrait.py           # patch the portrait HMI in place
   ```

   The check fails when a widget exists on only one side, so a widget added
   to the landscape project needs its `PORTRAIT_LAYOUT` entry first. It now
   also verifies attribute values (alignment, font, …) against the spec, so a
   change to `PORTRAIT_ATTRS` cannot pass while the committed HMI still has
   the old value. Only x/y/w/h (plus the page size) and the spec's attribute
   overrides change; names, ids and `sendme` are untouched, and every widget's
   `Send Component ID` is copied from the landscape HMI (the spec's
   `SIBLING_HMI`) — toggle touch settings in the landscape project, then
   re-run the script. A `PORTRAIT_ATTRS` change must also be followed by a
   TFT recompile (step 4 below): the HMI change alone does not reach devices.
   The layout rules the spec follows:
   - The header bar (`tHeader`/`tTitle`) spans the full top 50 px with the
     four function buttons at its ends, as in landscape; the content area
     starts at y 50 with 12 px side margins.
   - Grids re-flow (grid 3 × 2 → 2 × 3, select 3 × 4 → 2 × 6), rows stack
     their controls under the name line, sliders grow taller, button rows
     keep their order.
   - Re-open the project and check every page in the editor; text that no
     longer fits its (narrower) widget needs the next font size down.
   - Icons/backgrounds: either rotate the `pic` resources in the editor or
     re-import pre-rotated PNGs from `nextion/images/` (the background tiles
     in `nextion/images/bkg/portrait/` are already 320 × 480).
   - Keep every widget's **object name identical** to the landscape page.
     Only the geometry may differ.
   - Keep `sendme` and `Send Component ID` settings identical.
   - **Ids may change** if reordering happened; if they do, update the Python
     `COMPONENTS` registries accordingly — the hub must address the portrait
     page with the same names/ids it addresses the landscape one (the page id
     and name are the same; only the TFT asset differs).
4. Compile (`Build`) → `nextion/nspanel_haui_portrait.tft`.
5. Re-dump the portrait HMI and diff the component names against the Python
   registries.
6. Nothing to mirror for the editor: the panel previews are rendered by the
   shared Nextion simulator from the generated layouts
   (`frontend/virtual/layout_<orientation>.json`, refreshed by
   `gen_virtual_layout.py`), so a portrait device automatically gets the
   portrait page. Re-check a preview with a portrait device selected.

### 7.2 Keeping both variants in sync

- The two HMIs are **siblings** — treat the portrait one as a *view* of the
  landscape one. When you add a widget/page in the landscape HMI, repeat the
  "add widget/page" steps in the portrait HMI (same name, id, sendme, touch
  settings; different geometry) and keep the page lists identical.
- **There is one definition of components.** The hub's Python `COMPONENTS`
  registries address both TFTs with the same names and ids, so *any* change
  applied to the landscape HMI — widgets, ids, attributes, event code, and
  geometry or slider tweaks in `scripts/gen_portrait/landscape_layout.py` —
  must be applied to the portrait HMI as well (and vice versa), with its
  geometry expressed in `portrait_layout.py`. Be extra careful here: a widget
  missing on one side only fails on the device. `gen_portrait.py --check` for
  both specs and `verify_nextion/verify_nextion.py --require-portrait` are the guard rails.
- Both `.tft` files must be attached to every GitHub release. The hub's update
  controller downloads `nspanel_haui.tft` for `display_model: eu` (the default
  landscape layout) and `nspanel_haui_portrait.tft` for `display_model: us`
  (see [Display Models](configuration/display-models.md)).

### 7.3 Portrait-specific caveats

- **Gesture edge detection is model-aware.** The ESPHome scripts
  (`esphome/nspanel_haui/scripts_interaction.yaml`) read the *Display Model*
  number the hub syncs on every connect: `0` uses the landscape 450×320 edge
  dimensions, `1` uses the portrait 320×480 ones. Edge swipes therefore behave
  the same in both layouts — no HMI change needed.
- Touch coordinates on the portrait device are **not** the same as landscape;
  the hub maps touches by page/component id + name, so as long as ids/names
  match, on-screen controls work — but verify every button manually on real
  hardware.
- Keep the release checklist honest: a release that ships only the landscape
  TFT will leave `display_model: us` devices on an old TFT (the update flow
  just finds no matching asset).

## 8. After any HMI change: scripts to run

Run these from the repository root with the dev venv active
(`source .venv/bin/activate`), in this order: the layout specs write the HMIs,
the editor compiles them, and everything after that is generated from the
HMIs. A step that has nothing to do reports so (`wrote 0 widgets`,
`already '…'`), so running the whole sequence is always safe.

1. **Close the project in the Nextion Editor** (`File → Close Project`; answer
   *Yes* to keep your editor work). The editor re-saves the open project on
   Close Project and on every project switch, which overwrites whatever a
   script wrote in the meantime.
2. **Write the layout specs into both HMIs.** Run landscape first, because the
   portrait run copies every widget's *Send Component ID* from the landscape
   HMI:

   ```bash
   python scripts/gen_portrait/gen_portrait.py --spec landscape_layout   # nspanel_haui.HMI
   python scripts/gen_portrait/gen_portrait.py                           # nspanel_haui_portrait.HMI
   ```

   A coverage error names a widget that exists in only one HMI, or a portrait
   widget that `portrait_layout.py` does not list. Add the widget to the other
   HMI in the editor and its rect to the spec, then run both again. A widget the
   spec lists is reset to the spec's geometry and attributes, so an editor
   change to such a widget must also go into `landscape_layout.py` /
   `portrait_layout.py` (see [§7.2](#72-keeping-both-variants-in-sync)).
3. **Set the TFT version (releases with new TFTs only).**
   `python scripts/bump_version.py X.Y.Z --tft-update` writes
   `system.tftVersion` into both HMIs. It handles same-length versions only;
   see [Release process](release.md#2-version-bump).
4. **Regenerate the editor pictures whose source changed**, then import them
   in the editor. A script cannot add or replace a picture in the HMI, so
   import the new PNG over the old picture in **both** projects, keeping the
   picture id.

   | Script | Writes | Run it after |
   |--------|--------|--------------|
   | `python scripts/gen_grid/gen_grid.py` | `nextion/images/grid_landscape.png`, `grid_portrait.png` (picture 0, the editor-only `pGrid` design grid) | a layout rule (margins, header, bars) or a theme colour changed |
   | `python scripts/gen_backgrounds/gen_backgrounds.py` | `nextion/images/bkg/landscape/`, `bkg/portrait/` | a source picture in `nextion/src_images/bkg/` changed |
   | `python scripts/gen_spinner/gen_spinner.py` | `nextion/images/spinner_<orientation>_1.png`, `_2.png` (pictures 10, 11) | the `system` tile changed or `hSpinner` moved |

5. **Re-open, check and compile both projects.** Open each project from the
   recent list; it must open without "Version mismatch". Look at every page you
   changed: text that no longer fits its widget needs the next font size down.
   Then click `Compile` and use `File → TFT file output` to write
   `nextion/nspanel_haui.tft` and `nextion/nspanel_haui_portrait.tft`. Compile
   both whenever step 2 or 3 wrote either HMI: an HMI change alone never
   reaches a device.
6. **Regenerate the hub and preview assets** from both HMIs:

   ```bash
   python scripts/gen_virtual_layout/gen_virtual_layout.py
   ```

   It writes the preview layouts (`frontend/virtual/layout_landscape.json`,
   `layout_portrait.json`), `icon_map.json`, the preview pictures
   (`frontend/virtual/pictures/`, WebP from `nextion/images/`), the font widths
   the hub fits text with (`haui/mapping/font_metrics.json`), and checks every
   solid-colour page's theme code (see the hard rules). The optional
   [pre-commit hook](development.md#git-hooks) runs it on every commit.
7. **Update Python when ids or names changed.** Dump both HMIs and compare
   each page with its `COMPONENTS` registry in `haui/page/*.py`:

   ```bash
   python scripts/nextion2text/Nextion2Text.py -i nextion/nspanel_haui.HMI -o build/nextion-out/landscape -d -s -p visual
   python scripts/nextion2text/Nextion2Text.py -i nextion/nspanel_haui_portrait.HMI -o build/nextion-out/portrait -d -s -p visual
   ```

   If the hub now sends different commands (new ids, other widgets), refresh
   the golden page commands with
   `PAGE_COMMANDS_REGEN=1 pytest tests/test_page_commands_golden.py` and
   review the diff. If you added user-facing strings, run
   `python scripts/translations/extract_translations.py`.
8. **Run the gates.** All must pass before you commit:

   ```bash
   python scripts/gen_portrait/gen_portrait.py --spec landscape_layout --check
   python scripts/gen_portrait/gen_portrait.py --check
   python scripts/verify_nextion/verify_nextion.py --require-portrait
   python scripts/gen_virtual_layout/gen_virtual_layout.py --check
   python scripts/check_preview_coverage.py
   pytest tests/
   node --test 'tests/frontend/*.test.mjs'
   ruff check custom_components/ scripts/
   mypy
   ```

   - `gen_portrait.py --check` compares widget coverage and every value in the
     spec with the HMI.
   - `verify_nextion.py` checks that `clock.tTime` sends its component id and
     that every widget's *Send Component ID* is identical in both HMIs. It also
     checks that `system.tftVersion` matches `manifest.json` and that the
     portrait HMI and TFT exist.
   - `pytest` replays a render of every panel in both layouts
     (`tests/test_card_renders.py`).
9. **Test on a device of each model.** Every page renders completely, every
   widget responds to touch, gestures behave (see
   [§7.3](#73-portrait-specific-caveats)), and the update flow installs the
   right TFT for `display_model: us`.

The docs' screen overview (`docs/assets/screens/`, `docs/screens.html`) is
regenerated by the `Screens` workflow after each development firmware build,
so don't commit it by hand. To see every card locally, run
`python scripts/preview_gallery/gen_preview_gallery.py --serve`. A release
ships both TFTs and both HMI sources together; the version places and gates are
in [Release process & strategy](release.md).
