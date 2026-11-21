---
title: Editing the HMI
description: Working in the Nextion Editor on both HMI projects and keeping them in step with the Python pages
---

# Editing the HMI

The display UI is a Nextion Editor project — `nextion/nspanel_haui.HMI` and its portrait sibling `nextion/nspanel_haui_portrait.HMI` — compiled to `nspanel_haui.tft` and `nspanel_haui_portrait.tft`. Layout changes, new widgets, new pages and the portrait variant are hand work in that application; this page is the procedure and the contract that keeps the HMI and the Python pages in step. The hub side of the same cycle is [Nextion component](nextion.md).

## When you need this page

- Moving, resizing, recolouring or retitling a widget.
- Adding a widget or a whole page.
- Adding fonts or images: icons, backgrounds, the spinner.
- Maintaining both TFT layouts: landscape (EU and US mounted landscape) and rotated portrait (US mounted portrait). A release ships both assets together.
- Releasing a version with new TFTs: both `.tft` files and both `.HMI` sources go in the same release ([release process](release.md)).
- Debugging a page that renders nothing, ignores touches or shows stale content: [when something does not work](#when-something-does-not-work).

## Tools and prerequisites

| Tool | Purpose |
|------|---------|
| **Nextion Editor** (official, free, Windows) | Edit an `.HMI` and compile the `.tft` |
| [Nextion2Text](https://github.com/joBr99/Nextion2Text) — local copy `scripts/nextion2text/Nextion2Text.py` | Dump an HMI to readable text to check ids, names and coordinates |
| The repository's Python environment | Regenerate the layouts and run the gates |
| `scripts/nextion_vnc/nextion_vnc.sh` | Reach the editor on a Windows VM from a browser through noVNC |

When the editor runs in a Windows VM, `scripts/nextion_vnc/nextion_vnc.sh` bridges the VM's VNC server to a noVNC page and prints its URL (`http://127.0.0.1:6080/vnc.html?…`). The first run installs websockify and noVNC under `build/novnc/`. The VM defaults to `192.168.65.2:5900`; set `NEXTION_VNC_HOST`, `NEXTION_VNC_PORT` or `NOVNC_PORT` to change the VM or the local port. The page listens on `127.0.0.1` only and the VM's VNC password still applies; stop the bridge with `Ctrl+C`.

Dump either project before you map widgets, and again whenever ids may have moved:

```bash
python -m scripts.nextion2text.Nextion2Text -i nextion/nspanel_haui.HMI -o build/nextion-out/landscape -d -s -p visual
python -m scripts.nextion2text.Nextion2Text -i nextion/nspanel_haui_portrait.HMI -o build/nextion-out/portrait -d -s -p visual
```

`build/` is git-ignored. `-o` names the folder (one `.txt` per page), `-d` clears it first so stale files cannot linger, `-s` writes a stats summary and `-p visual` adds position, size and colours. An HMI is a binary project file: open it in the Nextion Editor, and let the scripts patch only what the [HMI↔Python contract](#the-hmipython-contract) and [After any HMI change](#after-any-hmi-change) describe.

## The HMI↔Python contract

The hub renders by object name (`tHeader.txt="…"`) and maps touches by id plus object name, so every widget the Python side touches must exist in the HMI with the same id and name.

| HMI side | Python side |
|----------|-------------|
| Widget object name on a page | `Component(id, "name")` entry in that page's `COMPONENTS` registry, `custom_components/nspanel_haui/haui/page/<page>.py` |
| Widget id (page-local, 1-based) | the `Component.id` int — must match exactly |
| Page id in the page properties | `DESCRIPTOR.page_id`, collected into `PAGE_MAPPING` by `haui/mapping/panel.py` |
| Page name | `DESCRIPTOR.page_name` |

If the HMI page `clock` has widget `tTime` with id `3`, Python has `t_time=Component(3, "tTime")` and calls `self.set_component_text(self.COMPONENTS.t_time, ...)`.

### What lives where

| File | Holds |
|------|-------|
| `nextion/nspanel_haui.HMI`, `nextion/nspanel_haui_portrait.HMI` | the layout and the page-scoped event code that must run on the display; `Program.s` declares the theme globals; `system.tftVersion` carries the TFT version |
| `scripts/hmi_layout/landscape_layout.py`, `portrait_layout.py` | the widget geometry and attribute overrides `gen_layout.py` writes |
| `scripts/hmi_layout/theme.py` | the theme colours compiled into solid widgets on both TFTs |
| `custom_components/nspanel_haui/haui/page/*.py` | behaviour: `COMPONENTS`, `DESCRIPTOR`, render and touch handlers |
| `custom_components/nspanel_haui/haui/mapping/panel.py` | `_page_classes`, and the `PAGE_MAPPING` derived from each `DESCRIPTOR.page_id` |

### Hard rules

- **Every page sends `sendme` in its `Preinitialize` event.** The hub waits for the `esphome.page` event before rendering; a page without it is never rendered.
- **Prepare the page in `Preinitialize`**: hide unused widgets, set picture backgrounds, clear text. The hub cannot touch the display before the page is shown.
- **A solid-colour page paints itself in the theme in `Preinitialize`.** The hub writes the theme globals declared in `Program.s` (`thmBg`, `thmHdrBg`, `thmHdrTxt`, `thmPressed`, `thmCompBg`; defaults = the `COLORS` palette) before every page switch, and the page assigns them to its own `bco` and to every widget colour compiled with a theme colour. Generate the code from the page's widgets and paste it right after `sendme` in both HMIs:

  ```bash
  python -m scripts.hmi_layout.gen_virtual_layout --theme-code grid
  ```

  Paste it again whenever a widget compiled with a theme colour is added, removed or recoloured. `gen_virtual_layout --check`, run by the test suite, fails while a page's code is missing or stale.
- **Enable `Send Component ID`** on every touch event the hub must react to (buttons, sliders, keypad keys). Without it the hub receives no component event.
- **Toggle `sendkey` in the landscape project only.** The portrait run copies every widget's `Send Component ID` from `SIBLING_HMI`, so a touch setting changed only in the portrait HMI is overwritten by the next `gen_layout --spec portrait`.
- **Component ids are page-local and change when you reorder widgets.** Re-dump the page and fix every affected `Component(id, …)`.
- **Keep behaviour in the hub.** Layout and visuals live in the HMI; state reads, commands and navigation live in `haui/page/*.py`. HMI event code beyond `sendme` is the exception.
- **Both HMIs carry the same widgets.** Same names, ids, order and event code in both projects: a widget present in one HMI only breaks that TFT silently at runtime, and `make hmi-check` is what proves the parity.
- **Respect the visible area.** Landscape is 480 × 320 px but the bezel hides the rightmost 30 px: keep interactive content left of x 450 ([dimensions](nextion.md#dimensions-and-non-visible-area)).
- **The TFT version lives in the HMI too.** `system.tftVersion` in both HMIs must equal `tft_version` in `esphome/nspanel_haui/version.yaml` — the TFT version can differ from the firmware version — and `python -m scripts.bump_tft_version` writes it.

## Changing an existing widget

Repositioning, resizing, recolouring or retitling a widget needs no Python change unless the object name or id moves too.

1. Open `nextion/nspanel_haui.HMI` in the Nextion Editor and select the widget on the page or in the component list.
2. Edit its properties: `x`, `y`, `w`, `h`, font id, colours, `.txt` default, picture.
3. Check whether the hub overwrites the value at render time (text, font size, colours, pictures). If it does, the HMI value is the initial look only, and colours the hub takes from the Home Assistant palette come from `COLORS` in `haui/mapping/color.py`, not from the HMI.
4. Put a geometry-only change in `scripts/hmi_layout/landscape_layout.py` and let `gen_layout.py` write it, then mirror it in `portrait_layout.py`. Close the project first: the editor overwrites whatever a script wrote when it saves.
5. Repeat the change in `nextion/nspanel_haui_portrait.HMI`.
6. Run [After any HMI change](#after-any-hmi-change), then test on a device: render the page, touch the widget, watch the hub log.
7. Check the render before flashing: `pytest tests/test_card_renders.py` replays the hub's render of every panel in the simulator, and the gallery shows the same cards (`python -m scripts.preview_gallery.gen_preview_gallery --serve`).

## Adding a widget or a page

### One widget on an existing page

1. Add the widget in the editor: a `text` for a sensor readout, a `button` for an action, a `gauge` or `slider` for a value.
2. Note its object name and id, and enable `Send Component ID` if the hub must react to it.
3. Extend the page's registry. A subclass merges into its base; a standalone registry (like `CommonNotifyPage`) takes a plain `Component(...)` line:

   ```python
   class MyPage(SomeBasePage):
       COMPONENTS = SomeBasePage.COMPONENTS.merge(
           t_new_readout=Component(9, "tNewReadout"),
       )
   ```

4. Use it: `self.set_component_text(self.COMPONENTS.t_new_readout, …)`, or `self.on_release(self.COMPONENTS.btn_x, self.callback_x)` with a handler `def callback_x(self, event, component): …`.
5. Run `python -m scripts.translations.extract_translations` after adding a `t()` or `self.translate()` call.
6. Repeat in the portrait HMI, then run [After any HMI change](#after-any-hmi-change).

### A new page

1. Add the page in the editor with a unique page id and a page name (for example `dehumidifier`).
2. In its `Preinitialize`, send `sendme` and prepare the page state; on a solid-colour page, paste its theme code after `sendme`.
3. Add all widgets and enable `Send Component ID` on the interactive ones.
4. Create `custom_components/nspanel_haui/haui/page/dehumidifier.py` with a `HAUIPage` subclass, a `COMPONENTS` registry and a `DESCRIPTOR` — unique `type_key`, `page_id` and `page_name` matching the editor, `label` and `description` through `_()` ([what the page class needs](design.md#what-the-page-class-needs)).
5. Register it in `_page_classes` in `haui/mapping/panel.py`, add the page's widget rects to both layout specs and mirror the page in the portrait HMI.
6. Document it in `docs/user/panels/panel_<key>.md` and run the checks.

## Fonts and images

- **Icons are font glyphs.** The MDI set is baked into the Nextion fonts in `nextion/fonts/` (`Roboto-Regular <size> (UTF_8).zi`, `Roboto-Light <size> (UTF_8).zi`), generated by `scripts/font_tools/Generate-HASP-Fonts.ps1` (Windows, `ZiLib.dll`; see `scripts/font_tools/README.md`). The hub maps a name to a code point in `haui/utils/icon.py` and writes the single glyph into a text widget, so a new icon needs the regenerated `.zi`, its import into both projects and [the name in the Python mapping](design.md#icons).
- **A widget's font must exist in the project.** A text widget references an embedded font by id; use one of the eight sizes, and make sure a hub `font=` override (the notify page's auto-sizing uses ids 3, 2 and 1) stays a size the device has.
- **The character set the fonts cover** is the unicode range list in `scripts/charset/gen_char.py`; a character outside it has no glyph, and `has_glyphs` reports it as missing.
- **Pictures live in `nextion/images/`** (`bkg/`, `grid_landscape.png`, `grid_portrait.png`, the spinner sheets). Backgrounds are imported as picture resources and the hub picks them from `haui/mapping/background.py` before a page switch. About, Clock, Clock Two, Weather and System are entirely picture-based: their look is the PNG, not widgets.
- **Background tiles are generated.** Put the source picture in `nextion/src_images/bkg/`, named after its key in `haui/mapping/background.py` (`system` is the `modern` picture), and run `python -m scripts.backgrounds.gen_backgrounds`: it writes the dimmed 480 × 320 and 320 × 480 tiles to `nextion/images/bkg/landscape/` and `bkg/portrait/`.
- **The icon cheatsheet is generated too.** `python -m scripts.font_tools.gen_cheatsheet` writes `docs/cheatsheet.html`; `make generated-check` fails while it is stale.
- **The design grid is editor-only.** `python -m scripts.design_grid.gen_grid` writes `grid_landscape.png` and `grid_portrait.png` (picture 0, `pGrid`) with margins, column and row guides, placeholder sizes, font samples and the theme colours as RGB565.
- **The spinner is two sprite sheets per orientation** (`spinner_<orientation>_1.png`, `_2.png`, pictures 11 and 12), drawn on the `system` tile cropped at the spinner's position. `python -m scripts.spinner.gen_spinner` re-renders them after a tile change or a move of `hSpinner`. The `tmSpinner` timer's `xpic` calls name both sheets by picture id and the editor does not renumber event code, so update those ids in both projects when you insert a picture before them; `gen_virtual_layout --check` fails while they point at other pictures.
- **Ad-hoc images** convert with `scripts/rgb565_image/` and `scripts/rgb_conversion/`.

### Adding or replacing a picture

1. Start from a source picture in `nextion/src_images/bkg/` and let `gen_backgrounds` render it (above); never edit a generated tile in `nextion/images/bkg/`.
2. Import the PNG in the landscape project as a picture resource, then in the portrait project with the same picture id. A script cannot add or replace a picture in an HMI.
3. Give it its contrast variant in `BACKGROUND_VARIANTS` (`haui/mapping/background.py`): the variant drives text, cycle cards and state icons together, and a picture without an entry falls back to the panel's theme fill ([themes and colours](design.md#backgrounds-and-contrast)).
4. Run [After any HMI change](#after-any-hmi-change). `gen_virtual_layout --check` fails while the preview pictures are stale, and `tests/test_docs_images.py` fails while a docs page references a picture the repository does not contain.

## The portrait variant

The US model mounted portrait needs a rotated layout: the same pages, object names and ids as the landscape project with different geometry. Both `.HMI` files are committed sources and both `.tft` files are build outputs of the editor. `scripts/hmi_layout/portrait_layout.py` is the single source of truth for that geometry (`PORTRAIT_LAYOUT` for the rects, `PORTRAIT_ATTRS` for attributes) and `python -m scripts.hmi_layout.gen_layout --spec portrait` writes it into the portrait HMI. The script also recomputes the per-page content stamp the editor validates, so a patched page does not open with "Version mismatch" / "Loading Page Failed". The editor is still needed for the display direction, picture import and compiling.

### First creation

1. Open `nextion/nspanel_haui.HMI` and use `File → Save As…` to create `nextion/nspanel_haui_portrait.HMI` before rotating anything. Commit it: it is the versioned source of the portrait asset.
2. In the copy's device settings, switch the display orientation to portrait (320 × 480). `gen_layout.py` patches widget geometry only, never the orientation.
3. Write the geometry from the spec and check it:

   ```bash
   python -m scripts.hmi_layout.gen_layout --spec portrait --check  # spec vs. HMI widgets
   python -m scripts.hmi_layout.gen_layout --spec portrait          # patch the portrait HMI
   ```

   The check fails when a widget exists on only one side, and it verifies every attribute value (alignment, font, …) against the spec, so a change to `PORTRAIT_ATTRS` cannot pass while the committed HMI holds the old value. Only `x`, `y`, `w`, `h`, the page size and the spec's attribute overrides change; names, ids and `sendme` stay, and every widget's `Send Component ID` is copied from the landscape HMI (`SIBLING_HMI`) — toggle touch settings in the landscape project and re-run the script. A `PORTRAIT_ATTRS` change only reaches devices through a TFT recompile.
4. Check every page in the editor: text that does not fit its narrower widget needs the next font size down. Icons and backgrounds are either rotated as `pic` resources in the editor or re-imported pre-rotated from `nextion/images/` (`nextion/images/bkg/portrait/` is already 320 × 480).
5. `Compile`, then `File → TFT file output` to `nextion/nspanel_haui_portrait.tft`.
6. Re-dump the portrait HMI and diff the widget names and ids against the Python registries.
7. Nothing to mirror for the editor: the panel previews come from the generated layouts (`frontend/virtual/layout_<orientation>.json`), so a portrait device gets the portrait page once `gen_virtual_layout` has run. Re-check a preview with a portrait device selected.

The portrait spec follows these layout rules:

- `tHeader` and `tTitle` span the top 50 px with the four function buttons at its ends; content starts at y 50 with 12 px side margins (x 12..308).
- Grids re-flow (grid 3 × 2 → 2 × 3, select 3 × 4 → 2 × 6), rows stack their controls under the name line, sliders grow taller, button rows keep their order.
- Every widget keeps its landscape object name and its `sendme` / `Send Component ID` setting; only geometry and the spec's attribute overrides differ.
- Page ids and page names are the same in both projects; only the TFT asset differs.

### Keeping both variants in sync

- Treat the portrait HMI as a view of the landscape one: any change to the landscape HMI — widgets, ids, attributes, event code, geometry in `landscape_layout.py` — needs its counterpart in the portrait HMI and `portrait_layout.py`, and the other way round. A widget missing on one side only fails on the device.
- `gen_layout.py --check` verifies landscape; `gen_layout.py --spec portrait --check` verifies portrait and enforces sibling parity, meaning the same widgets with an identical `Send Component ID`.
- There is one definition of components: the `COMPONENTS` registries address both TFTs with the same names and ids.
- Both `.tft` files ship on every release. The update controller downloads `nspanel_haui.tft` for `display_model: eu` and `nspanel_haui_portrait.tft` for `display_model: us` ([Display Models](../user/editor/display-models.md)).

### Portrait caveats

- Gesture edge detection is model-aware: the ESPHome scripts read the *Display Model* select the hub syncs on connect — **Landscape** uses the landscape 450 × 320 edge dimensions, **Portrait** the portrait 320 × 480 ones — so no HMI change is needed.
- Touch coordinates differ from landscape, but the hub maps touches by page, component id and name, so matching ids and names make the controls work. Verify every button on real hardware.
- A release that ships only the landscape TFT leaves `display_model: us` devices on an old one: the update flow finds no matching asset.

## After any HMI change

Run these from the repository root with `source .venv/bin/activate`, in this order: the layout specs write the HMIs, the editor compiles them, everything after that is generated from the HMIs. A step with nothing to do reports so (`wrote 0 widgets`, `already '…'`), so the whole sequence is safe to run.

1. **Close the project in the Nextion Editor** (`File → Close Project`, answering *Yes* to keep your work). The editor re-saves the open project on close and on every project switch, overwriting whatever a script wrote.
2. **Write the layout specs into both HMIs**, landscape first because the portrait run copies each widget's `Send Component ID` from it:

   ```bash
   python -m scripts.hmi_layout.gen_layout                           # nspanel_haui.HMI (landscape default)
   python -m scripts.hmi_layout.gen_layout --spec portrait           # nspanel_haui_portrait.HMI
   ```

   A coverage error names a widget that exists in only one HMI, or a portrait widget `portrait_layout.py` does not list: add the widget in the other project and its rect to the spec, then run both again. A widget the spec lists is reset to the spec's geometry and attributes, so an editor change to one must also go into `landscape_layout.py` or `portrait_layout.py`.
3. **Set the TFT version, releases with new TFTs only.** `python -m scripts.bump_version X.Y.Z --tft-update` writes `system.tftVersion` into both HMIs; it handles same-length versions only ([release process](release.md)).
4. **Regenerate the pictures whose source changed**, then import them in the editor. A script cannot add or replace a picture in an HMI, so import the new PNG over the old one in **both** projects, keeping the picture id.

   | Script | Writes | Run it after |
   |--------|--------|--------------|
   | `python -m scripts.design_grid.gen_grid` | `nextion/images/grid_landscape.png`, `grid_portrait.png` (picture 0, `pGrid`) | a layout rule (margins, header, bars) or a theme colour changed |
   | `python -m scripts.backgrounds.gen_backgrounds` | `nextion/images/bkg/landscape/`, `bkg/portrait/` | a source picture in `nextion/src_images/bkg/` changed |
   | `python -m scripts.spinner.gen_spinner` | `nextion/images/spinner_<orientation>_1.png`, `_2.png` (pictures 11 and 12) | the `system` tile changed or `hSpinner` moved |

5. **Re-open, check and compile both projects.** Each must open without "Version mismatch". Compile and write `nextion/nspanel_haui.tft` and `nextion/nspanel_haui_portrait.tft` whenever step 2 or 3 wrote either HMI: an HMI change alone never reaches a device.
6. **Regenerate the hub and preview assets** from both HMIs:

   ```bash
   python -m scripts.hmi_layout.gen_virtual_layout
   ```

   It writes `frontend/virtual/layout_landscape.json`, `layout_portrait.json`, `icon_map.json`, the preview pictures (WebP) and the font widths the hub fits text with (`haui/mapping/font_metrics.json`), and verifies every solid page's theme code. The optional [pre-commit hook](development.md) runs it on every commit.
7. **Update Python when ids or names changed.** Compare each page of the dumps from [Tools and prerequisites](#tools-and-prerequisites) with its `COMPONENTS` registry. If the hub now sends different commands, refresh the golden page commands with `PAGE_COMMANDS_REGEN=1 pytest tests/test_page_commands_golden.py` and review the diff; run `python -m scripts.translations.extract_translations` for new user-facing strings.
8. **Run the gates.** All must pass before you commit:

   ```bash
   python -m scripts.hmi_layout.gen_layout --check
   python -m scripts.hmi_layout.gen_layout --spec portrait --check
   python -m scripts.hmi_layout.gen_virtual_layout --check
   python -m scripts.check_preview_coverage
   pytest tests/
   node --test 'tests/frontend/*.test.mjs'
   ruff check custom_components/ scripts/
   mypy
   ```

   `pytest` checks that `system.tftVersion` in both HMIs matches `tft_version` in `esphome/nspanel_haui/version.yaml`, that both compiled TFTs carry it (`tests/test_bump_version.py`), and replays a render of every panel in both layouts (`tests/test_card_renders.py`). `gen_layout --check` also verifies that `clock.tTime` sends its component id. `make hmi-check` runs the layout, generated-asset and coverage guards alone.
9. **Test on a device of each model.** Every page renders completely, every widget responds to touch, gestures behave, and the update flow installs the right TFT for `display_model: us`.

The pre-commit hook regenerates the virtual layouts and stages them, then checks both layout specs, so a committed HMI never reaches `dev` without its regenerated layout.

### When something does not work

| Symptom | Cause |
|---------|-------|
| The editor refuses to open a project: "Version mismatch" / "Loading Page Failed" | The page block's content stamp is stale — a script wrote the block without re-stamping it, or the editor saved over a script's write. Close the project, re-run `gen_layout` for that spec, reopen |
| The hub log shows "Invalid variable name" (0x1A) | Render commands arrived before the page's `sendme` was acknowledged. Check the page's `Preinitialize` |
| A page shows the previous panel's content | The page sends no `sendme`, so the hub never renders it |
| A widget does not react to touch | `Send Component ID` is off for it, or its id changed after a reorder and `COMPONENTS` still holds the old one |
| A card or the docs screen shows an outdated page | The generated layouts are stale: run `gen_virtual_layout`, then `pytest tests/test_card_renders.py` |
| A portrait device shows landscape geometry | The portrait HMI was not recompiled, or the widget is missing from `PORTRAIT_LAYOUT` |

## The `.HMI` file format

What the scripts rely on, so a same-length patch is provably safe. Reference implementation: `scripts/hmi_layout/gen_layout.py` (`parse_pages`, `_write_attr`, `block_crc`).

- **Container.** A table of 16-byte name, start and size entries: `N.pa` page blocks, `N.i` and `N.is` pictures, `N.zi` fonts, `main.HMI` (device settings, including the display direction) and `Program.s`.
- **Page block.** A 56-byte header (`<I` stamp, size, header size, component count, …), a component table (`<III` per component: offset, size, …) and the components. An attribute is a record `<u32 len><16-byte name><value>`, ints little-endian and normally 4 bytes; `objname` and `type` (`121` is the page itself) identify a component.
- **Safe same-length writes:** `x`, `y`, `w`, `h` with the derived `endx = x + w - 1` and `endy = y + h - 1`, `font`, `isbr` (word wrap), `sendkey` (`Send Component ID`), colours, and the page component's own `w` and `h`. Anything that changes a block's length is editor work.
- **Block stamp.** Every page block starts with a content stamp the editor validates; a stale one fails with "Version mismatch" / "Loading Page Failed". It is CRC-32 (poly `0x04C11DB7`, MSB-first, init 0, no final XOR) over every byte after the stamp widened to a big-endian u32, plus 40 zero bytes, XOR an unknown length-dependent constant. Same-length edits cancel the constant: `new = old ^ crc(old block) ^ crc(new block)` (`block_crc`).
- **Pictures carry no stamp.** The container table has a checksum of its own that is not cracked, so block lengths and offsets stay as the editor wrote them.

