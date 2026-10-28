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
4. Compile (`Build`) to regenerate the TFT you're testing.
5. Re-dump with Nextion2Text and confirm the widget's id/name are unchanged
   (or update Python if they are).
6. Test on the device: render the page, touch the widget, watch the hub log.

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
6. Re-dump + run `pytest tests/`, `ruff`, `mypy` (see [§8](#8-verification-checklist-after-any-hmi-change)).

### Adding a new page

1. In the editor: add a page, give it a **unique page id** and a **page name**
   (e.g. `dehumidifier`).
2. In its `Preinitialize`, send `sendme` and prepare the page state.
3. Add all widgets; enable `Send Component ID` on the interactive ones.
4. In Python, create `haui/page/dehumidifier.py` with a `HAUIPage` subclass,
   a `COMPONENTS` registry, and a `DESCRIPTOR` (unique `type_key`,
   `page_id`/`page_name` matching the editor, `label`/`description` via `_()`).
5. Register it in `haui/mapping/panel.py` (`_page_classes` list) — the
   registration logic itself is closed for modification.
6. Add a preview renderer (`scripts/gen_preview/gen_preview.py --type <key>`),
   document the panel in `docs/panels/panel_<key>.md`, and run the checks.

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
   - The header bar (`tHeader`/`tTitle`) spans the full top 50 px; the four
     function buttons move to a bottom bar at y 430..480, so the content area
     is y 50..430 with 12 px side margins.
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
6. Mirror the portrait widget geometry into the editor's panel previews, or
   a portrait device keeps showing landscape placement. The previews follow
   the device's `display_model`: `frontend/previews/registry.js` stamps
   `portrait` on every preview result, `frontend/panel-card.js` then draws
   the 320 × 480 frame with the function buttons in a bottom bar, and the
   orientation-specific rules live under `.pg-card-preview--portrait` in
   `frontend/styles/preview/*.js` (a renderer can also branch on
   `isPortraitDevice(host)` from `frontend/previews/utils.js`, as the word
   clock does). Re-check each preview with a portrait device selected.

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

## 8. Verification checklist (after any HMI change)

1. Re-dump both HMIs:

   ```bash
   python scripts/nextion2text/Nextion2Text.py -i nextion/nspanel_haui.HMI -o build/nextion-out/landscape -d -s -p visual
   python scripts/nextion2text/Nextion2Text.py -i nextion/nspanel_haui_portrait.HMI -o build/nextion-out/portrait -d -s -p visual
   ```

2. Cross-check widget names/ids against `haui/page/*.py` `COMPONENTS`
   registries page by page.
3. Full checks: `pytest tests/`, `ruff check custom_components/ scripts/`, `mypy`,
   and if you touched `frontend/`, `node --test 'tests/frontend/*.test.mjs'`.
4. If you added user-facing strings: `python scripts/translations/extract_translations.py`.
5. Automatic release gate: `python scripts/verify_nextion/verify_nextion.py --require-portrait`
   fails the release until (a) `clock.tTime` has **Send Component ID** enabled,
   (b) `system.tftVersion` matches `manifest.json`, and (c) the portrait
   HMI/TFT exist.  Run it locally after every HMI edit; the release workflow
   runs it too.  For a release, set the version first with
   `python scripts/bump_version.py X.Y.Z` — it edits the HMI `tftVersion`
   text directly (same-length versions only) so you do not have to type it in
   the Nextion Editor.  A length-changing version still needs the Editor.
6. On-device test per model: page renders completely, all widgets hit-test
   correctly, gestures behave (see §7.3 for portrait), auto-update installs the
   right TFT for `display_model: us`.
7. Release: attach **both** TFTs (+ both HMI sources) and keep
   `manifest.json` / `version.yaml` / HMI version text in lockstep.
