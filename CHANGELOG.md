# Changelog

All notable changes to **NSPanel HAUI**, one line per change. The release notes
of each [GitHub release](https://github.com/happydasch/nspanel_haui/releases)
(prepared in `.github/release-notes/<tag>.md`) describe the changes in detail,
and [Update Process](docs/develop/update-process.md) has the steps for every breaking
change.

Releases are tagged `vX.Y.Z` and follow [Semantic Versioning](https://semver.org/);
commit messages follow [Conventional Commits](https://www.conventionalcommits.org/).

## [Unreleased]

### Added

- Hub: `nspanel_haui.show_image` draws an image into a rectangle on whatever page the panel is showing — the hub downloads it, rebuilds it from a few hundred `fill` rectangles in the display's own 65 536 colours and hands that program to a new firmware action (`draw_runs`), which streams it to the display in slices in about half a second — and `nspanel_haui.clear_image` paints the rectangle back to the page's background colour; a logo, an icon, a QR code or a chart comes out crisp, a photograph as a coarse mosaic, the editor's **Simulated** preview shows the same image while it shows that page, and neither the HMI nor the TFT changes ([Images on the panel](docs/user/actions.md#images-on-the-panel), [firmware surface](docs/develop/esphome.md#actions)).
- Hub: `nspanel_haui.show_image` also takes `path` instead of `url` — a file in the `www` folder of the configuration, the one Home Assistant already publishes at `/local`, so an image you have as a file needs no web server to reach the panel ([Images on the panel](docs/user/actions.md#images-on-the-panel)).
- Hub: `nspanel_haui.start_camera_stream` keeps a camera's picture on the panel — a snapshot a few times a second, drawn as only the rectangles that actually changed since the last frame the panel received, so a still scene sends nothing at all and one person walking costs a handful of rectangles per frame — with `nspanel_haui.stop_camera_stream` to end it; a frame the panel is still drawing is skipped instead of queued, the stream ends by itself on a page change, a sleeping display, a TFT install or a camera that stops answering, and no firmware change is needed ([A camera on the panel](docs/user/actions.md#a-camera-on-the-panel), [why it needs no firmware](docs/develop/esphome.md#a-camera-stream-needs-no-firmware-of-its-own)).
- Panel: a **Camera** panel type keeps one camera's picture on the display — the camera is picked in the panel editor and the hub's stream paints the camera page's big text area — the `tText` widget's own rectangle, cropped to fill it, the way the media panel's cover art goes where its icon is, while painting only what changed; the picture is painted whole when it appears and again only when the area was drawn over, so a plain refresh never flashes it — the paint that shows it may spend six times an update's rectangles, so it arrives at the quality's detail instead of as a coarse mosaic; one **Picture quality** setting decides that detail and the rate together, because on this display they are one budget: *High* draws 2-pixel cells at a frame a second, *Medium* 3-pixel cells at two, *Low* 6-pixel cells at four, where a frame rate the display cannot paint was a knob that did nothing; the editor's preview — **Live** as well as Simulated — and a panel card show that picture rather than an empty area; the page says *Waiting for the camera* until the first snapshot is drawn and *No camera selected* when it has none, and the stream starts when the page is shown and ends when it is left, so nothing runs in the background ([Camera panel](docs/user/panels/panel_camera.md)).
- Panel: the **Media** panel draws the player's cover art in place of the music icon while it publishes one - its `entity_picture`, fetched and rebuilt as a few hundred `fill` rectangles inside the icon widget's own rectangle (the position and size come from the TFT's layout for each display model) and replaced whenever the track, station or source changes; a player without one, a picture that cannot be loaded and a panel whose firmware cannot draw all keep the icon, and the page stays responsive while a cover loads because nothing waits for the download ([Panel Media](docs/user/panels/panel_media.md#how-it-behaves)).
- Panel: a **Camera** panel's card and thumbnail show its picture instead of *Waiting for the camera* - the panel list, the panel editor and the Add panel catalog ask the hub for one whole paint of the picture area planned from the camera's own snapshot at the quality the panel is set to (`plan_still_frame`), and a device that does show that panel for that camera keeps being replayed as it was, so a card looks like the panel and not like a screenshot of another screen - a sample camera, which is what a new panel is previewed with, shows one of the instance's own cameras while it has one, and a drawn picture only when it has none, so the committed docs screenshots stay the same on every machine - a camera that does not answer leaves the card on the placeholder, and a camera card's render is no longer kept in the browser, because a picture is stale by the next visit and far too large for the kept-render list ([Panel Camera](docs/user/panels/panel_camera.md)).
- Display: **Cool Glow**, **Warm Glow** and **Dusk** join the *Background* pictures — a cool teal-and-amber, a warm rust-and-orange and a violet dusk gradient that already carry the contrast for white text, so they are used as drawn instead of dimmed, and they slot in ahead of the seasonal tiles at picture ids 4–6 in both display models ([Background pages](docs/user/editor/themes.md#background-pages)).

### Changed

- Hub: `show_image` `quality` reaches 12 000 rectangles instead of 769 — and it is the total for the whole draw, the coarse pass included, not extra — and a pass is streamed in slices the panel can hold instead of one program, so a larger rectangle is no longer limited by the panel's memory, and each run travels in a third less space (five base-36 numbers; the firmware decodes them back into `fill`) — the ceiling is now the time a caller is willing to wait: the hub plans 2 ms per rectangle, so the top of the range is at most about 24 s, and a photograph is still a mosaic that belongs in a page background picture ([Images on the panel](docs/user/actions.md#images-on-the-panel)).
- Display: a draw no longer runs at the pacer's one-instruction-per-2-ms — the firmware switches the pacer off for the length of a `draw_runs` program and keeps a window of twelve `fill` instructions in flight, adding the next only when the display acknowledged one, so an image is drawn at the display's own rate instead of at `runs × 2 ms`: several times faster on a healthy panel, up to the serial link's ~3 700 instructions a second, while a display that needs longer is throttled rather than overrun and a stalled one fails the program instead of holding the pacer off; the hub's fence timer tolerates such a panel and the log line reports the runs per second it reached ([Pacing](docs/develop/nextion.md#a-draw-paces-itself-instead)).
- Hub: `show_image` paints its rectangle as one `fill` in the picture's own most common colour plus only the blocks that differ from it — the canvas is found with the picture instead of being black, so a logo's field, a photo's sky and the margins a letterbox leaves cost a single instruction: half the runs on flat art, a quarter on a picture with a large area of one tone, and at the same `quality` a finer grid, since the budget then goes on the detail that is actually there ([Images on the panel](docs/user/actions.md#images-on-the-panel)).
- Editor: badges, count bubbles, the repeat count and the item type chip take their own type step one below the caption — `--haui-text-badge` at 11px — so a pill sits inside the row's text instead of competing with the meta line beside it ([Visual foundations](docs/develop/frontend-visuals.md#text-sizes)).
- Editor: the inventory footer's update and integration-version figures line up at the card's end, the way the events footer's actions close the card beside it
- Editor: **Live** ends by itself the moment the editor moves away from the preview it belongs to — switching device, opening the **Panels** view or Fleet, or any sidebar such as **Edit panel** — so an edit never runs against the panel on screen, and returning to the preview shows Simulated again instead of resuming a live session behind a sidebar ([The Live Preview](docs/user/editor/README.md#the-live-preview)).
- Display: both release TFTs report **1.1.3** — the camera gets its own page, a large picture area between two columns of mode buttons in landscape and above the row of them in portrait, so the info page keeps its own text area; the landscape media page gives the cover art a 120 px square above the transport row, every slider knob is 10 px wide, the spinner draws the sprite sheets at their new picture ids, and every solid page carries its generated theme code in `Preinitialize` — so a panel installs the display file once through the ordinary update ([Editing the HMI](docs/develop/nextion-editor.md)).
- Repo: the integration manifest names its Home Assistant category — *DIY & makers → Boards & hardware interfaces*, the one the ESPHome integration sits in — so the integration is filed where its firmware lives instead of under no category at all, and the HACS validation no longer warns about it.
- Display: the **Modern** background — the System page's own backdrop, and `modern` wherever the *Background* option names it — is redrawn in the soft-glow style of the newer glow tiles: a dark navy with a cool light rising from the low-left, a warm ember high-right, a dot texture in two corners and no dimming on the way from its source picture, replacing the faceted polygons, with the spinner frames re-rendered onto it ([Editing the HMI](docs/develop/nextion-editor.md)).
- Display: the **Spring**, **Summer**, **Autumn** and **Winter** backgrounds are redrawn as distinct soft-glow scenes — blossoms over a dusk meadow, a sail on a warm evening coast, autumn canopy over layered hills, and moonlit alpine ridges — replacing the paper-cut illustrations while keeping the dark text palette ([Editing the HMI](docs/develop/nextion-editor.md)).


### Fixed

- Editor: the selected panel's Home and Idle toggles and its Edit, Duplicate and Delete buttons take a row each when their labels no longer fit beside each other, and a label wraps inside its own chip as a last resort, so a longer translation or a larger text size no longer pushes the label out of the card.

- Preview: replay confirmed image and camera updates for late viewers, preserve unrelated drawings during repaints, and keep stale page acknowledgements or reconnects from clearing or restoring the wrong screen ([Preview](docs/develop/preview.md)).

- Camera: show the first snapshot in progressively finer layers, recover from lost draw reports, and avoid repainting the scene when a sharper grid cannot fit.
- Camera: a stream pauses while the display is dark and paints the whole area again when it wakes, and a camera that stops answering is retried (slowing to one attempt every 30 s) instead of ending the stream — both used to leave the panel frozen on its last picture until the page was opened again.
- Camera: a dashboard card or thumbnail of a camera panel no longer sits on *Waiting for the camera* once the stream has run for a while — when the replay can no longer describe the area, the render asks the stream for a fresh whole picture and the next one carries it.
- Hub: a `fill` a page sends into the camera's rectangle now tells the stream that owns it, the way `show_image`, `clear_image` and a media cover already did — the picture is painted whole again instead of keeping the ghost of the wiped area.
- Hub: a still image is planned on the **finest** grid its run budget allows — the search probed only one way while the run count can rise as the grid coarsens, so a budget could land on a grid that was both coarser and dearer than one below it (at `quality: 200` a test photo was cell 10 where cell 6 cost fewer runs).
- Hub: two panels showing the same camera fetch and decode one snapshot between them instead of one each per frame, and a camera frame is planned on a copy of the stream's planner taken on the panel's worker rather than read while the worker may replace it.
- Hub: saving a camera panel while it is on the screen no longer freezes the video — the stop a page's cleanup asks for is only a request, and the start that keeps the running stream withdraws it, where before the scheduled stop landed on the stream the same turn had just kept, leaving the picture on its last frame with no stream and no placeholder; a TFT install now ends the stream before the display refuses its next frame, and no draw may be started into a transfer at all ([Panel Camera](docs/user/panels/panel_camera.md)).
- Hub: a `show_image`, a `clear_image` or a media cover drawn into the camera's rectangle makes the stream paint that rectangle whole on its next frame — one owner per rectangle, and any other writer tells it — so the picture no longer keeps a hole where the other program painted; the page replay is also bounded now, because a camera page never repaints its rectangle whole and every distinct fill a moving scene produced used to stay in it for the length of the stream ([Panel Camera](docs/user/panels/panel_camera.md), [Preview](docs/develop/preview.md)).
- Preview: a late Live viewer is never seeded with a composite of leftovers — when the replay can no longer describe the camera's area whole, the stream paints it for the viewer instead — and the Simulated preview now answers a draw slice with the same fence the panel sends, so it shows the busy display and the refused slice a real panel has ([Preview](docs/develop/preview.md)).
- Hub: a camera frame skipped because the display is still drawing no longer advances the stream's painted-image model; the next delta is planned against the frame that actually reached the panel.
- Panel: a camera page that is drawn again — a reload, a theme change, a second panel on the page — has its picture painted whole by the stream instead of replaying the frame the page remembers, and so does a picture the panel did not take whole (a slice it never took, one it refused twice, one another draw cut short): a delta is only true while the panel still shows what the stream painted, and nothing else ever cleared that rectangle again, so the page used to end up with changed rectangles over a picture that was no longer there ([Panel Camera](docs/user/panels/panel_camera.md)).
- Editor: a picture in the Simulated preview, the Live preview and a panel card is painted into one canvas instead of one element per rectangle — no white seam between scaled pixel rectangles either, which the crisp-edged SVG layer was working around — and a stream no longer makes the editor page sluggish: a 6 000-run picture held 6 000 nodes and the browser spent ~71 % of its time painting them, where it is now 14 nodes. A frame also paints only the rectangles it added to the picture instead of the whole picture again — a 100-rectangle delta used to repaint all 1 851 rectangles of the picture, and the canvas it painted into was recreated every frame — so a Simulated preview no longer flashes the picture whole on every frame; a picture sent again replaces the one under it instead of stacking on it, and a page re-render keeps a camera stream that had to coarsen instead of starting it again from a full paint ([Preview](docs/develop/preview.md)).
- Editor: the update triangle on the Device screen's selected device chip is as readable as the name beside it in a light theme — the mark takes the chip's label colour instead of the warning tone, which the blue fill left at 1.3:1
- Firmware: a page change stops a draw in flight instead of letting the rest of the image paint onto the new page — `goto_page` stops both draw scripts, clears the program and restores the pacer, and the hub drops its slice queue at the same point, so the band already on its way finishes on the old page and a report for the cancelled pass is ignored ([Pacing](docs/develop/nextion.md#a-draw-paces-itself-instead)).
- Firmware: a run the queue did not take now fails the slice instead of being counted as sent, so the hub re-sends the image once and a gap cannot be reported as success; the report also forgets a finished program, so a later buffer overflow cannot repaint a band of an image that is long done, and a retry stays one-shot ([Pacing](docs/develop/nextion.md#a-draw-paces-itself-instead)).
- Hub: `show_image` keeps two images in different rectangles on the page replay instead of deleting every earlier fill — a late editor viewer, a card render or a reconnect sees both; drawing over the same rectangle still replaces that image, and `clear_image` only removes what it covers ([Images on the panel](docs/user/actions.md#images-on-the-panel)).
- Hub: `show_image` refuses an empty `path` or `url` with a validation message instead of reading the `www` folder or fetching nothing, and an image that would decode to more than 16 million pixels is refused before it is decoded ([Images on the panel](docs/user/actions.md#images-on-the-panel)).
- Editor: a widget the hub updates over a drawn image now shows through it in the Live preview and the card replay — the image is split around the widget's rectangle and survives everywhere else, instead of covering every widget on the page; a touch only cuts it where the widget has a pressed look, so tapping a label or a hotspot leaves the picture whole ([Images on the panel](docs/user/actions.md#images-on-the-panel)).
- Hub: `show_image` re-sends an image once when the panel reports that it did not take every rectangle, instead of leaving the picture with the gaps that lost runs leave — and a panel whose firmware predates the acknowledged draw (`draw_format` 1) is sent slices of 64 rectangles instead of 8 000 characters, so the display can drain its receive buffer between them instead of overflowing it (which a detailed image of one-pixel-high rectangles does, leaving thin gaps and stray coloured strips), with one warning naming the old firmware ([Pacing](docs/develop/nextion.md#a-panel-that-drops-runs)).
- Release: a development build continues the version cycle the branch reports instead of falling back to the newest stable tag's next patch, so a cycle opened with `base: 0.6.0.dev0` keeps building `0.6.0.dev<run>` — the dispatch after it no longer publishes a *lower* version than the branch, and one that queued behind another build fast-forwards to the tip of `dev` before it derives its own ([Published development firmware](docs/develop/release.md#published-development-firmware)).
- Release: a development build never publishes a version that orders below a dev release already tagged — the `X.Y.Z.devN` tags are a floor under the cycle, the way the newest stable tag's next patch already is, so the newest dev build is the highest version in Home Assistant, in the hub's **Development** channel and in the GitHub release list instead of reading as an older release that is never offered as an update — and the branch reports the `0.6.0` cycle again, which the bug had reset to `0.5.9` ([Published development firmware](docs/develop/release.md#published-development-firmware)).
- Hub: `show_image` sends the run format the panel's firmware reports (`draw_format`, new in the handshake) instead of always the base-36 one — a panel on firmware that predates the packing refused every run and drew nothing at all while the editor's preview showed the image, so the wire format is negotiated now and such a panel is sent the `fill` instructions themselves ([Images on the panel](docs/user/actions.md#images-on-the-panel)).
- Editor: a Simulated preview's states end with the preview itself — leaving it for another device, the **Panels** view, Fleet or a sidebar, or closing the browser tab, drops them instead of leaving them on the device's virtual app for the next ten idle minutes, where a card render drew a simulated state as the panel's own; **Reset sandbox** in the Diagnostics card still does the same while the preview stays open ([The Live Preview](docs/user/editor/README.md#the-live-preview)).

## [0.5.8] — 2026-11-27

### Added

- Hub: **Configure** on the NSPanel HAUI integration card opens the hub's own settings — the **Hub name** Home Assistant shows for the integration, and the **Default time format**, **Default date format** and **Default locale-aware date layout** every panel inherits while its own format is **Default** — so a hub can be renamed and its display defaults changed after setup without opening the editor, and per-panel settings stay in the editor ([Hub settings](docs/user/hub-settings.md)).
- Editor: the Device screen's **Updates** sidebar offers **Repair display** under the installed versions — after a confirmation the hub installs the release's minimal repair TFT for the panel's display model and then the TFT this firmware needs, so a display that stays blank, sits on **Waiting for Initialization** or never finishes the 11 MB file is recovered from the editor instead of a Nextion Editor session ([Repair display](docs/user/editor/device.md#repair-display)). The action, the manifest's `repair` block and both repair TFTs ship together — a one-page Editor project per display model at about 465 KB, a twenty-fifth of the normal file — so a release publishes the block and the sidebar offers the repair ([The repair TFTs](docs/develop/nextion-editor.md#the-repair-tfts)).

### Changed

- Display: both release TFTs report **1.1.0** where they reported 0.4.8, and the firmware requires that version, so every panel installs the display file once through the ordinary update — the pages, widgets and scripts are unchanged, only `system.tftVersion` moved, so a repaired display ends on the same number an ordinary install does and the repair file (`1`) stays distinct from the release file ([Display repair](docs/develop/update-process.md#display-repair)).
- Editor: one type role per text, so the editor stops drifting — badges, count bubbles, the repeat count and the item type chip are one quiet pill look (12px, text weight, no uppercase) instead of 10, 12 and 13px with weights from 400 to 600; a value is 13px at 500 everywhere (Fleet's footer figures, the tile values, the event scope) and secondary text 12px at 400; the name a row or card is listed by takes a new 14px step between a value and a card title — a Fleet card's device name, an inventory row's device, a panel row, an item row, the dashboard card's device — while the name of a choice inside a control stays on the 13px value step; buttons and menu items take the 13px text step instead of inheriting the body step; and the eyebrow step is one recipe (10px, 600, `.05em`, uppercase). The whole ladder also sits one step below Home Assistant's own type — body text 15px to HA's 16px, card titles 15px, names and values 13px — so the dense screens read a little tighter at every depth, and `check_frontend_styles.py` now refuses a raw or off-scale size, half an eyebrow, 600 or tracking outside it, and a pill that resizes its own text ([Visual foundations](docs/develop/frontend-visuals.md#text-sizes)).
- Editor: the screens' content column stops at 1440px and centres instead of stretching across a wide monitor — Fleet's cards and device table and the Device screen's workspace and side stack keep their proportions, while the titlebar and the footer stay full-bleed ([Editor](docs/user/editor/README.md)).
- Editor: a card's header and footer bands are a quiet neutral step instead of the theme's heavy grey bar — one `--haui-surface-band` token mixes 6% of the theme's text colour into the card ground, so Fleet's inventory and events cards, the Device screen's workspace strip, the sidebars' title strips, the panel groups and every card heading open and close a card on the same neutral note, in light and dark themes alike, and a theme change moves all of them at once ([Editor](docs/user/editor/README.md)).
- Editor: Fleet's two overview cards now close with a footer — the inventory's **Updates** and **Integration version** figures sit under the device table instead of beside its title, as one line of `label value` runs that never wraps, and the update button keeps the title's row at its end on a phone instead of dropping to a row of its own; **Latest events** keeps **Reset**, **Last 24 hours** and **Logs** under the timeline instead of on its title line, so both headers stay short and the actions stay at hand ([Editor](docs/user/editor/README.md)).
- Editor: Fleet's two overview cards now read title then value the same way — **Latest events** carries the window it covers beside its title, right after the count, where **Last 24 hours** or **Since 14:32** used to sit in the header's bottom corner, so its second line is the device scope alone, exactly as the inventory heads its own card with **connected / total** and the sentence under it ([Editor](docs/user/editor/README.md)).
- Docs: the display-side script cleanup is recorded as shipped instead of pending — both TFTs (1.1.0) already carry it and recompiling the committed HMIs reproduces them byte for byte — and [Editing the HMI](docs/develop/nextion-editor.md#compiling-a-tft) now walks through turning an `.HMI` into a `.tft` in the Nextion Editor: the two steps that make a compile, the `Component overlap` warnings that are by design, and the artifact check that proves a TFT belongs to its source ([HMI event scripts](docs/develop/nextion-scripts.md#cleanup-applied)).

### Fixed

- Editor: reordering works by touch — a finger or a pen on a grip now drags a Fleet card or row, a panel row, an item or a swipe, where mobile Safari and Chrome start no HTML5 drag and the grip did nothing at all; the same drop markers show as for a mouse, panels still cross between Navigation and Hidden in one drop, the click a drag ends with no longer selects the row it landed on, and a grip held near the edge of a long list scrolls it ([Editor](docs/user/editor/README.md)).

## [0.5.7] — 2026-11-27

### Added

- Editor: the Device screen's side stack opens **Logs** for the device shown, between **Themes** and **Updates**, so a device's log lines no longer need the fleet overview ([Editor](docs/user/editor/README.md)).
- Editor: the device's **Diagnostics** card names the **Display link** — the UART baud the panel runs at, 921600 bps with a current TFT and lower with an older one — in the Versions tile and in **Copy report**, so a panel that fell back to a slow display link is visible without the ESPHome log ([Editor](docs/user/editor/README.md)).

### Fixed

- Display: the boot baud scan now recovers a display that stays silent instead of giving up for the rest of the boot — the probe re-enables the display's command returns (a just power-cycled Nextion answers nothing without it), a failed scan leaves the link at 115200 rather than at a rate nothing answers, and the scan is retried three times a minute apart. A panel that sat on the TFT's **Waiting for Initialization** page is brought back by a firmware update in the meantime; this keeps the scan from needing one.
- Display: a **TFT install** the display cannot hold at 921600 bps is retried once at 115200 bps — the panel power-cycles the display first, because a failed transfer leaves it waiting for data, and reports the install as failed only if the retry fails too; a download or heap error is not retried, since another transfer would not fix it ([Troubleshooting](docs/user/troubleshooting.md#the-panel-refuses-every-tft-upload)).
- Display: a failed boot scan now keeps its 115200 bps fallback for the retries instead of switching back to the rate nothing answered at, so the fallback gets the window it exists for ([Display baud](docs/develop/esphome.md#display-baud)).
- Editor: a fact keeps its reading on its label's line. The tile card is wide enough for the widest translation's label beside a reading such as **921600 bps**, and a label that still does not fit wraps instead of pushing the reading onto a line of its own, so **Diagnostics -> Versions** shows **Display link** on one line ([Editor](docs/user/editor/README.md)).
- Firmware: the vendored `nextion` patch resolves from the directory the package was fetched into instead of from `master`, so a build compiles the patch that shipped beside its own YAML — a panel installed from `dev` used to stop at `no member named 'tft_upload_display_fault'`, and no `ref:` is left to drift from the package or to serve a stale component cache ([Troubleshooting](docs/user/troubleshooting.md#esphome-stops-with-couldnt-find-remote-ref)).
- Update: the TFT version check logs `Checking installed version` once per check instead of twice when the display has already reported its version, so the line whose `installed=` is empty is the only one that means the display told the hub nothing ([Troubleshooting](docs/user/troubleshooting.md#the-panel-refuses-every-tft-upload)).
- Hardware buttons: a button assigned a scene, script, button, lock, vacuum or input select now runs that domain's own action instead of sending a `toggle` the domain does not provide, so a scene on a hardware button with its relay off activates instead of failing with a Home Assistant service error ([Hardware buttons](docs/user/editor/device.md#hardware-buttons)).
- Grid: a tile's power button sends `turn_on`/`turn_off` only to a domain that has them; a scene, script, button, lock, vacuum or input select runs that domain's own action, so a lock tile's power button locks and unlocks instead of failing with a Home Assistant service error ([Grid](docs/user/panels/panel_grid.md#colors)).
- Editor: a failure above the **Fleet** inventory is now red like every other failure in the editor instead of amber, so a status refresh that failed no longer reads as a warning; the refresh failure is still announced politely rather than as an alert ([Editor](docs/user/editor/README.md)).

### Changed

- Editor: the Device screen's **Themes**, **Logs**, **Updates** and **Backups** buttons no longer take four full-width lines on a narrow screen — two per line below 980px and one row of icon tiles on a phone, where the value each one showed takes no room and stays in its name for a screen reader ([Editor](docs/user/editor/README.md)).
- Editor: the Fleet inventory's title and device count stay visible on phones, with update and integration-version labels beside their values in a compact two-column strip instead of crowding the header's right edge ([Editor](docs/user/editor/README.md)).
- Editor: every card heading now sits on the soft surface, one step above its body — **Device inventory**, **Latest events** and **Discovered Devices** on Fleet, the Device screen's workspace strip and its side cards, a sidebar's title strip and the panel groups inside it — so a card reads title band then content on every page instead of one flat ground ([Editor](docs/user/editor/README.md)).

- Display: both TFTs (version 0.4.8) now boot the Nextion at 921600 bps, and the firmware starts its UART at the same rate, scanning down only for an older or stock TFT; there is still one TFT per display model, and existing panels get the faster link with their next display update. A display install moves the same 11 MB over that link, so the file spends about two minutes on the wire instead of about seventeen ([Display baud](docs/develop/nextion.md#display-baud)).
- Display: a page paints its body widgets' theme foreground from four `Program.s` globals in the TFT's Preinitialize code instead of from one hub command per widget, so opening a row panel sends 24 commands fewer and opening a grid panel 6 fewer; a TFT older than 0.4.7 keeps the hub's per-widget colours ([Design](docs/develop/design.md)).
- Release: `dev` is the integration branch again and `master` stays stable-only and is the repository default, so a clone and any link without a ref read released code while a **Development** firmware build carries unreleased code, and a stable release still arrives through a promotion pull request and a `vX.Y.Z` tag ([Release process](docs/develop/release.md)).
- Repo: GitHub's source archives leave out `nextion/`, so a HACS or Marketplace install downloads ~15 MB instead of ~74 MB; the raw TFT URLs, the release assets and a fresh clone are unchanged, and git already delta-compresses successive HMI and TFT revisions, so a history rewrite would save little ([Release process](docs/develop/release.md#guardrails-and-known-gaps)).
- Editor: a **Scan** that fails and a **Device status could not be refreshed** notice read as banners above **Device inventory** instead of a line of red text under the device carousel, and the failed status keeps its polite announcement ([Editor](docs/user/editor/README.md)).
- Editor: the Fleet inventory card ends with its device table — the bar of one coloured segment per device and its hover tip are gone, since every row already carries its device's connection icon and a selected row names it ([Editor](docs/user/editor/README.md)).

## [0.5.6] — 2026-11-23

### Fixed

- Firmware: the vendored Nextion override is fetched from `master`, so building your own firmware works again — every ESPHome build of the package used to stop at config validation with `couldn't find remote ref dev`, because 0.5.5 deleted that branch ([Troubleshooting](docs/user/troubleshooting.md#esphome-stops-with-couldnt-find-remote-ref)).
- Docs: the README images and links name `master` instead of the deleted `dev` branch, so the HACS and Marketplace listing shows its screenshots again ([README](README.md)).
- Editor: the footer's **Documentation** link opens the published docs instead of the deleted `/dev/` site, which answered 404 on a development build.

## [0.5.5] — 2026-11-23

### Changed

- Release: `master` is the only long-lived branch. A release is a pull request merged plus a `vX.Y.Z` tag; the post-release sync, `release/X.Y.Z` preparation on a second branch, `make release-preflight` and `publish_stable.py` are gone, and a development build reports its version through `esphome -s` instead of committing it, so no workflow pushes to a branch ([Release process](docs/develop/release.md#published-development-firmware)).
- Device: a **Development** firmware build no longer changes the integration's installed version — it carries its own version in the image, so a panel on the **Development** channel updates firmware and display while the integration stays on the last stable release ([Release process](docs/develop/release.md#published-development-firmware)).

### Fixed

- Display: the hub holds every display command while a TFT install is in flight, so a page switch, a timer or a notification can no longer be written into the transfer; the panel stops acknowledging pages during an upload, which used to make the page-ack timeout redraw the whole panel into it ([Troubleshooting](docs/user/troubleshooting.md#the-panel-refuses-every-tft-upload)).

## [0.5.4] — 2026-11-23

### Breaking changes

- Firmware: the **Display Model** config entity is a `select` with **Landscape** / **Portrait** instead of a `0`/`1` number, so the panel's device page offers a dropdown; `number.<device>_display_model` becomes `select.<device>_display_model` ([Upgrading](docs/user/update.md#display-model-is-a-dropdown)).
- Display: `nspanel_haui.update_tft` raises with the hub's reason when a TFT install does not start — no matching device, updates off, an install already running, an unusable URL — and answers with the update state, where it used to return as if it had started and only log the refusal. It also installs the URL on a panel that has not handshaked yet, instead of deriving a manifest install ([Updating](docs/user/update.md#if-something-goes-wrong)).

### Changed

- Editor: **Backups** says what an **Import** and a **Copy to other devices** replace in a warning banner instead of a line under the buttons ([Backups](docs/user/editor/README.md)).
- Editor: the connection segments at the foot of the Device inventory name their device and state in a popover on hover or focus, instead of the browser's own tooltip ([Editor](docs/user/editor/README.md)).
- Editor: the **Updates** sidebar opens the install picker for a display or firmware update above the **Update settings** card instead of at the sidebar's foot, so the choice sits with the versions and installs it belongs to ([Updates](docs/user/update.md)).
- Editor: the **Device inventory** header shows its pending updates and integration version as toned figures — a green check when nothing is waiting, an amber download when one is, and a warning tag while the panels report different versions — in the diagnostics tiles' type (13 px muted name above a 14 px/500 value), so the value reads first without growing the strip.
- Release: the release workflow merges the release into `dev` and `dev` into `master` once it published, so both branches end on one commit instead of a manual merge-back ([Release process](docs/develop/release.md)).
- Device: the **Page settle delay** default drops from `0.1` to `0.05` s, halving the wait before a new page is drawn; the display's page ack already means the page is active, so the delay is only a margin ([Device settings](docs/user/editor/device.md)). A device that already stores `0.1` keeps it until it is changed in the editor.
- Logging: the hub logs each ESPHome command chunk at **Debug** instead of **Info**, so a ticking page no longer writes about a line per second to the Home Assistant log.

### Fixed

- Firmware: the panel draws fast again — opening a panel and paging inside one. The component phase is gated on `esphome: loop_interval` (ESPHome's default is 16 ms) and the Nextion pacer sends one command per phase, so `command_spacing: 2ms` was really 16 ms per command; opening a panel (112–156 commands) took 1.8–2.5 s and a paging step 0.4–0.5 s, and a full command queue needed longer to drain than its 8 s stale age, so the tail of a heavy render was dropped unsent and left stale widgets. The firmware runs the loop every 2 ms again ([Nextion component](docs/develop/nextion.md#command-pacing-costs-one-component-phase-per-command)).
- Display: a TFT install from a URL or a local file is no longer skipped in silence. It starts on a panel that has not handshaked yet instead of turning into a manifest install, a second request names the install that is still running instead of answering as if it started, and `nspanel_haui.update_tft` raises with the hub's reason (and answers with the update state) instead of only logging it ([Updating](docs/user/update.md#if-something-goes-wrong)).
- Firmware: the panel reports a failed TFT upload with its reason as soon as the upload ends, so the hub fails the install within seconds instead of after its 20-minute timeout. Home Assistant also checks a TFT URL first — a `404`, a server that ignores range requests, an oversized file — and refuses it before the panel is sent off to download it ([Troubleshooting](docs/user/troubleshooting.md#tft-upload-failures)).

## [0.5.3] — 2026-11-21

### Breaking changes

- Panels: the Clock, ClockTwo and Weather **Background** names a picture — **Dark Color** (default), **Light Color** or a decorative one — instead of **Use color scheme**, which those pages never drew; a stored `scheme` falls back to the theme's plain fill ([Upgrading](docs/user/update.md#background-pages-draw-a-picture)).

### Added

- Dashboard card: a read-only status area — connection, display state, queued notifications, firmware and TFT versions, button lights — and `fleet`/`device` modes with `big`, `small` or `status` display modes ([Dashboard Card](docs/user/dashboard-card.md)).
- Dashboard card: the editor stores the panel's device id, so renaming the device no longer breaks cards, and offers a disabled device marked *(disabled)*.
- Dashboard card: `scale` draws the big preview at 20–100 % of the card's space.
- Editor: **Copy to other devices** writes device settings, panels or update settings onto other devices ([Backups](docs/user/editor/README.md)).
- Editor: **Quick start** builds a room, whole-home, status, entry/alarm, kitchen-timer or guest-Wi-Fi setup from an area's entities ([Quick Start Guide](docs/user/get-started.md)).
- Editor: the quick start's second step selects the **Theme** the created pages draw in ([Quick Start Guide](docs/user/get-started.md)).
- Editor: the panel detail card sets and unsets the **Home panel** and **Idle panel** roles ([Panel Configuration](docs/user/editor/panels.md)).
- Device: the firmware reports a `hub_api_version` contract version and the hub compares its major part, logging a mismatch and exposing `hub_api_compatible` in the diagnostics instead of guessing at an unknown payload; firmware that predates the field stays compatible ([Version compatibility](docs/user/version-compatibility.md)).

### Changed

- Dashboard card: `mode` is `fleet` or `device` and `display_mode` is `big`, `small` or `status`; saved `overview`/`home`/`live`/`tile` cards keep their view, and `devices`/`focus_mode` are unused ([Dashboard Card](docs/user/dashboard-card.md)).
- Dashboard card: the compact preview stacks above the status on narrow cards, and a disabled device keeps its render.
- Editor: **Add panel** drops **Start from a template** and its endpoint; a panel starts from a type, a built-in popup or a copy ([The Panel List](docs/user/editor/README.md)).
- Editor: the Add panel and Quick start catalogs share one card style.
- Editor: the Device screen orders **Themes**, **Updates** and **Backups**.
- Editor: the device settings order **General**, **Home & idle**, **Hardware buttons**, **Screen buttons**, **Screen**, **Sounds**, **Gestures** and **Advanced**.
- Editor: the Panels group counts share one soft block.
- Editor: the panel detail card uses equal-width action columns with **Delete** across the row.
- Editor: every panel of the idle sequence carries a marker in the Panels list ([Panel Configuration](docs/user/editor/panels.md)).
- Editor: the quick start uses role icons, speaks of the idle panel and puts needs and warnings in one banner ([Quick Start Guide](docs/user/get-started.md)).
- Editor: the quick start fills grid and row pages with available entities and creates them even when empty ([Quick Start Guide](docs/user/get-started.md)).
- Editor: Backups lays **Export** and **Import** side by side, and **Copy to other devices** has select all, clear and a status line ([Backups](docs/user/editor/README.md)).
- Editor: the titlebar stays pinned while a screen scrolls, and device sticky panels pin below it.
- Editor: **Latest events** keeps the moment **Reset** set across a reload, and **Last 24 hours** clears it ([Logs](docs/user/editor/README.md#logs)).
- Editor: an internal item's **Action** and **Action data** use Home Assistant's wording instead of **Service** and **Service data** ([Items](docs/user/editor/items.md#internal-items)).
- Development: `make check` runs the frontend, version, icon and translation checks, `make screens-check` verifies the screen overview, and the git hook refuses unstaged layout inputs ([Development](docs/develop/development.md)).
- Development: `make esphome-compile` and `make esphome-size` compile a firmware config and fail an image that fills 92 % of its app partition ([ESPHome](docs/develop/esphome.md)).
- Release: `make release-preflight`, `scripts/release/publish_stable.py`, uv-based CI installs and a separate screen-render job ([Release process](docs/develop/release.md)).
- CI: a pull request that touches the firmware compiles it, every action is pinned to a commit SHA with `persist-credentials: false`, and Dependabot, a shellcheck job and a Conventional Commits PR-title check guard the repository ([Release process](docs/develop/release.md)).
- Firmware: the dev, universal and hub-managed configs share `esphome/nspanel_haui/packages.yaml` ([ESPHome](docs/develop/esphome.md)).
- Firmware: local builds need ESPHome 2026.11; the vendored `nextion` patch is that release plus the TFT upload retry fix ([ESPHome](docs/develop/esphome.md)).
- Docs: the developer guide is rewritten and grouped by subsystem — General, ESPHome & display, Frontend and Releases; the live preview and the dashboard card transport move to their own page, and the upgrade history to `docs/develop/upgrading.md` ([Development setup](docs/develop/development.md)).
- Docs: **Editor architecture** is split into the overview, **Screens**, **Sidebars and overlays**, **Visual foundations**, **Components** and **Tests**, one page each ([Editor architecture](docs/develop/frontend.md)).
- Docs: feature ideas live in `FEATURE_WISHLIST.md` ([Feature wishlist](FEATURE_WISHLIST.md)).
- Docs: the user guide is reorganised into Setup, Editor and Panel types; the editor guide lives in `docs/user/editor/` and absorbs the device description ([The Editor](docs/user/editor/README.md)).
- Docs: **Version compatibility** lists which Home Assistant, integration, firmware and display versions work together ([Version compatibility](docs/user/version-compatibility.md)).
- Docs: **Back up the stock firmware** keeps the Sonoff firmware and its eWeLink credentials before the first flash ([Back up the stock firmware](docs/user/backup.md)).
- Docs: the user guide shows the editor screens, the panels' popups and the dashboard card in screenshots ([The Editor](docs/user/editor/README.md)).
- Docs: the README's quick start, editor and panels banners are captured from HTML pages like the hero, next to the editor screenshots and the dashboard card captures, and `tests/test_docs_images.py` fails a page that points at a missing picture ([Design Guidelines](docs/develop/design.md)).
- Docs: the generated **Screens overview** and **Icons cheatsheet** are pages of the guide, embedded in the site so the navigation stays, and still open full screen in a new tab ([Screens Overview](docs/user/screens.md), [Icons Cheatsheet](docs/user/icons.md)).
- Docs: the services reference is the **Actions** page at `user/actions.html`, following Home Assistant's name for them; every link points there ([Actions](docs/user/actions.md)).
- Repository: `CONTRIBUTING.md`, `SECURITY.md` and issue forms state how to contribute, report a vulnerability and file a bug ([Contributing](CONTRIBUTING.md)).
- Licensing: `licenses/` carries the notices for Roboto, Material Design Icons and the bundled Nextion and ESPHome tooling ([Third-party notices](licenses/README.md)).

### Fixed

- Panels: light themes keep body text and control icons readable ([Color Themes](docs/user/editor/themes.md)).
- Panels: a grid tile whose item is on lifts off the page in the selected theme's on color and draws its power button in that color, so the tile follows a theme change instead of the theme the setup was created in; the store clears the theme colors a quick start wrote into grid tiles ([Panel Grid](docs/user/panels/panel_grid.md)).
- Editor: a saved theme's new colors reach the panel previews and the dashboard card, instead of every card keeping the old palette until the editor is reloaded ([Color Themes](docs/user/editor/themes.md)).
- Panels: a collapsed single-navigation header button stays correct when a page updates it ([Panel QR-Code](docs/user/panels/panel_qr.md)).
- Panels: the quick start's word clock no longer stores the muted text tone for unlit letters ([Panel Clock Two](docs/user/panels/panel_clocktwo.md)).
- Editor: the quick start's configurations and the pages they create use the editor's language ([Quick Start Guide](docs/user/get-started.md)).
- Editor: the log level, display model and time/date format choices and the dashboard card's picker description use the editor's language, and German, French, Dutch and Polish cover every editor string ([Editor](docs/user/editor/README.md)).
- Panels: ClockTwo's top-left dot keeps its background patch on light pages ([Panel Clock Two](docs/user/panels/panel_clocktwo.md)).
- Panels: an empty or unresolved **Background** falls back to the theme's plain fill ([Background pages](docs/user/editor/themes.md#background-pages)).
- Panels: the Clock's entity buttons follow a light or decorative background's palette ([Panel Clock](docs/user/panels/panel_clock.md)).
- Editor: deleted panels no longer count as **Home panel** or **Idle panel** ([Panel Configuration](docs/user/editor/panels.md)).
- Editor: **Home & idle** says a device has no panels yet instead of two empty pickers, and its tile names it ([Panel Configuration](docs/user/editor/panels.md)).
- Editor: deleting or moving a panel drops its stale key from the device's **Home & idle** settings ([Panel Configuration](docs/user/editor/panels.md)).
- Panels: a keyless panel no longer breaks a device's header buttons.
- Editor: **Themes**, **Home & idle** and **Gestures** name themes and untitled panels instead of keys.
- Editor: the device carousel fades an edge only when more cards follow.
- Dashboard card: a new card starts with all devices, missing selections are prompted, failed lists retry and hub errors read as sentences.
- Editor: **Add** on an empty list option adds a plain entry or opens the entity picker ([Media Panel](docs/user/panels/panel_media.md)).
- Dashboard card: the status area shows firmware and TFT versions for home and live sessions.
- Device: an `unknown` display model or brightness no longer aborts start-up.
- Device: the display model defaults to `eu`.
- Editor: a failed render shows the hub's message as `role="alert"`.
- Editor: a render racing the virtual app's stop ends as a plain hub answer.

## [0.5.2] — 2026-11-17

### Breaking changes

- Themes: the **Theme variant** device setting is gone; a theme's own page background picks its weather, alarm and climate icon palette, and the Theme sidebar edits only that one ([Upgrading](docs/user/update.md#the-theme-picks-its-own-icon-colors)).
- Schedule: an entry with its own dimmed brightness needs the device's **Brightness dimmed**; stored devices without one get 20 % ([Upgrading](docs/user/update.md#a-schedule-entry-that-dims-needs-a-dimmed-brightness)).

### Added

- Themes: six colorful predefined themes — **Midnight**, **Ocean**, **Forest**, **Sunset**, **Violet** and the light **Sky** — beside Dark, Light, White and Black ([Themes](docs/user/editor/themes.md)).
- Dashboard card (`custom:nspanel-haui-card`): a device's home panel or live screen on any dashboard, view-only, for every signed-in user ([Dashboard Card](docs/user/dashboard-card.md)).
- Editor: a dashboard device is selected from its **Device inventory** row or the name strip under its card, with both highlighted.
- Editor: the device settings open on a grid of tiles, one per group and naming what it holds, with the group's page behind it ([Device Settings](docs/user/editor/device.md#device-settings)).
- Editor: the schedule sits in the **Screen** group, **Schedule** and **Gestures** are settings groups, and the device theme choice is in **General** ([Schedule](docs/user/editor/device.md#schedule), [Gestures](docs/user/editor/device.md#gestures)).
- Editor: **Move to…** moves a panel to another device and keeps its key unless that device uses it ([The Panel List](docs/user/editor/panels.md#panel-list)).
- Editor: item name, icon, color and value switch between **One value** and **Per state** rows instead of typed JSON ([Values that depend on the state](docs/user/editor/items.md#values-that-depend-on-the-state)).
- Editor: **Latest events** names its selected device and window, with **Reset** and **Last 24 hours** ([Logs](docs/user/editor/README.md#logs)).
- Editor: the **Device inventory** closes with one connection segment per device ([Managing devices](docs/user/editor/README.md#device-cards-and-inventory)).

### Changed

- Editor: entity pickers, item lists, **Diagnostics** and preview tooltips use the entity's own name without the device prefix.
- Editor: every switch sits at the right end of its row.
- Editor: schedule, gestures and theme are part of the device settings draft, while **Backups**, **Updates** and **Themes** remain sidebars ([Backups](docs/user/editor/README.md#backups)).
- Editor: the **Backups** sidebar replaces the **Backup** card ([Backups](docs/user/editor/README.md#backups)).
- Editor: **Themes** opens below **Connection** and **Diagnostics**, **Updates** above it, and both name what they hold and span the width.
- Editor: **Connection & device** is now **Connection**.
- Editor: a selected device scopes **Latest events** and **Logs**, otherwise both list every device ([Logs](docs/user/editor/README.md#logs)).
- Fleet: **Latest events** lists only the last 24 hours' warnings and errors; the full log is the **Logs** sidebar.
- Editor: one type scale at Home Assistant's sizes, following its font-size setting.
- Editor: panel group headings say **Navigation (1 panel)**.
- Editor: **Update settings** uses a channel list and switches like the other forms.
- Editor: device settings show one field per row with pickers at the right edge.
- Updates: an offered update is one installed-to-new badge, the integration version moved to the **Check for updates** row, and narrow sidebars shorten labels.
- Fleet: the **Device inventory** summary strip matches the **Latest events** header height.
- Fleet: the dashboard fills wide windows, a long inventory scrolls under its headings, and **Latest events** takes its height.
- Fleet: the device carousel always fades its right edge and dashed outlines fill leftover width.
- Device screen: **Connection** and **Diagnostics** use smaller values with the Wi-Fi bars at the tile's edge.
- Fleet and device: Wi-Fi strength stays visible offline, the dot keeps connection state, and uptime is green while online and stable.
- Editor: **Hub version**, **Hub log** and **Hub details** are now **Integration version**, **Integration log** and **Integration details**.
- Panels: the **Home panel** and **Idle panel** tiles show role icons and stack on narrow cards.

### Fixed

- Schedule: an entry's dimmed brightness no longer stays after it ends.
- Schedule: saving **Auto display off** during an entry no longer overrides it, and removing the schedule restores it.
- Schedule: entries start on time on DST change and sunrise/sunset entries resume after polar night.
- Editor: the Home Assistant app's status bar takes the header colour.
- Editor: with **Show entities in the preview**, Row panel buttons, switches and sliders show their entity.
- Editor: with **Show entities in the preview**, hardware buttons show the entity they switch.
- Editor: with **Show entities in the preview**, the Live preview names the entity under the mouse instead of erroring.
- Editor: with **Show entities in the preview**, unknown or unavailable entities are named too.
- Updates: withheld or refused firmware reasons and the "firmware is installing" notice are translated.
- Integration: the device holding a panel's notify and update entities is named after the panel.
- Updates: an unreadable manifest or missing check reads as the reason, not **Up to date**, and **Check for updates** shows release-list errors.
- Updates: an offline panel offers no **Install**, and the editor marks values as last read.
- Updates: a failed install clears when another firmware reconnects, and a second install is refused instead of started.
- Updates: the dashboard sees rollouts from other editors, finished rollouts can be dismissed, and disabled or reloaded devices are skipped.
- Editor: the dashboard meets WCAG AA contrast and screen readers hear headings, event levels, device cards, table columns and rollout changes.
- Fleet: event level dots use their tone instead of the dark text tone.
- Editor: icons in a tone keep the tone instead of a darker shade.
- Editor: tile fact cards keep long labels and readings inside their border.

## [0.5.1] — 2026-11-14

### Added

- Fleet: filter **Latest events** to the last 24 hours, with improved keyboard accessibility.

### Fixed

- Clock panel item buttons now open the configured item; Clock, Weather and Clock Two component IDs match the display layouts ([#97](https://github.com/happydasch/nspanel_haui/issues/97)).

## [0.5.0] — 2026-11-14

### Breaking changes

- Themes replace the color schemes: custom palettes live in a shared theme library, per-device `color_overrides` and `theme_overrides` are not converted, and hand-written config uses `theme_id` and `theme_variant`; the **Device Colors** sidebar is now the **Theme** sidebar on Preview ([Themes](docs/user/editor/themes.md), [Upgrading](docs/user/update.md#themes-replace-color-schemes)).
- A **Schedule** of entries (from/to as a time, or sunrise or sunset with an offset; sound, brightness, screen off and its duration) replaces the Day/Night profiles and the quiet hours; saved settings are not converted, and **Brightness** is a new device setting ([Upgrading](docs/develop/upgrading.md#050)).

### Added

- Editor: a Fleet/Device dashboard with linkable routes replaces the **Device Manager** and **Device Info** dialogs and the header's ⋯ menu ([Screens](docs/develop/frontend-screens.md#page-structure-and-navigation)).
- Fleet: scans for new panels when it opens, enables, disables and removes devices from their inventory row, and shows a summary strip (health, updates, versions, one segment per device), the device inventory and **Latest events**, the dated hub log of every device with repeated messages counted ([Screens](docs/develop/frontend-screens.md#fleet-screen-regions)).
- Device screen: a card of next actions (**Add panel**, the **Settings** cog, **Install update** while one is offered), the **Connection & device** card (uptime, Wi-Fi, current page, IP; opens **Updates**) and **Diagnostics** ([The Device Screen](docs/user/editor/README.md#device-view)).
- Diagnostics: the display state, the idle page countdown, the disconnects and late heartbeats of the last 24 hours, the current page's entities and the firmware and display versions; **Copy report** builds a bug report without entity ids or addresses ([Diagnostics](docs/user/editor/README.md#diagnostics)).
- Logs: a sidebar on the Device and Fleet screens, newest first and grouped by day, filtered by level or text, with warnings and errors tagged and a copy button for bug reports ([Device](docs/user/editor/device.md)).
- Themes: a shared library of predefined and custom palettes; the **Theme** sidebar edits their semantic and state-icon colors and imports or exports the library, and the device settings pick the device's theme from the same list, with **New theme**, **Export all** and **Import** ([Themes](docs/user/editor/themes.md)).
- Themes: every panel, including editable popups, can choose its own theme; an empty selection follows the device, and panel and item colors stay explicit overrides ([Panels](docs/user/editor/panels.md), [Themes](docs/user/editor/themes.md)).
- Schedule: any number of time windows (a time, or sunrise or sunset with an offset, also across midnight), each with sound, brightness, dimming and display-off settings ([Schedule](docs/user/editor/device.md#schedule)).
- Panels: search, inline rename, duplicate and copy from another device; a panel is reordered by dragging its grip (the row menu no longer has **Move up** and **Move down**), and the list shows only the popups the device extends.
- Panels: a selected row is described in the side column — its render (foldable, remembered per browser), type, key, group, item count, Home/Idle role and **Edit**, **Duplicate** and **Delete**; with no selection the card explains the panel groups and names the Home and Idle panels ([Panels](docs/user/editor/panels.md)).
- Add panel: collapsible groups (**Backgrounds**, **Entities**, **Grouping**, **Tools**, **Extend a popup**, **Copy an existing panel**) with a search; every type is previewed with sample entities and values, an entity popup with an entity of its domain, and a thumbnail enlarges on hover or tap ([The Panel List](docs/user/editor/panels.md#panel-list)).
- Add panel: eight starter templates under **Start from a template**, which open in the editor with the entities they need marked ([The Panel List](docs/user/editor/panels.md#panel-list)).
- Panel editor: each option is checked against its panel type (entity domain, required entity, number range, choices, item limit, color) in the editor and on the hub; a new or changed panel that breaks a rule cannot be saved, an unknown entity only warns, and older panels show **Check settings** ([The Panel Editor](docs/user/editor/panels.md#the-panel-editor)).
- Updates: an automatic firmware install waits 10 minutes first; the Updates sidebar can install it now, put it off by an hour or a day, or skip the version ([Update Process](docs/develop/update-process.md#firmware)).
- Updates: **Install updates** on Fleet installs one device at a time on the hub, stops at the first failure and can cancel the devices still queued ([Update Process](docs/develop/update-process.md#installing-every-device-one-at-a-time)).
- Updates: a running firmware or display install shows its step and an estimate of the time left in the Updates sidebar and on Fleet ([Update Process](docs/develop/update-process.md#progress)).
- Slovak: the display, the editor and the integration's dialogs are translated, and **Slovenčina** (`sk_SK`) is a device language with Slovak dates ([#94](https://github.com/happydasch/nspanel_haui/pull/94), [Device Configuration](docs/user/editor/device.md#general)).

### Changed

- Device settings: seven sections instead of nine — **General**, **Screen**, **Home & idle**, **Screen buttons & gestures**, **Hardware buttons**, **Sounds** and **Advanced** — whose rows open the **Theme**, **Schedule**, **Gestures** and **Updates** sidebars and show what each holds ([Device Configuration](docs/user/editor/device.md#device-settings)).
- Device settings: the extra idle panels (`idle_panel_extra`) are an ordered list to add, remove and reorder in **Home & idle**, beside the home panel ([Panels](docs/user/editor/panels.md#home-and-idle-panels)).
- Gestures: single swipes and multi-swipe sequences are one list, the device setting `gestures`: each gesture can step to the next or previous panel or open a panel, and saved `swipe_actions` and `gesture_sequences` are converted ([Gestures](docs/user/editor/device.md#gestures)).
- Editor: **Manage this device** on the Preview opens **Theme**, **Schedule** and **Gestures** in the sidebar (a full-screen page on a phone); **Schedule** and **Gestures** save with an explicit **Save** and use collapsible entry rows with summaries and counts, a new entry opening for editing ([Configuration](docs/user/editor/themes.md#choose-and-edit)).
- Editor: sidebars resize by dragging their edge; the panel editor pins its preview as a thumbnail once scrolled, previews unsaved edits, marks the field that cannot be saved and uses compact item rows ([The Panel Editor](docs/user/editor/panels.md#the-panel-editor)).
- Editor: field hints show only while the pointer rests on the field or keyboard focus is in it, floating over the form instead of taking space; touch screens keep them visible.
- Editor: cards and the preview no longer redraw on every state change, one status poll runs and pauses in a background tab, modules are cached, and the entity picker lists at most 100 matches.
- Preview: sounds and errors show as toasts, **Reset sandbox**, **Reset interaction** and **Redraw display** are in the expanded **Diagnostics** card, and a click on the **Current page** tile shows that page in the Simulated preview ([Controls](docs/user/editor/README.md#controls)).
- Preview: panel cards show their last render, kept in the browser, until the hub's new one arrives, instead of a placeholder after every reload ([The Live Preview](docs/user/editor/README.md#the-live-preview)).
- Display: the device's time and date formats apply to every panel: date, time, date-and-time, `input_datetime` and `event` entities and timestamp and date sensors show their state in them instead of as ISO text ([Device Configuration](docs/user/editor/device.md#general)).
- Display: the About page labels its versions **Integration** and **Firmware** instead of **HAUI-Version** and **YAML-Version**.
- Firmware: dimmed brightness is capped at the active full brightness, so a schedule entry with a low brightness cannot brighten the display when dimming begins.
- Updates: the Updates sidebar leads with one status (up to date, update available, installing, failed, or why no update fits) above the versions; its **Update settings** card shows the channel, how often to check (15 minutes to one week, or **Never**) and whether a new version waits for you or installs automatically, with the rest under **Advanced**, and each change saves by itself ([Update Process](docs/develop/update-process.md#editor-the-updates-sidebar)).
- Updates: a failed automatic firmware or display install is retried after **Wait between attempts** and stops after its attempt limit (3 by default), instead of retrying the firmware hourly forever and the display never ([Update Process](docs/develop/update-process.md#settings)).
- Updates: **Download firmware** and the `/api/nspanel_haui/firmware` endpoint are gone; download `nspanel_haui.bin` from the GitHub release.
- REST API: editor saves go to scoped endpoints for one device's settings or panels and to a device-order endpoint, and the whole-store panels route is read-only, so a save never touches another device and reordering does not reload the hub; `/api/nspanel_haui/color_schemes` is replaced by `/api/nspanel_haui/themes` ([Hub](docs/develop/hub.md)).
- REST API: the device status replaces `idle_page_active` with `idle_page`, renames `haui_version` and `haui_version_mismatch` to `integration_version` and `integration_version_mismatch`, and adds `display_state`, `connection_health` and `current_panel`; the `reset_interaction` endpoint is gone (the Live preview resets the timer), and hub log lines carry an ISO timestamp and the full level name.
- Translations: the editor strings are complete in English, German, French, Dutch and Polish, including the theme, schedule and gesture controls.
- Docs: the documentation is split into a user guide (`docs/user/`) and a developer guide (`docs/develop/`), so page addresses changed (`install.html` is now `user/install.html`); the user pages are rewritten in plainer language and **Custom Integration** is merged into [Installation](docs/user/install.md).
- Development builds: this cycle publishes `0.5.0.devN` instead of continuing the `0.4.8` patch line, and the Development Firmware workflow's version commit runs CI and deploys its screen overview to the dev docs, without a skip-CI trailer ([Release process](docs/develop/release.md#published-development-firmware)).
- Release checks: stable and development releases refuse a TFT that does not carry the configured `tft_version`, CI requires a `tft_version` bump when a compiled TFT changes as well as an HMI, and the redundant `verify_nextion.py` gate is folded into the layout spec checks and the test suite ([Release process](docs/develop/release.md#ci-gates-and-local-checks)).

### Fixed

- Unlock popup: the keypad takes the code again; since 0.4.5 it ignored every key, on the panel and in the preview, so a locked panel could not be opened.
- Hub: grid and row updates and light color drags run on the device's worker instead of a second thread, entity service calls reach Home Assistant in order, and a slow weather forecast no longer stalls the panel.
- Hub: a touch that recovers a lost page switch no longer leaves the page timeout armed to reload the page again 10 s later; a command the panel did not receive is sent again instead of being dropped as a duplicate; clearing the notifications closes an open notification list.
- Hub: every panel option, device setting and update setting has its default in one place (the panel type's option, `DEVICE_CONFIG`, `DEFAULT_CONFIG["update"]`); the pages and controllers no longer keep second copies, some of which had drifted from the declared default.
- Hub log: a panel's missing entity is warned about once, until it exists again, instead of on every render, which filled the log and pushed every other message out.
- Connection: a panel that reboots without the hub timing out first is reported disconnected before it reconnects (`nspanel_haui.connection_changed` fires `false`, then `true`), so the update and idle handling reset as after any other drop.
- Panels: a page no longer carries one panel's state into the next: the select popup forgets the previous popup's multiple selection and page, the unlock popup opens without the last code, light, weather and timer panels start from their own options, and a tap still being told apart from a swipe never reaches the next panel.
- Cover, climate, media and vacuum panels show their controls again when their entity comes back after being unavailable, instead of keeping them hidden until the panel is opened again.
- Light panel: the color marker no longer stays on the display after switching from the color wheel to another control.
- Idle page: saving while a later idle panel of the carousel is shown keeps it the idle page, so a touch still leaves it.
- Gestures: the last swipe of a gesture sequence no longer also runs its own swipe action, which navigated away from the panel the sequence had just opened.
- Updates: a check always answers the editor and the update entity, also for a release without a title or notes (which used to break the check); a firmware install never starts during a TFT upload, nor a TFT upload during a firmware install, even when one began while the other's files were fetched.
- Updates: a firmware or TFT install and the TFT release list always answer the editor and the update entity, also when they fail on the hub after fetching or when the device's app stops meanwhile, instead of leaving the request waiting forever.
- Updates: a working TFT install no longer shows the error of an earlier failed attempt in the update entity, and a TFT install or release list whose check a newer one replaced says so instead of acting on a manifest that may be stale.
- Update notices: the release notice and the firmware install notice are queued notifications, so they never replace a notification you are reading; they appear in the notification list and fire `nspanel_haui.notification`, and the install notice leaves the queue when the install ends ([Update Process](docs/develop/update-process.md#on-the-display)).
- Device settings: a **Date format** other than Default now takes effect; the default **Locale-aware date layout** overrode it.
- Device settings: a number field no longer snaps to its minimum (or loses an unfinished entry) while it is being edited.
- Editor sidebar: Tab and Shift+Tab stay inside the open panel editor or device settings instead of jumping to the close button or leaving the sidebar.
- Editor: a page left open across a Home Assistant restart that changed the editor reloads itself, instead of failing with "nspanel-simulator-frame has already been used" and showing a blank panel.
- Theme sidebar: built-in theme names are translated.
- Preview: the **Idle** control explains when the device has no idle panels instead of doing nothing.

### Contributors

Thanks to [@pikas1](https://github.com/pikas1) for the Slovak translation
([#94](https://github.com/happydasch/nspanel_haui/pull/94)).

## [0.4.7] — 2026-11-11

### Changed

- CI is consolidated into three workflows: `ci.yml` runs every push/PR gate
  (plus the nightly validators) and deploys Pages from a docs build made once
  per run, and the development build commits the version and the regenerated
  screen overview as one `[skip ci]` bot commit (`screens_only` regenerates the
  screens alone).
- Development firmware builds are dispatched manually instead of running on
  every `dev` push, so commits no longer publish a prerelease, push a bot
  version commit or regenerate the screens.
- The editor now runs on one observable store and one typed API client behind
  the existing views, with the v0.5 frontend architecture documented in
  `docs/develop/frontend.md`.
- The preview's idle control toggles the idle page: pressing it again wakes
  back to the panel it covered (or home) and restarts the interaction timer, in
  both Simulated and Live mode
  ([Configuration](docs/user/editor/README.md#the-live-preview)).

### Fixed

- Opening the Simulated preview starts the virtual panel over on its home panel
  with the real entity states, as switching back from Live already did.

## [0.4.6] — 2026-11-09

### Fixed

- The Marketplace no longer reports Home Assistant 2026.11.0 as too old:
  `hacs.json` declares the minimum as `2026.11.0`
  ([#90](https://github.com/happydasch/nspanel_haui/issues/90)).

## [0.4.5] — 2026-11-09

### Breaking changes

- Home Assistant 2026.11 is required; install and update through its
  Marketplace, which migrates HACS installs
  ([Upgrading](docs/develop/upgrading.md#045)).
- Firmware updates moved from the firmware to the integration's **HAUI
  Firmware** entity; panels on firmware 0.4.3 or older are updated once by hand
  ([Upgrading](docs/develop/upgrading.md#045)).
- Custom firmware builds are never offered the universal release image; the
  manifest and the device state name the build variant.
- The display TFT follows the firmware manifest; another release's TFT installs
  only **From URL**
  ([Upgrading](docs/develop/upgrading.md#045)).
- Native OTA is encrypted with the API key; the `ota_password` substitution is
  gone, and panels on 0.4 firmware need no migration install
  ([#81](https://github.com/happydasch/nspanel_haui/issues/81),
  [ESPHome](docs/develop/esphome.md#encrypted-native-ota)).
- The **Current Page** sensor moved to the firmware; delete the old integration
  entity ([Upgrading](docs/develop/upgrading.md#045)).
- The firmware drops the `haui_discover`, `req_device_info` and `req_reconnect`
  actions and the `use_relay_left`/`use_relay_right` events, which the hub
  never used ([Upgrading](docs/develop/upgrading.md#045)).
- The services raise an error when their `device` matches no running panel,
  instead of logging a warning and doing nothing
  ([Upgrading](docs/develop/upgrading.md#045)).
- The firmware drops the **Use Auto-Page** switch, **Timeout Page** number and `esphome.timeout` event; automatic page switching and each page's hold move to the hub. Empty Night idle keys no longer inherit Day; `use_auto_page`/`timeout_page` remain device settings.
- The `hub_idle_timeout` device setting is gone; the hub's own idle-page check replaces it ([Device Configuration](docs/user/editor/device.md#home-idle)).
- Update the integration first, then install matching firmware and TFT; mixed hub and firmware versions are unsupported ([Upgrade guide](docs/user/update.md#automatic-page-switching-moved-to-the-hub)).
- Notification `type` (`info`/`warning`/`critical`) is replaced by `icon_color` and `sound` on `nspanel_haui.send_notification`; the `nspanel_haui.notification` event carries both instead of `notif_type`, and the ESPHome `send_notification` action requires the two new variables ([Upgrading](docs/develop/upgrading.md#045)).
- Persistent notifications now open immediately on every path and may re-open over the idle page; the `critical`-only idle guard is gone ([Notifications](docs/user/actions.md#notifications)).

### Added

- Live preview in the editor: an interactive virtual panel run by the hub, in
  sandbox or live mode ([#85](https://github.com/happydasch/nspanel_haui/pull/85),
  [#86](https://github.com/happydasch/nspanel_haui/pull/86)).
- The live preview mirrors the device's queued notifications, read-only.
- Panel cards drawn by the hub: every card replays the hub's own render of its
  panel, unsaved edits included.
- [Screens overview](docs/screens.html) of every screen in landscape and
  portrait, regenerated after each dev build.
- [Development docs](https://happydasch.github.io/nspanel_haui/dev/) built from
  `dev`; the editor footer opens them on dev builds.
- Every popup can be edited; System, Blank, Settings and About stay fixed.
- **HAUI Firmware** update entity in the integration, with the **Firmware update
  channel** (`stable`/`dev`) and **Firmware manifest URL** settings.
- Day/Night profiles for brightness, dimming, idle page and display-off, by time
  window or sunrise/sunset.
- Cycle cards on the weather panel, up to four entity cards and configurable
  card timing.
- Inside temperature sensor picker for clock and weather panels.
- **Long press to go back** option for Clock, ClockTwo and Weather panels.
- Alarm panel action-button options: hidden arm modes and action icons
  ([#75](https://github.com/happydasch/nspanel_haui/pull/75)).
- **Current Page Number** sensor (the Nextion page id); it and **Current
  Page** are disabled by default ([ESPHome](docs/develop/esphome.md#page)).
- **Install update** in the **Device Info** dialog installs the display TFT or
  the firmware, also from a URL or a local file
  ([Updating](docs/user/update.md#installing-a-local-tft-or-firmware-image)).
- **Firmware mismatch** in the Device Manager and Device Info when the HAUI
  version differs from the panel firmware's `yaml_version`; missing versions
  are not a mismatch ([Update Process](docs/develop/update-process.md#in-the-editor)).
- **Enable updates** master switch and **Enable periodic update checks** toggle
  per panel.
- **Color scheme library** in **Device Colors**: built-in **Dark Color**,
  **Light Color**, **White** and **Black** schemes, plus custom schemes shared
  by every device in the hub and importable/exportable as JSON.
- Dark- and light-background weather, alarm and climate icon colors in each
  scheme; a device chooses its default icon variant, and pages with a static
  background use that background's variant.
- **Use color scheme** background for clock, word clock and weather panels:
  the TFT's solid dark/light fill in the scheme's background color with the
  scheme's text and state colors (new display TFT).
- The device YAML export carries the selected custom color scheme; importing it
  restores the scheme.

### Changed

- Changing a color of a built-in scheme in the Colors dialog creates and selects a custom copy automatically.
- Changing the display model asks before installing the matching TFT; saving the setting alone no longer flashes the display.
- Portrait function buttons are back in the header; portrait pages use the full
  height (portrait TFT).
- Repository scripts use `python -m` from the repository root, without import-path setup.
- Row toggles are a switch icon instead of a filled box.
- Cycle cards are off by default on clock and weather panels: only the time
  shows until **Show date**, **Show outside temperature** or other cards are
  enabled (clock panels cycled date and outside temperature before;
  [Upgrading](docs/develop/upgrading.md#045)).
- A clock panel without a weather entity skips the outside temperature card
  instead of showing `--°C`.
- **Screen Power** is disabled by default, like **Restart Display**.
- The **Touch** and **Brightness** sensors are disabled by default; enable them
  on the device page before using them in automations.
- Firmware versions compare like Home Assistant's: a final release is offered
  over its dev builds, an unparseable version counts as unknown, and the
  editor's version chips use the same ordering.
- Dev prereleases ship both display TFTs, and dev panels install the TFT their
  firmware needs ([Release](docs/develop/release.md#published-development-firmware)).
- CI fails a PR or push that changes a Nextion HMI without advancing the display
  TFT version and recompiling both TFTs, reading the base HMI's version when the
  base predates `tft_version`
  ([Release](docs/develop/release.md#published-development-firmware)).
- Panel titles and built-in popup titles are single words where possible, and
  every title is fitted to its header widget (longer ones end in `..`).
- **Auto-install firmware updates** is off by default; the display TFT still
  follows a firmware update on its own.
- The Device Manager finds new panels when it opens; its install picker moved
  to the **Info** dialog (**Install update**, **Redraw display**, **Download
  firmware**), preparing the 0.5 frontend redesign.
- The About page labels the integration version **HAUI Version** (it was
  **AD-Version**).
- The release notice opens once per release instead of after every update check;
  it can appear again after a restart or a channel change
  ([Update Process](docs/develop/update-process.md#on-the-display)).
- A notification sent without an icon shows none and uses the full text width;
  its icon colour and sound are general notification fields
  ([Actions](docs/user/actions.md#nspanel_hauisend_notification)).
- Grid tile, alarm keypad/action-button and Clock Two word colors default to the
  active color scheme; their optional color settings override it per panel or
  item. Values saved from older versions keep overriding until **Reset existing
  panel and item color overrides**.
- Single-entity panels (light, media, vacuum, cover, climate, alarm) accept no
  item and hide their controls when the entity is unavailable or `unknown`;
  light, media and vacuum also show **Unavailable**, and an `unknown` item
  opens the Unavailable message instead of running its action.
- The live preview's hardware buttons show their relay (blue) or the state of
  any entity they switch (yellow; covers report open/closed by position and
  locks, climate, alarm, media and timer entities report their active state);
  **Simulated/Live** is a toolbar switch, and **More tools** shows **Show
  entities** and **Reset sandbox** (Simulated mode only, disabled until a
  simulated state changed).
- A hub reconnect no longer counts as an interaction: the current page is restored at full brightness for the configured dimming timeout, then normal brightness timeouts resume. The hub restarts the idle-page timeout after restoring the page; the idle page and auto-navigate-home now run from one level-triggered hub check ([Device](docs/user/editor/device.md#screen)).

### Fixed

- The Colors dialog shows the device's saved color scheme in its selector again instead of the first built-in scheme.
- On hub disconnect, the firmware shows System at full brightness for `timeout_dim`, then dims without powering off; reconnect restores the current panel with the same grace ([Device](docs/user/editor/device.md#screen)).
- Repeated automation changes to HAUI-owned display switches now trigger a warning and pause corrections until the next connect or settings save, preventing on/off feedback loops ([Device Configuration](docs/user/editor/device.md#screen)).
- The idle page opens reliably again after popups and reconnects: the hub
  checks the activity clock every second instead of relying on one-shot timers
  and firmware events.
- The display turns off after the display-off timeout with auto-dimming
  disabled; one firmware script now owns brightness and display state.
- The display state is published only when it actually changes.
- A tap shorter than the 200 ms coordinate poll counts as an interaction, so
  the display does not dim or turn off during use (firmware).
- Cycle cards switch to a shorter form instead of running past the time area,
  and use a smaller font when a character has no glyph in the large one.
- The `background`, `component_background` and `component_pressed` colour
  overrides reach flat widgets, sliders and pressed buttons.
- Pages load in the device's colours instead of changing colour after they
  are shown, and saved colours apply at once (new display TFT).
- A saved background of the shown clock, word clock or weather panel, and the
  word clock's options, apply at once instead of on the next page change.
- The clock, word clock and weather time/date text and cycle cards follow the
  scheme's text color, and the temperature text no longer turns from grey to
  white after the page is shown (new display TFT).
- The QR page's SSID/password text and the Settings brightness labels,
  percentages and icons use the scheme colors instead of the HMI's dark-only
  ones.
- The Light panel falls back to the panel title when its entity has no name.
- An open notification is no longer replaced by a force-shown one, and the open
  list refreshes.
- Stacked panels and popups show up and home; stacked grids and rows keep their
  close button.
- Grid, row and clock tiles that open a stacked panel or run an action
  (`navigate:`, `action:`) work again instead of showing the entity-unavailable
  notification.
- The unlock popup shows its keypad and title again, has the header of the
  panel it locks (previous and next in navigation), and its navigation works
  on every opening.
- A cleared number field in the panel editor resets the option to its default
  instead of saving 0.
- ESPHome entity ids resolve through the entity registry again, so config sync
  and the inside temperature work with area-prefixed ids
  ([#77](https://github.com/happydasch/nspanel_haui/pull/77)).
- System Health no longer crashes; deprecated device registry calls are gone
  ([#77](https://github.com/happydasch/nspanel_haui/pull/77)).
- The light power button no longer turns black for lights without colour.
- Clock and weather panels and weather rows show 0 °C.
- The home temperature stays visible when the weather entity reports no
  temperature.
- The clock's temperature card shows the panel's own weather on opening.
- Whole numbers print without ".0" (`1012hPa`, `21°C`).
- Dev releases are tagged with their version (`X.Y.Z.devN`), so the Marketplace
  orders them and offers updates correctly.
- Clock, word clock, weather and alarm pages are current after waking the
  display.
- The panel's update notice compares the firmware version, not the TFT version.
- TFT checks no longer guess the required version when the firmware does not
  report it.
- An unchanged display TFT is no longer reinstalled under a newer firmware
  release: the manifest names the TFT's own version and only a newer one
  installs ([#83](https://github.com/happydasch/nspanel_haui/issues/83)).
- Notification paging keeps the **Dismiss** button.
- Notification popups no longer keep the display lit.
- The persistent alert sound starts after quiet hours and is silent inside them.
- The notification indicator blink runs on the hub's worker thread.
- Notification text is wrapped with the display fonts' real glyph widths, and
  the page counter stays visible next to a long title
  ([#84](https://github.com/happydasch/nspanel_haui/issues/84)).
- The update notice shows the release notes as plain text instead of raw
  Markdown ([#84](https://github.com/happydasch/nspanel_haui/issues/84)).
- Notification ids are unique.
- Multi-line notification text renders its line breaks.
- Quotes and backslashes in display text are escaped.
- The services accept the NSPanel HAUI device their device selector offers, not
  only the panel's ESPHome device.
- A TFT upload or firmware install that ends without the panel rebooting is
  reported as failed instead of done.
- A failed TFT upload can be retried without rebooting the panel; the retry
  stopped after 4 KB (vendored `nextion` patch).
- Custom firmware builds find their required TFT in the release of their
  firmware version when the update channel's manifest ships none.
- Device dialogs: the TFT picker names the required TFT version, not the
  firmware version; **Download firmware** skips dev prereleases; disabled
  devices offer no actions that need a running panel; a failed reorder keeps
  the old order; **Remove** asks for confirmation.
- A firmware install request with an unreadable body is refused instead of
  installing the offered firmware on every panel.
- Update checks and installs no longer stall the panel, and a busy hub no
  longer drops the panel's connection.
- Popups, the settings panel and the big QR code no longer leave auto-dimming,
  the idle page or display-off switched off when a saved config reopens them.
- The display no longer turns off with auto display-off disabled: the hub sets
  an auto switch toggled anywhere else back to its setting right away.
- The relays keep their last state across firmware updates and reboots instead
  of switching off on every boot ([ESPHome](docs/develop/esphome.md#interaction)).

### Contributors

Thanks to [@jameshiscott](https://github.com/jameshiscott) for the live preview
([#85](https://github.com/happydasch/nspanel_haui/pull/85),
[#86](https://github.com/happydasch/nspanel_haui/pull/86)) and **Long press to
go back**, and to [@quentinjourdan](https://github.com/quentinjourdan) for the
alarm action-button options ([#75](https://github.com/happydasch/nspanel_haui/pull/75))
and the entity registry fixes ([#77](https://github.com/happydasch/nspanel_haui/pull/77)).

## [0.4.4] — 2026-11-02

### Fixed

- `nspanel_haui.send_notification` accepts `timeout` again, so a notification
  can auto-dismiss ([#78](https://github.com/happydasch/nspanel_haui/issues/78);
  thanks to [@liviusefu](https://github.com/liviusefu)).

## [0.4.3] — 2026-10-28

### Breaking changes

- TFT installs moved from the firmware to the integration; the **Update
  Display** button and the `upload_tft` action are gone
  ([Upgrading](docs/develop/upgrading.md#045)).

### Added

- **HAUI Display** update entity for the display TFT.
- Install another firmware or TFT release, or one from a URL:
  `nspanel_haui.update_firmware` / `nspanel_haui.update_tft` with `version` or
  `url`, and pickers in the Device Manager.
- Device Manager actions **Check for updates** and **Install firmware**.
- `nspanel_haui.update_tft` targets a single panel.
- `scripts/dev_release.py` builds a local test firmware release.

### Changed

- Sounds are off by default (`sound_on_startup`, `sound_on_notification`).
- Production firmware leaves out the diagnostic sensors.
- The update settings are editable per device in the editor.
- Editor dialogs close on a click outside or Escape.

### Fixed

- **Return to the home panel after** works with an idle page.
- Panels can be deleted on the integration page.
- The buzzer no longer sticks on during firmware updates or reboots
  ([#62](https://github.com/happydasch/nspanel_haui/issues/62)).
- Universal-image panels keep their Wi-Fi across firmware updates.
- TFT installs from GitHub releases and GitHub manifest downloads work again
  (larger HTTP buffers).
- **Check for updates** reports its result and installs an outdated TFT.
- Firmware builds fetch the `nextion` patch together with the package.
- The TFT install after a firmware update finds the new release.
- The idle page exits on one touch when the display is on or dimmed.
- The update settings take effect; `check_on_connect` and an hourly
  `update_interval` are the defaults.
- Firmware auto-updates no longer depend on a TFT update.
- Update checks share one cached GitHub request per hub.
- Grid tiles resolve state-keyed colours, and their power buttons are no longer
  cut off.
- The internal temperature sensor is found through the entity registry.
- **Install TFT** stays available when the TFT version is unknown.

## [0.4.2] — 2026-10-27

### Breaking changes

- The ESPHome web server is no longer enabled by default
  ([ESPHome → Web server](docs/develop/esphome.md#web-server-optional)).

### Added

- Firmware auto-update: an **HAUI Firmware** entity and a
  `firmware-manifest.json` per release; the firmware installs before the TFT.
- `scripts/bump_version.py` bumps every version source, the HMI files included.

### Changed

- CI checks version consistency and translations; the release rejects a tag
  that disagrees with `manifest.json`.

### Fixed

- Display reads work on released ESPHome (vendored `nextion` patch).
- The TFT no longer reinstalls after every reboot
  ([#63](https://github.com/happydasch/nspanel_haui/issues/63)).
- The buzzer stops when a TFT upload starts
  ([#62](https://github.com/happydasch/nspanel_haui/issues/62)).
- Portrait weather time and date are centred
  ([#64](https://github.com/happydasch/nspanel_haui/issues/64)).
- Failed TFT installs report why.

### Contributors

Thanks to [@jsenecal](https://github.com/jsenecal) for the reports behind
[#62](https://github.com/happydasch/nspanel_haui/issues/62),
[#63](https://github.com/happydasch/nspanel_haui/issues/63) and
[#64](https://github.com/happydasch/nspanel_haui/issues/64).

## [0.4.1] — 2026-10-26

### Fixed

- Display commands are paced so the Nextion serial buffer no longer overflows;
  Clock Two font size and background fixes.

## [0.4.0] — 2026-10-26

### Breaking changes

- Home Assistant 2026.10 and ESPHome 2026.10 are required.
- Both the ESPHome firmware and the Nextion TFT must be updated; the release
  ships the universal firmware `nspanel_haui.bin`.
- The idle-page service, display settings and ESPHome actions/events were
  renamed, without aliases.
- Notification auto-dismiss (`timeout`) was removed.
- Saved panels are not migrated; the renamed device settings are.
- Compatibility paths were removed: validation is required, and YAML imports,
  colours, templates, function buttons and vacuum batteries follow the
  documented formats.

See [Updating](docs/user/update.md) for the steps.

### Added

- Universal prebuilt firmware: one `nspanel_haui.bin` for any number of EU and
  US/portrait panels.
- Gesture navigation and named gesture sequences.
- Device discovery in the editor (**Device Manager → Scan**).
- Per-device dimming, page and display-off timeouts, and a display-off schedule.
- US display model (`display_model`) with the portrait TFT and US time/date
  formats.
- `nspanel_haui.send_notification` with per-notification text size, `notify`
  entities and `nspanel_haui.reset_last_interaction`.
- Home Assistant events `nspanel_haui.page_changed`, `nspanel_haui.notification`
  and `nspanel_haui.connection_changed`.
- Current page sensor per device.
- Device Manager with panel status, TFT install, firmware download and update
  state; connection details in Device Info.
- Idle panel carousel (`idle_panel_extra`).
- Vacuum battery sensor option and alarm keypad styling.
- Climate panel, `action` item type, preview thumbnails, entity picker with
  search and editor toasts.
- Nextion release gate (`verify_nextion.py`) and installation docs.

### Changed

- Device settings live in the panel store; one worker thread per device.
- The TFT auto-update compares versions on every connect.
- Tapping the clock's time advances the card.
- Edge swipes follow the display model.
- The startup sound plays only after a fresh boot.
- Long notifications are split into pages.
- Dark theme refresh with stepped surfaces.
- Settings and panels save without reloading the hub; removed devices stay
  removed.
- Device settings reach the firmware on save and on every connect.
- The `wakeup` service works without a wakeup panel.
- Climate, weather, row and QR pages follow their entities' state.
- Complete editor translations for de, en, fr, nl and pl.

### Fixed

- Touches, page changes and the heartbeat stay responsive.
- Actions for services without a target run.
- `hub_availability` resets on the last disconnect, not the first.
- Row pages flag stale entity values (`stale_data_seconds`).
- Popups pause auto-dimming on devices named with capitals or `-`.
- Text widgets on grid, row, select, notify and alarm keypad pages sit flat on
  the page background.
- Device settings from 0.3.x are migrated on upgrade.
- The notification indicator takes the idle button's slot when no right header
  slot is free.

[0.5.8]: https://github.com/happydasch/nspanel_haui/compare/v0.5.7...v0.5.8
[0.5.7]: https://github.com/happydasch/nspanel_haui/compare/v0.5.6...v0.5.7
[0.5.6]: https://github.com/happydasch/nspanel_haui/compare/v0.5.5...v0.5.6
[0.5.5]: https://github.com/happydasch/nspanel_haui/compare/v0.5.4...v0.5.5
[0.5.4]: https://github.com/happydasch/nspanel_haui/compare/v0.5.3...v0.5.4
[0.5.3]: https://github.com/happydasch/nspanel_haui/compare/v0.5.2...v0.5.3
[0.5.2]: https://github.com/happydasch/nspanel_haui/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/happydasch/nspanel_haui/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/happydasch/nspanel_haui/compare/v0.4.7...v0.5.0
[0.4.7]: https://github.com/happydasch/nspanel_haui/compare/v0.4.6...v0.4.7
[0.4.6]: https://github.com/happydasch/nspanel_haui/compare/v0.4.5...v0.4.6
[0.4.5]: https://github.com/happydasch/nspanel_haui/compare/v0.4.4...v0.4.5
[0.4.4]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.4
[0.4.3]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.3
[0.4.2]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.2
[0.4.1]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.1
[0.4.0]: https://github.com/happydasch/nspanel_haui/releases/tag/v0.4.0
