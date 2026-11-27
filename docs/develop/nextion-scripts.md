---
title: HMI event scripts
description: Inventory of the event code in both HMI projects, what each script does and the hub command or firmware event it pairs with
---

# HMI event scripts

Both HMI projects carry script of their own: the `Preinitialize` block that every
page depends on for its theme or its background, the press feedback on the
tappable tiles, and the boot spinner on the system page. This page is the
inventory of that code — which script exists, what it does, and the hub command
or firmware event it pairs with — so moving behaviour between the display and
the hub is a decision rather than an accident.

Read it when you add, move or delete event code, when a page paints itself wrong
before the hub renders, or when you are about to move logic onto the display. The
rules that keep the HMI and the Python pages in step are in
[Nextion Editor](nextion-editor.md#the-hmipython-contract); the component the
firmware drives is [Nextion component](nextion.md).

## Where the boundary is

The hub owns the logic: it decides what a page shows and writes it with display
commands. Display-side script exists only where the hub cannot act or would be
too late:

| On the display | Why not the hub |
|---|---|
| `sendme` in every `Preinitialize` | it is how a page change reaches the firmware, which publishes `esphome.page`; without it the page is never rendered |
| Theme paste on the 14 solid pages | the hub cannot write a page's widgets before the page is active — the commands would be rejected (`Invalid variable name`) |
| Background picture on clock, clocktwo and weather | same: the page must paint itself from `system.vBackground.val`, which the hub sets before the switch |
| Widgets hidden, texts cleared, sliders zeroed | same: a page must not show the previous visit's values for the moment before the hub renders |
| Press feedback on the grid and media tiles | the tiles would feel dead for one hub round trip |
| The boot spinner on the system page | it runs before any connection exists |

Everything else — labels, values, colours, icon choices, page order — is the
hub's. A script that decides *what* a widget shows belongs in the page class, not
in the HMI.

## Taking the inventory

The numbers below come from the dumps of both projects:

```bash
python -m scripts.nextion2text.Nextion2Text -i nextion/nspanel_haui.HMI -o build/nextion-out/landscape -d -s -p visual
python -m scripts.nextion2text.Nextion2Text -i nextion/nspanel_haui_portrait.HMI -o build/nextion-out/portrait -d -s -p visual
```

One `.txt` per page plus `<project>_Stats.txt`, which is where the line counts
come from. `build/` is git-ignored, and the dump is read-only.

| | Landscape | Portrait |
|---|---|---|
| Pages | 19 | 19 |
| Components | 521 | 521 |
| Event blocks | 45 | 45 |
| Lines of event code | 1370 | 1367 |
| Lines unique within their page | 1000 | 997 |
| Widgets with **Send Component ID** | 199 | 199 |

The 370 lines in each project that repeat inside their own page are the theme
paste, the `vis …,0` block and the press feedback: the same shape on every page.
Re-take the dump after an HMI change, and update this page in the same commit
when you add or remove event code.

## Program.s

`Program.s` holds what must exist before any page runs. It is edited in the
Nextion Editor like the rest, and it is not part of any page's event code.

| Statement | What it does | Paired with |
|---|---|---|
| `int sys0=0,sys1=0,sys2=0` | the three integer globals the pages share | `sys0` is clocktwo's loop counter, `sys1` carries the background picture id |
| `int thmBg…thmHdrBg…thmHdrTxt…thmPressed…thmCompBg` | the five theme globals the solid pages read in `Preinitialize` | `THEME_GLOBALS` in `haui/mapping/color.py`, sent by `Theme.display_commands()` before every page switch |
| `int thmCompTxt…thmActive…thmActiveDk…thmTxt` | the four body foreground globals, read only by a page whose `Preinitialize` carries the generated foreground lines | `FOREGROUND_GLOBALS` in the same module; the hub sends them only to a TFT from `0.4.7` on, older panels get per-widget foregrounds from `haui/mapping/theme_foregrounds.py` |
| `bauds=921600` | the display's own boot rate | `hardware.yaml` starts the UART at the same rate; the boot scan in `display_baud.yaml` follows an older TFT down |
| `recmod=0` | passive mode: the display answers commands, it does not stream every event | the boot scan re-sends it before its probe |
| `lcd_dev fffb 0002 0000 0020` | the touch calibration fix | — |
| `printh 00 00 00 ff ff ff 88 ff ff ff` | prints the Nextion's start-up code `0x88` once at power-on | `nextion.cpp` reads `0x88` as *system successful start up* and marks the display's setup as reported |
| `page system` | the boot page | the hub keeps page 0 visible while disconnected, so this page is also what a panel shows with no hub |

The theme names must stay alphanumeric and at most 14 characters —
`tests/test_color.py` checks that against `THEME_GLOBALS`, because a Nextion
variable name has no room for more.

## Page Preinitialize

Every one of the 19 pages starts its `Preinitialize` with `sendme`, exactly once,
and nothing may precede it. What follows falls into a few patterns; the counts
are the landscape dump, and landscape and portrait agree except where
[parity](#parity) says otherwise.

| Page | Fill | Lines | `=thm` | `vis …,0` | `.txt=""` | What else it sets up |
|---|---|---|---|---|---|---|
| about | picture 3 | 19 | 0 | 3 | 15 | hides its two reference pictures `p0`/`p1` and clears every field it shows |
| alarm | solid | 92 | 63 | 17 | 9 | |
| blank | solid | 3 | 1 | 0 | 0 | the page background only — `BlankPage` sends no render of its own |
| climate | solid | 114 | 70 | 22 | 15 | |
| clock | picture 1 | 28 | 0 | 7 | 11 | background picture on the page and 5 widgets |
| clocktwo | picture 1 | 13 | 0 | 1 | 1 | background picture loop over widgets 2..116, plus `tNotif.picc` |
| cover | solid | 43 | 28 | 5 | 6 | |
| grid | solid | 127 | 71 | 31 | 17 | |
| light | solid | 55 | 34 | 10 | 6 | |
| media | solid | 108 | 64 | 23 | 14 | |
| notify | solid | 49 | 29 | 6 | 10 | |
| qr | solid | 58 | 27 | 11 | 15 | |
| row | solid | 221 | 122 | 51 | 25 | zeroes the 5 row sliders |
| select | solid | 107 | 65 | 17 | 21 | |
| settings | solid | 41 | 26 | 1 | 8 | zeroes both sliders, resets both percentage labels |
| system | picture 3 | 16 | 0 | 4 | 0 | first-run QR and spinner, see below |
| timer | solid | 77 | 53 | 11 | 8 | |
| vacuum | solid | 71 | 43 | 11 | 12 | |
| weather | picture 1 | 101 | 0 | 25 | 29 | background picture on the page and 30 widgets, no theme code |

Four patterns are worth knowing by name:

- **Theme paste** — the generated `=thm…` lines on the 14 solid pages, always
  ending the block under the comment
  `// theme colours: gen_virtual_layout.py --theme-code`. Never hand-edit them:
  `python -m scripts.hmi_layout.gen_virtual_layout --theme-code <page>` writes
  them and `--check` fails while a page disagrees with the palette.
- **Background picture** — clock, clocktwo and weather copy
  `system.vBackground.val` into their own and their widgets' picture ids.
  `haui/page/clock_common.py` sets that global from `background_picture_id()`,
  and the About and system pages use the fixed picture 3 instead.
- **Hide and clear** — optional widgets start hidden (`vis <widget>,0`) and the
  hub shows the ones the entity supports; text fields start empty so a value from
  the previous visit cannot show for the moment before `render_panel()` runs. The
  hub renders exactly the widgets the page left visible.
- **Zero the sliders** — row and settings reset their sliders to `0` so the thumb
  never starts at the last value it was dragged to. The hub then writes the real
  value.

## The system page

`system` is the boot page and the only page with global scope: it owns the
`firstRun`, `resTxt`, `resVal`, `tftVersion` and `vBackground` variables the rest
of the project reads.

- It composes `tMsg2` from `system.tftVersion` — the string
  `python -m scripts.bump_tft_version` advances with a release that ships new
  TFTs — so the boot screen names the TFT it is running.
- On the first boot after power-on (`system.firstRun.txt` is still `1`) it hides
  `tMsg1`, `tMsg2` and the QR code, and starts the spinner. The firmware clears
  `firstRun` when the hub connects
  (`scripts_connection.yaml`, `system.firstRun.txt="0"`), so a panel that reaches
  the hub falls out of the first-run state; the spinner and the message then wait
  for the next power cycle.
- `tmSpinner` is an 80 ms page timer, disabled in the editor and enabled by that
  `Preinitialize`. It steps `vFrame` through 30 positions in the two 140 × 140
  spinner pictures (ids 11 and 12) with `xpic …` plus `doevents`, wraps every 60
  frames into `vLoops`, and at `vLoops == 5` reveals `tMsg1` and `tMsg2` — the
  "still waiting" message.
- The page-local variables `vFrame`, `vLoops`, `vPosX`, `vPosY` live only here;
  nothing else reads them.

## Widget handlers

26 of the 45 blocks are not `Preinitialize`: 25 widget events and the one timer.
The touch the hub needs is not script at all — a widget with **Send Component
ID** enabled makes the display report `page,component_id,event`, the firmware
publishes it as `esphome.component`, and
`haui/abstract/mixins/touch_input_mixin.py` resolves it through the page's
`COMPONENTS` registry. 199 widgets in each project carry it, and `clock.tTime` is
the only one set to *on press* rather than *on press and release*.

| Page | Widget | Events | Script | Purpose | Hub counterpart |
|---|---|---|---|---|---|
| grid | `pGrid` | press | `vis pGrid,0` | hides the editor-only design grid | — (`Preinitialize` does it too; this is the belt-and-braces copy) |
| grid | `g1Overlay`…`g6Overlay` | press, release | `click g<N>Btn,1/0`, the same value into `g<N>Icon/Name/Power.bco` | the tile lights up under the finger | the hotspot's id is the tile's tap (`haui/page/grid.py`) |
| media | `m1Overlay`…`m3Overlay` | press, release | `click m<N>Btn,1/0` into `m<N>Icon/Name.bco` | the same feedback for the three media source tiles | `haui/page/media.py` |
| settings | `hBrght`, `hBrghtDim` | press, release | `click tBrghtPct,0` / `click tBrghtDimPct,0` | asks the matching label to recompute itself | the hub repeats the same `click` after it writes a value (`haui/page/settings.py`) |
| settings | `tBrghtPct`, `tBrghtDimPct` | release | `covx <slider>.val,<label>.txt,0,0` then `+="%"` | the percentage follows the thumb without a hub round trip | the hub writes the slider value and the label's colour, never its text |

The `pGrid` picture is the design grid from `scripts/design_grid/gen_grid`: it has
to be visible in the editor to lay a page out and has to be gone at runtime, so
each page hides it in `Preinitialize` and the grid page hides it again on the
first touch, which is the one moment a panel could still be showing it.

## Limits that matter

- **Timers are page-scoped.** `tmSpinner` is the only timer in either project,
  and it exists only on the system page; leaving the page stops it. A timer that
  keeps running across pages does not exist here, and periodic work belongs to
  the hub's own timers anyway.
- **State lives for one visit.** Page-local variables and widget values survive
  until the page is shown again, which is exactly why `Preinitialize` hides,
  clears and zeroes them. A page's `scope` decides what outlives it: only
  `system` is global, every other page is local.
- **There are no sleep or wake hooks.** Idle behaviour is the firmware dimming
  the backlight while page 0 stays visible; a real hardware sleep is an explicit
  action (`scripts_display.yaml`, `display_off`), not a schedule, so no page runs
  script on waking.
- **Script size.** The largest block is the row `Preinitialize` at 221 lines and
  the largest handler is the spinner timer at 29. Both projects compile with
  them; the Nextion Editor's compile output reports the project's program and RAM
  use, so check it after adding a large block rather than assuming there is room.

## Parity

Both projects hold the same 45 event blocks with the same owners, and three
`Preinitialize` bodies differ. None of the three changes what a page shows:

| Page | Landscape | Portrait | Reading |
|---|---|---|---|
| clock | `sys1=system.vBackground.val` | the same, under a `// background` comment | comment only |
| clocktwo | the picture loop skips widget 112 (`s1`) | the loop paints 2..116 | deliberate, and answered by the hub — see below |
| weather | no separator comment after the hide block | has a standalone `//` after the hide block | comment only |

The clocktwo exception is the only one that touches what the panel paints, and it
is a pair rather than a defect: the landscape loop leaves the top-left dot `s1`
(id 112, the first of the four second dots `s1`..`s4`) on its compiled picture,
and `ClockTwoPage.start_panel()` sends that widget's crop itself with
`s1.picc=<background picture>`. Both orientations therefore finish the page load
with the dot on the chosen picture, and the command is pinned by
`tests/test_page_clocktwo.py`, so neither half is dropped without the other
failing. Portrait reaches the same state twice over, which costs one redundant
write and nothing else.

An exception in one project's `Preinitialize` is only safe while a page class
sends the missing value itself. Before you call one a defect, look for that
counterpart: `grep -n "picc=" custom_components/nspanel_haui/haui/page/`.

What no check sees: the layout specs in `scripts/hmi_layout/` cover geometry and
attributes and `gen_virtual_layout --check` covers the theme code, but nothing
compares the two projects' event code. Compare it yourself with the two dumps
from [Taking the inventory](#taking-the-inventory). The virtual panel does run
every page's setup code in both orientations and warns on a command the display
would reject — a missing attribute, an undeclared variable — so
`node --test tests/frontend/*.test.mjs` catches script that no longer fits its
widgets, just not script that fits and differs.

## Cleanup applied

The three inert leftovers have been removed in the Nextion Editor and verified in
fresh event-code dumps from both projects:

- `weather` (landscape): removed the redundant first `sys1=system.vBackground.val`
  above the hide block; the assignment after the block remains.
- `row` (landscape): removed the trailing `// TES` comment.
- `system` (both): removed `sys0=0` and its stale spinner comment. The clocktwo loop
  still initializes `sys0` where it uses the counter.

The clocktwo guard remains intentionally: the hub already sends the dot's crop, so
dropping the guard only turns that command into a second write of the same value.
The current `.tft` artifacts and `tft_version` are unchanged; this cleanup does
not change what a page shows.

## What a new page must provide

- `sendme` as the first line of `Preinitialize`, or the hub never renders it.
- The generated theme code at the end of `Preinitialize` if the page is solid, or
  the background picture copy if it sits on a picture.
- `vis <widget>,0` and `.txt=""` for everything the hub may leave alone, so the
  page shows nothing it has not been told this visit.
- **Send Component ID** on every widget whose touch must reach the hub, in both
  projects and with the same ids — the hub addresses widgets through the page's
  `COMPONENTS` registry.
- No logic beyond the patterns above: what a widget shows is the page class's
  decision.
