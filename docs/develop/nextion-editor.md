---
title: Editing the HMI
description: Working in the Nextion Editor on both HMI projects and keeping them in step with the Python pages
---

# Editing the HMI

The display UI is a Nextion Editor project — `nextion/nspanel_haui.HMI` and its portrait sibling `nextion/nspanel_haui_portrait.HMI` — compiled to `nspanel_haui.tft` and `nspanel_haui_portrait.tft`. Layout changes, new widgets, new pages and the portrait variant are hand work in that application; this page is the procedure and the contract that keeps the HMI and the Python pages in step. The hub side of the same cycle is [Nextion component](nextion.md), and [HMI event scripts](nextion-scripts.md) inventories the event code both projects carry.

## When you need this page

- Moving, resizing, recolouring or retitling a widget.
- Adding a widget or a whole page.
- Adding fonts or images: icons, backgrounds, the spinner.
- Maintaining both TFT layouts: landscape (EU and US mounted landscape) and rotated portrait (US mounted portrait). A release ships both assets together.
- Releasing a version with new TFTs: both `.tft` files and both `.HMI` sources go in the same release ([release process](release.md)).
- Turning an HMI change into a device-ready file: [compiling a TFT](#compiling-a-tft).
- Debugging a page that renders nothing, ignores touches or shows stale content: [when something does not work](#when-something-does-not-work).

## Tools and prerequisites

| Tool | Purpose |
|------|---------|
| **Nextion Editor** (official, free, Windows) | Edit an `.HMI` and compile the `.tft` |
| [Nextion2Text](https://github.com/joBr99/Nextion2Text) — local copy `scripts/nextion2text/Nextion2Text.py` | Dump an HMI to readable text to check ids, names and coordinates |
| The repository's Python environment | Regenerate the layouts and run the gates |
| `scripts/nextion_vnc/nextion_vnc.sh` | Reach the editor on a Windows VM from a browser through noVNC |

When the editor runs in a Windows VM, `scripts/nextion_vnc/nextion_vnc.sh` bridges the VM's VNC server to a noVNC page and prints its URL (`http://127.0.0.1:6080/vnc.html?…`). The first run installs websockify and noVNC under `build/novnc/`. The VM defaults to `192.168.65.2:5900`; set `NEXTION_VNC_HOST`, `NEXTION_VNC_PORT` or `NOVNC_PORT` to change the VM or the local port. The page listens on `127.0.0.1` only and the VM's VNC password still applies; stop the bridge with `Ctrl+C`.

In this repository's development setup that VM maps the repository's `nextion/` folder as drive `Z:`, so the editor opens the committed `.HMI` and `File → TFT file output` writes the committed `.tft` in place — there is no copy step in either direction. The editor's start screen lists both projects under *Recent projects* with that path; [compiling a TFT](#compiling-a-tft) is the two-button cycle on top of it.

Dump either project before you map widgets, and again whenever ids may have moved:

```bash
python -m scripts.nextion2text.Nextion2Text -i nextion/nspanel_haui.HMI -o build/nextion-out/landscape -d -s -p visual
python -m scripts.nextion2text.Nextion2Text -i nextion/nspanel_haui_portrait.HMI -o build/nextion-out/portrait -d -s -p visual
```

`build/` is git-ignored. `-o` names the folder (one `.txt` per page), `-d` clears it first so stale files cannot linger, `-s` writes a stats summary and `-p visual` adds position, size and colours. An HMI is a binary project file: open it in the Nextion Editor, and let the scripts patch only what the [HMI↔Python contract](#the-hmipython-contract) and [After any HMI change](#after-any-hmi-change) describe.

### Working through VNC

The noVNC page is a viewer: every click and keystroke in it reaches the VM as an RFB event, so what follows applies to a hand on a mouse and to a script alike — the repair projects were finished by driving `192.168.65.2:5900` with `vncdotool` and reading screenshots back. The VM desktop is 1280 × 800; double-click the editor's title bar to maximize, which widens the `Attribute` panel enough that its drop-down cells can be hit.

Left to right, the maximized window holds the toolbox with the page's `Event` pane under it, the `Display` / `Program.s` / `macro` tabs over a canvas with scrollbars of its own, the page list and the `Attribute` grid, and the `Output` pane across the bottom. Select a widget by clicking it on the canvas or its orange name tag — the tag stays a target when the widget's own text is empty or its box is behind another one. `Program.s` is the tab of that name; page events (`Preinitialize`) are the tab inside the `Event` pane.

The five things that cost the most time:

- **A click that misses the canvas creates a widget.** The canvas scrolls inside the window, so a click aimed at a widget that is scrolled out of view lands on the toolbox, which *inserts the tool under the pointer* — a `Picture` with `Picture ID 65535`, or a 60 × 60 `Hotspot`, at 0,0. Nothing marks it: the picture draws nothing and the hotspot is transparent. The toolbar `Delete` removes the selected widget, and the dump is what proves the page holds only what you meant — the repair `system` page reports 5 components (the page, three texts, the version variable).
- **`Save` does not write the project on the `Z:` share.** Over a session of a dozen edits the toolbar button, `File → Save` and `Ctrl+S` all returned with the file's size and mtime unchanged; `File → Close Project` (answering `Yes` to *Do you want to save the changes?*) is what wrote it, in place. So persist by closing the project and confirm from the shell with `stat` and the dump — do not assume a Save landed because the menu closed. `File → Save as`, naming the open project to itself, is worse and not worth trying: it reports `Compressed file failed` and what it leaves cannot be trusted as a project. A `.tft` written before the project was saved is unaffected — the compile builds from the project in memory.
- **Set `txt_maxl` before `txt`.** The default is 10 characters; typing a longer `txt` answers with a modal `String too long, exceed the max length.`, and the retried `Enter` then lands on the cell under the pointer — for that row the pick-list of the attribute below it (`pw`: `Character` / `Password`), which silently changes it. Re-screenshot the panel after any failed edit rather than typing again.
- **The TFT output dialog starts outside the repository.** Its path field shows `C:\Users\<user>\AppData\Roaming\Nextion Editor\work`; type `Z:\` over it once and the dialog keeps it for the next output. **Output** then opens Explorer on `Z:`; close that window, or the next click only raises it.
- **Wait for each step.** Opening a project takes 15–20 s over SMB (the title bar shows the path when it is in), a compile 3–8 s, the TFT output 5–10 s and the close ~5 s. A script sleeps that long between events; a hand waits for the `Output` pane's last line.

A value is edited in place: a **double**-click on the cell for text and numbers (`Ctrl+A`, type, `Enter`), a **single** click for a drop-down followed by a click on the entry (`sta`, `vscope`, `isbr`, `xcen`, `ycen`, `pw` are the lists a repair project needs). A line of `Program.s` is replaced by clicking into it, `Home`, `Shift`+`End`, then typing over the selection. The grid scrolls with the wheel and its rows differ per widget type, so re-read the panel after scrolling instead of reusing coordinates.

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
| `nextion/nspanel_haui.HMI`, `nextion/nspanel_haui_portrait.HMI` | the layout and the page-scoped event code that must run on the display; `Program.s` declares the theme globals and the 921600 boot baud; `system.tftVersion` carries the TFT version |
| `scripts/hmi_layout/landscape_layout.py`, `portrait_layout.py` | the widget geometry and attribute overrides `gen_layout.py` writes |
| `scripts/hmi_layout/theme.py` | the theme colours compiled into solid widgets on both TFTs |
| `custom_components/nspanel_haui/haui/page/*.py` | behaviour: `COMPONENTS`, `DESCRIPTOR`, render and touch handlers |
| `custom_components/nspanel_haui/haui/mapping/panel.py` | `_page_classes`, and the `PAGE_MAPPING` derived from each `DESCRIPTOR.page_id` |

### Hard rules

- **`Program.s` sets `bauds=921600` in both HMIs.** The firmware starts its UART at that rate and only scans down as a fallback; a TFT compiled at another rate would need a rescan after every boot. `tests/test_bump_version.py` checks both HMIs.
- **Every page sends `sendme` in its `Preinitialize` event.** The hub waits for the `esphome.page` event before rendering; a page without it is never rendered.
- **Prepare the page in `Preinitialize`**: hide unused widgets, set picture backgrounds, clear text. The hub cannot touch the display before the page is shown.
- **A solid-colour page paints itself in the theme in `Preinitialize`.** The hub writes the five base theme globals declared in `Program.s` (`thmBg`, `thmHdrBg`, `thmHdrTxt`, `thmPressed`, `thmCompBg`) before every page switch. TFTs at `0.4.7` and newer also declare four body-foreground globals (`thmCompTxt`, `thmActive`, `thmActiveDk`, `thmTxt`), which the page applies to its widgets in `Preinitialize`. The hub only sends those extra globals to supported TFT versions; for older, unknown or invalid versions it retains per-widget foreground commands. Generate the theme code from the page's widgets and paste it right after `sendme` in both HMIs:

  ```bash
  python -m scripts.hmi_layout.gen_virtual_layout --theme-code grid
  ```

  The command emits foreground assignments when the selected HMI declares the four globals. Paste the generated code again whenever a widget compiled with a theme colour is added, removed or recoloured. `gen_virtual_layout --check`, run by the test suite, validates the matching legacy or foreground-enabled contract.
- **Enable `Send Component ID`** on every touch event the hub must react to (buttons, sliders, keypad keys). Without it the hub receives no component event.
- **Toggle `sendkey` in the landscape project only.** The portrait run copies every widget's `Send Component ID` from `SIBLING_HMI`, so a touch setting changed only in the portrait HMI is overwritten by the next `gen_layout --spec portrait`.
- **Component ids are page-local and change when you reorder widgets.** Re-dump the page and fix every affected `Component(id, …)`.
- **Keep behaviour in the hub.** Layout and visuals live in the HMI; state reads, commands and navigation live in `haui/page/*.py`. HMI event code beyond `sendme` is the exception.
- **Both HMIs carry the same widgets.** Same names, ids, order and event code in both projects: a widget present in one HMI only breaks that TFT silently at runtime, and `make hmi-check` is what proves the parity.
- **Respect the visible area.** Landscape is 480 × 320 px but the bezel hides the rightmost 30 px: keep interactive content left of x 450 ([dimensions](nextion.md#dimensions-and-non-visible-area)).
- **The TFT version lives in the HMI too.** `system.tftVersion` in both HMIs must equal `tft_version` in `esphome/nspanel_haui/version.yaml` — the TFT version can differ from the firmware version — and `python -m scripts.bump_tft_version` writes it. That text is a widget attribute, so the same run rewrites `frontend/virtual/layout_<orientation>.json`; never edit the layouts to carry a version by hand.

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
- **Background tiles are generated.** Put the source picture in `nextion/src_images/bkg/`, named after its key in `haui/mapping/background.py` (`system` is the `modern` picture), and run `python -m scripts.backgrounds.gen_backgrounds`: it writes the dimmed 480 × 320 and 320 × 480 tiles to `nextion/images/bkg/landscape/` and `bkg/portrait/`. A square source at the tile's long edge (480 × 480 here) is cropped without any resampling, which keeps a dithered gradient's palette intact — a 512 × 512 source is rescaled and turns a 58 kB tile into 158 kB.
- **The icon cheatsheet is generated too.** `python -m scripts.font_tools.gen_cheatsheet` writes `docs/cheatsheet.html`; `make generated-check` fails while it is stale.
- **The design grid is editor-only.** `python -m scripts.design_grid.gen_grid` writes `grid_landscape.png` and `grid_portrait.png` (picture 0, `pGrid`) with margins, column and row guides, placeholder sizes, font samples and the theme colours as RGB565.
- **The spinner is two sprite sheets per orientation** (`spinner_<orientation>_1.png`, `_2.png`, pictures 14 and 15), drawn on the `system` tile cropped at the spinner's position. `python -m scripts.spinner.gen_spinner` re-renders them after a tile change or a move of `hSpinner`. The `tmSpinner` timer's `xpic` calls name both sheets by picture id and the editor does not renumber event code, so update those ids in both projects when you insert a picture before them; `gen_virtual_layout --check` fails while they point at other pictures.
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
- One TFT per display model: those two files are the display builds, and the 921600 bps link is set in `Program.s` inside each, so there is no separate high-speed or normal-speed artifact to compile, keep in sync or install; an older TFT keeps a panel at its own rate until the display update replaces the file ([display baud](nextion.md#display-baud)).

### Portrait caveats

- Gesture edge detection is model-aware: the ESPHome scripts read the *Display Model* select the hub syncs on connect — **Landscape** uses the landscape 450 × 320 edge dimensions, **Portrait** the portrait 320 × 480 ones — so no HMI change is needed.
- Touch coordinates differ from landscape, but the hub maps touches by page, component id and name, so matching ids and names make the controls work. Verify every button on real hardware.
- A release that ships only the landscape TFT leaves `display_model: us` devices on an old one: the update flow finds no matching asset.

## Compiling a TFT

Only the Nextion Editor turns an `.HMI` into a `.tft`; no script can. It takes two commands and the second one is the one that gets forgotten: **Compile** builds the image in memory and reports it, `File → TFT file output` writes it to disk. A successful compile with an unchanged artifact on disk looks like a finished job and is not one.

1. **Open the project.** *Recent projects* on the start screen lists each project with its path — `Z:\nspanel_haui.HMI` and `Z:\nspanel_haui_portrait.HMI` in the setup above. A single click only selects an entry; double-click opens it. Give it 30–50 seconds over the SMB share: the title bar reads `Nextion Editor` until the project is in and switches to `Nextion Editor(Z:\nspanel_haui.HMI)` when it is, so wait for that rather than clicking again. `File → Open` reaches the same thing through a normal Windows file dialog filtered to `HMI Files`, where a full path typed into *File name* (`Z:\nspanel_haui_portrait.HMI`) plus `Enter` opens it directly. The recent list is a history, not the folder: an entry stays listed after its file is gone (`zz_probe.HMI` was still there after that probe was deleted), and opening it fails.
2. **Compile.** The **Compile** button on the toolbar, between *Save* and *Debug*. The Output pane at the bottom of the window fills with the memory report — `Available Memory:3584`, `Global Memory:432`, `Total size of picture`, `Total size of font` and one `Page:<name> Memory Occupied:432+…` line per page — and ends with the verdict:

   ```
   File Check Finish
   Compile Successful! 0 Errors, 10 Warnings.File Size:11,520,228
   ```

   `File Size` is the size of the image it just built. Note it: it is how you recognise the file that lands in `nextion/`.
3. **Write the image.** `File → TFT file output` is the **first** entry of the File menu; it opens a small dialog with the name prefilled (`nspanel_haui.tft`), the project's own drive in a dropdown (`Z:`), one **Output** button and the `only open the output folder` link, which does nothing but look. **Output** writes the file without asking — an existing `.tft` is replaced silently — and then opens the folder in Explorer, so the name in that field is the file you get.
4. **Repeat for the other project**, then check what you produced — below. Compiling does not mark a project as modified: `File → Close Project` right after it asks nothing about saving, and nothing is written.

`Compile` on its own changes nothing on disk; the `.tft` keeps its timestamp until `TFT file output` runs.

### What the compile should say

`0 Errors` is not negotiable, and every warning either project reports is of one kind: `Warning:Component overlap: <page>.<widget>&<widget>`. There are only three pairs behind it:

- **A transparent hotspot on the button it lights up** — `grid.g1Btn&g1Overlay` … `grid.g6Btn&g6Overlay`, and the media tiles' `m1Btn&m1Overlay`, `m2Btn&m2Overlay`, `m3Btn&m3Overlay`. The overlay is the touch area drawn over the visible button, so the two boxes are meant to coincide.
- **A header bar behind its page title** — in portrait only, because only the portrait layout has `tHeader`: a full-width 50 px bar with `tTitle` on top of it (`alarm.tHeader&tTitle`, `cover.tHeader&tTitle`, and the same pair on every page whose header carries the title). The landscape project has no `tHeader` at all, which is why it reports none of these.
- **The light page's two sliders sharing one slot** — `light.hBrightness&hColorTemp` sit at identical geometry on purpose: one slot on the page that shows brightness or colour temperature, never both. `scripts/hmi_layout/landscape_layout.py` and `portrait_layout.py` set both to the same `(x, y, w, h)`; if that ever stops being true, the warning disappears and a slider has moved.

Anything else is new — fix it before you write the TFT.

The 1.1.0 projects report 10 of these in landscape (six grid, three media, one light) and 20 in portrait (the same pairs plus the header ones). The count moves with the layout; the pairs should not.

The verdict is easy to miss: the Output pane is a few lines tall and scrolls, the warnings and the `Page:` lines come first, and the bar along the bottom of the window (`Encoding:utf-8|Model:NX4832F035_011…`) does not repeat it. Scroll the pane to its last line.

### Proving an artifact belongs to its source

The compiler is deterministic: compiling an unchanged project and writing it out reproduces the committed `.tft` byte for byte. That held for both 1.1.0 artifacts (`nspanel_haui.tft` 11,520,228 bytes and `nspanel_haui_portrait.tft` 11,323,456 bytes, same SHA-256 before and after the recompile).

`git status --short nextion/` is therefore the honest answer to *is this TFT the compile of these HMIs*:

| After a recompile | Means |
|---|---|
| no diff | the artifact was already current — nothing to commit |
| the `.tft` you just compiled | the HMI changed since the artifact was written, and this is that change |
| both `.tft` files | the landscape image went into the portrait file or the other way round — look at the name in the dialog |

Do not predict the outcome; let the diff decide. A comment is not part of the image at all: adding `// probe` to the system page's `Preinitialize` and recompiling produced a byte-identical `.tft` (same size, same SHA-256). An attribute the page draws is part of it — a colour, a font, geometry, `tftVersion`; `tests/test_bump_version.py` reads that text back out of the compiled file. So a cleanup that only removes comments needs no rebuild, and a rebuild made anyway leaves the artifact unchanged — which is what the commit should say.

The same check answers "does this cleanup change what a panel draws": an artifact that compiles back byte-identical to the one installed cannot draw a page differently, which is a stronger statement than a look at one page on one panel.

### What compiling does not touch

Compiling, and switching projects with `File → Open`, does not rewrite either `.HMI` while the project has no unsaved edits — verified by hash across a full landscape and portrait compile, and by `File → Close Project` asking nothing and writing nothing right after one. With unsaved edits it is that close which writes the project: answer *Yes* to *Do you want to save the changes?* and it is saved in place. Do not count on `Save` for it — over the `Z:` share the menu entry, the toolbar button and `Ctrl+S` all returned without writing anything, and `File → Save as` aimed at the open project reports `Compressed file failed` ([working through VNC](#working-through-vnc)). Closing is also the window [step 2 of the checklist](#after-any-hmi-change) closes before a script writes the file.

The folder itself carries Windows leftovers — `nextion/.DS_Store` and one in each subfolder — which the repository's `.gitignore` covers, so they never show up in `git status` and never belong in a commit.

## The repair TFTs

Two extra `.tft` files let the editor restore a display whose own file cannot be installed: `nextion/nspanel_haui_repair.tft` (landscape, `eu`) and `nextion/nspanel_haui_repair_portrait.tft` (portrait, `us`). They are not compiles of the release HMIs and they do not follow `tft_version`; they carry a fixed version of their own (`REPAIR_VERSION` in `scripts/release/generate_firmware_manifest.py`, currently `1`). The hub installs one first and the TFT the firmware needs right after it — see [Display repair](update-process.md#display-repair).

They exist because the usual TFT is 11.5 MB: a display that is half-written, runs at another baud, or reboots on the way through it cannot take that transfer, while a page that draws one message always installs. What makes even that page small is its fonts. Both repair projects carry **two subset faces of their own** — `nextion/fonts/repair_body.zi` (12,906 bytes, h24) and `nextion/fonts/repair_title.zi` (57,137 bytes, h72) — where the release HMIs load the full Roboto `.zi` files; those two are exactly the `Total size of font:70,043` a repair compile reports, against `887,752` for the full Roboto pair the projects started with — which is essentially the whole of why the full-font builds were about 1.25 MB (the landscape file committed before the swap was 1,249,540 bytes) while the pair now measures 465,028 and 465,032. Against the release files' 11,520,228 and 11,323,456 that is a twenty-fifth. The rest of what the repair project leaves out is the rest of what made the release file big — the background pictures (a repair compile has no `Total size of picture` line at all), the widget set of thirteen pages, the theme globals and the event scripts.

!!! note "The committed pair is real, and reproduces from its sources"
    `nextion/nspanel_haui_repair.HMI` (7,414,731 bytes) is compiled to `nextion/nspanel_haui_repair.tft`, and `nextion/nspanel_haui_repair_portrait.HMI` (8,251,267 bytes) to `nextion/nspanel_haui_repair_portrait.tft`. Recompiling each saved project and writing it out again reproduced its `.tft` byte for byte (same MD5 both times), which is the proof [proving an artifact belongs to its source](#proving-an-artifact-belongs-to-its-source) asks of the release pair.

### The project

One project per display model, built from an empty project of that size — **not** a copy of the release HMIs, whose 11 MB are the problem. A repair project is a single page, named `system` and holding id 0 so that `Program.s`' `page 0` starts on it, and that one page both draws the message and carries the version. Nothing else is in there: no picture, no icon, no theme global, no touch widget and therefore no `Send Component ID` anywhere. Each project needs exactly three things.

1. **`Program.s` sets the display link rate.** The firmware starts its UART at 921600 bps and only scans down as a fallback, so a repair TFT compiled at another rate is not the file that always installs:

   ```
   bauds=921600
   ```

   Overwrite only the keyword and the rate: the line keeps the editor's own comment, so it reads `bauds=921600 //Configure baudrate`, where the empty project ships `baud=9600`. `dim=100`, `recmod=0` and the `printh` boot message are that template's defaults and are fine as they are.

2. **The page draws the message**, with `sendme` as the whole of its `Preinitialize` event — the hub waits for that event, and the text is the widgets' own `txt`, so the page has no preparation to do:

   | Widget | id (landscape / portrait) | `txt` |
   |--------|---------------------------|-------|
   | `tRepairTitle` | 1 / 1 | `Repair` |
   | `tRepairBody` | 2 / 2 | `Installing the display file next.` |
   | `tRepairBody2` | 3 / 4 | `Do not power off the panel.` |

   All three are `Text`, `font` 1 for the title and 0 for the bodies, `txt_maxl` 64, `isbr` `False`, `xcen` and `ycen` `Center`, `pco` 0 on `bco` 65535 — black on white, like the release page they stand in for.

   Font 1 is `repair_title` (h72) and font 0 `repair_body` (h24): two subset `.zi` files of their own in `nextion/fonts/`, 12,906 and 57,137 bytes, 70,043 together where the full Roboto faces they replace are 887,752. Both are `iso-8859-1`, and the editor's `Fonts` pane lists each with the id the widgets use — id 0 `repair_body`, id 1 `repair_title`. A subset font draws nothing for a glyph it does not carry, so the canvas is the check: open the project and see all three lines, as both do. Changing a string means looking at that canvas again, and regenerating the font only if a character is missing.

   Two lines are two widgets, not one widget with `\r\n` in its `txt`: a `\r\n` inside a string literal typed into the event editor does not compile.

3. **`tftVersion` is a `Variable`, not a `Text`.** The firmware reads `system.tftVersion` as a text sensor at boot, and the release HMIs implement it as a **string** variable with global scope; a repair project must match that shape. A `Variable` left at its default `sta Number` compiles and installs and then answers nothing: the display reports no version, and an empty version is unknown to the hub, which is not the state a rescue file should leave behind.

   | Widget | id (landscape / portrait) | Attributes |
   |--------|---------------------------|------------|
   | `tftVersion` | 4 / 3 | `sta String`, `vscope global`, `txt 1`, `txt_maxl 10` |

   The ids differ between the two projects because their widgets were added in a different order. Nothing addresses a repair widget by id — the hub only ever reads `system.tftVersion` — so the names and the parity of the set are what matter.

### Geometry

| Model | Project size | Filename | `display_model` |
|-------|--------------|----------|-----------------|
| Landscape (EU, US mounted sideways) | 480 × 320 | `nextion/nspanel_haui_repair.tft` | `eu` |
| Portrait (US mounted upright) | 320 × 480 | `nextion/nspanel_haui_repair_portrait.tft` | `us` |

| Widget | landscape `x, y, w, h` | portrait `x, y, w, h` |
|--------|------------------------|-----------------------|
| `tRepairTitle` | 0, 0, 450, 96 | 0, 140, 320, 96 |
| `tRepairBody` | 0, 130, 450, 30 | 0, 290, 320, 30 |
| `tRepairBody2` | 0, 165, 450, 30 | 0, 325, 320, 30 |

Landscape hides its rightmost 30 px, so its texts stop at 450 and the portrait ones use the full 320 ([dimensions](nextion.md#dimensions-and-non-visible-area)). Font 1 (`repair_title`, h72) draws `Repair` 171 px wide on either page and font 0 (`repair_body`, h24) draws the longest body line 261 px wide, so nothing wraps or clips even on the 320 px page.

### Compiling and committing them

[Compiling a TFT](#compiling-a-tft) applies unchanged — **Compile**, then `File → TFT file output` with the filename from the table above. A repair compile reports `0 Errors` and no `Component overlap` warning at all: it has one widget per box, and its report has no `Total size of picture` line because the project holds no picture:

```text
Available Memory:3584
Global Memory:32
Total size of font:70,043
Page:system Memory Occupied:32+252=284
File Check Finish
Compile Successful! 0 Errors, 0 Warnings.File Size:465,028
```

Both repair projects report these figures — the same `Global Memory`, font total and page memory — and differ only in `File Size`: 465,028 landscape, 465,032 portrait. `Global Memory` is 32 where a release compile reports 432, because the one global here is a 10-character version string; `Total size of font` is the sum of the two `.zi` files, so it moving is the font list changing.

Then prove the pair before committing:

```bash
python -m scripts.verify_nextion.check_repair_tft
```

It reports each file of the manifest's `repair` block and fails on a missing file, an empty or oversized one, or one that does not carry the `tftVersion` text `1`. A committed pair is checked again by `pytest tests/test_release_manifest.py` and by the release workflow, which then publishes both files and names them in the manifest's `repair` block. Bumping `REPAIR_VERSION` means recompiling both files with the new `tftVersion` text — the check is what catches a forgotten one.

That check reads the compiled bytes, though, and `REPAIR_VERSION` is `"1"`: one byte turns up in a 465 KB compile by chance, so its `[OK]` proves little. Read the text out of the project instead, with the helper `scripts/bump_tft_version.py` already uses for the release HMIs — it understands a repair project's `system` page:

```bash
python -c 'from pathlib import Path; from scripts.bump_tft_version import read_tft_version; \
  [print(p, repr(read_tft_version(Path(p)))) for p in \
   ("nextion/nspanel_haui_repair.HMI", "nextion/nspanel_haui_repair_portrait.HMI")]'
```

Both lines must read `'1'`. That helper needs the widget to be a *string* variable: while the portrait project still carried a `sta Number` variable named `tftVersion`, it read back some other widget's text (`'newtxt'`) instead — which is how that mistake was caught. Text in the project, plus a `.tft` that reproduces from it, leaves only the boot itself for a real display.

Unlike the release TFTs, these files need no `tft_version` bump and no layout spec: they are not compiled from the projects `scripts/hmi_layout/` patches, and `tests/test_bump_version.py` only inspects the two release HMIs.

## After any HMI change

Run these from the repository root with `source .venv/bin/activate`, in this order: the layout specs write the HMIs, the editor compiles them, everything after that is generated from the HMIs. A step with nothing to do reports so (`wrote 0 widgets`, `already '…'`), so the whole sequence is safe to run.

1. **Close the project in the Nextion Editor** (`File → Close Project`, answering *Yes* to keep your work). The editor re-saves the open project on close and on every project switch, overwriting whatever a script wrote — and on the `Z:` share that close is the only thing that writes an edited project at all ([working through VNC](#working-through-vnc)).
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
   | `python -m scripts.spinner.gen_spinner` | `nextion/images/spinner_<orientation>_1.png`, `_2.png` (pictures 14 and 15) | the `system` tile changed or `hSpinner` moved |

5. **Re-open, check and compile both projects.** Each must open without "Version mismatch". Compile and write `nextion/nspanel_haui.tft` and `nextion/nspanel_haui_portrait.tft` whenever step 2 or 3 wrote either HMI — [compiling a TFT](#compiling-a-tft) has the buttons, the expected warnings and the artifact check that follows. An HMI change alone never reaches a device.
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
| **Compile** reports success but `nextion/*.tft` keeps its old timestamp | `Compile` only builds the image in memory — `File → TFT file output → Output` writes the file ([compiling a TFT](#compiling-a-tft)) |
| The editor looks hung after opening a project from the share | it is still loading the 19 MB project: the title bar only becomes `Nextion Editor(Z:\…HMI)` when it is in — wait rather than clicking again |
| The written `.tft` is not the compile you just ran | the `File Size` in the Output pane and the file's size must be the same number; if they differ, the compile ran before the last change or the dialog wrote the other project's name |

## The `.HMI` file format

What the scripts rely on, so a same-length patch is provably safe. Reference implementation: `scripts/hmi_layout/gen_layout.py` (`parse_pages`, `_write_attr`, `block_crc`).

- **Container.** A table of 16-byte name, start and size entries: `N.pa` page blocks, `N.i` and `N.is` pictures, `N.zi` fonts, `main.HMI` (device settings, including the display direction) and `Program.s`.
- **Page block.** A 56-byte header (`<I` stamp, size, header size, component count, …), a component table (`<III` per component: offset, size, …) and the components. An attribute is a record `<u32 len><16-byte name><value>`, ints little-endian and normally 4 bytes; `objname` and `type` (`121` is the page itself) identify a component.
- **Safe same-length writes:** `x`, `y`, `w`, `h` with the derived `endx = x + w - 1` and `endy = y + h - 1`, `font`, `isbr` (word wrap), `sendkey` (`Send Component ID`), colours, and the page component's own `w` and `h`. Anything that changes a block's length is editor work.
- **Block stamp.** Every page block starts with a content stamp the editor validates; a stale one fails with "Version mismatch" / "Loading Page Failed". It is CRC-32 (poly `0x04C11DB7`, MSB-first, init 0, no final XOR) over every byte after the stamp widened to a big-endian u32, plus 40 zero bytes, XOR an unknown length-dependent constant. Same-length edits cancel the constant: `new = old ^ crc(old block) ^ crc(new block)` (`block_crc`).
- **Pictures carry no stamp.** The container table has a checksum of its own that is not cracked, so block lengths and offsets stay as the editor wrote them.

